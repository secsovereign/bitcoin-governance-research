#!/usr/bin/env python3
"""
Link releases to commits, PRs, and issues.

This script analyzes releases and builds a mapping of:
- Release → Commits (commits between releases)
- Release → PRs (PRs merged in this release)
- Release → Issues (issues fixed/mentioned in this release)

Uses GitHub API compare endpoint to find commits between tags,
extracts PR numbers from merge commits, and parses release notes.
"""

import sys
import os
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from collections import defaultdict

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

# Pattern to extract PR numbers from commit messages
PR_PATTERN = re.compile(r'#(\d{4,6})', re.IGNORECASE)
MERGE_PR_PATTERN = re.compile(r'Merge (?:bitcoin/bitcoin#|#)(\d{4,6})', re.IGNORECASE)


class ReleaseComponentLinker:
    """Link releases to their components (commits, PRs, issues)."""
    
    def __init__(self):
        """Initialize release component linker."""
        self.token = config.get('data_collection.github.token') or os.getenv('GITHUB_TOKEN')
        self.repo_owner = config.get('data_collection.github.repository.owner', 'bitcoin')
        self.repo_name = config.get('data_collection.github.repository.name', 'bitcoin')
        self.data_dir = get_data_dir()
        
        # Initialize GitHub API client
        if self.token:
            self.github = Github(self.token)
            self.rate_limiter = RateLimiter(max_calls=4500, time_window=3600)
        else:
            logger.warning("No GitHub token provided. Rate limits will be stricter.")
            self.github = Github()
            self.rate_limiter = RateLimiter(max_calls=60, time_window=3600)
        
        self.repo = self.github.get_repo(f"{self.repo_owner}/{self.repo_name}")
        
        # Data directories
        self.releases_dir = self.data_dir / 'releases'
        self.github_dir = self.data_dir / 'github'
        self.output_file = self.releases_dir / 'release_components.jsonl'
    
    def link_all_releases(self):
        """Link all releases to their components."""
        logger.info("Starting release component linking")
        
        # Load releases
        releases_file = self.releases_dir / 'github_releases.jsonl'
        if not releases_file.exists():
            logger.error(f"Releases file not found: {releases_file}")
            return
        
        releases = []
        with open(releases_file) as f:
            for line in f:
                try:
                    releases.append(json.loads(line))
                except:
                    continue
        
        # Sort by published date (oldest first for proper comparison)
        releases.sort(key=lambda x: x.get('published_at', '') or x.get('created_at', ''))
        
        logger.info(f"Found {len(releases)} releases to process")
        
        # Process each release
        linked_releases = []
        previous_tag = None
        
        for i, release in enumerate(releases):
            tag = release.get('tag_name')
            if not tag:
                continue
            
            logger.info(f"Processing release {i+1}/{len(releases)}: {tag}")
            
            components = self._link_release_components(release, previous_tag)
            if components:
                linked_release = {
                    'tag_name': tag,
                    'name': release.get('name'),
                    'published_at': release.get('published_at'),
                    'created_at': release.get('created_at'),
                    'url': release.get('url'),
                    **components
                }
                linked_releases.append(linked_release)
            
            previous_tag = tag
        
        # Save results
        self._save_linked_releases(linked_releases)
        
        logger.info(f"Linked {len(linked_releases)} releases to their components")
    
    def _link_release_components(self, release: Dict[str, Any], previous_tag: Optional[str]) -> Dict[str, Any]:
        """Link a single release to its components.
        
        Args:
            release: Release data
            previous_tag: Previous release tag (for comparison)
            
        Returns:
            Dictionary with commits, PRs, and issues
        """
        tag = release.get('tag_name')
        if not tag:
            return {}
        
        components = {
            'commits': [],
            'prs': [],
            'issues': [],
            'commit_count': 0,
            'pr_count': 0,
            'issue_count': 0
        }
        
        try:
            # Get commits between previous tag and this tag
            if previous_tag:
                # Compare previous tag..current tag
                try:
                    self.rate_limiter.wait_if_needed()
                    comparison = self.repo.compare(previous_tag, tag)
                    commits = comparison.commits
                    
                    components['commit_count'] = comparison.total_commits
                    components['commits'] = [c.sha for c in commits[:1000]]  # Limit to first 1000
                    
                    # Extract PR numbers from merge commits
                    pr_numbers = set()
                    for commit in commits[:1000]:  # Limit to avoid rate limits
                        if len(commit.parents) > 1:  # Merge commit
                            message = commit.commit.message if commit.commit else ''
                            if message:
                                # Try merge PR pattern first
                                merge_match = MERGE_PR_PATTERN.search(message)
                                if merge_match:
                                    pr_numbers.add(int(merge_match.group(1)))
                                else:
                                    # Fallback: any PR mention
                                    pr_matches = PR_PATTERN.findall(message)
                                    for pr_num in pr_matches:
                                        try:
                                            pr_numbers.add(int(pr_num))
                                        except:
                                            pass
                    
                    components['prs'] = sorted(list(pr_numbers))
                    components['pr_count'] = len(pr_numbers)
                    
                except Exception as e:
                    logger.warning(f"Could not compare {previous_tag}..{tag}: {e}")
            else:
                # First release - get commits from tag (may be expensive)
                logger.info(f"First release {tag}, skipping commit comparison (would be expensive)")
            
            # Extract PRs and issues from release notes
            body = release.get('body', '')
            if body:
                # Extract PR numbers from release notes
                pr_mentions = set(PR_PATTERN.findall(body))
                for pr_num in pr_mentions:
                    try:
                        pr_num_int = int(pr_num)
                        if pr_num_int not in components['prs']:
                            components['prs'].append(pr_num_int)
                    except:
                        pass
                
                components['pr_count'] = len(components['prs'])
                components['prs'] = sorted(components['prs'])
                
                # Extract issue numbers (similar pattern)
                # Issues are typically mentioned as "Fixes #123" or "Closes #123"
                issue_pattern = re.compile(r'(?:fixes?|closes?|resolves?)\s*#(\d{4,6})', re.IGNORECASE)
                issue_mentions = set(issue_pattern.findall(body))
                for issue_num in issue_mentions:
                    try:
                        components['issues'].append(int(issue_num))
                    except:
                        pass
                
                components['issue_count'] = len(components['issues'])
                components['issues'] = sorted(components['issues'])
        
        except Exception as e:
            logger.error(f"Error linking components for {tag}: {e}")
            import traceback
            logger.debug(traceback.format_exc())
        
        return components
    
    def _save_linked_releases(self, linked_releases: List[Dict[str, Any]]):
        """Save linked releases to JSONL file."""
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.output_file, 'w') as f:
            for release in linked_releases:
                f.write(json.dumps(release) + '\n')
        
        logger.info(f"Saved {len(linked_releases)} linked releases to {self.output_file}")
    
    def enrich_with_pr_data(self):
        """Enrich release components with PR data from our collection."""
        logger.info("Enriching release components with PR data")
        
        if not self.output_file.exists():
            logger.error(f"Release components file not found: {self.output_file}")
            return
        
        # Load linked releases
        linked_releases = []
        with open(self.output_file) as f:
            for line in f:
                try:
                    linked_releases.append(json.loads(line))
                except:
                    continue
        
        # Load PR data
        prs_file = self.github_dir / 'prs_raw.jsonl'
        if not prs_file.exists():
            logger.warning("PR data file not found, skipping enrichment")
            return
        
        prs_by_number = {}
        with open(prs_file) as f:
            for line in f:
                try:
                    pr = json.loads(line)
                    prs_by_number[pr.get('number')] = pr
                except:
                    continue
        
        logger.info(f"Loaded {len(prs_by_number)} PRs")
        
        # Enrich releases with PR metadata
        enriched_releases = []
        for release in linked_releases:
            enriched = release.copy()
            pr_numbers = release.get('prs', [])
            
            # Add PR metadata
            pr_details = []
            for pr_num in pr_numbers[:100]:  # Limit to avoid huge files
                if pr_num in prs_by_number:
                    pr = prs_by_number[pr_num]
                    pr_details.append({
                        'number': pr_num,
                        'title': pr.get('title', '')[:100],
                        'author': pr.get('user', {}).get('login') if pr.get('user') else None,
                        'merged_at': pr.get('merged_at'),
                        'merged_by': pr.get('merged_by', {}).get('login') if pr.get('merged_by') else None,
                    })
            
            enriched['pr_details'] = pr_details
            enriched_releases.append(enriched)
        
        # Save enriched version
        enriched_file = self.releases_dir / 'release_components_enriched.jsonl'
        with open(enriched_file, 'w') as f:
            for release in enriched_releases:
                f.write(json.dumps(release) + '\n')
        
        logger.info(f"Saved enriched release components to {enriched_file}")


def main():
    """Main entry point."""
    import argparse
    import os
    
    parser = argparse.ArgumentParser(
        description='Link releases to commits, PRs, and issues'
    )
    parser.add_argument(
        '--enrich',
        action='store_true',
        help='Enrich with PR data from collection'
    )
    
    args = parser.parse_args()
    
    linker = ReleaseComponentLinker()
    
    if args.enrich:
        linker.enrich_with_pr_data()
    else:
        linker.link_all_releases()
        # Also enrich by default
        linker.enrich_with_pr_data()
    
    logger.info("Release component linking complete")


if __name__ == '__main__':
    import os
    main()
