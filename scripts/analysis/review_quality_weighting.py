#!/usr/bin/env python3
"""
Review Quality Weighting System

Assigns quality weights to different types of reviews:
- Formal GitHub reviews with comments: 1.0 (full weight)
- Formal GitHub reviews without comments: 0.7 (rubber stamp)
- ACK comments with hash: 0.3 (low quality)
- ACK comments without hash: 0.2 (very low quality)
- ACK comments with substantial text: 0.5 (medium quality)

Also considers when GitHub reviews were introduced (September 2016).
"""

import re
from typing import Dict, Any, Tuple
from datetime import datetime, timezone

# GitHub reviews were introduced in September 2016 (earliest review in data: 2016-09-14)
GITHUB_REVIEWS_INTRODUCED = datetime(2016, 9, 1, tzinfo=timezone.utc)

def get_review_quality_score(review: Dict[str, Any], pr_created_at: str = None) -> float:
    """
    Calculate quality score for a formal GitHub review.
    
    Returns:
        float: Quality score (0.0 to 1.0)
    """
    state = (review.get('state') or '').upper()
    body = (review.get('body') or '').strip()
    
    # If it's not APPROVED or CHANGES_REQUESTED, it's just a comment (0.5)
    if state not in ['APPROVED', 'CHANGES_REQUESTED']:
        return 0.5 if body else 0.3
    
    # Review with substantial body text
    if len(body) > 50:
        return 1.0
    
    # Review with some body text
    if len(body) > 10:
        return 0.8
    
    # Review with minimal body text
    if len(body) > 0:
        return 0.7
    
    # Rubber stamp (no body)
    return 0.5


def get_ack_quality_score(comment: Dict[str, Any]) -> float:
    """
    Calculate quality score for an ACK comment.
    
    Returns:
        float: Quality score (0.0 to 1.0)
    """
    body = (comment.get('body') or '').strip()
    body_lower = body.lower()
    
    # Check for hash (commit hash pattern)
    hash_pattern = re.compile(r'[a-f0-9]{7,40}', re.IGNORECASE)
    has_hash = bool(hash_pattern.search(body))
    
    # Substantial ACK (has meaningful text beyond just "ACK")
    if len(body) > 100:
        return 0.5  # Medium quality
    
    # ACK with some context
    if len(body) > 20:
        return 0.4
    
    # ACK with hash
    if has_hash:
        return 0.3  # Low quality - just hash
    
    # Simple ACK
    return 0.2  # Very low quality


def calculate_weighted_review_count(pr: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
    """
    Calculate weighted review count for a PR.
    
    Returns:
        Tuple[float, Dict]: (weighted_count, breakdown)
    """
    pr_created_at = pr.get('created_at', '')
    pr_date = None
    if pr_created_at:
        try:
            pr_date_str = pr_created_at.replace('Z', '+00:00')
            pr_date = datetime.fromisoformat(pr_date_str)
            # Ensure timezone-aware
            if pr_date.tzinfo is None:
                pr_date = pr_date.replace(tzinfo=timezone.utc)
        except:
            pass
    
    # Check if PR was created before GitHub reviews existed
    pre_review_era = pr_date and pr_date < GITHUB_REVIEWS_INTRODUCED if pr_date else False
    
    weighted_count = 0.0
    breakdown = {
        'formal_reviews': 0,
        'formal_review_weight': 0.0,
        'ack_comments': 0,
        'ack_weight': 0.0,
        'pre_review_era': pre_review_era
    }
    
    # Count formal GitHub reviews (ONLY for PRs created after Sept 2016)
    # PRs created before Sept 2016 should not have formal reviews (they didn't exist yet)
    reviews = pr.get('reviews', [])
    for review in reviews:
        # Skip formal reviews for PRs created before GitHub reviews existed
        if pre_review_era:
            # Formal reviews shouldn't exist for pre-review era PRs
            # If they do appear in data, they're likely errors or retroactive additions - ignore them
            continue
        
        breakdown['formal_reviews'] += 1
        weight = get_review_quality_score(review, pr_created_at)
        breakdown['formal_review_weight'] += weight
        weighted_count += weight
    
    # Count ACK comments
    ack_pattern = re.compile(r'(?:^|\s)ack(?:\s|$|[,\:])', re.IGNORECASE | re.MULTILINE)
    comments = pr.get('comments', [])
    
    for comment in comments:
        body = comment.get('body', '') or ''
        if ack_pattern.search(body):
            breakdown['ack_comments'] += 1
            weight = get_ack_quality_score(comment)
            breakdown['ack_weight'] += weight
            weighted_count += weight
    
    return weighted_count, breakdown


def has_meaningful_review(pr: Dict[str, Any], min_weight: float = 0.5) -> bool:
    """
    Check if PR has meaningful review (weighted count >= min_weight).
    
    Args:
        pr: PR dictionary
        min_weight: Minimum weighted review count to count as "reviewed"
    
    Returns:
        bool: True if PR has meaningful review
    """
    weighted_count, _ = calculate_weighted_review_count(pr)
    return weighted_count >= min_weight


def get_review_quality_category(pr: Dict[str, Any]) -> str:
    """
    Categorize PR review quality.
    
    Returns:
        str: Category name
    """
    weighted_count, breakdown = calculate_weighted_review_count(pr)
    
    if weighted_count == 0:
        return 'no_review'
    elif weighted_count < 0.3:
        return 'very_low_quality'  # Just simple ACK
    elif weighted_count < 0.5:
        return 'low_quality'  # ACK with hash or minimal review
    elif weighted_count < 1.0:
        return 'medium_quality'  # Some review but not substantial
    elif weighted_count < 2.0:
        return 'good_quality'  # At least one good review
    else:
        return 'high_quality'  # Multiple good reviews

