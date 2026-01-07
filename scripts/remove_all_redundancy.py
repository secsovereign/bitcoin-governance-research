#!/usr/bin/env python3
"""
Remove ALL Redundancy - Aggressive

Removes:
- 100% duplicate sections
- Executive Summary sections that duplicate content
- Redundant paragraphs
"""

import re
from pathlib import Path

base_dir = Path(__file__).parent.parent
pub_dir = base_dir / 'publication-package'
findings_dir = pub_dir / 'findings'

def remove_duplicate_sections(content):
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
                    # Remove the second one (keep first)
                    if sec2 not in to_remove:
                        to_remove.append(sec2)
    
    # Remove (reverse order)
    for sec in sorted(to_remove, key=lambda x: -x['start']):
        content = content[:sec['start']] + content[sec['end']:]
    
    return content

def remove_exec_summary_if_duplicate(content):
    """Remove Executive Summary if it's just a duplicate of other content."""
    # Find Executive Summary
    exec_match = re.search(r'^##\s+Executive Summary.*?(?=^##\s+|$)', content, re.MULTILINE | re.DOTALL)
    if not exec_match:
        return content
    
    exec_content = exec_match.group(0)
    exec_words = set(re.findall(r'\b\w{5,}\b', exec_content.lower()))
    
    # Check if it overlaps 90%+ with rest of document
    rest_content = content[exec_match.end():]
    rest_words = set(re.findall(r'\b\w{5,}\b', rest_content.lower()))
    
    if exec_words and rest_words:
        overlap = len(exec_words.intersection(rest_words)) / len(exec_words) * 100
        if overlap > 90:
            # Executive Summary is redundant - remove it
            content = content[:exec_match.start()] + content[exec_match.end():]
    
    return content

def process_doc(doc_path):
    """Process a document."""
    try:
        content = doc_path.read_text(encoding='utf-8')
        original_len = len(content)
        
        # Remove duplicate sections
        content = remove_duplicate_sections(content)
        
        # Remove redundant Executive Summary
        content = remove_exec_summary_if_duplicate(content)
        
        # Clean up
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        new_len = len(content)
        reduction = original_len - new_len
        
        if reduction > 50:
            doc_path.write_text(content, encoding='utf-8')
            return reduction, original_len
        
        return 0, original_len
    except Exception as e:
        print(f"ERROR: {doc_path.name}: {e}")
        return 0, 0

def main():
    """Process all documents."""
    print("="*80)
    print("REMOVING ALL REDUNDANT SECTIONS")
    print("="*80)
    print()
    
    docs = list(findings_dir.glob('*.md'))
    docs.remove(findings_dir / 'README.md')
    
    total_reduction = 0
    
    for doc in sorted(docs):
        reduction, original = process_doc(doc)
        if reduction > 0:
            pct = (reduction / original) * 100
            print(f"✅ {doc.name}: {reduction:,} chars ({pct:.1f}%)")
            total_reduction += reduction
    
    print()
    print(f"Total: {total_reduction:,} chars removed")
    print("="*80)

if __name__ == '__main__':
    main()
