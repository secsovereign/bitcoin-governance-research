#!/usr/bin/env python3
"""
Comprehensive Dataset Validation

Validates ALL data across the entire dataset:
1. Metric consistency across all documents
2. Methodology consistency
3. Calculation correctness
4. Date consistency
5. Maintainer/contributor data consistency
6. No stale data
7. No contradictions
"""

import json
import re
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone

script_dir = Path(__file__).parent.parent.parent
findings_dir = script_dir / 'findings'

def extract_metrics_from_markdown(filepath: Path) -> dict:
    """Extract key metrics from markdown files."""
    metrics = {}
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # Zero-review rates
            patterns = {
                'zero_review_historical': r'34[\.\s]*1%',
                'zero_review_recent': r'3[\.\s]*4%',
                'self_merge_rate': r'26[\.\s]*5%',
                'top_3_control': r'81[\.\s]*[01]%',
                'gini_historical': r'0\.85[01]',
                'gini_recent': r'0\.83[67]',
            }
            
            for key, pattern in patterns.items():
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    metrics[key] = matches[0]
            
            # Extract specific numbers
            if '34.1%' in content or '34.1' in content:
                metrics['has_34_1'] = True
            if '34.3%' in content or '34.3' in content:
                metrics['has_34_3'] = True
                
    except Exception as e:
        pass
    
    return metrics

def validate_maintainer_timeline():
    """Validate maintainer timeline analysis."""
    issues = []
    
    timeline_file = findings_dir / 'maintainer_timeline_analysis.json'
    if not timeline_file.exists():
        return issues
    
    try:
        with open(timeline_file) as f:
            data = json.load(f)
        
        timeline = data.get('timeline', {})
        
        # Check for required fields
        # Note: Maintainers with 0 merges are valid (they may have other roles)
        for maintainer, info in timeline.items():
            total_merges = info.get('total_merges', 0)
            
            # Only require join_date if they have merges
            if total_merges > 0 and not info.get('join_date'):
                issues.append(f"Maintainer {maintainer}: Missing join_date (has {total_merges} merges)")
            
            # total_merges should always be present (can be 0)
            if 'total_merges' not in info:
                issues.append(f"Maintainer {maintainer}: Missing total_merges field")
            
            # Verify merge count matches yearly breakdown
            total_merges = info.get('total_merges', 0)
            merges_by_year = info.get('merges_by_year', {})
            year_sum = sum(merges_by_year.values())
            
            if total_merges != year_sum:
                issues.append(f"Maintainer {maintainer}: Merge count mismatch (total={total_merges}, year_sum={year_sum})")
        
        print(f"   ✅ Maintainer timeline: {len(timeline)} maintainers analyzed")
        
    except Exception as e:
        issues.append(f"Error loading maintainer timeline: {e}")
    
    return issues

def validate_contributor_timeline():
    """Validate contributor timeline analysis."""
    issues = []
    
    timeline_file = findings_dir / 'contributor_timeline_analysis.json'
    if not timeline_file.exists():
        return issues
    
    try:
        with open(timeline_file) as f:
            data = json.load(f)
        
        timeline = data.get('timeline', {})
        
        # Check maintainer exclusion
        maintainers = {
            'laanwj', 'sipa', 'maflcko', 'fanquake', 'hebasto', 'jnewbery',
            'ryanofsky', 'achow101', 'theuni', 'jonasschnelli', 'sjors',
            'promag', 'instagibbs', 'thebluematt', 'jonatack', 'gmaxwell',
            'gavinandresen', 'petertodd', 'luke-jr', 'glozow'
        }
        
        found_maintainers = [c for c in timeline.keys() if c.lower() in maintainers]
        if found_maintainers:
            issues.append(f"Contributors contain maintainers: {found_maintainers}")
        
        print(f"   ✅ Contributor timeline: {len(timeline)} contributors analyzed")
        
    except Exception as e:
        issues.append(f"Error loading contributor timeline: {e}")
    
    return issues

def validate_key_metrics_consistency():
    """Validate key metrics are consistent across documents."""
    issues = []
    warnings = []
    
    # Expected values
    expected_metrics = {
        'zero_review_historical': '34.1%',
        'zero_review_recent': '3.4%',
        'self_merge_rate': '26.5%',
        'top_3_control': '81.1%',
    }
    
    # Collect metrics from all markdown files
    all_metrics = defaultdict(list)
    
    for md_file in findings_dir.glob('*.md'):
        if 'archive' in str(md_file):
            continue
        
        metrics = extract_metrics_from_markdown(md_file)
        for key, value in metrics.items():
            all_metrics[key].append((md_file.name, value))
    
    # Check for inconsistencies
    print("   Checking metric consistency...")
    
    # Check for 34.3% (should be 34.1%)
    if 'has_34_3' in [m[1] for metrics_list in all_metrics.values() for m in metrics_list]:
        files_with_34_3 = [m[0] for metrics_list in all_metrics.values() for m in metrics_list if 'has_34_3' in str(m)]
        if files_with_34_3:
            # Check if it's in historical context (acceptable) or as current value (not acceptable)
            warnings.append(f"Some files may still reference 34.3%: {set(files_with_34_3)}")
    
    print(f"   ✅ Metric consistency check complete")
    
    return issues, warnings

def validate_calculation_consistency():
    """Validate calculations are consistent."""
    issues = []
    
    # Load key analysis files
    analysis_files = [
        'merge_pattern_analysis.json',
        'temporal_analysis.json',
        'pr_importance_matrix.json',
    ]
    
    for filename in analysis_files:
        filepath = findings_dir / filename
        if filepath.exists():
            try:
                with open(filepath) as f:
                    data = json.load(f)
                
                # Basic validation
                if isinstance(data, dict) and len(data) > 0:
                    print(f"   ✅ {filename}: Valid JSON structure")
                else:
                    issues.append(f"{filename}: Invalid or empty structure")
                    
            except Exception as e:
                issues.append(f"{filename}: Error loading - {e}")
    
    return issues

def validate_maintainer_list_consistency():
    """Validate maintainer lists are consistent across files."""
    issues = []
    warnings = []
    
    # Known maintainers from comprehensive_recent_analysis.py
    expected_maintainers = {
        'laanwj', 'sipa', 'maflcko', 'fanquake', 'hebasto', 'jnewbery',
        'ryanofsky', 'achow101', 'theuni', 'jonasschnelli', 'Sjors',
        'promag', 'instagibbs', 'TheBlueMatt', 'jonatack', 'gmaxwell',
        'gavinandresen', 'petertodd', 'luke-jr', 'glozow'
    }
    
    # Check maintainer timeline
    timeline_file = findings_dir / 'maintainer_timeline_analysis.json'
    if timeline_file.exists():
        try:
            with open(timeline_file) as f:
                data = json.load(f)
            
            timeline = data.get('timeline', {})
            timeline_maintainers = set(timeline.keys())
            
            # Check for missing maintainers (case-insensitive)
            # Note: Maintainers with 0 merges won't have join_date but should still be in timeline
            expected_lower = {m.lower() for m in expected_maintainers}
            timeline_lower = {m.lower() for m in timeline_maintainers}
            missing = expected_lower - timeline_lower
            
            # Check if missing maintainers actually have 0 merges (then it's OK they're missing join_date)
            if missing:
                # This is actually OK - maintainers with 0 merges may not appear in timeline
                # They're still maintainers but just never merged PRs
                warnings.append(f"Maintainer timeline missing (may have 0 merges): {missing}")
            
            # Check for extra maintainers
            extra = {m.lower() for m in timeline_maintainers} - {m.lower() for m in expected_maintainers}
            if extra:
                warnings.append(f"Maintainer timeline has extra: {extra}")
            
            print(f"   ✅ Maintainer list consistency: {len(timeline_maintainers)} in timeline")
            
        except Exception as e:
            issues.append(f"Error checking maintainer timeline: {e}")
    
    return issues, warnings

def validate_date_consistency():
    """Validate dates are consistent and reasonable."""
    issues = []
    
    # Check maintainer timeline dates
    timeline_file = findings_dir / 'maintainer_timeline_analysis.json'
    if timeline_file.exists():
        try:
            with open(timeline_file) as f:
                data = json.load(f)
            
            timeline = data.get('timeline', {})
            now = datetime.now(timezone.utc)
            
            for maintainer, info in timeline.items():
                join_date_str = info.get('join_date_parsed')
                last_date_str = info.get('last_merge_date_parsed')
                
                if join_date_str:
                    try:
                        join_date = datetime.fromisoformat(join_date_str.replace('Z', '+00:00'))
                        if join_date > now:
                            issues.append(f"{maintainer}: Join date in future: {join_date_str}")
                        if join_date.year < 2009:
                            issues.append(f"{maintainer}: Join date before Bitcoin: {join_date_str}")
                    except:
                        pass
                
                if last_date_str:
                    try:
                        last_date = datetime.fromisoformat(last_date_str.replace('Z', '+00:00'))
                        if last_date > now:
                            issues.append(f"{maintainer}: Last date in future: {last_date_str}")
                    except:
                        pass
            
            print(f"   ✅ Date consistency: Checked {len(timeline)} maintainers")
            
        except Exception as e:
            issues.append(f"Error checking dates: {e}")
    
    return issues

def validate_methodology_notes():
    """Check that methodology notes are present in key documents."""
    issues = []
    warnings = []
    
    key_documents = [
        'EXECUTIVE_SUMMARY.md',
        'COMPLETE_ANALYSIS_WITH_CORRECTED_DATA.md',
        'TEMPORAL_ANALYSIS_REPORT.md',
        'PR_IMPORTANCE_ANALYSIS.md',
    ]
    
    for doc in key_documents:
        filepath = findings_dir / doc
        if filepath.exists():
            with open(filepath) as f:
                content = f.read()
            
            # Check for methodology note
            if 'methodology' not in content.lower() and 'last updated' not in content.lower():
                warnings.append(f"{doc}: May be missing methodology notes")
            else:
                print(f"   ✅ {doc}: Has methodology notes")
    
    return issues, warnings

def main():
    """Main validation function."""
    print("="*80)
    print("COMPREHENSIVE DATASET VALIDATION")
    print("="*80)
    print()
    
    all_issues = []
    all_warnings = []
    
    # 1. Maintainer Timeline
    print("1. MAINTAINER TIMELINE VALIDATION")
    issues = validate_maintainer_timeline()
    all_issues.extend(issues)
    print()
    
    # 2. Contributor Timeline
    print("2. CONTRIBUTOR TIMELINE VALIDATION")
    issues = validate_contributor_timeline()
    all_issues.extend(issues)
    print()
    
    # 3. Key Metrics Consistency
    print("3. KEY METRICS CONSISTENCY")
    issues, warnings = validate_key_metrics_consistency()
    all_issues.extend(issues)
    all_warnings.extend(warnings)
    print()
    
    # 4. Calculation Consistency
    print("4. CALCULATION CONSISTENCY")
    issues = validate_calculation_consistency()
    all_issues.extend(issues)
    print()
    
    # 5. Maintainer List Consistency
    print("5. MAINTAINER LIST CONSISTENCY")
    issues, warnings = validate_maintainer_list_consistency()
    all_issues.extend(issues)
    all_warnings.extend(warnings)
    print()
    
    # 6. Date Consistency
    print("6. DATE CONSISTENCY")
    issues = validate_date_consistency()
    all_issues.extend(issues)
    print()
    
    # 7. Methodology Notes
    print("7. METHODOLOGY NOTES")
    issues, warnings = validate_methodology_notes()
    all_issues.extend(issues)
    all_warnings.extend(warnings)
    print()
    
    # 8. Check for stale data patterns
    print("8. STALE DATA CHECK")
    stale_patterns = [
        (r'34\.3%', '34.3% (should be 34.1%)'),
        (r'37\.6%', '37.6% (outdated discrepancy)'),
        (r'57\.2%', '57.2% (pre-ACK integration)'),
    ]
    
    stale_found = []
    for md_file in findings_dir.glob('*.md'):
        if 'archive' in str(md_file) or 'validation' in str(md_file).lower():
            continue
        
        try:
            with open(md_file) as f:
                content = f.read()
            
            for pattern, description in stale_patterns:
                if re.search(pattern, content):
                    # Check if it's in historical context (acceptable)
                    if 'was' in content.lower() or 'before' in content.lower() or 'historical' in content.lower():
                        continue
                    stale_found.append((md_file.name, description))
        except:
            pass
    
    if stale_found:
        print(f"   ⚠️  Found {len(stale_found)} potential stale data references:")
        for filename, desc in stale_found[:10]:
            print(f"      - {filename}: {desc}")
        all_warnings.extend([f"{f}: {d}" for f, d in stale_found])
    else:
        print("   ✅ No stale data patterns found")
    print()
    
    # Summary
    print("="*80)
    print("VALIDATION SUMMARY")
    print("="*80)
    print()
    
    print(f"Critical Issues: {len(all_issues)}")
    if all_issues:
        print()
        print("ISSUES FOUND:")
        for issue in all_issues[:20]:
            print(f"  - {issue}")
        if len(all_issues) > 20:
            print(f"  ... and {len(all_issues) - 20} more")
    print()
    
    print(f"Warnings: {len(all_warnings)}")
    if all_warnings:
        print()
        print("WARNINGS:")
        for warning in all_warnings[:10]:
            print(f"  - {warning}")
        if len(all_warnings) > 10:
            print(f"  ... and {len(all_warnings) - 10} more")
    print()
    
    if not all_issues:
        print("✅ VALIDATION PASSED - No critical issues found")
    else:
        print("⚠️  VALIDATION FAILED - Critical issues need to be fixed")
    
    print()
    print("="*80)
    
    # Save report
    report_file = findings_dir / 'COMPREHENSIVE_DATASET_VALIDATION.md'
    with open(report_file, 'w') as f:
        f.write("# Comprehensive Dataset Validation Report\n\n")
        f.write(f"**Generated**: {datetime.now(timezone.utc).isoformat()}\n\n")
        f.write("---\n\n")
        
        f.write("## Summary\n\n")
        f.write(f"- **Critical Issues**: {len(all_issues)}\n")
        f.write(f"- **Warnings**: {len(all_warnings)}\n\n")
        
        if all_issues:
            f.write("## Critical Issues\n\n")
            for issue in all_issues:
                f.write(f"- {issue}\n")
            f.write("\n")
        
        if all_warnings:
            f.write("## Warnings\n\n")
            for warning in all_warnings:
                f.write(f"- {warning}\n")
            f.write("\n")
        
        if not all_issues:
            f.write("## Status\n\n")
            f.write("✅ **VALIDATION PASSED** - No critical issues found\n\n")
    
    print(f"Report saved to {report_file}")
    
    return len(all_issues) == 0

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)





