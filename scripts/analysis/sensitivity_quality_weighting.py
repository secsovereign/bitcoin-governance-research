#!/usr/bin/env python3
"""
Sensitivity Analysis for Quality Weighting

Tests how zero-review rates change with different quality thresholds
to validate robustness of results.
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple
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
    
    # Merge merged_by data if mapping file provided
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
    char_threshold_detailed: int = 50,
    char_threshold_good: int = 10
) -> float:
    """
    Calculate weighted review count for PR with configurable character thresholds.
    
    For each reviewer, takes the HIGHEST quality review (not sum).
    """
    from datetime import datetime
    import re
    
    # Check if PR was created before GitHub reviews existed
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
    
    # Track events with timestamps
    events = []
    
    # Formal GitHub reviews (ONLY for PRs created after Sept 2016)
    if not pre_review_era:
        for review in pr.get('reviews', []):
            author = (review.get('author') or '').lower()
            if author:
                date_str = review.get('submitted_at') or review.get('created_at')
                if date_str:
                    try:
                        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        # Custom scoring with configurable thresholds
                        state = (review.get('state') or '').upper()
                        body = (review.get('body') or '').strip()
                        
                        if state not in ['APPROVED', 'CHANGES_REQUESTED']:
                            score = 0.5 if body else 0.3
                        elif len(body) > char_threshold_detailed:
                            score = 1.0
                        elif len(body) > char_threshold_good:
                            score = 0.8
                        elif len(body) > 0:
                            score = 0.7
                        else:
                            score = 0.5
                        
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
    
    # Sort by date
    events.sort(key=lambda x: x['date'])
    
    # Track best score per reviewer, ignoring ACKs that come after detailed reviews
    reviewer_scores = {}
    
    for i, event in enumerate(events):
        author = event['author']
        event_type = event['type']
        score = event['score']
        
        if event_type == 'review':
            if author not in reviewer_scores or score > reviewer_scores[author]:
                reviewer_scores[author] = score
        elif event_type == 'ack':
            # Check if this ACK comes after a detailed review from same reviewer
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
    char_threshold_detailed: int = 50,
    char_threshold_good: int = 10,
    period_name: str = "all"
) -> Dict[str, Any]:
    """Calculate zero-review rate for given threshold and character thresholds."""
    zero_review = 0
    total = 0
    
    for pr in prs:
        # Only count merged PRs
        if not pr.get('merged', False):
            continue
        
        total += 1
        weighted_count = calculate_weighted_review_count(
            pr,
            char_threshold_detailed=char_threshold_detailed,
            char_threshold_good=char_threshold_good
        )
        
        # Use appropriate threshold based on era
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
        era_threshold = 0.3 if pre_review_era else threshold
        
        if weighted_count < era_threshold:
            zero_review += 1
    
    rate = (zero_review / total * 100) if total > 0 else 0
    
    return {
        'period': period_name,
        'threshold': threshold,
        'char_threshold_detailed': char_threshold_detailed,
        'char_threshold_good': char_threshold_good,
        'total_prs': total,
        'zero_review_count': zero_review,
        'zero_review_rate': rate
    }

def sensitivity_analysis_quality_weighting():
    """Run sensitivity analysis for quality weighting."""
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
    
    results = {}
    
    # Test different quality thresholds
    print("\nTesting quality thresholds...")
    thresholds = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
    
    for threshold in thresholds:
        print(f"  Testing threshold: {threshold}")
        
        # Historical period
        historical_result = calculate_zero_review_rate(
            historical_prs,
            threshold=threshold,
            period_name='historical'
        )
        
        # Recent period
        recent_result = calculate_zero_review_rate(
            recent_prs,
            threshold=threshold,
            period_name='recent'
        )
        
        results[threshold] = {
            'historical': historical_result,
            'recent': recent_result,
            'improvement': historical_result['zero_review_rate'] - recent_result['zero_review_rate']
        }
    
    # Test different character thresholds
    print("\nTesting character thresholds...")
    char_thresholds = [40, 50, 60]
    
    char_results = {}
    for char_thresh in char_thresholds:
        print(f"  Testing character threshold: {char_thresh}")
        
        # Use default quality threshold (0.5 for recent, 0.3 for historical)
        historical_result = calculate_zero_review_rate(
            historical_prs,
            threshold=0.3,
            char_threshold_detailed=char_thresh,
            period_name='historical'
        )
        
        recent_result = calculate_zero_review_rate(
            recent_prs,
            threshold=0.5,
            char_threshold_detailed=char_thresh,
            period_name='recent'
        )
        
        char_results[char_thresh] = {
            'historical': historical_result,
            'recent': recent_result,
            'improvement': historical_result['zero_review_rate'] - recent_result['zero_review_rate']
        }
    
    # Check pattern consistency
    pattern_consistent = True
    for threshold in thresholds:
        if (results[threshold]['historical']['zero_review_rate'] <= 
            results[threshold]['recent']['zero_review_rate']):
            pattern_consistent = False
            break
    
    # Calculate variation range
    historical_rates = [r['historical']['zero_review_rate'] for r in results.values()]
    recent_rates = [r['recent']['zero_review_rate'] for r in results.values()]
    
    variation_range = {
        'historical': {
            'min': min(historical_rates),
            'max': max(historical_rates),
            'range': max(historical_rates) - min(historical_rates)
        },
        'recent': {
            'min': min(recent_rates),
            'max': max(recent_rates),
            'range': max(recent_rates) - min(recent_rates)
        }
    }
    
    # Compile results
    output = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'quality_threshold_results': results,
        'character_threshold_results': char_results,
        'pattern_consistent': pattern_consistent,
        'variation_range': variation_range,
        'conclusion': {
            'pattern_consistent': pattern_consistent,
            'historical_variation': f"{variation_range['historical']['range']:.2f}%",
            'recent_variation': f"{variation_range['recent']['range']:.2f}%",
            'message': 'Results are robust across thresholds' if pattern_consistent else 'Patterns may vary with thresholds'
        }
    }
    
    return output

def main():
    """Main entry point."""
    print("="*80)
    print("SENSITIVITY ANALYSIS: Quality Weighting")
    print("="*80)
    print()
    
    results = sensitivity_analysis_quality_weighting()
    
    # Save results
    output_dir = script_dir / 'findings'
    output_dir.mkdir(exist_ok=True)
    
    json_file = output_dir / 'sensitivity_quality_weighting.json'
    with open(json_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: {json_file}")
    
    # Print summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Pattern consistent: {results['pattern_consistent']}")
    print(f"Historical variation range: {results['variation_range']['historical']['range']:.2f}%")
    print(f"Recent variation range: {results['variation_range']['recent']['range']:.2f}%")
    print()
    print("Quality Threshold Results:")
    for threshold, data in sorted(results['quality_threshold_results'].items()):
        hist_rate = data['historical']['zero_review_rate']
        recent_rate = data['recent']['zero_review_rate']
        improvement = data['improvement']
        print(f"  Threshold {threshold}: Historical {hist_rate:.1f}% → Recent {recent_rate:.1f}% (improvement: {improvement:.1f}%)")
    
    print("\nCharacter Threshold Results:")
    for char_thresh, data in sorted(results['character_threshold_results'].items()):
        hist_rate = data['historical']['zero_review_rate']
        recent_rate = data['recent']['zero_review_rate']
        improvement = data['improvement']
        print(f"  {char_thresh} chars: Historical {hist_rate:.1f}% → Recent {recent_rate:.1f}% (improvement: {improvement:.1f}%)")

if __name__ == '__main__':
    main()
