#!/usr/bin/env python3
"""
Final Redundancy Removal - Remove ALL 100% duplicate sections
"""

import re
from pathlib import Path

base_dir = Path(__file__).parent.parent
pub_dir = base_dir / 'publication-package'
findings_dir = pub_dir / 'findings'

def remove_duplicate_sections(content, doc_name):
    """Remove sections that are 100% duplicates."""
    sections = []
    for match in re.finditer(r'^##+\s+(.+)$', content, re.MULTILINE):
        start = match.start()
        next_match = re.search(r'^##+\s+', content[start+1:], re.MULTILINE)
        if next_match:
            end = start + 1 + next_match.start()
        else:
            end = len(content)
        sections.append({
            'title': match.group(1),
            'start': start,
            'end': end,
            'content': content[start:end]
        })
    
    # Find 100% duplicates
    to_remove = []
    for i, sec1 in enumerate(sections):
        for sec2 in sections[i+1:]:
            # Normalize
            norm1 = re.sub(r'\d+\.?\d*%?', 'X', sec1['content'].lower())
            norm1 = re.sub(r'[^\w\s]', '', norm1)
            norm2 = re.sub(r'\d+\.?\d*%?', 'X', sec2['content'].lower())
            norm2 = re.sub(r'[^\w\s]', '', norm2)
            
            words1 = set(re.findall(r'\b\w{5,}\b', norm1))
            words2 = set(re.findall(r'\b\w{5,}\b', norm2))
            
            if words1 and words2:
                overlap = len(words1.intersection(words2)) / min(len(words1), len(words2)) * 100
                if overlap > 95:
                    # Keep first, remove second
                    if sec2 not in to_remove:
                        to_remove.append(sec2)
    
    # Remove (reverse order)
    removed_titles = []
    for sec in sorted(to_remove, key=lambda x: -x['start']):
        removed_titles.append(sec['title'])
        content = content[:sec['start']] + content[sec['end']:]
    
    return content, removed_titles

# Documents with known duplicates
docs_to_fix = [
    'ENHANCED_FUNDING_ANALYSIS_REPORT.md',
    'EXTERNAL_RESEARCH_COMPARISON.md',
    'GINI_COEFFICIENT_EXPLANATION.md',
    'GLOSSARY_AND_CONTEXT.md',
    'MERGE_PATTERN_BREAKDOWN.md',
    'PR_IMPORTANCE_ANALYSIS.md',
    'RESEARCH_METHODOLOGY.md',
    'REVIEW_QUALITY_ENHANCED_ANALYSIS.md',
    'SATOSHI_GOVERNANCE_ANALYSIS.md',
    'SATOSHI_GOVERNANCE_INSIGHTS.md',
    'STATISTICAL_DEFENSE_RESULTS.md',
    'TEMPORAL_ANALYSIS_REPORT.md',
]

print("="*80)
print("REMOVING 100% DUPLICATE SECTIONS")
print("="*80)
print()

for doc_name in docs_to_fix:
    doc_path = findings_dir / doc_name
    if not doc_path.exists():
        continue
    
    content = doc_path.read_text(encoding='utf-8')
    original_len = len(content)
    
    content, removed = remove_duplicate_sections(content, doc_name)
    
    # Clean up
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    new_len = len(content)
    reduction = original_len - new_len
    
    if reduction > 50:
        doc_path.write_text(content, encoding='utf-8')
        print(f"✅ {doc_name}")
        print(f"   Removed {len(removed)} duplicate sections: {', '.join(removed[:3])}")
        print(f"   {reduction:,} chars removed")
        print()

print("="*80)
print("COMPLETE")
print("="*80)
