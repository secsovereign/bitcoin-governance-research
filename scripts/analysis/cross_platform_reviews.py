#!/usr/bin/env python3
"""
Cross-Platform Review Analysis: IRC and Mailing Lists

Extracts PR references from IRC messages and mailing list emails,
identifies review-like discussions, and integrates them into review counting.
"""

import json
import re
import sys
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
from typing import Dict, Any, List, Tuple, Set, Optional

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.cross_platform_sources import (
    extract_pr_numbers,
    extract_text_author_timestamp,
    load_mailing_lists,
)
from src.utils.paths import get_data_dir

# PR pattern: #12345 or https://github.com/bitcoin/bitcoin/pull/12345
PR_PATTERN = re.compile(r'(?:#|pull/)(\d{4,6})', re.IGNORECASE)

# Review-like keywords
REVIEW_KEYWORDS = {
    'high': ['review', 'reviewed', 'lgtm', 'looks good', 'tested', 'ack', 'nack', 'utack', 'concept ack'],
    'medium': ['merge', 'merging', 'approved', 'approve', 'changes', 'suggest', 'comment'],
    'low': ['pr', 'pull request', 'issue', 'bug', 'fix']
}

from src.utils.maintainers import load_maintainer_login_set

MAINTAINERS: Set[str] = set()


def load_maintainers() -> Set[str]:
    """Canonical lowercase GitHub logins (plus known aliases)."""
    return load_maintainer_login_set()


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


def get_forum_review_quality_score(post: Dict[str, Any], channel: str, pr_num: str) -> float:
    """Calculate quality score for Delving/Bitcointalk post as review."""
    text, author, _ = extract_text_author_timestamp(post, channel)
    body = text.lower()
    is_maintainer = author in MAINTAINERS

    if is_maintainer and any(kw in body for kw in REVIEW_KEYWORDS["high"]):
        if len(body) > 100:
            return 1.0
        if len(body) > 50:
            return 0.8
        return 0.7

    if is_maintainer or any(kw in body for kw in REVIEW_KEYWORDS["high"]):
        return 0.6 if len(body) > 50 else 0.5

    if any(kw in body for kw in REVIEW_KEYWORDS["medium"]):
        return 0.3

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


def _extract_pr_references_from_records(
    records: List[Dict[str, Any]],
    channel: str,
) -> Dict[str, List[Dict[str, Any]]]:
    pr_messages = defaultdict(list)
    for record in records:
        text, _, _ = extract_text_author_timestamp(record, channel)
        for pr_num in extract_pr_numbers(text):
            pr_messages[pr_num].append(record)
    return pr_messages


def extract_pr_references_from_emails(email_file: Optional[Path] = None) -> Dict[str, List[Dict[str, Any]]]:
    """
    Extract PR references from mailing list emails.

    Uses bitcoin-dev + cryptography (deduped) when email_file is omitted.
    """
    if email_file is not None:
        records: List[Dict[str, Any]] = []
        if email_file.exists():
            with open(email_file, encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            records.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
        return _extract_pr_references_from_records(records, "email")

    emails, _ = load_mailing_lists(dedupe=True)
    return _extract_pr_references_from_records(emails, "email")


def extract_pr_references_from_forum_posts(
    posts: List[Dict[str, Any]],
    channel: str,
) -> Dict[str, List[Dict[str, Any]]]:
    return _extract_pr_references_from_records(posts, channel)


def load_cross_platform_pr_references() -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    """Load PR references from IRC, mailing lists, Delving, and Bitcointalk."""
    irc_file = get_data_dir() / "irc" / "messages.jsonl"
    emails, _ = load_mailing_lists(dedupe=True)
    delving_file = get_data_dir() / "delving" / "posts.jsonl"
    bitcointalk_file = get_data_dir() / "bitcointalk" / "posts.jsonl"

    delving_posts: List[Dict[str, Any]] = []
    bitcointalk_posts: List[Dict[str, Any]] = []
    if delving_file.exists():
        with open(delving_file, encoding="utf-8") as f:
            delving_posts = [json.loads(line) for line in f if line.strip()]
    if bitcointalk_file.exists():
        with open(bitcointalk_file, encoding="utf-8") as f:
            bitcointalk_posts = [json.loads(line) for line in f if line.strip()]

    return {
        "irc": extract_pr_references_from_irc(irc_file),
        "email": _extract_pr_references_from_records(emails, "email"),
        "delving": extract_pr_references_from_forum_posts(delving_posts, "delving"),
        "bitcointalk": extract_pr_references_from_forum_posts(bitcointalk_posts, "bitcointalk"),
    }


def get_cross_platform_reviews(
    pr_num: str,
    pr_merged_at: str,
    irc_messages: Dict[str, List[Dict]],
    email_messages: Dict[str, List[Dict]],
    delving_messages: Optional[Dict[str, List[Dict]]] = None,
    bitcointalk_messages: Optional[Dict[str, List[Dict]]] = None,
) -> Dict[str, float]:
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

    for post in (delving_messages or {}).get(pr_num, []):
        post_date_str = post.get("created_at") or post.get("date")
        if not post_date_str:
            continue
        try:
            post_date = datetime.fromisoformat(post_date_str.replace("Z", "+00:00"))
            if post_date.tzinfo is None:
                post_date = post_date.replace(tzinfo=timezone.utc)
            if merge_date and post_date >= merge_date:
                continue
            author = (post.get("username") or post.get("author") or "").lower()
            if not author:
                continue
            score = get_forum_review_quality_score(post, "delving", pr_num)
            if author not in reviewer_scores or score > reviewer_scores[author]:
                reviewer_scores[author] = score
        except Exception:
            pass

    for post in (bitcointalk_messages or {}).get(pr_num, []):
        post_date_str = post.get("date")
        if not post_date_str:
            continue
        try:
            post_date = datetime.fromisoformat(post_date_str.replace("Z", "+00:00"))
            if post_date.tzinfo is None:
                post_date = post_date.replace(tzinfo=timezone.utc)
            if merge_date and post_date >= merge_date:
                continue
            author = (post.get("author") or "").lower()
            if not author:
                continue
            score = get_forum_review_quality_score(post, "bitcointalk", pr_num)
            if author not in reviewer_scores or score > reviewer_scores[author]:
                reviewer_scores[author] = score
        except Exception:
            pass
    
    return reviewer_scores


def calculate_cross_platform_weighted_review_count(
    pr: Dict[str, Any],
    irc_messages: Dict[str, List[Dict]],
    email_messages: Dict[str, List[Dict]],
    delving_messages: Optional[Dict[str, List[Dict]]] = None,
    bitcointalk_messages: Optional[Dict[str, List[Dict]]] = None,
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
        pr_num,
        pr_merged_at,
        irc_messages,
        email_messages,
        delving_messages=delving_messages,
        bitcointalk_messages=bitcointalk_messages,
    )
    
    # Sum the best score from each reviewer (already MAX per reviewer)
    return sum(cross_platform_scores.values())


def summarize_cross_platform_reviews() -> Dict[str, Any]:
    """Coverage of informal PR discussion. Does not change GitHub review-body scores."""
    global MAINTAINERS
    MAINTAINERS = load_maintainers()
    refs = load_cross_platform_pr_references()
    channels: Dict[str, Any] = {}
    all_pr_nums: Set[str] = set()
    for channel, messages in refs.items():
        n_msgs = sum(len(v) for v in messages.values())
        channels[channel] = {
            "prs_with_discussion": len(messages),
            "messages": n_msgs,
        }
        all_pr_nums.update(str(k) for k in messages)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "maintainer_logins": len(MAINTAINERS),
        "unique_prs_mentioned": len(all_pr_nums),
        "channels": channels,
        "note": (
            "PR mentions / review-like informal comments. "
            "Not mixed into GitHub rubber-stamp or body-length averages."
        ),
    }


if __name__ == '__main__':
    from src.utils.findings_io import save_analysis_json

    summary = summarize_cross_platform_reviews()
    print(f"Loaded {summary['maintainer_logins']} maintainers")
    for channel, stats in (summary.get("channels") or {}).items():
        print(f"{channel}: {stats['prs_with_discussion']} PRs, {stats['messages']} messages")
    written = save_analysis_json("cross_platform_reviews.json", summary)
    print(f"Wrote {', '.join(str(p) for p in written)}")
