#!/usr/bin/env python3
"""
Survivorship Bias Analysis

Framework: We only see those who succeeded, not who was filtered out
Application: Analyze closed/abandoned PRs by author type - who leaves after rejection?
Expected insight: High-quality contributors with low institutional backing exit early
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict, Counter

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger
from src.utils.paths import get_analysis_dir, get_data_dir

logger = setup_logger()


class SurvivorshipBiasAnalyzer:
    """Analyzer for survivorship bias in contributor retention."""
    
    def __init__(self):
        self.data_dir = get_data_dir()
        self.analysis_dir = get_analysis_dir()
        self.processed_dir = self.data_dir / 'processed'
        self.output_dir = self.analysis_dir / 'survivorship_bias'
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def run_analysis(self):
        """Run survivorship bias analysis."""
        logger.info("=" * 60)
        logger.info("Survivorship Bias Analysis")
        logger.info("=" * 60)
        
        prs = self._load_enriched_prs()
        if not prs:
            logger.error("No PR data found")
            return
        
        logger.info(f"Loaded {len(prs)} PRs")
        
        # Analyze who gets filtered out
        filtering_analysis = self._analyze_filtering(prs)
        
        # Analyze contributor trajectories
        trajectory_analysis = self._analyze_contributor_trajectories(prs)
        
        # Analyze abandonment patterns
        abandonment_analysis = self._analyze_abandonment(prs)
        
        # Analyze quality vs. retention
        quality_retention = self._analyze_quality_retention(prs)
        
        # Save results
        results = {
            'analysis_name': 'survivorship_bias',
            'version': '1.0',
            'metadata': {
                'total_prs': len(prs)
            },
            'data': {
                'filtering_analysis': filtering_analysis,
                'trajectory_analysis': trajectory_analysis,
                'abandonment_analysis': abandonment_analysis,
                'quality_retention': quality_retention
            }
        }
        
        output_file = self.output_dir / 'survivorship_bias.json'
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Results saved to {output_file}")
        logger.info("Survivorship bias analysis complete")
    
    def _load_enriched_prs(self) -> List[Dict[str, Any]]:
        """Load enriched PR data."""
        prs_file = self.processed_dir / 'enriched_prs.jsonl'
        if not prs_file.exists():
            prs_file = self.processed_dir / 'cleaned_prs.jsonl'
        
        if not prs_file.exists():
            logger.warning(f"PR data not found: {prs_file}")
            return []
        
        prs = []
        with open(prs_file, 'r') as f:
            for line in f:
                try:
                    prs.append(json.loads(line))
                except:
                    continue
        
        return prs
    
    def _analyze_filtering(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze who gets filtered out vs. who succeeds."""
        maintainer_prs = {'merged': 0, 'closed': 0, 'open': 0}
        non_maintainer_prs = {'merged': 0, 'closed': 0, 'open': 0}
        
        maintainer_authors = set()
        non_maintainer_authors = set()
        
        for pr in prs:
            maintainer_involvement = pr.get('maintainer_involvement', {})
            is_maintainer = maintainer_involvement.get('author_is_maintainer', False)
            author = pr.get('author') or pr.get('user', {}).get('login', '')
            
            state = pr.get('state', '').lower()
            merged = pr.get('merged', False)
            
            if merged:
                status = 'merged'
            elif state == 'closed':
                status = 'closed'
            else:
                status = 'open'
            
            if is_maintainer:
                maintainer_prs[status] += 1
                if author:
                    maintainer_authors.add(author)
            else:
                non_maintainer_prs[status] += 1
                if author:
                    non_maintainer_authors.add(author)
        
        maintainer_total = sum(maintainer_prs.values())
        non_maintainer_total = sum(non_maintainer_prs.values())
        
        return {
            'maintainer_prs': maintainer_prs,
            'non_maintainer_prs': non_maintainer_prs,
            'maintainer_merge_rate': maintainer_prs['merged'] / maintainer_total if maintainer_total > 0 else 0,
            'non_maintainer_merge_rate': non_maintainer_prs['merged'] / non_maintainer_total if non_maintainer_total > 0 else 0,
            'maintainer_closure_rate': maintainer_prs['closed'] / maintainer_total if maintainer_total > 0 else 0,
            'non_maintainer_closure_rate': non_maintainer_prs['closed'] / non_maintainer_total if non_maintainer_total > 0 else 0,
            'unique_maintainer_authors': len(maintainer_authors),
            'unique_non_maintainer_authors': len(non_maintainer_authors),
            'interpretation': 'Higher closure rate for non-maintainers = more filtering'
        }
    
    def _analyze_contributor_trajectories(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze contributor trajectories - who continues vs. who exits."""
        author_trajectories = defaultdict(list)
        
        for pr in prs:
            author = pr.get('author') or pr.get('user', {}).get('login', '')
            if not author:
                continue
            
            created_at = pr.get('created_at', '')
            if not created_at:
                continue
            
            try:
                year = int(created_at[:4])
                author_trajectories[author].append({
                    'year': year,
                    'merged': pr.get('merged', False),
                    'state': pr.get('state', '')
                })
            except:
                continue
        
        # Analyze trajectories
        one_time_contributors = 0
        persistent_contributors = 0
        exited_contributors = 0
        
        for author, prs_list in author_trajectories.items():
            if len(prs_list) == 1:
                one_time_contributors += 1
            elif len(prs_list) > 1:
                persistent_contributors += 1
                # Check if they exited (no recent PRs)
                years = sorted([p['year'] for p in prs_list])
                if years[-1] < 2020:  # No PRs in last 4 years
                    exited_contributors += 1
        
        return {
            'one_time_contributors': one_time_contributors,
            'persistent_contributors': persistent_contributors,
            'exited_contributors': exited_contributors,
            'exit_rate': exited_contributors / persistent_contributors if persistent_contributors > 0 else 0
        }
    
    def _analyze_abandonment(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze PR abandonment patterns."""
        maintainer_abandoned = 0
        non_maintainer_abandoned = 0
        maintainer_total = 0
        non_maintainer_total = 0
        
        for pr in prs:
            maintainer_involvement = pr.get('maintainer_involvement', {})
            is_maintainer = maintainer_involvement.get('author_is_maintainer', False)
            
            state = pr.get('state', '').lower()
            merged = pr.get('merged', False)
            
            # Abandoned = closed but not merged, and no recent activity
            if state == 'closed' and not merged:
                if is_maintainer:
                    maintainer_total += 1
                    # Check if abandoned (no recent comments)
                    comments = pr.get('comments', [])
                    if not comments or len(comments) == 0:
                        maintainer_abandoned += 1
                else:
                    non_maintainer_total += 1
                    comments = pr.get('comments', [])
                    if not comments or len(comments) == 0:
                        non_maintainer_abandoned += 1
        
        return {
            'maintainer_abandonment_rate': maintainer_abandoned / maintainer_total if maintainer_total > 0 else 0,
            'non_maintainer_abandonment_rate': non_maintainer_abandoned / non_maintainer_total if non_maintainer_total > 0 else 0,
            'abandonment_ratio': (non_maintainer_abandoned / non_maintainer_total) / (maintainer_abandoned / maintainer_total) if maintainer_total > 0 and maintainer_abandoned > 0 else None
        }
    
    def _analyze_quality_retention(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze relationship between PR quality and contributor retention."""
        # Simple quality proxy: PR size and review count
        author_quality = defaultdict(list)
        
        for pr in prs:
            author = pr.get('author') or pr.get('user', {}).get('login', '')
            if not author:
                continue
            
            # Quality indicators
            additions = pr.get('additions', 0)
            deletions = pr.get('deletions', 0)
            reviews = len(pr.get('reviews', []))
            merged = pr.get('merged', False)
            
            quality_score = (additions + deletions) * 0.5 + reviews * 10  # Simple proxy
            
            author_quality[author].append({
                'quality_score': quality_score,
                'merged': merged,
                'pr_count': 1
            })
        
        # Analyze retention by quality
        high_quality_exited = 0
        low_quality_exited = 0
        high_quality_persisted = 0
        low_quality_persisted = 0
        
        for author, prs_list in author_quality.items():
            if len(prs_list) == 1:
                # One-time contributor
                avg_quality = prs_list[0]['quality_score']
                if avg_quality > 100:  # Threshold
                    high_quality_exited += 1
                else:
                    low_quality_exited += 1
            else:
                # Persistent contributor
                avg_quality = sum(p['quality_score'] for p in prs_list) / len(prs_list)
                if avg_quality > 100:
                    high_quality_persisted += 1
                else:
                    low_quality_persisted += 1
        
        return {
            'high_quality_exited': high_quality_exited,
            'low_quality_exited': low_quality_exited,
            'high_quality_persisted': high_quality_persisted,
            'low_quality_persisted': low_quality_persisted,
            'high_quality_exit_rate': high_quality_exited / (high_quality_exited + high_quality_persisted) if (high_quality_exited + high_quality_persisted) > 0 else 0
        }


def main():
    analyzer = SurvivorshipBiasAnalyzer()
    analyzer.run_analysis()


if __name__ == '__main__':
    main()

