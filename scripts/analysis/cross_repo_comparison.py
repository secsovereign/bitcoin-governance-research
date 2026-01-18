#!/usr/bin/env python3
"""
Cross-Repository Comparison - Compare governance patterns between Bitcoin Core and BIPs repositories.

Analyzes:
1. Actor overlap analysis (who appears in both repositories)
2. Governance pattern comparison (merge authority, review patterns)
3. Power portability analysis (power in BIPs repo → power in Core repo)
4. Process comparison (BIP proposal vs Core implementation)
5. Governance transfer analysis (process improvements)
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, Counter
from datetime import datetime, timezone

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir, get_analysis_dir

logger = setup_logger()


class CrossRepoComparisonAnalyzer:
    """Analyzer for cross-repository governance comparison."""
    
    def __init__(self):
        """Initialize analyzer."""
        self.data_dir = get_data_dir()
        self.github_dir = self.data_dir / 'github'
        self.bips_dir = self.data_dir / 'bips'
        self.analysis_dir = get_analysis_dir()
        self.findings_dir = self.analysis_dir / 'findings' / 'data'
        self.findings_dir.mkdir(parents=True, exist_ok=True)
        
        # Maintainer list (Core repository)
        self.maintainers = {
            'laanwj', 'sipa', 'maflcko', 'fanquake', 'hebasto', 'jnewbery',
            'ryanofsky', 'achow101', 'theuni', 'jonasschnelli', 'Sjors',
            'promag', 'instagibbs', 'TheBlueMatt', 'jonatack', 'gmaxwell',
            'gavinandresen', 'petertodd', 'luke-jr', 'glozow'
        }
    
    def run_analysis(self):
        """Run cross-repository comparison analysis."""
        logger.info("=" * 60)
        logger.info("Cross-Repository Comparison Analysis")
        logger.info("=" * 60)
        
        # Load data
        core_prs = self._load_core_prs()
        bip_prs = self._load_bip_prs()
        bips = self._load_bips()
        
        logger.info(f"Loaded {len(core_prs)} Core PRs, {len(bip_prs)} BIP PRs, {len(bips)} BIPs")
        
        # Analyze actor overlap
        actor_overlap = self._analyze_actor_overlap(core_prs, bip_prs)
        
        # Compare governance patterns
        governance_comparison = self._compare_governance_patterns(core_prs, bip_prs)
        
        # Analyze power portability
        power_portability = self._analyze_power_portability(core_prs, bip_prs)
        
        # Compare processes
        process_comparison = self._compare_processes(core_prs, bip_prs, bips)
        
        # Analyze governance transfer
        governance_transfer = self._analyze_governance_transfer(core_prs, bip_prs)
        
        # Save results
        results = {
            'actor_overlap': actor_overlap,
            'governance_comparison': governance_comparison,
            'power_portability': power_portability,
            'process_comparison': process_comparison,
            'governance_transfer': governance_transfer,
            'statistics': self._generate_statistics(
                actor_overlap, governance_comparison, power_portability,
                process_comparison, governance_transfer
            ),
            'methodology': self._get_methodology()
        }
        
        self._save_results(results)
        logger.info("Cross-repository comparison analysis complete")
    
    def _load_core_prs(self) -> List[Dict[str, Any]]:
        """Load Core repository PRs."""
        prs_file = self.github_dir / 'prs_raw.jsonl'
        if not prs_file.exists():
            parent_data_dir = self.data_dir.parent.parent / 'data' / 'github' / 'prs_raw.jsonl'
            if parent_data_dir.exists():
                prs_file = parent_data_dir
            else:
                return []
        
        prs = []
        with open(prs_file, 'r') as f:
            for line in f:
                try:
                    prs.append(json.loads(line))
                except:
                    continue
        return prs
    
    def _load_bip_prs(self) -> List[Dict[str, Any]]:
        """Load BIP repository PRs."""
        prs_file = self.bips_dir / 'bips_prs.jsonl'
        if not prs_file.exists():
            return []
        
        prs = []
        with open(prs_file, 'r') as f:
            for line in f:
                try:
                    prs.append(json.loads(line))
                except:
                    continue
        return prs
    
    def _load_bips(self) -> List[Dict[str, Any]]:
        """Load BIPs."""
        bips_file = self.bips_dir / 'bips.jsonl'
        if not bips_file.exists():
            return []
        
        bips = []
        with open(bips_file, 'r') as f:
            for line in f:
                try:
                    bips.append(json.loads(line))
                except:
                    continue
        return bips
    
    def _analyze_actor_overlap(
        self,
        core_prs: List[Dict[str, Any]],
        bip_prs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze actor overlap between repositories."""
        logger.info("Analyzing actor overlap...")
        
        # Extract unique users per repository
        core_authors = {pr.get('author', '').lower() for pr in core_prs if pr.get('author')}
        bip_authors = {pr.get('author', '').lower() for pr in bip_prs if pr.get('author')}
        
        # Find overlaps
        overlapping_authors = core_authors & bip_authors
        
        # Maintainer overlap
        core_maintainers = core_authors & {m.lower() for m in self.maintainers}
        bip_maintainers = bip_authors & {m.lower() for m in self.maintainers}
        maintainer_overlap = core_maintainers & bip_maintainers
        
        return {
            'core_authors': len(core_authors),
            'bip_authors': len(bip_authors),
            'overlapping_authors': len(overlapping_authors),
            'overlap_rate_core': len(overlapping_authors) / len(core_authors) if core_authors else 0,
            'overlap_rate_bip': len(overlapping_authors) / len(bip_authors) if bip_authors else 0,
            'core_maintainers': len(core_maintainers),
            'bip_maintainers': len(bip_maintainers),
            'maintainer_overlap': len(maintainer_overlap),
            'overlap_examples': list(overlapping_authors)[:20]
        }
    
    def _compare_governance_patterns(
        self,
        core_prs: List[Dict[str, Any]],
        bip_prs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Compare governance patterns between repositories."""
        logger.info("Comparing governance patterns...")
        
        # Merge concentration (Core)
        core_merged = [pr for pr in core_prs if pr.get('merged')]
        core_mergers = Counter(pr.get('merged_by') for pr in core_merged if pr.get('merged_by'))
        core_top3_mergers = sum(count for _, count in core_mergers.most_common(3))
        core_total_merged = len(core_merged)
        core_top3_share = core_top3_mergers / core_total_merged if core_total_merged > 0 else 0
        
        # Merge concentration (BIPs)
        bip_merged = [pr for pr in bip_prs if pr.get('merged')]
        bip_mergers = Counter(pr.get('author') for pr in bip_merged if pr.get('author'))
        bip_top3_mergers = sum(count for _, count in bip_mergers.most_common(3))
        bip_total_merged = len(bip_merged)
        bip_top3_share = bip_top3_mergers / bip_total_merged if bip_total_merged > 0 else 0
        
        # Calculate Gini coefficient
        core_gini = self._calculate_gini([count for _, count in core_mergers.items()])
        bip_gini = self._calculate_gini([count for _, count in bip_mergers.items()])
        
        return {
            'core_repo': {
                'total_merged': core_total_merged,
                'unique_mergers': len(core_mergers),
                'top3_share': core_top3_share,
                'gini_coefficient': core_gini,
                'top_mergers': dict(core_mergers.most_common(10))
            },
            'bips_repo': {
                'total_merged': bip_total_merged,
                'unique_mergers': len(bip_mergers),
                'top3_share': bip_top3_share,
                'gini_coefficient': bip_gini,
                'top_mergers': dict(bip_mergers.most_common(10))
            },
            'comparison': {
                'concentration_difference': core_top3_share - bip_top3_share,
                'gini_difference': core_gini - bip_gini
            }
        }
    
    def _analyze_power_portability(
        self,
        core_prs: List[Dict[str, Any]],
        bip_prs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze power portability (power in BIPs repo → power in Core repo)."""
        logger.info("Analyzing power portability...")
        
        # Calculate power in BIPs repo (merge count)
        bip_power = Counter()
        for pr in bip_prs:
            if pr.get('merged'):
                author = (pr.get('author') or '').lower()
                if author:
                    bip_power[author] += 1
        
        # Calculate power in Core repo (merge count)
        core_power = Counter()
        for pr in core_prs:
            if pr.get('merged'):
                merged_by = (pr.get('merged_by') or '').lower()
                if merged_by:
                    core_power[merged_by] += 1
        
        # Find actors with power in both
        bip_top10 = {author for author, _ in bip_power.most_common(10)}
        core_top10 = {author for author, _ in core_power.most_common(10)}
        
        power_overlap = bip_top10 & core_top10
        
        # Calculate power correlation
        overlapping_actors = []
        for actor in power_overlap:
            bip_count = bip_power.get(actor, 0)
            core_count = core_power.get(actor, 0)
            overlapping_actors.append({
                'actor': actor,
                'bip_power': bip_count,
                'core_power': core_count
            })
        
        return {
            'bip_top10': list(bip_top10),
            'core_top10': list(core_top10),
            'power_overlap': list(power_overlap),
            'overlap_count': len(power_overlap),
            'power_overlap_rate': len(power_overlap) / 10 if len(bip_top10) > 0 else 0,
            'overlapping_actors': overlapping_actors
        }
    
    def _compare_processes(
        self,
        core_prs: List[Dict[str, Any]],
        bip_prs: List[Dict[str, Any]],
        bips: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Compare processes (BIP proposal vs Core implementation)."""
        logger.info("Comparing processes...")
        
        # BIP proposal process
        bip_merged = [pr for pr in bip_prs if pr.get('merged')]
        bip_rejected = [pr for pr in bip_prs if pr.get('state') == 'closed' and not pr.get('merged')]
        bip_merge_rate = len(bip_merged) / len(bip_prs) if bip_prs else 0
        
        # Core implementation process
        core_merged = [pr for pr in core_prs if pr.get('merged')]
        core_rejected = [pr for pr in core_prs if pr.get('state') == 'closed' and not pr.get('merged')]
        core_merge_rate = len(core_merged) / len(core_prs) if core_prs else 0
        
        return {
            'bip_process': {
                'total_prs': len(bip_prs),
                'merged': len(bip_merged),
                'rejected': len(bip_rejected),
                'merge_rate': bip_merge_rate
            },
            'core_process': {
                'total_prs': len(core_prs),
                'merged': len(core_merged),
                'rejected': len(core_rejected),
                'merge_rate': core_merge_rate
            },
            'process_comparison': {
                'merge_rate_difference': core_merge_rate - bip_merge_rate,
                'note': 'BIPs repo: proposal process; Core repo: implementation process'
            }
        }
    
    def _analyze_governance_transfer(
        self,
        core_prs: List[Dict[str, Any]],
        bip_prs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze governance transfer (process improvements)."""
        logger.info("Analyzing governance transfer...")
        
        # This is simplified - would need temporal analysis for full transfer analysis
        return {
            'note': 'Full governance transfer analysis requires temporal comparison',
            'actor_overlap_rate': len(set(pr.get('author') for pr in bip_prs if pr.get('author'))) / 
                                  len(set(pr.get('author') for pr in core_prs if pr.get('author'))) 
                                  if core_prs else 0
        }
    
    def _calculate_gini(self, values: List[float]) -> float:
        """Calculate Gini coefficient."""
        if not values or sum(values) == 0:
            return 0.0
        
        sorted_values = sorted(values)
        n = len(sorted_values)
        cumsum = 0
        for i, value in enumerate(sorted_values):
            cumsum += value * (i + 1)
        
        return (2 * cumsum) / (n * sum(sorted_values)) - (n + 1) / n
    
    def _generate_statistics(
        self,
        actor_overlap: Dict[str, Any],
        governance_comparison: Dict[str, Any],
        power_portability: Dict[str, Any],
        process_comparison: Dict[str, Any],
        governance_transfer: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate overall statistics."""
        return {
            'summary': {
                'actor_overlap_rate': actor_overlap.get('overlap_rate_core', 0),
                'core_gini': governance_comparison.get('core_repo', {}).get('gini_coefficient', 0),
                'bip_gini': governance_comparison.get('bips_repo', {}).get('gini_coefficient', 0),
                'power_overlap_rate': power_portability.get('power_overlap_rate', 0),
                'core_merge_rate': process_comparison.get('core_process', {}).get('merge_rate', 0),
                'bip_merge_rate': process_comparison.get('bip_process', {}).get('merge_rate', 0)
            }
        }
    
    def _get_methodology(self) -> Dict[str, Any]:
        """Get methodology description."""
        return {
            'actor_overlap': 'Exact username matching across repositories',
            'governance_comparison': 'Merge concentration (top 3 share, Gini coefficient)',
            'power_portability': 'Top 10 actors comparison (power in BIPs → power in Core)',
            'process_comparison': 'Merge rates and rejection rates',
            'governance_transfer': 'Actor overlap as proxy for governance transfer',
            'limitations': [
                'Power portability requires actor identification accuracy',
                'Process comparison simplified (BIPs: proposals, Core: implementation)',
                'Governance transfer requires temporal analysis'
            ]
        }
    
    def _save_results(self, results: Dict[str, Any]):
        """Save analysis results."""
        output_file = self.findings_dir / 'cross_repo_comparison.json'
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to {output_file}")


def main():
    """Main entry point."""
    analyzer = CrossRepoComparisonAnalyzer()
    analyzer.run_analysis()


if __name__ == '__main__':
    main()
