"""Pytest configuration and fixtures."""

import pytest
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, Generator
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir, get_analysis_dir


@pytest.fixture
def temp_data_dir() -> Generator[Path, None, None]:
    """Create temporary data directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir) / 'data'
        data_dir.mkdir(parents=True)
        yield data_dir


@pytest.fixture
def sample_pr() -> Dict[str, Any]:
    """Sample PR data for testing."""
    return {
        'number': 12345,
        'title': 'Test PR',
        'body': 'This is a test PR',
        'author': 'testuser',
        'state': 'merged',
        'created_at': '2024-01-01T00:00:00Z',
        'merged_at': '2024-01-02T00:00:00Z',
        'additions': 100,
        'deletions': 50,
        'reviews': [],
        'comments': []
    }


@pytest.fixture
def sample_prs_jsonl(temp_data_dir: Path) -> Path:
    """Create sample PRs JSONL file."""
    prs_file = temp_data_dir / 'github' / 'prs_raw.jsonl'
    prs_file.parent.mkdir(parents=True, exist_ok=True)
    
    sample_prs = [
        {
            'number': 1,
            'title': 'PR 1',
            'author': 'user1',
            'state': 'merged',
            'created_at': '2024-01-01T00:00:00Z',
            'merged_at': '2024-01-02T00:00:00Z'
        },
        {
            'number': 2,
            'title': 'PR 2',
            'author': 'user2',
            'state': 'closed',
            'created_at': '2024-01-03T00:00:00Z',
            'closed_at': '2024-01-04T00:00:00Z'
        }
    ]
    
    with open(prs_file, 'w') as f:
        for pr in sample_prs:
            f.write(json.dumps(pr) + '\n')
    
    return prs_file


@pytest.fixture
def sample_identity_mapping() -> Dict[str, Any]:
    """Sample identity mapping for testing."""
    return {
        'unified_1': {
            'github': ['user1', 'user1_alt'],
            'email': ['user1@example.com'],
            'irc': ['user1_nick']
        },
        'unified_2': {
            'github': ['user2'],
            'email': ['user2@example.com']
        }
    }


@pytest.fixture
def sample_maintainer_timeline() -> Dict[str, Any]:
    """Sample maintainer timeline for testing."""
    return {
        'maintainer_timeline': {
            'unified_1': {
                'estimated_start': '2020-01-01T00:00:00Z',
                'estimated_end': None,
                'confidence': 'high',
                'periods': [
                    {
                        'start': '2020-01-01T00:00:00Z',
                        'end': None,
                        'type': 'inferred'
                    }
                ],
                'merge_count': 100
            }
        }
    }


@pytest.fixture
def logger():
    """Setup logger for tests."""
    return setup_logger('test', log_level='WARNING')

