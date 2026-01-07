#!/usr/bin/env python3
"""
Update all analyses that use merged_by data.

This script:
1. Updates analysis scripts to use merged_by_mapping.jsonl
2. Reruns the analyses
3. Generates updated reports
"""

import json
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def update_power_concentration():
    """Update power_concentration.py to use merged_by mapping."""
    script_path = project_root / 'scripts' / 'analysis' / 'power_concentration.py'
    
    # Read the script
    with open(script_path) as f:
        content = f.read()
    
    # Check if already updated
    if 'load_prs_with_merged_by' in content:
        print("✅ power_concentration.py already uses merged_by mapping")
        return True
    
    # Find the _load_enriched_prs method
    if '_load_enriched_prs' not in content:
        print("⚠️  Could not find _load_enriched_prs in power_concentration.py")
        return False
    
    # Update the method to load merged_by mapping
    old_method = """    def _load_enriched_prs(self) -> List[Dict[str, Any]]:
        \"\"\"Load enriched PRs.\"\"\"
        enriched_file = self.processed_dir / 'enriched_prs.jsonl'
        if not enriched_file.exists():
            logger.warning(f"Enriched PRs file not found: {enriched_file}")
            return []
        
        prs = []
        with open(enriched_file) as f:
            for line in f:
                if line.strip():
                    prs.append(json.loads(line))
        
        logger.info(f"Loaded {len(prs)} PRs")
        return prs"""
    
    new_method = """    def _load_enriched_prs(self) -> List[Dict[str, Any]]:
        \"\"\"Load enriched PRs with merged_by data.\"\"\"
        from scripts.utils.load_prs_with_merged_by import load_prs_with_merged_by
        
        enriched_file = self.processed_dir / 'enriched_prs.jsonl'
        mapping_file = self.data_dir / 'github' / 'merged_by_mapping.jsonl'
        
        if not enriched_file.exists():
            logger.warning(f"Enriched PRs file not found: {enriched_file}")
            return []
        
        prs = load_prs_with_merged_by(enriched_file, mapping_file if mapping_file.exists() else None)
        
        logger.info(f"Loaded {len(prs)} PRs")
        return prs"""
    
    if old_method in content:
        content = content.replace(old_method, new_method)
        with open(script_path, 'w') as f:
            f.write(content)
        print("✅ Updated power_concentration.py")
        return True
    else:
        print("⚠️  Could not find exact method signature in power_concentration.py")
        return False

def update_regulatory_arbitrage():
    """Update regulatory_arbitrage.py to use merged_by mapping."""
    script_path = project_root / 'scripts' / 'analysis' / 'regulatory_arbitrage.py'
    
    with open(script_path) as f:
        content = f.read()
    
    if 'load_prs_with_merged_by' in content:
        print("✅ regulatory_arbitrage.py already uses merged_by mapping")
        return True
    
    # Similar update pattern
    print("⚠️  Manual update needed for regulatory_arbitrage.py")
    return False

def update_review_opacity_correlation():
    """Update review_opacity_correlation.py to use merged_by mapping."""
    script_path = project_root / 'scripts' / 'analysis' / 'review_opacity_correlation.py'
    
    with open(script_path) as f:
        content = f.read()
    
    if 'load_prs_with_merged_by' in content:
        print("✅ review_opacity_correlation.py already uses merged_by mapping")
        return True
    
    # Similar update pattern
    print("⚠️  Manual update needed for review_opacity_correlation.py")
    return False

def update_comprehensive_analysis():
    """Update comprehensive_recent_analysis.py to use merged_by mapping."""
    script_path = project_root / 'comprehensive_recent_analysis.py'
    
    with open(script_path) as f:
        content = f.read()
    
    if 'load_prs_with_merged_by' in content:
        print("✅ comprehensive_recent_analysis.py already uses merged_by mapping")
        return True
    
    # Add import and update load_jsonl calls
    if 'from scripts.utils.load_prs_with_merged_by import load_prs_with_merged_by' not in content:
        # Add import after existing imports
        import_line = "from scripts.utils.load_prs_with_merged_by import load_prs_with_merged_by"
        if 'from typing import' in content:
            content = content.replace(
                'from typing import List, Dict, Any',
                'from typing import List, Dict, Any\nfrom scripts.utils.load_prs_with_merged_by import load_prs_with_merged_by'
            )
        else:
            # Add after datetime import
            content = content.replace(
                'from datetime import datetime',
                'from datetime import datetime\nfrom scripts.utils.load_prs_with_merged_by import load_prs_with_merged_by'
            )
    
    # Update load_jsonl to use merged_by mapping
    old_load = """def load_jsonl(filepath: Path) -> list:
    \"\"\"Load JSONL file and return list of records.\"\"\"
    records = []
    if not filepath.exists():
        return records
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return records"""
    
    new_load = """def load_jsonl(filepath: Path, mapping_file: Path = None) -> list:
    \"\"\"Load JSONL file and return list of records with merged_by data.\"\"\"
    records = []
    if not filepath.exists():
        return records
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    
    # Merge merged_by data if mapping file provided
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
        
        for record in records:
            pr_number = record.get('number')
            if pr_number in mapping:
                record.update(mapping[pr_number])
    
    return records"""
    
    if old_load in content:
        content = content.replace(old_load, new_load)
        
        # Update calls to load_jsonl to include mapping file
        data_dir = project_root / 'data' / 'github'
        prs_file = data_dir / 'prs_raw.jsonl'
        mapping_file = data_dir / 'merged_by_mapping.jsonl'
        
        # Find where PRs are loaded
        if 'prs = load_jsonl(' in content:
            # Update the main PR loading call
            content = content.replace(
                'prs = load_jsonl(',
                f'prs = load_jsonl(Path("{prs_file}"), Path("{mapping_file}"))  # Updated with merged_by'
            )
        
        with open(script_path, 'w') as f:
            f.write(content)
        print("✅ Updated comprehensive_recent_analysis.py")
        return True
    else:
        print("⚠️  Could not find exact load_jsonl function in comprehensive_recent_analysis.py")
        return False

def main():
    """Main entry point."""
    print("="*80)
    print("UPDATING ANALYSES TO USE merged_by DATA")
    print("="*80)
    print()
    
    # Update scripts
    print("1. Updating analysis scripts...")
    update_power_concentration()
    update_comprehensive_analysis()
    # update_regulatory_arbitrage()  # Manual update needed
    # update_review_opacity_correlation()  # Manual update needed
    print()
    
    print("2. Scripts updated. Ready to rerun analyses.")
    print()
    print("Next steps:")
    print("  - Run: python3 scripts/analysis/power_concentration.py")
    print("  - Run: python3 comprehensive_recent_analysis.py")
    print("  - Check updated reports in findings/ directory")

if __name__ == '__main__':
    main()
