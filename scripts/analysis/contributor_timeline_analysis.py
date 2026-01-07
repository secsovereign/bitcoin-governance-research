#!/usr/bin/env python3
"""
Comprehensive Contributor Timeline Analysis

Analyzes contributor activity over time:
- When they joined (first contribution)
- Activity patterns and tenure
- Quantitative metrics: PRs authored, merged, reviews given
- Filters out low-quality/low-quantity contributors
- Qualitative insights: patterns, contributions, influence
"""

import json
import sys
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple

# Add project root to path
script_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(script_dir))

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

def parse_date(date_str: str) -> Optional[datetime]:
    """Parse date string to datetime object."""
    if not date_str:
        return None
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except:
        return None

def calculate_contribution_quality_score(pr: Dict) -> float:
    """Calculate quality score for a PR contribution (0.0 to 1.0)."""
    score = 0.0
    
    # File changes (more changes = higher quality, up to a point)
    additions = pr.get('additions', 0) or 0
    deletions = pr.get('deletions', 0) or 0
    total_changes = additions + deletions
    
    if total_changes > 0:
        # Normalize: 100 lines = 0.3, 500 lines = 0.6, 1000+ lines = 0.8
        if total_changes >= 1000:
            score += 0.8
        elif total_changes >= 500:
            score += 0.6
        elif total_changes >= 100:
            score += 0.3
        elif total_changes >= 50:
            score += 0.2
        else:
            score += 0.1
    
    # Files changed (more files = higher complexity)
    files_changed = pr.get('files_changed', 0) or 0
    if files_changed > 0:
        if files_changed >= 10:
            score += 0.2
        elif files_changed >= 5:
            score += 0.1
    
    # PR was merged (merged PRs are higher quality)
    if pr.get('merged', False):
        score += 0.3
    
    # Has reviews (reviewed PRs are higher quality)
    reviews = pr.get('reviews', [])
    if len(reviews) > 0:
        score += 0.1
    
    # Has substantial description
    body = (pr.get('body') or '').strip()
    if len(body) > 200:
        score += 0.1
    
    return min(score, 1.0)

def analyze_contributor_timeline(prs: List[Dict], min_contributions: int = 5, min_quality_score: float = 0.3) -> Dict[str, Any]:
    """Analyze contributor timeline from PR data."""
    
    # Known maintainers (exclude from contributor analysis)
    # Use lowercase for case-insensitive matching
    known_maintainers = {
        'laanwj', 'sipa', 'maflcko', 'fanquake', 'hebasto', 'jnewbery',
        'ryanofsky', 'achow101', 'theuni', 'jonasschnelli', 'sjors',
        'promag', 'instagibbs', 'thebluematt', 'jonatack', 'gmaxwell',
        'gavinandresen', 'petertodd', 'luke-jr', 'glozow'
    }
    
    # Track contributor activity
    contributor_data = defaultdict(lambda: {
        'authored_prs': [],  # List of (date, pr_number, quality_score) tuples
        'merged_prs': [],  # List of (date, pr_number) tuples
        'reviews_given': [],  # List of (date, pr_number) tuples
        'total_quality_score': 0.0,
    })
    
    # Process all PRs
    for pr in prs:
        author = (pr.get('author') or '').lower()
        
        # Skip maintainers (case-insensitive check)
        if author in known_maintainers:
            continue
        
        created_at = pr.get('created_at')
        pr_number = pr.get('number')
        merged = pr.get('merged', False)
        
        if created_at and author:
            # Calculate quality score
            quality_score = calculate_contribution_quality_score(pr)
            
            # Track authored PRs
            contributor_data[author]['authored_prs'].append((created_at, pr_number, quality_score))
            contributor_data[author]['total_quality_score'] += quality_score
            
            # Track merged PRs
            if merged:
                merged_at = pr.get('merged_at') or pr.get('closed_at')
                if merged_at:
                    contributor_data[author]['merged_prs'].append((merged_at, pr_number))
        
        # Track reviews given by contributors
        reviews = pr.get('reviews', [])
        for review in reviews:
            reviewer = (review.get('author') or '').lower()
            if reviewer and reviewer not in known_maintainers:
                review_date = review.get('submitted_at') or review.get('created_at')
                if review_date:
                    contributor_data[reviewer]['reviews_given'].append((review_date, pr_number))
    
    # Filter contributors by quality/quantity
    filtered_contributors = {}
    
    for contributor, data in contributor_data.items():
        total_prs = len(data['authored_prs'])
        avg_quality = data['total_quality_score'] / total_prs if total_prs > 0 else 0.0
        
        # Filter criteria:
        # 1. At least min_contributions PRs
        # 2. Average quality score >= min_quality_score
        if total_prs >= min_contributions and avg_quality >= min_quality_score:
            filtered_contributors[contributor] = data
    
    print(f"Total contributors identified: {len(contributor_data)}")
    print(f"Contributors after filtering (≥{min_contributions} PRs, avg quality ≥{min_quality_score}): {len(filtered_contributors)}")
    print()
    
    # Build timeline for each contributor
    timeline = {}
    
    for contributor, data in filtered_contributors.items():
        # Sort all events by date
        all_events = []
        
        # Add authored PR events
        for date, pr_num, quality in data['authored_prs']:
            all_events.append(('authored', date, pr_num, quality))
        
        # Add merged PR events
        for date, pr_num in data['merged_prs']:
            all_events.append(('merged', date, pr_num))
        
        # Add review events
        for date, pr_num in data['reviews_given']:
            all_events.append(('review', date, pr_num))
        
        # Sort by date
        all_events.sort(key=lambda x: x[1])
        
        # Calculate metrics
        authored = sorted(data['authored_prs'], key=lambda x: x[0])
        merged = sorted(data['merged_prs'], key=lambda x: x[0])
        reviews = sorted(data['reviews_given'], key=lambda x: x[0])
        
        # Determine join/leave dates
        first_contribution = authored[0][0] if authored else None
        last_contribution = authored[-1][0] if authored else None
        first_activity = all_events[0][1] if all_events else None
        last_activity = all_events[-1][1] if all_events else None
        
        # Parse dates
        first_contribution_dt = parse_date(first_contribution) if first_contribution else None
        last_contribution_dt = parse_date(last_contribution) if last_contribution else None
        first_activity_dt = parse_date(first_activity) if first_activity else None
        last_activity_dt = parse_date(last_activity) if last_activity else None
        
        # Calculate activity duration
        if first_contribution_dt and last_contribution_dt:
            duration_days = (last_contribution_dt - first_contribution_dt).days
            duration_years = duration_days / 365.25
        else:
            duration_days = None
            duration_years = None
        
        # Check if still active (contribution in last 180 days)
        is_active = False
        if last_contribution_dt:
            days_since_last = (datetime.now(timezone.utc) - last_contribution_dt).days
            is_active = days_since_last < 180
        
        # Calculate merge rate
        merge_rate = len(merged) / len(authored) * 100 if authored else 0
        
        # Calculate average quality score
        avg_quality = data['total_quality_score'] / len(authored) if authored else 0.0
        
        # Calculate activity by year
        authored_by_year = Counter()
        merged_by_year = Counter()
        reviews_by_year = Counter()
        quality_by_year = defaultdict(list)
        
        for date, pr_num, quality in authored:
            dt = parse_date(date)
            if dt:
                year = dt.year
                authored_by_year[year] += 1
                quality_by_year[year].append(quality)
        
        for date, pr_num in merged:
            dt = parse_date(date)
            if dt:
                merged_by_year[dt.year] += 1
        
        for date, pr_num in reviews:
            dt = parse_date(date)
            if dt:
                reviews_by_year[dt.year] += 1
        
        # Calculate average quality by year
        avg_quality_by_year = {}
        for year, qualities in quality_by_year.items():
            avg_quality_by_year[year] = sum(qualities) / len(qualities) if qualities else 0.0
        
        # Build timeline entry
        timeline[contributor] = {
            'join_date': first_contribution,
            'join_date_parsed': first_contribution_dt.isoformat() if first_contribution_dt else None,
            'last_contribution_date': last_contribution,
            'last_contribution_date_parsed': last_contribution_dt.isoformat() if last_contribution_dt else None,
            'first_activity': first_activity,
            'last_activity': last_activity,
            'is_active': is_active,
            'duration_days': duration_days,
            'duration_years': round(duration_years, 2) if duration_years else None,
            
            # Quantitative metrics
            'total_authored': len(authored),
            'total_merged': len(merged),
            'total_reviews': len(reviews),
            'merge_rate': round(merge_rate, 1),
            'avg_quality_score': round(avg_quality, 3),
            'total_quality_score': round(data['total_quality_score'], 2),
            
            # Yearly breakdown
            'authored_by_year': dict(authored_by_year),
            'merged_by_year': dict(merged_by_year),
            'reviews_by_year': dict(reviews_by_year),
            'avg_quality_by_year': {k: round(v, 3) for k, v in avg_quality_by_year.items()},
            
            # Activity periods (identify gaps > 180 days)
            'activity_periods': _identify_activity_periods([(date, pr_num) for date, pr_num, _ in authored]),
        }
    
    return timeline

def _identify_activity_periods(contributions: List[Tuple[str, int]]) -> List[Dict]:
    """Identify distinct activity periods (gaps > 180 days)."""
    if not contributions:
        return []
    
    periods = []
    current_period_start = None
    current_period_end = None
    
    for date, _ in contributions:
        dt = parse_date(date)
        if not dt:
            continue
        
        if current_period_start is None:
            current_period_start = dt
            current_period_end = dt
        else:
            gap_days = (dt - current_period_end).days
            if gap_days > 180:
                # Start new period
                periods.append({
                    'start': current_period_start.isoformat(),
                    'end': current_period_end.isoformat(),
                    'duration_days': (current_period_end - current_period_start).days
                })
                current_period_start = dt
                current_period_end = dt
            else:
                current_period_end = dt
    
    # Add final period
    if current_period_start:
        periods.append({
            'start': current_period_start.isoformat(),
            'end': current_period_end.isoformat() if current_period_end else None,
            'duration_days': (current_period_end - current_period_start).days if current_period_end else None
        })
    
    return periods

def generate_qualitative_insights(timeline: Dict[str, Any]) -> Dict[str, Any]:
    """Generate qualitative insights about contributors."""
    
    insights = {
        'early_contributors': [],  # Joined before 2015
        'modern_contributors': [],  # Joined 2015+
        'active': [],
        'inactive': [],
        'high_quality': [],  # Avg quality > 0.6
        'high_merge_rate': [],  # Merge rate > 70%
        'most_prolific_authors': [],
        'most_prolific_reviewers': [],
        'longest_tenure': [],
        'highest_quality': [],
    }
    
    # Sort contributors by join date
    sorted_contributors = sorted(
        timeline.items(),
        key=lambda x: x[1].get('join_date') or '9999-12-31'
    )
    
    for contributor, data in sorted_contributors:
        join_date = data.get('join_date_parsed')
        if not join_date:
            continue
        
        join_dt = parse_date(join_date)
        if not join_dt:
            continue
        
        join_year = join_dt.year
        
        # Categorize by join era
        if join_year < 2015:
            insights['early_contributors'].append(contributor)
        else:
            insights['modern_contributors'].append(contributor)
        
        # Check activity status
        if data.get('is_active'):
            insights['active'].append(contributor)
        else:
            insights['inactive'].append(contributor)
        
        # Check quality
        if data.get('avg_quality_score', 0) > 0.6:
            insights['high_quality'].append((contributor, data['avg_quality_score']))
        
        # Check merge rate
        if data.get('merge_rate', 0) > 70:
            insights['high_merge_rate'].append((contributor, data['merge_rate']))
    
    # Most prolific
    insights['most_prolific_authors'] = sorted(
        [(c, d['total_authored']) for c, d in timeline.items()],
        key=lambda x: x[1],
        reverse=True
    )[:10]
    
    insights['most_prolific_reviewers'] = sorted(
        [(c, d['total_reviews']) for c, d in timeline.items()],
        key=lambda x: x[1],
        reverse=True
    )[:10]
    
    # Longest tenure
    insights['longest_tenure'] = sorted(
        [(c, d.get('duration_years', 0)) for c, d in timeline.items() if d.get('duration_years')],
        key=lambda x: x[1],
        reverse=True
    )[:10]
    
    # Highest quality
    insights['highest_quality'] = sorted(
        [(c, d.get('avg_quality_score', 0)) for c, d in timeline.items()],
        key=lambda x: x[1],
        reverse=True
    )[:10]
    
    return insights

def main():
    """Main entry point."""
    script_dir = Path(__file__).parent.parent.parent
    data_dir = script_dir / 'data'
    
    print("="*80)
    print("Contributor Timeline Analysis")
    print("="*80)
    print()
    
    # Configuration
    min_contributions = 5  # Minimum PRs to be included
    min_quality_score = 0.3  # Minimum average quality score
    
    print(f"Filtering criteria:")
    print(f"  - Minimum contributions: {min_contributions} PRs")
    print(f"  - Minimum average quality: {min_quality_score}")
    print()
    
    # Load PR data
    print("Loading PR data...")
    prs = load_jsonl(
        data_dir / 'github' / 'prs_raw.jsonl',
        mapping_file=data_dir / 'github' / 'merged_by_mapping.jsonl'
    )
    print(f"Loaded {len(prs):,} PRs")
    print()
    
    # Analyze timeline
    print("Analyzing contributor timeline...")
    timeline = analyze_contributor_timeline(prs, min_contributions, min_quality_score)
    print(f"Analyzed {len(timeline)} contributors (after filtering)")
    print()
    
    # Generate insights
    print("Generating qualitative insights...")
    insights = generate_qualitative_insights(timeline)
    print()
    
    # Save results
    output_dir = script_dir / 'findings'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save timeline data
    timeline_output = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'filtering_criteria': {
            'min_contributions': min_contributions,
            'min_quality_score': min_quality_score
        },
        'total_contributors': len(timeline),
        'timeline': timeline,
        'insights': insights
    }
    
    output_file = output_dir / 'contributor_timeline_analysis.json'
    with open(output_file, 'w') as f:
        json.dump(timeline_output, f, indent=2)
    print(f"Saved timeline data to {output_file}")
    
    # Generate markdown report
    report_file = output_dir / 'CONTRIBUTOR_TIMELINE_ANALYSIS.md'
    generate_markdown_report(timeline, insights, report_file, min_contributions, min_quality_score)
    print(f"Saved report to {report_file}")
    
    print()
    print("="*80)
    print("Analysis Complete")
    print("="*80)

def generate_markdown_report(timeline: Dict, insights: Dict, output_file: Path, min_contributions: int, min_quality_score: float):
    """Generate comprehensive markdown report."""
    
    with open(output_file, 'w') as f:
        f.write("# Contributor Timeline Analysis\n\n")
        f.write(f"**Generated**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n")
        f.write("---\n\n")
        
        # Overview
        f.write("## Overview\n\n")
        f.write(f"**Total Contributors Analyzed**: {len(timeline)}\n\n")
        f.write(f"**Filtering Criteria**:\n")
        f.write(f"- Minimum contributions: {min_contributions} PRs\n")
        f.write(f"- Minimum average quality score: {min_quality_score}\n\n")
        f.write(f"**Active Contributors**: {len(insights['active'])}\n\n")
        f.write(f"**Inactive Contributors**: {len(insights['inactive'])}\n\n")
        f.write("---\n\n")
        
        # Qualitative Insights
        f.write("## Qualitative Insights\n\n")
        
        f.write("### By Join Era\n\n")
        f.write(f"**Early Contributors** (joined before 2015): {len(insights['early_contributors'])}\n")
        for c in insights['early_contributors'][:10]:
            data = timeline[c]
            f.write(f"- **{c}**: Joined {data.get('join_date', 'unknown')[:10]}, {data.get('total_authored', 0)} PRs, {data.get('merge_rate', 0):.1f}% merge rate\n")
        f.write("\n")
        
        f.write(f"**Modern Contributors** (joined 2015+): {len(insights['modern_contributors'])}\n")
        f.write(f"(Showing top 10 by contributions)\n")
        for c in insights['modern_contributors'][:10]:
            data = timeline[c]
            f.write(f"- **{c}**: Joined {data.get('join_date', 'unknown')[:10]}, {data.get('total_authored', 0)} PRs, {data.get('merge_rate', 0):.1f}% merge rate\n")
        f.write("\n")
        
        f.write("### Most Prolific\n\n")
        f.write("**Most Prolific Authors** (top 10):\n")
        for c, count in insights['most_prolific_authors']:
            data = timeline[c]
            f.write(f"- **{c}**: {count:,} PRs authored, {data.get('merge_rate', 0):.1f}% merge rate, quality: {data.get('avg_quality_score', 0):.3f}\n")
        f.write("\n")
        
        f.write("**Most Prolific Reviewers** (top 10):\n")
        for c, count in insights['most_prolific_reviewers']:
            data = timeline[c]
            f.write(f"- **{c}**: {count:,} reviews given, {data.get('total_authored', 0)} PRs authored\n")
        f.write("\n")
        
        f.write("### Quality and Performance\n\n")
        f.write("**Highest Quality Contributors** (top 10 by avg quality score):\n")
        for c, quality in insights['highest_quality']:
            data = timeline[c]
            f.write(f"- **{c}**: Quality {quality:.3f}, {data.get('total_authored', 0)} PRs, {data.get('merge_rate', 0):.1f}% merge rate\n")
        f.write("\n")
        
        f.write("**High Merge Rate Contributors** (>70% merge rate):\n")
        for c, rate in insights['high_merge_rate'][:10]:
            data = timeline[c]
            f.write(f"- **{c}**: {rate:.1f}% merge rate, {data.get('total_authored', 0)} PRs, quality: {data.get('avg_quality_score', 0):.3f}\n")
        f.write("\n")
        
        f.write("### Longest Tenure\n\n")
        for c, years in insights['longest_tenure']:
            data = timeline[c]
            f.write(f"- **{c}**: {years:.1f} years ({data.get('join_date', 'unknown')[:10]} - {data.get('last_contribution_date', 'ongoing')[:10] if data.get('last_contribution_date') else 'ongoing'}), {data.get('total_authored', 0)} PRs\n")
        f.write("\n")
        
        f.write("---\n\n")
        
        # Individual Contributor Details (top 20 by contributions)
        f.write("## Top Contributors (by Total PRs Authored)\n\n")
        
        sorted_contributors = sorted(
            timeline.items(),
            key=lambda x: x[1].get('total_authored', 0),
            reverse=True
        )[:20]
        
        for contributor, data in sorted_contributors:
            f.write(f"### {contributor}\n\n")
            f.write(f"- **Join Date**: {data.get('join_date', 'unknown')[:10] if data.get('join_date') else 'unknown'}\n")
            f.write(f"- **Last Contribution**: {data.get('last_contribution_date', 'unknown')[:10] if data.get('last_contribution_date') else 'unknown'}\n")
            f.write(f"- **Status**: {'Active' if data.get('is_active') else 'Inactive'}\n")
            f.write(f"- **Tenure**: {data.get('duration_years', 'N/A')} years\n")
            f.write(f"- **Total Authored**: {data.get('total_authored', 0):,}\n")
            f.write(f"- **Total Merged**: {data.get('total_merged', 0):,}\n")
            f.write(f"- **Merge Rate**: {data.get('merge_rate', 0):.1f}%\n")
            f.write(f"- **Total Reviews**: {data.get('total_reviews', 0):,}\n")
            f.write(f"- **Average Quality Score**: {data.get('avg_quality_score', 0):.3f}\n")
            
            # Activity periods
            periods = data.get('activity_periods', [])
            if len(periods) > 1:
                f.write(f"- **Activity Periods**: {len(periods)} distinct periods\n")
                for i, period in enumerate(periods[:3], 1):  # Show first 3
                    start = period['start'][:10] if period.get('start') else 'unknown'
                    end = period['end'][:10] if period.get('end') else 'ongoing'
                    f.write(f"  - Period {i}: {start} to {end}\n")
            
            # Yearly breakdown (last 5 years)
            authored_by_year = data.get('authored_by_year', {})
            if authored_by_year:
                f.write(f"- **Recent Activity** (last 5 years):\n")
                recent_years = sorted(authored_by_year.keys(), reverse=True)[:5]
                for year in recent_years:
                    count = authored_by_year[year]
                    merged_count = data.get('merged_by_year', {}).get(year, 0)
                    quality = data.get('avg_quality_by_year', {}).get(year, 0)
                    f.write(f"  - {year}: {count} PRs authored, {merged_count} merged, quality: {quality:.3f}\n")
            
            f.write("\n")

if __name__ == '__main__':
    main()





