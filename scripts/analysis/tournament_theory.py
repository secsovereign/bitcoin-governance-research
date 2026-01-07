#!/usr/bin/env python3
"""
Tournament Theory Analysis

Framework: Hierarchical rewards create winner-take-all competition
Application: Track contributor trajectories - steep cliff between "almost maintainer" and "maintainer"?
Expected insight: Tournament structure = exhaustion filter is feature, not bug
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict, Counter

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger
from src.utils.paths import get_analysis_dir, get_data_dir

logger = setup_logger()


class TournamentTheoryAnalyzer:
    """Analyzer for tournament structure in contributor hierarchy."""
    
    def __init__(self):
        self.data_dir = get_data_dir()
        self.analysis_dir = get_analysis_dir()
        self.processed_dir = self.data_dir / 'processed'
        self.output_dir = self.analysis_dir / 'tournament_theory'
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def run_analysis(self):
        """Run tournament theory analysis."""
        logger.info("=" * 60)
        logger.info("Tournament Theory Analysis")
        logger.info("=" * 60)
        
        prs = self._load_enriched_prs()
        if not prs:
            logger.error("No PR data found")
            return
        
        logger.info(f"Loaded {len(prs)} PRs")
        
        # Analyze contributor trajectories
        trajectories = self._analyze_trajectories(prs)
        
        # Analyze winner-take-all structure
        winner_take_all = self._analyze_winner_take_all(prs)
        
        # Analyze exhaustion filter
        exhaustion_filter = self._analyze_exhaustion_filter(prs)
        
        # Save results
        results = {
            'analysis_name': 'tournament_theory',
            'version': '1.0',
            'metadata': {
                'total_prs': len(prs)
            },
            'data': {
                'trajectories': trajectories,
                'winner_take_all': winner_take_all,
                'exhaustion_filter': exhaustion_filter
            }
        }
        
        output_file = self.output_dir / 'tournament_theory.json'
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Results saved to {output_file}")
        logger.info("Tournament theory analysis complete")
    
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
    
    def _analyze_trajectories(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze contributor trajectories toward maintainer status."""
        author_stats = defaultdict(lambda: {
            'prs': [],
            'merged': 0,
            'total_contributions': 0,
            'first_pr_year': None,
            'last_pr_year': None
        })
        
        for pr in prs:
            author = pr.get('author') or pr.get('user', {}).get('login', '')
            if not author:
                continue
            
            created_at = pr.get('created_at', '')
            if created_at:
                try:
                    year = int(created_at[:4])
                    if author_stats[author]['first_pr_year'] is None or year < author_stats[author]['first_pr_year']:
                        author_stats[author]['first_pr_year'] = year
                    if author_stats[author]['last_pr_year'] is None or year > author_stats[author]['last_pr_year']:
                        author_stats[author]['last_pr_year'] = year
                except:
                    pass
            
            author_stats[author]['prs'].append(pr)
            author_stats[author]['total_contributions'] += 1
            
            if pr.get('merged', False):
                author_stats[author]['merged'] += 1
        
        # Categorize contributors by trajectory
        tiers = {
            'maintainer': [],
            'almost_maintainer': [],  # High contribution, high merge rate
            'active_contributor': [],  # Moderate contribution
            'casual_contributor': []  # Low contribution
        }
        
        for author, stats in author_stats.items():
            maintainer_involvement = None
            for pr in stats['prs']:
                maintainer_involvement = pr.get('maintainer_involvement', {})
                if maintainer_involvement.get('author_is_maintainer', False):
                    break
            
            is_maintainer = maintainer_involvement and maintainer_involvement.get('author_is_maintainer', False)
            merge_rate = stats['merged'] / stats['total_contributions'] if stats['total_contributions'] > 0 else 0
            
            if is_maintainer:
                tiers['maintainer'].append({
                    'author': author,
                    'contributions': stats['total_contributions'],
                    'merge_rate': merge_rate
                })
            elif stats['total_contributions'] >= 20 and merge_rate >= 0.7:
                tiers['almost_maintainer'].append({
                    'author': author,
                    'contributions': stats['total_contributions'],
                    'merge_rate': merge_rate
                })
            elif stats['total_contributions'] >= 5:
                tiers['active_contributor'].append({
                    'author': author,
                    'contributions': stats['total_contributions'],
                    'merge_rate': merge_rate
                })
            else:
                tiers['casual_contributor'].append({
                    'author': author,
                    'contributions': stats['total_contributions'],
                    'merge_rate': merge_rate
                })
        
        # Calculate cliff between tiers
        maintainer_avg = sum(t['contributions'] for t in tiers['maintainer']) / len(tiers['maintainer']) if tiers['maintainer'] else 0
        almost_maintainer_avg = sum(t['contributions'] for t in tiers['almost_maintainer']) / len(tiers['almost_maintainer']) if tiers['almost_maintainer'] else 0
        
        return {
            'tiers': {k: len(v) for k, v in tiers.items()},
            'maintainer_avg_contributions': maintainer_avg,
            'almost_maintainer_avg_contributions': almost_maintainer_avg,
            'cliff_ratio': maintainer_avg / almost_maintainer_avg if almost_maintainer_avg > 0 else None,
            'interpretation': 'Higher cliff ratio = steeper barrier to maintainer status'
        }
    
    def _analyze_winner_take_all(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze winner-take-all structure."""
        author_contributions = Counter()
        
        for pr in prs:
            author = pr.get('author') or pr.get('user', {}).get('login', '')
            if author:
                author_contributions[author] += 1
        
        if not author_contributions:
            return {}
        
        total_contributions = sum(author_contributions.values())
        sorted_authors = author_contributions.most_common()
        
        # Calculate concentration
        top_10_share = sum(count for _, count in sorted_authors[:10]) / total_contributions
        top_5_share = sum(count for _, count in sorted_authors[:5]) / total_contributions
        top_1_share = sorted_authors[0][1] / total_contributions if sorted_authors else 0
        
        return {
            'top_1_share': top_1_share,
            'top_5_share': top_5_share,
            'top_10_share': top_10_share,
            'total_contributors': len(author_contributions),
            'interpretation': 'Higher shares = more winner-take-all structure'
        }
    
    def _analyze_exhaustion_filter(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze exhaustion filter - who gives up before reaching maintainer status."""
        author_journeys = defaultdict(lambda: {
            'prs': [],
            'merged': 0,
            'rejected': 0,
            'abandoned': 0
        })
        
        for pr in prs:
            author = pr.get('author') or pr.get('user', {}).get('login', '')
            if not author:
                continue
            
            author_journeys[author]['prs'].append(pr)
            
            if pr.get('merged', False):
                author_journeys[author]['merged'] += 1
            elif pr.get('state', '').lower() == 'closed':
                author_journeys[author]['rejected'] += 1
            else:
                author_journeys[author]['abandoned'] += 1
        
        # Analyze who exits
        exited_before_maintainer = 0
        reached_maintainer = 0
        
        for author, journey in author_journeys.items():
            # Check if became maintainer
            is_maintainer = False
            for pr in journey['prs']:
                maintainer_involvement = pr.get('maintainer_involvement', {})
                if maintainer_involvement.get('author_is_maintainer', False):
                    is_maintainer = True
                    break
            
            if is_maintainer:
                reached_maintainer += 1
            elif journey['merged'] >= 10:  # High contribution but not maintainer
                exited_before_maintainer += 1
        
        return {
            'exited_before_maintainer': exited_before_maintainer,
            'reached_maintainer': reached_maintainer,
            'exhaustion_rate': exited_before_maintainer / (exited_before_maintainer + reached_maintainer) if (exited_before_maintainer + reached_maintainer) > 0 else 0,
            'interpretation': 'Higher exhaustion rate = more filtering before maintainer status'
        }


def main():
    analyzer = TournamentTheoryAnalyzer()
    analyzer.run_analysis()


if __name__ == '__main__':
    main()

