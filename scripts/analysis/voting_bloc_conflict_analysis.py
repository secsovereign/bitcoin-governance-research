#!/usr/bin/env python3
"""
Voting Bloc + Conflict Resolution Analysis

Analyzes how voting blocs behave during conflicts:
- Do voting blocs vote together in conflicts?
- Do blocs break during conflicts or stay cohesive?
- Are conflicts more likely when blocs disagree?
- Do blocs mediate conflicts or escalate them?
"""

import json
import sys
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Any, Set, Tuple
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.utils.load_prs_with_merged_by import load_prs_with_merged_by


class VotingBlocConflictAnalyzer:
    """Analyze voting bloc behavior during conflicts."""
    
    def __init__(self, data_dir: Path):
        """Initialize."""
        self.data_dir = data_dir
        self.maintainers = {
            'laanwj', 'sipa', 'maflcko', 'fanquake', 'hebasto', 'jnewbery',
            'ryanofsky', 'achow101', 'theuni', 'jonasschnelli', 'Sjors',
            'promag', 'instagibbs', 'TheBlueMatt', 'jonatack', 'gmaxwell',
            'gavinandresen', 'petertodd', 'luke-jr', 'glozow', 'TheCharlatan'
        }
        
        self.nack_keywords = [
            'nack', 'nacked', 'nacking',
            'concept nack', 'approach nack', 'utack nack',
            'strong nack', 'weak nack'
        ]
    
    def load_prs(self) -> List[Dict[str, Any]]:
        """Load PRs with merged_by data."""
        prs_file = self.data_dir / 'github' / 'prs_raw.jsonl'
        mapping_file = self.data_dir / 'github' / 'merged_by_mapping.jsonl'
        return load_prs_with_merged_by(prs_file, mapping_file if mapping_file.exists() else None)
    
    def identify_conflicts(self, pr: Dict[str, Any]) -> Dict[str, Any]:
        """Identify if PR has conflicts and what type."""
        has_nack = False
        has_changes_requested = False
        has_heated_discussion = False
        
        # Check for NACKs
        for comment in pr.get('comments', []):
            body = (comment.get('body') or '').lower()
            if any(keyword in body for keyword in self.nack_keywords):
                has_nack = True
                break
        
        # Check for CHANGES_REQUESTED reviews
        for review in pr.get('reviews', []):
            if (review.get('state') or '').upper() == 'CHANGES_REQUESTED':
                has_changes_requested = True
                break
        
        # Check for heated discussion (multiple negative comments)
        negative_keywords = ['disagree', 'oppose', 'against', 'wrong', 'bad idea', 'concern', 'problem']
        negative_comments = sum(1 for comment in pr.get('comments', [])
                              if any(kw in (comment.get('body') or '').lower() for kw in negative_keywords))
        if negative_comments >= 3:
            has_heated_discussion = True
        
        has_conflict = has_nack or has_changes_requested or has_heated_discussion
        
        return {
            'has_conflict': has_conflict,
            'has_nack': has_nack,
            'has_changes_requested': has_changes_requested,
            'has_heated_discussion': has_heated_discussion,
            'conflict_types': {
                'nack': has_nack,
                'changes_requested': has_changes_requested,
                'heated_discussion': has_heated_discussion
            }
        }
    
    def analyze_bloc_behavior_in_conflicts(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze how voting blocs behave during conflicts."""
        print("Analyzing voting bloc behavior in conflicts...")
        
        maintainer_list = [m.lower() for m in self.maintainers]
        
        # Track PRs with conflicts
        conflict_prs = []
        non_conflict_prs = []
        
        for pr in prs:
            conflict_info = self.identify_conflicts(pr)
            if conflict_info['has_conflict']:
                conflict_prs.append((pr, conflict_info))
            else:
                non_conflict_prs.append(pr)
        
        # Analyze voting blocs in conflict PRs
        conflict_bloc_stats = self._analyze_blocs_in_prs([p[0] for p in conflict_prs], maintainer_list, 'conflict')
        
        # Analyze voting blocs in non-conflict PRs
        non_conflict_bloc_stats = self._analyze_blocs_in_prs(non_conflict_prs, maintainer_list, 'non_conflict')
        
        # Compare
        comparison = {
            'conflict_prs': {
                'count': len(conflict_prs),
                'avg_cohesion': conflict_bloc_stats['avg_cohesion'],
                'strong_blocs_count': conflict_bloc_stats['strong_blocs_count'],
                'voting_pairs': conflict_bloc_stats['voting_pairs']
            },
            'non_conflict_prs': {
                'count': len(non_conflict_prs),
                'avg_cohesion': non_conflict_bloc_stats['avg_cohesion'],
                'strong_blocs_count': non_conflict_bloc_stats['strong_blocs_count'],
                'voting_pairs': non_conflict_bloc_stats['voting_pairs']
            },
            'difference': {
                'cohesion_diff': conflict_bloc_stats['avg_cohesion'] - non_conflict_bloc_stats['avg_cohesion'],
                'strong_blocs_diff': conflict_bloc_stats['strong_blocs_count'] - non_conflict_bloc_stats['strong_blocs_count']
            }
        }
        
        return {
            'conflict_bloc_analysis': conflict_bloc_stats,
            'non_conflict_bloc_analysis': non_conflict_bloc_stats,
            'comparison': comparison,
            'total_conflict_prs': len(conflict_prs),
            'total_non_conflict_prs': len(non_conflict_prs)
        }
    
    def _analyze_blocs_in_prs(self, prs: List[Dict[str, Any]], maintainer_list: List[str], label: str) -> Dict[str, Any]:
        """Analyze voting blocs in a set of PRs."""
        # Track review decisions for each PR by maintainers
        pr_maintainer_reviews = defaultdict(lambda: defaultdict(str))  # pr_num -> maintainer -> review_state
        
        for pr in prs:
            pr_number = pr.get('number')
            if not pr_number:
                continue
            
            for review in pr.get('reviews', []):
                reviewer = (review.get('author') or '').lower()
                review_state = (review.get('state') or '').lower()
                
                if reviewer in maintainer_list and review_state in ['approved', 'changes_requested']:
                    pr_maintainer_reviews[pr_number][reviewer] = review_state
        
        # Identify pairs of maintainers who frequently vote together
        voting_together_counts = defaultdict(lambda: defaultdict(int))
        
        for pr_num, maintainer_states in pr_maintainer_reviews.items():
            active_maintainers_in_pr = [m for m in maintainer_list if m in maintainer_states]
            
            for i, m1 in enumerate(active_maintainers_in_pr):
                for m2 in active_maintainers_in_pr[i+1:]:
                    if maintainer_states[m1] == maintainer_states[m2]:
                        # They voted the same way
                        pair_key = tuple(sorted((m1, m2)))
                        voting_together_counts[pair_key][maintainer_states[m1]] += 1
        
        # Calculate cohesion for each pair
        blocs = []
        for pair, states in voting_together_counts.items():
            m1, m2 = pair
            total_same_votes = sum(states.values())
            
            if total_same_votes > 2:  # Only consider significant interactions
                # Count total times they reviewed same PRs
                total_together = sum(1 for pr_num, maintainer_states in pr_maintainer_reviews.items()
                                   if m1 in maintainer_states and m2 in maintainer_states)
                
                cohesion = total_same_votes / total_together if total_together > 0 else 0
                
                blocs.append({
                    'pair': f"{m1}_{m2}",
                    'm1': m1,
                    'm2': m2,
                    'together': total_same_votes,
                    'total': total_together,
                    'cohesion': cohesion
                })
        
        # Calculate average cohesion
        avg_cohesion = sum(b['cohesion'] for b in blocs) / len(blocs) if blocs else 0
        strong_blocs = [b for b in blocs if b['cohesion'] > 0.8]
        
        return {
            'voting_pairs': len(blocs),
            'avg_cohesion': avg_cohesion,
            'strong_blocs_count': len(strong_blocs),
            'top_blocs': sorted(blocs, key=lambda x: x['cohesion'], reverse=True)[:10]
        }
    
    def run_analysis(self) -> Dict[str, Any]:
        """Run full analysis."""
        print("="*80)
        print("VOTING BLOC + CONFLICT ANALYSIS")
        print("="*80)
        print()
        
        prs = self.load_prs()
        print(f"Loaded {len(prs):,} PRs")
        print()
        
        bloc_conflict_analysis = self.analyze_bloc_behavior_in_conflicts(prs)
        
        results = {
            'bloc_conflict_analysis': bloc_conflict_analysis,
            'analysis_date': datetime.now().isoformat()
        }
        
        return results
    
    def print_results(self, results: Dict[str, Any]):
        """Print results."""
        print("="*80)
        print("VOTING BLOC + CONFLICT RESULTS")
        print("="*80)
        print()
        
        analysis = results.get('bloc_conflict_analysis', {})
        comparison = analysis.get('comparison', {})
        
        print("COMPARISON: Voting Blocs in Conflicts vs. Non-Conflicts")
        print("-" * 80)
        print(f"Conflict PRs: {comparison.get('conflict_prs', {}).get('count', 0):,}")
        print(f"  Avg Cohesion: {comparison.get('conflict_prs', {}).get('avg_cohesion', 0):.1%}")
        print(f"  Strong Blocs: {comparison.get('conflict_prs', {}).get('strong_blocs_count', 0)}")
        print()
        print(f"Non-Conflict PRs: {comparison.get('non_conflict_prs', {}).get('count', 0):,}")
        print(f"  Avg Cohesion: {comparison.get('non_conflict_prs', {}).get('avg_cohesion', 0):.1%}")
        print(f"  Strong Blocs: {comparison.get('non_conflict_prs', {}).get('strong_blocs_count', 0)}")
        print()
        print(f"Difference:")
        print(f"  Cohesion Diff: {comparison.get('difference', {}).get('cohesion_diff', 0):+.1%}")
        print(f"  Strong Blocs Diff: {comparison.get('difference', {}).get('strong_blocs_diff', 0):+d}")
        print()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Voting Bloc + Conflict Analysis')
    parser.add_argument('--data-dir', type=Path, default=Path(__file__).parent.parent.parent.parent / 'data',
                       help='Data directory')
    parser.add_argument('--output', type=Path, default=Path(__file__).parent.parent.parent / 'findings' / 'data' / 'voting_bloc_conflict.json',
                       help='Output JSON file')
    
    args = parser.parse_args()
    
    analyzer = VotingBlocConflictAnalyzer(args.data_dir)
    results = analyzer.run_analysis()
    analyzer.print_results(results)
    
    # Save results
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nResults saved to: {args.output}")


if __name__ == '__main__':
    main()

