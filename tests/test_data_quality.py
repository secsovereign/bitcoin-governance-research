"""Tests for data quality tracking."""

import pytest
from src.utils.data_quality import DataQualityTracker


def test_data_quality_tracker_initialization():
    """Test DataQualityTracker initialization."""
    tracker = DataQualityTracker()
    assert tracker.metrics is not None
    assert 'collection_date' in tracker.metrics


def test_track_completeness():
    """Test completeness tracking."""
    tracker = DataQualityTracker()
    tracker.track_completeness('test_source', 100, 100)
    
    assert 'test_source' in tracker.metrics['completeness']
    assert tracker.metrics['completeness']['test_source']['percentage'] == 100.0
    assert tracker.metrics['completeness']['test_source']['status'] == 'complete'


def test_track_identity_resolution():
    """Test identity resolution tracking."""
    tracker = DataQualityTracker()
    tracker.track_identity_resolution(
        total_identities=100,
        high_confidence=80,
        medium_confidence=15,
        low_confidence=5,
        unmatched=0
    )
    
    assert tracker.metrics['identity_resolution']['total_identities'] == 100
    assert tracker.metrics['identity_resolution']['high_confidence_rate'] == 80.0
    assert tracker.metrics['identity_resolution']['match_rate'] == 100.0


def test_get_summary():
    """Test quality summary generation."""
    tracker = DataQualityTracker()
    tracker.track_completeness('test', 100, 100)
    tracker.track_identity_resolution(100, 80, 15, 5)
    
    summary = tracker.get_summary()
    assert 'overall_status' in summary
    assert 'metrics' in summary
    assert 'recommendations' in summary


def test_overall_status_calculation():
    """Test overall status calculation."""
    tracker = DataQualityTracker()
    
    # Good status
    tracker.track_completeness('test1', 100, 100)
    tracker.track_identity_resolution(100, 90, 10, 0)
    status = tracker._calculate_overall_status()
    assert status in ['excellent', 'good']


def test_save_report(tmp_path):
    """Test saving quality report."""
    tracker = DataQualityTracker()
    tracker.track_completeness('test', 100, 100)
    
    output_path = tmp_path / 'quality_report.json'
    tracker.save_report(output_path)
    
    assert output_path.exists()
    
    # Verify can load
    loaded = tracker.load_report(output_path)
    assert 'overall_status' in loaded

