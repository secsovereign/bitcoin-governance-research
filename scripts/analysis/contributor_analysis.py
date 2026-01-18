#!/usr/bin/env python3
"""
Contributor Analysis - Consolidated and Definitive

Single source of truth for contributor retention metrics.

DEFINITIONS:
- Contributor: Anyone with ANY GitHub activity (PR author, commenter, reviewer, 
  issue creator, issue commenter)
- Active: Had activity within the last 365 days
- Exited: No activity in the last 365 days
- Author: Someone who authored at least 1 PR
- Participant: Someone who only commented/reviewed/created issues (never authored PR)

COHORTS (based on total activities):
- One-time: Exactly 1 activity
- Active: 2+ activities

QUALITY (for PR authors only):
- Merge rate: PRs merged / PRs authored
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict
from datetime import datetime, timezone
from dataclasses import dataclass, field

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir, get_analysis_dir

logger = setup_logger()

# Constants
INACTIVITY_THRESHOLD_DAYS = 365  # Primary threshold: 1 year
SECONDARY_THRESHOLD_DAYS = 730   # Secondary threshold: 2 years


@dataclass
class Contributor:
    """A contributor with all their activities."""
    username: str
    prs_authored: int = 0
    prs_merged: int = 0
    pr_comments: int = 0
    pr_reviews: int = 0
    issues_created: int = 0
    issue_comments: int = 0
    first_activity: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    
    @property
    def total_activities(self) -> int:
        return (self.prs_authored + self.pr_comments + self.pr_reviews + 
                self.issues_created + self.issue_comments)
    
    @property
    def is_author(self) -> bool:
        """Did they ever author a PR?"""
        return self.prs_authored > 0
    
    @property
    def merge_rate(self) -> float:
        """PR merge rate (authors only)."""
        if self.prs_authored == 0:
            return 0.0
        return self.prs_merged / self.prs_authored
    
    @property
    def is_one_time(self) -> bool:
        """Did exactly 1 activity."""
        return self.total_activities == 1
    
    def is_active(self, reference_date: datetime, threshold_days: int = INACTIVITY_THRESHOLD_DAYS) -> bool:
        """Active within threshold."""
        if not self.last_activity:
            return False
        return (reference_date - self.last_activity).days < threshold_days
    
    def tenure_days(self) -> int:
        """Days between first and last activity."""
        if not self.first_activity or not self.last_activity:
            return 0
        return (self.last_activity - self.first_activity).days


class ContributorAnalyzer:
    """Consolidated contributor retention analysis."""
    
    def __init__(self):
        self.data_dir = get_data_dir()
        self.github_dir = self.data_dir / 'github'
        self.analysis_dir = get_analysis_dir()
        self.findings_dir = self.analysis_dir / 'findings' / 'data'
        self.findings_dir.mkdir(parents=True, exist_ok=True)
        
        self.contributors: Dict[str, Contributor] = {}
        self.reference_date = datetime.now(timezone.utc)
    
    def run(self):
        """Run the analysis."""
        logger.info("=" * 70)
        logger.info("Contributor Analysis (Consolidated)")
        logger.info("=" * 70)
        
        # Load data
        self._load_prs()
        self._load_issues()
        
        # Calculate
        results = self._calculate_metrics()
        
        # Save
        self._save(results)
        self._print_summary(results)
        
        return results
    
    def _load_prs(self):
        """Load all PR data."""
        prs_file = self.github_dir / 'prs_raw.jsonl'
        if not prs_file.exists():
            prs_file = self.data_dir.parent.parent / 'data' / 'github' / 'prs_raw.jsonl'
        
        if not prs_file.exists():
            logger.warning("PRs file not found")
            return
        
        logger.info("Loading PRs...")
        count = 0
        
        with open(prs_file) as f:
            for line in f:
                try:
                    pr = json.loads(line)
                    count += 1
                    
                    # PR author
                    author = (pr.get('author') or '').lower().strip()
                    if author:
                        self._get_or_create(author)
                        self.contributors[author].prs_authored += 1
                        if pr.get('merged'):
                            self.contributors[author].prs_merged += 1
                        self._update_dates(author, pr.get('created_at'))
                    
                    # Comments
                    for c in (pr.get('comments') or []):
                        user = (c.get('author') or c.get('user', {}).get('login', '') or '').lower().strip()
                        if user:
                            self._get_or_create(user)
                            self.contributors[user].pr_comments += 1
                            self._update_dates(user, c.get('created_at') or c.get('date'))
                    
                    # Reviews
                    for r in (pr.get('reviews') or []):
                        user = (r.get('author') or r.get('user', {}).get('login', '') or '').lower().strip()
                        if user:
                            self._get_or_create(user)
                            self.contributors[user].pr_reviews += 1
                            self._update_dates(user, r.get('submitted_at') or r.get('created_at'))
                
                except Exception:
                    continue
        
        logger.info(f"Loaded {count:,} PRs")
    
    def _load_issues(self):
        """Load all issues data."""
        issues_file = self.github_dir / 'issues_raw.jsonl'
        if not issues_file.exists():
            issues_file = self.data_dir.parent.parent / 'data' / 'github' / 'issues_raw.jsonl'
        
        if not issues_file.exists():
            logger.warning("Issues file not found")
            return
        
        logger.info("Loading issues...")
        count = 0
        
        with open(issues_file) as f:
            for line in f:
                try:
                    issue = json.loads(line)
                    count += 1
                    
                    # Issue creator
                    author = (issue.get('author') or issue.get('user', {}).get('login', '') or '').lower().strip()
                    if author:
                        self._get_or_create(author)
                        self.contributors[author].issues_created += 1
                        self._update_dates(author, issue.get('created_at'))
                    
                    # Comments
                    for c in (issue.get('comments') or []):
                        user = (c.get('author') or c.get('user', {}).get('login', '') or '').lower().strip()
                        if user:
                            self._get_or_create(user)
                            self.contributors[user].issue_comments += 1
                            self._update_dates(user, c.get('created_at') or c.get('date'))
                
                except Exception:
                    continue
        
        logger.info(f"Loaded {count:,} issues")
    
    def _get_or_create(self, username: str) -> Contributor:
        """Get or create a contributor."""
        if username not in self.contributors:
            self.contributors[username] = Contributor(username=username)
        return self.contributors[username]
    
    def _update_dates(self, username: str, date_str: Optional[str]):
        """Update first/last activity dates."""
        if not date_str:
            return
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            c = self.contributors[username]
            if c.first_activity is None or dt < c.first_activity:
                c.first_activity = dt
            if c.last_activity is None or dt > c.last_activity:
                c.last_activity = dt
        except Exception:
            pass
    
    def _calculate_metrics(self) -> Dict[str, Any]:
        """Calculate all metrics."""
        all_contribs = list(self.contributors.values())
        total = len(all_contribs)
        
        if total == 0:
            return {'error': 'No contributors found'}
        
        # Counts
        authors = [c for c in all_contribs if c.is_author]
        participants = [c for c in all_contribs if not c.is_author]
        one_time = [c for c in all_contribs if c.is_one_time]
        active_contribs = [c for c in all_contribs if c.is_active(self.reference_date)]
        
        # Activity totals
        total_prs = sum(c.prs_authored for c in all_contribs)
        total_pr_comments = sum(c.pr_comments for c in all_contribs)
        total_pr_reviews = sum(c.pr_reviews for c in all_contribs)
        total_issues = sum(c.issues_created for c in all_contribs)
        total_issue_comments = sum(c.issue_comments for c in all_contribs)
        
        # Exit analysis
        active_1yr = sum(1 for c in all_contribs if c.is_active(self.reference_date, 365))
        active_2yr = sum(1 for c in all_contribs if c.is_active(self.reference_date, 730))
        
        # Author exit analysis
        author_active_1yr = sum(1 for c in authors if c.is_active(self.reference_date, 365))
        
        # Quality (authors only)
        authors_with_merges = [c for c in authors if c.prs_merged > 0]
        high_quality = [c for c in authors if c.merge_rate >= 0.5]  # 50%+ merge rate
        high_quality_active = sum(1 for c in high_quality if c.is_active(self.reference_date, 365))
        
        # Tenure analysis (for active contributors with 2+ activities)
        active_multi = [c for c in all_contribs if c.is_active(self.reference_date) and c.total_activities >= 2]
        avg_tenure_active = (sum(c.tenure_days() for c in active_multi) / len(active_multi)) if active_multi else 0
        
        # Date range
        first_activity = min((c.first_activity for c in all_contribs if c.first_activity), default=None)
        last_activity = max((c.last_activity for c in all_contribs if c.last_activity), default=None)
        
        return {
            'summary': {
                'total_contributors': total,
                'total_authors': len(authors),
                'total_participants_only': len(participants),
                'one_time_contributors': len(one_time),
                'active_contributors': len(active_contribs)
            },
            'activities': {
                'prs_authored': total_prs,
                'pr_comments': total_pr_comments,
                'pr_reviews': total_pr_reviews,
                'issues_created': total_issues,
                'issue_comments': total_issue_comments,
                'total': total_prs + total_pr_comments + total_pr_reviews + total_issues + total_issue_comments
            },
            'retention': {
                'active_1yr': active_1yr,
                'exited_1yr': total - active_1yr,
                'retention_rate_1yr': active_1yr / total,
                'exit_rate_1yr': (total - active_1yr) / total,
                'active_2yr': active_2yr,
                'exited_2yr': total - active_2yr,
                'retention_rate_2yr': active_2yr / total,
                'exit_rate_2yr': (total - active_2yr) / total
            },
            'authors': {
                'total': len(authors),
                'active_1yr': author_active_1yr,
                'exit_rate_1yr': (len(authors) - author_active_1yr) / len(authors) if authors else 0,
                'avg_merge_rate': sum(c.merge_rate for c in authors) / len(authors) if authors else 0,
                'total_prs': total_prs,
                'total_merged': sum(c.prs_merged for c in authors)
            },
            'participants_only': {
                'total': len(participants),
                'active_1yr': sum(1 for c in participants if c.is_active(self.reference_date, 365)),
                'exit_rate_1yr': (len(participants) - sum(1 for c in participants if c.is_active(self.reference_date, 365))) / len(participants) if participants else 0,
                'description': 'Contributors who never authored a PR'
            },
            'one_time': {
                'total': len(one_time),
                'percentage': len(one_time) / total,
                'active_1yr': sum(1 for c in one_time if c.is_active(self.reference_date, 365)),
                'exit_rate_1yr': (len(one_time) - sum(1 for c in one_time if c.is_active(self.reference_date, 365))) / len(one_time) if one_time else 0
            },
            'quality': {
                'high_quality_authors': len(high_quality),
                'high_quality_definition': '50%+ PR merge rate',
                'high_quality_active_1yr': high_quality_active,
                'high_quality_exit_rate_1yr': (len(high_quality) - high_quality_active) / len(high_quality) if high_quality else 0
            },
            'tenure': {
                'avg_tenure_days_active': avg_tenure_active,
                'avg_tenure_years_active': avg_tenure_active / 365 if avg_tenure_active else 0
            },
            'data_range': {
                'first_activity': first_activity.isoformat() if first_activity else None,
                'last_activity': last_activity.isoformat() if last_activity else None,
                'analysis_date': self.reference_date.isoformat()
            },
            'methodology': {
                'contributor_definition': 'Anyone with any GitHub activity (PR author/commenter/reviewer, issue creator/commenter)',
                'active_definition': f'Activity within last {INACTIVITY_THRESHOLD_DAYS} days',
                'exit_definition': f'No activity in last {INACTIVITY_THRESHOLD_DAYS} days',
                'author_definition': 'Authored at least 1 PR',
                'participant_definition': 'Never authored a PR (comments/reviews/issues only)',
                'high_quality_definition': '50%+ PR merge rate',
                'one_time_definition': 'Exactly 1 total activity'
            }
        }
    
    def _save(self, results: Dict[str, Any]):
        """Save results."""
        output_file = self.findings_dir / 'contributor_analysis.json'
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        logger.info(f"Saved to {output_file}")
    
    def _print_summary(self, results: Dict[str, Any]):
        """Print summary."""
        print()
        print("=" * 70)
        print("CONTRIBUTOR ANALYSIS RESULTS")
        print("=" * 70)
        print()
        
        s = results['summary']
        r = results['retention']
        a = results['authors']
        p = results['participants_only']
        o = results['one_time']
        q = results['quality']
        
        print(f"TOTAL CONTRIBUTORS: {s['total_contributors']:,}")
        print(f"  • Authors (created PR): {s['total_authors']:,}")
        print(f"  • Participants only: {s['total_participants_only']:,} ({s['total_participants_only']/s['total_contributors']:.1%})")
        print()
        
        print(f"EXIT RATE (1 year): {r['exit_rate_1yr']:.1%}")
        print(f"  • Exited: {r['exited_1yr']:,}")
        print(f"  • Active: {r['active_1yr']:,}")
        print()
        
        print(f"EXIT RATE (2 year): {r['exit_rate_2yr']:.1%}")
        print(f"  • Exited: {r['exited_2yr']:,}")
        print(f"  • Active: {r['active_2yr']:,}")
        print()
        
        print(f"ONE-TIME CONTRIBUTORS: {o['total']:,} ({o['percentage']:.1%})")
        print(f"  • Exit rate: {o['exit_rate_1yr']:.1%}")
        print()
        
        print(f"PR AUTHORS: {a['total']:,}")
        print(f"  • Exit rate: {a['exit_rate_1yr']:.1%}")
        print(f"  • Avg merge rate: {a['avg_merge_rate']:.1%}")
        print()
        
        print(f"PARTICIPANTS ONLY (never authored PR): {p['total']:,}")
        print(f"  • Exit rate: {p['exit_rate_1yr']:.1%}")
        print()
        
        print(f"HIGH-QUALITY AUTHORS (50%+ merge rate): {q['high_quality_authors']:,}")
        print(f"  • Exit rate: {q['high_quality_exit_rate_1yr']:.1%}")
        print()


def main():
    analyzer = ContributorAnalyzer()
    analyzer.run()


if __name__ == '__main__':
    main()

