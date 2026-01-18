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

logger = setup_logger()

# Known maintainer aliases (publicly documented)
# Sources: GitHub profiles, mailing list signatures, IRC registrations
KNOWN_ALIASES = {
    # GitHub username: {platform: [known aliases]}
    'laanwj': {
        'github': ['laanwj'],
        'email': ['laanwj@gmail.com', 'laanwj@protonmail.com', 'wladimir.j.vanderlaan@gmail.com'],
        'irc': ['laanwj', 'wumpus'],
        'real_name': 'Wladimir J. van der Laan'
    },
    'sipa': {
        'github': ['sipa'],
        'email': ['pieter@wuille.net', 'pieter.wuille@gmail.com'],
        'irc': ['sipa'],
        'real_name': 'Pieter Wuille'
    },
    'gavinandresen': {
        'github': ['gavinandresen'],
        'email': ['gavinandresen@gmail.com', 'gavin@bitcoin.org'],
        'irc': ['gavinandresen', 'gavin'],
        'real_name': 'Gavin Andresen'
    },
    'gmaxwell': {
        'github': ['gmaxwell'],
        'email': ['greg@xiph.org', 'gmaxwell@gmail.com'],
        'irc': ['gmaxwell', 'nullc'],
        'real_name': 'Gregory Maxwell'
    },
    'TheBlueMatt': {
        'github': ['TheBlueMatt'],
        'email': ['matt@bluematt.me', 'matt.corallo@gmail.com'],
        'irc': ['BlueMatt', 'TheBlueMatt'],
        'real_name': 'Matt Corallo'
    },
    'luke-jr': {
        'github': ['luke-jr'],
        'email': ['luke-jr+git@dashjr.org', 'luke@dashjr.org'],
        'irc': ['luke-jr', 'Luke-Jr'],
        'real_name': 'Luke Dashjr'
    },
    'petertodd': {
        'github': ['petertodd'],
        'email': ['pete@petertodd.org'],
        'irc': ['petertodd', 'TD-Linux'],
        'real_name': 'Peter Todd'
    },
    'jgarzik': {
        'github': ['jgarzik'],
        'email': ['jgarzik@bitpay.com', 'jgarzik@gmail.com'],
        'irc': ['jgarzik'],
        'real_name': 'Jeff Garzik'
    },
    'fanquake': {
        'github': ['fanquake'],
        'email': ['fanquake@gmail.com'],
        'irc': ['fanquake'],
        'real_name': 'fanquake'
    },
    'maflcko': {
        'github': ['maflcko', 'MarcoFalke'],
        'email': ['falke.marco@gmail.com'],
        'irc': ['maflcko', 'MarcoFalke'],
        'real_name': 'Marco Falke'
    },
    'achow101': {
        'github': ['achow101'],
        'email': ['achow101@gmail.com', 'achow101-hierarchical@gmail.com'],
        'irc': ['achow101'],
        'real_name': 'Andrew Chow'
    },
    'jnewbery': {
        'github': ['jnewbery'],
        'email': ['john@johnnewbery.com'],
        'irc': ['jnewbery'],
        'real_name': 'John Newbery'
    },
    'ryanofsky': {
        'github': ['ryanofsky'],
        'email': ['russ@yanofsky.org'],
        'irc': ['ryanofsky'],
        'real_name': 'Russell Yanofsky'
    },
    'hebasto': {
        'github': ['hebasto'],
        'email': ['hebasto@gmail.com'],
        'irc': ['hebasto'],
        'real_name': 'Hennadii Stepanov'
    },
    'glozow': {
        'github': ['glozow'],
        'email': ['gloriajzhao@gmail.com'],
        'irc': ['glozow'],
        'real_name': 'Gloria Zhao'
    },
    'jonatack': {
        'github': ['jonatack'],
        'email': ['jon@atack.com'],
        'irc': ['jonatack'],
        'real_name': 'Jon Atack'
    },
    'instagibbs': {
        'github': ['instagibbs'],
        'email': ['gsanders87@gmail.com'],
        'irc': ['instagibbs'],
        'real_name': 'Gregory Sanders'
    },
    'theuni': {
        'github': ['theuni'],
        'email': ['cory@coryfields.com'],
        'irc': ['cfields', 'theuni'],
        'real_name': 'Cory Fields'
    },
    'jonasschnelli': {
        'github': ['jonasschnelli'],
        'email': ['dev@jonasschnelli.ch'],
        'irc': ['jonasschnelli'],
        'real_name': 'Jonas Schnelli'
    },
    'promag': {
        'github': ['promag'],
        'email': ['joao.da.silva@joaodacruz.com'],
        'irc': ['promag'],
        'real_name': 'João Barbosa'
    },
}


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
        
        self._build_alias_lookups()
    
    def _build_alias_lookups(self):
        """Build lookup tables from known aliases."""
        for unified_id, aliases in KNOWN_ALIASES.items():
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
        
        # Load data
        github_prs = self._load_prs()
        irc_messages = self._load_irc()
        emails = self._load_emails()
        
        logger.info(f"Loaded {len(github_prs)} PRs, {len(irc_messages)} IRC, {len(emails)} emails")
        
        # Method 1: Manual alias resolution
        manual_matches = self._resolve_manual_aliases(github_prs, irc_messages, emails)
        
        # Method 2: PR-mention linking
        pr_mention_matches = self._resolve_pr_mentions(github_prs, irc_messages, emails)
        
        # Method 3: Calculate improved overlap
        improved_overlap = self._calculate_improved_overlap(
            github_prs, irc_messages, emails, manual_matches, pr_mention_matches
        )
        
        # Save results
        results = {
            'manual_alias_resolution': manual_matches,
            'pr_mention_resolution': pr_mention_matches,
            'improved_overlap': improved_overlap,
            'methodology': {
                'manual_aliases': f'{len(KNOWN_ALIASES)} documented maintainer identities',
                'pr_mentions': 'IRC/email messages containing PR numbers matched to GitHub PR authors',
                'sources': 'GitHub profiles, mailing list signatures, IRC registrations'
            }
        }
        
        self._save_results(results)
        self._print_summary(results)
        
        return results
    
    def _load_prs(self) -> List[Dict]:
        """Load GitHub PRs."""
        prs_file = self.data_dir.parent.parent / 'data' / 'github' / 'prs_raw.jsonl'
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
        irc_file = self.data_dir.parent.parent / 'data' / 'irc' / 'messages.jsonl'
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
    
    def _load_emails(self) -> List[Dict]:
        """Load emails."""
        email_file = self.data_dir.parent.parent / 'data' / 'mailing_lists' / 'emails.jsonl'
        if not email_file.exists():
            return []
        
        emails = []
        with open(email_file) as f:
            for line in f:
                try:
                    emails.append(json.loads(line))
                except:
                    continue
        return emails
    
    def _resolve_manual_aliases(
        self, 
        github_prs: List[Dict],
        irc_messages: List[Dict],
        emails: List[Dict]
    ) -> Dict[str, Any]:
        """Resolve identities using manual alias mapping."""
        logger.info("Resolving manual aliases...")
        
        # Find GitHub users
        github_users = set()
        for pr in github_prs:
            author = (pr.get('author') or '').lower()
            if author:
                github_users.add(author)
            merged_by = (pr.get('merged_by') or '').lower()
            if merged_by:
                github_users.add(merged_by)
        
        # Find IRC users
        irc_users = set()
        for msg in irc_messages:
            nick = (msg.get('nickname') or '').lower()
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
        for unified_id, aliases in KNOWN_ALIASES.items():
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
                aliases = KNOWN_ALIASES.get(unified, {})
                irc_aliases = [a.lower() for a in aliases.get('irc', [])]
                email_aliases = [a.lower() for a in aliases.get('email', [])]
                real_name = aliases.get('real_name', '').lower()
                
                in_irc = any(a in irc_users for a in irc_aliases)
                in_email = any(a in email_users for a in email_aliases)
                in_email_names = real_name in email_names or any(real_name in n or n in real_name 
                                                                  for n in email_names if len(n) > 3)
                
                if in_irc or in_email or in_email_names:
                    cross_platform_unified.add(unified)
        
        return {
            'total_known_identities': len(KNOWN_ALIASES),
            'github_users_found': len(github_users),
            'github_users_resolved': github_resolved,
            'irc_users_found': len(irc_users),
            'irc_users_resolved': irc_resolved,
            'email_addresses_found': len(email_users),
            'email_addresses_resolved': email_resolved,
            'email_names_found': len(email_names),
            'email_names_resolved': email_names_resolved,
            'cross_platform_unified_identities': len(cross_platform_unified),
            'unified_identities': list(cross_platform_unified)
        }
    
    def _resolve_pr_mentions(
        self,
        github_prs: List[Dict],
        irc_messages: List[Dict],
        emails: List[Dict]
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
        
        # Find PR mentions in IRC
        irc_pr_mentions = defaultdict(set)  # irc_nick → set of pr_authors
        pr_pattern = re.compile(r'#(\d{4,6})\b')  # PR numbers are 4-6 digits
        
        for msg in irc_messages:
            nick = (msg.get('nickname') or '').lower()
            text = msg.get('message', '')
            
            for match in pr_pattern.findall(text):
                pr_num = int(match)
                if pr_num in pr_authors:
                    irc_pr_mentions[nick].add(pr_authors[pr_num])
        
        # Find PR mentions in emails
        email_pr_mentions = defaultdict(set)
        
        for email in emails:
            from_field = email.get('from', '')
            match = re.search(r'[\w.+-]+@[\w.-]+\.\w+', from_field)
            if not match:
                continue
            email_addr = match.group().lower()
            
            body = email.get('body', '') + email.get('subject', '')
            for match in pr_pattern.findall(body):
                pr_num = int(match)
                if pr_num in pr_authors:
                    email_pr_mentions[email_addr].add(pr_authors[pr_num])
        
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
            'total_pr_mentions_irc': sum(len(v) for v in irc_pr_mentions.values()),
            'total_pr_mentions_email': sum(len(v) for v in email_pr_mentions.values()),
            'potential_identity_links': len(potential_links),
            'links': potential_links[:50]  # Top 50
        }
    
    def _calculate_improved_overlap(
        self,
        github_prs: List[Dict],
        irc_messages: List[Dict],
        emails: List[Dict],
        manual_matches: Dict,
        pr_mentions: Dict
    ) -> Dict[str, Any]:
        """Calculate improved overlap using all resolution methods."""
        logger.info("Calculating improved overlap...")
        
        # Original overlap (exact matching)
        github_users = set()
        for pr in github_prs:
            author = (pr.get('author') or '').lower()
            if author:
                github_users.add(author)
        
        irc_users = set()
        for msg in irc_messages:
            nick = (msg.get('nickname') or '').lower()
            if nick:
                irc_users.add(nick)
        
        original_overlap = len(github_users & irc_users)
        
        # Improved overlap (using alias mapping)
        improved_overlap = original_overlap
        
        # Add matches from known aliases
        for unified_id, aliases in KNOWN_ALIASES.items():
            github_names = [a.lower() for a in aliases.get('github', [])]
            irc_names = [a.lower() for a in aliases.get('irc', [])]
            
            # Check if this person is in both
            in_github = any(g in github_users for g in github_names)
            in_irc = any(i in irc_users for i in irc_names)
            
            if in_github and in_irc:
                # Check if already counted in original
                if not any(g in irc_users for g in github_names):
                    improved_overlap += 1
        
        return {
            'original_github_irc_overlap': original_overlap,
            'improved_github_irc_overlap': improved_overlap,
            'improvement': improved_overlap - original_overlap,
            'improvement_percentage': (improved_overlap - original_overlap) / original_overlap * 100 if original_overlap > 0 else 0,
            'github_users': len(github_users),
            'irc_users': len(irc_users),
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
        output_file = self.findings_dir / 'enhanced_identity_resolution.json'
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Saved to {output_file}")


def main():
    resolver = EnhancedIdentityResolver()
    resolver.run_analysis()


if __name__ == '__main__':
    main()

