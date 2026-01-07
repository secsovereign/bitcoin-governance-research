#!/usr/bin/env python3
"""
Utility to load PRs with merged_by data from separate mapping file.

This allows analysis scripts to use merged_by data without modifying
the original dataset.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional


def load_prs_with_merged_by(
    prs_file: Path,
    mapping_file: Optional[Path] = None
) -> List[Dict[str, Any]]:
    """
    Load PRs and optionally merge in merged_by data from mapping file.
    
    Args:
        prs_file: Path to main PR dataset (prs_raw.jsonl)
        mapping_file: Optional path to merged_by mapping file
    
    Returns:
        List of PR dicts with merged_by data if mapping file provided
    """
    # Load PRs
    prs = []
    with open(prs_file) as f:
        for line in f:
            if line.strip():
                prs.append(json.loads(line))
    
    # Load mapping if provided
    if mapping_file and mapping_file.exists():
        mapping = {}
        with open(mapping_file) as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    mapping[data['pr_number']] = {
                        'merged_by': data.get('merged_by'),
                        'merged_by_id': data.get('merged_by_id')
                    }
        
        # Merge mapping into PRs
        for pr in prs:
            pr_number = pr.get('number')
            if pr_number in mapping:
                pr.update(mapping[pr_number])
    
    return prs


def get_merged_by_for_pr(pr_number: int, mapping_file: Path) -> Optional[Dict[str, Any]]:
    """Get merged_by data for a specific PR from mapping file."""
    if not mapping_file.exists():
        return None
    
    with open(mapping_file) as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                if data.get('pr_number') == pr_number:
                    return {
                        'merged_by': data.get('merged_by'),
                        'merged_by_id': data.get('merged_by_id')
                    }
    return None


# Example usage
if __name__ == '__main__':
    import sys
    
    prs_file = Path('data/github/prs_raw.jsonl')
    mapping_file = Path('data/github/merged_by_mapping.jsonl')
    
    if len(sys.argv) > 1:
        prs_file = Path(sys.argv[1])
    if len(sys.argv) > 2:
        mapping_file = Path(sys.argv[2])
    
    print(f"Loading PRs from {prs_file}...")
    prs = load_prs_with_merged_by(prs_file, mapping_file if mapping_file.exists() else None)
    
    print(f"Loaded {len(prs):,} PRs")
    
    merged = [p for p in prs if p.get('merged', False)]
    with_merged_by = [p for p in merged if p.get('merged_by')]
    
    print(f"Merged PRs: {len(merged):,}")
    print(f"With merged_by: {len(with_merged_by):,} ({len(with_merged_by)/len(merged)*100:.1f}%)" if merged else "N/A")
