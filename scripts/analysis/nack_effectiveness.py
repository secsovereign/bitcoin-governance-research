#!/usr/bin/env python3
"""
NACK Effectiveness Analysis - Analyze the impact of NACKs on PR outcomes.

Analyzes:
1. NACK effectiveness (do NACKs kill PRs?)
2. Maintainer vs non-maintainer NACK effectiveness
3. Top NACKers and their kill rates
4. NACK patterns and timing
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from collections import defaultdict, Counter
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir, get_analysis_dir
from src.utils.statistics import StatisticalAnalyzer
from src.schemas.analysis_results import create_result_template

logger = setup_logger()


class NackEffectivenessAnalyzer:
    """Analyzer for NACK effectiveness."""
    
    def __init__(self):
        """Initialize analyzer."""
        self.data_dir = get_data_dir()
        self.processed_dir = self.data_dir / 'processed'
        self.analysis_dir = get_analysis_dir() / 'nack_effectiveness'
        self.analysis_dir.mkdir(parents=True, exist_ok=True)
        
        self.stat_analyzer = StatisticalAnalyzer(random_seed=42)
        
        # NACK keywords
        self.nack_keywords = [
            'nack', 'nacked', 'nacking',
            'concept nack', 'approach nack', 'utack nack',
            'strong nack', 'weak nack'
        ]
    
    def run_analysis(self):
        """Run NACK effectiveness analysis."""
        logger.info("=" * 60)
        logger.info("NACK Effectiveness Analysis")
        logger.info("=" * 60)
        
        # Load data
        prs = self._load_enriched_prs()
        maintainer_timeline = self._load_maintainer_timeline()
        
        # Extract NACKs
        nacks = self._extract_nacks(prs)
        
        # Analyze NACK effectiveness
        effectiveness = self._analyze_effectiveness(nacks, prs)
        
        # Analyze maintainer vs non-maintainer NACKs
        maintainer_comparison = self._compare_maintainer_nacks(nacks, prs, maintainer_timeline)
        
        # Identify top NACKers
        top_nackers = self._identify_top_nackers(nacks, prs, maintainer_timeline)
        
        # Analyze NACK patterns
        patterns = self._analyze_nack_patterns(nacks, prs)
        
        # Save results
        self._save_results({
            'effectiveness': effectiveness,
            'maintainer_comparison': maintainer_comparison,
            'top_nackers': top_nackers,
            'patterns': patterns
        })
        
        logger.info("NACK effectiveness analysis complete")
    
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
                prs.append(json.loads(line))
        
        return prs
    
    def _load_maintainer_timeline(self) -> Dict[str, Any]:
        """Load maintainer timeline."""
        timeline_file = self.processed_dir / 'maintainer_timeline.json'
        
        if not timeline_file.exists():
            return {}
        
        with open(timeline_file, 'r') as f:
            data = json.load(f)
            return data.get('maintainer_timeline', {})
    
    def _extract_nacks(self, prs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract NACKs from PR comments and reviews."""
        nacks = []
        
        for pr in prs:
            pr_number = pr.get('number')
            
            # Check comments
            for comment in pr.get('comments', []):
                text = (comment.get('body') or '').lower()
                if any(keyword in text for keyword in self.nack_keywords):
                    nacks.append({
                        'pr_number': pr_number,
                        'type': 'comment',
                        'author': comment.get('author'),
                        'timestamp': comment.get('created_at'),
                        'text': comment.get('body', ''),
                        'pr_state': pr.get('state')
                    })
            
            # Check reviews
            for review in pr.get('reviews', []):
                text = (review.get('body') or '').lower()
                if any(keyword in text for keyword in self.nack_keywords):
                    nacks.append({
                        'pr_number': pr_number,
                        'type': 'review',
                        'author': review.get('author'),
                        'timestamp': review.get('submitted_at'),
                        'text': review.get('body', ''),
                        'review_state': review.get('state'),
                        'pr_state': pr.get('state')
                    })
        
        logger.info(f"Extracted {len(nacks)} NACKs")
        return nacks
    
    def _analyze_effectiveness(self, nacks: List[Dict[str, Any]], prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze NACK effectiveness."""
        # Map PRs by number
        prs_by_number = {pr.get('number'): pr for pr in prs}
        
        # Track NACK outcomes
        nacked_prs = set()
        nacked_and_closed = 0
        nacked_and_merged = 0
        
        for nack in nacks:
            pr_number = nack.get('pr_number')
            if pr_number:
                nacked_prs.add(pr_number)
                pr = prs_by_number.get(pr_number)
                if pr:
                    if pr.get('state') == 'closed' and not pr.get('merged'):
                        nacked_and_closed += 1
                    elif pr.get('merged'):
                        nacked_and_merged += 1
        
        total_nacked = len(nacked_prs)
        kill_rate = nacked_and_closed / total_nacked if total_nacked > 0 else 0
        
        # Compare to overall close rate
        total_prs = len(prs)
        closed_prs = sum(1 for pr in prs if pr.get('state') == 'closed' and not pr.get('merged'))
        overall_close_rate = closed_prs / total_prs if total_prs > 0 else 0
        
        return {
            'total_nacks': len(nacks),
            'nacked_prs': total_nacked,
            'nacked_and_closed': nacked_and_closed,
            'nacked_and_merged': nacked_and_merged,
            'kill_rate': kill_rate,
            'overall_close_rate': overall_close_rate,
            'effectiveness_ratio': kill_rate / overall_close_rate if overall_close_rate > 0 else 0
        }
    
    def _compare_maintainer_nacks(
        self,
        nacks: List[Dict[str, Any]],
        prs: List[Dict[str, Any]],
        maintainer_timeline: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare maintainer vs non-maintainer NACK effectiveness."""
        prs_by_number = {pr.get('number'): pr for pr in prs}
        
        maintainer_nacks = []
        non_maintainer_nacks = []
        
        for nack in nacks:
            author = nack.get('author')
            pr_number = nack.get('pr_number')
            
            # Check if maintainer
            is_maintainer = author in maintainer_timeline
            
            nack_with_outcome = {
                **nack,
                'pr_merged': prs_by_number.get(pr_number, {}).get('merged', False),
                'pr_closed': prs_by_number.get(pr_number, {}).get('state') == 'closed'
            }
            
            if is_maintainer:
                maintainer_nacks.append(nack_with_outcome)
            else:
                non_maintainer_nacks.append(nack_with_outcome)
        
        # Calculate kill rates
        maintainer_kills = sum(1 for n in maintainer_nacks if n['pr_closed'] and not n['pr_merged'])
        maintainer_kill_rate = maintainer_kills / len(maintainer_nacks) if maintainer_nacks else 0
        
        non_maintainer_kills = sum(1 for n in non_maintainer_nacks if n['pr_closed'] and not n['pr_merged'])
        non_maintainer_kill_rate = non_maintainer_kills / len(non_maintainer_nacks) if non_maintainer_nacks else 0
        
        return {
            'maintainer_nacks': len(maintainer_nacks),
            'non_maintainer_nacks': len(non_maintainer_nacks),
            'maintainer_kill_rate': maintainer_kill_rate,
            'non_maintainer_kill_rate': non_maintainer_kill_rate,
            'difference': maintainer_kill_rate - non_maintainer_kill_rate
        }
    
    def _identify_top_nackers(
        self,
        nacks: List[Dict[str, Any]],
        prs: List[Dict[str, Any]],
        maintainer_timeline: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identify top NACKers and their kill rates."""
        prs_by_number = {pr.get('number'): pr for pr in prs}
        
        nacker_stats = defaultdict(lambda: {'count': 0, 'kills': 0})
        
        for nack in nacks:
            author = nack.get('author')
            pr_number = nack.get('pr_number')
            
            if author:
                nacker_stats[author]['count'] += 1
                
                pr = prs_by_number.get(pr_number)
                if pr and pr.get('state') == 'closed' and not pr.get('merged'):
                    nacker_stats[author]['kills'] += 1
        
        # Calculate kill rates
        top_nackers = []
        for author, stats in nacker_stats.items():
            kill_rate = stats['kills'] / stats['count'] if stats['count'] > 0 else 0
            top_nackers.append({
                'author': author,
                'nack_count': stats['count'],
                'kills': stats['kills'],
                'kill_rate': kill_rate,
                'is_maintainer': author in maintainer_timeline
            })
        
        # Sort by kill rate, then by count
        top_nackers.sort(key=lambda x: (x['kill_rate'], x['nack_count']), reverse=True)
        
        return top_nackers[:20]  # Top 20
    
    def _analyze_nack_patterns(self, nacks: List[Dict[str, Any]], prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze NACK patterns."""
        # NACK timing (early vs late in PR lifecycle)
        early_nacks = 0
        late_nacks = 0
        
        prs_by_number = {pr.get('number'): pr for pr in prs}
        
        for nack in nacks:
            pr_number = nack.get('pr_number')
            pr = prs_by_number.get(pr_number)
            
            if pr and nack.get('timestamp') and pr.get('created_at'):
                try:
                    nack_time = datetime.fromisoformat(nack['timestamp'].replace('Z', '+00:00'))
                    pr_created = datetime.fromisoformat(pr['created_at'].replace('Z', '+00:00'))
                    days_after = (nack_time - pr_created).days
                    
                    if days_after < 7:
                        early_nacks += 1
                    else:
                        late_nacks += 1
                except Exception:
                    pass
        
        # NACK types
        nack_types = Counter()
        for nack in nacks:
            text = (nack.get('text') or '').lower()
            if 'concept nack' in text:
                nack_types['concept'] += 1
            elif 'approach nack' in text:
                nack_types['approach'] += 1
            elif 'utack nack' in text:
                nack_types['utack'] += 1
            else:
                nack_types['general'] += 1
        
        return {
            'early_nacks': early_nacks,
            'late_nacks': late_nacks,
            'nack_types': dict(nack_types),
            'total_nacks': len(nacks)
        }
    
    def _save_results(self, results: Dict[str, Any]):
        """Save analysis results."""
        result = create_result_template('nack_effectiveness_analysis', '1.0.0')
        result['metadata']['timestamp'] = datetime.now().isoformat()
        result['metadata']['data_sources'] = ['data/processed/enriched_prs.jsonl']
        result['data'] = results
        
        output_file = self.analysis_dir / 'nack_effectiveness_analysis.json'
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        logger.info(f"Results saved to {output_file}")
        
        # Generate summary
        eff = results.get('effectiveness', {})
        logger.info(f"NACK Effectiveness Summary:")
        logger.info(f"  Total NACKs: {eff.get('total_nacks', 0)}")
        logger.info(f"  Kill Rate: {eff.get('kill_rate', 0):.2%}")
        logger.info(f"  Effectiveness Ratio: {eff.get('effectiveness_ratio', 0):.2f}")


def main():
    """Main entry point."""
    analyzer = NackEffectivenessAnalyzer()
    analyzer.run_analysis()
    return 0


if __name__ == '__main__':
    sys.exit(main())

