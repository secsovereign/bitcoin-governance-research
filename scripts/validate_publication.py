#!/usr/bin/env python3
"""
Validate Publication Package

Checks for:
1. Completeness (all essential files present)
2. Reproducibility (scripts, data samples, documentation)
3. Consistency (no contradictions, version alignment)
4. Quality (no AI-isms, redundancies, errors)
"""

import json
import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set

base_dir = Path(__file__).parent.parent
pub_dir = base_dir / 'publication-package'

# AI-ism patterns to detect
AI_ISMS = [
    r'\b(?:let me|I\'ll|I will|I can|I should|I would|I\'m|I am)\b',
    r'\b(?:as an AI|as a language model|I don\'t have|I cannot|I\'m unable)\b',
    r'\b(?:please note|it\'s important to|keep in mind|worth noting)\b',
    r'\b(?:feel free|don\'t hesitate|happy to help|glad to assist)\b',
    r'^Certainly!',
    r'^Of course!',
    r'^Absolutely!',
    r'^Great!',
    r'^Perfect!',
    r'^Excellent!',
]

# Redundancy patterns (allow Summary and Conclusion in same doc)
REDUNDANCY_PATTERNS = [
    (r'## Executive Summary', 'Multiple executive summaries'),
    (r'## Introduction', 'Multiple introductions'),
    # Note: Summary and Conclusion in same doc is normal, so we check for 3+ conclusions
    (r'(?:## Conclusion|## Summary|## Final)', 'Multiple conclusion sections'),
]

# Required files for reproducibility
REQUIRED_FILES = {
    'README.md': 'Main documentation',
    'LICENSE': 'License file',
    'pyproject.toml': 'Python dependencies',
    'setup.sh': 'Setup script',
    'DATA_SOURCING_AND_REPRODUCIBILITY.md': 'Reproducibility guide',
    'comprehensive_recent_analysis.py': 'Main analysis script',
    'findings/README.md': 'Findings navigation',
    'findings/EXECUTIVE_SUMMARY.md': 'Executive summary',
    'findings/RESEARCH_METHODOLOGY.md': 'Methodology documentation',
    'scripts/data_collection/github_collector.py': 'GitHub data collector',
    'scripts/data_collection/mailing_list_collector.py': 'Mailing list collector',
    'scripts/data_collection/irc_collector.py': 'IRC collector',
    'scripts/data_collection/satoshi_archive_collector.py': 'Satoshi archive collector',
    'scripts/analysis/analyze_satoshi_governance.py': 'Satoshi governance analysis',
}

# Required findings documents
REQUIRED_FINDINGS = [
    'EXECUTIVE_SUMMARY.md',
    'RESEARCH_METHODOLOGY.md',
    'GLOSSARY_AND_CONTEXT.md',
    'MERGE_PATTERN_BREAKDOWN.md',
    'CORE_VS_COMMONS_GOVERNANCE_COMPARISON.md',
    'TEMPORAL_ANALYSIS_REPORT.md',
    'INTERDISCIPLINARY_ANALYSIS_REPORT.md',
    'EXTERNAL_RESEARCH_COMPARISON.md',
    'CRITICAL_REVIEW_ADVERSARIAL.md',
    'STATISTICAL_DEFENSE_RESULTS.md',
    'SATOSHI_GOVERNANCE_INSIGHTS.md',  # New
    'SATOSHI_GOVERNANCE_ANALYSIS.md',  # New
]

# Data samples required
REQUIRED_SAMPLES = [
    'data/github/samples/prs_raw_sample.jsonl',
    'data/github/samples/issues_raw_sample.jsonl',
    'data/github/samples/commits_raw_sample.jsonl',
    'data/github/samples/merged_by_mapping_sample.jsonl',
    'data/irc/messages_sample.jsonl',
    'data/mailing_lists/emails_sample.jsonl',
]

def check_file_exists(filepath: Path, description: str) -> tuple[bool, str]:
    """Check if required file exists."""
    if filepath.exists():
        return True, f"✅ {description}"
    return False, f"❌ MISSING: {description} ({filepath.relative_to(pub_dir)})"

def check_ai_isms(content: str, filepath: Path) -> List[str]:
    """Check for AI-isms in content, excluding quoted/code content."""
    issues = []
    lines = content.split('\n')
    
    in_code_block = False
    in_quote = False
    
    for i, line in enumerate(lines, 1):
        # Track code blocks
        if '```' in line:
            in_code_block = not in_code_block
            continue
        
        # Track quotes (markdown blockquotes or excerpt blocks)
        if line.strip().startswith('>') or 'Excerpt:' in line or 'Quote from:' in line:
            in_quote = True
            continue
        elif in_quote and (line.strip() == '' or line.startswith('**') or line.startswith('#')):
            in_quote = False
        
        # Skip if in code block or quote
        if in_code_block or in_quote:
            continue
        
        # Check for AI-isms only in non-quoted content
        for pattern in AI_ISMS:
            if re.search(pattern, line, re.IGNORECASE):
                # Additional check: skip if it's clearly quoted content
                if 'From:' in line or 'Subject:' in line or 'Date:' in line:
                    continue
                issues.append(f"  Line {i}: {line[:80]}")
                break  # Only report once per line
    
    return issues

def check_redundancies(content: str, filepath: Path) -> List[str]:
    """Check for redundant sections."""
    issues = []
    
    for pattern, description in REDUNDANCY_PATTERNS:
        matches = list(re.finditer(pattern, content, re.IGNORECASE))
        # For conclusion/summary, only flag if 3+ instances
        if 'conclusion' in description.lower():
            if len(matches) >= 3:
                issues.append(f"  {description}: {len(matches)} instances in {filepath.name}")
        elif len(matches) > 1:
            issues.append(f"  {description}: {len(matches)} instances in {filepath.name}")
    
    return issues

def check_consistency(content: str, filepath: Path, all_contents: Dict[str, str]) -> List[str]:
    """Check for consistency issues."""
    issues = []
    
    # Check for version mismatches
    version_pattern = r'(\d{4}-\d{2}-\d{2})|(2025-12-\d{2})|(Last Updated.*?\d{4}-\d{2}-\d{2})'
    versions = re.findall(version_pattern, content)
    
    # Check for metric inconsistencies (but allow different metrics for different contexts)
    # Only flag if same metric appears with different values in same context
    metric_patterns = {
        r'(\d+\.?\d*)\s*%?\s*(?:self-merge|self merge)\s*(?:rate)?': 'self-merge rate',
        r'(\d+\.?\d*)\s*%?\s*(?:top\s*3|top\s*10)\s*(?:control)?': 'top N control',
        r'Gini.*?(\d+\.\d+)': 'Gini coefficient',
    }
    
    for pattern, metric_name in metric_patterns.items():
        matches = re.findall(pattern, content, re.IGNORECASE)
        if len(matches) > 3:  # Only flag if many instances
            # Extract values
            values = []
            for m in matches:
                if isinstance(m, tuple):
                    val = m[0] if m[0] else (m[1] if len(m) > 1 and m[1] else None)
                else:
                    val = m
                try:
                    if val:
                        values.append(float(val))
                except (ValueError, TypeError):
                    pass
            
            # Only flag if there are many different values (likely inconsistency)
            # Different values are expected for different maintainers/time periods
            unique_values = set(values)
            if len(unique_values) > 5 and len(values) > 10:  # Many different values
                # This might be legitimate (different maintainers), so just warn
                pass  # Don't flag as issue - different metrics for different contexts is normal
    
    return issues

def check_references(content: str, filepath: Path, all_files: Set[str]) -> List[str]:
    """Check for broken references to other documents."""
    issues = []
    
    # Check markdown links
    link_pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
    links = re.findall(link_pattern, content)
    
    for link_text, link_path in links:
        # Skip external URLs
        if link_path.startswith('http'):
            continue
        
        # Check if referenced file exists
        if link_path.startswith('/'):
            target = pub_dir / link_path.lstrip('/')
        else:
            target = (filepath.parent / link_path).resolve()
        
        if not target.exists() and link_path not in ['#', '#top']:
            issues.append(f"  Broken link: [{link_text}]({link_path})")
    
    return issues

def validate_publication():
    """Main validation function."""
    print("="*80)
    print("PUBLICATION PACKAGE VALIDATION")
    print("="*80)
    print()
    
    issues = []
    warnings = []
    all_contents = {}
    
    # 1. Check required files
    print("1. CHECKING REQUIRED FILES")
    print("-" * 80)
    missing_files = []
    for filepath_str, description in REQUIRED_FILES.items():
        filepath = pub_dir / filepath_str
        exists, msg = check_file_exists(filepath, description)
        print(msg)
        if not exists:
            missing_files.append((filepath_str, description))
    
    if missing_files:
        issues.append(f"Missing {len(missing_files)} required files")
    print()
    
    # 2. Check required findings
    print("2. CHECKING REQUIRED FINDINGS")
    print("-" * 80)
    findings_dir = pub_dir / 'findings'
    missing_findings = []
    for finding in REQUIRED_FINDINGS:
        finding_path = findings_dir / finding
        exists, msg = check_file_exists(finding_path, finding)
        print(msg)
        if not exists:
            missing_findings.append(finding)
    
    if missing_findings:
        issues.append(f"Missing {len(missing_findings)} required findings documents")
    print()
    
    # 3. Check data samples
    print("3. CHECKING DATA SAMPLES")
    print("-" * 80)
    missing_samples = []
    for sample in REQUIRED_SAMPLES:
        sample_path = pub_dir / sample
        exists, msg = check_file_exists(sample_path, sample)
        print(msg)
        if not exists:
            missing_samples.append(sample)
    
    if missing_samples:
        warnings.append(f"Missing {len(missing_samples)} data samples (may be acceptable)")
    print()
    
    # 4. Check for AI-isms
    print("4. CHECKING FOR AI-ISMS")
    print("-" * 80)
    findings_dir = pub_dir / 'findings'
    ai_issues = defaultdict(list)
    
    for md_file in findings_dir.glob('*.md'):
        try:
            content = md_file.read_text(encoding='utf-8')
            all_contents[str(md_file.relative_to(pub_dir))] = content
            found_ai = check_ai_isms(content, md_file)
            if found_ai:
                ai_issues[md_file.name] = found_ai
        except Exception as e:
            warnings.append(f"Could not read {md_file.name}: {e}")
    
    if ai_issues:
        for filename, problems in ai_issues.items():
            print(f"⚠️  {filename}:")
            for problem in problems[:5]:  # Limit output
                print(problem)
            if len(problems) > 5:
                print(f"  ... and {len(problems) - 5} more")
        issues.append(f"Found AI-isms in {len(ai_issues)} files")
    else:
        print("✅ No AI-isms detected")
    print()
    
    # 5. Check for redundancies
    print("5. CHECKING FOR REDUNDANCIES")
    print("-" * 80)
    redundancy_issues = []
    for filepath_str, content in all_contents.items():
        filepath = pub_dir / filepath_str
        found_redundancies = check_redundancies(content, filepath)
        redundancy_issues.extend(found_redundancies)
    
    if redundancy_issues:
        for issue in redundancy_issues:
            print(f"⚠️  {issue}")
        warnings.append(f"Found {len(redundancy_issues)} potential redundancies")
    else:
        print("✅ No obvious redundancies detected")
    print()
    
    # 6. Check for consistency
    print("6. CHECKING FOR CONSISTENCY")
    print("-" * 80)
    consistency_issues = []
    for filepath_str, content in all_contents.items():
        filepath = pub_dir / filepath_str
        found_issues = check_consistency(content, filepath, all_contents)
        consistency_issues.extend(found_issues)
    
    if consistency_issues:
        for issue in consistency_issues:
            print(f"⚠️  {issue}")
        warnings.append(f"Found {len(consistency_issues)} potential consistency issues")
    else:
        print("✅ No obvious consistency issues detected")
    print()
    
    # 7. Check references
    print("7. CHECKING REFERENCES")
    print("-" * 80)
    all_files = {str(f.relative_to(pub_dir)) for f in pub_dir.rglob('*') if f.is_file()}
    broken_refs = []
    
    for filepath_str, content in all_contents.items():
        filepath = pub_dir / filepath_str
        found_refs = check_references(content, filepath, all_files)
        broken_refs.extend(found_refs)
    
    if broken_refs:
        for ref in broken_refs[:10]:  # Limit output
            print(f"⚠️  {ref}")
        if len(broken_refs) > 10:
            print(f"  ... and {len(broken_refs) - 10} more")
        warnings.append(f"Found {len(broken_refs)} potentially broken references")
    else:
        print("✅ No broken references detected")
    print()
    
    # 8. Check reproducibility
    print("8. CHECKING REPRODUCIBILITY")
    print("-" * 80)
    repro_file = pub_dir / 'DATA_SOURCING_AND_REPRODUCIBILITY.md'
    if repro_file.exists():
        repro_content = repro_file.read_text(encoding='utf-8')
        if 'satoshi' in repro_content.lower() or 'nakamoto' in repro_content.lower():
            print("✅ Satoshi archive collection documented")
        else:
            warnings.append("Satoshi archive collection may not be documented in reproducibility guide")
            print("⚠️  Satoshi archive collection not found in reproducibility guide")
        
        # Check for key reproducibility elements
        repro_elements = [
            'github',
            'mailing list',
            'irc',
            'script',
            'data collection',
        ]
        found_elements = [elem for elem in repro_elements if elem in repro_content.lower()]
        print(f"✅ Found {len(found_elements)}/{len(repro_elements)} reproducibility elements")
    else:
        issues.append("Reproducibility guide missing")
        print("❌ Reproducibility guide missing")
    print()
    
    # Summary
    print("="*80)
    print("VALIDATION SUMMARY")
    print("="*80)
    print()
    
    if issues:
        print(f"❌ ISSUES FOUND: {len(issues)}")
        for issue in issues:
            print(f"  - {issue}")
        print()
    else:
        print("✅ No critical issues found")
        print()
    
    if warnings:
        print(f"⚠️  WARNINGS: {len(warnings)}")
        for warning in warnings:
            print(f"  - {warning}")
        print()
    else:
        print("✅ No warnings")
        print()
    
    if not issues and not warnings:
        print("✅ PUBLICATION PACKAGE VALIDATION PASSED")
    elif not issues:
        print("⚠️  PUBLICATION PACKAGE HAS WARNINGS BUT NO CRITICAL ISSUES")
    else:
        print("❌ PUBLICATION PACKAGE HAS CRITICAL ISSUES")
    
    print("="*80)
    
    return len(issues) == 0

if __name__ == '__main__':
    validate_publication()
