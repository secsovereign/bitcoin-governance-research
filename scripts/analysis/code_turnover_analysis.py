#!/usr/bin/env python3
"""
Technical Debt Analysis - File-Level Analysis

Analyzes technical debt in Bitcoin Core using PR data.
Implements refined metrics: debt scores, patch-to-refactor ratios, untouchable code.

Key Metrics:
- Technical Debt Score: Composite metric (0-100) identifying debt
- Patch-to-Refactor Ratio: How often code is patched vs. refactored
- Untouchable Code: Code modified but never refactored
- Debt Accumulation: Is debt increasing over time?

Usage:
    python scripts/analysis/code_turnover_analysis.py
"""

import json
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Any, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def load_prs(prs_file: Path) -> List[Dict[str, Any]]:
    """Load PRs from JSONL file."""
    prs = []
    with open(prs_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                prs.append(json.loads(line))
    return prs

def categorize_file(filename: str) -> str:
    """Categorize file by subsystem."""
    filename_lower = filename.lower()
    if 'consensus' in filename_lower or 'validation' in filename_lower:
        return 'consensus'
    elif 'net' in filename_lower or 'p2p' in filename_lower:
        return 'network'
    elif 'wallet' in filename_lower:
        return 'wallet'
    elif 'rpc' in filename_lower:
        return 'rpc'
    elif 'test' in filename_lower or 'qa' in filename_lower:
        return 'test'
    elif 'doc' in filename_lower or 'readme' in filename_lower:
        return 'documentation'
    elif 'script' in filename_lower:
        return 'script'
    elif 'qt' in filename_lower or 'gui' in filename_lower:
        return 'gui'
    else:
        return 'other'

def is_critical_subsystem(subsystem: str) -> bool:
    """Check if subsystem is critical (consensus code)."""
    return subsystem == 'consensus'

def classify_change_type(changes: int, file_size_estimate: int, additions: int, deletions: int) -> str:
    """
    Classify a file change as patch, feature, refactor, or replacement.
    
    Criteria:
    - Patch: Small change (<20% of file, <100 lines)
    - Feature: New code added, minimal changes to existing
    - Bug Fix: Targeted fix, small scope
    - Refactor: Significant restructuring (>30% of file, or >200 lines)
    - Replacement: File deleted and recreated (100% turnover)
    """
    if file_size_estimate == 0:
        # New file or can't estimate
        if additions > 200:
            return 'feature'
        else:
            return 'patch'
    
    change_percentage = changes / file_size_estimate if file_size_estimate > 0 else 0
    
    # Replacement: Very high deletions relative to size
    if deletions > file_size_estimate * 0.8 and additions > file_size_estimate * 0.5:
        return 'replacement'
    
    # Refactor: Large change (>30% of file, or >200 lines)
    if change_percentage > 0.3 or changes > 200:
        return 'refactor'
    
    # Feature: Mostly additions, small deletions
    if additions > deletions * 2 and additions > 50:
        return 'feature'
    
    # Bug fix: Small targeted change
    if changes < 50 and deletions < additions:
        return 'bug_fix'
    
    # Default: Patch (small incremental change)
    return 'patch'

def calculate_debt_score(
    patch_frequency: float,
    refactoring_deficit: float,
    age_risk: float,
    complexity: float
) -> float:
    """
    Calculate technical debt score (0-100).
    
    Formula:
    Debt Score = (Patch Frequency × 0.3) + 
                 (Refactoring Deficit × 0.3) + 
                 (Age Risk × 0.2) + 
                 (Complexity × 0.2)
    """
    score = (
        min(patch_frequency, 100) * 0.3 +
        min(refactoring_deficit, 100) * 0.3 +
        min(age_risk, 100) * 0.2 +
        min(complexity, 100) * 0.2
    )
    return min(score, 100)

def analyze_file_turnover(prs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze file-level turnover from PR data.
    
    Returns:
        Dictionary with file-level statistics
    """
    # Track file changes with change type classification
    file_stats = defaultdict(lambda: {
        'modification_count': 0,
        'total_additions': 0,
        'total_deletions': 0,
        'total_changes': 0,
        'first_modified': None,
        'last_modified': None,
        'last_refactored': None,  # Last time file was refactored (>30% change)
        'prs': [],
        'change_types': defaultdict(int),  # Count by change type
        'subsystem': None,
        'years_active': 0,  # Years between first and last modification
    })
    
    # Process merged PRs only
    merged_prs = [pr for pr in prs if pr.get('merged', False) and pr.get('merged_at')]
    
    print(f"Processing {len(merged_prs)} merged PRs...")
    
    for pr in merged_prs:
        merged_at = pr.get('merged_at')
        if not merged_at:
            continue
            
        try:
            merged_date = datetime.fromisoformat(merged_at.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            continue
        
        files = pr.get('files', [])
        if not files:
            continue
        
        for file_info in files:
            filename = file_info.get('filename')
            if not filename:
                continue
            
            # Skip non-code files for main analysis
            if any(filename.endswith(ext) for ext in ['.md', '.txt', '.png', '.jpg', '.svg']):
                continue
            
            additions = file_info.get('additions', 0)
            deletions = file_info.get('deletions', 0)
            changes = file_info.get('changes', additions + deletions)
            
            # Estimate file size for change classification
            # Use running estimate: current size = previous additions - deletions
            current_size_estimate = max(
                file_stats[filename]['total_additions'] - file_stats[filename]['total_deletions'],
                changes  # At least as large as this change
            )
            
            # Classify change type
            change_type = classify_change_type(changes, current_size_estimate, additions, deletions)
            
            # Update file stats
            file_stats[filename]['modification_count'] += 1
            file_stats[filename]['total_additions'] += additions
            file_stats[filename]['total_deletions'] += deletions
            file_stats[filename]['total_changes'] += changes
            file_stats[filename]['change_types'][change_type] += 1
            file_stats[filename]['prs'].append({
                'pr_number': pr.get('number'),
                'merged_at': merged_at,
                'additions': additions,
                'deletions': deletions,
                'changes': changes,
                'change_type': change_type,
            })
            
            # Track first and last modification
            if file_stats[filename]['first_modified'] is None:
                file_stats[filename]['first_modified'] = merged_date
            if (file_stats[filename]['last_modified'] is None or 
                merged_date > file_stats[filename]['last_modified']):
                file_stats[filename]['last_modified'] = merged_date
            
            # Track last refactoring (significant change >30% or >200 lines)
            if change_type == 'refactor' or change_type == 'replacement':
                if (file_stats[filename]['last_refactored'] is None or 
                    merged_date > file_stats[filename]['last_refactored']):
                    file_stats[filename]['last_refactored'] = merged_date
            
            # Categorize subsystem (use first categorization)
            if file_stats[filename]['subsystem'] is None:
                file_stats[filename]['subsystem'] = categorize_file(filename)
    
    # Calculate derived metrics including technical debt scores
    file_metrics = {}
    now = datetime.now()
    
    for filename, stats in file_stats.items():
        # Calculate file age (days since last modification)
        if stats['last_modified']:
            age_days = (now.replace(tzinfo=stats['last_modified'].tzinfo) - stats['last_modified']).days
            age_years = age_days / 365.25
        else:
            age_days = None
            age_years = None
        
        # Calculate years active (first to last modification)
        if stats['first_modified'] and stats['last_modified']:
            years_active = (stats['last_modified'] - stats['first_modified']).days / 365.25
        else:
            years_active = 0
        
        # Estimate current file size
        estimated_size = max(
            stats['total_additions'] - stats['total_deletions'],
            stats['total_changes'] // 10,  # Rough heuristic
            100  # Minimum size estimate
        )
        
        # Calculate change type statistics
        patches = stats['change_types']['patch'] + stats['change_types']['bug_fix']
        refactors = stats['change_types']['refactor'] + stats['change_types']['replacement']
        features = stats['change_types']['feature']
        
        # Patch-to-refactor ratio
        if refactors > 0:
            patch_to_refactor_ratio = patches / refactors
        elif patches > 0:
            patch_to_refactor_ratio = patches  # High ratio = only patches, no refactoring
        else:
            patch_to_refactor_ratio = 0
        
        # Calculate years since last refactor
        if stats['last_refactored']:
            years_since_refactor = (now.replace(tzinfo=stats['last_refactored'].tzinfo) - 
                                   stats['last_refactored']).days / 365.25
        else:
            years_since_refactor = None
        
        # Calculate technical debt score components
        # 1. Patch Frequency (0-100): Modifications per year
        if years_active > 0:
            patch_frequency = min((stats['modification_count'] / years_active) * 10, 100)
        else:
            patch_frequency = 0
        
        # 2. Refactoring Deficit (0-100): Years since last refactor (if modified but not refactored)
        if years_since_refactor is not None:
            # If modified recently but not refactored = debt
            if stats['modification_count'] > 0 and refactors == 0:
                refactoring_deficit = min(years_since_refactor * 20, 100)  # Max at 5 years
            elif years_since_refactor > 3:
                refactoring_deficit = min((years_since_refactor - 3) * 20, 100)
            else:
                refactoring_deficit = 0
        elif stats['modification_count'] > 0 and refactors == 0:
            # Never refactored but modified = high debt
            refactoring_deficit = 100
        else:
            refactoring_deficit = 0
        
        # 3. Age Risk (0-100): Old critical code = higher risk
        is_critical = is_critical_subsystem(stats['subsystem'])
        if age_years is not None:
            if is_critical and age_years > 10:
                age_risk = 100  # Ancient consensus code = maximum risk
            elif is_critical and age_years > 5:
                age_risk = min((age_years - 5) * 20, 100)
            elif age_years > 10:
                age_risk = min((age_years - 10) * 10, 100)
            else:
                age_risk = 0
        else:
            age_risk = 0
        
        # 4. Complexity (0-100): Many patches on small file = accumulated shortcuts
        if estimated_size > 0:
            complexity_ratio = stats['modification_count'] / (estimated_size / 100)  # Mods per 100 lines
            complexity = min(complexity_ratio * 10, 100)
        else:
            complexity = 0
        
        # Calculate debt score
        debt_score = calculate_debt_score(
            patch_frequency,
            refactoring_deficit,
            age_risk,
            complexity
        )
        
        # Categorize debt level
        if debt_score < 25:
            debt_category = 'low'
        elif debt_score < 50:
            debt_category = 'medium'
        elif debt_score < 75:
            debt_category = 'high'
        else:
            debt_category = 'critical'
        
        # Check if code is "untouchable" (modified but never refactored in 5+ years)
        is_untouchable = (
            stats['modification_count'] > 0 and
            refactors == 0 and
            (years_since_refactor is None or years_since_refactor > 5) and
            age_years is not None and age_years < 5  # Modified recently
        )
        
        # Categorize file age
        if age_years is None:
            age_category = 'unknown'
        elif age_years < 1:
            age_category = 'recent'
        elif age_years < 3:
            age_category = 'modern'
        elif age_years < 5:
            age_category = 'mature'
        elif age_years < 10:
            age_category = 'legacy'
        else:
            age_category = 'ancient'
        
        file_metrics[filename] = {
            'filename': filename,
            'subsystem': stats['subsystem'],
            'is_critical': is_critical,
            'modification_count': stats['modification_count'],
            'total_additions': stats['total_additions'],
            'total_deletions': stats['total_deletions'],
            'total_changes': stats['total_changes'],
            'estimated_size': estimated_size,
            'years_active': years_active,
            'first_modified': stats['first_modified'].isoformat() if stats['first_modified'] else None,
            'last_modified': stats['last_modified'].isoformat() if stats['last_modified'] else None,
            'last_refactored': stats['last_refactored'].isoformat() if stats['last_refactored'] else None,
            'years_since_refactor': years_since_refactor,
            'age_days': age_days,
            'age_years': age_years,
            'age_category': age_category,
            'change_types': dict(stats['change_types']),
            'patches': patches,
            'refactors': refactors,
            'features': features,
            'patch_to_refactor_ratio': patch_to_refactor_ratio,
            'debt_score': debt_score,
            'debt_category': debt_category,
            'is_untouchable': is_untouchable,
            'debt_components': {
                'patch_frequency': patch_frequency,
                'refactoring_deficit': refactoring_deficit,
                'age_risk': age_risk,
                'complexity': complexity,
            },
            'pr_count': len(stats['prs']),
        }
    
    return file_metrics

def calculate_aggregate_metrics(file_metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate aggregate statistics including technical debt metrics."""
    if not file_metrics:
        return {}
    
    # Count files by category
    age_counts = defaultdict(int)
    subsystem_counts = defaultdict(int)
    debt_category_counts = defaultdict(int)
    
    total_modifications = 0
    total_changes = 0
    total_additions = 0
    total_deletions = 0
    total_patches = 0
    total_refactors = 0
    untouchable_count = 0
    high_debt_count = 0  # Debt score >50
    
    ages = []
    debt_scores = []
    patch_to_refactor_ratios = []
    
    # Track by subsystem
    subsystem_stats = defaultdict(lambda: {
        'files': 0,
        'total_debt_score': 0,
        'high_debt_count': 0,
        'untouchable_count': 0,
        'total_patches': 0,
        'total_refactors': 0,
    })
    
    for filename, metrics in file_metrics.items():
        age_counts[metrics['age_category']] += 1
        subsystem_counts[metrics['subsystem']] += 1
        debt_category_counts[metrics['debt_category']] += 1
        
        total_modifications += metrics['modification_count']
        total_changes += metrics['total_changes']
        total_additions += metrics['total_additions']
        total_deletions += metrics['total_deletions']
        total_patches += metrics['patches']
        total_refactors += metrics['refactors']
        
        if metrics['is_untouchable']:
            untouchable_count += 1
        if metrics['debt_score'] > 50:
            high_debt_count += 1
        
        if metrics['age_years'] is not None:
            ages.append(metrics['age_years'])
        debt_scores.append(metrics['debt_score'])
        if metrics['patch_to_refactor_ratio'] > 0:
            patch_to_refactor_ratios.append(metrics['patch_to_refactor_ratio'])
        
        # Subsystem statistics
        subsystem = metrics['subsystem']
        subsystem_stats[subsystem]['files'] += 1
        subsystem_stats[subsystem]['total_debt_score'] += metrics['debt_score']
        if metrics['debt_score'] > 50:
            subsystem_stats[subsystem]['high_debt_count'] += 1
        if metrics['is_untouchable']:
            subsystem_stats[subsystem]['untouchable_count'] += 1
        subsystem_stats[subsystem]['total_patches'] += metrics['patches']
        subsystem_stats[subsystem]['total_refactors'] += metrics['refactors']
    
    num_files = len(file_metrics)
    
    # Calculate percentiles
    ages_sorted = sorted(ages) if ages else []
    debt_scores_sorted = sorted(debt_scores) if debt_scores else []
    ratios_sorted = sorted(patch_to_refactor_ratios) if patch_to_refactor_ratios else []
    
    # Calculate subsystem averages
    subsystem_debt = {}
    for subsystem, stats in subsystem_stats.items():
        if stats['files'] > 0:
            subsystem_debt[subsystem] = {
                'files': stats['files'],
                'avg_debt_score': stats['total_debt_score'] / stats['files'],
                'high_debt_percentage': (stats['high_debt_count'] / stats['files']) * 100,
                'untouchable_percentage': (stats['untouchable_count'] / stats['files']) * 100,
                'total_patches': stats['total_patches'],
                'total_refactors': stats['total_refactors'],
                'patch_to_refactor_ratio': (
                    stats['total_patches'] / stats['total_refactors']
                    if stats['total_refactors'] > 0 else stats['total_patches']
                ),
            }
    
    # Overall patch-to-refactor ratio
    overall_patch_to_refactor = (
        total_patches / total_refactors
        if total_refactors > 0 else total_patches
    )
    
    return {
        'total_files': num_files,
        'total_modifications': total_modifications,
        'total_changes': total_changes,
        'total_additions': total_additions,
        'total_deletions': total_deletions,
        'total_patches': total_patches,
        'total_refactors': total_refactors,
        'overall_patch_to_refactor_ratio': overall_patch_to_refactor,
        'avg_modifications_per_file': total_modifications / num_files if num_files > 0 else 0,
        'avg_changes_per_file': total_changes / num_files if num_files > 0 else 0,
        'technical_debt_metrics': {
            'high_debt_count': high_debt_count,
            'high_debt_percentage': (high_debt_count / num_files * 100) if num_files > 0 else 0,
            'untouchable_count': untouchable_count,
            'untouchable_percentage': (untouchable_count / num_files * 100) if num_files > 0 else 0,
            'avg_debt_score': sum(debt_scores) / len(debt_scores) if debt_scores else 0,
            'median_debt_score': debt_scores_sorted[len(debt_scores_sorted)//2] if debt_scores_sorted else 0,
            'debt_distribution': dict(debt_category_counts),
        },
        'age_distribution': dict(age_counts),
        'subsystem_distribution': dict(subsystem_counts),
        'subsystem_debt': subsystem_debt,
        'age_statistics': {
            'mean': sum(ages) / len(ages) if ages else None,
            'median': ages_sorted[len(ages_sorted)//2] if ages_sorted else None,
            'min': ages_sorted[0] if ages_sorted else None,
            'max': ages_sorted[-1] if ages_sorted else None,
            'p25': ages_sorted[len(ages_sorted)//4] if ages_sorted else None,
            'p75': ages_sorted[3*len(ages_sorted)//4] if ages_sorted else None,
        } if ages_sorted else {},
        'patch_to_refactor_statistics': {
            'mean': sum(patch_to_refactor_ratios) / len(patch_to_refactor_ratios) if patch_to_refactor_ratios else None,
            'median': ratios_sorted[len(ratios_sorted)//2] if ratios_sorted else None,
            'min': ratios_sorted[0] if ratios_sorted else None,
            'max': ratios_sorted[-1] if ratios_sorted else None,
        } if ratios_sorted else {},
    }

def find_top_files(file_metrics: Dict[str, Any], metric: str, top_n: int = 20) -> List[Tuple[str, Any]]:
    """Find top N files by a given metric."""
    files_with_metric = [
        (filename, metrics[metric])
        for filename, metrics in file_metrics.items()
        if metrics.get(metric) is not None
    ]
    files_with_metric.sort(key=lambda x: x[1], reverse=True)
    return files_with_metric[:top_n]

def main():
    """Main analysis function."""
    # File paths
    data_dir = project_root / 'data' / 'github'
    prs_file = data_dir / 'prs_raw.jsonl'
    output_dir = project_root / 'findings' / 'data'
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / 'code_turnover_analysis.json'
    
    if not prs_file.exists():
        print(f"Error: PR data file not found: {prs_file}")
        sys.exit(1)
    
    print("Loading PR data...")
    prs = load_prs(prs_file)
    print(f"Loaded {len(prs)} PRs")
    
    print("Analyzing file turnover...")
    file_metrics = analyze_file_turnover(prs)
    print(f"Analyzed {len(file_metrics)} files")
    
    print("Calculating aggregate metrics...")
    aggregate_metrics = calculate_aggregate_metrics(file_metrics)
    
    # Find top files by various metrics
    top_modified = find_top_files(file_metrics, 'modification_count', 20)
    top_changes = find_top_files(file_metrics, 'total_changes', 20)
    top_debt = find_top_files(file_metrics, 'debt_score', 20)
    top_patch_ratio = find_top_files(file_metrics, 'patch_to_refactor_ratio', 20)
    oldest_files = find_top_files(file_metrics, 'age_years', 20)
    untouchable_files = [
        (f, m['debt_score'])
        for f, m in file_metrics.items()
        if m.get('is_untouchable', False)
    ]
    untouchable_files.sort(key=lambda x: x[1], reverse=True)
    
    # Prepare output
    output = {
        'analysis_date': datetime.now().isoformat(),
        'methodology': 'File-level turnover analysis using PR data',
        'data_source': str(prs_file),
        'total_prs_analyzed': len([p for p in prs if p.get('merged', False)]),
        'aggregate_metrics': aggregate_metrics,
        'top_files': {
            'highest_debt': [
                {'filename': f, 'value': v, **file_metrics[f]}
                for f, v in top_debt
            ],
            'most_modified': [
                {'filename': f, 'value': v, **file_metrics[f]}
                for f, v in top_modified
            ],
            'highest_patch_ratio': [
                {'filename': f, 'value': v, **file_metrics[f]}
                for f, v in top_patch_ratio
            ],
            'untouchable_code': [
                {'filename': f, 'value': v, **file_metrics[f]}
                for f, v in untouchable_files[:20]
            ],
            'oldest_files': [
                {'filename': f, 'value': v, **file_metrics[f]}
                for f, v in oldest_files
            ],
        },
        'file_metrics': file_metrics,
    }
    
    # Save results
    print(f"Saving results to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, default=str)
    
    # Print summary
    print("\n" + "="*80)
    print("TECHNICAL DEBT ANALYSIS SUMMARY")
    print("="*80)
    print(f"\nTotal files analyzed: {aggregate_metrics.get('total_files', 0):,}")
    print(f"Total modifications: {aggregate_metrics.get('total_modifications', 0):,}")
    print(f"Total code changes: {aggregate_metrics.get('total_changes', 0):,}")
    
    # Technical debt metrics
    debt_metrics = aggregate_metrics.get('technical_debt_metrics', {})
    print(f"\n{'='*80}")
    print("TECHNICAL DEBT METRICS")
    print(f"{'='*80}")
    print(f"High debt files (score >50): {debt_metrics.get('high_debt_count', 0):,} ({debt_metrics.get('high_debt_percentage', 0):.1f}%)")
    print(f"Untouchable code: {debt_metrics.get('untouchable_count', 0):,} ({debt_metrics.get('untouchable_percentage', 0):.1f}%)")
    print(f"Average debt score: {debt_metrics.get('avg_debt_score', 0):.1f}")
    print(f"Median debt score: {debt_metrics.get('median_debt_score', 0):.1f}")
    
    print(f"\nDebt Distribution:")
    for category, count in debt_metrics.get('debt_distribution', {}).items():
        pct = (count / aggregate_metrics['total_files'] * 100) if aggregate_metrics['total_files'] > 0 else 0
        print(f"  {category:20s}: {count:5d} files ({pct:5.1f}%)")
    
    # Patch-to-refactor ratio
    print(f"\n{'='*80}")
    print("PATCH-TO-REFACTOR ANALYSIS")
    print(f"{'='*80}")
    print(f"Total patches: {aggregate_metrics.get('total_patches', 0):,}")
    print(f"Total refactors: {aggregate_metrics.get('total_refactors', 0):,}")
    print(f"Overall patch-to-refactor ratio: {aggregate_metrics.get('overall_patch_to_refactor_ratio', 0):.1f}")
    if aggregate_metrics.get('patch_to_refactor_statistics'):
        ratio_stats = aggregate_metrics['patch_to_refactor_statistics']
        print(f"  Mean ratio: {ratio_stats.get('mean', 0):.1f}")
        print(f"  Median ratio: {ratio_stats.get('median', 0):.1f}")
    
    # Subsystem debt
    print(f"\n{'='*80}")
    print("DEBT BY SUBSYSTEM")
    print(f"{'='*80}")
    subsystem_debt = aggregate_metrics.get('subsystem_debt', {})
    for subsystem, stats in sorted(subsystem_debt.items(), key=lambda x: x[1]['avg_debt_score'], reverse=True):
        print(f"\n{subsystem.upper()}:")
        print(f"  Files: {stats['files']}")
        print(f"  Avg debt score: {stats['avg_debt_score']:.1f}")
        print(f"  High debt: {stats['high_debt_percentage']:.1f}%")
        print(f"  Untouchable: {stats['untouchable_percentage']:.1f}%")
        print(f"  Patch-to-refactor ratio: {stats['patch_to_refactor_ratio']:.1f}")
    
    # File age distribution
    print(f"\n{'='*80}")
    print("CODE AGE DISTRIBUTION")
    print(f"{'='*80}")
    for age, count in aggregate_metrics.get('age_distribution', {}).items():
        pct = (count / aggregate_metrics['total_files'] * 100) if aggregate_metrics['total_files'] > 0 else 0
        print(f"  {age:20s}: {count:5d} files ({pct:5.1f}%)")
    
    if aggregate_metrics.get('age_statistics'):
        age_stats = aggregate_metrics['age_statistics']
        print(f"\nAge Statistics:")
        print(f"  Mean age: {age_stats.get('mean', 0):.1f} years")
        print(f"  Median age: {age_stats.get('median', 0):.1f} years")
        print(f"  Oldest code: {age_stats.get('max', 0):.1f} years")
    
    # Top files
    print(f"\n{'='*80}")
    print("TOP 10 FILES BY DEBT SCORE")
    print(f"{'='*80}")
    for i, (filename, score) in enumerate(top_debt[:10], 1):
        metrics = file_metrics[filename]
        print(f"  {i:2d}. {filename:50s} (Score: {score:.1f}, Patches: {metrics['patches']}, Refactors: {metrics['refactors']})")
    
    print(f"\n{'='*80}")
    print("TOP 10 UNTOUCHABLE FILES")
    print(f"{'='*80}")
    for i, (filename, score) in enumerate(untouchable_files[:10], 1):
        metrics = file_metrics[filename]
        print(f"  {i:2d}. {filename:50s} (Score: {score:.1f}, Modified: {metrics['modification_count']}x, Never refactored)")
    
    print(f"\nResults saved to: {output_file}")
    print("="*80)

if __name__ == '__main__':
    main()

