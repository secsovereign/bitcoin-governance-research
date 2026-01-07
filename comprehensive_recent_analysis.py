#!/usr/bin/env python3
"""
Comprehensive analysis of Bitcoin Core governance metrics for recent period (2021-2025)
and comparison with historical period (2012-2020).
"""

import json
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import List, Dict, Any

def load_jsonl(filepath: Path, mapping_file: Path = None) -> list:
    """Load JSONL file and return list of records with merged_by data."""
    records = []
    if not filepath.exists():
        return records
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    
    # Merge merged_by data if mapping file provided
    if mapping_file and mapping_file.exists():
        mapping = {}
        with open(mapping_file) as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    mapping[data['pr_number']] = {
                        'merged_by': data.get('merged_by'),
                        'merged_by_id': data.get('merged_by_id')
                    }
        
        for record in records:
            pr_number = record.get('number')
            if pr_number in mapping:
                record.update(mapping[pr_number])
    
    return records

def get_year(date_str):
    """Extract year from date string."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00')).year
    except:
        return None

def calculate_gini(values: List[float]) -> float:
    """Calculate Gini coefficient."""
    if not values:
        return 0.0
    sorted_values = sorted(values)
    n = len(sorted_values)
    total = sum(sorted_values)
    if total == 0:
        return 0.0
    numerator = sum((i + 1) * val for i, val in enumerate(sorted_values))
    gini = (2 * numerator) / (n * total) - (n + 1) / n
    return gini

def analyze_period(prs: List[Dict], period_name: str, start_year: int, end_year: int):
    """Analyze a specific time period."""
    print(f"\n{'='*80}")
    print(f"{period_name} ({start_year}-{end_year})")
    print(f"{'='*80}\n")
    
    # Filter PRs by period
    period_prs = [p for p in prs if start_year <= get_year(p.get('created_at', '')) <= end_year]
    
    # Identify maintainers
    maintainers = {
        'laanwj', 'sipa', 'maflcko', 'fanquake', 'hebasto', 'jnewbery',
        'ryanofsky', 'achow101', 'theuni', 'jonasschnelli', 'Sjors',
        'promag', 'instagibbs', 'TheBlueMatt', 'jonatack', 'gmaxwell',
        'gavinandresen', 'petertodd', 'luke-jr', 'glozow'
    }
    
    print(f"Total PRs: {len(period_prs):,}")
    
    # Basic stats
    merged = [p for p in period_prs if p.get('merged', False)]
    open_prs = [p for p in period_prs if p.get('state') == 'open']
    closed_not_merged = [p for p in period_prs if p.get('state') == 'closed' and not p.get('merged', False)]
    
    print(f"  Merged: {len(merged):,}")
    print(f"  Open: {len(open_prs):,}")
    print(f"  Closed (not merged): {len(closed_not_merged):,}")
    print()
    
    # Maintainer vs non-maintainer
    maintainer_prs = [p for p in period_prs if p.get('author', '').lower() in [m.lower() for m in maintainers]]
    non_maintainer_prs = [p for p in period_prs if p.get('author', '').lower() not in [m.lower() for m in maintainers]]
    
    maintainer_merged = [p for p in merged if p.get('author', '').lower() in [m.lower() for m in maintainers]]
    non_maintainer_merged = [p for p in merged if p.get('author', '').lower() not in [m.lower() for m in maintainers]]
    
    print(f"Maintainer PRs: {len(maintainer_prs):,}")
    print(f"  Merged: {len(maintainer_merged):,} ({len(maintainer_merged)/len(maintainer_prs)*100:.1f}%)" if maintainer_prs else "  Merged: 0")
    print(f"Non-maintainer PRs: {len(non_maintainer_prs):,}")
    print(f"  Merged: {len(non_maintainer_merged):,} ({len(non_maintainer_merged)/len(non_maintainer_prs)*100:.1f}%)" if non_maintainer_prs else "  Merged: 0")
    print()
    
    # Helper function to count reviews with quality weighting
    import re
    from datetime import datetime, timezone
    
    # GitHub reviews were introduced in September 2016 (earliest review in data: 2016-09-14)
    GITHUB_REVIEWS_INTRODUCED = datetime(2016, 9, 1, tzinfo=timezone.utc)
    
    def get_review_quality_score(review):
        """Calculate quality score for formal GitHub review (0.0 to 1.0)."""
        state = (review.get('state') or '').upper()
        body = (review.get('body') or '').strip()
        
        if state not in ['APPROVED', 'CHANGES_REQUESTED']:
            return 0.5 if body else 0.3
        
        if len(body) > 50:
            return 1.0  # Substantial review
        elif len(body) > 10:
            return 0.8  # Some review
        elif len(body) > 0:
            return 0.7  # Minimal review
        else:
            return 0.5  # Rubber stamp
    
    def get_ack_quality_score(comment):
        """Calculate quality score for ACK comment (0.0 to 0.5)."""
        body = (comment.get('body') or '').strip()
        hash_pattern = re.compile(r'[a-f0-9]{7,40}', re.IGNORECASE)
        has_hash = bool(hash_pattern.search(body))
        
        if len(body) > 100:
            return 0.5  # Substantial ACK
        elif len(body) > 20:
            return 0.4  # ACK with context
        elif has_hash:
            return 0.3  # ACK with hash (low quality)
        else:
            return 0.2  # Simple ACK (very low quality)
    
    def calculate_weighted_review_count(pr):
        """Calculate weighted review count for PR.
        
        For each reviewer, takes the HIGHEST quality review (not sum).
        
        IMPORTANT: 
        - If a reviewer leaves multiple reviews, we take MAX (not sum)
        - If a reviewer does a detailed review (≥0.7) and then an ACK,
          the ACK is treated as a completion signal (not a separate review) and is IGNORED.
        - Cross-platform reviews (IRC, email) are included with same per-reviewer MAX logic.
        - Formal GitHub reviews are EXCLUDED for PRs created before Sept 2016 (pre-review era).
        
        Example: Reviewer leaves 3 reviews (0.8, 0.5, 1.0) = max(0.8, 0.5, 1.0) = 1.0
        """
        from datetime import datetime
        
        # Check if PR was created before GitHub reviews existed
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
        
        pre_review_era = pr_date and pr_date < GITHUB_REVIEWS_INTRODUCED if pr_date else False
        
        # Track events with timestamps to check timeline
        events = []
        
        # Formal GitHub reviews (ONLY for PRs created after Sept 2016)
        # PRs created before Sept 2016 should not have formal reviews (they didn't exist yet)
        if not pre_review_era:
            for review in pr.get('reviews', []):
                author = (review.get('author') or '').lower()
                if author:
                    date_str = review.get('submitted_at') or review.get('created_at')
                    if date_str:
                        try:
                            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                            score = get_review_quality_score(review)
                            events.append({
                                'type': 'review',
                                'author': author,
                                'date': dt,
                                'score': score
                            })
                        except:
                            pass
        # Note: If pre_review_era is True, we skip formal reviews entirely
        # (they shouldn't exist for those PRs, but if they do in data, they're likely errors)
        
        # ACK comments
        ack_pattern = re.compile(r'(?:^|\s)ack(?:\s|$|[,\:])', re.IGNORECASE | re.MULTILINE)
        for comment in pr.get('comments', []):
            body = comment.get('body', '') or ''
            if ack_pattern.search(body):
                author = (comment.get('author') or '').lower()
                if author:
                    date_str = comment.get('created_at')
                    if date_str:
                        try:
                            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                            score = get_ack_quality_score(comment)
                            events.append({
                                'type': 'ack',
                                'author': author,
                                'date': dt,
                                'score': score
                            })
                        except:
                            pass
        
        # Sort by date
        events.sort(key=lambda x: x['date'])
        
        # Track best score per reviewer, ignoring ACKs that come after detailed reviews
        reviewer_scores = {}
        ack_ignored_as_completion = set()  # Track ACKs ignored as completion signals
        
        for i, event in enumerate(events):
            author = event['author']
            event_type = event['type']
            score = event['score']
            
            if event_type == 'review':
                # Always use review if it's better
                if author not in reviewer_scores or score > reviewer_scores[author]:
                    reviewer_scores[author] = score
            elif event_type == 'ack':
                # Check if this ACK comes after a detailed review from same reviewer
                is_completion_signal = False
                for j in range(i):
                    prev_event = events[j]
                    if (prev_event['type'] == 'review' and
                        prev_event['author'] == author and
                        prev_event['score'] >= 0.7):  # Substantial review
                        is_completion_signal = True
                        break
                
                if is_completion_signal:
                    # ACK is a completion signal, ignore it
                    ack_ignored_as_completion.add((author, event['date']))
                else:
                    # ACK is standalone review, use if better
                    if author not in reviewer_scores or score > reviewer_scores[author]:
                        reviewer_scores[author] = score
        
        # Add cross-platform reviews (IRC, mailing lists)
        # Lazy load cross-platform data (only once per function call)
        if not hasattr(calculate_weighted_review_count, '_cross_platform_loaded'):
            try:
                import sys
                import os
                # Add scripts directory to path
                script_dir = Path(__file__).parent
                sys.path.insert(0, str(script_dir))
                
                from scripts.analysis.cross_platform_reviews import (
                    get_cross_platform_reviews,
                    extract_pr_references_from_irc,
                    extract_pr_references_from_emails,
                    load_maintainers
                )
                
                # Load maintainers
                calculate_weighted_review_count._maintainers = load_maintainers()
                
                # Load IRC and email data
                data_dir = script_dir / 'data'
                irc_file = data_dir / 'irc' / 'messages.jsonl'
                email_file = data_dir / 'mailing_lists' / 'emails.jsonl'
                
                calculate_weighted_review_count._irc_messages = extract_pr_references_from_irc(irc_file) if irc_file.exists() else {}
                calculate_weighted_review_count._email_messages = extract_pr_references_from_emails(email_file) if email_file.exists() else {}
                calculate_weighted_review_count._cross_platform_loaded = True
                calculate_weighted_review_count._get_cross_platform_reviews = get_cross_platform_reviews
            except Exception as e:
                # If cross-platform analysis fails, continue with GitHub-only
                calculate_weighted_review_count._cross_platform_loaded = True
                calculate_weighted_review_count._irc_messages = {}
                calculate_weighted_review_count._email_messages = {}
                calculate_weighted_review_count._get_cross_platform_reviews = None
        
        # Get cross-platform reviews for this PR
        if calculate_weighted_review_count._get_cross_platform_reviews:
            pr_num = str(pr.get('number', ''))
            pr_merged_at = pr.get('merged_at') or pr.get('closed_at')
            
            if pr_num and pr_merged_at:
                try:
                    cross_platform_scores = calculate_weighted_review_count._get_cross_platform_reviews(
                        pr_num,
                        pr_merged_at,
                        calculate_weighted_review_count._irc_messages,
                        calculate_weighted_review_count._email_messages
                    )
                    
                    # Merge with GitHub reviews (take MAX per reviewer across all platforms)
                    for author, score in cross_platform_scores.items():
                        if author not in reviewer_scores or score > reviewer_scores[author]:
                            reviewer_scores[author] = score
                except:
                    pass
        
        # Sum the best score from each reviewer (MAX per reviewer across all platforms)
        return sum(reviewer_scores.values())
    
    def has_meaningful_review(pr, min_weight=0.5):
        """Check if PR has meaningful review (weight >= min_weight)."""
        # For PRs before GitHub reviews existed (Sept 2016), lower threshold for ACK
        pr_date = None
        if pr.get('created_at'):
            try:
                pr_date_str = pr.get('created_at').replace('Z', '+00:00')
                pr_date = datetime.fromisoformat(pr_date_str)
                # Ensure timezone-aware
                if pr_date.tzinfo is None:
                    pr_date = pr_date.replace(tzinfo=timezone.utc)
            except:
                pass
        
        pre_review_era = pr_date and pr_date < GITHUB_REVIEWS_INTRODUCED if pr_date else False
        threshold = 0.3 if pre_review_era else 0.5  # Lower threshold for pre-review era
        
        weighted = calculate_weighted_review_count(pr)
        return weighted >= threshold
    
    # 1. Zero-review merge rate (using quality-weighted reviews)
    zero_review_merged = [p for p in merged if not has_meaningful_review(p)]
    maintainer_zero_review = [p for p in maintainer_merged if not has_meaningful_review(p)]
    non_maintainer_zero_review = [p for p in non_maintainer_merged if not has_meaningful_review(p)]
    
    print("1. ZERO-REVIEW MERGE RATE")
    print(f"  All merged PRs: {len(zero_review_merged):,}/{len(merged):,} ({len(zero_review_merged)/len(merged)*100:.1f}%)" if merged else "  All merged PRs: 0")
    if maintainer_merged:
        print(f"  Maintainer PRs: {len(maintainer_zero_review):,}/{len(maintainer_merged):,} ({len(maintainer_zero_review)/len(maintainer_merged)*100:.1f}%)")
    if non_maintainer_merged:
        print(f"  Non-maintainer PRs: {len(non_maintainer_zero_review):,}/{len(non_maintainer_merged):,} ({len(non_maintainer_zero_review)/len(non_maintainer_merged)*100:.1f}%)")
    print()
    
    # 2. Self-merge rate (using merged_by data)
    self_merged = []
    for pr in maintainer_merged:
        merged_by = pr.get('merged_by') or ''  # Use merged_by from mapping
        author = pr.get('author', '')
        # Only count as self-merge if merged_by matches author (not if merged_by is missing)
        if merged_by and author and merged_by.lower() == author.lower():
            self_merged.append(pr)
    
    print("2. SELF-MERGE RATE (Maintainer PRs)")
    if maintainer_merged:
        print(f"  Self-merged: {len(self_merged):,}/{len(maintainer_merged):,} ({len(self_merged)/len(maintainer_merged)*100:.1f}%)")
    else:
        print(f"  Self-merged: 0")
    print()
    
    # 3. Cross-status reviews (homophily) - including ACK comments
    maintainer_prs_with_reviews = [p for p in maintainer_merged if has_meaningful_review(p)]
    cross_status_reviews = 0
    same_status_reviews = 0
    
    # ACK pattern for extracting reviewers
    ack_pattern = re.compile(r'(?:^|\s)ack(?:\s|$|[,\:])', re.IGNORECASE | re.MULTILINE)
    
    for pr in maintainer_prs_with_reviews:
        reviewer_names = []
        
        # Get reviewers from formal GitHub reviews
        reviews = pr.get('reviews', [])
        reviewer_names.extend([r.get('author', '') or '' for r in reviews if r.get('author')])
        
        # Get reviewers from ACK comments
        comments = pr.get('comments', [])
        for comment in comments:
            body = comment.get('body', '') or ''
            if ack_pattern.search(body):
                author = comment.get('author', '') or ''
                if author:
                    reviewer_names.append(author)
        
        reviewer_names = [r.lower() for r in reviewer_names if r]
        
        has_non_maintainer = any(r not in [m.lower() for m in maintainers] for r in reviewer_names)
        has_maintainer = any(r in [m.lower() for m in maintainers] for r in reviewer_names)
        
        if has_non_maintainer:
            cross_status_reviews += 1
        if has_maintainer and not has_non_maintainer:
            same_status_reviews += 1
    
    print("3. CROSS-STATUS REVIEWS (HOMOPHILY)")
    if maintainer_prs_with_reviews:
        print(f"  Maintainer PRs with reviews: {len(maintainer_prs_with_reviews):,}")
        print(f"  With non-maintainer reviews: {cross_status_reviews:,} ({cross_status_reviews/len(maintainer_prs_with_reviews)*100:.1f}%)")
        print(f"  Only maintainer reviews: {same_status_reviews:,} ({same_status_reviews/len(maintainer_prs_with_reviews)*100:.1f}%)")
        homophily_coeff = same_status_reviews / len(maintainer_prs_with_reviews) if maintainer_prs_with_reviews else 0
        print(f"  Homophily coefficient: {homophily_coeff:.4f} (1.0 = perfect segregation)")
    else:
        print(f"  Maintainer PRs with reviews: 0")
    print()
    
    # 4. Gini coefficient (contribution inequality)
    author_counts = Counter(p.get('author', 'unknown') for p in period_prs)
    author_count_values = list(author_counts.values())
    gini = calculate_gini(author_count_values)
    
    print("4. GINI COEFFICIENT (Contribution Inequality)")
    print(f"  Unique authors: {len(author_counts):,}")
    print(f"  Gini coefficient: {gini:.4f}")
    if gini >= 0.6:
        print(f"  Status: EXTREME INEQUALITY (≥ 0.6)")
    elif gini >= 0.5:
        print(f"  Status: High inequality (≥ 0.5)")
    elif gini >= 0.3:
        print(f"  Status: Moderate inequality")
    else:
        print(f"  Status: Low inequality")
    
    # Top contributors
    top_10_total = sum(count for _, count in author_counts.most_common(10))
    print(f"  Top 10 authors: {top_10_total:,} PRs ({top_10_total/len(period_prs)*100:.1f}% of total)")
    print()
    
    # 5. Response times
    response_times = []
    maintainer_response_times = []
    non_maintainer_response_times = []
    
    for pr in period_prs:
        created = pr.get('created_at')
        if not created:
            continue
        
        comments = pr.get('comments', [])
        reviews = pr.get('reviews', [])
        
        first_response = None
        if comments:
            comment_times = [c.get('created_at') for c in comments if c.get('created_at')]
            if comment_times:
                first_response = min(comment_times)
        if reviews:
            review_times = [r.get('submitted_at') or r.get('created_at') for r in reviews if r.get('submitted_at') or r.get('created_at')]
            if review_times:
                min_review = min(review_times)
                if not first_response or min_review < first_response:
                    first_response = min_review
        
        if first_response and created:
            try:
                created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                response_dt = datetime.fromisoformat(first_response.replace('Z', '+00:00'))
                hours = (response_dt - created_dt).total_seconds() / 3600
                if hours > 0:
                    response_times.append(hours)
                    if pr.get('author', '').lower() in [m.lower() for m in maintainers]:
                        maintainer_response_times.append(hours)
                    else:
                        non_maintainer_response_times.append(hours)
            except:
                pass
    
    print("5. RESPONSE TIMES (First Response)")
    if response_times:
        avg_hours = sum(response_times) / len(response_times)
        print(f"  All PRs average: {avg_hours:.1f} hours ({avg_hours/24:.1f} days)")
    if maintainer_response_times:
        avg_maintainer = sum(maintainer_response_times) / len(maintainer_response_times)
        print(f"  Maintainer PRs: {avg_maintainer:.1f} hours ({avg_maintainer/24:.1f} days)")
    if non_maintainer_response_times:
        avg_non_maintainer = sum(non_maintainer_response_times) / len(non_maintainer_response_times)
        print(f"  Non-maintainer PRs: {avg_non_maintainer:.1f} hours ({avg_non_maintainer/24:.1f} days)")
        if maintainer_response_times:
            ratio = avg_non_maintainer / avg_maintainer
            print(f"  Ratio (non-maintainer/maintainer): {ratio:.2f}x")
    print()
    
    # 6. Open PR wait times
    now = datetime.now()
    open_wait_times = []
    for pr in open_prs:
        created = pr.get('created_at')
        if not created:
            continue
        try:
            created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
            days_waiting = (now - created_dt.replace(tzinfo=None)).days
            if days_waiting > 0:
                open_wait_times.append(days_waiting)
        except:
            pass
    
    print("6. OPEN PR WAIT TIMES")
    if open_wait_times:
        avg_days = sum(open_wait_times) / len(open_wait_times)
        median_days = sorted(open_wait_times)[len(open_wait_times)//2]
        max_days = max(open_wait_times)
        print(f"  Open PRs: {len(open_wait_times):,}")
        print(f"  Average wait: {avg_days:.1f} days ({avg_days/365.25:.2f} years)")
        print(f"  Median wait: {median_days:.1f} days ({median_days/365.25:.2f} years)")
        print(f"  Longest wait: {max_days:.1f} days ({max_days/365.25:.2f} years)")
    else:
        print(f"  Open PRs: 0")
    print()
    
    # 7. Maintainer NACKs
    nack_keywords = ['nack', 'nacked', 'nacking', 'concept nack', 'utack']
    maintainer_nacks_on_maintainers = 0
    
    for pr in period_prs:
        pr_author = pr.get('author', '')
        if not pr_author or pr_author.lower() not in [m.lower() for m in maintainers]:
            continue
        
        comments = pr.get('comments', [])
        reviews = pr.get('reviews', [])
        
        for comment in comments:
            body = (comment.get('body') or '').lower()
            author = comment.get('author') or ''
            if author and author.lower() in [m.lower() for m in maintainers]:
                if any(kw in body for kw in nack_keywords):
                    maintainer_nacks_on_maintainers += 1
        
        for review in reviews:
            body = (review.get('body') or '').lower()
            state = review.get('state', '')
            author = review.get('author') or ''
            if author and author.lower() in [m.lower() for m in maintainers]:
                if state == 'CHANGES_REQUESTED' or any(kw in body for kw in nack_keywords):
                    maintainer_nacks_on_maintainers += 1
    
    print("7. MAINTAINER-ON-MAINTAINER NACKs")
    print(f"  Total: {maintainer_nacks_on_maintainers:,}")
    print()
    
    # 8. Review concentration (Gini for reviews)
    reviewer_counts = Counter()
    for pr in period_prs:
        reviews = pr.get('reviews', [])
        for review in reviews:
            reviewer = review.get('author', '')
            if reviewer:
                reviewer_counts[reviewer] += 1
    
    if reviewer_counts:
        review_counts = list(reviewer_counts.values())
        review_gini = calculate_gini(review_counts)
        print("8. REVIEW CONCENTRATION (Gini)")
        print(f"  Unique reviewers: {len(reviewer_counts):,}")
        print(f"  Total reviews: {sum(review_counts):,}")
        print(f"  Gini coefficient: {review_gini:.4f}")
        top_5_reviews = sum(count for _, count in reviewer_counts.most_common(5))
        print(f"  Top 5 reviewers: {top_5_reviews:,} reviews ({top_5_reviews/sum(review_counts)*100:.1f}% of total)" if review_counts else "  Top 5 reviewers: 0")
    print()
    
    # Return summary
    return {
        'period': period_name,
        'total_prs': len(period_prs),
        'merged': len(merged),
        'zero_review_rate': len(zero_review_merged)/len(merged)*100 if merged else 0,
        'self_merge_rate': len(self_merged)/len(maintainer_merged)*100 if maintainer_merged else 0,
        'cross_status_review_rate': cross_status_reviews/len(maintainer_prs_with_reviews)*100 if maintainer_prs_with_reviews else 0,
        'gini': gini,
        'avg_response_hours': sum(response_times)/len(response_times) if response_times else 0,
        'avg_open_wait_days': sum(open_wait_times)/len(open_wait_times) if open_wait_times else 0,
        'maintainer_nacks': maintainer_nacks_on_maintainers,
        'review_gini': review_gini if reviewer_counts else 0
    }

def analyze_pr_importance_matrix(prs: List[Dict], calculate_weighted_review_count_func):
    """Analyze PR importance vs review quality matrix."""
    print(f"\n{'='*80}")
    print("PR IMPORTANCE vs REVIEW QUALITY MATRIX")
    print(f"{'='*80}\n")
    
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent))
        
        from scripts.analysis.pr_importance_matrix import (
            create_pr_review_matrix,
            analyze_by_pr_type,
            PRImportance
        )
        
        # Create matrix
        matrix_data = create_pr_review_matrix(prs, calculate_weighted_review_count_func)
        type_analysis = analyze_by_pr_type(prs, calculate_weighted_review_count_func)
        
        print("Zero-Review Rates by PR Importance:")
        print(f"{'Type':<15} {'Total':<10} {'Zero Review':<15} {'Rate':<10} {'Avg Review Score':<15}")
        print("-" * 80)
        
        for importance in PRImportance:
            if importance.value in type_analysis:
                data = type_analysis[importance.value]
                print(f"{importance.value:<15} {data['total']:<10} {data['zero_review']:<15} {data['zero_review_rate']:<10.1f}% {data['avg_review_score']:<15.2f}")
        
        print(f"\n{'='*80}")
        print("REVIEW QUALITY DISTRIBUTION BY PR TYPE")
        print(f"{'='*80}\n")
        
        # Print matrix
        review_qualities = ['none', 'low', 'medium', 'high']
        print(f"{'PR Type':<15} ", end='')
        for q in review_qualities:
            print(f"{q:<15} ", end='')
        print()
        print("-" * 80)
        
        for importance in PRImportance:
            if importance.value in matrix_data['matrix']:
                print(f"{importance.value:<15} ", end='')
                for q in review_qualities:
                    count = matrix_data['matrix'][importance.value].get(q, 0)
                    print(f"{count:<15} ", end='')
                print()
        
        # Save results
        output_file = Path(__file__).parent / 'findings' / 'pr_importance_matrix.json'
        with open(output_file, 'w') as f:
            json.dump({
                'matrix': matrix_data['matrix'],
                'stats': matrix_data['stats'],
                'type_analysis': type_analysis
            }, f, indent=2)
        
        print(f"\nResults saved to: {output_file}")
        
    except Exception as e:
        print(f"Note: PR importance matrix analysis not available: {e}")

def main():
    """Run comprehensive analysis."""
    data_dir = Path(__file__).parent / 'data'
    
    print("="*80)
    print("COMPREHENSIVE BITCOIN CORE GOVERNANCE ANALYSIS")
    print("Updated with Recent Data (2021-2025)")
    print("="*80)
    
    # Load PRs with merged_by data from mapping file
    prs = load_jsonl(
        data_dir / 'github' / 'prs_raw.jsonl',
        mapping_file=data_dir / 'github' / 'merged_by_mapping.jsonl'
    )
    print(f"\nTotal PRs in dataset: {len(prs):,}")
    
    # Count PRs with merged_by data
    merged_prs = [p for p in prs if p.get('merged', False)]
    with_merged_by = [p for p in merged_prs if p.get('merged_by')]
    print(f"Merged PRs with merged_by data: {len(with_merged_by):,}/{len(merged_prs):,} ({len(with_merged_by)/len(merged_prs)*100:.1f}%)" if merged_prs else "N/A")
    
    # Analyze both periods
    historical = analyze_period(prs, "HISTORICAL PERIOD", 2012, 2020)
    recent = analyze_period(prs, "RECENT PERIOD", 2021, 2025)
    
    # PR Importance Matrix Analysis
    # Import the function from analyze_period context
    # We need to recreate calculate_weighted_review_count here
    import re
    from datetime import datetime, timezone
    
    GITHUB_REVIEWS_INTRODUCED = datetime(2016, 9, 1, tzinfo=timezone.utc)
    
    def get_review_quality_score(review):
        state = (review.get('state') or '').upper()
        body = (review.get('body') or '').strip()
        if state not in ['APPROVED', 'CHANGES_REQUESTED']:
            return 0.5 if body else 0.3
        if len(body) > 50:
            return 1.0
        elif len(body) > 10:
            return 0.8
        elif len(body) > 0:
            return 0.7
        else:
            return 0.5
    
    def get_ack_quality_score(comment):
        body = (comment.get('body') or '').strip()
        hash_pattern = re.compile(r'[a-f0-9]{7,40}', re.IGNORECASE)
        has_hash = bool(hash_pattern.search(body))
        if len(body) > 100:
            return 0.5
        elif len(body) > 20:
            return 0.4
        elif has_hash:
            return 0.3
        else:
            return 0.2
    
    def calculate_weighted_review_count(pr):
        from datetime import datetime
        events = []
        for review in pr.get('reviews', []):
            author = (review.get('author') or '').lower()
            if author:
                date_str = review.get('submitted_at') or review.get('created_at')
                if date_str:
                    try:
                        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        score = get_review_quality_score(review)
                        events.append({'type': 'review', 'author': author, 'date': dt, 'score': score})
                    except:
                        pass
        ack_pattern = re.compile(r'(?:^|\s)ack(?:\s|$|[,\:])', re.IGNORECASE | re.MULTILINE)
        for comment in pr.get('comments', []):
            body = comment.get('body', '') or ''
            if ack_pattern.search(body):
                author = (comment.get('author') or '').lower()
                if author:
                    date_str = comment.get('created_at')
                    if date_str:
                        try:
                            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                            score = get_ack_quality_score(comment)
                            events.append({'type': 'ack', 'author': author, 'date': dt, 'score': score})
                        except:
                            pass
        events.sort(key=lambda x: x['date'])
        reviewer_scores = {}
        for i, event in enumerate(events):
            author = event['author']
            event_type = event['type']
            score = event['score']
            if event_type == 'review':
                if author not in reviewer_scores or score > reviewer_scores[author]:
                    reviewer_scores[author] = score
            elif event_type == 'ack':
                is_completion_signal = False
                for j in range(i):
                    prev_event = events[j]
                    if (prev_event['type'] == 'review' and
                        prev_event['author'] == author and
                        prev_event['score'] >= 0.7):
                        is_completion_signal = True
                        break
                if not is_completion_signal:
                    if author not in reviewer_scores or score > reviewer_scores[author]:
                        reviewer_scores[author] = score
        return sum(reviewer_scores.values())
    
    analyze_pr_importance_matrix(prs, calculate_weighted_review_count)
    
    # Comparison
    print(f"\n{'='*80}")
    print("COMPARISON: HISTORICAL vs RECENT")
    print(f"{'='*80}\n")
    
    metrics = [
        ('Zero-review merge rate', 'zero_review_rate', '%', True),
        ('Self-merge rate', 'self_merge_rate', '%', True),
        ('Cross-status review rate', 'cross_status_review_rate', '%', False),
        ('Gini coefficient', 'gini', '', True),
        ('Avg response time', 'avg_response_hours', 'hours', True),
        ('Avg open PR wait', 'avg_open_wait_days', 'days', True),
        ('Maintainer NACKs', 'maintainer_nacks', '', False),
        ('Review Gini', 'review_gini', '', True),
    ]
    
    print(f"{'Metric':<30} {'Historical':<15} {'Recent':<15} {'Change':<15}")
    print("-"*80)
    
    for metric_name, key, unit, is_lower_better in metrics:
        hist_val = historical.get(key, 0)
        recent_val = recent.get(key, 0)
        
        if hist_val == 0:
            change = "N/A"
        elif is_lower_better:
            change_pct = ((hist_val - recent_val) / hist_val) * 100
            change = f"{change_pct:+.1f}%"
        else:
            change_pct = ((recent_val - hist_val) / hist_val) * 100
            change = f"{change_pct:+.1f}%"
        
        hist_str = f"{hist_val:.2f}{unit}" if unit else f"{hist_val:.0f}"
        recent_str = f"{recent_val:.2f}{unit}" if unit else f"{recent_val:.0f}"
        
        print(f"{metric_name:<30} {hist_str:<15} {recent_str:<15} {change:<15}")
    
    print()
    print("="*80)

if __name__ == '__main__':
    main()
