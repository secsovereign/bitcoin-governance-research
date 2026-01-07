#!/usr/bin/env python3
"""
Fix Review Coverage Calculation

Investigates and fixes the review coverage calculation issue.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.utils.load_prs_with_merged_by import load_prs_with_merged_by

def investigate_review_coverage(data_dir: Path):
    """Investigate review coverage calculation."""
    print("="*80)
    print("REVIEW COVERAGE INVESTIGATION")
    print("="*80)
    print()
    
    prs_file = data_dir / 'github' / 'prs_raw.jsonl'
    mapping_file = data_dir / 'github' / 'merged_by_mapping.jsonl'
    prs = load_prs_with_merged_by(prs_file, mapping_file if mapping_file.exists() else None)
    
    print(f"Loaded {len(prs):,} PRs")
    print()
    
    # Check PRs with reviews
    prs_with_reviews = [p for p in prs if p.get('reviews') and len(p.get('reviews', [])) > 0]
    print(f"PRs with reviews: {len(prs_with_reviews):,}")
    
    # Check file data structure
    sample_prs = [p for p in prs_with_reviews[:10] if p.get('files') or p.get('files_changed')]
    print(f"\nSample PRs with file data: {len(sample_prs)}")
    
    for pr in sample_prs[:3]:
        print(f"\nPR #{pr.get('number')}:")
        print(f"  Files field: {type(pr.get('files'))}")
        print(f"  Files changed field: {type(pr.get('files_changed'))}")
        if pr.get('files'):
            print(f"  Files count: {len(pr.get('files', []))}")
            if pr.get('files'):
                print(f"  First file: {pr.get('files', [])[0] if pr.get('files') else 'None'}")
        if pr.get('files_changed'):
            print(f"  Files changed count: {len(pr.get('files_changed', []))}")
    
    # Check review comment structure
    print("\n" + "="*80)
    print("REVIEW COMMENT STRUCTURE")
    print("="*80)
    
    reviews_with_comments = []
    for pr in prs_with_reviews[:100]:
        for review in pr.get('reviews', []):
            if review.get('review_comments') or review.get('comments'):
                reviews_with_comments.append(review)
                if len(reviews_with_comments) >= 5:
                    break
        if len(reviews_with_comments) >= 5:
            break
    
    print(f"Found {len(reviews_with_comments)} reviews with comments")
    for i, review in enumerate(reviews_with_comments[:3]):
        print(f"\nReview {i+1}:")
        print(f"  Keys: {list(review.keys())}")
        if review.get('review_comments'):
            print(f"  Review comments: {len(review.get('review_comments', []))}")
            if review.get('review_comments'):
                print(f"  First comment keys: {list(review.get('review_comments', [])[0].keys()) if review.get('review_comments') else 'None'}")
        if review.get('comments'):
            print(f"  Comments: {len(review.get('comments', []))}")
    
    # Calculate coverage using different methods
    print("\n" + "="*80)
    print("COVERAGE CALCULATION TEST")
    print("="*80)
    
    test_prs = [p for p in prs_with_reviews if (p.get('files') or p.get('files_changed')) and len(p.get('reviews', [])) > 0][:100]
    
    methods = {
        'method1_files_field': 0,
        'method2_files_changed_field': 0,
        'method3_review_comments': 0,
        'method4_comments_field': 0
    }
    
    for pr in test_prs:
        files = pr.get('files', []) or []
        files_changed = pr.get('files_changed', []) or []
        reviews = pr.get('reviews', []) or []
        
        # Method 1: Use 'files' field
        if files:
            methods['method1_files_field'] += 1
        
        # Method 2: Use 'files_changed' field
        if files_changed:
            methods['method2_files_changed_field'] += 1
        
        # Method 3: Check review_comments
        has_review_comments = any(r.get('review_comments') for r in reviews)
        if has_review_comments:
            methods['method3_review_comments'] += 1
        
        # Method 4: Check comments field
        has_comments = any(r.get('comments') for r in reviews)
        if has_comments:
            methods['method4_comments_field'] += 1
    
    print(f"Test PRs: {len(test_prs)}")
    print(f"Method 1 (files field): {methods['method1_files_field']} PRs")
    print(f"Method 2 (files_changed field): {methods['method2_files_changed_field']} PRs")
    print(f"Method 3 (review_comments): {methods['method3_review_comments']} PRs")
    print(f"Method 4 (comments field): {methods['method4_comments_field']} PRs")
    
    # Calculate actual coverage
    print("\n" + "="*80)
    print("ACTUAL COVERAGE CALCULATION")
    print("="*80)
    
    coverage_results = []
    for pr in test_prs:
        # Get files
        files = []
        if pr.get('files'):
            files = [f if isinstance(f, str) else f.get('filename') or f.get('path', '') for f in pr.get('files', [])]
        elif pr.get('files_changed'):
            files = [f if isinstance(f, str) else f.get('filename') or f.get('path', '') for f in pr.get('files_changed', [])]
        
        if not files:
            continue
        
        # Get reviewed files from review comments
        reviewed_files = set()
        for review in pr.get('reviews', []):
            # Check review_comments
            for comment in review.get('review_comments', []):
                path = comment.get('path') or comment.get('file_path') or comment.get('filename')
                if path:
                    reviewed_files.add(path)
            
            # Check comments
            for comment in review.get('comments', []):
                path = comment.get('path') or comment.get('file_path') or comment.get('filename')
                if path:
                    reviewed_files.add(path)
        
        if files:
            coverage = len(reviewed_files) / len(files) if files else 0
            coverage_results.append({
                'pr_number': pr.get('number'),
                'total_files': len(files),
                'reviewed_files': len(reviewed_files),
                'coverage': coverage
            })
    
    if coverage_results:
        avg_coverage = sum(c['coverage'] for c in coverage_results) / len(coverage_results)
        print(f"PRs analyzed: {len(coverage_results)}")
        print(f"Average coverage: {avg_coverage*100:.1f}%")
        print(f"PRs with full coverage: {sum(1 for c in coverage_results if c['coverage'] >= 1.0)}")
        print(f"PRs with zero coverage: {sum(1 for c in coverage_results if c['coverage'] == 0.0)}")
    else:
        print("No coverage data could be calculated")
        print("This suggests the issue is with file data structure or review comment structure")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Investigate review coverage calculation')
    parser.add_argument('--data-dir', type=Path, default=Path(__file__).parent.parent.parent / 'data',
                       help='Data directory')
    
    args = parser.parse_args()
    investigate_review_coverage(args.data_dir)
