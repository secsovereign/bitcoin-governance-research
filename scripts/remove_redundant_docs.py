#!/usr/bin/env python3
"""
Remove Redundant Documents from Publication Package

Removes documents that are redundant with main methodology/timeline documents.
"""

import shutil
from pathlib import Path

base_dir = Path(__file__).parent.parent
pub_dir = base_dir / 'publication-package'
findings_dir = pub_dir / 'findings'

# Documents to remove (redundant with main documents)
REDUNDANT_DOCS = [
    'REVIEW_COUNTING_METHODOLOGY.md',  # Covered in RESEARCH_METHODOLOGY.md Section 4.1
    'REVIEW_COVERAGE_INVESTIGATION.md',  # Covered in RESEARCH_METHODOLOGY.md Section 6.1
    'LIMITATIONS_AND_IMPROVEMENTS.md',  # Covered in RESEARCH_METHODOLOGY.md Section 6
    'CURRENT_VS_HISTORICAL_MAINTAINERS.md',  # Covered in MAINTAINER_TIMELINE_ANALYSIS.md
]

def main():
    """Remove redundant documents."""
    print("="*80)
    print("REMOVING REDUNDANT DOCUMENTS")
    print("="*80)
    print()
    
    removed = []
    not_found = []
    
    for doc in REDUNDANT_DOCS:
        doc_path = findings_dir / doc
        if doc_path.exists():
            doc_path.unlink()
            removed.append(doc)
            print(f"✅ Removed: {doc}")
        else:
            not_found.append(doc)
            print(f"⚠️  Not found: {doc}")
    
    print()
    print(f"Removed {len(removed)} redundant documents")
    if not_found:
        print(f"Warning: {len(not_found)} documents not found")
    
    # Update README to remove references
    readme_path = findings_dir / 'README.md'
    if readme_path.exists():
        content = readme_path.read_text(encoding='utf-8')
        
        # Remove lines referencing removed documents
        lines = content.split('\n')
        new_lines = []
        skip_next = False
        
        for i, line in enumerate(lines):
            # Skip lines that reference removed docs
            if any(doc.replace('.md', '') in line for doc in removed):
                # Skip this line and next few if it's a list item
                if line.strip().startswith('-') or line.strip().startswith('*'):
                    continue
                skip_next = True
                continue
            
            if skip_next and (line.strip() == '' or not line.strip().startswith(' ')):
                skip_next = False
            
            if not skip_next:
                new_lines.append(line)
        
        readme_path.write_text('\n'.join(new_lines), encoding='utf-8')
        print(f"✅ Updated README.md to remove references")
    
    print()
    print("="*80)
    print("REDUNDANT DOCUMENTS REMOVED")
    print("="*80)

if __name__ == '__main__':
    main()
