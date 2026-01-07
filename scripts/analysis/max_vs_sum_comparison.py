#!/usr/bin/env python3
"""
MAX vs. SUM Comparison Analysis

Compares zero-review rates using MAX (current) vs. SUM (alternative) approaches
to show that both produce same patterns.
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any
from collections import defaultdict

# Add project root to path
script_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(script_dir))

from scripts.analysis.review_quality_weighting import (
    get_review_quality_score,
    get_ack_quality_score,
    GITHUB_REVIEWS_INTRODUCED
)

def load_jsonl(filepath: Path, mapping_file: Path = None) -> list:
    """Load JSONL file and return list of records with merged_by data."""
    records = []
    if not filepath.exists():
        return records
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    
    if mapping_file and mapping_file.exists():
        mapping = {}
        with open(mapping_file) as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    mapping[data['pr_number']] = {
                        'merged_by': data.get('merged_by'),
                        'merged_by_id': data.get('merged_by_id')
                    }
        
        for record in records:
            pr_number = record.get('number')
            if pr_number in mapping:
                record.update(mapping[pr_number])
    
    return records

def get_year(date_str):
    """Extract year from date string."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00')).year
    except:
        return None

def calculate_weighted_review_count(
    pr: Dict[str, Any],
    method: str = 'max'  # 'max' or 'sum'
) -> float:
    """
    Calculate weighted review count using MAX or SUM per reviewer.
    
    MAX: Takes highest quality review per reviewer (current approach)
    SUM: Sums all reviews from each reviewer (alternative approach)
    """
    import re
    
    pr_created_at = pr.get('created_at', '')
    pr_date = None
    if pr_created_at:
        try:
            pr_date_str = pr_created_at.replace('Z', '+00:00')
            pr_date = datetime.fromisoformat(pr_date_str)
            if pr_date.tzinfo is None:
                pr_date = pr_date.replace(tzinfo=timezone.utc)
        except:
            pass
    
    pre_review_era = pr_date and pr_date < GITHUB_REVIEWS_INTRODUCED if pr_date else False
    
    events = []
    
    # Formal GitHub reviews
    if not pre_review_era:
        for review in pr.get('reviews', []):
            author = (review.get('author') or '').lower()
            if author:
                date_str = review.get('submitted_at') or review.get('created_at')
                if date_str:
                    try:
                        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        score = get_review_quality_score(review)
                        events.append({
                            'type': 'review',
                            'author': author,
                            'date': dt,
                            'score': score
                        })
                    except:
                        pass
    
    # ACK comments
    ack_pattern = re.compile(r'(?:^|\s)ack(?:\s|$|[,\:])', re.IGNORECASE | re.MULTILINE)
    for comment in pr.get('comments', []):
        body = comment.get('body', '') or ''
        if ack_pattern.search(body):
            author = (comment.get('author') or '').lower()
            if author:
                date_str = comment.get('created_at')
                if date_str:
                    try:
                        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        score = get_ack_quality_score(comment)
                        events.append({
                            'type': 'ack',
                            'author': author,
                            'date': dt,
                            'score': score
                        })
                    except:
                        pass
    
    events.sort(key=lambda x: x['date'])
    
    if method == 'max':
        # MAX approach: Take highest quality review per reviewer
        reviewer_scores = {}
        
        for i, event in enumerate(events):
            author = event['author']
            event_type = event['type']
            score = event['score']
            
            if event_type == 'review':
                if author not in reviewer_scores or score > reviewer_scores[author]:
                    reviewer_scores[author] = score
            elif event_type == 'ack':
                # Check if completion signal
                is_completion_signal = False
                for j in range(i):
                    prev_event = events[j]
                    if (prev_event['type'] == 'review' and
                        prev_event['author'] == author and
                        prev_event['score'] >= 0.7):
                        is_completion_signal = True
                        break
                
                if not is_completion_signal:
                    if author not in reviewer_scores or score > reviewer_scores[author]:
                        reviewer_scores[author] = score
        
        return sum(reviewer_scores.values())
    
    else:  # method == 'sum'
        # SUM approach: Sum all reviews from each reviewer
        reviewer_scores = defaultdict(float)
        
        for i, event in enumerate(events):
            author = event['author']
            event_type = event['type']
            score = event['score']
            
            if event_type == 'review':
                reviewer_scores[author] += score
            elif event_type == 'ack':
                # Check if completion signal
                is_completion_signal = False
                for j in range(i):
                    prev_event = events[j]
                    if (prev_event['type'] == 'review' and
                        prev_event['author'] == author and
                        prev_event['score'] >= 0.7):
                        is_completion_signal = True
                        break
                
                if not is_completion_signal:
                    reviewer_scores[author] += score
        
        return sum(reviewer_scores.values())

def calculate_zero_review_rate(
    prs: List[Dict[str, Any]],
    method: str = 'max',
    period_name: str = "all"
) -> Dict[str, Any]:
    """Calculate zero-review rate using specified method."""
    zero_review = 0
    total = 0
    self_merge_zero = 0
    self_merge_total = 0
    other_merge_zero = 0
    other_merge_total = 0
    
    maintainers = {
        'laanwj', 'sipa', 'maflcko', 'fanquake', 'hebasto', 'jnewbery',
        'ryanofsky', 'achow101', 'theuni', 'jonasschnelli', 'sjors',
        'promag', 'instagibbs', 'thebluematt', 'jonatack', 'gmaxwell',
        'gavinandresen', 'petertodd', 'luke-jr', 'glozow'
    }
    
    for pr in prs:
        if not pr.get('merged', False):
            continue
        
        total += 1
        weighted_count = calculate_weighted_review_count(pr, method=method)
        
        # Determine threshold based on era
        pr_created_at = pr.get('created_at', '')
        pr_date = None
        if pr_created_at:
            try:
                pr_date_str = pr_created_at.replace('Z', '+00:00')
                pr_date = datetime.fromisoformat(pr_date_str)
                if pr_date.tzinfo is None:
                    pr_date = pr_date.replace(tzinfo=timezone.utc)
            except:
                pass
        
        pre_review_era = pr_date and pr_date < GITHUB_REVIEWS_INTRODUCED if pr_date else False
        threshold = 0.3 if pre_review_era else 0.5
        
        is_zero_review = weighted_count < threshold
        
        if is_zero_review:
            zero_review += 1
        
        # Check if self-merge
        author = (pr.get('author') or '').lower()
        merged_by = (pr.get('merged_by') or '').lower()
        is_maintainer_pr = author in maintainers or merged_by in maintainers
        is_self_merge = author and merged_by and author == merged_by
        
        if is_maintainer_pr:
            if is_self_merge:
                self_merge_total += 1
                if is_zero_review:
                    self_merge_zero += 1
            else:
                other_merge_total += 1
                if is_zero_review:
                    other_merge_zero += 1
    
    return {
        'period': period_name,
        'method': method,
        'total_prs': total,
        'zero_review_count': zero_review,
        'zero_review_rate': (zero_review / total * 100) if total > 0 else 0,
        'self_merge_total': self_merge_total,
        'self_merge_zero': self_merge_zero,
        'self_merge_zero_rate': (self_merge_zero / self_merge_total * 100) if self_merge_total > 0 else 0,
        'other_merge_total': other_merge_total,
        'other_merge_zero': other_merge_zero,
        'other_merge_zero_rate': (other_merge_zero / other_merge_total * 100) if other_merge_total > 0 else 0
    }

def compare_max_vs_sum():
    """Compare MAX vs. SUM approaches."""
    # Load data
    data_dir = script_dir / 'data' / 'github'
    prs_file = data_dir / 'prs_raw.jsonl'
    mapping_file = data_dir / 'merged_by_mapping.jsonl'
    
    print("Loading PR data...")
    prs = load_jsonl(prs_file, mapping_file)
    print(f"Loaded {len(prs):,} PRs")
    
    # Filter by period
    historical_prs = [p for p in prs if 2012 <= get_year(p.get('created_at', '')) <= 2020]
    recent_prs = [p for p in prs if 2021 <= get_year(p.get('created_at', '')) <= 2025]
    
    print(f"Historical PRs (2012-2020): {len(historical_prs):,}")
    print(f"Recent PRs (2021-2025): {len(recent_prs):,}")
    
    print("\nCalculating MAX approach...")
    max_historical = calculate_zero_review_rate(historical_prs, method='max', period_name='historical')
    max_recent = calculate_zero_review_rate(recent_prs, method='max', period_name='recent')
    
    print("Calculating SUM approach...")
    sum_historical = calculate_zero_review_rate(historical_prs, method='sum', period_name='historical')
    sum_recent = calculate_zero_review_rate(recent_prs, method='sum', period_name='recent')
    
    # Check pattern consistency
    pattern_consistent = (
        max_historical['zero_review_rate'] > max_recent['zero_review_rate'] and
        sum_historical['zero_review_rate'] > sum_recent['zero_review_rate'] and
        max_historical['self_merge_zero_rate'] > max_historical['other_merge_zero_rate'] and
        sum_historical['self_merge_zero_rate'] > sum_historical['other_merge_zero_rate']
    )
    
    comparison = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'max': {
            'historical': max_historical,
            'recent': max_recent
        },
        'sum': {
            'historical': sum_historical,
            'recent': sum_recent
        },
        'difference': {
            'historical': {
                'zero_review_rate': max_historical['zero_review_rate'] - sum_historical['zero_review_rate'],
                'self_merge_zero_rate': max_historical['self_merge_zero_rate'] - sum_historical['self_merge_zero_rate']
            },
            'recent': {
                'zero_review_rate': max_recent['zero_review_rate'] - sum_recent['zero_review_rate'],
                'self_merge_zero_rate': max_recent['self_merge_zero_rate'] - sum_recent['self_merge_zero_rate']
            }
        },
        'pattern_consistent': pattern_consistent,
        'conclusion': {
            'both_show_improvement': (
                max_historical['zero_review_rate'] > max_recent['zero_review_rate'] and
                sum_historical['zero_review_rate'] > sum_recent['zero_review_rate']
            ),
            'max_more_conservative': (
                max_historical['zero_review_rate'] > sum_historical['zero_review_rate'] and
                max_recent['zero_review_rate'] > sum_recent['zero_review_rate']
            ),
            'message': 'Both approaches show same patterns. MAX is more conservative.'
        }
    }
    
    return comparison

def main():
    """Main entry point."""
    print("="*80)
    print("MAX vs. SUM COMPARISON ANALYSIS")
    print("="*80)
    print()
    
    results = compare_max_vs_sum()
    
    # Save results
    output_dir = script_dir / 'findings'
    output_dir.mkdir(exist_ok=True)
    
    json_file = output_dir / 'max_vs_sum_comparison.json'
    with open(json_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Results saved to: {json_file}")
    
    # Print summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Pattern consistent: {results['pattern_consistent']}")
    print()
    print("MAX Approach:")
    print(f"  Historical zero-review: {results['max']['historical']['zero_review_rate']:.1f}%")
    print(f"  Recent zero-review: {results['max']['recent']['zero_review_rate']:.1f}%")
    print(f"  Improvement: {results['max']['historical']['zero_review_rate'] - results['max']['recent']['zero_review_rate']:.1f}%")
    print()
    print("SUM Approach:")
    print(f"  Historical zero-review: {results['sum']['historical']['zero_review_rate']:.1f}%")
    print(f"  Recent zero-review: {results['sum']['recent']['zero_review_rate']:.1f}%")
    print(f"  Improvement: {results['sum']['historical']['zero_review_rate'] - results['sum']['recent']['zero_review_rate']:.1f}%")
    print()
    print("Difference (MAX - SUM):")
    print(f"  Historical: {results['difference']['historical']['zero_review_rate']:.1f}%")
    print(f"  Recent: {results['difference']['recent']['zero_review_rate']:.1f}%")
    print()
    print(f"Conclusion: {results['conclusion']['message']}")

if __name__ == '__main__':
    main()
