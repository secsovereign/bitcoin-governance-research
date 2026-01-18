"""Power concentration metrics for governance analysis.

Provides standalone functions for calculating power concentration metrics:
- Gini coefficient
- Herfindahl-Hirschman Index (HHI)
- Top-N concentration shares
- Combined power scores

These can be used independently of NetworkAnalyzer for simpler analyses.
"""

from typing import Dict, Any, List, Optional
from collections import Counter


def calculate_gini(values: List[float]) -> float:
    """
    Calculate Gini coefficient for a distribution.
    
    The Gini coefficient measures inequality in a distribution:
    - 0.0 = perfect equality (everyone has the same)
    - 1.0 = perfect inequality (one person has everything)
    
    Args:
        values: List of numeric values (e.g., merge counts, review counts)
    
    Returns:
        Gini coefficient between 0 and 1
    
    Example:
        >>> calculate_gini([10, 10, 10, 10])  # Equal distribution
        0.0
        >>> calculate_gini([1, 0, 0, 0])  # Maximum inequality
        0.75
    """
    if not values or len(values) == 0:
        return 0.0
    
    # Filter out zeros and negatives for meaningful Gini
    values = [v for v in values if v > 0]
    if not values:
        return 0.0
    
    values = sorted(values)
    n = len(values)
    total = sum(values)
    
    if total == 0:
        return 0.0
    
    # Gini formula: G = (2 * sum(i * y_i) - (n + 1) * sum(y_i)) / (n * sum(y_i))
    cumsum = sum((i + 1) * y for i, y in enumerate(values))
    gini = (2 * cumsum - (n + 1) * total) / (n * total)
    
    return float(max(0.0, min(1.0, gini)))  # Clamp to [0, 1]


def calculate_hhi(values: List[float]) -> float:
    """
    Calculate Herfindahl-Hirschman Index (HHI) for market/power concentration.
    
    HHI is the sum of squared market shares:
    - 0.0 = perfect competition (infinite equal players)
    - 1.0 = monopoly (one player has 100%)
    - > 0.25 = highly concentrated
    - 0.15-0.25 = moderately concentrated
    - < 0.15 = unconcentrated
    
    Args:
        values: List of numeric values representing shares or counts
    
    Returns:
        HHI between 0 and 1
    """
    if not values or len(values) == 0:
        return 0.0
    
    total = sum(values)
    if total == 0:
        return 0.0
    
    shares = [v / total for v in values]
    hhi = sum(s ** 2 for s in shares)
    
    return float(hhi)


def calculate_top_n_share(values: List[float], n: int = 10) -> float:
    """
    Calculate the share of total held by top N contributors.
    
    Args:
        values: List of numeric values
        n: Number of top contributors to consider
    
    Returns:
        Share between 0 and 1 (e.g., 0.8 means top N have 80%)
    """
    if not values or len(values) == 0:
        return 0.0
    
    total = sum(values)
    if total == 0:
        return 0.0
    
    sorted_values = sorted(values, reverse=True)
    top_n_sum = sum(sorted_values[:n])
    
    return float(top_n_sum / total)


def calculate_concentration_metrics(values: List[float]) -> Dict[str, float]:
    """
    Calculate comprehensive concentration metrics for a distribution.
    
    Args:
        values: List of numeric values (e.g., contribution counts)
    
    Returns:
        Dictionary with:
        - gini_coefficient: Gini coefficient (0-1)
        - hhi: Herfindahl-Hirschman Index (0-1)
        - top_5_share: Share held by top 5
        - top_10_share: Share held by top 10
        - top_20_share: Share held by top 20
        - concentration_level: 'low', 'moderate', 'high', or 'very_high'
    """
    gini = calculate_gini(values)
    hhi = calculate_hhi(values)
    top_5 = calculate_top_n_share(values, 5)
    top_10 = calculate_top_n_share(values, 10)
    top_20 = calculate_top_n_share(values, 20)
    
    # Determine concentration level based on multiple metrics
    if gini >= 0.8 or hhi >= 0.25 or top_5 >= 0.7:
        level = 'very_high'
    elif gini >= 0.6 or hhi >= 0.15 or top_5 >= 0.5:
        level = 'high'
    elif gini >= 0.4 or hhi >= 0.10 or top_5 >= 0.35:
        level = 'moderate'
    else:
        level = 'low'
    
    return {
        'gini_coefficient': gini,
        'hhi': hhi,
        'top_5_share': top_5,
        'top_10_share': top_10,
        'top_20_share': top_20,
        'concentration_level': level,
        'total_contributors': len([v for v in values if v > 0]),
        'total_value': sum(values)
    }


def calculate_power_concentration_from_counts(
    counts: Dict[str, int],
    top_n: int = 10
) -> Dict[str, Any]:
    """
    Calculate power concentration from a dictionary of actor -> count.
    
    Args:
        counts: Dictionary mapping actor names to their counts
        top_n: Number of top actors to include in detailed breakdown
    
    Returns:
        Dictionary with concentration metrics and top actors
    """
    if not counts:
        return {
            'metrics': calculate_concentration_metrics([]),
            'top_actors': [],
            'total_actors': 0
        }
    
    values = list(counts.values())
    metrics = calculate_concentration_metrics(values)
    
    # Get top actors
    sorted_actors = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    total = sum(values)
    
    top_actors = [
        {
            'actor': actor,
            'count': count,
            'share': count / total if total > 0 else 0.0
        }
        for actor, count in sorted_actors[:top_n]
    ]
    
    return {
        'metrics': metrics,
        'top_actors': top_actors,
        'total_actors': len(counts)
    }


def calculate_temporal_concentration(
    time_period_counts: Dict[str, Dict[str, int]]
) -> Dict[str, Dict[str, float]]:
    """
    Calculate concentration metrics across time periods.
    
    Args:
        time_period_counts: Dictionary mapping period -> {actor: count}
    
    Returns:
        Dictionary mapping period -> concentration metrics
    """
    results = {}
    
    for period, counts in time_period_counts.items():
        if counts:
            values = list(counts.values())
            results[period] = calculate_concentration_metrics(values)
        else:
            results[period] = calculate_concentration_metrics([])
    
    return results


def interpret_gini(gini: float) -> str:
    """
    Provide human-readable interpretation of Gini coefficient.
    
    Args:
        gini: Gini coefficient (0-1)
    
    Returns:
        Interpretation string
    """
    if gini >= 0.9:
        return "Extreme concentration (near-monopoly)"
    elif gini >= 0.8:
        return "Very high concentration"
    elif gini >= 0.6:
        return "High concentration"
    elif gini >= 0.4:
        return "Moderate concentration"
    elif gini >= 0.2:
        return "Low concentration"
    else:
        return "Very low concentration (near-equality)"


def compare_concentration(
    period1_values: List[float],
    period2_values: List[float],
    period1_name: str = "Period 1",
    period2_name: str = "Period 2"
) -> Dict[str, Any]:
    """
    Compare concentration between two periods.
    
    Args:
        period1_values: Values from first period
        period2_values: Values from second period
        period1_name: Label for first period
        period2_name: Label for second period
    
    Returns:
        Dictionary with comparison metrics
    """
    metrics1 = calculate_concentration_metrics(period1_values)
    metrics2 = calculate_concentration_metrics(period2_values)
    
    gini_change = metrics2['gini_coefficient'] - metrics1['gini_coefficient']
    hhi_change = metrics2['hhi'] - metrics1['hhi']
    
    # Determine direction
    if gini_change > 0.05:
        direction = 'increasing'
    elif gini_change < -0.05:
        direction = 'decreasing'
    else:
        direction = 'stable'
    
    return {
        period1_name: metrics1,
        period2_name: metrics2,
        'changes': {
            'gini_change': gini_change,
            'hhi_change': hhi_change,
            'direction': direction,
            'interpretation': f"Power concentration is {direction}"
        }
    }

