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
        """Collect MAINTAINERS file history."""
        logger.info("Starting MAINTAINERS file history collection")
        
        try:
            # Clone repository to temp directory
            self.temp_dir = tempfile.mkdtemp(prefix="bitcoin_maintainers_")
            logger.info(f"Cloning repository to {self.temp_dir}")
            
            # Clone repository with full history (needed for MAINTAINERS file history)
            logger.info("Cloning repository with full history (this may take a few minutes)...")
            subprocess.run(
                ["git", "clone", self.repo_url, self.temp_dir],
                check=True,
                capture_output=True,
                timeout=600  # 10 minute timeout
            )
            
            # Get full history of MAINTAINERS file
            logger.info("Getting MAINTAINERS file history")
            result = subprocess.run(
                ["git", "log", "--all", "--full-history", "--pretty=format:%H|%ai|%an|%ae", "--", "MAINTAINERS"],
                cwd=self.temp_dir,
                capture_output=True,
                text=True,
                check=True
            )
            
            commits = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                parts = line.split('|', 3)
                if len(parts) >= 3:
                    commits.append({
                        'hash': parts[0],
                        'date': parts[1],
                        'author_name': parts[2],
                        'author_email': parts[3] if len(parts) > 3 else ''
                    })
            
            logger.info(f"Found {len(commits)} commits that modified MAINTAINERS")
            
            # Get MAINTAINERS file content for each commit
            maintainers_history = []
            for i, commit in enumerate(commits):
                try:
                    # Get file content at this commit
                    result = subprocess.run(
                        ["git", "show", f"{commit['hash']}:MAINTAINERS"],
                        cwd=self.temp_dir,
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    
                    maintainers_content = result.stdout
                    maintainers_list = self._parse_maintainers_file(maintainers_content)
                    
                    maintainers_history.append({
                        'commit_hash': commit['hash'],
                        'date': commit['date'],
                        'author_name': commit['author_name'],
                        'author_email': commit['author_email'],
                        'maintainers': maintainers_list,
                        'maintainer_count': len(maintainers_list)
                    })
                    
                    if (i + 1) % 50 == 0:
                        logger.info(f"Processed {i+1}/{len(commits)} MAINTAINERS file versions")
                        
                except subprocess.CalledProcessError as e:
                    logger.warning(f"Error getting MAINTAINERS for commit {commit['hash']}: {e}")
                    continue
            
            # Save history
            output_file = self.data_dir / "maintainers_history.jsonl"
            with open(output_file, 'w') as f:
                for entry in maintainers_history:
                    f.write(json.dumps(entry) + '\n')
            
            logger.info(f"Saved {len(maintainers_history)} MAINTAINERS file versions to {output_file}")
            
            # Generate summary
            self._generate_summary(maintainers_history)
            
        except Exception as e:
            logger.error(f"Error collecting MAINTAINERS history: {e}")
            import traceback
            logger.debug(traceback.format_exc())
        finally:
            # Clean up temp directory
            if self.temp_dir and os.path.exists(self.temp_dir):
                logger.info(f"Cleaning up temp directory: {self.temp_dir}")
                shutil.rmtree(self.temp_dir)
    
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

