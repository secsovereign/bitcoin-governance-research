#!/usr/bin/env python3
"""
Luke Dashjr case study data collector.

Collects all communications related to Luke Dashjr's maintainer removal.
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config import config
from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir

logger = setup_logger()


class LukeCaseCollector:
    """Collector for Luke Dashjr case study data."""
    
    def __init__(self):
        """Initialize Luke case collector."""
        self.date_range = config.get('data_collection.luke_case.date_range', {})
        self.keywords = config.get('data_collection.luke_case.keywords', [])
        
        # Output paths
        data_dir = get_data_dir()
        self.output_dir = data_dir / 'luke_case'
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.communications_file = self.output_dir / 'communications.jsonl'
    
    def collect_case_data(self):
        """Collect all data related to the Luke Dashjr case."""
        logger.info("Starting Luke Dashjr case study data collection")
        
        # This will search GitHub PRs, issues, and mailing lists
        # for relevant communications
        
        # For now, this is a placeholder that will be implemented
        # to search through already-collected data
        
        logger.info("Luke Dashjr case study data collection complete")
    
    def search_github_data(self):
        """Search GitHub data for Luke-related communications."""
        data_dir = get_data_dir()
        github_data_dir = data_dir / 'github'
        prs_file = github_data_dir / 'prs_raw.jsonl'
        issues_file = github_data_dir / 'issues_raw.jsonl'
        
        relevant_items = []
        
        # Search PRs
        if prs_file.exists():
            logger.info(f"Searching PRs in {prs_file}")
            with open(prs_file, 'r') as f:
                for line in f:
                    pr = json.loads(line)
                    if self._is_relevant(pr):
                        relevant_items.append({
                            'type': 'pr',
                            'data': pr
                        })
        
        # Search issues
        if issues_file.exists():
            logger.info(f"Searching issues in {issues_file}")
            with open(issues_file, 'r') as f:
                for line in f:
                    issue = json.loads(line)
                    if self._is_relevant(issue):
                        relevant_items.append({
                            'type': 'issue',
                            'data': issue
                        })
        
        # Write results
        with open(self.communications_file, 'w') as f:
            for item in relevant_items:
                f.write(json.dumps(item) + '\n')
        
        logger.info(f"Found {len(relevant_items)} relevant communications")
    
    def _is_relevant(self, item: Dict[str, Any]) -> bool:
        """Check if an item is relevant to the Luke case."""
        # Check date range
        if self.date_range:
            start_date = datetime.fromisoformat(self.date_range.get('start', '2022-06-01'))
            end_date = datetime.fromisoformat(self.date_range.get('end', '2023-06-01'))
            
            item_date = None
            if 'created_at' in item:
                try:
                    item_date = datetime.fromisoformat(item['created_at'].replace('Z', '+00:00'))
                except:
                    pass
            
            if item_date:
                if item_date < start_date or item_date > end_date:
                    return False
        
        # Check keywords in title, body, and comments
        text_to_search = []
        if 'title' in item:
            text_to_search.append(item['title'].lower())
        if 'body' in item:
            text_to_search.append(item['body'].lower() if item['body'] else '')
        if 'comments' in item:
            for comment in item['comments']:
                if 'body' in comment:
                    text_to_search.append(comment['body'].lower())
        
        full_text = ' '.join(text_to_search)
        
        for keyword in self.keywords:
            if keyword.lower() in full_text:
                return True
        
        return False


def main():
    """Main entry point."""
    collector = LukeCaseCollector()
    collector.collect_case_data()
    collector.search_github_data()


if __name__ == '__main__':
    main()

