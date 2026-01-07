#!/usr/bin/env python3
"""
Statistical Significance Tests

Performs chi-square tests, t-tests, and calculates effect sizes and
confidence intervals to validate that differences are statistically significant.
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any
from collections import Counter
import math

# Add project root to path
script_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(script_dir))

try:
    from scipy.stats import chi2_contingency, ttest_ind, linregress
    import numpy as np
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("WARNING: scipy not available. Some tests will be skipped.")
    print("Install with: pip install scipy numpy")

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

def calculate_cramers_v(contingency_table):
    """Calculate Cramer's V effect size."""
    if not SCIPY_AVAILABLE:
        return None
    
    chi2, _, _, _ = chi2_contingency(contingency_table)
    n = sum(sum(row) for row in contingency_table)
    min_dim = min(len(contingency_table), len(contingency_table[0]))
    
    if n == 0 or min_dim == 1:
        return 0.0
    
    cramers_v = math.sqrt(chi2 / (n * (min_dim - 1)))
    return cramers_v

def calculate_binomial_ci(successes, n, confidence=0.95):
    """Calculate binomial confidence interval using normal approximation."""
    if n == 0:
        return (0.0, 0.0)
    
    p = successes / n
    z = 1.96 if confidence == 0.95 else 2.576  # 95% or 99%
    
    margin = z * math.sqrt((p * (1 - p)) / n)
    lower = max(0.0, p - margin)
    upper = min(1.0, p + margin)
    
    return (lower * 100, upper * 100)  # Return as percentage

def chi_square_zero_review(historical_prs, recent_prs):
    """Chi-square test for zero-review rates."""
    if not SCIPY_AVAILABLE:
        return None
    
    # Calculate zero-review counts
    historical_total = sum(1 for p in historical_prs if p.get('merged', False))
    historical_zero = 0
    for pr in historical_prs:
        if not pr.get('merged', False):
            continue
        weighted_count = calculate_weighted_review_count(pr)
        threshold = 0.3  # Pre-review era threshold
        if weighted_count < threshold:
            historical_zero += 1
    historical_reviewed = historical_total - historical_zero
    
    recent_total = sum(1 for p in recent_prs if p.get('merged', False))
    recent_zero = 0
    for pr in recent_prs:
        if not pr.get('merged', False):
            continue
        weighted_count = calculate_weighted_review_count(pr)
        threshold = 0.5  # Post-review era threshold
        if weighted_count < threshold:
            recent_zero += 1
    recent_reviewed = recent_total - recent_zero
    
    # Contingency table
    contingency_table = [
        [historical_zero, historical_reviewed],
        [recent_zero, recent_reviewed]
    ]
    
    chi2, p_value, dof, expected = chi2_contingency(contingency_table)
    cramers_v = calculate_cramers_v(contingency_table)
    
    return {
        'chi2': float(chi2),
        'p_value': float(p_value),
        'dof': int(dof),
        'significant': p_value < 0.001,
        'cramers_v': float(cramers_v) if cramers_v else None,
        'effect_size': 'large' if cramers_v and cramers_v > 0.3 else 'medium' if cramers_v and cramers_v > 0.1 else 'small' if cramers_v else 'unknown',
        'contingency_table': contingency_table,
        'historical_rate': (historical_zero / historical_total * 100) if historical_total > 0 else 0,
        'recent_rate': (recent_zero / recent_total * 100) if recent_total > 0 else 0
    }

def t_test_self_merge_stability(prs):
    """T-test for self-merge rate stability over time."""
    if not SCIPY_AVAILABLE:
        return None
    
    maintainers = {
        'laanwj', 'sipa', 'maflcko', 'fanquake', 'hebasto', 'jnewbery',
        'ryanofsky', 'achow101', 'theuni', 'jonasschnelli', 'sjors',
        'promag', 'instagibbs', 'thebluematt', 'jonatack', 'gmaxwell',
        'gavinandresen', 'petertodd', 'luke-jr', 'glozow'
    }
    
    # Calculate yearly self-merge rates
    yearly_rates = Counter()
    yearly_totals = Counter()
    
    for pr in prs:
        if not pr.get('merged', False):
            continue
        
        author = (pr.get('author') or '').lower()
        merged_by = (pr.get('merged_by') or '').lower()
        
        if author in maintainers and merged_by in maintainers:
            year = get_year(pr.get('created_at', ''))
            if year:
                yearly_totals[year] += 1
                if author == merged_by:
                    yearly_rates[year] += 1
    
    # Get rates for historical and recent periods
    historical_years = list(range(2012, 2021))
    recent_years = list(range(2021, 2026))
    
    historical_rates = []
    for year in historical_years:
        if yearly_totals[year] > 0:
            rate = yearly_rates[year] / yearly_totals[year]
            historical_rates.append(rate)
    
    recent_rates = []
    for year in recent_years:
        if yearly_totals[year] > 0:
            rate = yearly_rates[year] / yearly_totals[year]
            recent_rates.append(rate)
    
    if len(historical_rates) < 2 or len(recent_rates) < 2:
        return None
    
    # T-test
    t_stat, p_value = ttest_ind(historical_rates, recent_rates)
    
    # Linear regression for trend
    all_years = historical_years + recent_years
    all_rates = []
    for year in all_years:
        if yearly_totals[year] > 0:
            rate = yearly_rates[year] / yearly_totals[year]
            all_rates.append(rate)
    
    if len(all_rates) >= 2:
        slope, intercept, r_value, p_value_trend, std_err = linregress(range(len(all_rates)), all_rates)
    else:
        slope, p_value_trend = 0, 1.0
    
    return {
        't_stat': float(t_stat),
        'p_value': float(p_value),
        'significant_difference': p_value < 0.05,
        'slope': float(slope) if 'slope' in locals() else 0.0,
        'p_value_trend': float(p_value_trend) if 'p_value_trend' in locals() else 1.0,
        'declining': slope < 0 and p_value_trend < 0.05 if 'slope' in locals() else False,
        'stable': abs(slope) < 0.01 or p_value_trend > 0.05 if 'slope' in locals() else True,
        'historical_avg': sum(historical_rates) / len(historical_rates) if historical_rates else 0,
        'recent_avg': sum(recent_rates) / len(recent_rates) if recent_rates else 0
    }

def calculate_confidence_intervals(prs):
    """Calculate 95% confidence intervals for key metrics."""
    maintainers = {
        'laanwj', 'sipa', 'maflcko', 'fanquake', 'hebasto', 'jnewbery',
        'ryanofsky', 'achow101', 'theuni', 'jonasschnelli', 'sjors',
        'promag', 'instagibbs', 'thebluematt', 'jonatack', 'gmaxwell',
        'gavinandresen', 'petertodd', 'luke-jr', 'glozow'
    }
    
    # Self-merge rate
    maintainer_merged = [p for p in prs if p.get('merged', False) and 
                        (p.get('author', '').lower() in maintainers or 
                         (p.get('merged_by') or '').lower() in maintainers)]
    self_merges = sum(1 for p in maintainer_merged 
                     if (p.get('author') or '').lower() == (p.get('merged_by') or '').lower())
    self_merge_ci = calculate_binomial_ci(self_merges, len(maintainer_merged))
    
    # Zero-review rates
    historical_prs = [p for p in prs if 2012 <= get_year(p.get('created_at', '')) <= 2020 and p.get('merged', False)]
    recent_prs = [p for p in prs if 2021 <= get_year(p.get('created_at', '')) <= 2025 and p.get('merged', False)]
    
    historical_zero = sum(1 for p in historical_prs 
                         if calculate_weighted_review_count(p) < 0.3)
    historical_ci = calculate_binomial_ci(historical_zero, len(historical_prs))
    
    recent_zero = sum(1 for p in recent_prs 
                     if calculate_weighted_review_count(p) < 0.5)
    recent_ci = calculate_binomial_ci(recent_zero, len(recent_prs))
    
    return {
        'self_merge_rate': {
            'value': (self_merges / len(maintainer_merged) * 100) if maintainer_merged else 0,
            'n': len(maintainer_merged),
            'ci_95': self_merge_ci
        },
        'zero_review_historical': {
            'value': (historical_zero / len(historical_prs) * 100) if historical_prs else 0,
            'n': len(historical_prs),
            'ci_95': historical_ci
        },
        'zero_review_recent': {
            'value': (recent_zero / len(recent_prs) * 100) if recent_prs else 0,
            'n': len(recent_prs),
            'ci_95': recent_ci
        }
    }

def main():
    """Main entry point."""
    print("="*80)
    print("STATISTICAL SIGNIFICANCE TESTS")
    print("="*80)
    print()
    
    if not SCIPY_AVAILABLE:
        print("ERROR: scipy is required for statistical tests.")
        print("Install with: pip install scipy numpy")
        return
    
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
    
    # Run tests
    print("\nRunning chi-square test for zero-review rates...")
    chi_square_result = chi_square_zero_review(historical_prs, recent_prs)
    
    print("Running t-test for self-merge rate stability...")
    t_test_result = t_test_self_merge_stability(prs)
    
    print("Calculating confidence intervals...")
    ci_results = calculate_confidence_intervals(prs)
    
    # Compile results
    results = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'chi_square_test': chi_square_result,
        't_test_self_merge': t_test_result,
        'confidence_intervals': ci_results
    }
    
    # Save results
    output_dir = script_dir / 'findings'
    output_dir.mkdir(exist_ok=True)
    
    json_file = output_dir / 'statistical_significance_tests.json'
    with open(json_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: {json_file}")
    
    # Print summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    if chi_square_result:
        print("\nChi-Square Test (Zero-Review Rates):")
        print(f"  Chi-square: {chi_square_result['chi2']:.2f}")
        print(f"  p-value: {chi_square_result['p_value']:.2e}")
        print(f"  Significant: {chi_square_result['significant']}")
        print(f"  Cramer's V: {chi_square_result['cramers_v']:.4f}" if chi_square_result['cramers_v'] else "  Cramer's V: N/A")
        print(f"  Effect size: {chi_square_result['effect_size']}")
        print(f"  Historical rate: {chi_square_result['historical_rate']:.1f}%")
        print(f"  Recent rate: {chi_square_result['recent_rate']:.1f}%")
    
    if t_test_result:
        print("\nT-Test (Self-Merge Rate Stability):")
        print(f"  t-statistic: {t_test_result['t_stat']:.4f}")
        print(f"  p-value: {t_test_result['p_value']:.4f}")
        print(f"  Significant difference: {t_test_result['significant_difference']}")
        print(f"  Slope: {t_test_result['slope']:.6f}")
        print(f"  Trend p-value: {t_test_result['p_value_trend']:.4f}")
        print(f"  Stable: {t_test_result['stable']}")
        print(f"  Historical avg: {t_test_result['historical_avg']*100:.1f}%")
        print(f"  Recent avg: {t_test_result['recent_avg']*100:.1f}%")
    
    print("\nConfidence Intervals (95%):")
    if ci_results['self_merge_rate']['n'] > 0:
        ci = ci_results['self_merge_rate']['ci_95']
        print(f"  Self-merge rate: {ci_results['self_merge_rate']['value']:.1f}% [{ci[0]:.1f}%, {ci[1]:.1f}%]")
    if ci_results['zero_review_historical']['n'] > 0:
        ci = ci_results['zero_review_historical']['ci_95']
        print(f"  Zero-review (historical): {ci_results['zero_review_historical']['value']:.1f}% [{ci[0]:.1f}%, {ci[1]:.1f}%]")
    if ci_results['zero_review_recent']['n'] > 0:
        ci = ci_results['zero_review_recent']['ci_95']
        print(f"  Zero-review (recent): {ci_results['zero_review_recent']['value']:.1f}% [{ci[0]:.1f}%, {ci[1]:.1f}%]")

if __name__ == '__main__':
    main()
