#!/usr/bin/env python3
"""
Funding Correlation Analysis

Quick analysis: Do PRs with funding mentions have different outcomes?
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any
from collections import Counter

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.utils.load_prs_with_merged_by import load_prs_with_merged_by

def analyze_funding_correlation(data_dir: Path):
    """Analyze correlation between funding mentions and PR outcomes."""
    print("="*80)
    print("FUNDING CORRELATION ANALYSIS")
    print("="*80)
    print()
    
    prs_file = data_dir / 'github' / 'prs_raw.jsonl'
    mapping_file = data_dir / 'github' / 'merged_by_mapping.jsonl'
    prs = load_prs_with_merged_by(prs_file, mapping_file if mapping_file.exists() else None)
    
    print(f"Loaded {len(prs):,} PRs")
    print()
    
    # Funding keywords
    funding_keywords = ['funding', 'grant', 'sponsor', 'donation', 'salary', 'corporate', 
                       'foundation', 'company', 'employer', 'paid', 'compensation']
    
    funding_sources = ['mit', 'coinbase', 'bitcoin foundation', 'chaincode', 'blockstream',
                       'square', 'block', 'digital currency group', 'dcg']
    
    # Categorize PRs
    with_funding = []
    without_funding = []
    
    for pr in prs:
        body = (pr.get('body') or '').lower()
        comments_text = ' '.join([c.get('body', '') for c in pr.get('comments', [])]).lower()
        all_text = body + ' ' + comments_text
        
        has_funding = any(kw in all_text for kw in funding_keywords) or \
                     any(src in all_text for src in funding_sources)
        
        if has_funding:
            with_funding.append(pr)
        else:
            without_funding.append(pr)
    
    print(f"PRs with funding mentions: {len(with_funding):,} ({len(with_funding)/len(prs)*100:.1f}%)")
    print(f"PRs without funding mentions: {len(without_funding):,}")
    print()
    
    # Compare outcomes
    def analyze_group(group_prs, group_name):
        merged = [p for p in group_prs if p.get('merged', False)]
        maintainer_prs = [p for p in group_prs 
                          if (p.get('author') or '').lower() in 
                          ['laanwj', 'sipa', 'maflcko', 'fanquake', 'hebasto', 'jnewbery',
                           'ryanofsky', 'achow101', 'theuni', 'jonasschnelli', 'sjors',
                           'promag', 'instagibbs', 'thebluematt', 'jonatack', 'gmaxwell',
                           'gavinandresen', 'petertodd', 'luke-jr', 'glozow']]
        
        maintainer_merged = [p for p in merged if p in maintainer_prs]
        
        # Time to merge
        times = []
        for pr in merged:
            created = pr.get('created_at')
            merged_at = pr.get('merged_at')
            if created and merged_at:
                try:
                    from datetime import datetime
                    created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    merged_dt = datetime.fromisoformat(merged_at.replace('Z', '+00:00'))
                    days = (merged_dt - created_dt).total_seconds() / 86400
                    if days >= 0:
                        times.append(days)
                except:
                    pass
        
        avg_time = sum(times) / len(times) if times else 0
        
        # Review counts
        avg_reviews = sum(len(p.get('reviews', [])) for p in merged) / len(merged) if merged else 0
        
        return {
            'total': len(group_prs),
            'merged': len(merged),
            'merge_rate': len(merged) / len(group_prs) if group_prs else 0,
            'maintainer_prs': len(maintainer_prs),
            'maintainer_merged': len(maintainer_merged),
            'maintainer_merge_rate': len(maintainer_merged) / len(maintainer_prs) if maintainer_prs else 0,
            'avg_time_to_merge_days': avg_time,
            'avg_reviews': avg_reviews
        }
    
    with_stats = analyze_group(with_funding, 'with_funding')
    without_stats = analyze_group(without_funding, 'without_funding')
    
    print("OUTCOME COMPARISON")
    print("-" * 80)
    print(f"Merge rate:")
    print(f"  With funding mention: {with_stats['merge_rate']*100:.1f}%")
    print(f"  Without funding mention: {without_stats['merge_rate']*100:.1f}%")
    print(f"  Difference: {(with_stats['merge_rate'] - without_stats['merge_rate'])*100:+.1f} percentage points")
    print()
    
    print(f"Maintainer merge rate:")
    print(f"  With funding mention: {with_stats['maintainer_merge_rate']*100:.1f}%")
    print(f"  Without funding mention: {without_stats['maintainer_merge_rate']*100:.1f}%")
    print()
    
    print(f"Average time to merge:")
    print(f"  With funding mention: {with_stats['avg_time_to_merge_days']:.1f} days")
    print(f"  Without funding mention: {without_stats['avg_time_to_merge_days']:.1f} days")
    print(f"  Difference: {with_stats['avg_time_to_merge_days'] - without_stats['avg_time_to_merge_days']:+.1f} days")
    print()
    
    print(f"Average reviews (merged PRs):")
    print(f"  With funding mention: {with_stats['avg_reviews']:.1f}")
    print(f"  Without funding mention: {without_stats['avg_reviews']:.1f}")
    print()
    
    # Save results
    output_file = data_dir.parent / 'findings' / 'funding_correlation.json'
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump({
            'with_funding': with_stats,
            'without_funding': without_stats,
            'total_with_funding': len(with_funding),
            'total_without_funding': len(without_funding)
        }, f, indent=2)
    
    print(f"Results saved to: {output_file}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze funding correlation')
    parser.add_argument('--data-dir', type=Path, default=Path(__file__).parent.parent.parent / 'data',
                       help='Data directory')
    
    args = parser.parse_args()
    analyze_funding_correlation(args.data_dir)
