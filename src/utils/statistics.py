"""Statistical analysis utilities with standardized tests and reporting."""

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LogisticRegression
from typing import Dict, Any, Tuple, Optional, List
import warnings

# Statistical constants
SIGNIFICANCE_LEVEL = 0.05
EFFECT_SIZE_THRESHOLDS = {
    'cohens_d': {'small': 0.2, 'medium': 0.5, 'large': 0.8},
    'odds_ratio': {'small': 1.5, 'medium': 2.5, 'large': 4.0}
}


class StatisticalAnalyzer:
    """Standardized statistical analysis utilities."""
    
    def __init__(self, random_seed: int = 42):
        """Initialize analyzer with random seed for reproducibility."""
        np.random.seed(random_seed)
        self.random_seed = random_seed
    
    def chi_square_test(
        self,
        group1: pd.Series,
        group2: pd.Series,
        correction: bool = True
    ) -> Dict[str, Any]:
        """
        Perform chi-square test of independence.
        
        Args:
            group1: First categorical variable
            group2: Second categorical variable
            correction: Apply Yates' correction for 2x2 tables
        
        Returns:
            Dictionary with test results
        """
        # Create contingency table
        contingency = pd.crosstab(group1, group2)
        
        # Perform test
        if correction and contingency.shape == (2, 2):
            chi2, p_value, dof, expected = stats.chi2_contingency(
                contingency, correction=True
            )
        else:
            chi2, p_value, dof, expected = stats.chi2_contingency(contingency)
        
        # Calculate effect size (Cramér's V)
        n = contingency.sum().sum()
        cramers_v = np.sqrt(chi2 / (n * (min(contingency.shape) - 1)))
        
        return {
            'test': 'chi_square',
            'statistic': float(chi2),
            'p_value': float(p_value),
            'degrees_of_freedom': int(dof),
            'effect_size': {
                'cramers_v': float(cramers_v),
                'interpretation': self._interpret_cramers_v(cramers_v)
            },
            'significant': p_value < SIGNIFICANCE_LEVEL,
            'contingency_table': contingency.to_dict(),
            'expected_frequencies': pd.DataFrame(expected).to_dict()
        }
    
    def t_test(
        self,
        group1: pd.Series,
        group2: pd.Series,
        equal_var: bool = False
    ) -> Dict[str, Any]:
        """
        Perform independent samples t-test.
        
        Args:
            group1: First group data
            group2: Second group data
            equal_var: Assume equal variances (default: False, uses Welch's t-test)
        
        Returns:
            Dictionary with test results
        """
        # Remove NaN values
        group1_clean = group1.dropna()
        group2_clean = group2.dropna()
        
        if len(group1_clean) < 2 or len(group2_clean) < 2:
            return {
                'test': 't_test',
                'error': 'Insufficient data for t-test'
            }
        
        # Perform test
        statistic, p_value = stats.ttest_ind(group1_clean, group2_clean, equal_var=equal_var)
        
        # Calculate effect size (Cohen's d)
        pooled_std = np.sqrt(
            ((len(group1_clean) - 1) * group1_clean.std()**2 +
             (len(group2_clean) - 1) * group2_clean.std()**2) /
            (len(group1_clean) + len(group2_clean) - 2)
        )
        cohens_d = (group1_clean.mean() - group2_clean.mean()) / pooled_std if pooled_std > 0 else 0
        
        # Calculate confidence interval
        ci = self._calculate_ci_difference(group1_clean, group2_clean)
        
        return {
            'test': 't_test',
            'statistic': float(statistic),
            'p_value': float(p_value),
            'effect_size': {
                'cohens_d': float(cohens_d),
                'interpretation': self._interpret_cohens_d(cohens_d)
            },
            'confidence_interval_95': ci,
            'significant': p_value < SIGNIFICANCE_LEVEL,
            'group1_stats': {
                'mean': float(group1_clean.mean()),
                'std': float(group1_clean.std()),
                'n': len(group1_clean)
            },
            'group2_stats': {
                'mean': float(group2_clean.mean()),
                'std': float(group2_clean.std()),
                'n': len(group2_clean)
            }
        }
    
    def mann_whitney_test(
        self,
        group1: pd.Series,
        group2: pd.Series
    ) -> Dict[str, Any]:
        """
        Perform Mann-Whitney U test (non-parametric alternative to t-test).
        
        Args:
            group1: First group data
            group2: Second group data
        
        Returns:
            Dictionary with test results
        """
        group1_clean = group1.dropna()
        group2_clean = group2.dropna()
        
        if len(group1_clean) < 2 or len(group2_clean) < 2:
            return {
                'test': 'mann_whitney',
                'error': 'Insufficient data for Mann-Whitney test'
            }
        
        statistic, p_value = stats.mannwhitneyu(group1_clean, group2_clean, alternative='two-sided')
        
        # Calculate effect size (rank-biserial correlation)
        n1, n2 = len(group1_clean), len(group2_clean)
        r = 1 - (2 * statistic) / (n1 * n2)
        
        return {
            'test': 'mann_whitney',
            'statistic': float(statistic),
            'p_value': float(p_value),
            'effect_size': {
                'rank_biserial': float(r),
                'interpretation': self._interpret_correlation(abs(r))
            },
            'significant': p_value < SIGNIFICANCE_LEVEL,
            'group1_stats': {
                'median': float(group1_clean.median()),
                'n': len(group1_clean)
            },
            'group2_stats': {
                'median': float(group2_clean.median()),
                'n': len(group2_clean)
            }
        }
    
    def logistic_regression(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        feature_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Perform logistic regression analysis.
        
        Args:
            X: Feature matrix
            y: Binary outcome variable
            feature_names: Optional list of feature names
        
        Returns:
            Dictionary with regression results
        """
        # Remove NaN values
        mask = ~(X.isna().any(axis=1) | y.isna())
        X_clean = X[mask]
        y_clean = y[mask]
        
        if len(X_clean) < 10:
            return {
                'test': 'logistic_regression',
                'error': 'Insufficient data for logistic regression'
            }
        
        # Fit model
        model = LogisticRegression(random_state=self.random_seed, max_iter=1000)
        model.fit(X_clean, y_clean)
        
        # Get coefficients and p-values
        coefficients = model.coef_[0]
        intercept = model.intercept_[0]
        
        # Calculate p-values using Wald test
        from scipy.stats import norm
        se = np.sqrt(np.diag(np.linalg.inv(np.dot(X_clean.T, X_clean))))
        z_scores = coefficients / se
        p_values = 2 * (1 - norm.cdf(np.abs(z_scores)))
        
        # Calculate odds ratios
        odds_ratios = np.exp(coefficients)
        
        # Feature names
        if feature_names is None:
            feature_names = [f'feature_{i}' for i in range(len(coefficients))]
        
        # Build results
        results = {
            'test': 'logistic_regression',
            'intercept': float(intercept),
            'coefficients': {
                name: {
                    'coefficient': float(coef),
                    'p_value': float(p_val),
                    'odds_ratio': float(or_val),
                    'significant': p_val < SIGNIFICANCE_LEVEL,
                    'interpretation': self._interpret_odds_ratio(or_val)
                }
                for name, coef, p_val, or_val in zip(feature_names, coefficients, p_values, odds_ratios)
            },
            'model_score': float(model.score(X_clean, y_clean)),
            'n_samples': len(X_clean)
        }
        
        return results
    
    def _calculate_ci_difference(
        self,
        group1: pd.Series,
        group2: pd.Series,
        confidence: float = 0.95
    ) -> List[float]:
        """Calculate confidence interval for difference in means."""
        n1, n2 = len(group1), len(group2)
        mean1, mean2 = group1.mean(), group2.mean()
        std1, std2 = group1.std(), group2.std()
        
        # Standard error
        se = np.sqrt((std1**2 / n1) + (std2**2 / n2))
        
        # T-critical value
        df = min(n1 - 1, n2 - 1)
        t_crit = stats.t.ppf((1 + confidence) / 2, df)
        
        # Difference
        diff = mean1 - mean2
        
        return [float(diff - t_crit * se), float(diff + t_crit * se)]
    
    def _interpret_cohens_d(self, d: float) -> str:
        """Interpret Cohen's d effect size."""
        abs_d = abs(d)
        if abs_d < EFFECT_SIZE_THRESHOLDS['cohens_d']['small']:
            return 'negligible'
        elif abs_d < EFFECT_SIZE_THRESHOLDS['cohens_d']['medium']:
            return 'small'
        elif abs_d < EFFECT_SIZE_THRESHOLDS['cohens_d']['large']:
            return 'medium'
        else:
            return 'large'
    
    def _interpret_cramers_v(self, v: float) -> str:
        """Interpret Cramér's V effect size."""
        if v < 0.1:
            return 'negligible'
        elif v < 0.3:
            return 'small'
        elif v < 0.5:
            return 'medium'
        else:
            return 'large'
    
    def _interpret_odds_ratio(self, or_val: float) -> str:
        """Interpret odds ratio effect size."""
        if or_val < 1:
            or_val = 1 / or_val
        
        if or_val < EFFECT_SIZE_THRESHOLDS['odds_ratio']['small']:
            return 'negligible'
        elif or_val < EFFECT_SIZE_THRESHOLDS['odds_ratio']['medium']:
            return 'small'
        elif or_val < EFFECT_SIZE_THRESHOLDS['odds_ratio']['large']:
            return 'medium'
        else:
            return 'large'
    
    def _interpret_correlation(self, r: float) -> str:
        """Interpret correlation coefficient."""
        if r < 0.1:
            return 'negligible'
        elif r < 0.3:
            return 'small'
        elif r < 0.5:
            return 'medium'
        else:
            return 'large'
    
    def correct_multiple_comparisons(
        self,
        p_values: List[float],
        method: str = 'fdr_bh'
    ) -> List[float]:
        """
        Apply multiple comparison correction.
        
        Args:
            p_values: List of p-values
            method: Correction method ('fdr_bh', 'bonferroni', 'holm')
        
        Returns:
            Corrected p-values
        """
        from statsmodels.stats.multitest import multipletests
        
        if method == 'fdr_bh':
            _, p_corrected, _, _ = multipletests(p_values, alpha=SIGNIFICANCE_LEVEL, method='fdr_bh')
        elif method == 'bonferroni':
            _, p_corrected, _, _ = multipletests(p_values, alpha=SIGNIFICANCE_LEVEL, method='bonferroni')
        elif method == 'holm':
            _, p_corrected, _, _ = multipletests(p_values, alpha=SIGNIFICANCE_LEVEL, method='holm')
        else:
            raise ValueError(f"Unknown correction method: {method}")
        
        return p_corrected.tolist()

