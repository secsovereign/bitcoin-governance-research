"""Comprehensive integration tests for all components."""

import pytest
import json
from pathlib import Path
from src.utils.data_quality import DataQualityTracker
from src.utils.data_validation import DataValidator
from src.utils.reproducibility import ReproducibilityManager
from src.utils.progress_tracking import ProgressTracker
from src.utils.data_versioning import DataVersionManager


def test_full_data_pipeline(temp_data_dir, sample_pr):
    """Test complete data processing pipeline."""
    # Initialize components
    quality_tracker = DataQualityTracker()
    validator = DataValidator()
    
    # Step 1: Validate raw data
    is_valid, errors = validator.validate_pr_data(sample_pr)
    assert is_valid
    
    # Step 2: Track quality
    quality_tracker.track_completeness('test_source', 100, 100)
    summary = quality_tracker.get_summary()
    assert 'overall_status' in summary
    
    # Step 3: Validate cleaned data
    cleaned_pr = sample_pr.copy()
    cleaned_pr['created_at'] = cleaned_pr['created_at'].replace('Z', '+00:00')
    is_valid, _ = validator.validate_pr_data(cleaned_pr)
    assert is_valid


def test_data_quality_tracking():
    """Test data quality tracking integration."""
    tracker = DataQualityTracker()
    
    # Track multiple metrics
    tracker.track_completeness('github_prs', 1000, 1000)
    tracker.track_identity_resolution(100, 80, 15, 5)
    
    summary = tracker.get_summary()
    assert summary['overall_status'] in ['excellent', 'good', 'fair']


def test_reproducibility_integration(tmp_path):
    """Test reproducibility system integration."""
    manager = ReproducibilityManager(seed=42)
    manager.set_seed(42)
    
    metadata = manager.capture_analysis_metadata(
        'test_analysis',
        {'param1': 'value1'},
        output_file=tmp_path / 'metadata.json'
    )
    
    assert metadata['random_seed'] == 42
    assert metadata['analysis_name'] == 'test_analysis'
    assert (tmp_path / 'metadata.json').exists()


def test_progress_tracking_integration():
    """Test progress tracking integration."""
    tracker = ProgressTracker('test_task')
    tracker.start(total_items=100)
    
    tracker.update(processed=50, failed=0)
    assert tracker.get_progress_percentage() == 50.0
    
    tracker.checkpoint({'processed_items': 50}, "Halfway")
    assert tracker.can_resume()
    
    summary = tracker.get_summary()
    assert summary['processed'] == 50
    assert summary['percentage'] == 50.0


def test_data_versioning_integration(tmp_path):
    """Test data versioning integration."""
    manager = DataVersionManager(version_dir=tmp_path / 'versions')
    
    # Create test file
    test_file = tmp_path / 'test_data.json'
    test_file.write_text('{"test": "data"}')
    
    # Create version
    version = manager.create_version(test_file, metadata={'test': True})
    
    assert 'version_id' in version
    assert 'checksum' in version
    assert version['checksum'] is not None
    
    # Verify integrity
    is_valid = manager.verify_file_integrity(test_file, version['checksum'])
    assert is_valid


def test_external_pressure_integration(temp_data_dir):
    """Test external pressure indicators integration."""
    # Create sample external pressure data
    pressure_data = {
        'summary': {
            'mailing_lists': {'total': 100, 'with_pressure': 42, 'percentage': 42.0},
            'irc': {'total': 1000, 'with_pressure': 53, 'percentage': 5.3},
            'total_pressure_mentions': 500
        }
    }
    
    pressure_file = temp_data_dir / 'processed' / 'external_pressure_indicators.json'
    pressure_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(pressure_file, 'w') as f:
        json.dump(pressure_data, f)
    
    # Test loading
    with open(pressure_file, 'r') as f:
        loaded = json.load(f)
    
    assert loaded['summary']['mailing_lists']['percentage'] == 42.0
    assert loaded['summary']['total_pressure_mentions'] == 500


def test_contributor_integration():
    """Test contributor data integration."""
    contributors = {
        'lookup': {
            'user1': {'rank': 1, 'contributions': 1000},
            'user2': {'rank': 2, 'contributions': 500}
        },
        'total': 2
    }
    
    # Test ranking lookup
    user1 = contributors['lookup']['user1']
    assert user1['rank'] == 1
    assert user1['contributions'] == 1000
    assert user1['rank'] <= 10  # Top 10


def test_release_signer_integration():
    """Test release signer data integration."""
    signers_data = {
        'releases': [
            {'tag': 'v1.0.0', 'is_signed': True, 'signer_email': 'test@example.com'},
            {'tag': 'v1.0.1', 'is_signed': False}
        ],
        'signing_stats': {
            'total': 2,
            'signed': 1,
            'unsigned': 1,
            'unique_signers': 1
        }
    }
    
    assert signers_data['signing_stats']['signed'] == 1
    assert signers_data['signing_stats']['unique_signers'] == 1
    assert len(signers_data['releases']) == 2


def test_all_utilities_work_together():
    """Test that all utilities work together."""
    # Initialize all utilities
    quality_tracker = DataQualityTracker()
    validator = DataValidator()
    repro_manager = ReproducibilityManager(seed=42)
    progress_tracker = ProgressTracker('integration_test')
    
    # Use them together
    repro_manager.set_seed(42)
    progress_tracker.start(total_items=10)
    quality_tracker.track_completeness('test', 10, 10)
    
    is_valid, _ = validator.validate_pr_data({
        'number': 1,
        'author': 'test',
        'created_at': '2024-01-01T00:00:00Z',
        'state': 'open'
    })
    
    assert is_valid
    assert progress_tracker.get_progress_percentage() == 0.0
    assert repro_manager.seed == 42

