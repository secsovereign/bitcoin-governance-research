#!/usr/bin/env python3
"""
Commit signing information collector.

Checks if commits in merged PRs are cryptographically signed.
"""

import sys
import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
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


class CommitSigningCollector:
    """Collector for commit signing information."""
    
    def __init__(self):
        """Initialize commit signing collector."""
        self.token = config.get('data_collection.github.token') or os.getenv('GITHUB_TOKEN')
        self.repo_owner = config.get('data_collection.github.repository.owner', 'bitcoin')
        self.repo_name = config.get('data_collection.github.repository.name', 'bitcoin')
        self.data_dir = get_data_dir() / "github"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize GitHub API client
        if self.token:
            self.github = Github(self.token)
            # Conservative rate limiting - share with other collectors
            self.rate_limiter = RateLimiter(max_calls=4000, time_window=3600)
        else:
            logger.warning("No GitHub token provided. Rate limits will be stricter.")
            self.github = Github()
            self.rate_limiter = RateLimiter(max_calls=50, time_window=3600)
        
        self.repo = self.github.get_repo(f"{self.repo_owner}/{self.repo_name}")
    
    def collect(self):
        """Collect commit signing information from merged PRs."""
        logger.info("Starting commit signing information collection")
        
        prs_file = self.data_dir / "prs_raw.jsonl"
        output_file = self.data_dir / "commit_signing.jsonl"
        
        if not prs_file.exists():
            logger.error(f"PRs file not found: {prs_file}")
            return
        
        # Read merged PRs
        merged_prs = []
        with open(prs_file, 'r') as f:
            for line in f:
                pr = json.loads(line)
                if pr.get('state') == 'closed' and pr.get('merged_at'):
                    merged_prs.append(pr)
        
        logger.info(f"Found {len(merged_prs)} merged PRs to check")
        
        signing_data = []
        checked = 0
        
        with open(output_file, 'w') as f:
            for pr in merged_prs:
                try:
                    # Check rate limit periodically
                    if checked % 50 == 0:
                        self._check_and_wait_for_rate_limit()
                    
                    self.rate_limiter.wait_if_needed()
                    
                    # Get merge commit
                    merge_commit_sha = pr.get('merge_commit_sha')
                    if not merge_commit_sha:
                        continue
                    
                    commit_data = self._check_commit_signing(merge_commit_sha, pr.get('number'))
                    
                    if commit_data:
                        signing_data.append(commit_data)
                        f.write(json.dumps(commit_data) + '\n')
                        f.flush()
                    
                    checked += 1
                    
                    if checked % 100 == 0:
                        signed_count = sum(1 for d in signing_data if d.get('is_signed', False))
                        logger.info(f"Checked {checked}/{len(merged_prs)} PRs ({signed_count} signed commits)")
                
                except Exception as e:
                    logger.warning(f"Error checking PR {pr.get('number')}: {e}")
                    continue
        
        logger.info(f"Collected signing information for {len(signing_data)} commits")
        logger.info(f"Saved to {output_file}")
        
        # Generate summary
        self._generate_summary(signing_data)
    
    def _check_commit_signing(self, commit_sha: str, pr_number: int) -> Optional[Dict[str, Any]]:
        """Check if a commit is cryptographically signed."""
        try:
            commit = self.repo.get_commit(commit_sha)
            
            commit_data = {
                'pr_number': pr_number,
                'commit_sha': commit_sha,
                'commit_url': commit.html_url,
                'author': commit.author.login if commit.author else None,
                'committer': commit.committer.login if commit.committer else None,
                'commit_date': commit.commit.author.date.isoformat() if commit.commit.author and commit.commit.author.date else None,
                'is_signed': False,
                'verification': None,
                'signer': None,
                'signature_type': None
            }
            
            # Check verification status
            if hasattr(commit, 'verification') and commit.verification:
                verification = commit.verification
                commit_data['verification'] = {
                    'verified': verification.verified if hasattr(verification, 'verified') else False,
                    'reason': verification.reason if hasattr(verification, 'reason') else None,
                    'signature': verification.signature if hasattr(verification, 'signature') else None,
                    'payload': verification.payload if hasattr(verification, 'payload') else None
                }
                
                commit_data['is_signed'] = verification.verified if hasattr(verification, 'verified') else False
                
                if commit_data['is_signed']:
                    # Try to extract signer info
                    if hasattr(verification, 'signature') and verification.signature:
                        commit_data['signature_type'] = 'gpg'  # GitHub typically uses GPG
                    
                    # Check if we can get signer from commit message or other sources
                    if commit.commit.message:
                        # Look for signed-off-by or similar
                        if 'Signed-off-by:' in commit.commit.message:
                            commit_data['signature_type'] = 'signed-off-by'
            
            return commit_data
            
        except Exception as e:
            logger.debug(f"Error checking commit {commit_sha}: {e}")
            return None
    
    def _check_and_wait_for_rate_limit(self):
        """Check GitHub API rate limit and wait if needed."""
        try:
            rate_limit = self.github.get_rate_limit()
            remaining = None
            if hasattr(rate_limit, 'remaining'):
                remaining = rate_limit.remaining
            elif hasattr(rate_limit, 'core') and hasattr(rate_limit.core, 'remaining'):
                remaining = rate_limit.core.remaining
            
            if remaining is not None:
                if remaining < 100:
                    logger.warning(f"GitHub API rate limit low: {remaining} remaining. Waiting...")
                    import time
                    time.sleep(60)
                elif remaining < 500:
                    logger.info(f"GitHub API rate limit: {remaining} remaining")
        except Exception as e:
            logger.debug(f"Could not check rate limit: {e}")
    
    def _generate_summary(self, signing_data: List[Dict[str, Any]]):
        """Generate summary of collected signing data."""
        logger.info("=== Commit Signing Collection Summary ===")
        logger.info(f"Total commits checked: {len(signing_data)}")
        
        signed_count = sum(1 for d in signing_data if d.get('is_signed', False))
        unsigned_count = len(signing_data) - signed_count
        
        logger.info(f"Signed commits: {signed_count} ({signed_count*100/len(signing_data) if signing_data else 0:.1f}%)")
        logger.info(f"Unsigned commits: {unsigned_count} ({unsigned_count*100/len(signing_data) if signing_data else 0:.1f}%)")
        
        # Count by signature type
        signature_types = {}
        for data in signing_data:
            sig_type = data.get('signature_type') or 'none'
            signature_types[sig_type] = signature_types.get(sig_type, 0) + 1
        
        if signature_types:
            logger.info("Signature types:")
            for sig_type, count in sorted(signature_types.items(), key=lambda x: x[1], reverse=True):
                logger.info(f"  {sig_type}: {count}")


def main():
    """Main entry point."""
    collector = CommitSigningCollector()
    collector.collect()
    logger.info("Commit signing collection complete")


if __name__ == '__main__':
    main()


