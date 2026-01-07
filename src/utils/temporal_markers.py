"""Temporal event markers for Bitcoin Core history."""

from typing import List, Dict, Any
from datetime import datetime

# Major events in Bitcoin Core history
TEMPORAL_EVENTS = [
    {
        'date': '2010-08-15',
        'event': 'inflation_bug',
        'description': 'Value overflow incident (CVE-2010-5139)',
        'category': 'security'
    },
    {
        'date': '2013-03-11',
        'event': 'version_0.8_split',
        'description': 'Version 0.8 chain split',
        'category': 'consensus'
    },
    {
        'date': '2015-08-01',
        'event': 'blocksize_wars_start',
        'description': 'Blocksize wars begin',
        'category': 'governance'
    },
    {
        'date': '2017-08-01',
        'event': 'segwit_activation',
        'description': 'SegWit activated',
        'category': 'consensus'
    },
    {
        'date': '2017-08-01',
        'event': 'bitcoin_cash_fork',
        'description': 'Bitcoin Cash fork',
        'category': 'governance'
    },
    {
        'date': '2018-09-17',
        'event': 'inflation_bug_2018',
        'description': 'CVE-2018-17144 inflation bug',
        'category': 'security'
    },
    {
        'date': '2021-11-14',
        'event': 'taproot_activation',
        'description': 'Taproot activated',
        'category': 'consensus'
    },
    {
        'date': '2022-06-01',
        'event': 'luke_maintainer_removal',
        'description': 'Luke Dashjr maintainer access removed',
        'category': 'governance'
    }
]


def get_events_in_period(start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    Get events in date range.
    
    Args:
        start_date: Start date (ISO format)
        end_date: End date (ISO format)
    
    Returns:
        List of events in the period
    """
    start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
    end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    
    events = []
    for event in TEMPORAL_EVENTS:
        event_date = datetime.fromisoformat(event['date'])
        if start <= event_date <= end:
            events.append(event)
    
    return events


def get_event_by_name(event_name: str) -> Dict[str, Any]:
    """Get event by name."""
    for event in TEMPORAL_EVENTS:
        if event['event'] == event_name:
            return event
    return {}


def get_events_by_category(category: str) -> List[Dict[str, Any]]:
    """Get events by category."""
    return [e for e in TEMPORAL_EVENTS if e.get('category') == category]

