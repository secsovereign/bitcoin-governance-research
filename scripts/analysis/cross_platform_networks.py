#!/usr/bin/env python3
"""
Cross-Platform Influence Networks - Build comprehensive influence networks across GitHub, IRC, and Email.

Analyzes:
1. Multi-platform identity resolution (GitHub ↔ IRC ↔ Email)
2. Platform-specific networks (per platform)
3. Cross-platform influence (influence across platforms)
4. Influence flow (IRC → Email → GitHub)
5. Hidden influencers (influential in one platform but not others)
"""

import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from collections import defaultdict, Counter
from datetime import datetime, timezone

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir, get_analysis_dir

logger = setup_logger()


class CrossPlatformNetworkAnalyzer:
    """Analyzer for cross-platform influence networks."""
    
    def __init__(self):
        """Initialize analyzer."""
        self.data_dir = get_data_dir()
        self.github_dir = self.data_dir / 'github'
        self.irc_dir = self.data_dir / 'irc'
        self.mailing_dir = self.data_dir / 'mailing_lists'
        self.analysis_dir = get_analysis_dir()
        self.findings_dir = self.analysis_dir / 'findings' / 'data'
        self.findings_dir.mkdir(parents=True, exist_ok=True)
        
        # Identity mappings (simplified - exact matches + common patterns)
        self.identity_mappings = {}
        self._build_identity_mappings()
    
    def _build_identity_mappings(self):
        """Build identity mappings (GitHub username ↔ IRC nickname ↔ Email)."""
        # Known mappings for maintainers (common patterns)
        known_mappings = {
            'sipa': {'irc': 'sipa', 'github': 'sipa'},
            'laanwj': {'irc': 'laanwj', 'github': 'laanwj'},
            'maflcko': {'irc': 'maflcko', 'github': 'maflcko'},
            'fanquake': {'irc': 'fanquake', 'github': 'fanquake'},
            'jnewbery': {'irc': 'jnewbery', 'github': 'jnewbery'},
            'ryanofsky': {'irc': 'ryanofsky', 'github': 'ryanofsky'},
            'achow101': {'irc': 'achow101', 'github': 'achow101'},
        }
        
        for unified_id, platforms in known_mappings.items():
            for platform, username in platforms.items():
                key = f"{platform}:{username.lower()}"
                if key not in self.identity_mappings:
                    self.identity_mappings[key] = unified_id
    
    def run_analysis(self):
        """Run cross-platform network analysis."""
        logger.info("=" * 60)
        logger.info("Cross-Platform Influence Networks Analysis")
        logger.info("=" * 60)
        
        # Load data
        github_prs = self._load_core_prs()
        irc_messages = self._load_irc_messages()
        emails = self._load_emails()
        
        logger.info(f"Loaded {len(github_prs)} GitHub PRs, {len(irc_messages)} IRC messages, {len(emails)} emails")
        
        # Build platform-specific networks
        github_network = self._build_github_network(github_prs)
        irc_network = self._build_irc_network(irc_messages)
        email_network = self._build_email_network(emails)
        
        # Resolve identities across platforms
        identity_resolution = self._resolve_identities(github_prs, irc_messages, emails)
        
        # Build cross-platform networks
        cross_platform_network = self._build_cross_platform_network(
            github_network, irc_network, email_network, identity_resolution
        )
        
        # Analyze influence flow (IRC → Email → GitHub)
        influence_flow = self._analyze_influence_flow(irc_messages, emails, github_prs)
        
        # Identify hidden influencers
        hidden_influencers = self._identify_hidden_influencers(
            github_network, irc_network, email_network, identity_resolution
        )
        
        # Analyze homophily patterns (maintainer clustering)
        homophily_analysis = self._analyze_homophily(github_prs)
        
        # Save results
        results = {
            'github_network': github_network,
            'irc_network': irc_network,
            'email_network': email_network,
            'identity_resolution': identity_resolution,
            'cross_platform_network': cross_platform_network,
            'influence_flow': influence_flow,
            'hidden_influencers': hidden_influencers,
            'homophily_analysis': homophily_analysis,
            'statistics': self._generate_statistics(
                github_network, irc_network, email_network,
                cross_platform_network, identity_resolution, homophily_analysis
            ),
            'methodology': self._get_methodology()
        }
        
        self._save_results(results)
        logger.info("Cross-platform network analysis complete")
    
    def _load_core_prs(self) -> List[Dict[str, Any]]:
        """Load Core repository PRs."""
        prs_file = self.github_dir / 'prs_raw.jsonl'
        if not prs_file.exists():
            parent_data_dir = self.data_dir.parent.parent / 'data' / 'github' / 'prs_raw.jsonl'
            if parent_data_dir.exists():
                prs_file = parent_data_dir
            else:
                return []
        
        prs = []
        with open(prs_file, 'r') as f:
            for line in f:
                try:
                    prs.append(json.loads(line))
                except:
                    continue
        return prs
    
    def _load_irc_messages(self) -> List[Dict[str, Any]]:
        """Load IRC messages."""
        irc_file = self.irc_dir / 'messages.jsonl'
        if not irc_file.exists():
            parent_data_dir = self.data_dir.parent.parent / 'data' / 'irc' / 'messages.jsonl'
            if parent_data_dir.exists():
                irc_file = parent_data_dir
            else:
                return []
        
        messages = []
        with open(irc_file, 'r') as f:
            for line in f:
                try:
                    messages.append(json.loads(line))
                except:
                    continue
        return messages
    
    def _load_emails(self) -> List[Dict[str, Any]]:
        """Load mailing list emails."""
        email_file = self.mailing_dir / 'emails.jsonl'
        if not email_file.exists():
            parent_data_dir = self.data_dir.parent.parent / 'data' / 'mailing_lists' / 'emails.jsonl'
            if parent_data_dir.exists():
                email_file = parent_data_dir
            else:
                return []
        
        emails = []
        with open(email_file, 'r') as f:
            for line in f:
                try:
                    emails.append(json.loads(line))
                except:
                    continue
        return emails
    
    def _build_github_network(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build GitHub influence network (PR reviews, comments)."""
        logger.info("Building GitHub network...")
        
        review_network = defaultdict(lambda: Counter())
        merge_network = defaultdict(lambda: Counter())
        all_actors = set()
        
        for pr in prs:
            author = (pr.get('author') or '').lower()
            merged_by = (pr.get('merged_by') or '').lower()
            
            if author:
                all_actors.add(author)
            if merged_by:
                all_actors.add(merged_by)
            
            if merged_by and author:
                merge_network[merged_by][author] += 1
            
            # Also track reviewers
            for review in (pr.get('reviews') or []):
                reviewer = (review.get('author') or review.get('user', {}).get('login', '') or '').lower()
                if reviewer:
                    all_actors.add(reviewer)
                    if author:
                        review_network[reviewer][author] += 1
        
        return {
            'review_network': {k: dict(v) for k, v in list(review_network.items())[:50]},
            'merge_network': {k: dict(v) for k, v in list(merge_network.items())[:50]},
            'total_actors': len(all_actors)
        }
    
    def _build_irc_network(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build IRC influence network (@mentions, reply patterns)."""
        logger.info("Building IRC network...")
        
        mention_network = defaultdict(lambda: Counter())
        
        for msg in messages:
            nickname = (msg.get('nickname') or '').lower()
            message = (msg.get('message') or '').lower()
            
            # Extract @mentions
            mentions = re.findall(r'@(\w+)', message)
            for mention in mentions:
                mention_network[nickname][mention.lower()] += 1
        
        return {
            'mention_network': {k: dict(v) for k, v in list(mention_network.items())[:50]},
            'total_actors': len(mention_network)
        }
    
    def _build_email_network(self, emails: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build email influence network (replies, mentions)."""
        logger.info("Building email network...")
        
        reply_network = defaultdict(lambda: Counter())
        all_actors = set()
        
        for email in emails:
            from_field = email.get('from', '')
            author = self._extract_email_author(from_field).lower()
            
            if author:
                all_actors.add(author)
            
            # Count replies (simplified)
            in_reply_to = email.get('in_reply_to')
            if in_reply_to:
                reply_network[author]['replies_sent'] += 1
        
        return {
            'reply_network': {k: dict(v) for k, v in list(reply_network.items())[:50]},
            'total_actors': len(all_actors)
        }
    
    def _resolve_identities(
        self,
        github_prs: List[Dict[str, Any]],
        irc_messages: List[Dict[str, Any]],
        emails: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Resolve identities across platforms."""
        logger.info("Resolving identities across platforms...")
        
        # Extract unique users per platform
        github_users = set()
        for pr in github_prs:
            author = (pr.get('author') or '').lower()
            if author:
                github_users.add(author)
            merged_by = (pr.get('merged_by') or '').lower()
            if merged_by:
                github_users.add(merged_by)
        
        irc_users = set()
        for msg in irc_messages:
            nickname = (msg.get('nickname') or '').lower()
            if nickname:
                irc_users.add(nickname)
        
        email_users = set()
        for email in emails:
            from_field = email.get('from', '')
            author = self._extract_email_author(from_field).lower()
            if author:
                email_users.add(author)
        
        # Find overlaps (exact matches)
        github_irc_overlap = github_users & irc_users
        github_email_overlap = github_users & email_users
        irc_email_overlap = irc_users & email_users
        all_platform_overlap = github_users & irc_users & email_users
        
        return {
            'github_users': len(github_users),
            'irc_users': len(irc_users),
            'email_users': len(email_users),
            'github_irc_overlap': len(github_irc_overlap),
            'github_email_overlap': len(github_email_overlap),
            'irc_email_overlap': len(irc_email_overlap),
            'all_platform_overlap': len(all_platform_overlap),
            'overlap_rate_github_irc': len(github_irc_overlap) / len(github_users) if github_users else 0,
            'overlap_rate_github_email': len(github_email_overlap) / len(github_users) if github_users else 0,
            'overlap_rate_irc_email': len(irc_email_overlap) / len(irc_users) if irc_users else 0,
            'overlap_examples': {
                'github_irc': list(github_irc_overlap)[:20],
                'github_email': list(github_email_overlap)[:20],
                'all_platform': list(all_platform_overlap)[:20]
            }
        }
    
    def _build_cross_platform_network(
        self,
        github_network: Dict[str, Any],
        irc_network: Dict[str, Any],
        email_network: Dict[str, Any],
        identity_resolution: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build cross-platform influence network."""
        logger.info("Building cross-platform network...")
        
        # Cross-platform influence (actors appearing on multiple platforms)
        cross_platform_actors = identity_resolution.get('overlap_examples', {})
        
        return {
            'cross_platform_actors': cross_platform_actors,
            'multi_platform_activity': {
                'all_platform': len(cross_platform_actors.get('all_platform', [])),
                'github_irc': len(cross_platform_actors.get('github_irc', [])),
                'github_email': len(cross_platform_actors.get('github_email', []))
            }
        }
    
    def _analyze_influence_flow(
        self,
        irc_messages: List[Dict[str, Any]],
        emails: List[Dict[str, Any]],
        github_prs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze influence flow (IRC → Email → GitHub)."""
        logger.info("Analyzing influence flow...")
        
        # Track PR mentions across platforms over time
        pr_mentions_by_platform = {
            'irc': defaultdict(list),
            'email': defaultdict(list),
            'github': defaultdict(list)
        }
        
        # IRC PR mentions
        for msg in irc_messages:
            message = msg.get('message', '') or ''
            pr_numbers = re.findall(r'(?:PR|#)(\d{4,})', message, re.IGNORECASE)
            timestamp = msg.get('timestamp')
            for pr_num in pr_numbers:
                if timestamp:
                    pr_mentions_by_platform['irc'][pr_num].append(timestamp)
        
        # Email PR mentions
        for email in emails:
            subject = (email.get('subject', '') or '').lower()
            body = (email.get('body', '') or '').lower()
            text = subject + ' ' + body
            pr_numbers = re.findall(r'(?:PR|#)(\d{4,})', text, re.IGNORECASE)
            timestamp = email.get('date')
            for pr_num in pr_numbers:
                if timestamp:
                    pr_mentions_by_platform['email'][pr_num].append(timestamp)
        
        # GitHub PR mentions (PR creation)
        for pr in github_prs:
            pr_num = str(pr.get('number', ''))
            created_at = pr.get('created_at')
            if created_at:
                pr_mentions_by_platform['github'][pr_num].append(created_at)
        
        # Find PRs mentioned in IRC/Email before GitHub creation
        prs_discussed_before_github = []
        for pr_num in set(list(pr_mentions_by_platform['irc'].keys()) + list(pr_mentions_by_platform['email'].keys())):
            github_dates = pr_mentions_by_platform['github'].get(pr_num, [])
            irc_dates = pr_mentions_by_platform['irc'].get(pr_num, [])
            email_dates = pr_mentions_by_platform['email'].get(pr_num, [])
            
            if github_dates and (irc_dates or email_dates):
                # Check if IRC/Email mentions happened before GitHub PR creation
                try:
                    github_date = min([datetime.fromisoformat(d.replace('Z', '+00:00')) for d in github_dates])
                    informal_dates = []
                    for d in irc_dates + email_dates:
                        try:
                            informal_dates.append(datetime.fromisoformat(d.replace('Z', '+00:00')))
                        except:
                            pass
                    
                    if informal_dates:
                        informal_min = min(informal_dates)
                        if informal_min < github_date:
                            prs_discussed_before_github.append(pr_num)
                except:
                    pass
        
        return {
            'prs_mentioned_in_irc': len(pr_mentions_by_platform['irc']),
            'prs_mentioned_in_email': len(pr_mentions_by_platform['email']),
            'prs_discussed_before_github': len(prs_discussed_before_github),
            'flow_rate': len(prs_discussed_before_github) / len(pr_mentions_by_platform['github']) if pr_mentions_by_platform['github'] else 0
        }
    
    def _identify_hidden_influencers(
        self,
        github_network: Dict[str, Any],
        irc_network: Dict[str, Any],
        email_network: Dict[str, Any],
        identity_resolution: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Identify hidden influencers (influential in one platform but not others)."""
        logger.info("Identifying hidden influencers...")
        
        # Actors with high activity in informal channels but low in GitHub
        github_actors = set()
        irc_actors = set()
        email_actors = set()
        
        # Extract actors from networks
        if 'merge_network' in github_network:
            github_actors.update(github_network['merge_network'].keys())
        if 'mention_network' in irc_network:
            irc_actors.update(irc_network['mention_network'].keys())
        if 'reply_network' in email_network:
            email_actors.update(email_network['reply_network'].keys())
        
        # Find hidden influencers
        irc_only = irc_actors - github_actors
        email_only = email_actors - github_actors
        
        return {
            'irc_only_influencers': list(irc_only)[:20],
            'email_only_influencers': list(email_only)[:20],
            'total_hidden_influencers': len(irc_only | email_only)
        }
    
    def _extract_email_author(self, from_field: str) -> str:
        """Extract author from email 'from' field."""
        if not from_field:
            return ''
        
        email_match = re.search(r'[\w\.-]+@[\w\.-]+', from_field)
        if email_match:
            return email_match.group(0).split('@')[0]
        
        name_match = re.search(r'^([^<]+)', from_field)
        if name_match:
            return name_match.group(1).strip()
        
        return from_field.strip()
    
    def _analyze_homophily(self, github_prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze homophily patterns (maintainer clustering) in review network."""
        logger.info("Analyzing homophily patterns...")
        
        # Maintainer list
        MAINTAINERS = {
            'laanwj', 'sipa', 'maflcko', 'fanquake', 'hebasto', 'jnewbery',
            'ryanofsky', 'achow101', 'theuni', 'jonasschnelli', 'Sjors',
            'promag', 'instagibbs', 'TheBlueMatt', 'jonatack', 'gmaxwell',
            'gavinandresen', 'petertodd', 'luke-jr', 'glozow'
        }
        
        # Count review patterns by maintainer status
        same_status_edges = 0
        different_status_edges = 0
        maintainer_to_maintainer = 0
        non_maintainer_to_non_maintainer = 0
        maintainer_to_non_maintainer = 0
        non_maintainer_to_maintainer = 0
        total_review_edges = 0
        
        for pr in github_prs:
            author = (pr.get('author') or '').lower()
            if not author:
                continue
            
            author_is_maintainer = author in MAINTAINERS or author in {m.lower() for m in MAINTAINERS}
            
            # Count reviews
            for review in pr.get('reviews', []):
                reviewer = (review.get('author') or '').lower()
                if not reviewer or reviewer == author:
                    continue
                
                total_review_edges += 1
                reviewer_is_maintainer = reviewer in MAINTAINERS or reviewer in {m.lower() for m in MAINTAINERS}
                
                if reviewer_is_maintainer == author_is_maintainer:
                    same_status_edges += 1
                    if reviewer_is_maintainer:
                        maintainer_to_maintainer += 1
                    else:
                        non_maintainer_to_non_maintainer += 1
                else:
                    different_status_edges += 1
                    if reviewer_is_maintainer:
                        maintainer_to_non_maintainer += 1
                    else:
                        non_maintainer_to_maintainer += 1
        
        # Calculate homophily coefficient
        homophily_coefficient = same_status_edges / total_review_edges if total_review_edges > 0 else 0.0
        
        # Calculate maintainer clustering
        maintainer_reviews = maintainer_to_maintainer + maintainer_to_non_maintainer
        maintainer_review_concentration = maintainer_reviews / total_review_edges if total_review_edges > 0 else 0.0
        
        # Calculate clustering coefficient (maintainer-to-maintainer / all maintainer reviews)
        clustering_coefficient = maintainer_to_maintainer / maintainer_reviews if maintainer_reviews > 0 else 0.0
        
        return {
            'homophily_coefficient': homophily_coefficient,
            'same_status_edges': same_status_edges,
            'different_status_edges': different_status_edges,
            'maintainer_to_maintainer': maintainer_to_maintainer,
            'non_maintainer_to_non_maintainer': non_maintainer_to_non_maintainer,
            'maintainer_to_non_maintainer': maintainer_to_non_maintainer,
            'non_maintainer_to_maintainer': non_maintainer_to_maintainer,
            'total_review_edges': total_review_edges,
            'clustering_coefficient': clustering_coefficient,
            'maintainer_review_concentration': maintainer_review_concentration,
            'interpretation': self._interpret_homophily(homophily_coefficient)
        }
    
    def _interpret_homophily(self, coefficient: float) -> str:
        """Interpret homophily coefficient."""
        if coefficient >= 0.7:
            return 'Very high homophily (strong clustering)'
        elif coefficient >= 0.6:
            return 'High homophily (moderate clustering)'
        elif coefficient >= 0.5:
            return 'Moderate homophily (balanced)'
        else:
            return 'Low homophily (mixed networks)'
    
    def _generate_statistics(
        self,
        github_network: Dict[str, Any],
        irc_network: Dict[str, Any],
        email_network: Dict[str, Any],
        cross_platform_network: Dict[str, Any],
        identity_resolution: Dict[str, Any],
        homophily_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate overall statistics."""
        return {
            'summary': {
                'github_actors': github_network.get('total_actors', 0),
                'irc_actors': irc_network.get('total_actors', 0),
                'email_actors': email_network.get('total_actors', 0),
                'cross_platform_overlap': identity_resolution.get('all_platform_overlap', 0),
                'hidden_influencers': cross_platform_network.get('multi_platform_activity', {}).get('all_platform', 0),
                'homophily_coefficient': homophily_analysis.get('homophily_coefficient', 0.0),
                'clustering_coefficient': homophily_analysis.get('clustering_coefficient', 0.0)
            }
        }
    
    def _get_methodology(self) -> Dict[str, Any]:
        """Get methodology description."""
        return {
            'identity_resolution': 'Exact username matching across platforms',
            'network_construction': 'Mention networks (IRC), reply networks (email), merge networks (GitHub)',
            'influence_flow': 'PR mentions across platforms tracked by timestamp',
            'hidden_influencers': 'Actors with high activity in informal channels but low in GitHub',
            'limitations': [
                'Identity resolution based on exact matches (may miss variations)',
                'Influence flow analysis requires timestamp parsing',
                'Hidden influencers identified by platform activity comparison'
            ]
        }
    
    def _save_results(self, results: Dict[str, Any]):
        """Save analysis results."""
        output_file = self.findings_dir / 'cross_platform_networks.json'
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to {output_file}")


def main():
    """Main entry point."""
    analyzer = CrossPlatformNetworkAnalyzer()
    analyzer.run_analysis()


if __name__ == '__main__':
    main()
