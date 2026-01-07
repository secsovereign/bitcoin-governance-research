#!/usr/bin/env python3
"""
GitHub commits collector for Bitcoin Core repository.

Collects commit history, including merge commits, to analyze
decision-making patterns and maintainer activity.
"""

import sys
import os
import json
import time
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


class GitHubCommitsCollector:
    """Collector for GitHub commits."""
    
    def __init__(self):
        """Initialize commits collector."""
        self.token = config.get('data_collection.github.token') or os.getenv('GITHUB_TOKEN')
        self.repo_owner = config.get('data_collection.github.repository.owner', 'bitcoin')
        self.repo_name = config.get('data_collection.github.repository.name', 'bitcoin')
        self.data_dir = get_data_dir() / "github"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize GitHub API client
        if self.token:
            self.github = Github(self.token)
            # More conservative rate limiting - share with other collectors
            # Use 80% of limit to leave room for PRs/Issues collectors
            self.rate_limiter = RateLimiter(max_calls=4000, time_window=3600)  # 4000/hour to share with other collectors
        else:
            logger.warning("No GitHub token provided. Rate limits will be stricter.")
            self.github = Github()
            self.rate_limiter = RateLimiter(max_calls=50, time_window=3600)  # Leave room for other collectors
        
        self.repo = self.github.get_repo(f"{self.repo_owner}/{self.repo_name}")
        
        # Track if we need to check rate limits
        self._check_rate_limit_every = 50  # Check GitHub API rate limit every 50 commits
    
    def collect_all_commits(self):
        """Collect all commits from the repository."""
        logger.info("Starting commits collection")
        
        commits_file = self.data_dir / "commits_raw.jsonl"
        
        # Get all commits (this will take a while for large repos)
        try:
            commits = self.repo.get_commits()
            total_commits = commits.totalCount
            
            logger.info(f"Found {total_commits} total commits")
            
            collected = 0
            with open(commits_file, 'w') as f:
                for commit in commits:
                    # Check GitHub API rate limit periodically
                    if collected % self._check_rate_limit_every == 0:
                        self._check_and_wait_for_rate_limit()
                    
                    self.rate_limiter.wait_if_needed()
                    
                    commit_data = self._extract_commit_data(commit)
                    if commit_data:
                        f.write(json.dumps(commit_data) + '\n')
                        f.flush()
                        collected += 1
                    
                    # Small delay to spread out API calls
                    if collected % 100 == 0:
                        logger.info(f"Collected {collected}/{total_commits} commits ({collected*100//total_commits}%)")
                        time.sleep(0.5)  # 500ms delay every 100 commits
                    elif collected % 10 == 0:
                        time.sleep(0.1)  # 100ms delay every 10 commits
            
            logger.info(f"Collected {collected} commits to {commits_file}")
            
        except Exception as e:
            logger.error(f"Error collecting commits: {e}")
            import traceback
            logger.debug(traceback.format_exc())
    
    def collect_commits_limited(self, limit: int):
        """Collect a limited number of commits (for testing)."""
        logger.info(f"Collecting {limit} commits (limited mode)")
        
        commits_file = self.data_dir / "commits_raw.jsonl"
        
        try:
            commits = self.repo.get_commits()
            
            collected = 0
            with open(commits_file, 'w') as f:
                for commit in commits:
                    if collected >= limit:
                        break
                    
                    # Check GitHub API rate limit periodically
                    if collected % self._check_rate_limit_every == 0:
                        self._check_and_wait_for_rate_limit()
                    
                    self.rate_limiter.wait_if_needed()
                    
                    commit_data = self._extract_commit_data(commit)
                    if commit_data:
                        f.write(json.dumps(commit_data) + '\n')
                        f.flush()
                        collected += 1
                    
                    # Small delay to spread out API calls
                    if collected % 10 == 0:
                        logger.info(f"Collected {collected}/{limit} commits")
                        time.sleep(0.1)  # 100ms delay every 10 commits
            
            logger.info(f"Collected {collected} commits to {commits_file}")
            
        except Exception as e:
            logger.error(f"Error collecting commits: {e}")
            import traceback
            logger.debug(traceback.format_exc())
    
    def _check_and_wait_for_rate_limit(self):
        """Check GitHub API rate limit and wait if needed."""
        try:
            rate_limit = self.github.get_rate_limit()
            # PyGithub API structure varies, try different access patterns
            remaining = None
            if hasattr(rate_limit, 'remaining'):
                remaining = rate_limit.remaining
            elif hasattr(rate_limit, 'core') and hasattr(rate_limit.core, 'remaining'):
                remaining = rate_limit.core.remaining
            
            if remaining is not None:
                if remaining < 100:
                    logger.warning(f"GitHub API rate limit low: {remaining} remaining. Waiting...")
                    # Wait until we have more headroom
                    time.sleep(60)  # Wait 1 minute
                elif remaining < 500:
                    logger.info(f"GitHub API rate limit: {remaining} remaining")
        except Exception as e:
            logger.debug(f"Could not check rate limit: {e}")
    
    def _extract_commit_data(self, commit) -> Optional[Dict[str, Any]]:
        """Extract data from a commit object - optimized to minimize API calls."""
        try:
            commit_sha = commit.sha
            
            # Use data from commit object directly (no extra API call)
            # Most commit data is available from the iterator
            commit_data = {
                'sha': commit_sha,
                'message': commit.commit.message if commit.commit else None,
                'author': {
                    'name': commit.commit.author.name if commit.commit and commit.commit.author else None,
                    'email': commit.commit.author.email if commit.commit and commit.commit.author else None,
                    'login': commit.author.login if commit.author else None,
                    'date': commit.commit.author.date.isoformat() if commit.commit and commit.commit.author and commit.commit.author.date else None
                },
                'committer': {
                    'name': commit.commit.committer.name if commit.commit and commit.commit.committer else None,
                    'email': commit.commit.committer.email if commit.commit and commit.commit.committer else None,
                    'login': commit.committer.login if commit.committer else None,
                    'date': commit.commit.committer.date.isoformat() if commit.commit and commit.commit.committer and commit.commit.committer.date else None
                },
                'url': commit.html_url if hasattr(commit, 'html_url') else None,
                'is_merge': len(commit.parents) > 1 if commit.parents else False,
                'parents': [p.sha for p in commit.parents] if commit.parents else []
            }
            
            # Only fetch full commit details if we really need stats/files
            # This is optional and can be skipped to save API calls
            try:
                # Only get full commit if we have rate limit headroom
                if self.rate_limiter.can_proceed():
                    self.rate_limiter.wait_if_needed()
                    full_commit = self.repo.get_commit(commit_sha)
                    commit_data['stats'] = {
                        'additions': full_commit.stats.additions if full_commit.stats else 0,
                        'deletions': full_commit.stats.deletions if full_commit.stats else 0,
                        'total': full_commit.stats.total if full_commit.stats else 0
                    }
                    commit_data['files_changed'] = len(full_commit.files) if full_commit.files else 0
                else:
                    # Skip stats if rate limit is tight
                    commit_data['stats'] = {'additions': 0, 'deletions': 0, 'total': 0}
                    commit_data['files_changed'] = 0
            except Exception as e:
                logger.debug(f"Could not get full commit details for {commit_sha}: {e}")
                commit_data['stats'] = {'additions': 0, 'deletions': 0, 'total': 0}
                commit_data['files_changed'] = 0
            
            # Extract PR number from merge commit message if present
            if commit_data['is_merge'] and commit_data['message']:
                pr_match = re.search(r'#(\d+)', commit_data['message'])
                if pr_match:
                    commit_data['merged_pr_number'] = int(pr_match.group(1))
            
            return commit_data
            
        except Exception as e:
            logger.debug(f"Error extracting commit data: {e}")
            return None


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Collect commits from bitcoin/bitcoin')
    parser.add_argument('--limit', type=int, default=None,
                       help='Limit number of commits to collect (for testing)')
    
    args = parser.parse_args()
    
    collector = GitHubCommitsCollector()
    
    logger.info("Starting GitHub commits collection")
    if args.limit:
        logger.info(f"LIMIT MODE: Collecting only {args.limit} commits (for testing)")
        collector.collect_commits_limited(args.limit)
    else:
        collector.collect_all_commits()
    
    logger.info("GitHub commits collection complete")


if __name__ == '__main__':
    import re
    main()

