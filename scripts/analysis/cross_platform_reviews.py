#!/usr/bin/env python3
"""
Cross-Platform Review Analysis: IRC and Mailing Lists

Extracts PR references from IRC messages and mailing list emails,
identifies review-like discussions, and integrates them into review counting.
"""

import json
import re
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
from typing import Dict, Any, List, Tuple, Set

# PR pattern: #12345 or https://github.com/bitcoin/bitcoin/pull/12345
PR_PATTERN = re.compile(r'(?:#|pull/)(\d{4,6})', re.IGNORECASE)

# Review-like keywords
REVIEW_KEYWORDS = {
    'high': ['review', 'reviewed', 'lgtm', 'looks good', 'tested', 'ack', 'nack', 'utack', 'concept ack'],
    'medium': ['merge', 'merging', 'approved', 'approve', 'changes', 'suggest', 'comment'],
    'low': ['pr', 'pull request', 'issue', 'bug', 'fix']
}

# Maintainers list (will be loaded from file)
MAINTAINERS = set()


def load_maintainers() -> Set[str]:
    """Load maintainer list from file."""
    maintainers = set()
    maintainers_file = Path('data/maintainers/maintainers_summary.json')
    if maintainers_file.exists():
        try:
            with open(maintainers_file) as f:
                data = json.load(f)
                for m in data.get('maintainers', []):
                    github = m.get('github', '').lower()
                    name = m.get('name', '').lower()
                    if github:
                        maintainers.add(github)
                    if name:
                        maintainers.add(name)
        except:
            pass
    return maintainers


def get_irc_review_quality_score(message: Dict[str, Any], pr_num: str) -> float:
    """
    Calculate quality score for IRC message as review.
    
    Returns:
        float: Quality score (0.2 to 1.0)
    """
    body = (message.get('body') or message.get('message') or '').lower()
    author = (message.get('author') or message.get('nick') or '').lower()
    
    is_maintainer = author in MAINTAINERS
    
    # High quality: Technical discussion with maintainer
    if is_maintainer and any(kw in body for kw in REVIEW_KEYWORDS['high']):
        if len(body) > 100:
            return 1.0  # Detailed technical discussion
        elif len(body) > 50:
            return 0.8  # Good discussion
        else:
            return 0.7  # Brief but technical
    
    # Medium quality: Technical discussion or maintainer mention
    if is_maintainer or any(kw in body for kw in REVIEW_KEYWORDS['high']):
        if len(body) > 50:
            return 0.6
        else:
            return 0.5
    
    # Low quality: Casual mention
    if any(kw in body for kw in REVIEW_KEYWORDS['medium']):
        return 0.3
    
    # Very low: Just PR mention
    return 0.2


def get_email_review_quality_score(email: Dict[str, Any], pr_num: str) -> float:
    """
    Calculate quality score for email as review.
    
    Returns:
        float: Quality score (0.2 to 1.0)
    """
    body = (email.get('body') or email.get('content') or '').lower()
    subject = (email.get('subject') or '').lower()
    from_field = (email.get('from') or '').lower()
    
    text = body + ' ' + subject
    
    # Check if from maintainer (would need identity mapping)
    is_maintainer = any(m in from_field for m in MAINTAINERS)
    
    # High quality: Formal discussion thread with technical analysis
    if any(kw in text for kw in REVIEW_KEYWORDS['high']):
        if len(body) > 200:
            return 1.0  # Detailed technical analysis
        elif len(body) > 100:
            return 0.8  # Good discussion
        else:
            return 0.7  # Brief but technical
    
    # Medium quality: Discussion thread
    if any(kw in text for kw in REVIEW_KEYWORDS['medium']):
        if len(body) > 100:
            return 0.6
        else:
            return 0.5
    
    # Low quality: Brief mention
    return 0.3


def extract_pr_references_from_irc(irc_file: Path) -> Dict[str, List[Dict[str, Any]]]:
    """
    Extract PR references from IRC messages.
    
    Returns:
        Dict mapping PR number to list of IRC messages mentioning it
    """
    pr_messages = defaultdict(list)
    
    if not irc_file.exists():
        return pr_messages
    
    with open(irc_file) as f:
        for line in f:
            if not line.strip():
                continue
            try:
                msg = json.loads(line)
                body = msg.get('body') or msg.get('message') or ''
                matches = PR_PATTERN.findall(body)
                
                for pr_num in matches:
                    # Include all PR mentions - filtering by quality happens in scoring
                    pr_messages[pr_num].append(msg)
            except:
                pass
    
    return pr_messages


def extract_pr_references_from_emails(email_file: Path) -> Dict[str, List[Dict[str, Any]]]:
    """
    Extract PR references from mailing list emails.
    
    Returns:
        Dict mapping PR number to list of emails mentioning it
    """
    pr_emails = defaultdict(list)
    
    if not email_file.exists():
        return pr_emails
    
    with open(email_file) as f:
        for line in f:
            if not line.strip():
                continue
            try:
                email = json.loads(line)
                body = email.get('body') or email.get('content') or ''
                subject = email.get('subject') or ''
                text = body + ' ' + subject
                
                matches = PR_PATTERN.findall(text)
                
                for pr_num in matches:
                    # Include all PR mentions - filtering by quality happens in scoring
                    pr_emails[pr_num].append(email)
            except:
                pass
    
    return pr_emails


def get_cross_platform_reviews(pr_num: str, pr_merged_at: str, 
                               irc_messages: Dict[str, List[Dict]], 
                               email_messages: Dict[str, List[Dict]]) -> Dict[str, float]:
    """
    Get cross-platform reviews for a PR.
    
    Returns:
        Dict mapping reviewer identity to their best review score
    """
    reviewer_scores = {}
    
    # Parse merge date
    merge_date = None
    if pr_merged_at:
        try:
            merge_date = datetime.fromisoformat(pr_merged_at.replace('Z', '+00:00'))
            if merge_date.tzinfo is None:
                merge_date = merge_date.replace(tzinfo=timezone.utc)
        except:
            pass
    
    # Process IRC messages
    for msg in irc_messages.get(pr_num, []):
        msg_date_str = msg.get('date') or msg.get('timestamp')
        if not msg_date_str:
            continue
        
        try:
            msg_date = datetime.fromisoformat(msg_date_str.replace('Z', '+00:00'))
            if msg_date.tzinfo is None:
                msg_date = msg_date.replace(tzinfo=timezone.utc)
            
            # Only count if before merge
            if merge_date and msg_date >= merge_date:
                continue
            
            author = (msg.get('author') or msg.get('nick') or '').lower()
            if not author:
                continue
            
            score = get_irc_review_quality_score(msg, pr_num)
            
            # Take MAX per reviewer (same logic as GitHub reviews)
            if author not in reviewer_scores or score > reviewer_scores[author]:
                reviewer_scores[author] = score
        except:
            pass
    
    # Process email messages
    for email in email_messages.get(pr_num, []):
        email_date_str = email.get('date')
        if not email_date_str:
            continue
        
        try:
            email_date = datetime.fromisoformat(email_date_str.replace('Z', '+00:00'))
            if email_date.tzinfo is None:
                email_date = email_date.replace(tzinfo=timezone.utc)
            
            # Only count if before merge
            if merge_date and email_date >= merge_date:
                continue
            
            from_field = (email.get('from') or '').lower()
            # Extract email address or name as identifier
            email_match = re.search(r'[\w\.-]+@[\w\.-]+', from_field)
            author = email_match.group(0).lower() if email_match else from_field
            
            if not author:
                continue
            
            score = get_email_review_quality_score(email, pr_num)
            
            # Take MAX per reviewer (same logic as GitHub reviews)
            if author not in reviewer_scores or score > reviewer_scores[author]:
                reviewer_scores[author] = score
        except:
            pass
    
    return reviewer_scores


def calculate_cross_platform_weighted_review_count(
    pr: Dict[str, Any],
    irc_messages: Dict[str, List[Dict]],
    email_messages: Dict[str, List[Dict]]
) -> float:
    """
    Calculate weighted review count including cross-platform reviews.
    
    Returns:
        float: Additional weighted review count from IRC/email
    """
    pr_num = str(pr.get('number', ''))
    if not pr_num:
        return 0.0
    
    pr_merged_at = pr.get('merged_at') or pr.get('closed_at')
    if not pr_merged_at:
        return 0.0
    
    cross_platform_scores = get_cross_platform_reviews(
        pr_num, pr_merged_at, irc_messages, email_messages
    )
    
    # Sum the best score from each reviewer (already MAX per reviewer)
    return sum(cross_platform_scores.values())


if __name__ == '__main__':
    # Load maintainers
    MAINTAINERS = load_maintainers()
    print(f"Loaded {len(MAINTAINERS)} maintainers")
    
    # Extract PR references
    irc_file = Path('data/irc/messages.jsonl')
    email_file = Path('data/mailing_lists/emails.jsonl')
    
    print("Extracting PR references from IRC...")
    irc_messages = extract_pr_references_from_irc(irc_file)
    print(f"  Found {len(irc_messages)} PRs with IRC discussion")
    
    print("Extracting PR references from emails...")
    email_messages = extract_pr_references_from_emails(email_file)
    print(f"  Found {len(email_messages)} PRs with email discussion")
