#!/usr/bin/env python3
"""
Enhanced Identity Resolution - Objective methods to resolve identities across platforms.

Methods:
1. Manual alias mapping (documented maintainer identities)
2. PR-mention linking (IRC/email mentions of PR numbers → GitHub PR authors)
3. Email address matching (GitHub commit emails → mailing list emails)
"""

import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple
from collections import defaultdict, Counter

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir, get_analysis_dir
from src.utils.cross_platform_sources import (
    audit_source_overlap,
    extract_pr_numbers,
    load_bitcointalk_posts,
    load_delving_posts,
    load_mailing_lists,
)
from src.utils.maintainers import (
    canonicalize_actor,
    canonicalize_nick,
    documented_identities,
    normalize_login,
)

logger = setup_logger()


class EnhancedIdentityResolver:
    """Enhanced identity resolution using multiple objective methods."""
    
    def __init__(self):
        self.data_dir = get_data_dir()
        self.analysis_dir = get_analysis_dir()
        self.findings_dir = self.analysis_dir / 'findings' / 'data'
        self.findings_dir.mkdir(parents=True, exist_ok=True)
        
        # Build lookup tables from known aliases
        self.github_to_unified = {}
        self.email_to_unified = {}
        self.irc_to_unified = {}
        
        self.identities = documented_identities()
        self._build_alias_lookups()
    
    def _build_alias_lookups(self):
        """Build lookup tables from canonical_maintainers.json."""
        for unified_id, aliases in self.identities.items():
            for gh in aliases.get('github', []):
                self.github_to_unified[gh.lower()] = unified_id
            for email in aliases.get('email', []):
                self.email_to_unified[email.lower()] = unified_id
            for irc in aliases.get('irc', []):
                self.irc_to_unified[irc.lower()] = unified_id
    
    def run_analysis(self):
        """Run enhanced identity resolution."""
        logger.info("=" * 60)
        logger.info("Enhanced Identity Resolution")
        logger.info("=" * 60)
        
        source_audit = audit_source_overlap()

        # Load data
        github_prs = self._load_prs()
        irc_messages = self._load_irc()
        emails, email_meta = load_mailing_lists(dedupe=True)
        delving_posts, _ = load_delving_posts()
        bitcointalk_posts, _ = load_bitcointalk_posts()

        logger.info(
            "Loaded %s PRs, %s IRC, %s emails (%s deduped), %s Delving, %s Bitcointalk",
            len(github_prs),
            len(irc_messages),
            len(emails),
            email_meta.get("duplicates_removed", 0),
            len(delving_posts),
            len(bitcointalk_posts),
        )

        # Method 1: Manual alias resolution
        manual_matches = self._resolve_manual_aliases(
            github_prs, irc_messages, emails, delving_posts, bitcointalk_posts
        )

        # Method 2: PR-mention linking
        pr_mention_matches = self._resolve_pr_mentions(
            github_prs, irc_messages, emails, delving_posts, bitcointalk_posts
        )

        # Method 3: Calculate improved overlap
        improved_overlap = self._calculate_improved_overlap(
            github_prs,
            irc_messages,
            emails,
            delving_posts,
            manual_matches,
            pr_mention_matches,
        )

        # Save results
        results = {
            'source_audit': source_audit,
            'email_load_meta': email_meta,
            'manual_alias_resolution': manual_matches,
            'pr_mention_resolution': pr_mention_matches,
            'improved_overlap': improved_overlap,
            'methodology': {
                'manual_aliases': f'{len(self.identities)} documented identities from canonical_maintainers.json',
                'pr_mentions': 'IRC/email/forum messages containing PR numbers matched to GitHub PR authors',
                'mailing_lists': 'bitcoin-dev + cryptography with message_id dedupe',
                'forums': 'Delving usernames often match GitHub handles; Bitcointalk uses legacy handles',
                'sources': 'GitHub profiles, mailing list signatures, IRC registrations, forum posts'
            }
        }
        
        self._save_results(results)
        self._print_summary(results)
        
        return results
    
    def _load_prs(self) -> List[Dict]:
        """Load GitHub PRs."""
        prs_file = self.data_dir / 'github' / 'prs_raw.jsonl'
        if not prs_file.exists():
            return []
        
        prs = []
        with open(prs_file) as f:
            for line in f:
                try:
                    prs.append(json.loads(line))
                except:
                    continue
        return prs
    
    def _load_irc(self) -> List[Dict]:
        """Load IRC messages."""
        irc_file = self.data_dir / 'irc' / 'messages.jsonl'
        if not irc_file.exists():
            return []
        
        messages = []
        with open(irc_file) as f:
            for line in f:
                try:
                    messages.append(json.loads(line))
                except:
                    continue
        return messages
    
    def _resolve_manual_aliases(
        self, 
        github_prs: List[Dict],
        irc_messages: List[Dict],
        emails: List[Dict],
        delving_posts: List[Dict],
        bitcointalk_posts: List[Dict],
    ) -> Dict[str, Any]:
        """Resolve identities using manual alias mapping."""
        logger.info("Resolving manual aliases...")
        
        # Find GitHub users
        github_users = set()
        for pr in github_prs:
            author = normalize_login(pr.get('author'))
            if author:
                github_users.add(author)
            merged_by = normalize_login(pr.get('merged_by'))
            if merged_by:
                github_users.add(merged_by)
        
        # Find IRC users
        irc_users = set()
        for msg in irc_messages:
            nick = canonicalize_nick(msg.get('nickname'))
            if nick:
                irc_users.add(nick)
        
        # Find email users - extract name from "Name via bitcoin-dev <...>" format
        email_users = set()
        email_names = set()
        for email in emails:
            from_field = email.get('from', '')
            
            # Extract email address if present
            email_match = re.search(r'[\w.+-]+@[\w.-]+\.\w+', from_field)
            if email_match:
                email_users.add(email_match.group().lower())
            
            # Extract name from "Name via bitcoin-dev" format
            name_match = re.match(r'^([^<]+?)(?:\s+via\s+[\w-]+)?\s*<', from_field)
            if name_match:
                name = name_match.group(1).strip().lower()
                if name:
                    email_names.add(name)
        
        # Count matches
        github_resolved = sum(1 for u in github_users if u in self.github_to_unified)
        irc_resolved = sum(1 for u in irc_users if u in self.irc_to_unified)
        email_resolved = sum(1 for u in email_users if u in self.email_to_unified)
        
        # Also check email names against real_name
        name_to_unified = {}
        for unified_id, aliases in self.identities.items():
            real_name = aliases.get('real_name', '').lower()
            if real_name:
                name_to_unified[real_name] = unified_id
                # Also add first name + last name variations
                parts = real_name.split()
                if len(parts) >= 2:
                    name_to_unified[parts[0]] = unified_id  # First name
                    name_to_unified[parts[-1]] = unified_id  # Last name
        
        email_names_resolved = sum(1 for n in email_names if n in name_to_unified or 
                                   any(known in n for known in name_to_unified.keys()))
        
        # Calculate cross-platform matches using aliases
        cross_platform_unified = set()
        for u in github_users:
            unified = self.github_to_unified.get(u)
            if unified:
                # Check if this unified ID also appears in IRC or email
                aliases = self.identities.get(unified, {})
                irc_aliases = [a.lower() for a in aliases.get('irc', [])]
                email_aliases = [a.lower() for a in aliases.get('email', [])]
                real_name = aliases.get('real_name', '').lower()
                
                in_irc = any(a in irc_users for a in irc_aliases)
                in_email = any(a in email_users for a in email_aliases)
                in_email_names = real_name in email_names or any(real_name in n or n in real_name 
                                                                  for n in email_names if len(n) > 3)
                
                if in_irc or in_email or in_email_names:
                    cross_platform_unified.add(unified)
        
        delving_users = {
            (post.get("username") or "").lower()
            for post in delving_posts
            if post.get("username")
        }
        bitcointalk_users = {
            (post.get("author") or "").lower()
            for post in bitcointalk_posts
            if post.get("author")
        }
        github_delving_exact = len(github_users & delving_users)
        github_bitcointalk_exact = len(github_users & bitcointalk_users)

        return {
            'total_known_identities': len(self.identities),
            'github_users_found': len(github_users),
            'github_users_resolved': github_resolved,
            'irc_users_found': len(irc_users),
            'irc_users_resolved': irc_resolved,
            'email_addresses_found': len(email_users),
            'email_addresses_resolved': email_resolved,
            'email_names_found': len(email_names),
            'email_names_resolved': email_names_resolved,
            'delving_users_found': len(delving_users),
            'bitcointalk_users_found': len(bitcointalk_users),
            'github_delving_exact_overlap': github_delving_exact,
            'github_bitcointalk_exact_overlap': github_bitcointalk_exact,
            'cross_platform_unified_identities': len(cross_platform_unified),
            'unified_identities': list(cross_platform_unified)
        }
    
    def _resolve_pr_mentions(
        self,
        github_prs: List[Dict],
        irc_messages: List[Dict],
        emails: List[Dict],
        delving_posts: List[Dict],
        bitcointalk_posts: List[Dict],
    ) -> Dict[str, Any]:
        """Resolve identities by linking PR mentions to PR authors."""
        logger.info("Resolving PR mentions...")
        
        # Build PR number → author mapping
        pr_authors = {}
        for pr in github_prs:
            number = pr.get('number')
            author = (pr.get('author') or '').lower()
            if number and author:
                pr_authors[number] = author
        
        def _collect_mentions(messages, channel):
            mentions = defaultdict(set)
            for item in messages:
                if channel == 'irc':
                    actor = canonicalize_nick(item.get('nickname'))
                    text = item.get('message', '') or ''
                elif channel == 'email':
                    from_field = item.get('from', '')
                    match = re.search(r'[\w.+-]+@[\w.-]+\.\w+', from_field)
                    if not match:
                        continue
                    actor = canonicalize_actor(email=match.group())
                    text = f"{item.get('body', '')} {item.get('subject', '')}"
                elif channel == 'delving':
                    actor = (item.get('username') or '').lower()
                    text = f"{item.get('content', '')} {item.get('cooked_html', '')}"
                else:
                    actor = (item.get('author') or '').lower()
                    text = item.get('content', '') or ''
                if not actor:
                    continue
                for pr_num_str in extract_pr_numbers(text):
                    pr_num = int(pr_num_str)
                    if pr_num in pr_authors:
                        mentions[actor].add(pr_authors[pr_num])
            return mentions

        irc_pr_mentions = _collect_mentions(irc_messages, 'irc')
        email_pr_mentions = _collect_mentions(emails, 'email')
        delving_pr_mentions = _collect_mentions(delving_posts, 'delving')
        bitcointalk_pr_mentions = _collect_mentions(bitcointalk_posts, 'bitcointalk')
        
        # Find potential identity links (someone who mentions PRs by specific authors frequently)
        potential_links = []
        
        # IRC users who frequently mention a specific author's PRs might be that author
        for irc_nick, mentioned_authors in irc_pr_mentions.items():
            author_counts = Counter(mentioned_authors)
            if author_counts:
                top_author, count = author_counts.most_common(1)[0]
                if count >= 3 and irc_nick == top_author:  # Only count self-mentions
                    potential_links.append({
                        'irc': irc_nick,
                        'github': top_author,
                        'pr_mentions': count,
                        'confidence': 'high' if count >= 10 else 'medium'
                    })
        
        return {
            'irc_users_mentioning_prs': len(irc_pr_mentions),
            'email_users_mentioning_prs': len(email_pr_mentions),
            'delving_users_mentioning_prs': len(delving_pr_mentions),
            'bitcointalk_users_mentioning_prs': len(bitcointalk_pr_mentions),
            'total_pr_mentions_irc': sum(len(v) for v in irc_pr_mentions.values()),
            'total_pr_mentions_email': sum(len(v) for v in email_pr_mentions.values()),
            'total_pr_mentions_delving': sum(len(v) for v in delving_pr_mentions.values()),
            'total_pr_mentions_bitcointalk': sum(len(v) for v in bitcointalk_pr_mentions.values()),
            'potential_identity_links': len(potential_links),
            'links': potential_links[:50]  # Top 50
        }
    
    def _calculate_improved_overlap(
        self,
        github_prs: List[Dict],
        irc_messages: List[Dict],
        emails: List[Dict],
        delving_posts: List[Dict],
        manual_matches: Dict,
        pr_mentions: Dict
    ) -> Dict[str, Any]:
        """Calculate improved overlap using all resolution methods."""
        logger.info("Calculating improved overlap...")
        
        github_raw = set()
        irc_raw = set()
        github_canon = set()
        irc_canon = set()
        for pr in github_prs:
            author = (pr.get('author') or '').lower()
            if author:
                github_raw.add(author)
                github_canon.add(normalize_login(author))
        for msg in irc_messages:
            nick = (msg.get('nickname') or '').lower()
            if nick:
                irc_raw.add(nick)
                irc_canon.add(canonicalize_nick(nick))
        
        delving_users = {
            (post.get("username") or "").lower()
            for post in delving_posts
            if post.get("username")
        }
        original_overlap = len(github_raw & irc_raw)
        github_delving_overlap = len(github_raw & delving_users)
        improved_overlap = len(github_canon & irc_canon)
        
        return {
            'original_github_irc_overlap': original_overlap,
            'improved_github_irc_overlap': improved_overlap,
            'github_delving_exact_overlap': github_delving_overlap,
            'improvement': improved_overlap - original_overlap,
            'improvement_percentage': (improved_overlap - original_overlap) / original_overlap * 100 if original_overlap > 0 else 0,
            'github_users': len(github_raw),
            'irc_users': len(irc_raw),
            'delving_users': len(delving_users),
            'unified_maintainers_found': manual_matches.get('cross_platform_unified_identities', 0)
        }
    
    def _print_summary(self, results: Dict):
        """Print summary."""
        print()
        print("=" * 70)
        print("ENHANCED IDENTITY RESOLUTION RESULTS")
        print("=" * 70)
        print()
        
        manual = results['manual_alias_resolution']
        print(f"MANUAL ALIAS RESOLUTION ({manual['total_known_identities']} known identities):")
        print(f"  GitHub users resolved: {manual['github_users_resolved']}/{manual['github_users_found']}")
        print(f"  IRC users resolved: {manual['irc_users_resolved']}/{manual['irc_users_found']}")
        print(f"  Email addresses resolved: {manual['email_addresses_resolved']}/{manual['email_addresses_found']}")
        print(f"  Cross-platform unified: {manual['cross_platform_unified_identities']}")
        print()
        
        pr_mentions = results['pr_mention_resolution']
        print(f"PR MENTION RESOLUTION:")
        print(f"  IRC users mentioning PRs: {pr_mentions['irc_users_mentioning_prs']}")
        print(f"  Email users mentioning PRs: {pr_mentions['email_users_mentioning_prs']}")
        print(f"  Potential identity links: {pr_mentions['potential_identity_links']}")
        print()
        
        overlap = results['improved_overlap']
        print(f"IMPROVED OVERLAP:")
        print(f"  Original GitHub-IRC overlap: {overlap['original_github_irc_overlap']}")
        print(f"  Improved GitHub-IRC overlap: {overlap['improved_github_irc_overlap']}")
        print(f"  Improvement: +{overlap['improvement']} ({overlap['improvement_percentage']:.1f}%)")
        print()
    
    def _save_results(self, results: Dict):
        """Save results."""
        from src.utils.findings_io import save_analysis_json
        written = save_analysis_json('enhanced_identity_resolution.json', results)
        logger.info(f"Saved to {', '.join(str(p) for p in written)}")


def main():
    resolver = EnhancedIdentityResolver()
    resolver.run_analysis()


if __name__ == '__main__':
    main()

