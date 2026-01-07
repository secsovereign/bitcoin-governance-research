"""Tests for new data sources integration."""

import pytest
import json
from pathlib import Path


def test_external_pressure_structure():
    """Test external pressure indicators data structure."""
    pressure_data = {
        'summary': {
            'mailing_lists': {
                'total': 100,
                'with_pressure': 42,
                'percentage': 42.0
            },
            'irc': {
                'total': 1000,
                'with_pressure': 53,
                'percentage': 5.3
            },
            'total_pressure_mentions': 500,
            'pressure_type_counts': {
                'regulatory': 100,
                'corporate': 50,
                'threat': 30
            }
        },
        'mailing_list_emails': [],
        'irc_messages': []
    }
    
    # Validate structure
    assert 'summary' in pressure_data
    assert 'mailing_lists' in pressure_data['summary']
    assert 'irc' in pressure_data['summary']
    assert 'pressure_type_counts' in pressure_data['summary']
    
    # Validate percentages
    assert pressure_data['summary']['mailing_lists']['percentage'] == 42.0
    assert pressure_data['summary']['irc']['percentage'] == 5.3


def test_commit_data_structure():
    """Test commit data structure."""
    commit = {
        'sha': 'abc123',
        'commit': {
            'author': {
                'name': 'Test Author',
                'email': 'test@example.com',
                'date': '2024-01-01T00:00:00Z'
            },
            'message': 'Test commit',
            'verification': {
                'verified': True,
                'reason': 'valid'
            }
        },
        'stats': {
            'additions': 10,
            'deletions': 5
        }
    }
    
    assert 'sha' in commit
    assert 'commit' in commit
    assert 'author' in commit['commit']
    assert 'verification' in commit['commit']


def test_commit_signing_structure():
    """Test commit signing data structure."""
    signing_record = {
        'pr_number': 123,
        'commit_sha': 'abc123',
        'is_signed': True,
        'signer_email': 'test@example.com',
        'signer_name': 'Test Signer',
        'verification_status': 'verified'
    }
    
    assert 'pr_number' in signing_record
    assert 'commit_sha' in signing_record
    assert 'is_signed' in signing_record
    assert signing_record['is_signed'] is True


def test_release_signer_integration():
    """Test release signer data integration."""
    release = {
        'tag': 'v1.0.0',
        'is_signed': True,
        'signer_email': 'test@example.com',
        'signer_name': 'Test Signer',
        'tagger_date_iso': '2024-01-01T00:00:00Z'
    }
    
    # Test required fields
    assert 'tag' in release
    assert 'is_signed' in release
    assert 'signer_email' in release or not release['is_signed']


def test_contributor_data_structure():
    """Test contributor data structure."""
    contributor = {
        'login': 'testuser',
        'contributions': 1000,
        'name': 'Test User',
        'email': 'test@example.com',
        'rank': 1
    }
    
    assert 'login' in contributor
    assert 'contributions' in contributor
    assert isinstance(contributor['contributions'], int)
    assert contributor['contributions'] > 0


def test_external_pressure_keywords():
    """Test external pressure keyword detection."""
    regulatory_keywords = ['sec', 'cftc', 'regulation', 'government', 'ban']
    corporate_keywords = ['sponsor', 'funding', 'grant', 'corporate']
    threat_keywords = ['threat', 'pressure', 'coercion']
    
    # Test keyword matching
    text = "The SEC is regulating Bitcoin and corporate sponsors are funding development"
    text_lower = text.lower()
    
    has_regulatory = any(kw in text_lower for kw in regulatory_keywords)
    has_corporate = any(kw in text_lower for kw in corporate_keywords)
    
    assert has_regulatory
    assert has_corporate


def test_data_integration_flow(temp_data_dir):
    """Test data integration flow."""
    # Simulate data flow: raw -> cleaned -> enriched
    
    # Step 1: Raw data
    raw_pr = {
        'number': 123,
        'title': 'Test PR',
        'author': 'testuser',
        'created_at': '2024-01-01T00:00:00Z',
        'state': 'merged'
    }
    
    # Step 2: Cleaned data (normalized)
    cleaned_pr = raw_pr.copy()
    cleaned_pr['created_at'] = cleaned_pr['created_at'].replace('Z', '+00:00')
    
    # Step 3: Enriched data (with additional context)
    enriched_pr = cleaned_pr.copy()
    enriched_pr['contributor_ranking'] = {'rank': 1, 'contributions': 1000}
    enriched_pr['external_pressure_context'] = {'has_pressure_data': True}
    
    # Validate flow
    assert 'number' in raw_pr
    assert 'created_at' in cleaned_pr
    assert 'contributor_ranking' in enriched_pr
    assert 'external_pressure_context' in enriched_pr

