#!/usr/bin/env python3
"""
Optimized backfill for merged_by data.

Creates a SEPARATE mapping file (pr_number -> merged_by) that can be
merged with the main dataset later. This avoids any risk to the original data.

Uses parallel requests with rate limiting for faster execution.
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from github import Github

class OptimizedMergedByBackfiller:
    """Optimized backfill with parallel requests and separate output."""
    
    def __init__(self, token: Optional[str] = None, max_workers: int = 5):
        """Initialize backfiller."""
        self.token = token or self._get_token()
        if not self.token:
            raise ValueError("GitHub token required. Set GITHUB_TOKEN environment variable.")
        
        self.max_workers = max_workers
        self.github = Github(self.token)
        self.repo = self.github.get_repo("bitcoin/bitcoin")
        
        # Rate limiting: GitHub allows 5,000 requests/hour = ~1.4 req/sec
        # With 5 workers, we can do ~7 req/sec, but we'll be conservative
        self.rate_limit_delay = 0.15  # ~6.7 req/sec per worker, ~33 req/sec total (safe)
        self.last_request_time = {}
        self.request_lock = Lock()
    
    def _get_token(self) -> Optional[str]:
        """Get GitHub token from environment or config."""
        return os.getenv('GITHUB_TOKEN')
    
    def _rate_limited_request(self, worker_id: int):
        """Ensure rate limiting per worker."""
        with self.request_lock:
            now = time.time()
            last = self.last_request_time.get(worker_id, 0)
            elapsed = now - last
            if elapsed < self.rate_limit_delay:
                time.sleep(self.rate_limit_delay - elapsed)
            self.last_request_time[worker_id] = time.time()
    
    def backfill_single_pr(self, pr_number: int, worker_id: int) -> Optional[Dict[str, Any]]:
        """Get merged_by data for a single PR (thread-safe)."""
        try:
            self._rate_limited_request(worker_id)
            pr = self.repo.get_pull(pr_number)
            
            if not pr.merged:
                return None
            
            merged_by_data = {
                'pr_number': pr_number,
                'merged_by': pr.merged_by.login if pr.merged_by else None,
                'merged_by_id': pr.merged_by.id if pr.merged_by else None,
            }
            
            return merged_by_data
        except Exception as e:
            print(f"Error getting PR {pr_number}: {e}")
            return None
    
    def backfill_prs_parallel(self, pr_numbers: List[int], output_file: Path):
        """Backfill multiple PRs in parallel."""
        print("="*80)
        print("OPTIMIZED BACKFILL: merged_by DATA")
        print("="*80)
        print()
        print(f"Processing {len(pr_numbers):,} PRs with {self.max_workers} workers")
        print(f"Estimated time: ~{len(pr_numbers) / (self.max_workers / self.rate_limit_delay) / 60:.1f} minutes")
        print()
        
        results = []
        completed = 0
        errors = 0
        start_time = time.time()
        
        # Process in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_pr = {
                executor.submit(self.backfill_single_pr, pr_num, i % self.max_workers): pr_num
                for i, pr_num in enumerate(pr_numbers)
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_pr):
                pr_num = future_to_pr[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                        completed += 1
                    else:
                        errors += 1
                except Exception as e:
                    print(f"Error processing PR {pr_num}: {e}")
                    errors += 1
                
                # Progress update
                if (completed + errors) % 50 == 0:
                    elapsed = time.time() - start_time
                    rate = (completed + errors) / elapsed if elapsed > 0 else 0
                    remaining = (len(pr_numbers) - completed - errors) / rate if rate > 0 else 0
                    print(f"Progress: {completed + errors}/{len(pr_numbers)} "
                          f"({completed} success, {errors} errors) | "
                          f"Rate: {rate:.1f} PRs/sec | "
                          f"ETA: {remaining/60:.1f} min")
        
        elapsed = time.time() - start_time
        print()
        print(f"Backfill complete in {elapsed/60:.1f} minutes")
        print(f"  Success: {completed}")
        print(f"  Errors: {errors}")
        print()
        
        # Save to separate mapping file
        print(f"Saving mapping to {output_file}...")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            for result in results:
                f.write(json.dumps(result) + '\n')
        
        print(f"Saved {len(results):,} mappings to {output_file}")
        print()
        print("This is a SEPARATE file. Your original dataset is untouched.")
        print("You can merge this later using merge_merged_by_data.py")
    
    def get_prs_to_backfill(self, input_file: Path, merged_only: bool = True, 
                           maintainers_only: bool = False) -> List[int]:
        """Get list of PR numbers that need backfilling."""
        print(f"Loading PRs from {input_file}...")
        prs = []
        with open(input_file) as f:
            for line in f:
                if line.strip():
                    prs.append(json.loads(line))
        
        print(f"Loaded {len(prs):,} PRs")
        
        # Filter
        if merged_only:
            prs = [p for p in prs if p.get('merged', False)]
            print(f"Filtered to {len(prs):,} merged PRs")
        
        if maintainers_only:
            maintainers = {
                'laanwj', 'sipa', 'maflcko', 'fanquake', 'hebasto', 'jnewbery',
                'ryanofsky', 'achow101', 'theuni', 'jonasschnelli', 'Sjors',
                'promag', 'instagibbs', 'TheBlueMatt', 'jonatack', 'gmaxwell',
                'gavinandresen', 'petertodd', 'luke-jr', 'glozow'
            }
            prs = [p for p in prs 
                   if (p.get('author') or '').lower() in [m.lower() for m in maintainers]]
            print(f"Filtered to {len(prs):,} maintainer PRs")
        
        # Get PRs that need backfilling (don't have merged_by)
        pr_numbers = []
        for pr in prs:
            if not pr.get('merged_by') and pr.get('number'):
                pr_numbers.append(pr['number'])
        
        print(f"Found {len(pr_numbers):,} PRs needing backfill")
        print()
        
        return pr_numbers


def merge_mapping_into_dataset(mapping_file: Path, dataset_file: Path, output_file: Path):
    """Merge the separate mapping file into the main dataset."""
    print("="*80)
    print("MERGING merged_by DATA INTO DATASET")
    print("="*80)
    print()
    
    # Load mapping
    print(f"Loading mapping from {mapping_file}...")
    mapping = {}
    with open(mapping_file) as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                mapping[data['pr_number']] = {
                    'merged_by': data.get('merged_by'),
                    'merged_by_id': data.get('merged_by_id')
                }
    
    print(f"Loaded {len(mapping):,} mappings")
    print()
    
    # Load and update dataset
    print(f"Loading dataset from {dataset_file}...")
    updated = 0
    total = 0
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(dataset_file) as infile, open(output_file, 'w') as outfile:
        for line in infile:
            if not line.strip():
                continue
            
            pr = json.loads(line)
            total += 1
            
            pr_number = pr.get('number')
            if pr_number in mapping:
                pr.update(mapping[pr_number])
                updated += 1
            
            outfile.write(json.dumps(pr) + '\n')
    
    print(f"Updated {updated:,} PRs out of {total:,} total")
    print(f"Saved to {output_file}")
    print()
    print("Original dataset preserved at:", dataset_file)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Optimized backfill for merged_by data (creates separate mapping file)'
    )
    parser.add_argument('--input', type=Path, 
                       default=Path('data/github/prs_raw.jsonl'),
                       help='Input PR file')
    parser.add_argument('--output', type=Path,
                       default=Path('data/github/merged_by_mapping.jsonl'),
                       help='Output mapping file (separate from main dataset)')
    parser.add_argument('--maintainers-only', action='store_true',
                       help='Only backfill merged maintainer PRs')
    parser.add_argument('--workers', type=int, default=5,
                       help='Number of parallel workers (default: 5)')
    parser.add_argument('--token', type=str,
                       help='GitHub token (or set GITHUB_TOKEN env var)')
    parser.add_argument('--merge', action='store_true',
                       help='Merge existing mapping file into dataset')
    parser.add_argument('--merge-input', type=Path,
                       help='Dataset file to merge into (for --merge)')
    parser.add_argument('--merge-output', type=Path,
                       help='Output file for merged dataset (for --merge)')
    
    args = parser.parse_args()
    
    if args.merge:
        # Merge mode
        if not args.merge_input or not args.merge_output:
            parser.error("--merge requires --merge-input and --merge-output")
        merge_mapping_into_dataset(args.output, args.merge_input, args.merge_output)
    else:
        # Backfill mode
        token = args.token or None
        backfiller = OptimizedMergedByBackfiller(token=token, max_workers=args.workers)
        
        pr_numbers = backfiller.get_prs_to_backfill(
            args.input,
            merged_only=True,
            maintainers_only=args.maintainers_only
        )
        
        if pr_numbers:
            backfiller.backfill_prs_parallel(pr_numbers, args.output)
        else:
            print("No PRs need backfilling!")


if __name__ == '__main__':
    main()
