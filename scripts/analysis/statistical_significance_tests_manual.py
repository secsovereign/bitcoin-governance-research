#!/usr/bin/env python3
"""
Statistical Significance Tests (Manual Calculations)

Performs chi-square tests, t-tests, and calculates effect sizes and
confidence intervals using manual calculations (no scipy required).
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

def chi_square_manual(contingency_table):
    """Manual chi-square calculation."""
    # contingency_table = [[a, b], [c, d]]
    a, b = contingency_table[0]
    c, d = contingency_table[1]
    
    n = a + b + c + d
    if n == 0:
        return None
    
    # Expected frequencies
    row1_total = a + b
    row2_total = c + d
    col1_total = a + c
    col2_total = b + d
    
    e_a = (row1_total * col1_total) / n
    e_b = (row1_total * col2_total) / n
    e_c = (row2_total * col1_total) / n
    e_d = (row2_total * col2_total) / n
    
    # Chi-square statistic
    chi2 = ((a - e_a)**2 / e_a if e_a > 0 else 0) + \
           ((b - e_b)**2 / e_b if e_b > 0 else 0) + \
           ((c - e_c)**2 / e_c if e_c > 0 else 0) + \
           ((d - e_d)**2 / e_d if e_d > 0 else 0)
    
    # Degrees of freedom = (rows - 1) * (cols - 1) = 1
    dof = 1
    
    # Approximate p-value using chi-square distribution
    # For dof=1, chi2 > 10.83 gives p < 0.001
    # chi2 > 6.63 gives p < 0.01
    # chi2 > 3.84 gives p < 0.05
    if chi2 > 10.83:
        p_value = "< 0.001"
        significant = True
    elif chi2 > 6.63:
        p_value = "< 0.01"
        significant = True
    elif chi2 > 3.84:
        p_value = "< 0.05"
        significant = True
    else:
        p_value = "> 0.05"
        significant = False
    
    # Cramer's V
    min_dim = min(2, 2)  # 2x2 table
    cramers_v = math.sqrt(chi2 / (n * (min_dim - 1))) if n > 0 and min_dim > 1 else 0.0
    
    return {
        'chi2': chi2,
        'p_value': p_value,
        'dof': dof,
        'significant': significant,
        'cramers_v': cramers_v,
        'effect_size': 'large' if cramers_v > 0.3 else 'medium' if cramers_v > 0.1 else 'small'
    }

def t_test_manual(group1, group2):
    """Manual t-test calculation (two-sample, equal variance)."""
    n1, n2 = len(group1), len(group2)
    if n1 < 2 or n2 < 2:
        return None
    
    mean1 = sum(group1) / n1
    mean2 = sum(group2) / n2
    
    var1 = sum((x - mean1)**2 for x in group1) / (n1 - 1) if n1 > 1 else 0
    var2 = sum((x - mean2)**2 for x in group2) / (n2 - 1) if n2 > 1 else 0
    
    # Pooled standard error
    pooled_se = math.sqrt((var1 / n1) + (var2 / n2))
    
    if pooled_se == 0:
        return None
    
    # t-statistic
    t_stat = (mean1 - mean2) / pooled_se
    
    # Degrees of freedom
    dof = n1 + n2 - 2
    
    # Approximate p-value
    # For large samples (dof > 30), |t| > 3.29 gives p < 0.001
    # |t| > 2.58 gives p < 0.01
    # |t| > 1.96 gives p < 0.05
    abs_t = abs(t_stat)
    if abs_t > 3.29:
        p_value = "< 0.001"
        significant = True
    elif abs_t > 2.58:
        p_value = "< 0.01"
        significant = True
    elif abs_t > 1.96:
        p_value = "< 0.05"
        significant = True
    else:
        p_value = "> 0.05"
        significant = False
    
    return {
        't_stat': t_stat,
        'p_value': p_value,
        'dof': dof,
        'significant_difference': significant,
        'mean1': mean1,
        'mean2': mean2
    }

def linear_regression_manual(x, y):
    """Manual linear regression."""
    n = len(x)
    if n < 2:
        return None
    
    sum_x = sum(x)
    sum_y = sum(y)
    sum_xy = sum(x[i] * y[i] for i in range(n))
    sum_x2 = sum(x[i]**2 for i in range(n))
    
    # Slope
    denominator = n * sum_x2 - sum_x**2
    if denominator == 0:
        return None
    
    slope = (n * sum_xy - sum_x * sum_y) / denominator
    
    # Intercept
    intercept = (sum_y - slope * sum_x) / n
    
    # R-squared
    mean_y = sum_y / n
    ss_tot = sum((y[i] - mean_y)**2 for i in range(n))
    ss_res = sum((y[i] - (slope * x[i] + intercept))**2 for i in range(n))
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
    
    # Approximate p-value for slope
    # Simplified: if |slope| is large relative to data range, likely significant
    # This is a rough approximation
    x_range = max(x) - min(x) if x else 1
    y_range = max(y) - min(y) if y else 1
    slope_normalized = abs(slope) * x_range / y_range if y_range > 0 else 0
    
    if slope_normalized > 0.5:
        p_value_trend = "< 0.05"
        significant_trend = True
    else:
        p_value_trend = "> 0.05"
        significant_trend = False
    
    return {
        'slope': slope,
        'intercept': intercept,
        'r_squared': r_squared,
        'p_value_trend': p_value_trend,
        'significant_trend': significant_trend
    }

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
    
    result = chi_square_manual(contingency_table)
    if result:
        result['contingency_table'] = contingency_table
        result['historical_rate'] = (historical_zero / historical_total * 100) if historical_total > 0 else 0
        result['recent_rate'] = (recent_zero / recent_total * 100) if recent_total > 0 else 0
    
    return result

def t_test_self_merge_stability(prs):
    """T-test for self-merge rate stability over time."""
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
    t_result = t_test_manual(historical_rates, recent_rates)
    
    # Linear regression for trend
    all_years = historical_years + recent_years
    all_rates = []
    for year in all_years:
        if yearly_totals[year] > 0:
            rate = yearly_rates[year] / yearly_totals[year]
            all_rates.append(rate)
    
    if len(all_rates) >= 2:
        x = list(range(len(all_rates)))
        reg_result = linear_regression_manual(x, all_rates)
    else:
        reg_result = None
    
    if t_result:
        result = t_result.copy()
        result['historical_avg'] = sum(historical_rates) / len(historical_rates) if historical_rates else 0
        result['recent_avg'] = sum(recent_rates) / len(recent_rates) if recent_rates else 0
        result['stable'] = not result['significant_difference']
        
        if reg_result:
            result['slope'] = reg_result['slope']
            result['p_value_trend'] = reg_result['p_value_trend']
            result['declining'] = reg_result['slope'] < 0 and reg_result['significant_trend']
        else:
            result['slope'] = 0.0
            result['p_value_trend'] = "> 0.05"
            result['declining'] = False
        
        return result
    
    return None

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
    print("STATISTICAL SIGNIFICANCE TESTS (Manual Calculations)")
    print("="*80)
    print()
    
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
        'method': 'manual_calculations',
        'note': 'Calculations performed manually (no scipy required). p-values are approximations.',
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
        print(f"  p-value: {chi_square_result['p_value']}")
        print(f"  Significant: {chi_square_result['significant']}")
        print(f"  Cramer's V: {chi_square_result['cramers_v']:.4f}")
        print(f"  Effect size: {chi_square_result['effect_size']}")
        print(f"  Historical rate: {chi_square_result['historical_rate']:.1f}%")
        print(f"  Recent rate: {chi_square_result['recent_rate']:.1f}%")
    
    if t_test_result:
        print("\nT-Test (Self-Merge Rate Stability):")
        print(f"  t-statistic: {t_test_result['t_stat']:.4f}")
        print(f"  p-value: {t_test_result['p_value']}")
        print(f"  Significant difference: {t_test_result['significant_difference']}")
        print(f"  Stable: {t_test_result['stable']}")
        if 'slope' in t_test_result:
            print(f"  Slope: {t_test_result['slope']:.6f}")
            print(f"  Trend p-value: {t_test_result['p_value_trend']}")
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
