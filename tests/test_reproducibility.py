"""Tests for reproducibility system."""

import pytest
import numpy as np
from pathlib import Path
from src.utils.reproducibility import (
    ReproducibilityManager,
    get_reproducibility_manager,
    set_global_seed
)


def test_reproducibility_manager_initialization():
    """Test ReproducibilityManager initialization."""
    manager = ReproducibilityManager(seed=42)
    assert manager.seed == 42
    assert 'environment' in manager.reproducibility_info


def test_set_seed():
    """Test setting random seed."""
    manager = ReproducibilityManager(seed=123)
    manager.set_seed(123)
    
    # Generate some random numbers
    np_values = np.random.rand(5)
    
    # Reset and regenerate - should be same
    manager.set_seed(123)
    np_values2 = np.random.rand(5)
    
    assert np.allclose(np_values, np_values2)


def test_capture_analysis_metadata(tmp_path):
    """Test capturing analysis metadata."""
    manager = ReproducibilityManager(seed=42)
    
    metadata = manager.capture_analysis_metadata(
        'test_analysis',
        {'param1': 'value1'},
        output_file=tmp_path / 'metadata.json'
    )
    
    assert metadata['analysis_name'] == 'test_analysis'
    assert metadata['random_seed'] == 42
    assert 'timestamp' in metadata
    assert 'environment' in metadata
    
    # Verify file was created
    assert (tmp_path / 'metadata.json').exists()


def test_load_analysis_metadata(tmp_path):
    """Test loading analysis metadata."""
    manager = ReproducibilityManager(seed=42)
    
    # Create metadata file
    metadata_file = tmp_path / 'metadata.json'
    manager.capture_analysis_metadata(
        'test_analysis',
        {'param1': 'value1'},
        output_file=metadata_file
    )
    
    # Load it
    loaded = manager.load_analysis_metadata(metadata_file)
    assert loaded['analysis_name'] == 'test_analysis'
    assert loaded['random_seed'] == 42


def test_create_reproducibility_report(tmp_path):
    """Test creating reproducibility report."""
    manager = ReproducibilityManager(seed=42)
    
    report_file = manager.create_reproducibility_report(
        'test_analysis',
        output_dir=tmp_path
    )
    
    assert report_file.exists()
    
    # Verify content
    import json
    with open(report_file, 'r') as f:
        report = json.load(f)
    
    assert report['analysis_name'] == 'test_analysis'
    assert report['random_seed'] == 42
    assert 'environment' in report


def test_get_reproducibility_manager():
    """Test global reproducibility manager."""
    manager1 = get_reproducibility_manager(seed=42)
    manager2 = get_reproducibility_manager(seed=42)
    
    # Should be same instance
    assert manager1 is manager2


def test_set_global_seed():
    """Test setting global seed."""
    set_global_seed(999)
    manager = get_reproducibility_manager()
    assert manager.seed == 999

