#!/usr/bin/env python3
"""
Quick validation script to check self-merge rate on a sample of PRs.

This checks a small sample of maintainer PRs directly from GitHub
to quickly validate or invalidate the self-merge claim.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any
from github import Github
from github.RateLimiter import RateLimiter

def quick_validate():
    """Quickly validate self-merge claim on sample PRs."""
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        print("ERROR: GITHUB_TOKEN environment variable not set")
        print("Set it with: export GITHUB_TOKEN=your_token")
        return
    
    github = Github(token)
    rate_limiter = RateLimiter(max_calls=4500, time_window=3600)
    repo = github.get_repo("bitcoin/bitcoin")
    
    maintainers = {
        'laanwj', 'sipa', 'maflcko', 'fanquake', 'hebasto', 'jnewbery',
        'ryanofsky', 'achow101', 'theuni', 'jonasschnelli', 'Sjors',
        'promag', 'instagibbs', 'TheBlueMatt', 'jonatack', 'gmaxwell',
        'gavinandresen', 'petertodd', 'luke-jr', 'glozow'
    }
    
    # Load PR numbers to check
    data_dir = Path(__file__).parent.parent.parent / 'data' / 'github'
    prs = []
    with open(data_dir / 'prs_raw.jsonl') as f:
        for line in f:
            if line.strip():
                prs.append(json.loads(line))
    
    # Get merged maintainer PRs
    maintainer_merged = []
    for pr in prs:
        if not pr.get('merged', False):
            continue
        author = (pr.get('author') or '').lower()
        if author in [m.lower() for m in maintainers]:
            maintainer_merged.append(pr)
    
    # Sample for validation (first 50)
    sample_size = min(50, len(maintainer_merged))
    sample = maintainer_merged[:sample_size]
    
    print("="*80)
    print(f"QUICK VALIDATION: Checking {sample_size} maintainer PRs")
    print("="*80)
    print()
    
    results = []
    self_merged = 0
    other_merged = 0
    errors = 0
    
    for i, pr in enumerate(sample):
        pr_number = pr.get('number')
        author = pr.get('author', 'unknown')
        
        try:
            rate_limiter.wait_if_needed()
            github_pr = repo.get_pull(pr_number)
            
            if github_pr.merged:
                merged_by = github_pr.merged_by.login if github_pr.merged_by else None
                is_self = merged_by and merged_by.lower() == author.lower()
                
                if is_self:
                    self_merged += 1
                else:
                    other_merged += 1
                
                results.append({
                    'pr': pr_number,
                    'author': author,
                    'merged_by': merged_by,
                    'is_self_merge': is_self
                })
                
                status = "✓ SELF" if is_self else "✗ OTHER"
                print(f"[{i+1}/{sample_size}] PR #{pr_number} ({author}): {status} (merged by: {merged_by})")
            else:
                errors += 1
                print(f"[{i+1}/{sample_size}] PR #{pr_number}: Not merged (data inconsistency)")
        
        except Exception as e:
            errors += 1
            print(f"[{i+1}/{sample_size}] PR #{pr_number}: Error - {e}")
    
    print()
    print("="*80)
    print("VALIDATION RESULTS")
    print("="*80)
    print()
    print(f"Sample size: {sample_size}")
    print(f"Self-merged: {self_merged} ({self_merged/sample_size*100:.1f}%)")
    print(f"Merged by others: {other_merged} ({other_merged/sample_size*100:.1f}%)")
    print(f"Errors: {errors}")
    print()
    
    if sample_size >= 30:
        print("STATISTICAL SIGNIFICANCE:")
        print(f"  If {self_merged/sample_size*100:.1f}% self-merge rate holds,")
        print(f"  we can reject '100% self-merge' claim with high confidence.")
        print()
    
    # Save results
    output_file = Path(__file__).parent.parent.parent / 'findings' / 'self_merge_validation_sample.json'
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump({
            'sample_size': sample_size,
            'self_merged': self_merged,
            'other_merged': other_merged,
            'self_merge_rate': self_merged / sample_size if sample_size > 0 else 0,
            'results': results
        }, f, indent=2)
    
    print(f"Results saved to: {output_file}")


if __name__ == '__main__':
    quick_validate()
