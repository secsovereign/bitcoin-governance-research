#!/usr/bin/env python3
"""
Consolidate Redundant Content Within Documents

Removes repetitive sections and consolidates similar content.
"""

import re
from pathlib import Path

base_dir = Path(__file__).parent.parent
pub_dir = base_dir / 'publication-package'
findings_dir = pub_dir / 'findings'

def consolidate_core_vs_commons():
    """Consolidate CORE_VS_COMMONS document - remove repetitive sections."""
    doc_path = findings_dir / 'CORE_VS_COMMONS_GOVERNANCE_COMPARISON.md'
    
    if not doc_path.exists():
        return
    
    content = doc_path.read_text(encoding='utf-8')
    
    # Sections to remove (redundant with other sections)
    sections_to_remove = [
        r'## Reframing the Narrative.*?(?=## |$)',
        r'## Comparative Metrics: Why 26\.5% Is Still Problematic.*?(?=## |$)',
        r'## The Real Problem: Structural Inequality.*?(?=## |$)',
        r'## Specific Critiques of 26\.5% Self-Merge.*?(?=## |$)',
    ]
    
    # Remove redundant sections
    for pattern in sections_to_remove:
        content = re.sub(pattern, '', content, flags=re.DOTALL)
    
    # Consolidate repetitive lists - keep only the most comprehensive version
    # Remove duplicate "5 points" lists - they appear in multiple places
    
    # Find all instances of the 5-point list
    five_point_pattern = r'(?:1\.|1\))\s*\*\*Arbitrary authority\*\*.*?(?:5\.|5\))\s*\*\*No transparency\*\*'
    matches = list(re.finditer(five_point_pattern, content, re.DOTALL | re.IGNORECASE))
    
    # Keep only the first comprehensive instance, remove others
    if len(matches) > 1:
        # Keep first, remove rest
        for match in reversed(matches[1:]):  # Reverse to maintain positions
            content = content[:match.start()] + content[match.end():]
    
    # Remove excessive repetition of "26.5%" - consolidate mentions
    # Keep key mentions but remove redundant explanations
    
    # Consolidate conclusion - remove if it just repeats executive summary
    conclusion_pattern = r'## Conclusion\n\n.*?(?=## |$)'
    conclusion_match = re.search(conclusion_pattern, content, re.DOTALL)
    exec_summary_pattern = r'## Executive Summary\n\n.*?(?=## |$)'
    exec_match = re.search(exec_summary_pattern, content, re.DOTALL)
    
    if conclusion_match and exec_match:
        conclusion_text = conclusion_match.group(0).lower()
        exec_text = exec_match.group(0).lower()
        
        # Check overlap
        conclusion_words = set(re.findall(r'\b\w{5,}\b', conclusion_text))
        exec_words = set(re.findall(r'\b\w{5,}\b', exec_text))
        overlap = len(conclusion_words.intersection(exec_words)) / len(conclusion_words) * 100 if conclusion_words else 0
        
        if overlap > 70:
            # Conclusion is too similar to exec summary - make it more concise
            # Replace with brief conclusion
            new_conclusion = """## Conclusion

The 26.5% self-merge rate reveals structural governance problems: arbitrary authority, exclusive privilege, no accountability, power concentration, and lack of transparency. A commons governance model would address these through rule-based authority, equal treatment, community accountability, distributed power, and transparent processes.

The rate is less important than the **structural inequality** it represents."""
            
            content = content[:conclusion_match.start()] + new_conclusion + content[conclusion_match.end():]
    
    # Clean up extra blank lines
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    # Write back
    doc_path.write_text(content, encoding='utf-8')
    print(f"✅ Consolidated {doc_path.name}")

def main():
    """Consolidate redundant content."""
    print("="*80)
    print("CONSOLIDATING REDUNDANT CONTENT")
    print("="*80)
    print()
    
    consolidate_core_vs_commons()
    
    print()
    print("="*80)
    print("CONSOLIDATION COMPLETE")
    print("="*80)

if __name__ == '__main__':
    main()
