#!/usr/bin/env python3
"""
PR Importance vs Review Quality Matrix Analysis

Creates a matrix showing review quality distribution by PR importance,
addressing the question: "Do trivial/housekeeping PRs need less review?"
"""

import json
import re
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, Any, List, Tuple
from enum import Enum

class PRImportance(Enum):
    """PR importance levels."""
    TRIVIAL = "trivial"  # Typo fixes, formatting, trivial changes (<10 lines)
    LOW = "low"  # Documentation, tests, housekeeping (10-50 lines)
    NORMAL = "normal"  # Regular code changes (50-200 lines)
    HIGH = "high"  # Significant features, refactoring (200-500 lines)
    CRITICAL = "critical"  # Consensus changes, security, protocol changes (>500 lines or consensus-related)

class ReviewQuality(Enum):
    """Review quality levels."""
    NONE = "none"  # No review (<0.3)
    LOW = "low"  # Simple ACK, minimal review (0.3-0.5)
    MEDIUM = "medium"  # Some review, ACK with context (0.5-0.8)
    HIGH = "high"  # Detailed review (0.8-1.0+)

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
    stats = defaultdict(lambda: {
        'total': 0,
        'zero_review': 0,
        'avg_review_score': [],
        'self_merge': 0,
        'maintainer_pr': 0
    })
    
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
        
        # Track self-merge and maintainer status
        author = (pr.get('author', '') or '').lower()
        merged_by = (pr.get('merged_by', '') or '').lower()
        maintainers = {
            'laanwj', 'sipa', 'maflcko', 'fanquake', 'hebasto', 'jnewbery',
            'ryanofsky', 'achow101', 'theuni', 'jonasschnelli', 'sjors',
            'promag', 'instagibbs', 'thebluematt', 'jonatack', 'gmaxwell',
            'gavinandresen', 'petertodd', 'luke-jr', 'glozow'
        }
        
        if author in maintainers:
            stats[importance.value]['maintainer_pr'] += 1
            if merged_by == author:
                stats[importance.value]['self_merge'] += 1
    
    # Calculate averages
    for importance in stats:
        scores = stats[importance]['avg_review_score']
        stats[importance]['avg_review_score'] = sum(scores) / len(scores) if scores else 0
        stats[importance]['zero_review_rate'] = stats[importance]['zero_review'] / stats[importance]['total'] * 100 if stats[importance]['total'] > 0 else 0
        stats[importance]['self_merge_rate'] = stats[importance]['self_merge'] / stats[importance]['maintainer_pr'] * 100 if stats[importance]['maintainer_pr'] > 0 else 0
    
    return {
        'matrix': dict(matrix),
        'stats': dict(stats),
        'total_prs': sum(s['total'] for s in stats.values())
    }

def analyze_by_pr_type(prs: list, calculate_weighted_review_count) -> Dict[str, Any]:
    """
    Analyze zero-review rates and review quality by PR type.
    
    Returns:
        Dict with analysis results
    """
    results = {}
    
    for importance in PRImportance:
        type_prs = [p for p in prs if p.get('merged') and classify_pr_importance(p) == importance]
        
        if not type_prs:
            continue
        
        zero_review = [p for p in type_prs if calculate_weighted_review_count(p) < 0.5]
        maintainer_prs = [p for p in type_prs if (p.get('author', '') or '').lower() in {
            'laanwj', 'sipa', 'maflcko', 'fanquake', 'hebasto', 'jnewbery',
            'ryanofsky', 'achow101', 'theuni', 'jonasschnelli', 'sjors',
            'promag', 'instagibbs', 'thebluematt', 'jonatack', 'gmaxwell',
            'gavinandresen', 'petertodd', 'luke-jr', 'glozow'
        }]
        
        maintainer_zero = [p for p in maintainer_prs if calculate_weighted_review_count(p) < 0.5]
        
        results[importance.value] = {
            'total': len(type_prs),
            'zero_review': len(zero_review),
            'zero_review_rate': len(zero_review) / len(type_prs) * 100 if type_prs else 0,
            'maintainer_prs': len(maintainer_prs),
            'maintainer_zero_review': len(maintainer_zero),
            'maintainer_zero_review_rate': len(maintainer_zero) / len(maintainer_prs) * 100 if maintainer_prs else 0,
            'avg_review_score': sum(calculate_weighted_review_count(p) for p in type_prs) / len(type_prs) if type_prs else 0
        }
    
    return results

if __name__ == '__main__':
    print("PR Classification System")
    print("=" * 50)
