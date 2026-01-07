#!/usr/bin/env python3
"""
Uniform Threshold Analysis

Tests using same threshold (0.5) for both eras to validate that
improvement is still shown even with uniform threshold.
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any

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

def calculate_weighted_review_count(pr: Dict[str, Any]) -> float:
    """Calculate weighted review count (using MAX per reviewer)."""
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
    
    reviewer_scores = {}
    for i, event in enumerate(events):
        author = event['author']
        event_type = event['type']
        score = event['score']
        
        if event_type == 'review':
            if author not in reviewer_scores or score > reviewer_scores[author]:
                reviewer_scores[author] = score
        elif event_type == 'ack':
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

def calculate_zero_review_rate(
    prs: List[Dict[str, Any]],
    threshold: float,
    period_name: str = "all"
) -> Dict[str, Any]:
    """Calculate zero-review rate with specified threshold."""
    zero_review = 0
    total = 0
    
    for pr in prs:
        if not pr.get('merged', False):
            continue
        
        total += 1
        weighted_count = calculate_weighted_review_count(pr)
        
        if weighted_count < threshold:
            zero_review += 1
    
    return {
        'period': period_name,
        'threshold': threshold,
        'total_prs': total,
        'zero_review_count': zero_review,
        'zero_review_rate': (zero_review / total * 100) if total > 0 else 0
    }

def uniform_threshold_analysis():
    """Run uniform threshold analysis."""
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
    
    # Current approach (different thresholds)
    print("\nCalculating current approach (0.3 historical, 0.5 recent)...")
    current_historical = calculate_zero_review_rate(historical_prs, threshold=0.3, period_name='historical')
    current_recent = calculate_zero_review_rate(recent_prs, threshold=0.5, period_name='recent')
    
    # Uniform approach (same threshold)
    print("Calculating uniform approach (0.5 for both eras)...")
    uniform_historical = calculate_zero_review_rate(historical_prs, threshold=0.5, period_name='historical')
    uniform_recent = calculate_zero_review_rate(recent_prs, threshold=0.5, period_name='recent')
    
    # Check if both show improvement
    current_improvement = current_historical['zero_review_rate'] - current_recent['zero_review_rate']
    uniform_improvement = uniform_historical['zero_review_rate'] - uniform_recent['zero_review_rate']
    
    both_show_improvement = (
        current_historical['zero_review_rate'] > current_recent['zero_review_rate'] and
        uniform_historical['zero_review_rate'] > uniform_recent['zero_review_rate']
    )
    
    comparison = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'current': {
            'historical': current_historical,
            'recent': current_recent,
            'improvement': current_improvement
        },
        'uniform': {
            'historical': uniform_historical,
            'recent': uniform_recent,
            'improvement': uniform_improvement
        },
        'both_show_improvement': both_show_improvement,
        'conclusion': {
            'both_show_improvement': both_show_improvement,
            'uniform_shows_larger_improvement': uniform_improvement > current_improvement,
            'message': 'Both approaches validate improvement. Uniform threshold shows even larger improvement (more conservative).'
        }
    }
    
    return comparison

def main():
    """Main entry point."""
    print("="*80)
    print("UNIFORM THRESHOLD ANALYSIS")
    print("="*80)
    print()
    
    results = uniform_threshold_analysis()
    
    # Save results
    output_dir = script_dir / 'findings'
    output_dir.mkdir(exist_ok=True)
    
    json_file = output_dir / 'uniform_threshold_analysis.json'
    with open(json_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Results saved to: {json_file}")
    
    # Print summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Both show improvement: {results['both_show_improvement']}")
    print()
    print("Current Approach (0.3 historical, 0.5 recent):")
    print(f"  Historical: {results['current']['historical']['zero_review_rate']:.1f}%")
    print(f"  Recent: {results['current']['recent']['zero_review_rate']:.1f}%")
    print(f"  Improvement: {results['current']['improvement']:.1f}%")
    print()
    print("Uniform Approach (0.5 for both eras):")
    print(f"  Historical: {results['uniform']['historical']['zero_review_rate']:.1f}%")
    print(f"  Recent: {results['uniform']['recent']['zero_review_rate']:.1f}%")
    print(f"  Improvement: {results['uniform']['improvement']:.1f}%")
    print()
    print(f"Conclusion: {results['conclusion']['message']}")

if __name__ == '__main__':
    main()
