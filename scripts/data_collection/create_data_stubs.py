#!/usr/bin/env python3
"""
Create Data Stubs

Creates sample/stub files from large datasets to show structure
without including full data in distribution.
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def create_stub(input_file: Path, output_file: Path, sample_size: int = 10):
    """Create a stub file with sample records."""
    if not input_file.exists():
        print(f"Warning: {input_file} does not exist")
        return False
    
    print(f"Creating stub: {input_file.name} -> {output_file.name}")
    
    records = []
    with open(input_file, 'r') as f:
        for i, line in enumerate(f):
            if i >= sample_size:
                break
            if line.strip():
                try:
                    records.append(json.loads(line))
                except:
                    pass
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w') as f:
        for record in records:
            f.write(json.dumps(record) + '\n')
    
    print(f"  Created {len(records)} sample records")
    return True


def main():
    """Create data stubs."""
    data_dir = Path(__file__).parent.parent.parent / 'data' / 'github'
    stubs_dir = data_dir / 'samples'
    
    stubs_dir.mkdir(parents=True, exist_ok=True)
    
    files_to_stub = [
        ('prs_raw.jsonl', 'prs_raw_sample.jsonl', 10),
        ('issues_raw.jsonl', 'issues_raw_sample.jsonl', 10),
        ('commits_raw.jsonl', 'commits_raw_sample.jsonl', 10),
        ('merged_by_mapping.jsonl', 'merged_by_mapping_sample.jsonl', 20),
    ]
    
    print("="*80)
    print("CREATING DATA STUBS")
    print("="*80)
    print()
    
    created = 0
    for input_name, output_name, sample_size in files_to_stub:
        input_file = data_dir / input_name
        output_file = stubs_dir / output_name
        
        if create_stub(input_file, output_file, sample_size):
            created += 1
    
    print()
    print(f"Created {created} stub files in {stubs_dir}")
    print()
    print("Stub files show data structure without including full datasets.")
    print("Useful for understanding data format and for documentation.")


if __name__ == '__main__':
    main()
