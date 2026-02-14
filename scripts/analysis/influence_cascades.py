#!/usr/bin/env python3
"""
Influence Cascades Analysis

Analyzes how one person's opinion influences others over time.
Tracks opinion changes in PR reviews/comments after a maintainer's review.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Any, Set, Tuple, Optional
from datetime import datetime, timedelta
from statistics import mean, median

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.utils.load_prs_with_merged_by import load_prs_with_merged_by


class InfluenceCascadeAnalyzer:
    """Analyze influence cascades in PR reviews."""
    
    def __init__(self, data_dir: Path):
        """Initialize."""
        self.data_dir = data_dir
        self.maintainers = {
            'laanwj', 'sipa', 'maflcko', 'fanquake', 'hebasto', 'jnewbery',
            'ryanofsky', 'achow101', 'theuni', 'jonasschnelli', 'Sjors',
            'promag', 'instagibbs', 'TheBlueMatt', 'jonatack', 'gmaxwell',
            'gavinandresen', 'petertodd', 'luke-jr', 'glozow', 'TheCharlatan'
        }
    
    def load_prs(self) -> List[Dict[str, Any]]:
        """Load PRs with merged_by data."""
        prs_file = self.data_dir / 'github' / 'prs_raw.jsonl'
        mapping_file = self.data_dir / 'github' / 'merged_by_mapping.jsonl'
        return load_prs_with_merged_by(prs_file, mapping_file if mapping_file.exists() else None)
    
    def parse_timestamp(self, ts: Optional[str]) -> Optional[datetime]:
        """Parse timestamp string to datetime."""
        if not ts:
            return None
        try:
            # Handle various formats
            ts = ts.replace('Z', '+00:00')
            return datetime.fromisoformat(ts)
        except:
            return None
    
    def get_review_state(self, review: Dict[str, Any]) -> Optional[str]:
        """Get review state (APPROVED, CHANGES_REQUESTED, COMMENTED)."""
        return review.get('state')
    
    def analyze_influence_cascades(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze how maintainer reviews influence subsequent reviews.
        
        For each PR:
        1. Find first maintainer review
        2. Track subsequent reviews and see if they align with maintainer
        3. Measure time-to-alignment
        4. Count opinion changes
        """
        print("Analyzing influence cascades...")
        
        results = {
            'total_prs_analyzed': 0,
            'prs_with_maintainer_review': 0,
            'cascade_events': [],
            'influence_metrics': {},
            'maintainer_influence': defaultdict(lambda: {
                'total_reviews_after': 0,
                'aligned_reviews': 0,
                'opposed_reviews': 0,
                'avg_time_to_alignment_hours': [],
                'cascade_rate': 0.0
            })
        }
        
        for pr in prs:
            if not pr.get('reviews'):
                continue
            
            reviews = pr.get('reviews', [])
            if len(reviews) < 2:  # Need at least 2 reviews to see cascade
                continue
            
            results['total_prs_analyzed'] += 1
            
            # Sort reviews by timestamp
            review_times = []
            for review in reviews:
                ts = self.parse_timestamp(review.get('created_at'))
                if ts:
                    reviewer = (review.get('author') or '').lower()
                    state = self.get_review_state(review)
                    if reviewer and state:
                        review_times.append((ts, reviewer, state, review))
            
            if len(review_times) < 2:
                continue
            
            review_times.sort(key=lambda x: x[0])
            
            # Find first maintainer review
            first_maintainer_review = None
            for i, (ts, reviewer, state, review) in enumerate(review_times):
                if reviewer in [m.lower() for m in self.maintainers]:
                    first_maintainer_review = (i, ts, reviewer, state, review)
                    break
            
            if not first_maintainer_review:
                continue
            
            results['prs_with_maintainer_review'] += 1
            maint_idx, maint_ts, maint_reviewer, maint_state, maint_review = first_maintainer_review
            
            # Track subsequent reviews
            subsequent_reviews = review_times[maint_idx + 1:]
            
            for ts, reviewer, state, review in subsequent_reviews:
                # Skip if same reviewer (they can't influence themselves)
                if reviewer == maint_reviewer:
                    continue
                
                # Skip if reviewer is also a maintainer (they might not be influenced)
                if reviewer in [m.lower() for m in self.maintainers]:
                    continue
                
                time_diff = (ts - maint_ts).total_seconds() / 3600  # hours
                
                # Check if review aligns with maintainer
                aligned = False
                if maint_state == 'APPROVED' and state == 'APPROVED':
                    aligned = True
                elif maint_state == 'CHANGES_REQUESTED' and state == 'CHANGES_REQUESTED':
                    aligned = True
                
                results['maintainer_influence'][maint_reviewer]['total_reviews_after'] += 1
                
                if aligned:
                    results['maintainer_influence'][maint_reviewer]['aligned_reviews'] += 1
                    results['maintainer_influence'][maint_reviewer]['avg_time_to_alignment_hours'].append(time_diff)
                    
                    results['cascade_events'].append({
                        'pr_number': pr.get('number'),
                        'maintainer': maint_reviewer,
                        'maintainer_state': maint_state,
                        'follower': reviewer,
                        'follower_state': state,
                        'time_to_alignment_hours': time_diff,
                        'pr_author': (pr.get('author') or '').lower()
                    })
                else:
                    results['maintainer_influence'][maint_reviewer]['opposed_reviews'] += 1
        
        # Calculate cascade rates
        for maintainer in results['maintainer_influence']:
            stats = results['maintainer_influence'][maintainer]
            total = stats['total_reviews_after']
            if total > 0:
                stats['cascade_rate'] = stats['aligned_reviews'] / total
            if stats['avg_time_to_alignment_hours']:
                stats['avg_time_to_alignment_hours'] = mean(stats['avg_time_to_alignment_hours'])
            else:
                stats['avg_time_to_alignment_hours'] = None
        
        # Calculate overall metrics
        all_cascade_rates = [
            stats['cascade_rate'] 
            for stats in results['maintainer_influence'].values() 
            if stats['total_reviews_after'] > 10  # Only maintainers with enough data
        ]
        
        if all_cascade_rates:
            results['influence_metrics'] = {
                'avg_cascade_rate': mean(all_cascade_rates),
                'median_cascade_rate': median(all_cascade_rates),
                'max_cascade_rate': max(all_cascade_rates),
                'min_cascade_rate': min(all_cascade_rates)
            }
        
        return results
    
    def analyze_opinion_changes(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Track when reviewers change their opinion after a maintainer review.
        
        This is more sophisticated - looks for reviewers who review twice,
        with the second review after a maintainer review.
        """
        print("Analyzing opinion changes...")
        
        results = {
            'opinion_changes': [],
            'change_metrics': {}
        }
        
        for pr in prs:
            reviews = pr.get('reviews', [])
            if len(reviews) < 2:
                continue
            
            # Get all reviews with timestamps
            review_sequence = []
            for review in reviews:
                ts = self.parse_timestamp(review.get('created_at'))
                reviewer = (review.get('author') or '').lower()
                state = self.get_review_state(review)
                if ts and reviewer and state:
                    review_sequence.append((ts, reviewer, state))
            
            if len(review_sequence) < 2:
                continue
            
            review_sequence.sort(key=lambda x: x[0])
            
            # Find reviewers who reviewed multiple times
            reviewer_states = defaultdict(list)
            for ts, reviewer, state in review_sequence:
                reviewer_states[reviewer].append((ts, state))
            
            # Check for opinion changes after maintainer reviews
            for i, (ts, reviewer, state) in enumerate(review_sequence):
                # Is this a maintainer review?
                if reviewer not in [m.lower() for m in self.maintainers]:
                    continue
                
                # Check subsequent reviews for opinion changes
                for j, (ts2, reviewer2, state2) in enumerate(review_sequence[i+1:], start=i+1):
                    # Did this reviewer review before?
                    prev_reviews = [s for t, s in reviewer_states[reviewer2] if t < ts]
                    if not prev_reviews:
                        continue
                    
                    prev_state = prev_reviews[-1]  # Last state before maintainer review
                    
                    # Did opinion change?
                    if prev_state != state2:
                        time_to_change = (ts2 - ts).total_seconds() / 3600
                        results['opinion_changes'].append({
                            'pr_number': pr.get('number'),
                            'maintainer': reviewer,
                            'maintainer_state': state,
                            'reviewer': reviewer2,
                            'previous_state': prev_state,
                            'new_state': state2,
                            'time_to_change_hours': time_to_change
                        })
        
        # Calculate metrics
        if results['opinion_changes']:
            times_to_change = [c['time_to_change_hours'] for c in results['opinion_changes']]
            results['change_metrics'] = {
                'total_changes': len(results['opinion_changes']),
                'avg_time_to_change_hours': mean(times_to_change),
                'median_time_to_change_hours': median(times_to_change)
            }
        
        return results
    
    def run_analysis(self) -> Dict[str, Any]:
        """Run full analysis."""
        print("Loading PRs...")
        prs = self.load_prs()
        print(f"Loaded {len(prs)} PRs")
        
        # Run analyses
        cascade_results = self.analyze_influence_cascades(prs)
        opinion_results = self.analyze_opinion_changes(prs)
        
        # Combine results
        combined = {
            'cascade_analysis': cascade_results,
            'opinion_change_analysis': opinion_results,
            'summary': {
                'total_prs': len(prs),
                'prs_with_cascades': cascade_results['prs_with_maintainer_review'],
                'total_cascade_events': len(cascade_results['cascade_events']),
                'total_opinion_changes': len(opinion_results['opinion_changes']),
                'avg_cascade_rate': cascade_results['influence_metrics'].get('avg_cascade_rate', 0),
                'maintainers_analyzed': len(cascade_results['maintainer_influence'])
            }
        }
        
        return combined


def main():
    """Main entry point."""
    data_dir = Path(__file__).parent.parent.parent / 'data'
    output_dir = Path(__file__).parent.parent.parent / 'analysis' / 'findings' / 'data'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    analyzer = InfluenceCascadeAnalyzer(data_dir)
    results = analyzer.run_analysis()
    
    # Save results
    output_file = output_dir / 'influence_cascades.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nAnalysis complete!")
    print(f"Results saved to: {output_file}")
    print(f"\nSummary:")
    print(f"  Total PRs analyzed: {results['summary']['total_prs']}")
    print(f"  PRs with maintainer reviews: {results['summary']['prs_with_cascades']}")
    print(f"  Total cascade events: {results['summary']['total_cascade_events']}")
    print(f"  Total opinion changes: {results['summary']['total_opinion_changes']}")
    print(f"  Average cascade rate: {results['summary']['avg_cascade_rate']:.2%}")
    print(f"  Maintainers analyzed: {results['summary']['maintainers_analyzed']}")


if __name__ == '__main__':
    main()

