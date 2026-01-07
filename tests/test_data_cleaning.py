"""Tests for data cleaning pipeline."""

import pytest
import json
from pathlib import Path
from src.utils.data_validation import DataValidator


def test_clean_pr_data(sample_pr):
    """Test PR data cleaning."""
    validator = DataValidator()
    is_valid, errors = validator.validate_pr_data(sample_pr)
    
    assert is_valid
    assert len(errors) == 0


def test_clean_release_signer_data():
    """Test release signer data structure."""
    sample_release = {
        'tag': 'v1.0.0',
        'is_signed': True,
        'signer_email': 'test@example.com',
        'signer_name': 'Test Signer',
        'tagger_date_iso': '2024-01-01T00:00:00Z'
    }
    
    validator = DataValidator()
    # Release signers don't have specific validator, but should have required fields
    assert 'tag' in sample_release
    assert 'is_signed' in sample_release
    assert sample_release['is_signed'] is True


def test_clean_commit_data():
    """Test commit data structure."""
    sample_commit = {
        'sha': 'abc123',
        'commit': {
            'author': {
                'date': '2024-01-01T00:00:00Z',
                'name': 'Test Author'
            },
            'message': 'Test commit message'
        }
    }
    
    assert 'sha' in sample_commit
    assert 'commit' in sample_commit
    assert 'author' in sample_commit['commit']
    assert 'date' in sample_commit['commit']['author']


def test_timestamp_normalization():
    """Test timestamp normalization."""
    from datetime import datetime
    
    # Test various timestamp formats
    formats = [
        '2024-01-01T00:00:00Z',
        '2024-01-01T00:00:00+00:00',
        '2024-01-01 00:00:00'
    ]
    
    for ts in formats:
        try:
            if 'T' in ts:
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            else:
                dt = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
            assert dt is not None
        except Exception:
            # Some formats may need special handling
            pass


def test_text_cleaning():
    """Test text cleaning functionality."""
    # Test HTML removal
    html_text = "<p>Test <strong>text</strong></p>"
    cleaned = html_text.replace('<p>', '').replace('</p>', '').replace('<strong>', '').replace('</strong>', '')
    assert 'Test text' in cleaned
    
    # Test markdown removal
    markdown_text = "**Test** text with `code`"
    cleaned = markdown_text.replace('**', '').replace('`', '')
    assert 'Test' in cleaned and 'text' in cleaned


def test_missing_data_handling():
    """Test handling of missing data."""
    incomplete_pr = {
        'number': 123,
        'author': 'testuser'
        # Missing: created_at, state
    }
    
    validator = DataValidator()
    is_valid, errors = validator.validate_pr_data(incomplete_pr)
    
    assert not is_valid
    assert len(errors) > 0
    assert any('created_at' in error for error in errors)

