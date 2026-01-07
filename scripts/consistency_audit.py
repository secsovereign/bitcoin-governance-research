#!/usr/bin/env python3
"""
Consistency Audit: Find and fix all inconsistencies across findings

Ensures all reports use the latest methodology and consistent metrics.
"""

import re
from pathlib import Path
from collections import defaultdict

# Latest correct values
CORRECT_METRICS = {
    'zero_review_historical': '34.1%',  # Latest with cross-platform
    'zero_review_recent': '3.4%',  # Latest
    'self_merge_rate': '26.5%',  # Rounded from 26.46-26.63%
    'gini_historical': '0.851',
    'gini_recent': '0.837',
    'top_3_control': '81.1%',
    'top_10_control_historical': '42.7%',
    'top_10_control_recent': '49.8%',
}

# Patterns to find and replace
REPLACEMENTS = [
    # Zero-review historical
    (r'34\.3%', '34.1%', 'zero-review historical (with cross-platform)'),
    (r'34\.2%', '34.1%', 'zero-review historical'),
    (r'34\.13%', '34.1%', 'zero-review historical (rounded)'),
    
    # Zero-review recent
    (r'3\.3%', '3.4%', 'zero-review recent'),
    (r'3\.39%', '3.4%', 'zero-review recent (rounded)'),
    
    # Self-merge (standardize to 26.5%)
    (r'26\.46%', '26.5%', 'self-merge rate (historical)'),
    (r'26\.63%', '26.5%', 'self-merge rate (recent)'),
    
    # Top 3 control
    (r'\b81%\b', '81.1%', 'top 3 control (more precise)'),
    
    # Top 10 control (context-dependent)
    # Will handle separately
    
    # Gini (context-dependent)
    # Will handle separately
]

def audit_file(filepath: Path) -> list:
    """Audit a single file for inconsistencies."""
    issues = []
    content = filepath.read_text()
    original_content = content
    
    # Apply replacements
    for pattern, replacement, reason in REPLACEMENTS:
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            if content != original_content:
                issues.append(f"  Fixed: {pattern} -> {replacement} ({reason})")
    
    return issues, content

if __name__ == '__main__':
    findings_dir = Path('findings')
    all_issues = []
    
    for md_file in sorted(findings_dir.glob('*.md')):
        if 'archive' in str(md_file):
            continue
        
        issues, new_content = audit_file(md_file)
        if issues:
            print(f"\n{md_file.name}:")
            for issue in issues:
                print(issue)
