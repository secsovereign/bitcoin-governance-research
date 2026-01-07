#!/usr/bin/env python3
"""
Communication Pattern Analysis - Understand how communication patterns affect governance.

Analyzes:
1. Platform-specific patterns (GitHub vs mailing list vs IRC)
2. Cross-platform participation
3. Communication networks
4. Temporal evolution
5. Response patterns
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from collections import defaultdict, Counter
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir, get_analysis_dir
from src.utils.network_analysis import NetworkAnalyzer
from src.schemas.analysis_results import create_result_template

logger = setup_logger()


class CommunicationPatternAnalyzer:
    """Analyzer for communication patterns."""
    
    def __init__(self):
        """Initialize analyzer."""
        self.data_dir = get_data_dir()
        self.processed_dir = self.data_dir / 'processed'
        self.analysis_dir = get_analysis_dir() / 'communication_patterns'
        self.analysis_dir.mkdir(parents=True, exist_ok=True)
        
        self.network_analyzer = NetworkAnalyzer()
    
    def run_analysis(self):
        """Run communication pattern analysis."""
        logger.info("=" * 60)
        logger.info("Communication Pattern Analysis")
        logger.info("=" * 60)
        
        # Load data
        prs = self._load_enriched_prs()
        emails = self._load_emails()
        irc_messages = self._load_irc()
        identity_mappings = self._load_identity_mappings()
        
        # Analyze platform-specific patterns
        platform_patterns = self._analyze_platform_patterns(prs, emails, irc_messages)
        
        # Analyze cross-platform participation
        cross_platform = self._analyze_cross_platform(prs, emails, irc_messages, identity_mappings)
        
        # Build communication networks
        networks = self._build_communication_networks(prs, emails, irc_messages, identity_mappings)
        
        # Analyze temporal evolution
        temporal = self._analyze_temporal_evolution(prs, emails, irc_messages)
        
        # Analyze response patterns
        response_patterns = self._analyze_response_patterns(prs, emails)
        
        # Save results
        self._save_results({
            'platform_patterns': platform_patterns,
            'cross_platform': cross_platform,
            'networks': networks,
            'temporal_evolution': temporal,
            'response_patterns': response_patterns
        })
        
        logger.info("Communication pattern analysis complete")
    
    def _load_enriched_prs(self) -> List[Dict[str, Any]]:
        """Load enriched PR data."""
        prs_file = self.processed_dir / 'enriched_prs.jsonl'
        if not prs_file.exists():
            prs_file = self.processed_dir / 'cleaned_prs.jsonl'
        
        if not prs_file.exists():
            return []
        
        prs = []
        with open(prs_file, 'r') as f:
            for line in f:
                prs.append(json.loads(line))
        return prs
    
    def _load_emails(self) -> List[Dict[str, Any]]:
        """Load email data."""
        emails_file = self.processed_dir / 'cleaned_emails.jsonl'
        if not emails_file.exists():
            return []
        
        emails = []
        with open(emails_file, 'r') as f:
            for line in f:
                emails.append(json.loads(line))
        return emails
    
    def _load_irc(self) -> List[Dict[str, Any]]:
        """Load IRC data."""
        irc_file = self.processed_dir / 'cleaned_irc.jsonl'
        if not irc_file.exists():
            return []
        
        messages = []
        with open(irc_file, 'r') as f:
            for line in f:
                messages.append(json.loads(line))
        return messages
    
    def _load_identity_mappings(self) -> Dict[str, str]:
        """Load identity mappings."""
        mappings_file = get_analysis_dir() / 'user_identities' / 'identity_mappings.json'
        
        if not mappings_file.exists():
            return {}
        
        with open(mappings_file, 'r') as f:
            data = json.load(f)
            github_to_unified = {}
            for unified_id, profile in data.get('unified_profiles', {}).items():
                for gh_user in profile.get('github_usernames', []):
                    github_to_unified[gh_user] = unified_id
            return github_to_unified
    
    def _analyze_platform_patterns(
        self,
        prs: List[Dict[str, Any]],
        emails: List[Dict[str, Any]],
        irc_messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze platform-specific communication patterns."""
        # GitHub patterns
        github_participants = set()
        github_avg_length = []
        
        for pr in prs:
            author = pr.get('author')
            if author:
                github_participants.add(author)
            
            # Average comment length
            for comment in pr.get('comments', []):
                body = comment.get('body', '')
                if body:
                    github_avg_length.append(len(body))
        
        # Email patterns
        email_participants = set()
        email_avg_length = []
        
        for email in emails:
            from_field = email.get('from', '')
            if from_field:
                email_participants.add(from_field)
            
            body = email.get('body', '')
            if body:
                email_avg_length.append(len(body))
        
        # IRC patterns
        irc_participants = set()
        irc_avg_length = []
        
        for msg in irc_messages:
            author = msg.get('author')
            if author:
                irc_participants.add(author)
            
            content = msg.get('content', '')
            if content:
                irc_avg_length.append(len(content))
        
        return {
            'github': {
                'participants': len(github_participants),
                'avg_message_length': sum(github_avg_length) / len(github_avg_length) if github_avg_length else 0,
                'total_messages': len(prs) + sum(len(pr.get('comments', [])) for pr in prs)
            },
            'email': {
                'participants': len(email_participants),
                'avg_message_length': sum(email_avg_length) / len(email_avg_length) if email_avg_length else 0,
                'total_messages': len(emails)
            },
            'irc': {
                'participants': len(irc_participants),
                'avg_message_length': sum(irc_avg_length) / len(irc_avg_length) if irc_avg_length else 0,
                'total_messages': len(irc_messages)
            }
        }
    
    def _analyze_cross_platform(
        self,
        prs: List[Dict[str, Any]],
        emails: List[Dict[str, Any]],
        irc_messages: List[Dict[str, Any]],
        identity_mappings: Dict[str, str]
    ) -> Dict[str, Any]:
        """Analyze cross-platform participation."""
        # Count participants per platform
        github_users = set()
        email_users = set()
        irc_users = set()
        
        for pr in prs:
            author = pr.get('author')
            if author:
                github_users.add(identity_mappings.get(author, author))
        
        for email in emails:
            from_field = email.get('from', '')
            if from_field:
                email_users.add(from_field)
        
        for msg in irc_messages:
            author = msg.get('author')
            if author:
                irc_users.add(author)
        
        # Cross-platform participants
        all_platforms = github_users | email_users | irc_users
        github_only = github_users - email_users - irc_users
        email_only = email_users - github_users - irc_users
        irc_only = irc_users - github_users - email_users
        all_three = github_users & email_users & irc_users
        
        return {
            'total_unique_participants': len(all_platforms),
            'github_only': len(github_only),
            'email_only': len(email_only),
            'irc_only': len(irc_only),
            'all_three_platforms': len(all_three),
            'cross_platform_rate': len(all_three) / len(all_platforms) if all_platforms else 0
        }
    
    def _build_communication_networks(
        self,
        prs: List[Dict[str, Any]],
        emails: List[Dict[str, Any]],
        irc_messages: List[Dict[str, Any]],
        identity_mappings: Dict[str, str]
    ) -> Dict[str, Any]:
        """Build communication networks."""
        nodes = set()
        edges = []
        
        # GitHub network (reviewer -> author)
        for pr in prs:
            author = pr.get('author')
            if author:
                author_unified = identity_mappings.get(author, author)
                nodes.add(author_unified)
                
                for review in pr.get('reviews', []):
                    reviewer = review.get('author')
                    if reviewer:
                        reviewer_unified = identity_mappings.get(reviewer, reviewer)
                        nodes.add(reviewer_unified)
                        edges.append({
                            'source': reviewer_unified,
                            'target': author_unified,
                            'type': 'review',
                            'platform': 'github'
                        })
        
        # Email network (replier -> original author)
        for email in emails:
            from_field = email.get('from', '')
            in_reply_to = email.get('in_reply_to')
            
            if from_field and in_reply_to:
                nodes.add(from_field)
                # Would need to find original author from in_reply_to
                # Simplified for now
                edges.append({
                    'source': from_field,
                    'target': 'unknown',
                    'type': 'reply',
                    'platform': 'email'
                })
        
        return {
            'network_size': {'nodes': len(nodes), 'edges': len(edges)},
            'platforms': ['github', 'email', 'irc'],
            'note': 'Full network analysis requires complete identity resolution'
        }
    
    def _analyze_temporal_evolution(
        self,
        prs: List[Dict[str, Any]],
        emails: List[Dict[str, Any]],
        irc_messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze temporal evolution of communication."""
        # Group by year
        github_by_year = defaultdict(int)
        email_by_year = defaultdict(int)
        irc_by_year = defaultdict(int)
        
        for pr in prs:
            if pr.get('created_at'):
                try:
                    year = datetime.fromisoformat(pr['created_at'].replace('Z', '+00:00')).year
                    github_by_year[year] += 1
                except Exception:
                    pass
        
        for email in emails:
            if email.get('date'):
                try:
                    year = datetime.fromisoformat(email['date'].replace('Z', '+00:00')).year
                    email_by_year[year] += 1
                except Exception:
                    pass
        
        for msg in irc_messages:
            if msg.get('timestamp'):
                try:
                    year = datetime.fromisoformat(msg['timestamp'].replace('Z', '+00:00')).year
                    irc_by_year[year] += 1
                except Exception:
                    pass
        
        return {
            'github_by_year': dict(github_by_year),
            'email_by_year': dict(email_by_year),
            'irc_by_year': dict(irc_by_year)
        }
    
    def _analyze_response_patterns(
        self,
        prs: List[Dict[str, Any]],
        emails: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze response patterns."""
        # Response times in PRs
        response_times = []
        
        for pr in prs:
            created = pr.get('created_at')
            first_comment = None
            
            for comment in pr.get('comments', []):
                comment_time = comment.get('created_at')
                if comment_time and (not first_comment or comment_time < first_comment):
                    first_comment = comment_time
            
            if created and first_comment:
                try:
                    created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    comment_dt = datetime.fromisoformat(first_comment.replace('Z', '+00:00'))
                    hours = (comment_dt - created_dt).total_seconds() / 3600
                    if hours >= 0:
                        response_times.append(hours)
                except Exception:
                    pass
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else None
        
        return {
            'avg_response_time_hours': avg_response_time,
            'total_responses': len(response_times),
            'response_rate': len(response_times) / len(prs) if prs else 0
        }
    
    def _save_results(self, results: Dict[str, Any]):
        """Save analysis results."""
        result = create_result_template('communication_patterns_analysis', '1.0.0')
        result['metadata']['timestamp'] = datetime.now().isoformat()
        result['metadata']['data_sources'] = [
            'data/processed/enriched_prs.jsonl',
            'data/processed/cleaned_emails.jsonl',
            'data/processed/cleaned_irc.jsonl'
        ]
        result['data'] = results
        
        output_file = self.analysis_dir / 'communication_patterns_analysis.json'
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        logger.info(f"Results saved to {output_file}")


def main():
    """Main entry point."""
    analyzer = CommunicationPatternAnalyzer()
    analyzer.run_analysis()
    return 0


if __name__ == '__main__':
    sys.exit(main())

