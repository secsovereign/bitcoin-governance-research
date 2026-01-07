#!/usr/bin/env python3
"""
Comprehensive Temporal Analysis

Analyzes patterns over time, including:
- Maintainer status changes over time
- Behavioral changes by era/cohort
- Temporal patterns in self-merge, reviews, etc.
- Who was maintainer when each PR was merged
"""

import json
import sys
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Any, Set, Tuple
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.utils.load_prs_with_merged_by import load_prs_with_merged_by

class TemporalAnalyzer:
    """Comprehensive temporal analysis."""
    
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
    
    def analyze_temporal_self_merge_patterns(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze how self-merge patterns changed over time."""
        print("Analyzing temporal self-merge patterns...")
        
        # Group by year
        by_year = defaultdict(lambda: {
            'total_maintainer_merged': 0,
            'self_merged': 0,
            'other_merged': 0,
            'zero_review_self_merged': 0,
            'zero_review_other_merged': 0
        })
        
        for pr in prs:
            if not pr.get('merged', False):
                continue
            
            author = (pr.get('author') or '').lower()
            merged_by = (pr.get('merged_by') or '').lower()
            
            if author not in [m.lower() for m in self.maintainers]:
                continue
            
            # Get year
            merged_at = pr.get('merged_at')
            if not merged_at:
                continue
            
            try:
                year = datetime.fromisoformat(merged_at.replace('Z', '+00:00')).year
            except:
                continue
            
            by_year[year]['total_maintainer_merged'] += 1
            
            reviews = pr.get('reviews', [])
            is_self_merge = merged_by and author and merged_by == author
            
            if is_self_merge:
                by_year[year]['self_merged'] += 1
                if len(reviews) == 0:
                    by_year[year]['zero_review_self_merged'] += 1
            else:
                by_year[year]['other_merged'] += 1
                if len(reviews) == 0:
                    by_year[year]['zero_review_other_merged'] += 1
        
        # Calculate rates
        results = {}
        for year in sorted(by_year.keys()):
            stats = by_year[year]
            if stats['total_maintainer_merged'] < 10:  # Skip years with too few PRs
                continue
            
            results[year] = {
                'total': stats['total_maintainer_merged'],
                'self_merge_rate': stats['self_merged'] / stats['total_maintainer_merged'] if stats['total_maintainer_merged'] > 0 else 0,
                'zero_review_self_merge_rate': stats['zero_review_self_merged'] / stats['self_merged'] if stats['self_merged'] > 0 else 0,
                'zero_review_other_merge_rate': stats['zero_review_other_merged'] / stats['other_merged'] if stats['other_merged'] > 0 else 0,
                'avg_reviews': sum(len(pr.get('reviews', [])) for pr in prs 
                                 if pr.get('merged', False) and 
                                 (pr.get('author') or '').lower() in [m.lower() for m in self.maintainers] and
                                 pr.get('merged_at') and
                                 datetime.fromisoformat(pr['merged_at'].replace('Z', '+00:00')).year == year) / stats['total_maintainer_merged'] if stats['total_maintainer_merged'] > 0 else 0
            }
        
        return results
    
    def analyze_maintainer_era_patterns(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze patterns by maintainer era (when they became active)."""
        print("Analyzing maintainer era patterns...")
        
        # Find first PR date for each maintainer
        first_pr_date = {}
        for pr in prs:
            author = (pr.get('author') or '').lower()
            if author in [m.lower() for m in self.maintainers]:
                created = pr.get('created_at')
                if created:
                    try:
                        created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                        if author not in first_pr_date or created_dt < first_pr_date[author]:
                            first_pr_date[author] = created_dt
                    except:
                        pass
        
        # Group into eras
        eras = {
            'early_2010s': [],  # 2010-2013
            'mid_2010s': [],    # 2014-2016
            'late_2010s': [],   # 2017-2019
            '2020s': []         # 2020+
        }
        
        for maintainer, first_date in first_pr_date.items():
            year = first_date.year
            if year <= 2013:
                eras['early_2010s'].append(maintainer)
            elif year <= 2016:
                eras['mid_2010s'].append(maintainer)
            elif year <= 2019:
                eras['late_2010s'].append(maintainer)
            else:
                eras['2020s'].append(maintainer)
        
        # Analyze behavior by era
        era_stats = {}
        for era_name, members in eras.items():
            if not members:
                continue
            
            # Get PRs from this era's maintainers
            era_prs = [p for p in prs 
                      if (p.get('author') or '').lower() in [m.lower() for m in members] and
                      p.get('merged', False)]
            
            self_merged = [p for p in era_prs 
                          if (p.get('merged_by') or '').lower() == (p.get('author') or '').lower()]
            
            era_stats[era_name] = {
                'members': members,
                'total_prs': len(era_prs),
                'self_merge_rate': len(self_merged) / len(era_prs) if era_prs else 0,
                'zero_review_rate': sum(1 for p in era_prs if len(p.get('reviews', [])) == 0) / len(era_prs) if era_prs else 0,
                'avg_reviews': sum(len(p.get('reviews', [])) for p in era_prs) / len(era_prs) if era_prs else 0,
                'avg_time_to_merge': self._avg_time_to_merge(era_prs)
            }
        
        return era_stats
    
    def analyze_quarterly_trends(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze quarterly trends in key metrics."""
        print("Analyzing quarterly trends...")
        
        by_quarter = defaultdict(lambda: {
            'total': 0,
            'self_merged': 0,
            'zero_review': 0,
            'avg_reviews': 0,
            'review_counts': []
        })
        
        for pr in prs:
            if not pr.get('merged', False):
                continue
            
            author = (pr.get('author') or '').lower()
            if author not in [m.lower() for m in self.maintainers]:
                continue
            
            merged_at = pr.get('merged_at')
            if not merged_at:
                continue
            
            try:
                merged_dt = datetime.fromisoformat(merged_at.replace('Z', '+00:00'))
                quarter = f"{merged_dt.year}-Q{(merged_dt.month-1)//3 + 1}"
            except:
                continue
            
            by_quarter[quarter]['total'] += 1
            reviews = pr.get('reviews', [])
            by_quarter[quarter]['review_counts'].append(len(reviews))
            
            merged_by = (pr.get('merged_by') or '').lower()
            if merged_by and author and merged_by == author:
                by_quarter[quarter]['self_merged'] += 1
            
            if len(reviews) == 0:
                by_quarter[quarter]['zero_review'] += 1
        
        # Calculate rates
        results = {}
        for quarter in sorted(by_quarter.keys()):
            stats = by_quarter[quarter]
            if stats['total'] < 5:  # Skip quarters with too few PRs
                continue
            
            results[quarter] = {
                'total': stats['total'],
                'self_merge_rate': stats['self_merged'] / stats['total'] if stats['total'] > 0 else 0,
                'zero_review_rate': stats['zero_review'] / stats['total'] if stats['total'] > 0 else 0,
                'avg_reviews': sum(stats['review_counts']) / len(stats['review_counts']) if stats['review_counts'] else 0
            }
        
        return results
    
    def analyze_maintainer_lifecycle(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze maintainer lifecycle: first PR to maintainer status patterns."""
        print("Analyzing maintainer lifecycle...")
        
        # Find first PR for each maintainer
        first_prs = {}
        for pr in prs:
            author = (pr.get('author') or '').lower()
            if author in [m.lower() for m in self.maintainers]:
                created = pr.get('created_at')
                if created:
                    try:
                        created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                        if author not in first_prs or created_dt < first_prs[author]['date']:
                            first_prs[author] = {
                                'date': created_dt,
                                'pr_number': pr.get('number'),
                                'merged': pr.get('merged', False)
                            }
                    except:
                        pass
        
        # Analyze patterns
        lifecycle_stats = {
            'first_prs': {},
            'time_to_first_merge': [],
            'first_pr_merged_rate': 0
        }
        
        for maintainer, first_pr in first_prs.items():
            lifecycle_stats['first_prs'][maintainer] = {
                'date': first_pr['date'].isoformat(),
                'pr_number': first_pr['pr_number'],
                'merged': first_pr['merged']
            }
            
            if first_pr['merged']:
                lifecycle_stats['time_to_first_merge'].append(0)  # First PR was merged
        
        if lifecycle_stats['time_to_first_merge']:
            lifecycle_stats['first_pr_merged_rate'] = len(lifecycle_stats['time_to_first_merge']) / len(first_prs)
        
        return lifecycle_stats
    
    def analyze_behavioral_changes_over_time(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze how individual maintainer behavior changed over time."""
        print("Analyzing behavioral changes over time...")
        
        # Group PRs by maintainer and time period
        maintainer_periods = defaultdict(lambda: defaultdict(list))
        
        for pr in prs:
            if not pr.get('merged', False):
                continue
            
            author = (pr.get('author') or '').lower()
            if author not in [m.lower() for m in self.maintainers]:
                continue
            
            merged_at = pr.get('merged_at')
            if not merged_at:
                continue
            
            try:
                merged_dt = datetime.fromisoformat(merged_at.replace('Z', '+00:00'))
                year = merged_dt.year
                
                # Group into periods
                if year <= 2015:
                    period = '2010-2015'
                elif year <= 2020:
                    period = '2016-2020'
                else:
                    period = '2021-2025'
                
                maintainer_periods[author][period].append(pr)
            except:
                pass
        
        # Analyze changes
        behavioral_changes = {}
        for maintainer, periods in maintainer_periods.items():
            if len(periods) < 2:  # Need at least 2 periods to see change
                continue
            
            changes = {}
            for period, period_prs in periods.items():
                if len(period_prs) < 10:  # Need enough PRs
                    continue
                
                self_merged = [p for p in period_prs 
                              if (p.get('merged_by') or '').lower() == maintainer]
                
                changes[period] = {
                    'total': len(period_prs),
                    'self_merge_rate': len(self_merged) / len(period_prs) if period_prs else 0,
                    'zero_review_rate': sum(1 for p in period_prs if len(p.get('reviews', [])) == 0) / len(period_prs) if period_prs else 0,
                    'avg_reviews': sum(len(p.get('reviews', [])) for p in period_prs) / len(period_prs) if period_prs else 0
                }
            
            if len(changes) >= 2:
                behavioral_changes[maintainer] = changes
        
        return behavioral_changes
    
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
    
    def run_all_analyses(self) -> Dict[str, Any]:
        """Run all temporal analyses."""
        print("="*80)
        print("COMPREHENSIVE TEMPORAL ANALYSIS")
        print("="*80)
        print()
        
        prs = self.load_prs()
        print(f"Loaded {len(prs):,} PRs")
        print()
        
        results = {
            'temporal_self_merge': self.analyze_temporal_self_merge_patterns(prs),
            'maintainer_eras': self.analyze_maintainer_era_patterns(prs),
            'quarterly_trends': self.analyze_quarterly_trends(prs),
            'maintainer_lifecycle': self.analyze_maintainer_lifecycle(prs),
            'behavioral_changes': self.analyze_behavioral_changes_over_time(prs),
            'analysis_date': datetime.now().isoformat()
        }
        
        return results
    
    def print_results(self, results: Dict[str, Any]):
        """Print results."""
        print("="*80)
        print("TEMPORAL ANALYSIS RESULTS")
        print("="*80)
        print()
        
        # Temporal self-merge patterns
        print("TEMPORAL SELF-MERGE PATTERNS")
        print("-" * 80)
        temporal = results['temporal_self_merge']
        print("Year | Total | Self-Merge Rate | Zero-Review Self-Merge | Avg Reviews")
        print("-" * 80)
        for year in sorted(temporal.keys())[-10:]:  # Last 10 years
            stats = temporal[year]
            print(f"{year} | {stats['total']:5d} | {stats['self_merge_rate']*100:6.1f}% | {stats['zero_review_self_merge_rate']*100:6.1f}% | {stats['avg_reviews']:.1f}")
        print()
        
        # Maintainer eras
        print("MAINTAINER ERA PATTERNS")
        print("-" * 80)
        eras = results['maintainer_eras']
        for era_name, stats in eras.items():
            if stats.get('total_prs', 0) > 0:
                print(f"{era_name}:")
                print(f"  Members: {len(stats['members'])}")
                print(f"  Self-merge rate: {stats['self_merge_rate']*100:.1f}%")
                print(f"  Zero-review rate: {stats['zero_review_rate']*100:.1f}%")
                print(f"  Avg reviews: {stats['avg_reviews']:.1f}")
                print()
        
        # Quarterly trends (last 8 quarters)
        print("QUARTERLY TRENDS (Last 8 Quarters)")
        print("-" * 80)
        quarterly = results['quarterly_trends']
        print("Quarter | Total | Self-Merge | Zero-Review | Avg Reviews")
        print("-" * 80)
        for quarter in sorted(quarterly.keys())[-8:]:
            stats = quarterly[quarter]
            print(f"{quarter} | {stats['total']:5d} | {stats['self_merge_rate']*100:6.1f}% | {stats['zero_review_rate']*100:6.1f}% | {stats['avg_reviews']:.1f}")
        print()
        
        # Behavioral changes
        print("BEHAVIORAL CHANGES OVER TIME (Sample)")
        print("-" * 80)
        changes = results['behavioral_changes']
        for maintainer, periods in list(changes.items())[:5]:
            print(f"{maintainer}:")
            for period, stats in periods.items():
                print(f"  {period}: {stats['self_merge_rate']*100:.1f}% self-merge, {stats['avg_reviews']:.1f} avg reviews")
            print()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Comprehensive temporal analysis')
    parser.add_argument('--data-dir', type=Path, default=Path(__file__).parent.parent.parent / 'data',
                       help='Data directory')
    parser.add_argument('--output', type=Path, default=Path(__file__).parent.parent.parent / 'findings' / 'temporal_analysis.json',
                       help='Output JSON file')
    
    args = parser.parse_args()
    
    analyzer = TemporalAnalyzer(args.data_dir)
    results = analyzer.run_all_analyses()
    analyzer.print_results(results)
    
    # Save results
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nResults saved to: {args.output}")


if __name__ == '__main__':
    main()
