#!/usr/bin/env python3
"""
Comprehensive Maintainer Timeline Analysis

Analyzes maintainer activity over time:
- When they joined (first merge)
- When they left (last merge, if applicable)
- Quantitative metrics: PRs merged, PRs authored, reviews given
- Qualitative insights: patterns, contributions, influence
"""

import json
import sys
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

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

def analyze_maintainer_timeline(prs: List[Dict]) -> Dict[str, Any]:
    """Analyze maintainer timeline from PR data."""
    
    # Known maintainers (from comprehensive_recent_analysis.py)
    # Use lowercase for case-insensitive matching
    known_maintainers = {
        'laanwj', 'sipa', 'maflcko', 'fanquake', 'hebasto', 'jnewbery',
        'ryanofsky', 'achow101', 'theuni', 'jonasschnelli', 'sjors',
        'promag', 'instagibbs', 'thebluematt', 'jonatack', 'gmaxwell',
        'gavinandresen', 'petertodd', 'luke-jr', 'glozow'
    }
    
    # Track maintainer activity
    maintainer_data = defaultdict(lambda: {
        'merges': [],  # List of (date, pr_number) tuples
        'authored_prs': [],  # List of (date, pr_number) tuples
        'reviews_given': [],  # List of (date, pr_number) tuples
        'self_merges': [],  # List of (date, pr_number) tuples
        'zero_review_merges': [],  # List of (date, pr_number) tuples
    })
    
    # Process all PRs
    for pr in prs:
        author = (pr.get('author') or '').lower()
        merged_by = (pr.get('merged_by') or '').lower()
        merged_at = pr.get('merged_at') or pr.get('closed_at')
        pr_number = pr.get('number')
        created_at = pr.get('created_at')
        
        # Track authored PRs for maintainers
        if author in known_maintainers:
            if created_at:
                maintainer_data[author]['authored_prs'].append((created_at, pr_number))
        
        # Track merges (case-insensitive check)
        if merged_by and merged_by.lower() in known_maintainers and merged_at:
            maintainer_data[merged_by.lower()]['merges'].append((merged_at, pr_number))
            
            # Track self-merges
            if author and author == merged_by:
                maintainer_data[merged_by]['self_merges'].append((merged_at, pr_number))
            
            # Check for zero-review merge
            reviews = pr.get('reviews', [])
            comments = pr.get('comments', [])
            has_review = False
            
            # Check formal reviews
            if reviews:
                has_review = True
            else:
                # Check for ACK comments
                import re
                ack_pattern = re.compile(r'(?:^|\s)ack(?:\s|$|[,\:])', re.IGNORECASE | re.MULTILINE)
                for comment in comments:
                    if ack_pattern.search(comment.get('body', '')):
                        has_review = True
                        break
            
            if not has_review:
                maintainer_data[merged_by.lower()]['zero_review_merges'].append((merged_at, pr_number))
        
        # Track reviews given by maintainers
        reviews = pr.get('reviews', [])
        for review in reviews:
            reviewer = (review.get('author') or '').lower()
            if reviewer in known_maintainers:
                review_date = review.get('submitted_at') or review.get('created_at')
                if review_date:
                    maintainer_data[reviewer]['reviews_given'].append((review_date, pr_number))
    
    # Build timeline for each maintainer
    timeline = {}
    
    for maintainer, data in maintainer_data.items():
        # Sort all events by date
        all_events = []
        
        # Add merge events
        for date, pr_num in data['merges']:
            all_events.append(('merge', date, pr_num))
        
        # Add authored PR events
        for date, pr_num in data['authored_prs']:
            all_events.append(('authored', date, pr_num))
        
        # Add review events
        for date, pr_num in data['reviews_given']:
            all_events.append(('review', date, pr_num))
        
        # Sort by date
        all_events.sort(key=lambda x: x[1])
        
        # Calculate metrics
        merges = sorted(data['merges'], key=lambda x: x[0])
        authored = sorted(data['authored_prs'], key=lambda x: x[0])
        reviews = sorted(data['reviews_given'], key=lambda x: x[0])
        self_merges = sorted(data['self_merges'], key=lambda x: x[0])
        zero_review = sorted(data['zero_review_merges'], key=lambda x: x[0])
        
        # Determine join/leave dates
        first_merge = merges[0][0] if merges else None
        last_merge = merges[-1][0] if merges else None
        first_activity = all_events[0][1] if all_events else None
        last_activity = all_events[-1][1] if all_events else None
        
        # Parse dates
        first_merge_dt = parse_date(first_merge) if first_merge else None
        last_merge_dt = parse_date(last_merge) if last_merge else None
        first_activity_dt = parse_date(first_activity) if first_activity else None
        last_activity_dt = parse_date(last_activity) if last_activity else None
        
        # Calculate activity duration
        if first_merge_dt and last_merge_dt:
            duration_days = (last_merge_dt - first_merge_dt).days
            duration_years = duration_days / 365.25
        else:
            duration_days = None
            duration_years = None
        
        # Check if still active (merge in last 180 days)
        is_active = False
        if last_merge_dt:
            days_since_last = (datetime.now(timezone.utc) - last_merge_dt).days
            is_active = days_since_last < 180
        
        # Calculate activity by year
        merges_by_year = Counter()
        authored_by_year = Counter()
        reviews_by_year = Counter()
        self_merges_by_year = Counter()
        
        for date, _ in merges:
            dt = parse_date(date)
            if dt:
                merges_by_year[dt.year] += 1
        
        for date, _ in authored:
            dt = parse_date(date)
            if dt:
                authored_by_year[dt.year] += 1
        
        for date, _ in reviews:
            dt = parse_date(date)
            if dt:
                reviews_by_year[dt.year] += 1
        
        for date, _ in self_merges:
            dt = parse_date(date)
            if dt:
                self_merges_by_year[dt.year] += 1
        
        # Calculate self-merge rate
        self_merge_rate = len(self_merges) / len(merges) * 100 if merges else 0
        
        # Calculate zero-review merge rate
        zero_review_rate = len(zero_review) / len(merges) * 100 if merges else 0
        
        # Build timeline entry
        timeline[maintainer] = {
            'join_date': first_merge,
            'join_date_parsed': first_merge_dt.isoformat() if first_merge_dt else None,
            'last_merge_date': last_merge,
            'last_merge_date_parsed': last_merge_dt.isoformat() if last_merge_dt else None,
            'first_activity': first_activity,
            'last_activity': last_activity,
            'is_active': is_active,
            'duration_days': duration_days,
            'duration_years': round(duration_years, 2) if duration_years else None,
            
            # Quantitative metrics
            'total_merges': len(merges),
            'total_authored': len(authored),
            'total_reviews': len(reviews),
            'total_self_merges': len(self_merges),
            'total_zero_review_merges': len(zero_review),
            'self_merge_rate': round(self_merge_rate, 1),
            'zero_review_rate': round(zero_review_rate, 1),
            
            # Yearly breakdown
            'merges_by_year': dict(merges_by_year),
            'authored_by_year': dict(authored_by_year),
            'reviews_by_year': dict(reviews_by_year),
            'self_merges_by_year': dict(self_merges_by_year),
            
            # Activity periods (identify gaps > 180 days)
            'activity_periods': _identify_activity_periods(merges),
        }
    
    return timeline

def _identify_activity_periods(merges: List[Tuple[str, int]]) -> List[Dict]:
    """Identify distinct activity periods (gaps > 180 days)."""
    if not merges:
        return []
    
    periods = []
    current_period_start = None
    current_period_end = None
    
    for date, _ in merges:
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
    """Generate qualitative insights about maintainers."""
    
    insights = {
        'founders': [],  # Joined before 2012
        'early_maintainers': [],  # Joined 2012-2015
        'modern_maintainers': [],  # Joined 2016+
        'inactive': [],  # Not active in last 180 days
        'high_self_merge': [],  # Self-merge rate > 30%
        'high_zero_review': [],  # Zero-review rate > 20%
        'most_prolific_mergers': [],
        'most_prolific_authors': [],
        'most_prolific_reviewers': [],
        'longest_tenure': [],
        'shortest_tenure': [],
    }
    
    # Sort maintainers by join date
    sorted_maintainers = sorted(
        timeline.items(),
        key=lambda x: x[1].get('join_date') or '9999-12-31'
    )
    
    for maintainer, data in sorted_maintainers:
        join_date = data.get('join_date_parsed')
        if not join_date:
            continue
        
        join_dt = parse_date(join_date)
        if not join_dt:
            continue
        
        join_year = join_dt.year
        
        # Categorize by join era
        if join_year < 2012:
            insights['founders'].append(maintainer)
        elif join_year < 2016:
            insights['early_maintainers'].append(maintainer)
        else:
            insights['modern_maintainers'].append(maintainer)
        
        # Check activity status
        if not data.get('is_active'):
            insights['inactive'].append(maintainer)
        
        # Check self-merge rate
        if data.get('self_merge_rate', 0) > 30:
            insights['high_self_merge'].append((maintainer, data['self_merge_rate']))
        
        # Check zero-review rate
        if data.get('zero_review_rate', 0) > 20:
            insights['high_zero_review'].append((maintainer, data['zero_review_rate']))
    
    # Most prolific
    insights['most_prolific_mergers'] = sorted(
        [(m, d['total_merges']) for m, d in timeline.items()],
        key=lambda x: x[1],
        reverse=True
    )[:5]
    
    insights['most_prolific_authors'] = sorted(
        [(m, d['total_authored']) for m, d in timeline.items()],
        key=lambda x: x[1],
        reverse=True
    )[:5]
    
    insights['most_prolific_reviewers'] = sorted(
        [(m, d['total_reviews']) for m, d in timeline.items()],
        key=lambda x: x[1],
        reverse=True
    )[:5]
    
    # Longest/shortest tenure
    insights['longest_tenure'] = sorted(
        [(m, d.get('duration_years', 0)) for m, d in timeline.items() if d.get('duration_years')],
        key=lambda x: x[1],
        reverse=True
    )[:5]
    
    insights['shortest_tenure'] = sorted(
        [(m, d.get('duration_years', 0)) for m, d in timeline.items() if d.get('duration_years')],
        key=lambda x: x[1]
    )[:5]
    
    return insights

def main():
    """Main entry point."""
    # Use the script's location to find data directory
    script_dir = Path(__file__).parent.parent.parent
    data_dir = script_dir / 'data'
    
    print("="*80)
    print("Maintainer Timeline Analysis")
    print("="*80)
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
    print("Analyzing maintainer timeline...")
    timeline = analyze_maintainer_timeline(prs)
    print(f"Analyzed {len(timeline)} maintainers")
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
        'total_maintainers': len(timeline),
        'timeline': timeline,
        'insights': insights
    }
    
    output_file = output_dir / 'maintainer_timeline_analysis.json'
    with open(output_file, 'w') as f:
        json.dump(timeline_output, f, indent=2)
    print(f"Saved timeline data to {output_file}")
    
    # Generate markdown report
    report_file = output_dir / 'MAINTAINER_TIMELINE_ANALYSIS.md'
    generate_markdown_report(timeline, insights, report_file)
    print(f"Saved report to {report_file}")
    
    print()
    print("="*80)
    print("Analysis Complete")
    print("="*80)

def generate_markdown_report(timeline: Dict, insights: Dict, output_file: Path):
    """Generate comprehensive markdown report."""
    
    with open(output_file, 'w') as f:
        f.write("# Maintainer Timeline Analysis\n\n")
        f.write(f"**Generated**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n")
        f.write("---\n\n")
        
        # Overview
        f.write("## Overview\n\n")
        f.write(f"**Total Maintainers Analyzed**: {len(timeline)}\n\n")
        f.write(f"**Active Maintainers**: {sum(1 for d in timeline.values() if d.get('is_active'))}\n\n")
        f.write(f"**Inactive Maintainers**: {len(insights['inactive'])}\n\n")
        f.write("---\n\n")
        
        # Qualitative Insights
        f.write("## Qualitative Insights\n\n")
        
        f.write("### By Join Era\n\n")
        f.write(f"**Founders** (joined before 2012): {len(insights['founders'])}\n")
        for m in insights['founders']:
            data = timeline[m]
            f.write(f"- **{m}**: Joined {data.get('join_date', 'unknown')}, {data.get('total_merges', 0)} merges\n")
        f.write("\n")
        
        f.write(f"**Early Maintainers** (joined 2012-2015): {len(insights['early_maintainers'])}\n")
        for m in insights['early_maintainers']:
            data = timeline[m]
            f.write(f"- **{m}**: Joined {data.get('join_date', 'unknown')}, {data.get('total_merges', 0)} merges\n")
        f.write("\n")
        
        f.write(f"**Modern Maintainers** (joined 2016+): {len(insights['modern_maintainers'])}\n")
        for m in insights['modern_maintainers']:
            data = timeline[m]
            f.write(f"- **{m}**: Joined {data.get('join_date', 'unknown')}, {data.get('total_merges', 0)} merges\n")
        f.write("\n")
        
        f.write("### Most Prolific\n\n")
        f.write("**Most Prolific Mergers** (top 5):\n")
        for m, count in insights['most_prolific_mergers']:
            f.write(f"- **{m}**: {count:,} merges\n")
        f.write("\n")
        
        f.write("**Most Prolific Authors** (top 5):\n")
        for m, count in insights['most_prolific_authors']:
            f.write(f"- **{m}**: {count:,} PRs authored\n")
        f.write("\n")
        
        f.write("**Most Prolific Reviewers** (top 5):\n")
        for m, count in insights['most_prolific_reviewers']:
            f.write(f"- **{m}**: {count:,} reviews given\n")
        f.write("\n")
        
        f.write("### Longest Tenure\n\n")
        for m, years in insights['longest_tenure']:
            data = timeline[m]
            f.write(f"- **{m}**: {years:.1f} years ({data.get('join_date', 'unknown')} - {data.get('last_merge_date', 'ongoing')})\n")
        f.write("\n")
        
        f.write("### Patterns\n\n")
        f.write(f"**High Self-Merge Rate** (>30%): {len(insights['high_self_merge'])}\n")
        for m, rate in insights['high_self_merge']:
            f.write(f"- **{m}**: {rate:.1f}%\n")
        f.write("\n")
        
        f.write(f"**High Zero-Review Merge Rate** (>20%): {len(insights['high_zero_review'])}\n")
        for m, rate in insights['high_zero_review']:
            f.write(f"- **{m}**: {rate:.1f}%\n")
        f.write("\n")
        
        f.write("---\n\n")
        
        # Individual Maintainer Details
        f.write("## Individual Maintainer Details\n\n")
        
        # Sort by join date
        sorted_maintainers = sorted(
            timeline.items(),
            key=lambda x: x[1].get('join_date') or '9999-12-31'
        )
        
        for maintainer, data in sorted_maintainers:
            f.write(f"### {maintainer}\n\n")
            f.write(f"- **Join Date**: {data.get('join_date', 'unknown')}\n")
            f.write(f"- **Last Merge**: {data.get('last_merge_date', 'unknown')}\n")
            f.write(f"- **Status**: {'Active' if data.get('is_active') else 'Inactive'}\n")
            f.write(f"- **Tenure**: {data.get('duration_years', 'N/A')} years\n")
            f.write(f"- **Total Merges**: {data.get('total_merges', 0):,}\n")
            f.write(f"- **Total Authored**: {data.get('total_authored', 0):,}\n")
            f.write(f"- **Total Reviews**: {data.get('total_reviews', 0):,}\n")
            f.write(f"- **Self-Merge Rate**: {data.get('self_merge_rate', 0):.1f}%\n")
            f.write(f"- **Zero-Review Merge Rate**: {data.get('zero_review_rate', 0):.1f}%\n")
            
            # Activity periods
            periods = data.get('activity_periods', [])
            if len(periods) > 1:
                f.write(f"- **Activity Periods**: {len(periods)} distinct periods\n")
                for i, period in enumerate(periods, 1):
                    start = period['start'][:10] if period.get('start') else 'unknown'
                    end = period['end'][:10] if period.get('end') else 'ongoing'
                    f.write(f"  - Period {i}: {start} to {end}\n")
            
            # Yearly breakdown (last 5 years)
            merges_by_year = data.get('merges_by_year', {})
            if merges_by_year:
                f.write(f"- **Recent Activity** (last 5 years):\n")
                recent_years = sorted(merges_by_year.keys(), reverse=True)[:5]
                for year in recent_years:
                    f.write(f"  - {year}: {merges_by_year[year]} merges\n")
            
            f.write("\n")

if __name__ == '__main__':
    main()
