#!/usr/bin/env python3
"""
Maintainer Premium Analysis

Analyzes whether PRs from maintainers get preferential treatment.
"""

import sys
import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any
from scipy import stats
from sklearn.linear_model import LogisticRegression

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config import config
from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir, get_analysis_dir

logger = setup_logger()


class MaintainerPremiumAnalyzer:
    """Analyzer for maintainer premium effects."""
    
    def __init__(self):
        """Initialize analyzer."""
        self.data_dir = get_data_dir()
        self.analysis_dir = get_analysis_dir() / 'maintainer_premium'
        self.analysis_dir.mkdir(parents=True, exist_ok=True)
    
    def run_analysis(self):
        """Run the maintainer premium analysis."""
        logger.info("Starting maintainer premium analysis")
        
        # Load data
        prs = self._load_pr_data()
        
        # Identify maintainer status
        maintainers = self._load_maintainer_timeline()
        prs = self._add_maintainer_status(prs, maintainers)
        
        # Calculate metrics
        metrics = self._calculate_metrics(prs)
        
        # Statistical tests
        results = self._statistical_tests(prs)
        
        # Analyze review effectiveness by maintainer status (NEW)
        review_effectiveness = self._analyze_review_effectiveness(prs)
        
        # Save results
        self._save_results(metrics, results, prs, review_effectiveness)
        
        logger.info("Maintainer premium analysis complete")
    
    def _load_pr_data(self) -> pd.DataFrame:
        """Load PR data from JSONL file."""
        # Use enriched PRs data (complete dataset)
        processed_dir = self.data_dir / 'processed'
        prs_file = processed_dir / 'enriched_prs.jsonl'
        
        if not prs_file.exists():
            # Fallback to cleaned_prs if enriched doesn't exist
            prs_file = processed_dir / 'cleaned_prs.jsonl'
        
        if not prs_file.exists():
            raise FileNotFoundError(f"PR data file not found: {prs_file}")
        
        prs = []
        with open(prs_file, 'r') as f:
            for line in f:
                prs.append(json.loads(line))
        
        return pd.DataFrame(prs)
    
    def _load_maintainer_timeline(self) -> Dict[str, Any]:
        """Load maintainer timeline from MAINTAINERS file history."""
        # This would parse git log of MAINTAINERS file
        # For now, return placeholder
        return {}
    
    def _add_maintainer_status(self, prs: pd.DataFrame, maintainers: Dict) -> pd.DataFrame:
        """Add maintainer status to PRs."""
        # Placeholder implementation
        prs['is_maintainer'] = False  # Would be determined from maintainers dict
        return prs
    
    def _calculate_metrics(self, prs: pd.DataFrame) -> Dict[str, Any]:
        """Calculate maintainer premium metrics."""
        maintainer_prs = prs[prs['is_maintainer'] == True]
        non_maintainer_prs = prs[prs['is_maintainer'] == False]
        
        metrics = {
            'maintainer_merge_rate': maintainer_prs['merged'].mean() if 'merged' in maintainer_prs.columns else 0,
            'non_maintainer_merge_rate': non_maintainer_prs['merged'].mean() if 'merged' in non_maintainer_prs.columns else 0,
            'maintainer_median_time_to_merge': maintainer_prs['time_to_merge_days'].median() if 'time_to_merge_days' in maintainer_prs.columns else None,
            'non_maintainer_median_time_to_merge': non_maintainer_prs['time_to_merge_days'].median() if 'time_to_merge_days' in non_maintainer_prs.columns else None,
        }
        
        return metrics
    
    def _statistical_tests(self, prs: pd.DataFrame) -> Dict[str, Any]:
        """Run statistical tests."""
        results = {}
        
        # Chi-square test for merge rate
        if 'merged' in prs.columns and 'is_maintainer' in prs.columns:
            contingency = pd.crosstab(prs['is_maintainer'], prs['merged'])
            chi2, p_value, dof, expected = stats.chi2_contingency(contingency)
            results['chi_square'] = {
                'chi2': float(chi2),
                'p_value': float(p_value),
                'degrees_of_freedom': int(dof)
            }
        
        # T-test for time to merge
        if 'time_to_merge_days' in prs.columns:
            maintainer_times = prs[prs['is_maintainer'] == True]['time_to_merge_days'].dropna()
            non_maintainer_times = prs[prs['is_maintainer'] == False]['time_to_merge_days'].dropna()
            
            if len(maintainer_times) > 0 and len(non_maintainer_times) > 0:
                t_stat, p_value = stats.ttest_ind(maintainer_times, non_maintainer_times)
                results['t_test'] = {
                    't_statistic': float(t_stat),
                    'p_value': float(p_value)
                }
        
        return results
    
    def _analyze_review_effectiveness(self, prs: pd.DataFrame) -> Dict[str, Any]:
        """Analyze review effectiveness by maintainer status."""
        # This would analyze if maintainer reviews are more effective
        # For now, return structure
        return {
            'maintainer_review_effectiveness': 'to_be_analyzed',
            'non_maintainer_review_effectiveness': 'to_be_analyzed'
        }
    
    def _save_results(self, metrics: Dict, results: Dict, prs: pd.DataFrame, review_effectiveness: Dict = None):
        """Save analysis results."""
        # Save metrics
        output_data = {
            'metrics': metrics,
            'statistical_tests': results
        }
        
        if review_effectiveness:
            output_data['review_effectiveness'] = review_effectiveness
        
        with open(self.analysis_dir / 'statistics.json', 'w') as f:
            json.dump(output_data, f, indent=2)
        
        # Save data
        prs.to_csv(self.analysis_dir / 'data.csv', index=False)
        
        logger.info(f"Results saved to {self.analysis_dir}")


def main():
    """Main entry point."""
    analyzer = MaintainerPremiumAnalyzer()
    analyzer.run_analysis()


if __name__ == '__main__':
    main()

