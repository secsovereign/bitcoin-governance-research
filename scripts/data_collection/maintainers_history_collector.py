#!/usr/bin/env python3
"""
MAINTAINERS file history collector for Bitcoin Core repository.

Tracks maintainer status changes over time by analyzing git history
of the MAINTAINERS file.
"""

import sys
import os
import json
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import re

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config import config
from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir

logger = setup_logger()


class MaintainersHistoryCollector:
    """Collector for MAINTAINERS file history."""
    
    def __init__(self):
        """Initialize maintainers history collector."""
        self.repo_url = "https://github.com/bitcoin/bitcoin.git"
        self.data_dir = get_data_dir() / "maintainers"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir = None
        
    def collect(self):
        """Collect MAINTAINERS file history.

        Bitcoin Core does **not** maintain an in-tree MAINTAINERS file.
        Cloning the full repo solely for this purpose is wasteful and yields
        an empty history. Prefer merge-inferred timeline construction.
        """
        logger.info("Starting MAINTAINERS file history collection")
        logger.warning(
            "bitcoin/bitcoin has no MAINTAINERS file. Skipping git clone; "
            "delegating to maintainer_timeline.py (canonical list + merged_by)."
        )
        from scripts.data_processing.maintainer_timeline import MaintainerTimelineTracker

        MaintainerTimelineTracker().build_timeline()
        # Keep an explicit empty history artifact so callers know the file DNE
        history_path = self.data_dir / "maintainers_history.jsonl"
        if not history_path.exists() or history_path.stat().st_size == 0:
            note = {
                "note": "No MAINTAINERS file in bitcoin/bitcoin",
                "date": datetime.now().isoformat(),
                "maintainers": [],
                "maintainer_count": 0,
                "delegated_to": "scripts/data_processing/maintainer_timeline.py",
            }
            history_path.write_text(json.dumps(note) + "\n", encoding="utf-8")
        logger.info("MAINTAINERS history collection complete (delegated)")
        return
    
    def _parse_maintainers_file(self, content: str) -> List[Dict[str, Any]]:
        """Parse MAINTAINERS file content to extract maintainer information."""
        maintainers = []
        
        # MAINTAINERS file format varies, but typically has sections like:
        # # Maintainers
        # Name <email>
        # or
        # Name (GitHub username)
        
        lines = content.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                if 'maintainer' in line.lower():
                    current_section = 'maintainers'
                continue
            
            # Try to parse maintainer line
            # Format: Name <email> or Name (username) or Name <email> (username)
            maintainer_match = re.match(
                r'^(.+?)(?:\s*<([^>]+)>)?(?:\s*\(([^)]+)\))?$',
                line
            )
            
            if maintainer_match:
                name = maintainer_match.group(1).strip()
                email = maintainer_match.group(2) if maintainer_match.group(2) else None
                username = maintainer_match.group(3) if maintainer_match.group(3) else None
                
                # Clean up name (remove extra whitespace)
                name = ' '.join(name.split())
                
                if name and (email or username):
                    maintainers.append({
                        'name': name,
                        'email': email,
                        'username': username,
                        'line': line
                    })
        
        return maintainers
    
    def _generate_summary(self, history: List[Dict[str, Any]]):
        """Generate summary statistics."""
        summary = {
            'total_versions': len(history),
            'unique_maintainers': set(),
            'maintainer_changes': [],
            'timeline': []
        }
        
        # Track maintainer additions/removals
        previous_maintainers = set()
        
        for entry in sorted(history, key=lambda x: x['date']):
            current_maintainers = {m['name'] for m in entry['maintainers']}
            summary['unique_maintainers'].update(current_maintainers)
            
            # Find changes
            added = current_maintainers - previous_maintainers
            removed = previous_maintainers - current_maintainers
            
            if added or removed:
                summary['maintainer_changes'].append({
                    'date': entry['date'],
                    'commit': entry['commit_hash'],
                    'author': entry['author_name'],
                    'added': list(added),
                    'removed': list(removed),
                    'total_count': entry['maintainer_count']
                })
            
            summary['timeline'].append({
                'date': entry['date'],
                'count': entry['maintainer_count'],
                'maintainers': [m['name'] for m in entry['maintainers']]
            })
            
            previous_maintainers = current_maintainers
        
        summary['unique_maintainers'] = list(summary['unique_maintainers'])
        
        # Save summary
        summary_file = self.data_dir / "maintainers_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Summary: {len(summary['unique_maintainers'])} unique maintainers, "
                   f"{len(summary['maintainer_changes'])} status changes")


def main():
    """Main entry point."""
    collector = MaintainersHistoryCollector()
    collector.collect()


if __name__ == '__main__':
    main()

