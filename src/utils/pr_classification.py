"""PR classification utilities for governance analysis.

Provides functions to classify PRs by importance level based on:
- File changes (size, type)
- Keywords (consensus, security, housekeeping)
- Labels
- Content analysis
"""

from typing import Dict, Any
from enum import Enum


class PRImportance(Enum):
    """PR importance levels."""
    TRIVIAL = "trivial"  # Typo fixes, formatting, trivial changes (<10 lines)
    LOW = "low"  # Documentation, tests, housekeeping (10-50 lines)
    NORMAL = "normal"  # Regular code changes (50-200 lines)
    HIGH = "high"  # Significant features, refactoring (200-500 lines)
    CRITICAL = "critical"  # Consensus changes, security, protocol changes (>500 lines or consensus-related)


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
    
    Args:
        pr: PR dictionary with title, body, files, labels, etc.
    
    Returns:
        PRImportance enum value
    """
    title = (pr.get('title', '') or '').lower()
    body = (pr.get('body', '') or '').lower()
    text = title + ' ' + body
    
    # Get file changes
    files = pr.get('files', []) or []
    total_additions = pr.get('total_additions', 0) or 0
    total_deletions = pr.get('total_deletions', 0) or 0
    total_changes = total_additions + total_deletions
    
    # Check labels
    labels = []
    for l in (pr.get('labels', []) or []):
        if isinstance(l, dict):
            labels.append(l.get('name', '').lower())
        else:
            labels.append(str(l).lower())
    
    # Critical indicators
    is_critical = (
        any(kw in text for kw in CRITICAL_KEYWORDS) or
        any('consensus' in l or 'security' in l or 'critical' in l for l in labels) or
        total_changes > 1000
    )
    
    if is_critical:
        return PRImportance.CRITICAL
    
    # File-based classification
    file_types = set()
    consensus_files = False
    for f in files:
        if isinstance(f, dict):
            filename = f.get('filename', '') or f.get('path', '')
        else:
            filename = str(f)
        
        if filename.endswith(('.md', '.txt', '.rst', '.tex')):
            file_types.add('docs')
        elif 'test' in filename.lower() or filename.endswith(('_test.cpp', '_tests.cpp', '_test.h')):
            file_types.add('tests')
        elif filename.endswith(('.h', '.cpp', '.c')):
            file_types.add('code')
            # Check for consensus-related files
            if any(x in filename.lower() for x in ['consensus', 'validation', 'script', 'policy']):
                consensus_files = True
    
    # Housekeeping indicators
    is_housekeeping = (
        any(kw in text for kw in HOUSEKEEPING_KEYWORDS) or
        any('doc' in l or 'test' in l or 'trivial' in l for l in labels) or
        (len(file_types) == 1 and 'docs' in file_types)
    )
    
    # Size-based classification
    if total_changes < 5:
        size = 'trivial'
    elif total_changes < 20:
        size = 'very_small'
    elif total_changes < 50:
        size = 'small'
    elif total_changes < 200:
        size = 'medium'
    elif total_changes < 500:
        size = 'large'
    else:
        size = 'very_large'
    
    # Classification logic (refined)
    if is_housekeeping and total_changes < 10:
        return PRImportance.TRIVIAL
    elif is_housekeeping or (len(file_types) == 1 and 'docs' in file_types):
        return PRImportance.LOW
    elif consensus_files and total_changes > 100:
        return PRImportance.CRITICAL
    elif consensus_files:
        return PRImportance.HIGH
    elif size == 'trivial' and total_changes < 5:
        return PRImportance.TRIVIAL
    elif size == 'very_large' and total_changes > 1000:
        return PRImportance.CRITICAL
    elif size == 'very_large':
        return PRImportance.HIGH
    elif size in ['very_small', 'small']:
        return PRImportance.LOW
    elif size == 'large':
        return PRImportance.HIGH
    else:
        return PRImportance.NORMAL


def get_pr_importance_label(pr: Dict[str, Any]) -> str:
    """
    Get PR importance as string label.
    
    Args:
        pr: PR dictionary
    
    Returns:
        Importance label: 'trivial', 'low', 'normal', 'high', or 'critical'
    """
    return classify_pr_importance(pr).value


def is_consensus_related(pr: Dict[str, Any]) -> bool:
    """
    Check if PR is consensus-related.
    
    Args:
        pr: PR dictionary
    
    Returns:
        True if PR is consensus-related
    """
    importance = classify_pr_importance(pr)
    return importance in [PRImportance.CRITICAL, PRImportance.HIGH]


def is_housekeeping(pr: Dict[str, Any]) -> bool:
    """
    Check if PR is housekeeping (trivial or low importance).
    
    Args:
        pr: PR dictionary
    
    Returns:
        True if PR is housekeeping
    """
    importance = classify_pr_importance(pr)
    return importance in [PRImportance.TRIVIAL, PRImportance.LOW]

