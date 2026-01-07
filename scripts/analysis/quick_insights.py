#!/usr/bin/env python3
"""
Quick Insights: Low-Effort, High-Impact Analyses

Derives valuable insights from existing data with minimal computation.
"""

import json
import sys
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Any
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.utils.load_prs_with_merged_by import load_prs_with_merged_by

class QuickInsights:
    """Generate quick insights from existing data."""
    
    def __init__(self, data_dir: Path):
        """Initialize."""
        self.data_dir = data_dir
        self.maintainers = {
            'laanwj', 'sipa', 'maflcko', 'fanquake', 'hebasto', 'jnewbery',
            'ryanofsky', 'achow101', 'theuni', 'jonasschnelli', 'Sjors',
            'promag', 'instagibbs', 'TheBlueMatt', 'jonatack', 'gmaxwell',
            'gavinandresen', 'petertodd', 'luke-jr', 'glozow'
        }
    
    def load_prs(self) -> List[Dict[str, Any]]:
        """Load PRs with merged_by data."""
        prs_file = self.data_dir / 'github' / 'prs_raw.jsonl'
        mapping_file = self.data_dir / 'github' / 'merged_by_mapping.jsonl'
        return load_prs_with_merged_by(prs_file, mapping_file if mapping_file.exists() else None)
    
    def analyze_self_merge_correlations(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """What correlates with self-merge?"""
        print("Analyzing self-merge correlations...")
        
        maintainer_merged = [p for p in prs 
                             if p.get('merged', False) and 
                             (p.get('author') or '').lower() in [m.lower() for m in self.maintainers]]
        
        self_merged = []
        other_merged = []
        
        for pr in maintainer_merged:
            author = (pr.get('author') or '').lower()
            merged_by = (pr.get('merged_by') or '').lower()
            is_self = merged_by and author and merged_by == author
            
            if is_self:
                self_merged.append(pr)
            else:
                other_merged.append(pr)
        
        # Compare metrics
        def avg_metric(prs, metric_func):
            if not prs:
                return 0
            return sum(metric_func(p) for p in prs) / len(prs)
        
        results = {
            'zero_review_rate': {
                'self_merge': avg_metric(self_merged, lambda p: 1 if len(p.get('reviews', [])) == 0 else 0),
                'other_merge': avg_metric(other_merged, lambda p: 1 if len(p.get('reviews', [])) == 0 else 0)
            },
            'avg_review_count': {
                'self_merge': avg_metric(self_merged, lambda p: len(p.get('reviews', []))),
                'other_merge': avg_metric(other_merged, lambda p: len(p.get('reviews', [])))
            },
            'avg_time_to_merge_days': {
                'self_merge': self._avg_time_to_merge(self_merged),
                'other_merge': self._avg_time_to_merge(other_merged)
            },
            'avg_files_changed': {
                'self_merge': avg_metric(self_merged, lambda p: len(p.get('files', []))),
                'other_merge': avg_metric(other_merged, lambda p: len(p.get('files', [])))
            }
        }
        
        return results
    
    def _avg_time_to_merge(self, prs: List[Dict[str, Any]]) -> float:
        """Calculate average time to merge in days."""
        times = []
        for pr in prs:
            created = pr.get('created_at')
            merged = pr.get('merged_at')
            if created and merged:
                try:
                    created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    merged_dt = datetime.fromisoformat(merged.replace('Z', '+00:00'))
                    days = (merged_dt - created_dt).total_seconds() / 86400
                    if days >= 0:
                        times.append(days)
                except:
                    pass
        return sum(times) / len(times) if times else 0
    
    def analyze_maintainer_outliers(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Identify outlier maintainers (extremes in behavior)."""
        print("Analyzing maintainer outliers...")
        
        maintainer_stats = defaultdict(lambda: {
            'total_merged': 0,
            'self_merged': 0,
            'zero_review_self_merged': 0,
            'total_merges_by_others': 0,
            'avg_reviews': 0,
            'review_counts': []
        })
        
        for pr in prs:
            if not pr.get('merged', False):
                continue
            
            author = (pr.get('author') or '').lower()
            merged_by = (pr.get('merged_by') or '').lower()
            
            if author in [m.lower() for m in self.maintainers]:
                maintainer_stats[author]['total_merged'] += 1
                reviews = pr.get('reviews', [])
                maintainer_stats[author]['review_counts'].append(len(reviews))
                
                if merged_by and author and merged_by == author:
                    maintainer_stats[author]['self_merged'] += 1
                    if len(reviews) == 0:
                        maintainer_stats[author]['zero_review_self_merged'] += 1
                else:
                    maintainer_stats[author]['total_merges_by_others'] += 1
        
        # Calculate rates and identify outliers
        outliers = {
            'highest_self_merge': [],
            'lowest_self_merge': [],
            'highest_zero_review_self_merge': [],
            'most_merged_by_others': []
        }
        
        for maintainer, stats in maintainer_stats.items():
            if stats['total_merged'] < 50:  # Skip low-volume maintainers
                continue
            
            self_merge_rate = stats['self_merged'] / stats['total_merged'] if stats['total_merged'] > 0 else 0
            zero_review_rate = stats['zero_review_self_merged'] / stats['self_merged'] if stats['self_merged'] > 0 else 0
            avg_reviews = sum(stats['review_counts']) / len(stats['review_counts']) if stats['review_counts'] else 0
            
            outliers['highest_self_merge'].append({
                'maintainer': maintainer,
                'rate': self_merge_rate,
                'count': stats['self_merged'],
                'total': stats['total_merged']
            })
            
            outliers['highest_zero_review_self_merge'].append({
                'maintainer': maintainer,
                'rate': zero_review_rate,
                'count': stats['zero_review_self_merged'],
                'self_merged': stats['self_merged']
            })
            
            outliers['most_merged_by_others'].append({
                'maintainer': maintainer,
                'count': stats['total_merges_by_others'],
                'total': stats['total_merged']
            })
        
        # Sort and get top/bottom
        outliers['highest_self_merge'].sort(key=lambda x: x['rate'], reverse=True)
        outliers['lowest_self_merge'] = sorted(outliers['highest_self_merge'], key=lambda x: x['rate'])[:10]
        outliers['highest_self_merge'] = outliers['highest_self_merge'][:10]
        outliers['highest_zero_review_self_merge'].sort(key=lambda x: x['rate'], reverse=True)
        outliers['highest_zero_review_self_merge'] = outliers['highest_zero_review_self_merge'][:10]
        outliers['most_merged_by_others'].sort(key=lambda x: x['count'], reverse=True)
        outliers['most_merged_by_others'] = outliers['most_merged_by_others'][:10]
        
        return outliers
    
    def analyze_pr_success_factors(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """What factors predict PR merge success?"""
        print("Analyzing PR success factors...")
        
        maintainer_prs = [p for p in prs 
                         if (p.get('author') or '').lower() in [m.lower() for m in self.maintainers]]
        non_maintainer_prs = [p for p in prs 
                             if (p.get('author') or '').lower() not in [m.lower() for m in self.maintainers]]
        
        def analyze_group(group_prs, group_name):
            merged = [p for p in group_prs if p.get('merged', False)]
            not_merged = [p for p in group_prs if not p.get('merged', False)]
            
            def avg_reviews(prs):
                if not prs:
                    return 0
                return sum(len(p.get('reviews', [])) for p in prs) / len(prs)
            
            def avg_files(prs):
                if not prs:
                    return 0
                return sum(len(p.get('files', [])) for p in prs) / len(prs)
            
            def has_funding_mention(prs):
                if not prs:
                    return 0
                funding_keywords = ['funding', 'grant', 'sponsor', 'donation', 'salary', 'corporate']
                count = 0
                for pr in prs:
                    body = (pr.get('body') or '').lower()
                    if any(kw in body for kw in funding_keywords):
                        count += 1
                return count / len(prs)
            
            return {
                'merge_rate': len(merged) / len(group_prs) if group_prs else 0,
                'avg_reviews_merged': avg_reviews(merged),
                'avg_reviews_not_merged': avg_reviews(not_merged),
                'avg_files_merged': avg_files(merged),
                'avg_files_not_merged': avg_files(not_merged),
                'funding_mention_rate_merged': has_funding_mention(merged),
                'funding_mention_rate_not_merged': has_funding_mention(not_merged)
            }
        
        return {
            'maintainer': analyze_group(maintainer_prs, 'maintainer'),
            'non_maintainer': analyze_group(non_maintainer_prs, 'non_maintainer')
        }
    
    def analyze_temporal_anomalies(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Identify years with unusual patterns."""
        print("Analyzing temporal anomalies...")
        
        year_stats = defaultdict(lambda: {
            'total_prs': 0,
            'merged': 0,
            'self_merged': 0,
            'zero_review_merged': 0,
            'maintainer_prs': 0
        })
        
        for pr in prs:
            if not pr.get('merged_at'):
                continue
            
            try:
                year = datetime.fromisoformat(pr['merged_at'].replace('Z', '+00:00')).year
            except:
                continue
            
            year_stats[year]['total_prs'] += 1
            if pr.get('merged', False):
                year_stats[year]['merged'] += 1
                
                author = (pr.get('author') or '').lower()
                merged_by = (pr.get('merged_by') or '').lower()
                
                if author in [m.lower() for m in self.maintainers]:
                    year_stats[year]['maintainer_prs'] += 1
                    if merged_by and author and merged_by == author:
                        year_stats[year]['self_merged'] += 1
                
                if len(pr.get('reviews', [])) == 0:
                    year_stats[year]['zero_review_merged'] += 1
        
        # Calculate rates and find anomalies
        results = {}
        for year in sorted(year_stats.keys()):
            stats = year_stats[year]
            if stats['total_prs'] < 50:  # Skip years with too few PRs
                continue
            
            results[year] = {
                'merge_rate': stats['merged'] / stats['total_prs'] if stats['total_prs'] > 0 else 0,
                'self_merge_rate': stats['self_merged'] / stats['maintainer_prs'] if stats['maintainer_prs'] > 0 else 0,
                'zero_review_rate': stats['zero_review_merged'] / stats['merged'] if stats['merged'] > 0 else 0,
                'total_prs': stats['total_prs']
            }
        
        # Find years with highest/lowest rates
        if results:
            highest_self_merge = max(results.items(), key=lambda x: x[1]['self_merge_rate'])
            lowest_self_merge = min(results.items(), key=lambda x: x[1]['self_merge_rate'])
            highest_zero_review = max(results.items(), key=lambda x: x[1]['zero_review_rate'])
            lowest_zero_review = min(results.items(), key=lambda x: x[1]['zero_review_rate'])
        
            return {
                'yearly_rates': results,
                'anomalies': {
                    'highest_self_merge_year': highest_self_merge,
                    'lowest_self_merge_year': lowest_self_merge,
                    'highest_zero_review_year': highest_zero_review,
                    'lowest_zero_review_year': lowest_zero_review
                }
            }
        
        return {'yearly_rates': results, 'anomalies': {}}
    
    def analyze_response_time_bias(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Do maintainers get faster responses?"""
        print("Analyzing response time bias...")
        
        maintainer_prs = []
        non_maintainer_prs = []
        
        for pr in prs:
            author = (pr.get('author') or '').lower()
            is_maintainer = author in [m.lower() for m in self.maintainers]
            
            # Get first response time
            created = pr.get('created_at')
            reviews = pr.get('reviews', [])
            comments = pr.get('comments', [])
            
            first_response = None
            for review in reviews:
                resp_time = review.get('submitted_at') or review.get('created_at')
                if resp_time and (not first_response or resp_time < first_response):
                    first_response = resp_time
            
            for comment in comments:
                resp_time = comment.get('created_at')
                if resp_time and (not first_response or resp_time < first_response):
                    first_response = resp_time
            
            if created and first_response:
                try:
                    created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    resp_dt = datetime.fromisoformat(first_response.replace('Z', '+00:00'))
                    hours = (resp_dt - created_dt).total_seconds() / 3600
                    if hours >= 0 and hours < 10000:  # Reasonable range
                        if is_maintainer:
                            maintainer_prs.append(hours)
                        else:
                            non_maintainer_prs.append(hours)
                except:
                    pass
        
        def stats(hours_list):
            if not hours_list:
                return {}
            return {
                'avg': sum(hours_list) / len(hours_list),
                'median': sorted(hours_list)[len(hours_list) // 2] if hours_list else 0,
                'count': len(hours_list)
            }
        
        return {
            'maintainer': stats(maintainer_prs),
            'non_maintainer': stats(non_maintainer_prs),
            'ratio': stats(maintainer_prs).get('avg', 0) / stats(non_maintainer_prs).get('avg', 1) if non_maintainer_prs else 0
        }
    
    def run_all_analyses(self) -> Dict[str, Any]:
        """Run all quick insight analyses."""
        print("="*80)
        print("QUICK INSIGHTS ANALYSIS")
        print("="*80)
        print()
        
        prs = self.load_prs()
        print(f"Loaded {len(prs):,} PRs")
        print()
        
        results = {
            'self_merge_correlations': self.analyze_self_merge_correlations(prs),
            'maintainer_outliers': self.analyze_maintainer_outliers(prs),
            'pr_success_factors': self.analyze_pr_success_factors(prs),
            'temporal_anomalies': self.analyze_temporal_anomalies(prs),
            'response_time_bias': self.analyze_response_time_bias(prs),
            'analysis_date': datetime.now().isoformat()
        }
        
        return results
    
    def print_results(self, results: Dict[str, Any]):
        """Print results."""
        print("="*80)
        print("QUICK INSIGHTS RESULTS")
        print("="*80)
        print()
        
        # Self-merge correlations
        print("SELF-MERGE CORRELATIONS")
        print("-" * 80)
        corr = results['self_merge_correlations']
        print("Zero-review rate:")
        print(f"  Self-merge: {corr['zero_review_rate']['self_merge']*100:.1f}%")
        print(f"  Other-merge: {corr['zero_review_rate']['other_merge']*100:.1f}%")
        print()
        print("Average review count:")
        print(f"  Self-merge: {corr['avg_review_count']['self_merge']:.1f}")
        print(f"  Other-merge: {corr['avg_review_count']['other_merge']:.1f}")
        print()
        print("Average time to merge:")
        print(f"  Self-merge: {corr['avg_time_to_merge_days']['self_merge']:.1f} days")
        print(f"  Other-merge: {corr['avg_time_to_merge_days']['other_merge']:.1f} days")
        print()
        
        # Maintainer outliers
        print("MAINTAINER OUTLIERS")
        print("-" * 80)
        outliers = results['maintainer_outliers']
        print("Highest self-merge rates:")
        for m in outliers['highest_self_merge'][:5]:
            print(f"  {m['maintainer']}: {m['rate']*100:.1f}% ({m['count']}/{m['total']})")
        print()
        print("Lowest self-merge rates (never self-merge):")
        for m in outliers['lowest_self_merge'][:5]:
            print(f"  {m['maintainer']}: {m['rate']*100:.1f}% ({m['count']}/{m['total']})")
        print()
        print("Highest zero-review self-merge rates:")
        for m in outliers['highest_zero_review_self_merge'][:5]:
            print(f"  {m['maintainer']}: {m['rate']*100:.1f}% ({m['count']}/{m['self_merged']} self-merges)")
        print()
        
        # PR success factors
        print("PR SUCCESS FACTORS")
        print("-" * 80)
        success = results['pr_success_factors']
        print("Maintainer PRs:")
        print(f"  Merge rate: {success['maintainer']['merge_rate']*100:.1f}%")
        print(f"  Avg reviews (merged): {success['maintainer']['avg_reviews_merged']:.1f}")
        print(f"  Avg reviews (not merged): {success['maintainer']['avg_reviews_not_merged']:.1f}")
        print()
        print("Non-maintainer PRs:")
        print(f"  Merge rate: {success['non_maintainer']['merge_rate']*100:.1f}%")
        print(f"  Avg reviews (merged): {success['non_maintainer']['avg_reviews_merged']:.1f}")
        print(f"  Avg reviews (not merged): {success['non_maintainer']['avg_reviews_not_merged']:.1f}")
        print()
        
        # Temporal anomalies
        print("TEMPORAL ANOMALIES")
        print("-" * 80)
        temporal = results['temporal_anomalies']
        if temporal.get('anomalies'):
            anom = temporal['anomalies']
            if 'highest_self_merge_year' in anom:
                year, data = anom['highest_self_merge_year']
                print(f"Highest self-merge year: {year} ({data['self_merge_rate']*100:.1f}%)")
            if 'lowest_zero_review_year' in anom:
                year, data = anom['lowest_zero_review_year']
                print(f"Lowest zero-review year: {year} ({data['zero_review_rate']*100:.1f}%)")
        print()
        
        # Response time bias
        print("RESPONSE TIME BIAS")
        print("-" * 80)
        bias = results['response_time_bias']
        print(f"Maintainer PRs: {bias['maintainer'].get('avg', 0):.1f} hours avg ({bias['maintainer'].get('count', 0):,} PRs)")
        print(f"Non-maintainer PRs: {bias['non_maintainer'].get('avg', 0):.1f} hours avg ({bias['non_maintainer'].get('count', 0):,} PRs)")
        print(f"Ratio: {bias['ratio']:.2f}x (maintainer/non-maintainer)")
        print()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate quick insights from data')
    parser.add_argument('--data-dir', type=Path, default=Path(__file__).parent.parent.parent / 'data',
                       help='Data directory')
    parser.add_argument('--output', type=Path, default=Path(__file__).parent.parent.parent / 'findings' / 'quick_insights.json',
                       help='Output JSON file')
    
    args = parser.parse_args()
    
    analyzer = QuickInsights(args.data_dir)
    results = analyzer.run_all_analyses()
    analyzer.print_results(results)
    
    # Save results
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: {args.output}")


if __name__ == '__main__':
    main()
