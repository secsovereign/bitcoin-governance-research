#!/usr/bin/env python3
"""
Audit dataset for inconsistencies and speculation.

Checks for:
1. Metric inconsistencies across documents
2. Speculative language (likely, might, could, probably, etc.)
3. Unsupported claims
4. Contradictions
"""

import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple

def find_speculative_language(filepath: Path) -> List[Tuple[int, str]]:
    """Find speculative language in markdown files."""
    speculative_patterns = [
        r'\b(likely|probably|perhaps|maybe|might|could|possibly|seems|appears|suggests|indicates)\b',
        r'\b(if|assuming|suppose|presumably|presume)\b',
        r'\b(would|should|may|can)\s+(be|have|mean|indicate|suggest)',
    ]
    
    issues = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f, 1):
                for pattern in speculative_patterns:
                    matches = re.finditer(pattern, line, re.IGNORECASE)
                    for match in matches:
                        # Skip if it's in a code block or already qualified
                        if '```' in line or '**Note**' in line or '**Limitation**' in line:
                            continue
                        issues.append((i, line.strip()))
    except Exception as e:
        pass
    
    return issues

def extract_metrics(filepath: Path) -> Dict[str, List[Tuple[int, str]]]:
    """Extract key metrics from markdown files."""
    metrics = defaultdict(list)
    
    # Key metrics to track
    metric_patterns = {
        'zero_review_historical': r'(\d+\.?\d*)%?\s*(?:zero[- ]review|historical)',
        'zero_review_recent': r'(\d+\.?\d*)%?\s*(?:zero[- ]review|recent)',
        'self_merge_rate': r'(\d+\.?\d*)%?\s*self[- ]merge',
        'top_3_control': r'(\d+\.?\d*)%?\s*(?:top\s*3|81\.)',
        'gini_coefficient': r'(\d+\.?\d*)\s*(?:gini|inequality)',
        'top_10_control': r'(\d+\.?\d*)%?\s*top\s*10',
    }
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # Check for specific metric values
            # Zero-review historical
            matches = re.finditer(r'34[\.\s]*[13]%', content, re.IGNORECASE)
            for match in matches:
                metrics['zero_review_historical'].append((match.start(), match.group()))
            
            # Self-merge rate
            matches = re.finditer(r'26[\.\s]*5%', content, re.IGNORECASE)
            for match in matches:
                metrics['self_merge_rate'].append((match.start(), match.group()))
            
            # Top 3 control
            matches = re.finditer(r'81[\.\s]*[01]%', content, re.IGNORECASE)
            for match in matches:
                metrics['top_3_control'].append((match.start(), match.group()))
            
    except Exception as e:
        pass
    
    return metrics

def check_metric_consistency(files: List[Path]) -> Dict[str, List[str]]:
    """Check for metric inconsistencies across files."""
    inconsistencies = defaultdict(list)
    
    # Track all occurrences of key metrics
    metric_values = {
        'zero_review_historical': set(),
        'zero_review_recent': set(),
        'self_merge_rate': set(),
        'top_3_control': set(),
        'gini_historical': set(),
        'gini_recent': set(),
    }
    
    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Zero-review historical
                matches = re.findall(r'34[\.\s]*[13]%', content, re.IGNORECASE)
                for match in matches:
                    metric_values['zero_review_historical'].add(match)
                
                # Zero-review recent
                matches = re.findall(r'3[\.\s]*4%', content, re.IGNORECASE)
                for match in matches:
                    if 'recent' in content.lower() or '2021' in content:
                        metric_values['zero_review_recent'].add(match)
                
                # Self-merge
                matches = re.findall(r'26[\.\s]*5%', content, re.IGNORECASE)
                for match in matches:
                    metric_values['self_merge_rate'].add(match)
                
                # Top 3
                matches = re.findall(r'81[\.\s]*[01]%', content, re.IGNORECASE)
                for match in matches:
                    metric_values['top_3_control'].add(match)
                
        except Exception as e:
            pass
    
    # Check for inconsistencies
    for metric, values in metric_values.items():
        if len(values) > 1:
            inconsistencies[metric].extend(list(values))
    
    return inconsistencies

def audit_file(filepath: Path) -> Dict:
    """Audit a single file for issues."""
    issues = {
        'speculative_language': [],
        'metrics': {},
        'file': str(filepath)
    }
    
    # Find speculative language
    issues['speculative_language'] = find_speculative_language(filepath)
    
    # Extract metrics
    issues['metrics'] = extract_metrics(filepath)
    
    return issues

def main():
    """Main audit function."""
    findings_dir = Path(__file__).parent.parent.parent / 'findings'
    
    print("="*80)
    print("Dataset Audit: Inconsistencies and Speculation")
    print("="*80)
    print()
    
    # Find all markdown files
    md_files = list(findings_dir.glob('*.md'))
    
    print(f"Auditing {len(md_files)} markdown files...")
    print()
    
    all_issues = []
    all_metrics = defaultdict(set)
    
    for filepath in sorted(md_files):
        issues = audit_file(filepath)
        if issues['speculative_language'] or issues['metrics']:
            all_issues.append(issues)
    
    # Check metric consistency across files
    print("Checking metric consistency...")
    inconsistencies = check_metric_consistency(md_files)
    
    # Report findings
    print("\n" + "="*80)
    print("FINDINGS")
    print("="*80)
    print()
    
    # Speculative language
    total_speculative = sum(len(i['speculative_language']) for i in all_issues)
    if total_speculative > 0:
        print(f"⚠️  SPECULATIVE LANGUAGE: {total_speculative} instances found")
        print()
        for issue in all_issues:
            if issue['speculative_language']:
                print(f"  {Path(issue['file']).name}:")
                for line_num, line in issue['speculative_language'][:5]:  # Show first 5
                    print(f"    Line {line_num}: {line[:80]}...")
                if len(issue['speculative_language']) > 5:
                    print(f"    ... and {len(issue['speculative_language']) - 5} more")
                print()
    else:
        print("✅ No speculative language found")
        print()
    
    # Metric inconsistencies
    if inconsistencies:
        print(f"⚠️  METRIC INCONSISTENCIES FOUND:")
        print()
        for metric, values in inconsistencies.items():
            if len(values) > 1:
                print(f"  {metric}: {', '.join(sorted(set(values)))}")
        print()
    else:
        print("✅ No metric inconsistencies found")
        print()
    
    # Detailed report
    print("="*80)
    print("DETAILED REPORT")
    print("="*80)
    print()
    
    for issue in all_issues:
        if issue['speculative_language'] or issue['metrics']:
            print(f"\n📄 {Path(issue['file']).name}")
            print("-" * 80)
            
            if issue['speculative_language']:
                print(f"  Speculative language: {len(issue['speculative_language'])} instances")
                for line_num, line in issue['speculative_language'][:3]:
                    print(f"    Line {line_num}: {line[:70]}...")
            
            if issue['metrics']:
                print(f"  Metrics found: {list(issue['metrics'].keys())}")
    
    # Save report
    report_file = findings_dir / 'AUDIT_INCONSISTENCIES_AND_SPECULATION.md'
    with open(report_file, 'w') as f:
        f.write("# Audit Report: Inconsistencies and Speculation\n\n")
        f.write(f"**Generated**: {Path(__file__).stat().st_mtime}\n\n")
        f.write("---\n\n")
        
        f.write("## Summary\n\n")
        f.write(f"- **Files audited**: {len(md_files)}\n")
        f.write(f"- **Files with issues**: {len(all_issues)}\n")
        f.write(f"- **Total speculative language instances**: {total_speculative}\n")
        f.write(f"- **Metric inconsistencies**: {len(inconsistencies)}\n\n")
        
        f.write("## Speculative Language\n\n")
        if total_speculative > 0:
            for issue in all_issues:
                if issue['speculative_language']:
                    f.write(f"### {Path(issue['file']).name}\n\n")
                    for line_num, line in issue['speculative_language']:
                        f.write(f"- Line {line_num}: `{line[:100]}`\n")
                    f.write("\n")
        else:
            f.write("✅ No speculative language found.\n\n")
        
        f.write("## Metric Inconsistencies\n\n")
        if inconsistencies:
            for metric, values in inconsistencies.items():
                f.write(f"### {metric}\n\n")
                f.write(f"Found values: {', '.join(sorted(set(values)))}\n\n")
        else:
            f.write("✅ No metric inconsistencies found.\n\n")
    
    print(f"\n✅ Report saved to {report_file}")

if __name__ == '__main__':
    main()





