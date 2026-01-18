"""Utility functions for the analysis project."""

# Power metrics
from src.utils.power_metrics import (
    calculate_gini,
    calculate_hhi,
    calculate_top_n_share,
    calculate_concentration_metrics,
    calculate_power_concentration_from_counts,
    calculate_temporal_concentration,
    interpret_gini,
    compare_concentration
)

# Temporal utilities
from src.utils.temporal_utils import (
    parse_date,
    get_year,
    get_quarter,
    get_year_month,
    get_era,
    group_by_period,
    count_by_period,
    count_by_actor_by_period,
    calculate_rate_by_period,
    calculate_trend,
    analyze_cohort_retention,
    calculate_moving_average,
    GOVERNANCE_ERAS
)

__all__ = [
    # Power metrics
    'calculate_gini',
    'calculate_hhi',
    'calculate_top_n_share',
    'calculate_concentration_metrics',
    'calculate_power_concentration_from_counts',
    'calculate_temporal_concentration',
    'interpret_gini',
    'compare_concentration',
    # Temporal utilities
    'parse_date',
    'get_year',
    'get_quarter',
    'get_year_month',
    'get_era',
    'group_by_period',
    'count_by_period',
    'count_by_actor_by_period',
    'calculate_rate_by_period',
    'calculate_trend',
    'analyze_cohort_retention',
    'calculate_moving_average',
    'GOVERNANCE_ERAS',
    # PR classification
    'PRImportance',
    'classify_pr_importance',
    'get_pr_importance_label',
    'is_consensus_related',
    'is_housekeeping'
]

# Import PR classification
from src.utils.pr_classification import (
    PRImportance,
    classify_pr_importance,
    get_pr_importance_label,
    is_consensus_related,
    is_housekeeping
)
