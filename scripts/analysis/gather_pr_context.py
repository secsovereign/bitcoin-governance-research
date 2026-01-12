#!/usr/bin/env python3
"""
Gather all context for a specific PR for governance analysis.

This script collects all available data about a specific PR across all data sources:
- GitHub PR data (comments, reviews, metadata)
- IRC messages mentioning the PR
- Mailing list emails mentioning the PR
- Related commits
- Maintainer information
- Timeline of events

Output: Structured JSON file ready for AI analysis
"""

import sys
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir

logger = setup_logger()


class PRContextGatherer:
    """Gather all context for a specific PR."""
    
    def __init__(self):
        """Initialize PR context gatherer."""
        self.data_dir = get_data_dir()
        self.github_dir = self.data_dir / 'github'
        self.irc_dir = self.data_dir / 'irc'
        self.mailing_lists_dir = self.data_dir / 'mailing_lists'
        
        # Load maintainer list
        self.maintainers = {
            'laanwj', 'sipa', 'maflcko', 'fanquake', 'hebasto', 'jnewbery',
            'ryanofsky', 'achow101', 'theuni', 'jonasschnelli', 'Sjors',
            'promag', 'instagibbs', 'TheBlueMatt', 'jonatack', 'gmaxwell',
            'gavinandresen', 'petertodd', 'luke-jr', 'glozow'
        }
    
    def gather_pr_context(self, pr_number: int) -> Dict[str, Any]:
        """Gather all context for a specific PR.
        
        Args:
            pr_number: PR number to analyze
            
        Returns:
            Dictionary with all collected context
        """
        logger.info(f"Gathering context for PR #{pr_number}")
        
        context = {
            'pr_number': pr_number,
            'gathered_at': datetime.now().isoformat(),
            'github_pr': None,
            'related_commits': [],
            'irc_messages': [],
            'mailing_list_emails': [],
            'timeline': [],
            'participants': {},
            'governance_indicators': {}
        }
        
        # 1. Get GitHub PR data
        context['github_pr'] = self._get_github_pr(pr_number)
        if not context['github_pr']:
            logger.error(f"PR #{pr_number} not found in GitHub data")
            return context
        
        # 2. Get related commits
        context['related_commits'] = self._get_related_commits(pr_number, context['github_pr'])
        
        # 3. Get IRC messages
        context['irc_messages'] = self._get_irc_messages(pr_number, context['github_pr'])
        
        # 4. Get mailing list emails
        context['mailing_list_emails'] = self._get_mailing_list_emails(pr_number, context['github_pr'])
        
        # 5. Build timeline
        context['timeline'] = self._build_timeline(context)
        
        # 6. Analyze participants
        context['participants'] = self._analyze_participants(context)
        
        # 7. Extract governance indicators
        context['governance_indicators'] = self._extract_governance_indicators(context)
        
        logger.info(f"Gathered context: {len(context['irc_messages'])} IRC messages, "
                   f"{len(context['mailing_list_emails'])} emails, "
                   f"{len(context['related_commits'])} commits")
        
        return context
    
    def _get_github_pr(self, pr_number: int) -> Optional[Dict[str, Any]]:
        """Get GitHub PR data."""
        prs_file = self.github_dir / 'prs_raw.jsonl'
        if not prs_file.exists():
            logger.error(f"PRs file not found: {prs_file}")
            return None
        
        with open(prs_file) as f:
            for line in f:
                try:
                    pr = json.loads(line)
                    if pr.get('number') == pr_number:
                        return pr
                except:
                    continue
        
        return None
    
    def _get_related_commits(self, pr_number: int, pr_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get commits related to this PR."""
        commits_file = self.github_dir / 'commits_raw.jsonl'
        if not commits_file.exists():
            return []
        
        related = []
        
        # Method 1: Merge commit with PR number in message
        with open(commits_file) as f:
            for line in f:
                try:
                    commit = json.loads(line)
                    if commit.get('merged_pr_number') == pr_number:
                        related.append(commit)
                except:
                    continue
        
        # Method 2: Commits by PR author in PR timeframe
        if pr_data:
            pr_author = pr_data.get('user', {}).get('login')
            created_at = pr_data.get('created_at')
            merged_at = pr_data.get('merged_at')
            
            if pr_author and created_at:
                with open(commits_file) as f:
                    for line in f:
                        try:
                            commit = json.loads(line)
                            commit_author = commit.get('author', {}).get('login')
                            commit_date = commit.get('author', {}).get('date')
                            
                            if (commit_author == pr_author and 
                                commit_date and created_at and 
                                commit_date >= created_at[:10] and
                                (not merged_at or commit_date <= merged_at[:10])):
                                # Avoid duplicates
                                if commit.get('sha') not in [c.get('sha') for c in related]:
                                    related.append(commit)
                        except:
                            continue
        
        return related
    
    def _get_irc_messages(self, pr_number: int, pr_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get IRC messages mentioning this PR."""
        irc_file = self.irc_dir / 'messages.jsonl'
        if not irc_file.exists():
            return []
        
        messages = []
        pr_pattern = re.compile(rf'#{pr_number}\b', re.IGNORECASE)
        
        # Search terms: PR number, PR title keywords, author username
        search_terms = [f"#{pr_number}"]
        if pr_data:
            title = pr_data.get('title', '')
            # Extract key words from title (3+ chars)
            title_words = [w for w in re.findall(r'\b\w{3,}\b', title.lower()) if len(w) >= 3]
            search_terms.extend(title_words[:5])  # Top 5 words
            
            author = pr_data.get('user', {}).get('login', '')
            if author:
                search_terms.append(author.lower())
        
        with open(irc_file) as f:
            for line in f:
                try:
                    msg = json.loads(line)
                    message_text = msg.get('message', '').lower()
                    
                    # Check if message mentions PR number or related terms
                    if pr_pattern.search(message_text):
                        messages.append(msg)
                    elif any(term in message_text for term in search_terms[1:]):  # Skip PR number, already checked
                        # Additional context: check if it's within PR timeframe
                        if pr_data:
                            msg_date = msg.get('timestamp', '')[:10]
                            pr_created = pr_data.get('created_at', '')[:10]
                            pr_merged = pr_data.get('merged_at', '')[:10] if pr_data.get('merged_at') else None
                            
                            if msg_date >= pr_created and (not pr_merged or msg_date <= pr_merged):
                                messages.append(msg)
                except:
                    continue
        
        return messages
    
    def _get_mailing_list_emails(self, pr_number: int, pr_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get mailing list emails mentioning this PR."""
        emails_file = self.mailing_lists_dir / 'emails.jsonl'
        if not emails_file.exists():
            return []
        
        emails = []
        pr_pattern = re.compile(rf'#{pr_number}\b', re.IGNORECASE)
        
        # Search terms: PR number, PR title keywords, author username
        search_terms = [f"#{pr_number}"]
        if pr_data:
            title = pr_data.get('title', '')
            title_words = [w for w in re.findall(r'\b\w{3,}\b', title.lower()) if len(w) >= 3]
            search_terms.extend(title_words[:5])
            
            author = pr_data.get('user', {}).get('login', '')
            if author:
                search_terms.append(author.lower())
        
        with open(emails_file) as f:
            for line in f:
                try:
                    email = json.loads(line)
                    subject = email.get('subject', '').lower()
                    body = email.get('body', '').lower()
                    
                    # Check if email mentions PR number or related terms
                    if pr_pattern.search(subject) or pr_pattern.search(body):
                        emails.append(email)
                    elif any(term in subject or term in body for term in search_terms[1:]):
                        # Additional context: check if it's within PR timeframe
                        if pr_data:
                            email_date = email.get('date', '')[:10]
                            pr_created = pr_data.get('created_at', '')[:10]
                            pr_merged = pr_data.get('merged_at', '')[:10] if pr_data.get('merged_at') else None
                            
                            if email_date >= pr_created and (not pr_merged or email_date <= pr_merged):
                                emails.append(email)
                except:
                    continue
        
        return emails
    
    def _build_timeline(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build chronological timeline of events."""
        timeline = []
        
        pr = context.get('github_pr')
        if pr:
            # PR creation
            timeline.append({
                'timestamp': pr.get('created_at'),
                'type': 'pr_created',
                'actor': pr.get('user', {}).get('login'),
                'description': f"PR #{pr.get('number')} created: {pr.get('title', '')[:60]}"
            })
            
            # PR comments
            for comment in pr.get('comments', []):
                timeline.append({
                    'timestamp': comment.get('created_at'),
                    'type': 'comment',
                    'actor': comment.get('user', {}).get('login'),
                    'description': comment.get('body', '')[:100],
                    'full_text': comment.get('body', '')
                })
            
            # PR reviews
            for review in pr.get('reviews', []):
                timeline.append({
                    'timestamp': review.get('submitted_at'),
                    'type': f"review_{review.get('state', 'unknown')}",
                    'actor': review.get('user', {}).get('login'),
                    'description': review.get('body', '')[:100] or f"{review.get('state', 'unknown')} review",
                    'full_text': review.get('body', '')
                })
            
            # PR merge
            if pr.get('merged_at'):
                timeline.append({
                    'timestamp': pr.get('merged_at'),
                    'type': 'pr_merged',
                    'actor': pr.get('merged_by', {}).get('login'),
                    'description': f"PR merged by {pr.get('merged_by', {}).get('login', 'unknown')}"
                })
        
        # IRC messages
        for msg in context.get('irc_messages', []):
            timeline.append({
                'timestamp': msg.get('timestamp'),
                'type': 'irc_message',
                'actor': msg.get('nickname'),
                'description': msg.get('message', '')[:100],
                'channel': msg.get('channel'),
                'full_text': msg.get('message', '')
            })
        
        # Mailing list emails
        for email in context.get('mailing_list_emails', []):
            timeline.append({
                'timestamp': email.get('date'),
                'type': 'email',
                'actor': email.get('from', ''),
                'description': email.get('subject', '')[:100],
                'full_text': email.get('body', '')
            })
        
        # Commits
        for commit in context.get('related_commits', []):
            timeline.append({
                'timestamp': commit.get('author', {}).get('date'),
                'type': 'commit',
                'actor': commit.get('author', {}).get('login'),
                'description': commit.get('message', '')[:100],
                'sha': commit.get('sha')
            })
        
        # Sort by timestamp
        timeline.sort(key=lambda x: x.get('timestamp', ''))
        
        return timeline
    
    def _analyze_participants(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze participants and their roles."""
        participants = defaultdict(lambda: {
            'roles': set(),
            'activities': [],
            'is_maintainer': False
        })
        
        pr = context.get('github_pr')
        if pr:
            # PR author
            author = pr.get('user', {}).get('login')
            if author:
                participants[author]['roles'].add('pr_author')
                participants[author]['is_maintainer'] = author in self.maintainers
            
            # Merged by
            merged_by = pr.get('merged_by', {}).get('login')
            if merged_by:
                participants[merged_by]['roles'].add('merger')
                participants[merged_by]['is_maintainer'] = merged_by in self.maintainers
            
            # Commenters
            for comment in pr.get('comments', []):
                commenter = comment.get('user', {}).get('login')
                if commenter:
                    participants[commenter]['roles'].add('commenter')
                    participants[commenter]['is_maintainer'] = commenter in self.maintainers
                    participants[commenter]['activities'].append({
                        'type': 'comment',
                        'timestamp': comment.get('created_at')
                    })
                else:
                    # Handle cases where user might be None or missing
                    commenter_name = comment.get('user', {}).get('login') or 'unknown'
                    if commenter_name != 'unknown':
                        participants[commenter_name]['roles'].add('commenter')
                        participants[commenter_name]['activities'].append({
                            'type': 'comment',
                            'timestamp': comment.get('created_at')
                        })
            
            # Reviewers
            for review in pr.get('reviews', []):
                reviewer = review.get('user', {}).get('login')
                if reviewer:
                    participants[reviewer]['roles'].add('reviewer')
                    participants[reviewer]['is_maintainer'] = reviewer in self.maintainers
                    participants[reviewer]['activities'].append({
                        'type': f"review_{review.get('state')}",
                        'timestamp': review.get('submitted_at')
                    })
                else:
                    # Handle cases where user might be None or missing
                    reviewer_name = review.get('user', {}).get('login') or 'unknown'
                    if reviewer_name != 'unknown':
                        participants[reviewer_name]['roles'].add('reviewer')
                        participants[reviewer_name]['activities'].append({
                            'type': f"review_{review.get('state')}",
                            'timestamp': review.get('submitted_at')
                        })
        
        # IRC participants
        for msg in context.get('irc_messages', []):
            nick = msg.get('nickname')
            if nick:
                participants[nick]['roles'].add('irc_participant')
                participants[nick]['activities'].append({
                    'type': 'irc_message',
                    'timestamp': msg.get('timestamp')
                })
        
        # Email participants
        for email in context.get('mailing_list_emails', []):
            sender = email.get('from', '')
            if sender:
                participants[sender]['roles'].add('email_participant')
                participants[sender]['activities'].append({
                    'type': 'email',
                    'timestamp': email.get('date')
                })
        
        # Convert sets to lists for JSON serialization
        result = {}
        for username, data in participants.items():
            result[username] = {
                'roles': list(data['roles']),
                'activity_count': len(data['activities']),
                'is_maintainer': data['is_maintainer'],
                'activities': data['activities']
            }
        
        return result
    
    def _extract_governance_indicators(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract governance-related indicators."""
        indicators = {
            'self_merge': False,
            'zero_reviews': False,
            'maintainer_involvement': [],
            'conflict_indicators': [],
            'transparency_indicators': [],
            'decision_making_patterns': []
        }
        
        pr = context.get('github_pr')
        if not pr:
            return indicators
        
        # Self-merge check
        author = pr.get('user', {}).get('login')
        merged_by = pr.get('merged_by', {}).get('login')
        if author and merged_by and author == merged_by:
            indicators['self_merge'] = True
        
        # Review count
        reviews = pr.get('reviews', [])
        if len(reviews) == 0:
            indicators['zero_reviews'] = True
        
        # Maintainer involvement
        maintainer_activities = []
        for participant, data in context.get('participants', {}).items():
            if data.get('is_maintainer'):
                maintainer_activities.append({
                    'username': participant,
                    'roles': data.get('roles', [])
                })
        indicators['maintainer_involvement'] = maintainer_activities
        
        # Conflict indicators (NACKs, rejections, negative language)
        conflict_keywords = ['nack', 'reject', 'oppose', 'against', 'concern', 'problem']
        for comment in pr.get('comments', []):
            body = comment.get('body', '').lower()
            if any(keyword in body for keyword in conflict_keywords):
                indicators['conflict_indicators'].append({
                    'type': 'comment',
                    'author': comment.get('user', {}).get('login'),
                    'timestamp': comment.get('created_at'),
                    'excerpt': comment.get('body', '')[:200]
                })
        
        # Transparency indicators (cross-platform discussion)
        if context.get('irc_messages') or context.get('mailing_list_emails'):
            indicators['transparency_indicators'].append({
                'type': 'cross_platform_discussion',
                'irc_messages': len(context.get('irc_messages', [])),
                'emails': len(context.get('mailing_list_emails', []))
            })
        
        # Decision making patterns
        if pr.get('merged'):
            indicators['decision_making_patterns'].append({
                'decision': 'merged',
                'merged_by': merged_by,
                'review_count': len(reviews),
                'time_to_merge': self._calculate_time_diff(
                    pr.get('created_at'), pr.get('merged_at')
                ) if pr.get('merged_at') else None
            })
        elif pr.get('state') == 'closed':
            indicators['decision_making_patterns'].append({
                'decision': 'closed_without_merge',
                'closed_at': pr.get('closed_at')
            })
        
        return indicators
    
    def _calculate_time_diff(self, start: str, end: str) -> Optional[int]:
        """Calculate time difference in hours."""
        try:
            start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
            diff = end_dt - start_dt
            return int(diff.total_seconds() / 3600)
        except:
            return None
    
    def save_context(self, context: Dict[str, Any], output_file: Path):
        """Save context to JSON file."""
        # Convert sets to lists for JSON serialization
        def convert_sets(obj):
            if isinstance(obj, set):
                return list(obj)
            elif isinstance(obj, dict):
                return {k: convert_sets(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_sets(item) for item in obj]
            return obj
        
        context_serializable = convert_sets(context)
        
        with open(output_file, 'w') as f:
            json.dump(context_serializable, f, indent=2)
        
        logger.info(f"Saved context to {output_file}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Gather all context for a specific PR for governance analysis'
    )
    parser.add_argument('pr_number', type=int, help='PR number to analyze')
    parser.add_argument(
        '--output', '-o',
        type=Path,
        default=None,
        help='Output file path (default: pr_context_{pr_number}.json)'
    )
    
    args = parser.parse_args()
    
    gatherer = PRContextGatherer()
    context = gatherer.gather_pr_context(args.pr_number)
    
    if not context.get('github_pr'):
        logger.error(f"Could not find PR #{args.pr_number}")
        sys.exit(1)
    
    # Determine output file
    if args.output:
        output_file = args.output
    else:
        output_dir = project_root / 'data' / 'pr_contexts'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"pr_context_{args.pr_number}.json"
    
    gatherer.save_context(context, output_file)
    
    # Print summary
    print(f"\n=== PR #{args.pr_number} Context Summary ===")
    print(f"Title: {context['github_pr'].get('title', 'N/A')}")
    print(f"Author: {context['github_pr'].get('user', {}).get('login', 'N/A')}")
    print(f"Status: {context['github_pr'].get('state', 'N/A')}")
    print(f"Merged: {context['github_pr'].get('merged', False)}")
    if context['github_pr'].get('merged_by'):
        print(f"Merged by: {context['github_pr']['merged_by'].get('login', 'N/A')}")
    print(f"\nData collected:")
    print(f"  - Comments: {len(context['github_pr'].get('comments', []))}")
    print(f"  - Reviews: {len(context['github_pr'].get('reviews', []))}")
    print(f"  - IRC messages: {len(context['irc_messages'])}")
    print(f"  - Mailing list emails: {len(context['mailing_list_emails'])}")
    print(f"  - Related commits: {len(context['related_commits'])}")
    print(f"  - Participants: {len(context['participants'])}")
    print(f"\nGovernance indicators:")
    if context['governance_indicators'].get('self_merge'):
        print(f"  ⚠️  Self-merge detected")
    if context['governance_indicators'].get('zero_reviews'):
        print(f"  ⚠️  Zero reviews")
    print(f"  - Maintainers involved: {len(context['governance_indicators'].get('maintainer_involvement', []))}")
    print(f"  - Conflict indicators: {len(context['governance_indicators'].get('conflict_indicators', []))}")
    print(f"\nContext saved to: {output_file}")


if __name__ == '__main__':
    main()
