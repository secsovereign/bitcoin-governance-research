#!/usr/bin/env python3
"""
Export Network Data for Visualization

Exports merge and review relationships as graph data for visualization.
"""

import json
import sys
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.utils.load_prs_with_merged_by import load_prs_with_merged_by

def export_network_data(data_dir: Path):
    """Export network data for visualization."""
    print("="*80)
    print("EXPORTING NETWORK DATA")
    print("="*80)
    print()
    
    prs_file = data_dir / 'github' / 'prs_raw.jsonl'
    mapping_file = data_dir / 'github' / 'merged_by_mapping.jsonl'
    prs = load_prs_with_merged_by(prs_file, mapping_file if mapping_file.exists() else None)
    
    print(f"Loaded {len(prs):,} PRs")
    print()
    
    # Build networks
    merge_edges = Counter()  # (merger, author) -> count
    review_edges = Counter()  # (reviewer, author) -> count
    nodes = set()
    
    for pr in prs:
        if not pr.get('merged', False):
            continue
        
        author = (pr.get('author') or '').lower()
        merged_by = (pr.get('merged_by') or '').lower()
        
        if author and merged_by:
            nodes.add(author)
            nodes.add(merged_by)
            merge_edges[(merged_by, author)] += 1
        
        # Review relationships
        reviews = pr.get('reviews', [])
        for review in reviews:
            reviewer = (review.get('author') or '').lower()
            if reviewer and author:
                nodes.add(reviewer)
                nodes.add(author)
                review_edges[(reviewer, author)] += 1
    
    # Export as JSON (can be imported into network visualization tools)
    network_data = {
        'nodes': [{'id': node, 'label': node} for node in sorted(nodes)],
        'merge_edges': [
            {'source': src, 'target': tgt, 'weight': count}
            for (src, tgt), count in merge_edges.most_common(100)  # Top 100 relationships
        ],
        'review_edges': [
            {'source': src, 'target': tgt, 'weight': count}
            for (src, tgt), count in review_edges.most_common(200)  # Top 200 relationships
        ],
        'stats': {
            'total_nodes': len(nodes),
            'total_merge_edges': len(merge_edges),
            'total_review_edges': len(review_edges)
        }
    }
    
    # Save
    output_file = data_dir.parent / 'findings' / 'network_data.json'
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(network_data, f, indent=2)
    
    print(f"Exported network data:")
    print(f"  Nodes: {len(nodes):,}")
    print(f"  Merge edges: {len(merge_edges):,} (top 100 exported)")
    print(f"  Review edges: {len(review_edges):,} (top 200 exported)")
    print()
    print(f"Saved to: {output_file}")
    print()
    print("Can be imported into:")
    print("  - Gephi (network visualization)")
    print("  - Cytoscape (network analysis)")
    print("  - D3.js (web visualization)")
    print("  - NetworkX (Python analysis)")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Export network data')
    parser.add_argument('--data-dir', type=Path, default=Path(__file__).parent.parent.parent / 'data',
                       help='Data directory')
    
    args = parser.parse_args()
    export_network_data(args.data_dir)
