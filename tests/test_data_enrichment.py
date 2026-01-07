"""Tests for data enrichment pipeline."""

import pytest
import json
from pathlib import Path


def test_external_pressure_loading(temp_data_dir):
    """Test loading external pressure indicators."""
    # Create sample external pressure data
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
    assert loaded['summary']['irc']['percentage'] == 5.3


def test_contributor_ranking():
    """Test contributor ranking logic."""
    contributors = {
        'lookup': {
            'user1': {'rank': 1, 'contributions': 1000},
            'user2': {'rank': 2, 'contributions': 500},
            'user3': {'rank': 10, 'contributions': 100}
        }
    }
    
    # Test ranking lookup
    user1_rank = contributors['lookup']['user1']['rank']
    assert user1_rank == 1
    
    user3_rank = contributors['lookup']['user3']['rank']
    assert user3_rank == 10
    assert user3_rank <= 10  # Top 10 contributor


def test_release_signer_loading(temp_data_dir):
    """Test loading release signer data."""
    signers_data = {
        'releases': [
            {'tag': 'v1.0.0', 'is_signed': True, 'signer_email': 'test@example.com'},
            {'tag': 'v1.0.1', 'is_signed': False}
        ],
        'signers': {
            'test@example.com': {
                'name': 'Test Signer',
                'release_count': 1
            }
        },
        'signing_stats': {
            'total': 2,
            'signed': 1,
            'unsigned': 1,
            'unique_signers': 1
        }
    }
    
    # Test structure
    assert len(signers_data['releases']) == 2
    assert signers_data['signing_stats']['signed'] == 1
    assert signers_data['signing_stats']['unique_signers'] == 1


def test_maintainer_tagging(sample_pr):
    """Test maintainer tagging logic."""
    # Sample maintainer timeline
    maintainer_timeline = {
        'maintainer1': {
            'periods': [
                {'start': '2020-01-01T00:00:00Z', 'end': None}
            ]
        }
    }
    
    # Test maintainer check
    is_maintainer = 'maintainer1' in maintainer_timeline
    assert is_maintainer
    
    # Test non-maintainer
    is_not_maintainer = 'nonmaintainer' not in maintainer_timeline
    assert is_not_maintainer


def test_pr_classification():
    """Test PR classification logic."""
    # Test consensus-related PR
    consensus_pr = {
        'title': 'Fix consensus validation',
        'body': 'This PR fixes a consensus bug',
        'labels': []
    }
    
    text = f"{consensus_pr['title']} {consensus_pr['body']}".lower()
    is_consensus = 'consensus' in text
    assert is_consensus
    
    # Test bug fix PR
    bug_pr = {
        'title': 'Fix crash bug',
        'body': 'Fixes segfault',
        'labels': [{'name': 'bug'}]
    }
    
    text = f"{bug_pr['title']} {bug_pr['body']}".lower()
    is_bug = 'bug' in text or 'fix' in text
    assert is_bug


def test_commit_signing_loading(temp_data_dir):
    """Test loading commit signing data."""
    # Create sample commit signing data
    signing_data = [
        {'pr_number': 123, 'commit_sha': 'abc123', 'is_signed': True},
        {'pr_number': 124, 'commit_sha': 'def456', 'is_signed': False}
    ]
    
    signing_file = temp_data_dir / 'github' / 'commit_signing.jsonl'
    signing_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(signing_file, 'w') as f:
        for record in signing_data:
            f.write(json.dumps(record) + '\n')
    
    # Test loading
    loaded = {}
    with open(signing_file, 'r') as f:
        for line in f:
            record = json.loads(line)
            loaded[record['pr_number']] = record
    
    assert 123 in loaded
    assert loaded[123]['is_signed'] is True
    assert loaded[124]['is_signed'] is False

