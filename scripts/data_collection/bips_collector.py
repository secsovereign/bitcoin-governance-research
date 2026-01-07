#!/usr/bin/env python3
"""
BIPs (Bitcoin Improvement Proposals) collector.

Collects BIPs, their discussions, and status from the bitcoin/bips repository.
"""

import sys
import os
import json
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import re

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


class BIPsCollector:
    """Collector for Bitcoin Improvement Proposals."""
    
    def __init__(self):
        """Initialize BIPs collector."""
        self.token = config.get('data_collection.github.token') or os.getenv('GITHUB_TOKEN')
        self.repo_owner = 'bitcoin'
        self.repo_name = 'bips'
        self.data_dir = get_data_dir() / "bips"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize GitHub API client
        if self.token:
            self.github = Github(self.token)
            self.rate_limiter = RateLimiter(max_calls=4500, time_window=3600)  # 5000/hour with buffer
        else:
            logger.warning("No GitHub token provided. Rate limits will be stricter.")
            self.github = Github()
            self.rate_limiter = RateLimiter(max_calls=60, time_window=3600)
        
        self.repo = self.github.get_repo(f"{self.repo_owner}/{self.repo_name}")
    
    def collect(self):
        """Collect all BIPs data."""
        logger.info("Starting BIPs collection")
        
        # Collect BIP files
        self._collect_bip_files()
        
        # Collect BIP repository issues and PRs
        self._collect_bip_discussions()
        
        logger.info("BIPs collection complete")
    
    def _collect_bip_files(self):
        """Collect BIP files from repository."""
        logger.info("Collecting BIP files from repository")
        
        try:
            # Clone repository to get BIP files
            temp_dir = tempfile.mkdtemp(prefix="bitcoin_bips_")
            logger.info(f"Cloning BIPs repository to {temp_dir}")
            
            subprocess.run(
                ["git", "clone", "--depth=1", f"https://github.com/{self.repo_owner}/{self.repo_name}.git", temp_dir],
                check=True,
                capture_output=True
            )
            
            # Find all BIP files
            bip_dir = Path(temp_dir) / "bip-XXXX.mediawiki"
            if not bip_dir.exists():
                # Try alternative structure
                bip_dir = Path(temp_dir)
            
            bip_files = list(bip_dir.rglob("bip-*.mediawiki")) + list(bip_dir.rglob("bip-*.md"))
            
            logger.info(f"Found {len(bip_files)} BIP files")
            
            bips = []
            for bip_file in bip_files:
                try:
                    bip_data = self._parse_bip_file(bip_file)
                    if bip_data:
                        bips.append(bip_data)
                except Exception as e:
                    logger.warning(f"Error parsing BIP file {bip_file}: {e}")
                    continue
            
            # Save BIPs
            output_file = self.data_dir / "bips.jsonl"
            with open(output_file, 'w') as f:
                for bip in bips:
                    f.write(json.dumps(bip) + '\n')
            
            logger.info(f"Saved {len(bips)} BIPs to {output_file}")
            
            # Clean up
            shutil.rmtree(temp_dir)
            
        except Exception as e:
            logger.error(f"Error collecting BIP files: {e}")
            import traceback
            logger.debug(traceback.format_exc())
    
    def _parse_bip_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Parse a BIP file to extract metadata."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            # Extract BIP number from filename
            bip_match = re.search(r'bip-(\d+)', file_path.name, re.I)
            bip_number = int(bip_match.group(1)) if bip_match else None
            
            # Parse BIP metadata (mediawiki or markdown format)
            metadata = {
                'bip_number': bip_number,
                'filename': file_path.name,
                'content': content,
                'content_length': len(content)
            }
            
            # Extract title
            title_match = re.search(r'^Title:\s*(.+)$', content, re.M | re.I)
            if title_match:
                metadata['title'] = title_match.group(1).strip()
            
            # Extract author
            author_match = re.search(r'^Author:\s*(.+)$', content, re.M | re.I)
            if author_match:
                metadata['author'] = author_match.group(1).strip()
            
            # Extract status
            status_match = re.search(r'^Status:\s*(.+)$', content, re.M | re.I)
            if status_match:
                metadata['status'] = status_match.group(1).strip()
            
            # Extract type
            type_match = re.search(r'^Type:\s*(.+)$', content, re.M | re.I)
            if type_match:
                metadata['type'] = type_match.group(1).strip()
            
            # Extract created date
            created_match = re.search(r'^Created:\s*(.+)$', content, re.M | re.I)
            if created_match:
                metadata['created'] = created_match.group(1).strip()
            
            return metadata
            
        except Exception as e:
            logger.debug(f"Error parsing BIP file {file_path}: {e}")
            return None
    
    def _collect_bip_discussions(self):
        """Collect issues and PRs from BIPs repository."""
        logger.info("Collecting BIP repository issues and PRs")
        
        try:
            # Collect issues
            issues = []
            for issue in self.repo.get_issues(state='all'):
                self.rate_limiter.wait_if_needed()
                
                issue_data = {
                    'number': issue.number,
                    'title': issue.title,
                    'body': issue.body,
                    'state': issue.state,
                    'created_at': issue.created_at.isoformat() if issue.created_at else None,
                    'closed_at': issue.closed_at.isoformat() if issue.closed_at else None,
                    'author': issue.user.login if issue.user else None,
                    'labels': [label.name for label in issue.labels],
                    'comments_count': issue.comments,
                    'comments': []
                }
                
                # Get comments
                for comment in issue.get_comments():
                    self.rate_limiter.wait_if_needed()
                    issue_data['comments'].append({
                        'author': comment.user.login if comment.user else None,
                        'body': comment.body,
                        'created_at': comment.created_at.isoformat() if comment.created_at else None
                    })
                
                issues.append(issue_data)
                
                if len(issues) % 10 == 0:
                    logger.info(f"Collected {len(issues)} issues from BIPs repository")
            
            # Save issues
            issues_file = self.data_dir / "bips_issues.jsonl"
            with open(issues_file, 'w') as f:
                for issue in issues:
                    f.write(json.dumps(issue) + '\n')
            
            logger.info(f"Saved {len(issues)} issues to {issues_file}")
            
            # Collect PRs (similar to issues)
            prs = []
            for pr in self.repo.get_pulls(state='all'):
                self.rate_limiter.wait_if_needed()
                
                pr_data = {
                    'number': pr.number,
                    'title': pr.title,
                    'body': pr.body,
                    'state': pr.state,
                    'created_at': pr.created_at.isoformat() if pr.created_at else None,
                    'merged_at': pr.merged_at.isoformat() if pr.merged_at else None,
                    'closed_at': pr.closed_at.isoformat() if pr.closed_at else None,
                    'author': pr.user.login if pr.user else None,
                    'merged': pr.merged,
                    'mergeable': pr.mergeable,
                    'comments_count': pr.comments,
                    'review_comments_count': pr.review_comments
                }
                
                prs.append(pr_data)
                
                if len(prs) % 10 == 0:
                    logger.info(f"Collected {len(prs)} PRs from BIPs repository")
            
            # Save PRs
            prs_file = self.data_dir / "bips_prs.jsonl"
            with open(prs_file, 'w') as f:
                for pr in prs:
                    f.write(json.dumps(pr) + '\n')
            
            logger.info(f"Saved {len(prs)} PRs to {prs_file}")
            
        except Exception as e:
            logger.error(f"Error collecting BIP discussions: {e}")
            import traceback
            logger.debug(traceback.format_exc())


def main():
    """Main entry point."""
    collector = BIPsCollector()
    collector.collect()


if __name__ == '__main__':
    main()

