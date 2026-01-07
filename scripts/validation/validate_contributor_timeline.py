#!/usr/bin/env python3
"""
Comprehensive validation of contributor timeline analysis.

Validates:
1. Methodology soundness
2. Data consistency
3. Calculation correctness
4. Maintainer exclusion
5. Filtering criteria compliance
"""

import json
import sys
from pathlib import Path
from collections import Counter

script_dir = Path(__file__).parent.parent.parent
data_file = script_dir / 'findings' / 'contributor_timeline_analysis.json'
report_file = script_dir / 'findings' / 'CONTRIBUTOR_TIMELINE_ANALYSIS.md'

def validate_contributor_timeline():
    """Comprehensive validation."""
    
    print("="*80)
    print("COMPREHENSIVE VALIDATION: Contributor Timeline Analysis")
    print("="*80)
    print()
    
    # Load data
    with open(data_file) as f:
        data = json.load(f)
    
    timeline = data['timeline']
    criteria = data['filtering_criteria']
    
    issues = []
    warnings = []
    
    # 1. Filtering criteria compliance
    print("1. FILTERING CRITERIA COMPLIANCE")
    violations = 0
    for contributor, info in timeline.items():
        total = info.get('total_authored', 0)
        avg_quality = info.get('avg_quality_score', 0)
        
        if total < criteria['min_contributions']:
            violations += 1
            issues.append(f"{contributor}: Only {total} PRs (min: {criteria['min_contributions']})")
        if avg_quality < criteria['min_quality_score']:
            violations += 1
            issues.append(f"{contributor}: Quality {avg_quality:.3f} (min: {criteria['min_quality_score']})")
    
    if violations == 0:
        print(f"   ✅ All {len(timeline)} contributors meet filtering criteria")
    else:
        print(f"   ❌ {violations} violations found")
        for issue in issues[:5]:
            print(f"      - {issue}")
    print()
    
    # 2. Maintainer exclusion
    print("2. MAINTAINER EXCLUSION")
    maintainers = {
        'laanwj', 'sipa', 'maflcko', 'fanquake', 'hebasto', 'jnewbery',
        'ryanofsky', 'achow101', 'theuni', 'jonasschnelli', 'sjors',
        'promag', 'instagibbs', 'thebluematt', 'jonatack', 'gmaxwell',
        'gavinandresen', 'petertodd', 'luke-jr', 'glozow'
    }
    found_maintainers = [c for c in timeline.keys() if c.lower() in maintainers]
    
    if found_maintainers:
        print(f"   ❌ Found {len(found_maintainers)} maintainers: {found_maintainers}")
        issues.extend([f"Maintainer in contributor list: {m}" for m in found_maintainers])
    else:
        print(f"   ✅ No maintainers found in {len(timeline)} contributors")
    print()
    
    # 3. Data consistency (total vs yearly breakdown)
    print("3. DATA CONSISTENCY (Total vs Yearly Breakdown)")
    inconsistencies = 0
    for contributor, info in timeline.items():
        total_authored = info.get('total_authored', 0)
        total_merged = info.get('total_merged', 0)
        authored_by_year = info.get('authored_by_year', {})
        merged_by_year = info.get('merged_by_year', {})
        
        year_sum_authored = sum(authored_by_year.values())
        year_sum_merged = sum(merged_by_year.values())
        
        if total_authored != year_sum_authored:
            inconsistencies += 1
            if inconsistencies <= 3:
                issues.append(f"{contributor}: Authored total={total_authored}, year_sum={year_sum_authored}")
        
        if total_merged != year_sum_merged:
            inconsistencies += 1
            if inconsistencies <= 3:
                issues.append(f"{contributor}: Merged total={total_merged}, year_sum={year_sum_merged}")
    
    if inconsistencies == 0:
        print(f"   ✅ Data consistency verified for all {len(timeline)} contributors")
    else:
        print(f"   ❌ {inconsistencies} inconsistencies found")
    print()
    
    # 4. Quality score calculations
    print("4. QUALITY SCORE CALCULATIONS")
    quality_errors = 0
    for contributor, info in timeline.items():
        total_quality = info.get('total_quality_score', 0)
        total_authored = info.get('total_authored', 0)
        avg_quality = info.get('avg_quality_score', 0)
        
        if total_authored > 0:
            expected_avg = total_quality / total_authored
            if abs(expected_avg - avg_quality) > 0.01:
                quality_errors += 1
                if quality_errors <= 3:
                    issues.append(f"{contributor}: Quality expected={expected_avg:.3f}, got={avg_quality:.3f}")
    
    if quality_errors == 0:
        print(f"   ✅ Quality score calculations verified for all {len(timeline)} contributors")
    else:
        print(f"   ❌ {quality_errors} calculation errors")
    print()
    
    # 5. Merge rate calculations
    print("5. MERGE RATE CALCULATIONS")
    merge_rate_errors = 0
    for contributor, info in timeline.items():
        total_authored = info.get('total_authored', 0)
        total_merged = info.get('total_merged', 0)
        merge_rate = info.get('merge_rate', 0)
        
        if total_authored > 0:
            expected_rate = (total_merged / total_authored) * 100
            if abs(expected_rate - merge_rate) > 0.1:
                merge_rate_errors += 1
                if merge_rate_errors <= 3:
                    issues.append(f"{contributor}: Merge rate expected={expected_rate:.1f}%, got={merge_rate:.1f}%")
    
    if merge_rate_errors == 0:
        print(f"   ✅ Merge rate calculations verified for all {len(timeline)} contributors")
    else:
        print(f"   ❌ {merge_rate_errors} calculation errors")
    print()
    
    # 6. Date consistency
    print("6. DATE CONSISTENCY")
    date_issues = 0
    for contributor, info in timeline.items():
        join_date = info.get('join_date')
        join_date_parsed = info.get('join_date_parsed')
        last_date = info.get('last_contribution_date')
        last_date_parsed = info.get('last_contribution_date_parsed')
        
        # Check that parsed dates match original dates (first 10 chars should match)
        if join_date and join_date_parsed:
            if join_date[:10] != join_date_parsed[:10]:
                date_issues += 1
                if date_issues <= 3:
                    warnings.append(f"{contributor}: Join date mismatch")
        
        if last_date and last_date_parsed:
            if last_date[:10] != last_date_parsed[:10]:
                date_issues += 1
                if date_issues <= 3:
                    warnings.append(f"{contributor}: Last date mismatch")
    
    if date_issues == 0:
        print(f"   ✅ Date consistency verified")
    else:
        print(f"   ⚠️  {date_issues} date inconsistencies (may be timezone-related)")
    print()
    
    # 7. Activity status validation
    print("7. ACTIVITY STATUS VALIDATION")
    from datetime import datetime, timezone, timedelta
    
    activity_issues = 0
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=180)
    
    for contributor, info in timeline.items():
        is_active = info.get('is_active', False)
        last_date_parsed = info.get('last_contribution_date_parsed')
        
        if last_date_parsed:
            try:
                last_dt = datetime.fromisoformat(last_date_parsed.replace('Z', '+00:00'))
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=timezone.utc)
                
                should_be_active = last_dt > cutoff
                if is_active != should_be_active:
                    activity_issues += 1
                    if activity_issues <= 3:
                        warnings.append(f"{contributor}: Activity status mismatch (is_active={is_active}, should_be={should_be_active})")
            except:
                pass
    
    if activity_issues == 0:
        print(f"   ✅ Activity status verified")
    else:
        print(f"   ⚠️  {activity_issues} activity status issues")
    print()
    
    # 8. Methodology validation
    print("8. METHODOLOGY VALIDATION")
    methodology_issues = []
    
    # Check quality score range
    quality_scores = [info.get('avg_quality_score', 0) for info in timeline.values()]
    min_quality = min(quality_scores) if quality_scores else 0
    max_quality = max(quality_scores) if quality_scores else 0
    
    if min_quality < 0 or max_quality > 1.0:
        methodology_issues.append(f"Quality scores out of range: min={min_quality:.3f}, max={max_quality:.3f}")
    
    # Check merge rates are reasonable (0-100%)
    merge_rates = [info.get('merge_rate', 0) for info in timeline.values()]
    min_merge = min(merge_rates) if merge_rates else 0
    max_merge = max(merge_rates) if merge_rates else 0
    
    if min_merge < 0 or max_merge > 100:
        methodology_issues.append(f"Merge rates out of range: min={min_merge:.1f}%, max={max_merge:.1f}%")
    
    # Check that merged <= authored
    for contributor, info in timeline.items():
        total_authored = info.get('total_authored', 0)
        total_merged = info.get('total_merged', 0)
        if total_merged > total_authored:
            methodology_issues.append(f"{contributor}: Merged ({total_merged}) > Authored ({total_authored})")
    
    if methodology_issues:
        print(f"   ❌ {len(methodology_issues)} methodology issues:")
        for issue in methodology_issues[:5]:
            print(f"      - {issue}")
        issues.extend(methodology_issues)
    else:
        print(f"   ✅ Methodology validated")
        print(f"      - Quality scores: {min_quality:.3f} to {max_quality:.3f} (valid range: 0.0-1.0)")
        print(f"      - Merge rates: {min_merge:.1f}% to {max_merge:.1f}% (valid range: 0-100%)")
    print()
    
    # 9. Cross-reference with markdown report
    print("9. CROSS-REFERENCE WITH MARKDOWN REPORT")
    if report_file.exists():
        with open(report_file) as f:
            report_content = f.read()
        
        # Check key numbers match
        total_in_report = len([l for l in report_content.split('\n') if 'Total Contributors Analyzed' in l])
        if total_in_report > 0:
            # Extract number from report
            import re
            match = re.search(r'Total Contributors Analyzed.*?(\d+)', report_content)
            if match:
                report_total = int(match.group(1))
                if report_total != len(timeline):
                    issues.append(f"Contributor count mismatch: JSON={len(timeline)}, Report={report_total}")
                else:
                    print(f"   ✅ Contributor count matches: {len(timeline)}")
            else:
                warnings.append("Could not extract contributor count from report")
        else:
            warnings.append("Could not find contributor count in report")
    else:
        warnings.append("Report file not found")
    print()
    
    # Summary
    print("="*80)
    print("VALIDATION SUMMARY")
    print("="*80)
    print()
    
    total_checks = 9
    passed_checks = total_checks - len([i for i in issues if '❌' in str(i) or 'Found' in str(i)])
    
    print(f"Checks passed: {passed_checks}/{total_checks}")
    print(f"Critical issues: {len([i for i in issues if '❌' in str(i) or 'Maintainer' in str(i)])}")
    print(f"Warnings: {len(warnings)}")
    print()
    
    if issues:
        print("CRITICAL ISSUES:")
        for issue in issues[:10]:
            print(f"  - {issue}")
        if len(issues) > 10:
            print(f"  ... and {len(issues) - 10} more")
        print()
    
    if warnings:
        print("WARNINGS:")
        for warning in warnings[:5]:
            print(f"  - {warning}")
        if len(warnings) > 5:
            print(f"  ... and {len(warnings) - 5} more")
        print()
    
    if not issues:
        print("✅ VALIDATION PASSED - All checks passed, methodology is sound")
    else:
        print("⚠️  VALIDATION FAILED - Issues found, review required")
    
    print()
    print("="*80)
    
    return len(issues) == 0

if __name__ == '__main__':
    success = validate_contributor_timeline()
    sys.exit(0 if success else 1)





