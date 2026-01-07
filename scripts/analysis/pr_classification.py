#!/usr/bin/env python3
"""
PR Classification System: Classify PRs by type and importance

Creates a matrix of PR importance vs review quality to provide
nuanced analysis of review requirements.
"""

import json
import re
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, Any, Tuple
from enum import Enum

class PRImportance(Enum):
    """PR importance levels."""
    TRIVIAL = "trivial"  # Typo fixes, formatting, trivial changes
    LOW = "low"  # Documentation, tests, housekeeping
    NORMAL = "normal"  # Regular code changes
    HIGH = "high"  # Significant features, refactoring
    CRITICAL = "critical"  # Consensus changes, security, protocol changes

class ReviewQuality(Enum):
    """Review quality levels."""
    NONE = "none"  # No review
    LOW = "low"  # Simple ACK, minimal review (0.2-0.4)
    MEDIUM = "medium"  # Some review, ACK with context (0.5-0.7)
    HIGH = "high"  # Detailed review (0.8-1.0)

# Classification patterns
HOUSEKEEPING_KEYWORDS = [
    'typo', 'fix typo', 'typos', 'spelling', 'grammar',
    'doc', 'docs', 'documentation', 'readme', 'comment',
    'format', 'formatting', 'whitespace', 'style', 'lint',
    'refactor', 'cleanup', 'clean up', 'remove unused',
    'test', 'tests', 'test:',
    'ci', 'travis', 'github actions',
    'bump', 'update', 'dependencies'
]

CRITICAL_KEYWORDS = [
    'consensus', 'consensus change', 'consensus rule',
    'validation', 'verify', 'check',
    'security', 'vulnerability', 'exploit', 'attack',
    'rpc', 'api', 'interface',
    'network', 'p2p', 'protocol',
    'wallet', 'keys', 'signature',
    'mining', 'block', 'transaction',
    'fee', 'mempool', 'policy',
    'refactor', 'refactoring'
]

def classify_pr_importance(pr: Dict[str, Any]) -> PRImportance:
    """
    Classify PR by importance level.
    
    Returns:
        PRImportance enum value
    """
    title = (pr.get('title', '') or '').lower()
    body = (pr.get('body', '') or '').lower()
    text = title + ' ' + body
    
    # Check file changes
    files = pr.get('files', []) or pr.get('changed_files', []) or []
    additions = pr.get('additions', 0) or 0
    deletions = pr.get('deletions', 0) or 0
    total_changes = additions + deletions
    
    # Check labels
    labels = [l.get('name', '').lower() if isinstance(l, dict) else str(l).lower() 
              for l in (pr.get('labels', []) or [])]
    
    # Critical indicators
    is_critical = (
        any(kw in text for kw in CRITICAL_KEYWORDS) or
        any('consensus' in l or 'security' in l or 'critical' in l for l in labels) or
        total_changes > 1000
    )
    
    if is_critical:
        return PRImportance.CRITICAL
    
    # Housekeeping indicators
    is_housekeeping = (
        any(kw in text for kw in HOUSEKEEPING_KEYWORDS) or
        any('doc' in l or 'test' in l or 'trivial' in l for l in labels)
    )
    
    # File-based classification
    file_types = set()
    for f in files:
        if isinstance(f, dict):
            filename = f.get('filename', '') or f.get('path', '')
        else:
            filename = str(f)
        
        if filename.endswith(('.md', '.txt', '.rst', '.tex')):
            file_types.add('docs')
        elif 'test' in filename.lower() or filename.endswith('_test.cpp') or filename.endswith('_tests.cpp'):
            file_types.add('tests')
        elif filename.endswith(('.h', '.cpp', '.c')):
            file_types.add('code')
    
    # Size-based classification
    if total_changes < 5:
        size = 'trivial'
    elif total_changes < 50:
        size = 'small'
    elif total_changes < 200:
        size = 'medium'
    else:
        size = 'large'
    
    # Classification logic
    if is_housekeeping and total_changes < 10:
        return PRImportance.TRIVIAL
    elif is_housekeeping or (len(file_types) == 1 and 'docs' in file_types):
        return PRImportance.LOW
    elif size == 'large' or total_changes > 500:
        return PRImportance.HIGH
    elif size == 'trivial' and total_changes < 5:
        return PRImportance.TRIVIAL
    else:
        return PRImportance.NORMAL

def classify_review_quality(weighted_score: float) -> ReviewQuality:
    """
    Classify review quality based on weighted score.
    
    Args:
        weighted_score: Quality-weighted review count
        
    Returns:
        ReviewQuality enum value
    """
    if weighted_score < 0.3:
        return ReviewQuality.NONE
    elif weighted_score < 0.5:
        return ReviewQuality.LOW
    elif weighted_score < 0.8:
        return ReviewQuality.MEDIUM
    else:
        return ReviewQuality.HIGH

def create_pr_review_matrix(prs: list, calculate_weighted_review_count) -> Dict[str, Any]:
    """
    Create matrix of PR importance vs review quality.
    
    Returns:
        Dict with matrix data and statistics
    """
    matrix = defaultdict(lambda: defaultdict(int))
    stats = defaultdict(lambda: {'total': 0, 'zero_review': 0, 'avg_review_score': []})
    
    for pr in prs:
        if not pr.get('merged'):
            continue
        
        # Classify PR
        importance = classify_pr_importance(pr)
        
        # Calculate review quality
        weighted_score = calculate_weighted_review_count(pr)
        review_quality = classify_review_quality(weighted_score)
        
        # Update matrix
        matrix[importance.value][review_quality.value] += 1
        
        # Update stats
        stats[importance.value]['total'] += 1
        if weighted_score < 0.5:
            stats[importance.value]['zero_review'] += 1
        stats[importance.value]['avg_review_score'].append(weighted_score)
    
    # Calculate averages
    for importance in stats:
        scores = stats[importance]['avg_review_score']
        stats[importance]['avg_review_score'] = sum(scores) / len(scores) if scores else 0
        stats[importance]['zero_review_rate'] = stats[importance]['zero_review'] / stats[importance]['total'] * 100 if stats[importance]['total'] > 0 else 0
    
    return {
        'matrix': dict(matrix),
        'stats': dict(stats),
        'total_prs': sum(s['total'] for s in stats.values())
    }

if __name__ == '__main__':
    # Test classification
    test_prs = [
        {'title': 'Fix typo in README', 'body': '', 'additions': 1, 'deletions': 1, 'files': [], 'labels': []},
        {'title': 'Add consensus rule validation', 'body': 'Implements new consensus rule', 'additions': 500, 'deletions': 200, 'files': [], 'labels': []},
        {'title': 'Update documentation', 'body': 'Update API docs', 'additions': 50, 'deletions': 10, 'files': [{'filename': 'docs/api.md'}], 'labels': []},
    ]
    
    for pr in test_prs:
        importance = classify_pr_importance(pr)
        print(f"PR: {pr['title']}")
        print(f"  Importance: {importance.value}")
        print()
