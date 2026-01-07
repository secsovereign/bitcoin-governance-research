#!/usr/bin/env python3
"""
Backfill merged_by data for existing PRs.

This script updates existing PR data with merged_by information
without re-collecting all PR data.
"""

import json
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional
from github import Github
from github.RateLimiter import RateLimiter

class MergedByBackfiller:
    """Backfill merged_by data for existing PRs."""
    
    def __init__(self, token: Optional[str] = None):
        """Initialize backfiller."""
        self.token = token or self._get_token()
        if not self.token:
            raise ValueError("GitHub token required. Set GITHUB_TOKEN environment variable.")
        
        self.github = Github(self.token)
        self.rate_limiter = RateLimiter(max_calls=4500, time_window=3600)
        self.repo = self.github.get_repo("bitcoin/bitcoin")
    
    def _get_token(self) -> Optional[str]:
        """Get GitHub token from environment or config."""
        import os
        return os.getenv('GITHUB_TOKEN')
    
    def backfill_pr(self, pr_number: int) -> Optional[Dict[str, Any]]:
        """Get merged_by data for a single PR."""
        try:
            self.rate_limiter.wait_if_needed()
            pr = self.repo.get_pull(pr_number)
            
            merged_by_data = {
                'merged_by': pr.merged_by.login if pr.merged_by else None,
                'merged_by_id': pr.merged_by.id if pr.merged_by else None,
            }
            
            return merged_by_data
        except Exception as e:
            print(f"Error getting PR {pr_number}: {e}")
            return None
    
    def backfill_file(self, input_file: Path, output_file: Path, merged_only: bool = True):
        """Backfill merged_by data for PRs in a file."""
        print("="*80)
        print("BACKFILLING merged_by DATA")
        print("="*80)
        print()
        
        # Load existing PRs
        prs = []
        print(f"Loading PRs from {input_file}...")
        with open(input_file) as f:
            for line in f:
                if line.strip():
                    prs.append(json.loads(line))
        
        print(f"Loaded {len(prs):,} PRs")
        
        # Filter to merged PRs if requested
        if merged_only:
            prs = [p for p in prs if p.get('merged', False)]
            print(f"Filtered to {len(prs):,} merged PRs")
        
        print()
        
        # Backfill data
        updated_count = 0
        error_count = 0
        
        for i, pr in enumerate(prs):
            pr_number = pr.get('number')
            if not pr_number:
                continue
            
            # Skip if already has merged_by
            if pr.get('merged_by'):
                continue
            
            # Get merged_by data
            merged_by_data = self.backfill_pr(pr_number)
            
            if merged_by_data:
                pr.update(merged_by_data)
                updated_count += 1
            else:
                error_count += 1
            
            if (i + 1) % 10 == 0:
                print(f"Processed {i+1}/{len(prs)} PRs ({updated_count} updated, {error_count} errors)")
        
        print()
        print(f"Backfill complete: {updated_count} updated, {error_count} errors")
        print()
        
        # Save updated PRs
        print(f"Saving to {output_file}...")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            for pr in prs:
                f.write(json.dumps(pr) + '\n')
        
        print(f"Saved {len(prs):,} PRs to {output_file}")
    
    def backfill_merged_maintainer_prs(self, input_file: Path, output_file: Path):
        """Backfill only merged maintainer PRs (priority)."""
        maintainers = {
            'laanwj', 'sipa', 'maflcko', 'fanquake', 'hebasto', 'jnewbery',
            'ryanofsky', 'achow101', 'theuni', 'jonasschnelli', 'Sjors',
            'promag', 'instagibbs', 'TheBlueMatt', 'jonatack', 'gmaxwell',
            'gavinandresen', 'petertodd', 'luke-jr', 'glozow'
        }
        
        print("="*80)
        print("BACKFILLING merged_by FOR MAINTAINER PRs")
        print("="*80)
        print()
        
        # Load existing PRs
        prs = []
        print(f"Loading PRs from {input_file}...")
        with open(input_file) as f:
            for line in f:
                if line.strip():
                    prs.append(json.loads(line))
        
        print(f"Loaded {len(prs):,} PRs")
        
        # Filter to merged maintainer PRs
        maintainer_merged = []
        for pr in prs:
            if not pr.get('merged', False):
                continue
            author = (pr.get('author') or '').lower()
            if author in [m.lower() for m in maintainers]:
                maintainer_merged.append(pr)
        
        print(f"Found {len(maintainer_merged):,} merged maintainer PRs")
        print()
        
        # Backfill data
        updated_count = 0
        error_count = 0
        
        for i, pr in enumerate(maintainer_merged):
            pr_number = pr.get('number')
            if not pr_number:
                continue
            
            # Skip if already has merged_by
            if pr.get('merged_by'):
                continue
            
            # Get merged_by data
            merged_by_data = self.backfill_pr(pr_number)
            
            if merged_by_data:
                # Update in both lists
                pr.update(merged_by_data)
                # Also update in main prs list
                for main_pr in prs:
                    if main_pr.get('number') == pr_number:
                        main_pr.update(merged_by_data)
                        break
                updated_count += 1
            else:
                error_count += 1
            
            if (i + 1) % 10 == 0:
                print(f"Processed {i+1}/{len(maintainer_merged)} PRs ({updated_count} updated, {error_count} errors)")
        
        print()
        print(f"Backfill complete: {updated_count} updated, {error_count} errors")
        print()
        
        # Save updated PRs
        print(f"Saving to {output_file}...")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            for pr in prs:
                f.write(json.dumps(pr) + '\n')
        
        print(f"Saved {len(prs):,} PRs to {output_file}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Backfill merged_by data for PRs')
    parser.add_argument('--input', type=Path, default=Path('data/github/prs_raw.jsonl'),
                        help='Input PR file')
    parser.add_argument('--output', type=Path, default=Path('data/github/prs_raw.jsonl'),
                        help='Output PR file (can be same as input)')
    parser.add_argument('--maintainers-only', action='store_true',
                        help='Only backfill merged maintainer PRs')
    parser.add_argument('--token', type=str, help='GitHub token (or set GITHUB_TOKEN env var)')
    
    args = parser.parse_args()
    
    token = args.token or None
    backfiller = MergedByBackfiller(token=token)
    
    if args.maintainers_only:
        backfiller.backfill_merged_maintainer_prs(args.input, args.output)
    else:
        backfiller.backfill_file(args.input, args.output, merged_only=True)


if __name__ == '__main__':
    main()
