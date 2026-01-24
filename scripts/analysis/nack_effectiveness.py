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
try:
    from src.utils.statistics import StatisticalAnalyzer
    HAS_STAT_ANALYZER = True
except ImportError:
    HAS_STAT_ANALYZER = False
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
        
        if HAS_STAT_ANALYZER:
            self.stat_analyzer = StatisticalAnalyzer(random_seed=42)
        else:
            self.stat_analyzer = None
        
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
        
        # Analyze conflict resolution patterns
        conflict_resolution = self._analyze_conflict_resolution(nacks, prs, maintainer_timeline)
        
        # Save results
        self._save_results({
            'effectiveness': effectiveness,
            'maintainer_comparison': maintainer_comparison,
            'top_nackers': top_nackers,
            'patterns': patterns,
            'conflict_resolution': conflict_resolution
        })
        
        logger.info("NACK effectiveness analysis complete")
    
    def _load_enriched_prs(self) -> List[Dict[str, Any]]:
        """Load enriched PR data."""
        prs_file = self.processed_dir / 'enriched_prs.jsonl'
        
        if not prs_file.exists():
            prs_file = self.processed_dir / 'cleaned_prs.jsonl'
        
        # Check parent directory if not found (go up from publication-package/data to commons-research/data)
        if not prs_file.exists():
            parent_processed = self.data_dir.parent.parent / 'data' / 'processed'
            prs_file = parent_processed / 'enriched_prs.jsonl'
            if not prs_file.exists():
                prs_file = parent_processed / 'cleaned_prs.jsonl'
        
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
    
    def _analyze_conflict_resolution(
        self,
        nacks: List[Dict[str, Any]],
        prs: List[Dict[str, Any]],
        maintainer_timeline: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze conflict resolution patterns."""
        logger.info("Analyzing conflict resolution patterns...")
        
        prs_by_number = {pr.get('number'): pr for pr in prs}
        
        # Identify conflicts: NACKs, CHANGES_REQUESTED reviews
        conflicts = []
        conflict_keywords = ['disagree', 'oppose', 'against', 'wrong', 'bad idea', 'concern']
        
        for pr in prs:
            pr_number = pr.get('number')
            if not pr_number:
                continue
            
            # Check for NACKs
            has_nack = any(n.get('pr_number') == pr_number for n in nacks)
            
            # Check for CHANGES_REQUESTED reviews
            has_changes_requested = any(
                r.get('state', '').upper() == 'CHANGES_REQUESTED'
                for r in pr.get('reviews', [])
            )
            
            # Check for heated discussions (keyword-based)
            has_heated_discussion = False
            for comment in pr.get('comments', []):
                text = (comment.get('body') or '').lower()
                if any(kw in text for kw in conflict_keywords):
                    has_heated_discussion = True
                    break
            
            if has_nack or has_changes_requested or has_heated_discussion:
                conflicts.append({
                    'pr_number': pr_number,
                    'has_nack': has_nack,
                    'has_changes_requested': has_changes_requested,
                    'has_heated_discussion': has_heated_discussion,
                    'pr_state': pr.get('state'),
                    'merged': pr.get('merged', False),
                    'closed': pr.get('state') == 'closed'
                })
        
        # Track resolution paths
        resolution_paths = {
            'merged_anyway': 0,
            'withdrawn': 0,
            'modified': 0,  # Hard to detect, but can infer from multiple updates
            'still_open': 0,
            'closed': 0
        }
        
        for conflict in conflicts:
            pr_number = conflict['pr_number']
            pr = prs_by_number.get(pr_number)
            
            if not pr:
                continue
            
            if conflict['merged']:
                resolution_paths['merged_anyway'] += 1
            elif pr.get('state') == 'closed' and not conflict['merged']:
                # Check if withdrawn (closed without merge, no recent activity)
                resolution_paths['closed'] += 1
            elif pr.get('state') == 'open':
                resolution_paths['still_open'] += 1
        
        # Measure time-to-resolution
        resolution_times = []
        for conflict in conflicts:
            pr_number = conflict['pr_number']
            pr = prs_by_number.get(pr_number)
            
            if not pr or not conflict['closed']:
                continue
            
            created = pr.get('created_at')
            closed = pr.get('closed_at')
            
            if created and closed:
                try:
                    created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    closed_dt = datetime.fromisoformat(closed.replace('Z', '+00:00'))
                    days = (closed_dt - created_dt).days
                    resolution_times.append(days)
                except:
                    pass
        
        avg_resolution_time = sum(resolution_times) / len(resolution_times) if resolution_times else 0
        
        # Conflict networks (who conflicts with whom)
        conflict_networks = defaultdict(lambda: {'conflicts_with': set(), 'conflict_count': 0})
        
        for conflict in conflicts:
            pr_number = conflict['pr_number']
            pr = prs_by_number.get(pr_number)
            
            if not pr:
                continue
            
            author = (pr.get('author') or '').lower()
            
            # Find conflict participants
            for nack in nacks:
                if nack.get('pr_number') == pr_number:
                    nacker = (nack.get('author') or '').lower()
                    if nacker and author:
                        conflict_networks[author]['conflicts_with'].add(nacker)
                        conflict_networks[author]['conflict_count'] += 1
            
            for review in pr.get('reviews', []):
                if review.get('state', '').upper() == 'CHANGES_REQUESTED':
                    reviewer = (review.get('author') or '').lower()
                    if reviewer and author:
                        conflict_networks[author]['conflicts_with'].add(reviewer)
                        conflict_networks[author]['conflict_count'] += 1
        
        # Convert sets to lists for JSON serialization
        conflict_networks_serializable = {}
        for author, data in conflict_networks.items():
            conflict_networks_serializable[author] = {
                'conflicts_with': list(data['conflicts_with']),
                'conflict_count': data['conflict_count']
            }
        
        return {
            'total_conflicts': len(conflicts),
            'conflicts_by_type': {
                'nack': sum(1 for c in conflicts if c['has_nack']),
                'changes_requested': sum(1 for c in conflicts if c['has_changes_requested']),
                'heated_discussion': sum(1 for c in conflicts if c['has_heated_discussion'])
            },
            'resolution_paths': resolution_paths,
            'avg_resolution_time_days': avg_resolution_time,
            'resolution_time_count': len(resolution_times),
            'conflict_networks': conflict_networks_serializable,
            'top_conflict_participants': sorted(
                conflict_networks_serializable.items(),
                key=lambda x: x[1]['conflict_count'],
                reverse=True
            )[:10]
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

