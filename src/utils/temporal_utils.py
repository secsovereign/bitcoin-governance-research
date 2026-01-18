"""Temporal analysis utilities for governance research.

Provides reusable functions for time-based analysis:
- Period grouping (yearly, quarterly, by era)
- Trend calculation
- Cohort analysis utilities
"""

from typing import Dict, Any, List, Optional, Tuple, Callable
from datetime import datetime, timezone
from collections import defaultdict


# Era definitions for Bitcoin Core
GOVERNANCE_ERAS = {
    'satoshi': ('2009-01-03', '2011-04-23'),      # Satoshi active
    'early': ('2011-04-24', '2014-12-31'),        # Early post-Satoshi
    'transition': ('2015-01-01', '2017-08-23'),   # SegWit period
    'modern': ('2017-08-24', '2021-11-13'),       # Post-SegWit to Taproot
    'current': ('2021-11-14', '2099-12-31')       # Post-Taproot
}


def parse_date(date_str: str) -> Optional[datetime]:
    """
    Parse a date string into a datetime object.
    
    Handles various formats commonly found in GitHub/email data.
    
    Args:
        date_str: Date string in ISO format or similar
    
    Returns:
        datetime object (timezone-aware) or None if parsing fails
    """
    if not date_str:
        return None
    
    try:
        # Handle Z suffix
        if date_str.endswith('Z'):
            date_str = date_str[:-1] + '+00:00'
        
        dt = datetime.fromisoformat(date_str)
        
        # Ensure timezone-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        return dt
    except (ValueError, TypeError):
        return None


def get_year(date_str: str) -> Optional[int]:
    """Extract year from date string."""
    dt = parse_date(date_str)
    return dt.year if dt else None


def get_quarter(date_str: str) -> Optional[str]:
    """Get quarter string (e.g., '2023-Q1') from date string."""
    dt = parse_date(date_str)
    if not dt:
        return None
    quarter = (dt.month - 1) // 3 + 1
    return f"{dt.year}-Q{quarter}"


def get_year_month(date_str: str) -> Optional[str]:
    """Get year-month string (e.g., '2023-01') from date string."""
    dt = parse_date(date_str)
    return f"{dt.year}-{dt.month:02d}" if dt else None


def get_era(date_str: str) -> Optional[str]:
    """
    Determine which governance era a date falls into.
    
    Args:
        date_str: Date string
    
    Returns:
        Era name ('satoshi', 'early', 'transition', 'modern', 'current')
    """
    dt = parse_date(date_str)
    if not dt:
        return None
    
    for era_name, (start_str, end_str) in GOVERNANCE_ERAS.items():
        start = datetime.fromisoformat(start_str).replace(tzinfo=timezone.utc)
        end = datetime.fromisoformat(end_str).replace(tzinfo=timezone.utc)
        if start <= dt <= end:
            return era_name
    
    return 'unknown'


def group_by_period(
    items: List[Dict[str, Any]],
    date_field: str,
    period_type: str = 'year'
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Group items by time period.
    
    Args:
        items: List of dictionaries containing date field
        date_field: Name of the field containing the date
        period_type: 'year', 'quarter', 'month', or 'era'
    
    Returns:
        Dictionary mapping period -> list of items
    """
    period_funcs = {
        'year': lambda d: str(get_year(d)) if get_year(d) else None,
        'quarter': get_quarter,
        'month': get_year_month,
        'era': get_era
    }
    
    period_func = period_funcs.get(period_type, period_funcs['year'])
    
    grouped = defaultdict(list)
    for item in items:
        date_str = item.get(date_field)
        if date_str:
            period = period_func(date_str)
            if period:
                grouped[period].append(item)
    
    return dict(grouped)


def count_by_period(
    items: List[Dict[str, Any]],
    date_field: str,
    period_type: str = 'year'
) -> Dict[str, int]:
    """
    Count items by time period.
    
    Args:
        items: List of items with date field
        date_field: Name of the date field
        period_type: 'year', 'quarter', 'month', or 'era'
    
    Returns:
        Dictionary mapping period -> count
    """
    grouped = group_by_period(items, date_field, period_type)
    return {period: len(items) for period, items in grouped.items()}


def count_by_actor_by_period(
    items: List[Dict[str, Any]],
    date_field: str,
    actor_field: str,
    period_type: str = 'year'
) -> Dict[str, Dict[str, int]]:
    """
    Count items by actor within each period.
    
    Args:
        items: List of items
        date_field: Name of the date field
        actor_field: Name of the actor field
        period_type: 'year', 'quarter', 'month', or 'era'
    
    Returns:
        Dictionary mapping period -> {actor: count}
    """
    grouped = group_by_period(items, date_field, period_type)
    
    result = {}
    for period, period_items in grouped.items():
        actor_counts = defaultdict(int)
        for item in period_items:
            actor = item.get(actor_field)
            if actor:
                actor_counts[actor.lower()] += 1
        result[period] = dict(actor_counts)
    
    return result


def calculate_rate_by_period(
    numerator_items: List[Dict[str, Any]],
    denominator_items: List[Dict[str, Any]],
    date_field: str,
    period_type: str = 'year'
) -> Dict[str, float]:
    """
    Calculate rate (numerator/denominator) by period.
    
    Args:
        numerator_items: Items for numerator count
        denominator_items: Items for denominator count
        date_field: Date field name
        period_type: Period grouping type
    
    Returns:
        Dictionary mapping period -> rate
    """
    num_counts = count_by_period(numerator_items, date_field, period_type)
    denom_counts = count_by_period(denominator_items, date_field, period_type)
    
    all_periods = set(num_counts.keys()) | set(denom_counts.keys())
    
    rates = {}
    for period in all_periods:
        num = num_counts.get(period, 0)
        denom = denom_counts.get(period, 0)
        rates[period] = num / denom if denom > 0 else 0.0
    
    return rates


def calculate_trend(
    period_values: Dict[str, float],
    window: int = 3
) -> Dict[str, Any]:
    """
    Calculate trend from period values.
    
    Args:
        period_values: Dictionary mapping period -> value
        window: Number of periods for moving average
    
    Returns:
        Dictionary with trend analysis
    """
    if not period_values:
        return {'trend': 'unknown', 'change': 0.0}
    
    sorted_periods = sorted(period_values.keys())
    values = [period_values[p] for p in sorted_periods]
    
    if len(values) < 2:
        return {'trend': 'unknown', 'change': 0.0}
    
    # Calculate overall change
    first_value = values[0]
    last_value = values[-1]
    change = last_value - first_value
    pct_change = (change / first_value * 100) if first_value != 0 else 0.0
    
    # Determine trend direction
    if len(values) >= window:
        recent_avg = sum(values[-window:]) / window
        early_avg = sum(values[:window]) / window
        if recent_avg > early_avg * 1.1:
            trend = 'increasing'
        elif recent_avg < early_avg * 0.9:
            trend = 'decreasing'
        else:
            trend = 'stable'
    else:
        if change > 0:
            trend = 'increasing'
        elif change < 0:
            trend = 'decreasing'
        else:
            trend = 'stable'
    
    return {
        'trend': trend,
        'absolute_change': change,
        'percent_change': pct_change,
        'first_period': sorted_periods[0],
        'last_period': sorted_periods[-1],
        'first_value': first_value,
        'last_value': last_value,
        'period_count': len(values)
    }


def analyze_cohort_retention(
    items: List[Dict[str, Any]],
    join_date_field: str,
    activity_date_field: str,
    actor_field: str,
    inactivity_threshold_days: int = 365
) -> Dict[str, Any]:
    """
    Analyze cohort retention patterns.
    
    Args:
        items: List of activity items
        join_date_field: Field containing first activity date
        activity_date_field: Field containing activity date
        actor_field: Field containing actor identifier
        inactivity_threshold_days: Days of inactivity to consider "exited"
    
    Returns:
        Dictionary with cohort retention analysis
    """
    from datetime import timedelta
    
    # Build actor profiles
    actors = defaultdict(lambda: {'first': None, 'last': None, 'count': 0})
    
    for item in items:
        actor = item.get(actor_field)
        if not actor:
            continue
        
        date_str = item.get(activity_date_field)
        dt = parse_date(date_str)
        if not dt:
            continue
        
        actor_data = actors[actor.lower()]
        actor_data['count'] += 1
        
        if actor_data['first'] is None or dt < actor_data['first']:
            actor_data['first'] = dt
        if actor_data['last'] is None or dt > actor_data['last']:
            actor_data['last'] = dt
    
    # Analyze by join year
    reference_date = datetime.now(timezone.utc)
    threshold = timedelta(days=inactivity_threshold_days)
    
    cohorts = defaultdict(lambda: {'joined': 0, 'active': 0, 'exited': 0})
    
    for actor, data in actors.items():
        if data['first'] is None:
            continue
        
        join_year = str(data['first'].year)
        cohorts[join_year]['joined'] += 1
        
        if data['last'] and (reference_date - data['last']) < threshold:
            cohorts[join_year]['active'] += 1
        else:
            cohorts[join_year]['exited'] += 1
    
    # Calculate retention rates
    cohort_analysis = {}
    for year, data in sorted(cohorts.items()):
        retention_rate = data['active'] / data['joined'] if data['joined'] > 0 else 0.0
        cohort_analysis[year] = {
            'joined': data['joined'],
            'active': data['active'],
            'exited': data['exited'],
            'retention_rate': retention_rate,
            'exit_rate': 1 - retention_rate
        }
    
    return cohort_analysis


def calculate_moving_average(
    period_values: Dict[str, float],
    window: int = 3
) -> Dict[str, float]:
    """
    Calculate moving average over periods.
    
    Args:
        period_values: Dictionary mapping period -> value
        window: Window size for moving average
    
    Returns:
        Dictionary mapping period -> moving average
    """
    sorted_periods = sorted(period_values.keys())
    values = [period_values[p] for p in sorted_periods]
    
    if len(values) < window:
        return period_values.copy()
    
    result = {}
    for i, period in enumerate(sorted_periods):
        if i < window - 1:
            # Not enough data for full window
            result[period] = sum(values[:i+1]) / (i + 1)
        else:
            result[period] = sum(values[i-window+1:i+1]) / window
    
    return result

