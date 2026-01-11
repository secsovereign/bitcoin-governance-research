#!/usr/bin/env python3
"""
GitHub data collector for Bitcoin Core repository.

Collects all Pull Requests, issues, comments, and reviews from the
bitcoin/bitcoin repository.
"""

import sys
import os
import json
import time
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config import config
from src.utils.logger import setup_logger
from src.utils.rate_limiter import RateLimiter
from src.utils.paths import get_data_dir

try:
    from github import Github
except ImportError:
    print("Error: PyGithub package not installed.")
    print("Run: pip install PyGithub")
    sys.exit(1)


logger = setup_logger()


class GitHubCollector:
    """Collector for GitHub data."""
    
    def __init__(self):
        """Initialize GitHub collector."""
        self.token = config.get('data_collection.github.token') or os.getenv('GITHUB_TOKEN')
        self.repo_owner = config.get('data_collection.github.repository.owner', 'bitcoin')
        self.repo_name = config.get('data_collection.github.repository.name', 'bitcoin')
        self.batch_size = config.get('data_collection.github.batch_size', 100)
        
        # Initialize GitHub API client
        if self.token:
            self.github = Github(self.token)
            
            # Get actual rate limit from GitHub API (supports Enterprise Cloud with 15,000/hour)
            try:
                rate_limit = self.github.get_rate_limit()
                if hasattr(rate_limit, 'core') and hasattr(rate_limit.core, 'limit'):
                    actual_limit = rate_limit.core.limit
                elif hasattr(rate_limit, 'limit'):
                    actual_limit = rate_limit.limit
                else:
                    actual_limit = 5000  # Default fallback
                logger.info(f"Detected GitHub API rate limit: {actual_limit:,} requests/hour")
            except Exception as e:
                logger.warning(f"Could not detect rate limit, using default 5,000/hour: {e}")
                actual_limit = 5000
            
            # Use 98% of actual limit for maximum speed (safe buffer of 2%)
            buffer = config.get('data_collection.github.rate_limit_buffer', 0.98)
            max_calls = int(buffer * actual_limit)
            self.rate_limiter = RateLimiter(
                max_calls=max_calls,
                time_window=3600
            )
            logger.info(f"Rate limiter configured: {max_calls:,} requests/hour ({int(buffer*100)}% of {actual_limit:,})")
        else:
            self.github = Github()
            self.rate_limiter = RateLimiter(max_calls=60, time_window=3600)  # Unauthenticated limit
        
        self.repo = self.github.get_repo(f"{self.repo_owner}/{self.repo_name}")
        
        # Output paths
        data_dir = get_data_dir()
        self.output_dir = data_dir / 'github'
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.prs_file = self.output_dir / 'prs_raw.jsonl'
        self.issues_file = self.output_dir / 'issues_raw.jsonl'
        
        # Track rate limit checks (less frequent = faster, but still safe)
        self._check_rate_limit_every = 100  # Check GitHub API rate limit every 100 PRs (was 50)
    
    def _check_and_wait_for_rate_limit(self):
        """Check GitHub API rate limit and wait if needed."""
        try:
            rate_limit = self.github.get_rate_limit()
            remaining = None
            reset_time = None
            
            # PyGithub API structure varies by version
            if hasattr(rate_limit, 'core') and hasattr(rate_limit.core, 'remaining'):
                remaining = rate_limit.core.remaining
                if hasattr(rate_limit.core, 'reset'):
                    reset_time = rate_limit.core.reset
            elif hasattr(rate_limit, 'remaining'):
                remaining = rate_limit.remaining
                if hasattr(rate_limit, 'reset'):
                    reset_time = rate_limit.reset
            
            if remaining is not None:
                if remaining < 50:  # More aggressive threshold (was 100) - wait only when very low
                    logger.warning(f"GitHub API rate limit very low: {remaining} remaining")
                    if reset_time:
                        wait_seconds = max(30, reset_time - int(time.time()) + 5)  # Reduced buffer (was 10s, now 5s)
                        logger.info(f"Waiting {wait_seconds}s until rate limit resets...")
                        time.sleep(wait_seconds)
                    else:
                        time.sleep(30)  # Reduced fallback (was 60s)
                elif remaining < 250:  # More aggressive threshold (was 500)
                    logger.info(f"GitHub API rate limit: {remaining} remaining")
        except Exception as e:
            logger.debug(f"Could not check rate limit: {e}")
    
    def collect_all_prs(self, skip_existing: bool = True):
        """Collect all pull requests from the repository.
        
        Args:
            skip_existing: If True, skip PRs that already exist. If False, collect all PRs.
        """
        logger.info(f"Starting PR collection from {self.repo_owner}/{self.repo_name}")
        
        existing_pr_numbers = set()
        
        # ALWAYS load existing PR numbers from backups first (CRITICAL - this is where we saved the new PRs)
        data_dir = get_data_dir()
        backup_dir = data_dir.parent / 'backups' / 'safe'
        if backup_dir.exists():
            backup_files = list(backup_dir.glob('prs_raw_*.jsonl'))
            if backup_files:
                logger.info(f"Loading existing PRs from {len(backup_files)} backup file(s)...")
                for backup_file in backup_files:
                    logger.info(f"  Loading from {backup_file.name}...")
                    with open(backup_file, 'r') as f:
                        for line in f:
                            try:
                                existing_pr = json.loads(line)
                                if existing_pr.get('number'):
                                    existing_pr_numbers.add(existing_pr['number'])
                            except:
                                continue
                logger.info(f"Loaded {len(existing_pr_numbers)} existing PR numbers from backups")
        
        if skip_existing:
            # Also check raw file
            if self.prs_file.exists():
                logger.info(f"Found existing PR file with {sum(1 for _ in open(self.prs_file))} entries, resuming...")
                with open(self.prs_file, 'r') as f:
                    for line in f:
                        try:
                            existing_pr = json.loads(line)
                            if existing_pr.get('number'):
                                existing_pr_numbers.add(existing_pr['number'])
                        except:
                            continue
            
            # Also check processed files (in case raw file was lost/overwritten)
            processed_dir = self.output_dir.parent / 'processed'
            processed_prs_file = processed_dir / 'cleaned_prs.jsonl'
            if processed_prs_file.exists():
                logger.info(f"Also checking processed PR file for existing PRs...")
                with open(processed_prs_file, 'r') as f:
                    for line in f:
                        try:
                            existing_pr = json.loads(line)
                            if existing_pr.get('number'):
                                existing_pr_numbers.add(existing_pr['number'])
                        except:
                            continue
        
        if existing_pr_numbers:
            logger.info(f"Found {len(existing_pr_numbers)} existing PRs, will skip duplicates and collect missing ones")
        else:
            logger.info("No existing PRs found, collecting all PRs")
        
        # Create backup of existing file before resuming (CRITICAL - protect current data)
        if self.prs_file.exists() and existing_pr_numbers:
            backup_dir = data_dir.parent / 'backups' / 'safe'
            backup_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = backup_dir / f'prs_raw_RESUME_BACKUP_{timestamp}.jsonl'
            
            # Count lines for logging
            line_count = sum(1 for _ in open(self.prs_file))
            file_size = self.prs_file.stat().st_size / (1024 * 1024)  # MB
            
            logger.info(f"Creating backup of existing PR file before resuming...")
            logger.info(f"  Current file: {line_count:,} PRs ({file_size:.1f} MB)")
            logger.info(f"  Backup location: {backup_file.name}")
            
            shutil.copy2(self.prs_file, backup_file)
            logger.info(f"✅ Backup created successfully: {backup_file}")
            logger.info(f"   You can safely resume collection now - your data is protected")
        
        # Start with most recent PRs and work backwards
        prs = self.repo.get_pulls(state='all', sort='created', direction='desc')
        total_count = prs.totalCount
        logger.info(f"Found {total_count} total PRs, starting with most recent and working backwards")
        
        collected = 0
        skipped = 0
        errors = 0
        max_retries = 3
        consecutive_existing = 0  # Track consecutive existing PRs to stop early
        
        with open(self.prs_file, 'a') as f:  # Append mode to resume
            for pr in prs:
                # Skip PRs we already have
                if pr.number in existing_pr_numbers:
                    skipped += 1
                    consecutive_existing += 1
                    
                    # If we've hit 100 consecutive existing PRs, we've likely reached the boundary
                    # Continue a bit more to catch any gaps, then stop
                    if consecutive_existing >= 100 and skipped > 1000:
                        logger.info(f"Hit {consecutive_existing} consecutive existing PRs. Likely reached existing data boundary.")
                        logger.info(f"Stopping collection - found {collected} new PRs, skipped {skipped} existing")
                        break
                    
                    if skipped % 1000 == 0:
                        logger.info(f"Skipped {skipped} already-collected PRs (working backwards)...")
                    continue
                
                # Reset counter when we find a new PR
                consecutive_existing = 0
                
                # Check GitHub API rate limit periodically
                if collected % self._check_rate_limit_every == 0:
                    self._check_and_wait_for_rate_limit()
                
                # Use our rate limiter
                self.rate_limiter.wait_if_needed()
                
                # Extract PR data with retry logic
                pr_data = None
                for attempt in range(max_retries):
                    try:
                        pr_data = self._extract_pr_data(pr)
                        break
                    except Exception as e:
                        error_msg = str(e).lower()
                        if '403' in error_msg or 'rate limit' in error_msg or 'forbidden' in error_msg:
                            logger.warning(f"Rate limited on PR {pr.number}, attempt {attempt + 1}/{max_retries}")
                            if attempt < max_retries - 1:
                                # Wait longer on each retry
                                wait_time = (attempt + 1) * 60  # 1min, 2min, 3min
                                logger.info(f"Waiting {wait_time}s before retry...")
                                time.sleep(wait_time)
                                self._check_and_wait_for_rate_limit()
                            else:
                                logger.error(f"Failed to collect PR {pr.number} after {max_retries} attempts: {e}")
                                errors += 1
                        else:
                            logger.error(f"Error extracting PR {pr.number}: {e}")
                            errors += 1
                            break
                
                if pr_data:
                    f.write(json.dumps(pr_data) + '\n')
                    f.flush()
                    collected += 1
                    if collected % 100 == 0:
                        logger.info(f"Collected {collected} new PRs, skipped {skipped} existing, {errors} errors ({collected+skipped}/{total_count} total, {(collected+skipped)/total_count*100:.1f}%)")
        
        logger.info(f"PR collection complete: {collected} new PRs collected, {skipped} skipped (already collected), {errors} errors")
    
    def collect_prs_limited(self, limit: int):
        """Collect a limited number of PRs for testing."""
        logger.info(f"Starting LIMITED PR collection ({limit} PRs) from {self.repo_owner}/{self.repo_name}")
        
        prs = self.repo.get_pulls(state='all', sort='created', direction='desc')  # Most recent first
        total_count = prs.totalCount
        logger.info(f"Found {total_count} total PRs, collecting {limit} most recent")
        
        collected = 0
        with open(self.prs_file, 'w') as f:
            for pr in prs[:limit]:
                self.rate_limiter.wait_if_needed()
                
                pr_data = self._extract_pr_data(pr)
                f.write(json.dumps(pr_data) + '\n')
                f.flush()
                
                collected += 1
                if collected % 10 == 0:
                    logger.info(f"Collected {collected}/{limit} PRs")
        
        logger.info(f"Limited PR collection complete: {collected} PRs collected")
    
    def _extract_pr_data(self, pr) -> Dict[str, Any]:
        """Extract all relevant data from a PR object."""
        try:
            # Basic PR data
            pr_data = {
                'number': pr.number,
                'title': pr.title,
                'body': pr.body,
                'state': pr.state,
                'created_at': pr.created_at.isoformat() if pr.created_at else None,
                'updated_at': pr.updated_at.isoformat() if pr.updated_at else None,
                'closed_at': pr.closed_at.isoformat() if pr.closed_at else None,
                'merged_at': pr.merged_at.isoformat() if pr.merged_at else None,
                'author': pr.user.login if pr.user else None,
                'author_id': pr.user.id if pr.user else None,
                'draft': pr.draft,
                'mergeable': pr.mergeable,
                'merged': pr.merged,
                'mergeable_state': pr.mergeable_state,
                'labels': [label.name for label in pr.labels],
                'milestone': pr.milestone.title if pr.milestone else None,
                'merged_by': pr.merged_by.login if pr.merged_by else None,
                'merged_by_id': pr.merged_by.id if pr.merged_by else None,
            }
            
            # Comments
            self.rate_limiter.wait_if_needed()
            comments = pr.get_issue_comments()
            pr_data['comments'] = [
                {
                    'body': comment.body,
                    'author': comment.user.login if comment.user else None,
                    'created_at': comment.created_at.isoformat() if comment.created_at else None,
                }
                for comment in comments
            ]
            
            # Reviews
            self.rate_limiter.wait_if_needed()
            reviews = pr.get_reviews()
            pr_data['reviews'] = []
            for review in reviews:
                review_data = {
                    'state': review.state,
                    'body': review.body,
                    'author': review.user.login if review.user else None,
                }
                # PyGithub API: reviews use submitted_at, not created_at
                if hasattr(review, 'submitted_at') and review.submitted_at:
                    review_data['submitted_at'] = review.submitted_at.isoformat()
                elif hasattr(review, 'created_at') and review.created_at:
                    review_data['created_at'] = review.created_at.isoformat()
                pr_data['reviews'].append(review_data)
            
            # Review comments
            self.rate_limiter.wait_if_needed()
            review_comments = pr.get_review_comments()
            pr_data['review_comments'] = [
                {
                    'body': comment.body,
                    'author': comment.user.login if comment.user else None,
                    'created_at': comment.created_at.isoformat() if comment.created_at else None,
                    'path': comment.path,
                    'line': comment.line,
                }
                for comment in review_comments
            ]
            
            # Files changed
            self.rate_limiter.wait_if_needed()
            files = pr.get_files()
            pr_data['files'] = [
                {
                    'filename': file.filename,
                    'additions': file.additions,
                    'deletions': file.deletions,
                    'changes': file.changes,
                    'status': file.status,
                }
                for file in files
            ]
            
            # Calculate derived fields
            if pr_data['created_at'] and pr_data['merged_at']:
                created = datetime.fromisoformat(pr_data['created_at'].replace('Z', '+00:00'))
                merged = datetime.fromisoformat(pr_data['merged_at'].replace('Z', '+00:00'))
                pr_data['time_to_merge_days'] = (merged - created).days
            elif pr_data['created_at'] and pr_data['closed_at']:
                created = datetime.fromisoformat(pr_data['created_at'].replace('Z', '+00:00'))
                closed = datetime.fromisoformat(pr_data['closed_at'].replace('Z', '+00:00'))
                pr_data['time_to_close_days'] = (closed - created).days
            
            pr_data['total_comments'] = len(pr_data['comments'])
            pr_data['total_reviews'] = len(pr_data['reviews'])
            pr_data['total_files_changed'] = len(pr_data['files'])
            pr_data['total_additions'] = sum(f['additions'] for f in pr_data['files'])
            pr_data['total_deletions'] = sum(f['deletions'] for f in pr_data['files'])
            
            return pr_data
            
        except Exception as e:
            logger.error(f"Error extracting PR {pr.number}: {e}")
            return {
                'number': pr.number,
                'error': str(e)
            }
    
    def collect_all_issues(self, skip_existing: bool = True):
        """Collect all issues from the repository.
        
        Args:
            skip_existing: If True, skip issues that already exist. If False, collect all issues.
        """
        logger.info(f"Starting issue collection from {self.repo_owner}/{self.repo_name}")
        
        existing_issue_numbers = set()
        
        # ALWAYS load existing issue numbers from backups first (CRITICAL - this is where we saved the new issues)
        data_dir = get_data_dir()
        backup_dir = data_dir.parent / 'backups' / 'safe'
        if backup_dir.exists():
            backup_files = list(backup_dir.glob('issues_raw_*.jsonl'))
            if backup_files:
                logger.info(f"Loading existing issues from {len(backup_files)} backup file(s)...")
                for backup_file in backup_files:
                    logger.info(f"  Loading from {backup_file.name}...")
                    with open(backup_file, 'r') as f:
                        for line in f:
                            try:
                                existing_issue = json.loads(line)
                                if existing_issue.get('number'):
                                    existing_issue_numbers.add(existing_issue['number'])
                            except:
                                continue
                logger.info(f"Loaded {len(existing_issue_numbers)} existing issue numbers from backups")
        
        if skip_existing:
            # Also check raw file
            if self.issues_file.exists():
                logger.info(f"Found existing issue file with {sum(1 for _ in open(self.issues_file))} entries, resuming...")
                with open(self.issues_file, 'r') as f:
                    for line in f:
                        try:
                            existing_issue = json.loads(line)
                            if existing_issue.get('number'):
                                existing_issue_numbers.add(existing_issue['number'])
                        except:
                            continue
            
            # Also check processed files (in case raw file was lost/overwritten)
            processed_dir = self.output_dir.parent / 'processed'
            processed_issues_file = processed_dir / 'cleaned_issues.jsonl'
            if processed_issues_file.exists():
                logger.info(f"Also checking processed issue file for existing issues...")
                with open(processed_issues_file, 'r') as f:
                    for line in f:
                        try:
                            existing_issue = json.loads(line)
                            if existing_issue.get('number'):
                                existing_issue_numbers.add(existing_issue['number'])
                        except:
                            continue
        
        if existing_issue_numbers:
            logger.info(f"Found {len(existing_issue_numbers)} existing issues, will skip duplicates and collect missing ones")
        else:
            logger.info("No existing issues found, collecting all issues")
        
        issues = self.repo.get_issues(state='all', sort='created', direction='asc')
        total_count = issues.totalCount
        logger.info(f"Found {total_count} total issues")
        
        collected = 0
        skipped = 0
        errors = 0
        max_retries = 3
        
        # Create backup of existing file before appending (if file exists and has data)
        if self.issues_file.exists() and existing_issue_numbers:
            backup_dir = data_dir.parent / 'backups' / 'safe'
            backup_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = backup_dir / f'issues_raw_{timestamp}.jsonl'
            logger.info(f"Creating backup of existing issues file to {backup_file.name}...")
            shutil.copy2(self.issues_file, backup_file)
            logger.info(f"Backup created: {backup_file}")
        
        with open(self.issues_file, 'a') as f:  # Append mode to resume
            for issue in issues:
                # Skip PRs (they're tracked separately)
                if issue.pull_request:
                    continue
                
                # Skip issues we already have, but continue collecting (don't stop - we need to find gaps)
                if issue.number in existing_issue_numbers:
                    skipped += 1
                    if skipped % 1000 == 0:
                        logger.info(f"Skipped {skipped} already-collected issues...")
                    continue
                
                # Check GitHub API rate limit periodically
                if collected % self._check_rate_limit_every == 0:
                    self._check_and_wait_for_rate_limit()
                
                # Use our rate limiter
                self.rate_limiter.wait_if_needed()
                
                # Extract issue data with retry logic
                issue_data = None
                for attempt in range(max_retries):
                    try:
                        issue_data = self._extract_issue_data(issue)
                        break
                    except Exception as e:
                        error_msg = str(e).lower()
                        if '403' in error_msg or 'rate limit' in error_msg or 'forbidden' in error_msg:
                            logger.warning(f"Rate limited on issue {issue.number}, attempt {attempt + 1}/{max_retries}")
                            if attempt < max_retries - 1:
                                # Wait longer on each retry
                                wait_time = (attempt + 1) * 60  # 1min, 2min, 3min
                                logger.info(f"Waiting {wait_time}s before retry...")
                                time.sleep(wait_time)
                                self._check_and_wait_for_rate_limit()
                            else:
                                logger.error(f"Failed to collect issue {issue.number} after {max_retries} attempts: {e}")
                                errors += 1
                        else:
                            logger.error(f"Error extracting issue {issue.number}: {e}")
                            errors += 1
                            break
                
                if issue_data:
                    f.write(json.dumps(issue_data) + '\n')
                    f.flush()
                    collected += 1
                    if collected % 100 == 0:
                        logger.info(f"Collected {collected} new issues, skipped {skipped} existing, {errors} errors ({collected+skipped}/{total_count} total, {(collected+skipped)/total_count*100:.1f}%)")
        
        logger.info(f"Issue collection complete: {collected} new issues collected, {skipped} skipped (already collected), {errors} errors")
    
    def collect_issues_limited(self, limit: int):
        """Collect a limited number of issues for testing."""
        logger.info(f"Starting LIMITED issue collection ({limit} issues) from {self.repo_owner}/{self.repo_name}")
        
        # Create backup of existing file before overwriting (if it exists)
        if self.issues_file.exists():
            data_dir = get_data_dir()
            backup_dir = data_dir.parent / 'backups' / 'safe'
            backup_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = backup_dir / f'issues_raw_LIMITED_BACKUP_{timestamp}.jsonl'
            logger.warning(f"LIMITED MODE: Creating backup of existing issues file to {backup_file.name}...")
            shutil.copy2(self.issues_file, backup_file)
            logger.info(f"Backup created: {backup_file}")
        
        issues = self.repo.get_issues(state='all', sort='created', direction='desc')  # Most recent first
        total_count = issues.totalCount
        logger.info(f"Found {total_count} total issues, collecting {limit} most recent")
        
        collected = 0
        with open(self.issues_file, 'w') as f:  # Write mode for limited collection (testing only)
            for issue in issues:
                # Skip PRs (they're tracked separately)
                if issue.pull_request:
                    continue
                
                if collected >= limit:
                    break
                
                self.rate_limiter.wait_if_needed()
                
                issue_data = self._extract_issue_data(issue)
                f.write(json.dumps(issue_data) + '\n')
                f.flush()
                
                collected += 1
                if collected % 10 == 0:
                    logger.info(f"Collected {collected}/{limit} issues")
        
        logger.info(f"Limited issue collection complete: {collected} issues collected")
    
    def _extract_issue_data(self, issue) -> Dict[str, Any]:
        """Extract all relevant data from an issue object."""
        try:
            issue_data = {
                'number': issue.number,
                'title': issue.title,
                'body': issue.body,
                'state': issue.state,
                'created_at': issue.created_at.isoformat() if issue.created_at else None,
                'updated_at': issue.updated_at.isoformat() if issue.updated_at else None,
                'closed_at': issue.closed_at.isoformat() if issue.closed_at else None,
                'author': issue.user.login if issue.user else None,
                'labels': [label.name for label in issue.labels],
                'milestone': issue.milestone.title if issue.milestone else None,
            }
            
            # Comments
            self.rate_limiter.wait_if_needed()
            comments = issue.get_comments()
            issue_data['comments'] = [
                {
                    'body': comment.body,
                    'author': comment.user.login if comment.user else None,
                    'created_at': comment.created_at.isoformat() if comment.created_at else None,
                }
                for comment in comments
            ]
            
            issue_data['total_comments'] = len(issue_data['comments'])
            
            return issue_data
            
        except Exception as e:
            logger.error(f"Error extracting issue {issue.number}: {e}")
            return {
                'number': issue.number,
                'error': str(e)
            }


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Collect GitHub data from bitcoin/bitcoin')
    parser.add_argument('--limit', type=int, default=None,
                       help='Limit number of PRs/issues to collect (for testing)')
    parser.add_argument('--prs-only', action='store_true',
                       help='Only collect PRs, skip issues')
    parser.add_argument('--issues-only', action='store_true',
                       help='Only collect issues, skip PRs')
    
    args = parser.parse_args()
    
    collector = GitHubCollector()
    
    logger.info("Starting GitHub data collection")
    if args.limit:
        logger.info(f"LIMIT MODE: Collecting only {args.limit} items (for testing)")
    
    # Collect PRs
    if not args.issues_only:
        if args.limit:
            collector.collect_prs_limited(args.limit)
        else:
            collector.collect_all_prs()
    
    # Collect issues
    if not args.prs_only:
        if args.limit:
            collector.collect_issues_limited(args.limit)
        else:
            collector.collect_all_issues()
    
    logger.info("GitHub data collection complete")


if __name__ == '__main__':
    import os
    main()

