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
try:
    from src.utils.network_analysis import NetworkAnalyzer
    HAS_NETWORK_ANALYZER = True
except ImportError:
    HAS_NETWORK_ANALYZER = False
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
        
        if HAS_NETWORK_ANALYZER:
            self.network_analyzer = NetworkAnalyzer()
        else:
            self.network_analyzer = None
    
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
        
        # Analyze coordination costs
        coordination_costs = self._analyze_coordination_costs(prs, emails, irc_messages)
        
        # Analyze coordination costs temporal (GitHub only for performance)
        # Note: Full email/IRC matching is computationally expensive, so temporal analysis uses GitHub data only
        try:
            coordination_costs_temporal = self._analyze_coordination_costs_temporal(prs, emails, irc_messages)
        except Exception as e:
            logger.warning(f"Coordination costs temporal analysis skipped due to performance: {e}")
            coordination_costs_temporal = {'note': 'Analysis skipped due to performance constraints'}
        
        # Save results
        self._save_results({
            'platform_patterns': platform_patterns,
            'cross_platform': cross_platform,
            'networks': networks,
            'temporal_evolution': temporal,
            'response_patterns': response_patterns,
            'coordination_costs': coordination_costs,
            'coordination_costs_temporal': coordination_costs_temporal
        })
        
        logger.info("Communication pattern analysis complete")
    
    def _load_enriched_prs(self) -> List[Dict[str, Any]]:
        """Load enriched PR data."""
        prs_file = self.processed_dir / 'enriched_prs.jsonl'
        if not prs_file.exists():
            prs_file = self.processed_dir / 'cleaned_prs.jsonl'
        
        # Check parent directory if not found (go up from publication-package/data to commons-research/data)
        if not prs_file.exists():
            parent_processed = self.data_dir.parent.parent / 'data' / 'processed'
            prs_file = parent_processed / 'enriched_prs.jsonl'
            if not prs_file.exists():
                prs_file = parent_processed / 'cleaned_prs.jsonl'
        
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
        # Check parent directory if not found
        if not emails_file.exists():
            parent_processed = self.data_dir.parent.parent / 'data' / 'processed'
            emails_file = parent_processed / 'cleaned_emails.jsonl'
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
        # Check parent directory if not found
        if not irc_file.exists():
            parent_processed = self.data_dir.parent.parent / 'data' / 'processed'
            irc_file = parent_processed / 'cleaned_irc.jsonl'
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
    
    def _analyze_coordination_costs(
        self,
        prs: List[Dict[str, Any]],
        emails: List[Dict[str, Any]],
        irc_messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze coordination costs - communication volume per decision."""
        logger.info("Analyzing coordination costs...")
        
        # PR communication volume
        pr_communication = []
        
        for pr in prs:
            if not pr.get('merged', False):
                continue
            
            pr_number = pr.get('number')
            if not pr_number:
                continue
            
            # Count GitHub communication
            comments_count = len(pr.get('comments', []))
            reviews_count = len(pr.get('reviews', []))
            review_comments_count = len(pr.get('review_comments', []))
            github_volume = comments_count + reviews_count + review_comments_count
            
            # Count email mentions (simple: check if PR number mentioned)
            email_mentions = 0
            pr_str = f"#{pr_number}" or f"pull/{pr_number}"
            for email in emails:
                body = (email.get('body') or '').lower()
                subject = (email.get('subject') or '').lower()
                if pr_str.lower() in body or pr_str.lower() in subject:
                    email_mentions += 1
            
            # Count IRC mentions
            irc_mentions = 0
            for msg in irc_messages:
                message = (msg.get('message') or '').lower()
                if pr_str.lower() in message:
                    irc_mentions += 1
            
            # PR complexity
            files = pr.get('files', [])
            files_count = len(files) if files else 0
            total_additions = pr.get('total_additions', 0) or 0
            total_deletions = pr.get('total_deletions', 0) or 0
            total_changes = total_additions + total_deletions
            
            # Decision timeline
            created = pr.get('created_at')
            merged = pr.get('merged_at')
            decision_time_days = None
            if created and merged:
                try:
                    created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    merged_dt = datetime.fromisoformat(merged.replace('Z', '+00:00'))
                    decision_time_days = (merged_dt - created_dt).days
                except:
                    pass
            
            pr_communication.append({
                'pr_number': pr_number,
                'github_volume': github_volume,
                'email_mentions': email_mentions,
                'irc_mentions': irc_mentions,
                'total_communication': github_volume + email_mentions + irc_mentions,
                'files_count': files_count,
                'total_changes': total_changes,
                'decision_time_days': decision_time_days,
                'participants': len(set(
                    [pr.get('author')] +
                    [c.get('author') for c in pr.get('comments', [])] +
                    [r.get('author') for r in pr.get('reviews', [])]
                ))
            })
        
        # Calculate correlations
        if pr_communication:
            # Group by complexity
            by_complexity = {
                'low': [p for p in pr_communication if p['files_count'] <= 5],
                'medium': [p for p in pr_communication if 5 < p['files_count'] <= 15],
                'high': [p for p in pr_communication if p['files_count'] > 15]
            }
            
            complexity_stats = {}
            for complexity, prs_list in by_complexity.items():
                if prs_list:
                    complexity_stats[complexity] = {
                        'count': len(prs_list),
                        'avg_communication': sum(p['total_communication'] for p in prs_list) / len(prs_list),
                        'avg_participants': sum(p['participants'] for p in prs_list) / len(prs_list),
                        'avg_decision_time': sum(p['decision_time_days'] for p in prs_list if p['decision_time_days']) / len([p for p in prs_list if p['decision_time_days']]) if [p for p in prs_list if p['decision_time_days']] else None
                    }
            
            # Overall stats
            overall_stats = {
                'total_prs': len(pr_communication),
                'avg_communication_per_pr': sum(p['total_communication'] for p in pr_communication) / len(pr_communication),
                'avg_participants_per_pr': sum(p['participants'] for p in pr_communication) / len(pr_communication),
                'avg_decision_time_days': sum(p['decision_time_days'] for p in pr_communication if p['decision_time_days']) / len([p for p in pr_communication if p['decision_time_days']]) if [p for p in pr_communication if p['decision_time_days']] else None
            }
        else:
            complexity_stats = {}
            overall_stats = {}
        
        return {
            'overall': overall_stats,
            'by_complexity': complexity_stats,
            'interpretation': {
                'communication_volume': 'Total messages/comments/reviews per PR',
                'coordination_overhead': 'How much communication is needed per decision',
                'complexity_correlation': 'Does coordination cost increase with PR complexity?'
            }
        }
    
    def _analyze_coordination_costs_temporal(
        self,
        prs: List[Dict[str, Any]],
        emails: List[Dict[str, Any]],
        irc_messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze coordination costs over time (GitHub only for performance)."""
        logger.info("Analyzing coordination costs temporal patterns (GitHub data only)...")
        
        # Group PRs by year
        prs_by_year = defaultdict(list)
        for pr in prs:
            if not pr.get('merged', False):
                continue
            created = pr.get('created_at')
            if created:
                try:
                    year = datetime.fromisoformat(created.replace('Z', '+00:00')).year
                    prs_by_year[year].append(pr)
                except:
                    pass
        
        temporal_costs = {}
        
        for year in sorted(prs_by_year.keys()):
            year_prs = prs_by_year[year]
            if len(year_prs) < 50:  # Require minimum PRs
                continue
            
            # Analyze coordination costs for this year (GitHub only for performance)
            year_communication = []
            
            for pr in year_prs:
                pr_number = pr.get('number')
                if not pr_number:
                    continue
                
                # Count GitHub communication only (email/IRC matching is too slow)
                comments_count = len(pr.get('comments', []))
                reviews_count = len(pr.get('reviews', []))
                review_comments_count = len(pr.get('review_comments', []))
                github_volume = comments_count + reviews_count + review_comments_count
                
                # Decision timeline
                created = pr.get('created_at')
                merged = pr.get('merged_at')
                decision_time_days = None
                if created and merged:
                    try:
                        created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                        merged_dt = datetime.fromisoformat(merged.replace('Z', '+00:00'))
                        decision_time_days = (merged_dt - created_dt).days
                    except:
                        pass
                
                year_communication.append({
                    'github_volume': github_volume,
                    'total_communication': github_volume,  # GitHub only
                    'decision_time_days': decision_time_days,
                    'participants': len(set(
                        [pr.get('author')] +
                        [c.get('author') for c in pr.get('comments', [])] +
                        [r.get('author') for r in pr.get('reviews', [])]
                    ))
                })
            
            if year_communication:
                temporal_costs[year] = {
                    'total_prs': len(year_communication),
                    'avg_communication_per_pr': sum(p['total_communication'] for p in year_communication) / len(year_communication),
                    'avg_participants_per_pr': sum(p['participants'] for p in year_communication) / len(year_communication),
                    'avg_decision_time_days': sum(p['decision_time_days'] for p in year_communication if p['decision_time_days']) / len([p for p in year_communication if p['decision_time_days']]) if [p for p in year_communication if p['decision_time_days']] else None,
                    'note': 'GitHub data only - email/IRC matching skipped for performance'
                }
        
        return temporal_costs
    
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

