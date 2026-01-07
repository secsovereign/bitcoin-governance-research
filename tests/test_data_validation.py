"""Tests for data validation."""

import pytest
import json
from pathlib import Path
from src.utils.data_validation import DataValidator


def test_validate_pr_data(sample_pr):
    """Test PR data validation."""
    validator = DataValidator()
    is_valid, errors = validator.validate_pr_data(sample_pr)
    
    assert is_valid
    assert len(errors) == 0


def test_validate_pr_data_missing_fields():
    """Test PR validation with missing fields."""
    validator = DataValidator()
    invalid_pr = {'number': 123}
    is_valid, errors = validator.validate_pr_data(invalid_pr)
    
    assert not is_valid
    assert len(errors) > 0
    assert any('author' in error for error in errors)


def test_validate_pr_data_invalid_timestamp():
    """Test PR validation with invalid timestamp."""
    validator = DataValidator()
    invalid_pr = {
        'number': 123,
        'author': 'test',
        'created_at': 'invalid-date',
        'state': 'open'
    }
    is_valid, errors = validator.validate_pr_data(invalid_pr)
    
    assert not is_valid
    assert any('timestamp' in error for error in errors)


def test_validate_identity_mapping(sample_identity_mapping):
    """Test identity mapping validation."""
    validator = DataValidator()
    is_valid, errors = validator.validate_identity_mapping(sample_identity_mapping)
    
    assert is_valid
    assert len(errors) == 0


def test_validate_maintainer_timeline(sample_maintainer_timeline):
    """Test maintainer timeline validation."""
    validator = DataValidator()
    is_valid, errors = validator.validate_maintainer_timeline(sample_maintainer_timeline)
    
    assert is_valid
    assert len(errors) == 0


def test_validate_jsonl_file(sample_prs_jsonl):
    """Test JSONL file validation."""
    validator = DataValidator()
    report = validator.validate_jsonl_file(
        sample_prs_jsonl,
        required_fields=['number', 'author', 'state']
    )
    
    assert report['valid']
    assert report['valid_records'] == 2
    assert report['invalid_records'] == 0


def test_check_duplicates(temp_data_dir):
    """Test duplicate checking."""
    validator = DataValidator()
    
    # Create file with duplicates
    prs_file = temp_data_dir / 'processed' / 'cleaned_prs.jsonl'
    prs_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(prs_file, 'w') as f:
        # Write same PR twice
        pr = {'number': 1, 'author': 'test', 'state': 'merged'}
        f.write(json.dumps(pr) + '\n')
        f.write(json.dumps(pr) + '\n')
    
    result = validator._check_duplicates(temp_data_dir)
    assert result['found']
    assert result['count'] > 0

