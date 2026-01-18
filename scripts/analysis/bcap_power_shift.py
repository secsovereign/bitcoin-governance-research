#!/usr/bin/env python3
"""
BCAP Power Shift Analysis - Analyze how Bitcoin Core governance changes during consensus changes.

BCAP describes power shifts between ecosystem stakeholders during consensus changes.
This script applies the CONCEPT to Core-internal governance during consensus periods:
- How does power concentration change?
- Do review patterns shift?
- Does merge authority change during contentious periods?

Focus periods:
- SegWit (2015-2017)
- Taproot (2018-2021)
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, Counter
from datetime import datetime, timedelta, timezone

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir, get_analysis_dir
from scripts.utils.load_prs_with_merged_by import load_prs_with_merged_by

logger = setup_logger()


# Consensus change periods
CONSENSUS_PERIODS = {
    'segwit': {
        'start': '2015-12-07',  # BIP141 proposal
        'end': '2017-08-23',     # SegWit activation
        'phases': {
            'pre_signal': ('2015-12-07', '2016-11-21'),  # Before signaling started
            'signaling': ('2016-11-21', '2017-07-29'),   # Signaling period
            'activation': ('2017-07-29', '2017-08-23')   # Activation period
        }
    },
    'taproot': {
        'start': '2018-01-06',   # Taproot proposal
        'end': '2021-11-14',     # Taproot activation
        'phases': {
            'pre_signal': ('2018-01-06', '2020-05-01'),
            'signaling': ('2020-05-01', '2021-06-12'),
            'activation': ('2021-06-12', '2021-11-14')
        }
    }
}

# Baseline periods (6 months before consensus period starts)
BASELINE_PERIODS = {
    'segwit': ('2015-06-07', '2015-12-06'),
    'taproot': ('2017-07-06', '2018-01-05')
}


class BCAPPowerShiftAnalyzer:
    """Analyzes power shifts in Bitcoin Core governance during consensus changes."""
    
    def __init__(self):
        """Initialize analyzer."""
        self.data_dir = get_data_dir()
        self.processed_dir = self.data_dir / 'processed'
        self.analysis_dir = get_analysis_dir()
        self.findings_dir = self.analysis_dir / 'findings' / 'data'
        self.findings_dir.mkdir(parents=True, exist_ok=True)
        
        # Maintainer list
        self.maintainers = {
            'laanwj', 'sipa', 'maflcko', 'fanquake', 'hebasto', 'jnewbery',
            'ryanofsky', 'achow101', 'theuni', 'jonasschnelli', 'Sjors',
            'promag', 'instagibbs', 'TheBlueMatt', 'jonatack', 'gmaxwell',
            'gavinandresen', 'petertodd', 'luke-jr', 'glozow'
        }
    
    def run_analysis(self):
        """Run power shift analysis."""
        logger.info("=" * 60)
        logger.info("BCAP Power Shift Analysis")
        logger.info("=" * 60)
        
        # Load data
        prs = self._load_prs()
        
        # Analyze SegWit period
        segwit_analysis = self._analyze_consensus_period(prs, 'segwit')
        
        # Analyze Taproot period
        taproot_analysis = self._analyze_consensus_period(prs, 'taproot')
        
        # Compare with baseline periods
        baseline_comparison = self._compare_with_baseline(prs)
        
        # Generate overall statistics
        statistics = self._generate_statistics(segwit_analysis, taproot_analysis, baseline_comparison)
        
        # Save results
        results = {
            'segwit_analysis': segwit_analysis,
            'taproot_analysis': taproot_analysis,
            'baseline_comparison': baseline_comparison,
            'statistics': statistics,
            'methodology': self._get_methodology()
        }
        
        self._save_results(results)
        
        logger.info("Power shift analysis complete")
    
    def _analyze_consensus_period(
        self,
        prs: List[Dict[str, Any]],
        period: str
    ) -> Dict[str, Any]:
        """Analyze power shifts during a consensus change period."""
        logger.info(f"Analyzing power shifts for {period}...")
        
        period_data = CONSENSUS_PERIODS[period]
        phases = period_data['phases']
        
        # Get PRs for each phase
        phase_prs = {}
        for phase_name, (start_str, end_str) in phases.items():
            start_date = datetime.fromisoformat(start_str).replace(tzinfo=timezone.utc)
            end_date = datetime.fromisoformat(end_str).replace(tzinfo=timezone.utc)
            phase_prs[phase_name] = self._filter_prs_by_date(prs, start_date, end_date)
        
        # Analyze power concentration in each phase
        phase_analyses = {}
        for phase_name, phase_prs_list in phase_prs.items():
            phase_analyses[phase_name] = self._analyze_phase(
                phase_prs_list, phase_name, period
            )
        
        # Analyze overall period
        start_date = datetime.fromisoformat(period_data['start']).replace(tzinfo=timezone.utc)
        end_date = datetime.fromisoformat(period_data['end']).replace(tzinfo=timezone.utc)
        all_period_prs = self._filter_prs_by_date(prs, start_date, end_date)
        overall_analysis = self._analyze_phase(all_period_prs, 'overall', period)
        
        return {
            'period': period,
            'start_date': period_data['start'],
            'end_date': period_data['end'],
            'phase_analyses': phase_analyses,
            'overall_analysis': overall_analysis,
            'total_prs': len(all_period_prs)
        }
    
    def _analyze_phase(
        self,
        prs: List[Dict[str, Any]],
        phase_name: str,
        period: str
    ) -> Dict[str, Any]:
        """Analyze power concentration and review patterns for a phase."""
        
        # Power concentration metrics
        merge_counts = defaultdict(int)
        review_counts = defaultdict(int)
        maintainer_pr_counts = defaultdict(int)
        self_merge_count = 0
        zero_review_count = 0
        
        # Review pattern metrics
        total_reviews = 0
        maintainer_reviews = 0
        non_maintainer_reviews = 0
        review_response_time = []
        
        # Merge authority metrics
        maintainer_merged = 0
        non_maintainer_merged = 0
        
        for pr in prs:
            if not pr.get('merged', False):
                continue
            
            merged_by = (pr.get('merged_by') or '').lower()
            author = (pr.get('author') or '').lower()
            
            # Count merges by person
            if merged_by:
                merge_counts[merged_by] += 1
                if merged_by in [m.lower() for m in self.maintainers]:
                    maintainer_merged += 1
                else:
                    non_maintainer_merged += 1
            
            # Self-merge detection
            if merged_by and author and merged_by == author:
                self_merge_count += 1
            
            # Count maintainer PRs
            if author in [m.lower() for m in self.maintainers]:
                maintainer_pr_counts[author] += 1
            
            # Review analysis
            reviews = pr.get('reviews', [])
            total_reviews += len(reviews)
            
            if len(reviews) == 0:
                zero_review_count += 1
            
            for review in reviews:
                reviewer = (review.get('author') or '').lower()
                if reviewer:
                    review_counts[reviewer] += 1
                    
                    if reviewer in [m.lower() for m in self.maintainers]:
                        maintainer_reviews += 1
                    else:
                        non_maintainer_reviews += 1
                
                # Response time (simplified - time from PR creation to review)
                created = pr.get('created_at')
                review_date = review.get('submitted_at')
                if created and review_date:
                    try:
                        created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                        review_dt = datetime.fromisoformat(review_date.replace('Z', '+00:00'))
                        hours = (review_dt - created_dt).total_seconds() / 3600
                        if hours >= 0:
                            review_response_time.append(hours)
                    except:
                        pass
        
        # Calculate power concentration (Gini-like measure for top 3)
        sorted_merges = sorted(merge_counts.values(), reverse=True)
        total_merges = sum(merge_counts.values())
        
        if total_merges > 0:
            top3_merge_share = sum(sorted_merges[:3]) / total_merges
            top5_merge_share = sum(sorted_merges[:5]) / total_merges
        else:
            top3_merge_share = 0
            top5_merge_share = 0
        
        # Calculate review concentration
        sorted_reviews = sorted(review_counts.values(), reverse=True)
        total_review_count = sum(review_counts.values())
        
        if total_review_count > 0:
            top3_review_share = sum(sorted_reviews[:3]) / total_review_count
            top5_review_share = sum(sorted_reviews[:5]) / total_review_count
        else:
            top3_review_share = 0
            top5_review_share = 0
        
        # Calculate metrics
        merged_prs = sum(1 for pr in prs if pr.get('merged', False))
        self_merge_rate = (self_merge_count / merged_prs * 100) if merged_prs > 0 else 0
        zero_review_rate = (zero_review_count / merged_prs * 100) if merged_prs > 0 else 0
        
        avg_reviews_per_pr = total_reviews / merged_prs if merged_prs > 0 else 0
        maintainer_review_share = (maintainer_reviews / total_reviews * 100) if total_reviews > 0 else 0
        
        avg_response_time = sum(review_response_time) / len(review_response_time) if review_response_time else 0
        
        return {
            'phase': phase_name,
            'merged_prs': merged_prs,
            'power_concentration': {
                'top3_merge_share': top3_merge_share,
                'top5_merge_share': top5_merge_share,
                'top3_review_share': top3_review_share,
                'top5_review_share': top5_review_share,
                'merge_counts': dict(sorted(merge_counts.items(), key=lambda x: x[1], reverse=True)[:10])
            },
            'review_patterns': {
                'avg_reviews_per_pr': avg_reviews_per_pr,
                'maintainer_review_share': maintainer_review_share,
                'non_maintainer_review_share': 100 - maintainer_review_share,
                'zero_review_rate': zero_review_rate,
                'avg_response_time_hours': avg_response_time
            },
            'merge_authority': {
                'self_merge_rate': self_merge_rate,
                'maintainer_merged': maintainer_merged,
                'non_maintainer_merged': non_maintainer_merged,
                'maintainer_merge_share': (maintainer_merged / merged_prs * 100) if merged_prs > 0 else 0
            }
        }
    
    def _compare_with_baseline(
        self,
        prs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Compare consensus periods with baseline periods."""
        logger.info("Comparing with baseline periods...")
        
        comparisons = {}
        
        for period_name, (start_str, end_str) in BASELINE_PERIODS.items():
            start_date = datetime.fromisoformat(start_str).replace(tzinfo=timezone.utc)
            end_date = datetime.fromisoformat(end_str).replace(tzinfo=timezone.utc)
            baseline_prs = self._filter_prs_by_date(prs, start_date, end_date)
            
            baseline_analysis = self._analyze_phase(baseline_prs, 'baseline', period_name)
            comparisons[period_name] = baseline_analysis
        
        return comparisons
    
    def _filter_prs_by_date(
        self,
        prs: List[Dict[str, Any]],
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Filter PRs by date range."""
        filtered = []
        
        for pr in prs:
            created = pr.get('created_at')
            if not created:
                continue
            
            try:
                created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                if start_date <= created_dt <= end_date:
                    filtered.append(pr)
            except:
                continue
        
        return filtered
    
    def _generate_statistics(
        self,
        segwit_analysis: Dict[str, Any],
        taproot_analysis: Dict[str, Any],
        baseline_comparison: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate overall statistics."""
        
        # Compare phases
        segwit_overall = segwit_analysis.get('overall_analysis', {})
        taproot_overall = taproot_analysis.get('overall_analysis', {})
        
        return {
            'segwit': {
                'power_concentration': segwit_overall.get('power_concentration', {}),
                'review_patterns': segwit_overall.get('review_patterns', {}),
                'merge_authority': segwit_overall.get('merge_authority', {})
            },
            'taproot': {
                'power_concentration': taproot_overall.get('power_concentration', {}),
                'review_patterns': taproot_overall.get('review_patterns', {}),
                'merge_authority': taproot_overall.get('merge_authority', {})
            },
            'baseline_comparison': baseline_comparison
        }
    
    def _get_methodology(self) -> Dict[str, Any]:
        """Get methodology description."""
        return {
            'framework': 'BCAP Power Shift Concept (applied to Core-internal governance)',
            'reference': 'https://github.com/bitcoin-cap/bcap',
            'analysis_focus': 'How Bitcoin Core governance changes during consensus change periods',
            'metrics': {
                'power_concentration': 'Top 3/5 merge share, review share',
                'review_patterns': 'Review rates, maintainer vs non-maintainer reviews',
                'merge_authority': 'Self-merge rates, maintainer merge share'
            },
            'periods': {
                'consensus_periods': CONSENSUS_PERIODS,
                'baseline_periods': BASELINE_PERIODS
            }
        }
    
    def _load_prs(self) -> List[Dict[str, Any]]:
        """Load PR data."""
        # Try processed first, then fallback to raw
        prs_file = self.processed_dir / 'enriched_prs.jsonl'
        
        if not prs_file.exists():
            prs_file = self.processed_dir / 'cleaned_prs.jsonl'
        
        if not prs_file.exists():
            prs_file = self.data_dir / 'github' / 'prs_raw.jsonl'
        
        # Fallback to parent directory (commons-research/data/)
        if not prs_file.exists():
            parent_data_dir = self.data_dir.parent.parent / 'data'
            prs_file = parent_data_dir / 'github' / 'prs_raw.jsonl'
        
        if not prs_file.exists():
            logger.warning(f"PR data not found. Tried: {self.processed_dir / 'enriched_prs.jsonl'}, {self.data_dir / 'github' / 'prs_raw.jsonl'}, {prs_file}")
            return []
        
        # Try mapping file in both locations
        mapping_file = self.data_dir / 'github' / 'merged_by_mapping.jsonl'
        if not mapping_file.exists():
            parent_data_dir = self.data_dir.parent.parent / 'data'
            mapping_file = parent_data_dir / 'github' / 'merged_by_mapping.jsonl'
        
        prs = load_prs_with_merged_by(prs_file, mapping_file if mapping_file.exists() else None)
        
        logger.info(f"Loaded {len(prs)} PRs from {prs_file}")
        return prs
    
    def _save_results(self, results: Dict[str, Any]):
        """Save analysis results."""
        output_file = self.findings_dir / 'bcap_power_shift.json'
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Saved results to {output_file}")


def main():
    """Main entry point."""
    analyzer = BCAPPowerShiftAnalyzer()
    analyzer.run_analysis()


if __name__ == '__main__':
    main()

