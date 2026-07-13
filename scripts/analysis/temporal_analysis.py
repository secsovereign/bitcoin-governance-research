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
from typing import Dict, List, Any, Set, Tuple, Optional
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.utils.load_prs_with_merged_by import load_prs_with_merged_by
from src.utils.maintainers import load_maintainer_login_set

class TemporalAnalyzer:
    """Comprehensive temporal analysis."""
    
    def __init__(self, data_dir: Path):
        """Initialize."""
        self.data_dir = data_dir
        self.maintainers = load_maintainer_login_set() or {
            'laanwj', 'sipa', 'maflcko', 'fanquake', 'hebasto', 'jnewbery',
            'ryanofsky', 'achow101', 'theuni', 'jonasschnelli', 'sjors',
            'promag', 'instagibbs', 'thebluematt', 'jonatack', 'gmaxwell',
            'gavinandresen', 'petertodd', 'luke-jr', 'glozow', 'thecharlatan'
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
    
    def _get_period(self, year: int) -> str:
        """Get period name for a year."""
        if 2012 <= year <= 2020:
            return 'historical'
        elif 2021 <= year <= 2025:
            return 'recent'
        return 'other'
    
    def _calculate_time_to_merge(self, pr: Dict[str, Any]) -> Optional[float]:
        """Calculate time to merge in days."""
        created = pr.get('created_at')
        merged = pr.get('merged_at')
        if not created or not merged:
            return None
        try:
            created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
            merged_dt = datetime.fromisoformat(merged.replace('Z', '+00:00'))
            days = (merged_dt - created_dt).total_seconds() / 86400
            return days if days >= 0 else None
        except:
            return None
    
    def _classify_pr_importance(self, pr: Dict[str, Any]) -> str:
        """Classify PR by importance level."""
        additions = pr.get('additions', 0)
        deletions = pr.get('deletions', 0)
        total_changes = additions + deletions
        files = pr.get('files', [])
        has_consensus = any('consensus' in f.get('filename', '').lower() or 
                           'validation' in f.get('filename', '').lower() or
                           'script' in f.get('filename', '').lower()
                           for f in files)
        
        if total_changes < 10:
            return 'trivial'
        elif total_changes < 50:
            return 'low'
        elif total_changes < 200:
            return 'normal'
        elif total_changes < 500:
            return 'high'
        elif total_changes >= 500 or has_consensus:
            return 'critical'
        return 'normal'
    
    def _calculate_review_score(self, pr: Dict[str, Any]) -> float:
        """Calculate quality-weighted review score."""
        reviews = pr.get('reviews', [])
        if not reviews:
            return 0.0
        score = 0.0
        for review in reviews:
            body = (review.get('body') or '').lower()
            if 'ack' in body or 'lgtm' in body:
                score += 0.3
            else:
                score += 1.0
        return score
    
    def _is_zero_review(self, pr: Dict[str, Any], threshold: float = 0.5) -> bool:
        """Check if PR has zero meaningful review."""
        score = self._calculate_review_score(pr)
        return score < threshold
    
    def analyze_speed_hack_temporal(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze time-to-merge for self-merge vs other-merge by period."""
        print("Analyzing speed hack temporal patterns...")
        
        maintainer_merged = [p for p in prs 
                            if p.get('merged', False) and 
                            (p.get('author') or '').lower() in [m.lower() for m in self.maintainers]]
        
        results = {
            'historical': {'self_merge': [], 'other_merge': []},
            'recent': {'self_merge': [], 'other_merge': []},
            'all_time': {'self_merge': [], 'other_merge': []}
        }
        
        for pr in maintainer_merged:
            merged_at = pr.get('merged_at')
            if not merged_at:
                continue
            
            try:
                year = datetime.fromisoformat(merged_at.replace('Z', '+00:00')).year
                period = self._get_period(year)
            except:
                continue
            
            time_to_merge = self._calculate_time_to_merge(pr)
            if time_to_merge is None:
                continue
            
            author = (pr.get('author') or '').lower()
            merged_by = (pr.get('merged_by') or '').lower()
            is_self = merged_by and author and merged_by == author
            
            if is_self:
                results['all_time']['self_merge'].append(time_to_merge)
                if period in results:
                    results[period]['self_merge'].append(time_to_merge)
            else:
                results['all_time']['other_merge'].append(time_to_merge)
                if period in results:
                    results[period]['other_merge'].append(time_to_merge)
        
        def avg(lst):
            return sum(lst) / len(lst) if lst else 0
        
        output = {}
        for period_name, period_data in results.items():
            if not period_data['self_merge'] and not period_data['other_merge']:
                continue
            
            output[period_name] = {
                'self_merge_avg_days': avg(period_data['self_merge']),
                'other_merge_avg_days': avg(period_data['other_merge']),
                'self_merge_count': len(period_data['self_merge']),
                'other_merge_count': len(period_data['other_merge']),
                'speed_ratio': (avg(period_data['other_merge']) / avg(period_data['self_merge']) 
                               if avg(period_data['self_merge']) > 0 else 0)
            }
        
        return output
    
    def analyze_pr_importance_temporal(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze PR importance patterns by period."""
        print("Analyzing PR importance temporal patterns...")
        
        maintainer_merged = [p for p in prs 
                            if p.get('merged', False) and 
                            (p.get('author') or '').lower() in [m.lower() for m in self.maintainers]]
        
        results = defaultdict(lambda: defaultdict(lambda: {'total': 0, 'zero_review': 0, 'self_merge': 0}))
        
        for pr in maintainer_merged:
            merged_at = pr.get('merged_at')
            if not merged_at:
                continue
            
            try:
                year = datetime.fromisoformat(merged_at.replace('Z', '+00:00')).year
                period = self._get_period(year)
            except:
                continue
            
            importance = self._classify_pr_importance(pr)
            is_zero = self._is_zero_review(pr)
            author = (pr.get('author') or '').lower()
            merged_by = (pr.get('merged_by') or '').lower()
            is_self = merged_by and author and merged_by == author
            
            results[period][importance]['total'] += 1
            if is_zero:
                results[period][importance]['zero_review'] += 1
            if is_self:
                results[period][importance]['self_merge'] += 1
        
        output = {}
        for period, importance_data in results.items():
            output[period] = {}
            for importance, stats in importance_data.items():
                if stats['total'] == 0:
                    continue
                output[period][importance] = {
                    'total': stats['total'],
                    'zero_review_count': stats['zero_review'],
                    'zero_review_rate': stats['zero_review'] / stats['total'],
                    'self_merge_count': stats['self_merge'],
                    'self_merge_rate': stats['self_merge'] / stats['total']
                }
        
        return output
    
    def analyze_power_concentration_temporal(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze power concentration metrics by period."""
        print("Analyzing power concentration temporal patterns...")
        
        maintainer_merged = [p for p in prs 
                            if p.get('merged', False) and 
                            (p.get('author') or '').lower() in [m.lower() for m in self.maintainers]]
        
        results = defaultdict(lambda: defaultdict(int))
        
        for pr in maintainer_merged:
            merged_at = pr.get('merged_at')
            if not merged_at:
                continue
            
            try:
                year = datetime.fromisoformat(merged_at.replace('Z', '+00:00')).year
                period = self._get_period(year)
            except:
                continue
            
            merged_by = (pr.get('merged_by') or '').lower()
            if merged_by:
                results[period][merged_by] += 1
        
        output = {}
        for period, merger_counts in results.items():
            if not merger_counts:
                continue
            
            total_merges = sum(merger_counts.values())
            sorted_mergers = sorted(merger_counts.items(), key=lambda x: x[1], reverse=True)
            
            top3_count = sum(count for _, count in sorted_mergers[:3])
            top10_count = sum(count for _, count in sorted_mergers[:10])
            
            n = len(sorted_mergers)
            if n == 0:
                continue
            
            cumsum = 0
            gini_sum = 0
            for i, (_, count) in enumerate(sorted_mergers):
                cumsum += count
                gini_sum += (i + 1) * count
            
            gini = (2 * gini_sum) / (n * total_merges) - (n + 1) / n if n > 0 and total_merges > 0 else 0
            
            output[period] = {
                'total_merges': total_merges,
                'unique_mergers': len(sorted_mergers),
                'top3_control': top3_count / total_merges if total_merges > 0 else 0,
                'top10_control': top10_count / total_merges if total_merges > 0 else 0,
                'gini_coefficient': gini,
                'top_mergers': {name: count for name, count in sorted_mergers[:10]}
            }
        
        return output
    
    def analyze_review_quality_temporal(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze review quality metrics by period."""
        print("Analyzing review quality temporal patterns...")
        
        maintainer_merged = [p for p in prs 
                            if p.get('merged', False) and 
                            (p.get('author') or '').lower() in [m.lower() for m in self.maintainers]]
        
        results = defaultdict(lambda: {
            'total': 0,
            'zero_review': 0,
            'review_scores': [],
            'review_counts': []
        })
        
        for pr in maintainer_merged:
            merged_at = pr.get('merged_at')
            if not merged_at:
                continue
            
            try:
                year = datetime.fromisoformat(merged_at.replace('Z', '+00:00')).year
                period = self._get_period(year)
            except:
                continue
            
            results[period]['total'] += 1
            if self._is_zero_review(pr):
                results[period]['zero_review'] += 1
            
            score = self._calculate_review_score(pr)
            results[period]['review_scores'].append(score)
            
            review_count = len(pr.get('reviews', []))
            results[period]['review_counts'].append(review_count)
        
        output = {}
        for period, stats in results.items():
            if stats['total'] == 0:
                continue
            
            output[period] = {
                'total': stats['total'],
                'zero_review_count': stats['zero_review'],
                'zero_review_rate': stats['zero_review'] / stats['total'],
                'avg_review_score': sum(stats['review_scores']) / len(stats['review_scores']) if stats['review_scores'] else 0,
                'avg_review_count': sum(stats['review_counts']) / len(stats['review_counts']) if stats['review_counts'] else 0
            }
        
        return output
    
    def analyze_response_time_inequality(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze response time inequality by author status."""
        print("Analyzing response time inequality...")
        
        def parse_timestamp(ts: Optional[str]) -> Optional[datetime]:
            if not ts:
                return None
            try:
                return datetime.fromisoformat(ts.replace('Z', '+00:00'))
            except:
                return None
        
        maintainer_list = [m.lower() for m in self.maintainers]
        
        response_times = {
            'maintainer_authors': [],
            'non_maintainer_authors': [],
            'time_to_first_review': {
                'maintainer': [],
                'non_maintainer': []
            },
            'time_to_merge': {
                'maintainer': [],
                'non_maintainer': []
            }
        }
        
        for pr in prs:
            if not pr.get('merged', False):
                continue
            
            author = (pr.get('author') or '').lower()
            is_maintainer = author in maintainer_list
            
            created = parse_timestamp(pr.get('created_at'))
            merged = parse_timestamp(pr.get('merged_at'))
            
            if not created or not merged:
                continue
            
            # Time to merge
            time_to_merge = (merged - created).total_seconds() / 3600  # hours
            if is_maintainer:
                response_times['time_to_merge']['maintainer'].append(time_to_merge)
            else:
                response_times['time_to_merge']['non_maintainer'].append(time_to_merge)
            
            # Time to first review
            reviews = pr.get('reviews', [])
            if reviews:
                first_review_time = None
                for review in reviews:
                    review_ts = parse_timestamp(review.get('submitted_at') or review.get('created_at'))
                    if review_ts and review_ts > created:
                        if first_review_time is None or review_ts < first_review_time:
                            first_review_time = review_ts
                
                if first_review_time:
                    time_to_review = (first_review_time - created).total_seconds() / 3600  # hours
                    if is_maintainer:
                        response_times['time_to_first_review']['maintainer'].append(time_to_review)
                    else:
                        response_times['time_to_first_review']['non_maintainer'].append(time_to_review)
        
        # Calculate statistics
        def calc_stats(times: List[float]) -> Dict[str, float]:
            if not times:
                return {'count': 0, 'mean': 0, 'median': 0}
            times_sorted = sorted(times)
            return {
                'count': len(times),
                'mean': sum(times) / len(times),
                'median': times_sorted[len(times_sorted) // 2] if times_sorted else 0
            }
        
        results = {
            'time_to_first_review': {
                'maintainer': calc_stats(response_times['time_to_first_review']['maintainer']),
                'non_maintainer': calc_stats(response_times['time_to_first_review']['non_maintainer']),
                'inequality_ratio': 0.0
            },
            'time_to_merge': {
                'maintainer': calc_stats(response_times['time_to_merge']['maintainer']),
                'non_maintainer': calc_stats(response_times['time_to_merge']['non_maintainer']),
                'inequality_ratio': 0.0
            }
        }
        
        # Calculate inequality ratios
        maint_review_mean = results['time_to_first_review']['maintainer']['mean']
        non_maint_review_mean = results['time_to_first_review']['non_maintainer']['mean']
        if non_maint_review_mean > 0:
            results['time_to_first_review']['inequality_ratio'] = non_maint_review_mean / maint_review_mean if maint_review_mean > 0 else 0
        
        maint_merge_mean = results['time_to_merge']['maintainer']['mean']
        non_maint_merge_mean = results['time_to_merge']['non_maintainer']['mean']
        if non_maint_merge_mean > 0:
            results['time_to_merge']['inequality_ratio'] = non_maint_merge_mean / maint_merge_mean if maint_merge_mean > 0 else 0
        
        return results
    
    def analyze_response_time_by_complexity(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze response time inequality by code complexity."""
        print("Analyzing response time by complexity...")
        
        def parse_timestamp(ts: Optional[str]) -> Optional[datetime]:
            if not ts:
                return None
            try:
                return datetime.fromisoformat(ts.replace('Z', '+00:00'))
            except:
                return None
        
        maintainer_list = [m.lower() for m in self.maintainers]
        
        # Group by complexity
        complexity_groups = {
            'low': {'maintainer': {'review': [], 'merge': []}, 'non_maintainer': {'review': [], 'merge': []}},
            'medium': {'maintainer': {'review': [], 'merge': []}, 'non_maintainer': {'review': [], 'merge': []}},
            'high': {'maintainer': {'review': [], 'merge': []}, 'non_maintainer': {'review': [], 'merge': []}}
        }
        
        for pr in prs:
            if not pr.get('merged', False):
                continue
            
            # Determine complexity
            files = pr.get('files', [])
            files_count = len(files) if files else 0
            
            if files_count <= 5:
                complexity = 'low'
            elif files_count <= 15:
                complexity = 'medium'
            else:
                complexity = 'high'
            
            author = (pr.get('author') or '').lower()
            is_maintainer = author in maintainer_list
            
            created = parse_timestamp(pr.get('created_at'))
            merged = parse_timestamp(pr.get('merged_at'))
            
            if not created or not merged:
                continue
            
            # Time to merge
            time_to_merge = (merged - created).total_seconds() / 3600  # hours
            if is_maintainer:
                complexity_groups[complexity]['maintainer']['merge'].append(time_to_merge)
            else:
                complexity_groups[complexity]['non_maintainer']['merge'].append(time_to_merge)
            
            # Time to first review
            reviews = pr.get('reviews', [])
            if reviews:
                first_review_time = None
                for review in reviews:
                    review_ts = parse_timestamp(review.get('submitted_at') or review.get('created_at'))
                    if review_ts and review_ts > created:
                        if first_review_time is None or review_ts < first_review_time:
                            first_review_time = review_ts
                
                if first_review_time:
                    time_to_review = (first_review_time - created).total_seconds() / 3600  # hours
                    if is_maintainer:
                        complexity_groups[complexity]['maintainer']['review'].append(time_to_review)
                    else:
                        complexity_groups[complexity]['non_maintainer']['review'].append(time_to_review)
        
        # Calculate statistics
        def calc_stats(times: List[float]) -> Dict[str, float]:
            if not times:
                return {'count': 0, 'mean': 0, 'median': 0}
            times_sorted = sorted(times)
            return {
                'count': len(times),
                'mean': sum(times) / len(times),
                'median': times_sorted[len(times_sorted) // 2] if times_sorted else 0
            }
        
        results = {}
        for complexity in ['low', 'medium', 'high']:
            group = complexity_groups[complexity]
            results[complexity] = {
                'time_to_first_review': {
                    'maintainer': calc_stats(group['maintainer']['review']),
                    'non_maintainer': calc_stats(group['non_maintainer']['review']),
                    'inequality_ratio': 0.0
                },
                'time_to_merge': {
                    'maintainer': calc_stats(group['maintainer']['merge']),
                    'non_maintainer': calc_stats(group['non_maintainer']['merge']),
                    'inequality_ratio': 0.0
                }
            }
            
            # Calculate inequality ratios
            maint_review_mean = results[complexity]['time_to_first_review']['maintainer']['mean']
            non_maint_review_mean = results[complexity]['time_to_first_review']['non_maintainer']['mean']
            if non_maint_review_mean > 0 and maint_review_mean > 0:
                results[complexity]['time_to_first_review']['inequality_ratio'] = non_maint_review_mean / maint_review_mean
            
            maint_merge_mean = results[complexity]['time_to_merge']['maintainer']['mean']
            non_maint_merge_mean = results[complexity]['time_to_merge']['non_maintainer']['mean']
            if non_maint_merge_mean > 0 and maint_merge_mean > 0:
                results[complexity]['time_to_merge']['inequality_ratio'] = non_maint_merge_mean / maint_merge_mean
        
        return results
    
    def analyze_temporal_network_evolution(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze how network structure changes over time."""
        print("Analyzing temporal network evolution...")
        
        def parse_timestamp(ts: Optional[str]) -> Optional[datetime]:
            if not ts:
                return None
            try:
                return datetime.fromisoformat(ts.replace('Z', '+00:00'))
            except:
                return None
        
        # Group PRs by year
        prs_by_year = defaultdict(list)
        for pr in prs:
            if not pr.get('merged', False):
                continue
            merged_at = parse_timestamp(pr.get('merged_at'))
            if merged_at:
                year = merged_at.year
                prs_by_year[year].append(pr)
        
        network_evolution = {}
        
        for year in sorted(prs_by_year.keys()):
            year_prs = prs_by_year[year]
            
            # Build network for this year
            merge_edges = defaultdict(lambda: defaultdict(int))
            review_edges = defaultdict(lambda: defaultdict(int))
            nodes = set()
            
            for pr in year_prs:
                author = (pr.get('author') or '').lower()
                merged_by = (pr.get('merged_by') or '').lower()
                
                if author and merged_by:
                    nodes.add(author)
                    nodes.add(merged_by)
                    merge_edges[merged_by][author] += 1
                
                for review in pr.get('reviews', []):
                    reviewer = (review.get('author') or '').lower()
                    if reviewer and author:
                        nodes.add(reviewer)
                        nodes.add(author)
                        review_edges[reviewer][author] += 1
            
            # Calculate network metrics
            merge_degree = {node: sum(merge_edges[node].values()) for node in nodes}
            review_degree = {node: sum(review_edges[node].values()) for node in nodes}
            
            # Top 3 concentration (power concentration)
            sorted_merge = sorted(merge_degree.items(), key=lambda x: x[1], reverse=True)
            total_merges = sum(merge_degree.values())
            top3_merges = sum(count for _, count in sorted_merge[:3])
            top3_concentration = top3_merges / total_merges if total_merges > 0 else 0
            
            # Unique authors merged (betweenness proxy)
            unique_authors_merged = {}
            for merger, authors in merge_edges.items():
                unique_authors_merged[merger] = len(authors)
            
            network_evolution[year] = {
                'total_nodes': len(nodes),
                'total_merges': total_merges,
                'top3_concentration': top3_concentration,
                'top_merger': sorted_merge[0][0] if sorted_merge else None,
                'top_merger_count': sorted_merge[0][1] if sorted_merge else 0,
                'unique_authors_merged': len(unique_authors_merged),
                'max_unique_authors': max(unique_authors_merged.values()) if unique_authors_merged else 0
            }
        
        return network_evolution
    
    def analyze_voting_bloc_temporal(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze voting bloc formation and cohesion over time."""
        print("Analyzing voting bloc temporal patterns...")
        
        maintainer_list = [m.lower() for m in self.maintainers]
        
        # Group PRs by year
        prs_by_year = defaultdict(list)
        for pr in prs:
            merged_at = pr.get('merged_at')
            if merged_at:
                try:
                    year = datetime.fromisoformat(merged_at.replace('Z', '+00:00')).year
                    prs_by_year[year].append(pr)
                except ValueError:
                    pass
        
        temporal_bloc_metrics = {}
        
        for year in sorted(prs_by_year.keys()):
            year_prs = prs_by_year[year]
            if len(year_prs) < 50:  # Require minimum PRs for meaningful analysis
                continue
            
            # Track review decisions for each PR by maintainers
            pr_maintainer_reviews = defaultdict(lambda: defaultdict(str))  # pr_num -> maintainer -> review_state
            
            for pr in year_prs:
                pr_number = pr.get('number')
                if not pr_number:
                    continue
                
                for review in pr.get('reviews', []):
                    reviewer = (review.get('author') or '').lower()
                    review_state = (review.get('state') or '').lower()
                    
                    if reviewer in maintainer_list and review_state in ['approved', 'changes_requested']:
                        pr_maintainer_reviews[pr_number][reviewer] = review_state
            
            # Identify pairs of maintainers who frequently vote together
            voting_together_counts = defaultdict(lambda: defaultdict(int))
            
            for pr_num, maintainer_states in pr_maintainer_reviews.items():
                active_maintainers_in_pr = [m for m in maintainer_list if m in maintainer_states]
                
                for i, m1 in enumerate(active_maintainers_in_pr):
                    for m2 in active_maintainers_in_pr[i+1:]:
                        if maintainer_states[m1] == maintainer_states[m2]:
                            # They voted the same way
                            pair_key = tuple(sorted((m1, m2)))
                            voting_together_counts[pair_key][maintainer_states[m1]] += 1
            
            # Calculate cohesion for each pair
            blocs = []
            for pair, states in voting_together_counts.items():
                m1, m2 = pair
                total_same_votes = sum(states.values())
                
                if total_same_votes > 2:  # Only consider significant interactions
                    # Count total times they reviewed same PRs
                    total_together = sum(1 for pr_num, maintainer_states in pr_maintainer_reviews.items()
                                       if m1 in maintainer_states and m2 in maintainer_states)
                    
                    cohesion = total_same_votes / total_together if total_together > 0 else 0
                    
                    blocs.append({
                        'pair': f"{m1}_{m2}",
                        'm1': m1,
                        'm2': m2,
                        'together': total_same_votes,
                        'total': total_together,
                        'cohesion': cohesion
                    })
            
            # Calculate average cohesion
            avg_cohesion = sum(b['cohesion'] for b in blocs) / len(blocs) if blocs else 0
            strong_blocs = [b for b in blocs if b['cohesion'] > 0.8]
            
            temporal_bloc_metrics[year] = {
                'total_prs_in_year': len(year_prs),
                'voting_pairs': len(blocs),
                'avg_cohesion': avg_cohesion,
                'strong_blocs_count': len(strong_blocs),
                'top_blocs': sorted(blocs, key=lambda x: x['cohesion'], reverse=True)[:5]
            }
        
        return temporal_bloc_metrics
    
    def analyze_conflict_resolution_temporal(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze conflict resolution patterns over time."""
        print("Analyzing conflict resolution temporal patterns...")
        
        # NACK keywords
        nack_keywords = [
            'nack', 'nacked', 'nacking',
            'concept nack', 'approach nack', 'utack nack',
            'strong nack', 'weak nack'
        ]
        
        # Group PRs by year
        prs_by_year = defaultdict(list)
        for pr in prs:
            created_at = pr.get('created_at')
            if created_at:
                try:
                    year = datetime.fromisoformat(created_at.replace('Z', '+00:00')).year
                    prs_by_year[year].append(pr)
                except ValueError:
                    pass
        
        temporal_conflict_metrics = {}
        
        for year in sorted(prs_by_year.keys()):
            year_prs = prs_by_year[year]
            if len(year_prs) < 50:  # Require minimum PRs
                continue
            
            conflicts = []
            conflict_types = {'nack': 0, 'changes_requested': 0, 'heated_discussion': 0}
            resolution_paths = {'merged_anyway': 0, 'closed': 0, 'withdrawn': 0, 'still_open': 0}
            resolution_times = []
            
            for pr in year_prs:
                pr_number = pr.get('number')
                has_nack = False
                has_changes_requested = False
                has_heated_discussion = False
                
                # Check for NACKs
                for comment in pr.get('comments', []):
                    body = (comment.get('body') or '').lower()
                    if any(keyword in body for keyword in nack_keywords):
                        has_nack = True
                        conflict_types['nack'] += 1
                        break
                
                # Check for CHANGES_REQUESTED reviews
                for review in pr.get('reviews', []):
                    if (review.get('state') or '').upper() == 'CHANGES_REQUESTED':
                        has_changes_requested = True
                        conflict_types['changes_requested'] += 1
                        break
                
                # Check for heated discussion (multiple negative comments)
                negative_keywords = ['disagree', 'oppose', 'against', 'wrong', 'bad idea', 'concern', 'problem']
                negative_comments = sum(1 for comment in pr.get('comments', [])
                                      if any(kw in (comment.get('body') or '').lower() for kw in negative_keywords))
                if negative_comments >= 3:
                    has_heated_discussion = True
                    conflict_types['heated_discussion'] += 1
                
                # If has conflict, track it
                if has_nack or has_changes_requested or has_heated_discussion:
                    conflicts.append(pr_number)
                    
                    # Determine resolution path
                    if pr.get('merged', False):
                        resolution_paths['merged_anyway'] += 1
                    elif pr.get('state') == 'closed':
                        resolution_paths['closed'] += 1
                    else:
                        resolution_paths['still_open'] += 1
                    
                    # Calculate resolution time
                    created_at = pr.get('created_at')
                    closed_at = pr.get('closed_at')
                    merged_at = pr.get('merged_at')
                    
                    if created_at:
                        try:
                            created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            end_dt = None
                            
                            if merged_at:
                                end_dt = datetime.fromisoformat(merged_at.replace('Z', '+00:00'))
                            elif closed_at:
                                end_dt = datetime.fromisoformat(closed_at.replace('Z', '+00:00'))
                            
                            if end_dt:
                                resolution_days = (end_dt - created_dt).days
                                if resolution_days >= 0:
                                    resolution_times.append(resolution_days)
                        except ValueError:
                            pass
            
            avg_resolution_time = sum(resolution_times) / len(resolution_times) if resolution_times else 0
            
            temporal_conflict_metrics[year] = {
                'total_prs_in_year': len(year_prs),
                'total_conflicts': len(conflicts),
                'conflict_rate': len(conflicts) / len(year_prs) if year_prs else 0,
                'conflicts_by_type': conflict_types.copy(),
                'resolution_paths': resolution_paths.copy(),
                'avg_resolution_time_days': avg_resolution_time,
                'conflict_prs_count': len(conflicts)
            }
        
        return temporal_conflict_metrics
    
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
            'speed_hack_temporal': self.analyze_speed_hack_temporal(prs),
            'pr_importance_temporal': self.analyze_pr_importance_temporal(prs),
            'power_concentration_temporal': self.analyze_power_concentration_temporal(prs),
            'review_quality_temporal': self.analyze_review_quality_temporal(prs),
            'response_time_inequality': self.analyze_response_time_inequality(prs),
            'response_time_by_complexity': self.analyze_response_time_by_complexity(prs),
            'network_evolution': self.analyze_temporal_network_evolution(prs),
            'voting_bloc_temporal': self.analyze_voting_bloc_temporal(prs),
            'conflict_resolution_temporal': self.analyze_conflict_resolution_temporal(prs),
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
        changes = results.get('behavioral_changes', {})
        for maintainer, periods in list(changes.items())[:5]:
            print(f"{maintainer}:")
            for period, stats in periods.items():
                print(f"  {period}: {stats['self_merge_rate']*100:.1f}% self-merge, {stats['avg_reviews']:.1f} avg reviews")
            print()
        
        # Response Time Inequality
        print("RESPONSE TIME INEQUALITY")
        print("-" * 80)
        response_times = results.get('response_time_inequality', {})
        if response_times:
            print("Time to First Review (Hours):")
            print(f"  Maintainer PRs: Avg={response_times.get('time_to_first_review', {}).get('maintainer', {}).get('mean', 0):.1f}, Median={response_times.get('time_to_first_review', {}).get('maintainer', {}).get('median', 0):.1f}")
            print(f"  Non-Maintainer PRs: Avg={response_times.get('time_to_first_review', {}).get('non_maintainer', {}).get('mean', 0):.1f}, Median={response_times.get('time_to_first_review', {}).get('non_maintainer', {}).get('median', 0):.1f}")
            print("Time to Merge (Hours):")
            print(f"  Maintainer PRs: Avg={response_times.get('time_to_merge', {}).get('maintainer', {}).get('mean', 0):.1f}, Median={response_times.get('time_to_merge', {}).get('maintainer', {}).get('median', 0):.1f}")
            print(f"  Non-Maintainer PRs: Avg={response_times.get('time_to_merge', {}).get('non_maintainer', {}).get('mean', 0):.1f}, Median={response_times.get('time_to_merge', {}).get('non_maintainer', {}).get('median', 0):.1f}")
        print()
        
        # Voting Bloc Temporal
        print("VOTING BLOC TEMPORAL EVOLUTION")
        print("-" * 80)
        voting_bloc_temporal = results.get('voting_bloc_temporal', {})
        if voting_bloc_temporal:
            print("Year | PRs | Voting Pairs | Avg Cohesion | Strong Blocs")
            print("-" * 80)
            for year in sorted(voting_bloc_temporal.keys())[-10:]:  # Last 10 years
                stats = voting_bloc_temporal[year]
                print(f"{year} | {stats.get('total_prs_in_year', 0):4d} | {stats.get('voting_pairs', 0):11d} | {stats.get('avg_cohesion', 0):6.1%} | {stats.get('strong_blocs_count', 0):12d}")
        print()
        
        # Conflict Resolution Temporal
        print("CONFLICT RESOLUTION TEMPORAL EVOLUTION")
        print("-" * 80)
        conflict_temporal = results.get('conflict_resolution_temporal', {})
        if conflict_temporal:
            print("Year | PRs | Conflicts | Conflict Rate | Avg Resolution (days)")
            print("-" * 80)
            for year in sorted(conflict_temporal.keys())[-10:]:  # Last 10 years
                stats = conflict_temporal[year]
                print(f"{year} | {stats.get('total_prs_in_year', 0):4d} | {stats.get('total_conflicts', 0):9d} | {stats.get('conflict_rate', 0):12.1%} | {stats.get('avg_resolution_time_days', 0):20.1f}")
        print()
        
        # Response Time by Complexity
        print("RESPONSE TIME BY COMPLEXITY")
        print("-" * 80)
        response_by_complexity = results.get('response_time_by_complexity', {})
        if response_by_complexity:
            for complexity in ['low', 'medium', 'high']:
                if complexity in response_by_complexity:
                    stats = response_by_complexity[complexity]
                    print(f"{complexity.upper()} Complexity:")
                    print(f"  First Review - Maintainer: {stats['time_to_first_review']['maintainer']['median']:.1f}h, Non-maintainer: {stats['time_to_first_review']['non_maintainer']['median']:.1f}h (Inequality: {stats['time_to_first_review']['inequality_ratio']:.2f}x)")
                    print(f"  Merge Time - Maintainer: {stats['time_to_merge']['maintainer']['median']:.1f}h, Non-maintainer: {stats['time_to_merge']['non_maintainer']['median']:.1f}h (Inequality: {stats['time_to_merge']['inequality_ratio']:.2f}x)")
            print()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Comprehensive temporal analysis')
    parser.add_argument('--data-dir', type=Path, default=Path(__file__).parent.parent.parent.parent / 'data',
                       help='Data directory')
    parser.add_argument('--output', type=Path, default=Path(__file__).parent.parent.parent / 'findings' / 'data' / 'temporal_analysis.json',
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
