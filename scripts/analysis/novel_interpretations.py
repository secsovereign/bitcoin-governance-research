#!/usr/bin/env python3
"""
Novel Interpretations: New Ways of Looking at the Data

Provides novel aggregations and interpretations without creating charts.
Focuses on behavioral patterns, hierarchies, and relationships.
"""

import json
import sys
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Any, Set, Tuple
from datetime import datetime
from statistics import median, mean

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.utils.load_prs_with_merged_by import load_prs_with_merged_by

class NovelInterpretations:
    """Generate novel interpretations of the data."""
    
    def __init__(self, data_dir: Path):
        """Initialize."""
        self.data_dir = data_dir
        self.maintainers = {
            'laanwj', 'sipa', 'maflcko', 'fanquake', 'hebasto', 'jnewbery',
            'ryanofsky', 'achow101', 'theuni', 'jonasschnelli', 'Sjors',
            'promag', 'instagibbs', 'TheBlueMatt', 'jonatack', 'gmaxwell',
            'gavinandresen', 'petertodd', 'luke-jr', 'glozow'
        }
    
    def load_prs(self) -> List[Dict[str, Any]]:
        """Load PRs with merged_by data."""
        prs_file = self.data_dir / 'github' / 'prs_raw.jsonl'
        mapping_file = self.data_dir / 'github' / 'merged_by_mapping.jsonl'
        return load_prs_with_merged_by(prs_file, mapping_file if mapping_file.exists() else None)
    
    def analyze_behavioral_clusters(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Cluster maintainers by behavioral patterns."""
        print("Analyzing behavioral clusters...")
        
        maintainer_stats = defaultdict(lambda: {
            'self_merge_rate': 0,
            'zero_review_self_merge_rate': 0,
            'avg_reviews_received': 0,
            'avg_reviews_given': 0,
            'merge_authority': 0,  # How many others they merge
            'pr_count': 0,
            'merge_count': 0
        })
        
        # Collect stats
        for pr in prs:
            if not pr.get('merged', False):
                continue
            
            author = (pr.get('author') or '').lower()
            merged_by = (pr.get('merged_by') or '').lower()
            
            if author in [m.lower() for m in self.maintainers]:
                maintainer_stats[author]['pr_count'] += 1
                reviews = pr.get('reviews', [])
                maintainer_stats[author]['avg_reviews_received'] += len(reviews)
                
                if merged_by and author and merged_by == author:
                    maintainer_stats[author]['self_merge_rate'] += 1
                    if len(reviews) == 0:
                        maintainer_stats[author]['zero_review_self_merge_rate'] += 1
            
            if merged_by in [m.lower() for m in self.maintainers]:
                maintainer_stats[merged_by]['merge_count'] += 1
        
        # Count unique authors merged
        unique_authors_merged = defaultdict(set)
        for pr in prs:
            if pr.get('merged', False):
                author = (pr.get('author') or '').lower()
                merged_by = (pr.get('merged_by') or '').lower()
                if merged_by in [m.lower() for m in self.maintainers]:
                    unique_authors_merged[merged_by].add(author)
        
        for maintainer in maintainer_stats:
            maintainer_stats[maintainer]['merge_authority'] = len(unique_authors_merged[maintainer])
            if maintainer_stats[maintainer]['pr_count'] > 0:
                maintainer_stats[maintainer]['self_merge_rate'] /= maintainer_stats[maintainer]['pr_count']
                maintainer_stats[maintainer]['avg_reviews_received'] /= maintainer_stats[maintainer]['pr_count']
        
        # Count reviews given
        reviews_given = Counter()
        for pr in prs:
            for review in pr.get('reviews', []):
                reviewer = (review.get('author') or '').lower()
                if reviewer in [m.lower() for m in self.maintainers]:
                    reviews_given[reviewer] += 1
        
        for maintainer in maintainer_stats:
            maintainer_stats[maintainer]['avg_reviews_given'] = reviews_given[maintainer]
        
        # Cluster by behavior
        clusters = {
            'high_self_merge_high_authority': [],  # Self-merge a lot, merge many others
            'high_self_merge_low_authority': [],   # Self-merge a lot, merge few others
            'low_self_merge_high_authority': [],   # Rarely self-merge, merge many others
            'low_self_merge_low_authority': [],     # Rarely self-merge, merge few others
            'high_reviewer': [],                    # Give many reviews
            'low_reviewer': []                      # Give few reviews
        }
        
        for maintainer, stats in maintainer_stats.items():
            if stats['pr_count'] < 50:  # Skip low-volume
                continue
            
            high_self = stats['self_merge_rate'] > 0.3
            high_authority = stats['merge_authority'] > 10
            high_reviewer = stats['avg_reviews_given'] > 1000
            
            if high_self and high_authority:
                clusters['high_self_merge_high_authority'].append({
                    'maintainer': maintainer,
                    'self_merge_rate': stats['self_merge_rate'],
                    'merge_authority': stats['merge_authority']
                })
            elif high_self and not high_authority:
                clusters['high_self_merge_low_authority'].append({
                    'maintainer': maintainer,
                    'self_merge_rate': stats['self_merge_rate'],
                    'merge_authority': stats['merge_authority']
                })
            elif not high_self and high_authority:
                clusters['low_self_merge_high_authority'].append({
                    'maintainer': maintainer,
                    'self_merge_rate': stats['self_merge_rate'],
                    'merge_authority': stats['merge_authority']
                })
            elif not high_self and not high_authority:
                clusters['low_self_merge_low_authority'].append({
                    'maintainer': maintainer,
                    'self_merge_rate': stats['self_merge_rate'],
                    'merge_authority': stats['merge_authority']
                })
            
            if high_reviewer:
                clusters['high_reviewer'].append({
                    'maintainer': maintainer,
                    'reviews_given': stats['avg_reviews_given']
                })
            else:
                clusters['low_reviewer'].append({
                    'maintainer': maintainer,
                    'reviews_given': stats['avg_reviews_given']
                })
        
        return {
            'clusters': clusters,
            'individual_stats': dict(maintainer_stats)
        }
    
    def analyze_review_reciprocity(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze review reciprocity: Do maintainers review each other?"""
        print("Analyzing review reciprocity...")
        
        # Track who reviews whom
        review_relationships = defaultdict(lambda: defaultdict(int))
        
        for pr in prs:
            author = (pr.get('author') or '').lower()
            if author not in [m.lower() for m in self.maintainers]:
                continue
            
            for review in pr.get('reviews', []):
                reviewer = (review.get('author') or '').lower()
                if reviewer in [m.lower() for m in self.maintainers] and reviewer != author:
                    review_relationships[author][reviewer] += 1
        
        # Calculate reciprocity
        reciprocal_pairs = []
        one_way_pairs = []
        
        maintainer_list = [m.lower() for m in self.maintainers]
        for i, m1 in enumerate(maintainer_list):
            for m2 in maintainer_list[i+1:]:
                m1_reviews_m2 = review_relationships[m2].get(m1, 0)
                m2_reviews_m1 = review_relationships[m1].get(m2, 0)
                
                if m1_reviews_m2 > 0 and m2_reviews_m1 > 0:
                    reciprocal_pairs.append({
                        'pair': (m1, m2),
                        'm1_reviews_m2': m1_reviews_m2,
                        'm2_reviews_m1': m2_reviews_m1,
                        'total': m1_reviews_m2 + m2_reviews_m1
                    })
                elif m1_reviews_m2 > 0 or m2_reviews_m1 > 0:
                    one_way_pairs.append({
                        'pair': (m1, m2),
                        'direction': f"{m1} -> {m2}" if m1_reviews_m2 > 0 else f"{m2} -> {m1}",
                        'count': max(m1_reviews_m2, m2_reviews_m1)
                    })
        
        reciprocal_pairs.sort(key=lambda x: x['total'], reverse=True)
        one_way_pairs.sort(key=lambda x: x['count'], reverse=True)
        
        return {
            'reciprocal_pairs': reciprocal_pairs[:20],
            'one_way_pairs': one_way_pairs[:20],
            'reciprocity_rate': len(reciprocal_pairs) / (len(reciprocal_pairs) + len(one_way_pairs)) if (reciprocal_pairs or one_way_pairs) else 0
        }
    
    def analyze_power_hierarchy(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze power hierarchy: Who merges whom reveals hierarchy."""
        print("Analyzing power hierarchy...")
        
        # Track merge relationships between maintainers
        merge_relationships = defaultdict(lambda: defaultdict(int))
        
        for pr in prs:
            if not pr.get('merged', False):
                continue
            
            author = (pr.get('author') or '').lower()
            merged_by = (pr.get('merged_by') or '').lower()
            
            if author in [m.lower() for m in self.maintainers] and \
               merged_by in [m.lower() for m in self.maintainers] and \
               author != merged_by:
                merge_relationships[merged_by][author] += 1
        
        # Build hierarchy: who merges whom most
        hierarchy = []
        for merger, authors in merge_relationships.items():
            total_merges = sum(authors.values())
            top_authors = sorted(authors.items(), key=lambda x: x[1], reverse=True)[:5]
            
            hierarchy.append({
                'merger': merger,
                'total_maintainer_merges': total_merges,
                'top_authors_merged': top_authors,
                'authority_score': total_merges  # Simple score
            })
        
        hierarchy.sort(key=lambda x: x['authority_score'], reverse=True)
        
        # Find "subordinate" relationships (A merges B frequently)
        strong_relationships = []
        for merger, authors in merge_relationships.items():
            for author, count in authors.items():
                if count >= 20:  # Threshold
                    strong_relationships.append({
                        'merger': merger,
                        'author': author,
                        'count': count,
                        'relationship': f"{merger} frequently merges {author}"
                    })
        
        strong_relationships.sort(key=lambda x: x['count'], reverse=True)
        
        return {
            'hierarchy': hierarchy[:15],
            'strong_relationships': strong_relationships[:20]
        }
    
    def analyze_escalation_patterns(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze escalation: What triggers more reviews?"""
        print("Analyzing escalation patterns...")
        
        # Group PRs by review count
        by_review_count = defaultdict(list)
        
        for pr in prs:
            review_count = len(pr.get('reviews', []))
            by_review_count[review_count].append(pr)
        
        # Analyze what distinguishes high-review PRs
        def analyze_group(group_prs, group_name):
            if not group_prs:
                return {}
            
            maintainer_rate = sum(1 for p in group_prs 
                                 if (p.get('author') or '').lower() in [m.lower() for m in self.maintainers]) / len(group_prs)
            
            avg_files = sum(len(p.get('files', [])) for p in group_prs) / len(group_prs)
            
            # Check for contentious indicators
            has_nack = sum(1 for p in group_prs 
                          if any('nack' in (r.get('body') or '').lower() 
                                for r in p.get('reviews', []))) / len(group_prs)
            
            # Funding mentions
            funding_rate = sum(1 for p in group_prs 
                              if any(kw in (p.get('body') or '').lower() 
                                    for kw in ['funding', 'grant', 'sponsor'])) / len(group_prs)
            
            # Time to first review
            times_to_first_review = []
            for pr in group_prs:
                created = pr.get('created_at')
                reviews = pr.get('reviews', [])
                if created and reviews:
                    first_review = min(r.get('submitted_at') or r.get('created_at', '') 
                                      for r in reviews if r.get('submitted_at') or r.get('created_at'))
                    if first_review:
                        try:
                            created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                            review_dt = datetime.fromisoformat(first_review.replace('Z', '+00:00'))
                            hours = (review_dt - created_dt).total_seconds() / 3600
                            if hours >= 0:
                                times_to_first_review.append(hours)
                        except:
                            pass
            
            avg_time_to_first = sum(times_to_first_review) / len(times_to_first_review) if times_to_first_review else 0
            
            return {
                'count': len(group_prs),
                'maintainer_rate': maintainer_rate,
                'avg_files': avg_files,
                'nack_rate': has_nack,
                'funding_rate': funding_rate,
                'avg_time_to_first_review_hours': avg_time_to_first
            }
        
        low_review = analyze_group(by_review_count[0] + by_review_count[1], 'low (0-1)')
        medium_review = analyze_group(by_review_count[2] + by_review_count[3] + by_review_count[4], 'medium (2-4)')
        high_review = analyze_group([p for count, prs in by_review_count.items() if count >= 5 for p in prs], 'high (5+)')
        
        return {
            'low_review': low_review,
            'medium_review': medium_review,
            'high_review': high_review
        }
    
    def analyze_temporal_cohorts(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze maintainers by cohort (when they became active)."""
        print("Analyzing temporal cohorts...")
        
        # Find first PR date for each maintainer
        first_pr_date = {}
        
        for pr in prs:
            author = (pr.get('author') or '').lower()
            if author in [m.lower() for m in self.maintainers]:
                created = pr.get('created_at')
                if created:
                    try:
                        created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                        if author not in first_pr_date or created_dt < first_pr_date[author]:
                            first_pr_date[author] = created_dt
                    except:
                        pass
        
        # Group into cohorts
        cohorts = {
            'early_2010s': [],  # 2010-2013
            'mid_2010s': [],    # 2014-2016
            'late_2010s': [],   # 2017-2019
            '2020s': []         # 2020+
        }
        
        for maintainer, first_date in first_pr_date.items():
            year = first_date.year
            if year <= 2013:
                cohorts['early_2010s'].append(maintainer)
            elif year <= 2016:
                cohorts['mid_2010s'].append(maintainer)
            elif year <= 2019:
                cohorts['late_2010s'].append(maintainer)
            else:
                cohorts['2020s'].append(maintainer)
        
        # Analyze behavior by cohort
        cohort_stats = {}
        for cohort_name, members in cohorts.items():
            if not members:
                continue
            
            # Get PRs from this cohort
            cohort_prs = [p for p in prs 
                         if (p.get('author') or '').lower() in [m.lower() for m in members]]
            
            merged = [p for p in cohort_prs if p.get('merged', False)]
            self_merged = [p for p in merged 
                          if (p.get('merged_by') or '').lower() == (p.get('author') or '').lower()]
            
            cohort_stats[cohort_name] = {
                'members': members,
                'total_prs': len(cohort_prs),
                'merge_rate': len(merged) / len(cohort_prs) if cohort_prs else 0,
                'self_merge_rate': len(self_merged) / len(merged) if merged else 0,
                'avg_reviews': sum(len(p.get('reviews', [])) for p in merged) / len(merged) if merged else 0
            }
        
        return cohort_stats
    
    def analyze_decision_patterns(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """What distinguishes merged vs rejected PRs beyond obvious factors?"""
        print("Analyzing decision patterns...")
        
        maintainer_prs = [p for p in prs 
                         if (p.get('author') or '').lower() in [m.lower() for m in self.maintainers]]
        non_maintainer_prs = [p for p in prs 
                             if (p.get('author') or '').lower() not in [m.lower() for m in self.maintainers]]
        
        def analyze_outcome(group_prs, group_name):
            merged = [p for p in group_prs if p.get('merged', False)]
            rejected = [p for p in group_prs if not p.get('merged', False) and p.get('state') == 'closed']
            
            def calc_metric(prs, metric_func):
                if not prs:
                    return 0
                return sum(metric_func(p) for p in prs) / len(prs)
            
            # Review patterns
            merged_avg_reviews = calc_metric(merged, lambda p: len(p.get('reviews', [])))
            rejected_avg_reviews = calc_metric(rejected, lambda p: len(p.get('reviews', [])))
            
            # Approval rate
            merged_approval_rate = calc_metric(merged, 
                lambda p: 1 if any(r.get('state') == 'APPROVED' for r in p.get('reviews', [])) else 0)
            rejected_approval_rate = calc_metric(rejected,
                lambda p: 1 if any(r.get('state') == 'APPROVED' for r in p.get('reviews', [])) else 0)
            
            # NACK rate
            merged_nack_rate = calc_metric(merged,
                lambda p: 1 if any('nack' in (r.get('body') or '').lower() 
                                   for r in p.get('reviews', [])) else 0)
            rejected_nack_rate = calc_metric(rejected,
                lambda p: 1 if any('nack' in (r.get('body') or '').lower() 
                                   for r in p.get('reviews', [])) else 0)
            
            # Time patterns
            merged_times = []
            rejected_times = []
            
            for pr in merged:
                created = pr.get('created_at')
                closed = pr.get('merged_at')
                if created and closed:
                    try:
                        created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                        closed_dt = datetime.fromisoformat(closed.replace('Z', '+00:00'))
                        days = (closed_dt - created_dt).total_seconds() / 86400
                        if days >= 0:
                            merged_times.append(days)
                    except:
                        pass
            
            for pr in rejected:
                created = pr.get('created_at')
                closed = pr.get('closed_at')
                if created and closed:
                    try:
                        created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                        closed_dt = datetime.fromisoformat(closed.replace('Z', '+00:00'))
                        days = (closed_dt - created_dt).total_seconds() / 86400
                        if days >= 0:
                            rejected_times.append(days)
                    except:
                        pass
            
            return {
                'merged_count': len(merged),
                'rejected_count': len(rejected),
                'merged_avg_reviews': merged_avg_reviews,
                'rejected_avg_reviews': rejected_avg_reviews,
                'merged_approval_rate': merged_approval_rate,
                'rejected_approval_rate': rejected_approval_rate,
                'merged_nack_rate': merged_nack_rate,
                'rejected_nack_rate': rejected_nack_rate,
                'merged_avg_days': sum(merged_times) / len(merged_times) if merged_times else 0,
                'rejected_avg_days': sum(rejected_times) / len(rejected_times) if rejected_times else 0
            }
        
        return {
            'maintainer': analyze_outcome(maintainer_prs, 'maintainer'),
            'non_maintainer': analyze_outcome(non_maintainer_prs, 'non_maintainer')
        }
    
    def run_all_analyses(self) -> Dict[str, Any]:
        """Run all novel interpretation analyses."""
        print("="*80)
        print("NOVEL INTERPRETATIONS ANALYSIS")
        print("="*80)
        print()
        
        prs = self.load_prs()
        print(f"Loaded {len(prs):,} PRs")
        print()
        
        results = {
            'behavioral_clusters': self.analyze_behavioral_clusters(prs),
            'review_reciprocity': self.analyze_review_reciprocity(prs),
            'power_hierarchy': self.analyze_power_hierarchy(prs),
            'escalation_patterns': self.analyze_escalation_patterns(prs),
            'temporal_cohorts': self.analyze_temporal_cohorts(prs),
            'decision_patterns': self.analyze_decision_patterns(prs),
            'analysis_date': datetime.now().isoformat()
        }
        
        return results
    
    def print_results(self, results: Dict[str, Any]):
        """Print results."""
        print("="*80)
        print("NOVEL INTERPRETATIONS RESULTS")
        print("="*80)
        print()
        
        # Behavioral clusters
        print("BEHAVIORAL CLUSTERS")
        print("-" * 80)
        clusters = results['behavioral_clusters']['clusters']
        print(f"High self-merge + High authority (merge many others):")
        for m in clusters['high_self_merge_high_authority'][:5]:
            print(f"  {m['maintainer']}: {m['self_merge_rate']*100:.1f}% self-merge, {m['merge_authority']} authors merged")
        print()
        print(f"High self-merge + Low authority (mostly self-merge):")
        for m in clusters['high_self_merge_low_authority'][:5]:
            print(f"  {m['maintainer']}: {m['self_merge_rate']*100:.1f}% self-merge, {m['merge_authority']} authors merged")
        print()
        print(f"Low self-merge + High authority (merge others, not self):")
        for m in clusters['low_self_merge_high_authority'][:5]:
            print(f"  {m['maintainer']}: {m['self_merge_rate']*100:.1f}% self-merge, {m['merge_authority']} authors merged")
        print()
        
        # Review reciprocity
        print("REVIEW RECIPROCITY")
        print("-" * 80)
        recip = results['review_reciprocity']
        print(f"Reciprocity rate: {recip['reciprocity_rate']*100:.1f}%")
        print("Top reciprocal pairs:")
        for pair in recip['reciprocal_pairs'][:5]:
            m1, m2 = pair['pair']
            print(f"  {m1} ↔ {m2}: {pair['m1_reviews_m2']} and {pair['m2_reviews_m1']} reviews")
        print()
        
        # Power hierarchy
        print("POWER HIERARCHY")
        print("-" * 80)
        hierarchy = results['power_hierarchy']
        print("Top mergers of other maintainers:")
        for h in hierarchy['hierarchy'][:5]:
            print(f"  {h['merger']}: {h['total_maintainer_merges']} maintainer PRs merged")
            if h['top_authors_merged']:
                top = h['top_authors_merged'][0]
                print(f"    Most frequently merges: {top[0]} ({top[1]} times)")
        print()
        print("Strong subordinate relationships:")
        for rel in hierarchy['strong_relationships'][:5]:
            print(f"  {rel['relationship']}: {rel['count']} times")
        print()
        
        # Escalation patterns
        print("ESCALATION PATTERNS")
        print("-" * 80)
        escalation = results['escalation_patterns']
        print("Low review PRs (0-1 reviews):")
        print(f"  Maintainer rate: {escalation['low_review']['maintainer_rate']*100:.1f}%")
        print(f"  NACK rate: {escalation['low_review']['nack_rate']*100:.1f}%")
        print()
        print("High review PRs (5+ reviews):")
        print(f"  Maintainer rate: {escalation['high_review']['maintainer_rate']*100:.1f}%")
        print(f"  NACK rate: {escalation['high_review']['nack_rate']*100:.1f}%")
        print()
        
        # Temporal cohorts
        print("TEMPORAL COHORTS")
        print("-" * 80)
        cohorts = results['temporal_cohorts']
        for cohort_name, stats in cohorts.items():
            if stats.get('total_prs', 0) > 0:
                print(f"{cohort_name}:")
                print(f"  Members: {', '.join(stats['members'][:5])}")
                print(f"  Self-merge rate: {stats['self_merge_rate']*100:.1f}%")
                print(f"  Avg reviews: {stats['avg_reviews']:.1f}")
                print()
        
        # Decision patterns
        print("DECISION PATTERNS")
        print("-" * 80)
        decisions = results['decision_patterns']
        print("Maintainer PRs:")
        print(f"  Merged avg reviews: {decisions['maintainer']['merged_avg_reviews']:.1f}")
        print(f"  Rejected avg reviews: {decisions['maintainer']['rejected_avg_reviews']:.1f}")
        print(f"  Merged approval rate: {decisions['maintainer']['merged_approval_rate']*100:.1f}%")
        print(f"  Rejected approval rate: {decisions['maintainer']['rejected_approval_rate']*100:.1f}%")
        print()
        print("Non-maintainer PRs:")
        print(f"  Merged avg reviews: {decisions['non_maintainer']['merged_avg_reviews']:.1f}")
        print(f"  Rejected avg reviews: {decisions['non_maintainer']['rejected_avg_reviews']:.1f}")
        print(f"  Merged approval rate: {decisions['non_maintainer']['merged_approval_rate']*100:.1f}%")
        print(f"  Rejected approval rate: {decisions['non_maintainer']['rejected_approval_rate']*100:.1f}%")
        print()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate novel interpretations')
    parser.add_argument('--data-dir', type=Path, default=Path(__file__).parent.parent.parent / 'data',
                       help='Data directory')
    parser.add_argument('--output', type=Path, default=Path(__file__).parent.parent.parent / 'findings' / 'novel_interpretations.json',
                       help='Output JSON file')
    
    args = parser.parse_args()
    
    analyzer = NovelInterpretations(args.data_dir)
    results = analyzer.run_all_analyses()
    analyzer.print_results(results)
    
    # Save results
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nResults saved to: {args.output}")


if __name__ == '__main__':
    main()
