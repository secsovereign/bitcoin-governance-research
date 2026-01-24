#!/usr/bin/env python3
"""
Code Complexity vs Governance Complexity Correlation Analysis

Analyzes correlation between code complexity and governance complexity.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.utils.load_prs_with_merged_by import load_prs_with_merged_by
from scripts.analysis.pr_importance_matrix import analyze_complexity_correlation


def simple_review_count(pr: Dict[str, Any]) -> float:
    """
    Simple review count function for complexity analysis.
    Just counts reviews - we don't need weighted scoring for this analysis.
    """
    reviews = pr.get('reviews', [])
    # Filter out COMMENTED reviews (they're not really reviews)
    meaningful_reviews = [r for r in reviews if r.get('state', '').upper() in ['APPROVED', 'CHANGES_REQUESTED']]
    return float(len(meaningful_reviews))


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Code Complexity vs Governance Complexity Analysis')
    parser.add_argument('--data-dir', type=Path, default=Path(__file__).parent.parent.parent.parent / 'data',
                       help='Data directory')
    parser.add_argument('--output', type=Path, default=Path(__file__).parent.parent.parent / 'findings' / 'data' / 'complexity_correlation.json',
                       help='Output JSON file')
    
    args = parser.parse_args()
    
    print("="*80)
    print("CODE COMPLEXITY VS GOVERNANCE COMPLEXITY ANALYSIS")
    print("="*80)
    print()
    
    # Load PRs
    print("Loading PRs...")
    prs_file = args.data_dir / 'github' / 'prs_raw.jsonl'
    mapping_file = args.data_dir / 'github' / 'merged_by_mapping.jsonl'
    prs = load_prs_with_merged_by(prs_file, mapping_file if mapping_file.exists() else None)
    print(f"Loaded {len(prs):,} PRs")
    print()
    
    # Run analysis
    print("Analyzing complexity correlation...")
    results = analyze_complexity_correlation(prs, simple_review_count)
    
    # Print results
    print("="*80)
    print("COMPLEXITY CORRELATION RESULTS")
    print("="*80)
    print()
    
    if 'error' in results:
        print(f"Error: {results['error']}")
        return
    
    overall = results.get('overall', {})
    print(f"Overall:")
    print(f"  Total PRs: {overall.get('total_prs', 0):,}")
    print(f"  Avg files per PR: {overall.get('avg_files', 0):.1f}")
    print(f"  Avg reviews per PR: {overall.get('avg_reviews', 0):.1f}")
    print(f"  Avg participants per PR: {overall.get('avg_participants', 0):.1f}")
    print()
    
    print(f"Correlation (files vs reviews): {results.get('correlation_files_vs_reviews', 0):.3f}")
    print(f"  (Positive = more complex code gets more governance attention)")
    print()
    
    print("By Code Complexity:")
    print("-" * 80)
    by_complexity = results.get('by_code_complexity', {})
    for level in ['low', 'medium', 'high']:
        if level in by_complexity:
            stats = by_complexity[level]
            print(f"{level.upper()} complexity (files {'≤5' if level=='low' else '6-15' if level=='medium' else '>15'}):")
            print(f"  PRs: {stats.get('count', 0):,}")
            print(f"  Avg reviews: {stats.get('avg_review_count', 0):.1f}")
            print(f"  Avg comments: {stats.get('avg_comment_count', 0):.1f}")
            print(f"  Avg participants: {stats.get('avg_participant_count', 0):.1f}")
            print(f"  Avg discussion length: {stats.get('avg_discussion_length', 0):,.0f} chars")
            if stats.get('avg_decision_time'):
                print(f"  Avg decision time: {stats.get('avg_decision_time', 0):.1f} days")
            print()
    
    # Save results
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"Results saved to: {args.output}")


if __name__ == '__main__':
    main()

