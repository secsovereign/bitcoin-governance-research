#!/usr/bin/env python3
"""
Interdisciplinary Analysis: Applying Multiple Disciplinary Frameworks

Applies analyses from:
- Network Science (centrality, clustering, communities)
- Game Theory (cooperation patterns, prisoner's dilemma)
- Information Theory (entropy, information flow)
- Organizational Behavior (decision-making, group dynamics)
- Political Science (coalition formation, voting patterns)
- Complex Systems (emergence, self-organization)
"""

import json
import sys
import math
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Any, Set, Tuple
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.utils.load_prs_with_merged_by import load_prs_with_merged_by

class InterdisciplinaryAnalyzer:
    """Apply multiple disciplinary frameworks."""
    
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
    
    def network_centrality_analysis(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Network Science: Calculate centrality metrics."""
        print("Analyzing network centrality...")
        
        # Build merge network
        merge_edges = defaultdict(lambda: defaultdict(int))
        review_edges = defaultdict(lambda: defaultdict(int))
        nodes = set()
        
        for pr in prs:
            if not pr.get('merged', False):
                continue
            
            author = (pr.get('author') or '').lower()
            merged_by = (pr.get('merged_by') or '').lower()
            
            if author and merged_by:
                nodes.add(author)
                nodes.add(merged_by)
                merge_edges[merged_by][author] += 1
            
            # Review network
            for review in pr.get('reviews', []):
                reviewer = (review.get('author') or '').lower()
                if reviewer and author:
                    nodes.add(reviewer)
                    nodes.add(author)
                    review_edges[reviewer][author] += 1
        
        # Calculate degree centrality (simple: number of connections)
        merge_degree = {node: sum(merge_edges[node].values()) for node in nodes}
        review_degree = {node: sum(review_edges[node].values()) for node in nodes}
        
        # Calculate betweenness (simplified: nodes that connect many others)
        # For merge network: nodes that merge many different authors
        merge_betweenness = {}
        for merger, authors in merge_edges.items():
            merge_betweenness[merger] = len(authors)  # Unique authors merged
        
        # Top central nodes
        top_merge_centrality = sorted(merge_degree.items(), key=lambda x: x[1], reverse=True)[:10]
        top_review_centrality = sorted(review_degree.items(), key=lambda x: x[1], reverse=True)[:10]
        top_betweenness = sorted(merge_betweenness.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'merge_centrality': dict(top_merge_centrality),
            'review_centrality': dict(top_review_centrality),
            'betweenness': dict(top_betweenness),
            'total_nodes': len(nodes)
        }
    
    def game_theory_cooperation(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Game Theory: Analyze cooperation patterns."""
        print("Analyzing cooperation patterns...")
        
        # Track mutual cooperation: A reviews B's PR, B reviews A's PR
        mutual_cooperation = defaultdict(int)
        one_way_cooperation = defaultdict(int)
        
        maintainer_list = [m.lower() for m in self.maintainers]
        
        for pr in prs:
            author = (pr.get('author') or '').lower()
            if author not in maintainer_list:
                continue
            
            reviewers = {(r.get('author') or '').lower() for r in pr.get('reviews', []) if r.get('author')}
            reviewers = {r for r in reviewers if r in maintainer_list and r != author}
            
            for reviewer in reviewers:
                # Check if author also reviews reviewer's PRs
                author_reviews_reviewer = False
                for other_pr in prs:
                    if (other_pr.get('author') or '').lower() == reviewer:
                        other_reviewers = {(r.get('author') or '').lower() for r in other_pr.get('reviews', []) if r.get('author')}
                        if author in other_reviewers:
                            author_reviews_reviewer = True
                            break
                
                if author_reviews_reviewer:
                    pair_key = f"{author}_{reviewer}"
                    mutual_cooperation[pair_key] += 1
                else:
                    pair_key = f"{author}_{reviewer}"
                    one_way_cooperation[pair_key] += 1
        
        cooperation_rate = len(mutual_cooperation) / (len(mutual_cooperation) + len(one_way_cooperation)) if (mutual_cooperation or one_way_cooperation) else 0
        
        return {
            'mutual_cooperation_pairs': len(mutual_cooperation),
            'one_way_cooperation_pairs': len(one_way_cooperation),
            'cooperation_rate': cooperation_rate,
            'top_mutual_pairs': dict(sorted(mutual_cooperation.items(), key=lambda x: x[1], reverse=True)[:10])
        }
    
    def information_theory_entropy(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Information Theory: Calculate entropy of distributions."""
        print("Analyzing information entropy...")
        
        # Entropy of merge distribution (how concentrated are merges?)
        merge_counts = Counter()
        for pr in prs:
            if pr.get('merged', False):
                merged_by = (pr.get('merged_by') or '').lower()
                if merged_by:
                    merge_counts[merged_by] += 1
        
        # Calculate Shannon entropy
        total_merges = sum(merge_counts.values())
        if total_merges > 0:
            merge_entropy = -sum((count/total_merges) * math.log2(count/total_merges) 
                                for count in merge_counts.values() if count > 0)
            max_entropy = math.log2(len(merge_counts)) if merge_counts else 0
            normalized_entropy = merge_entropy / max_entropy if max_entropy > 0 else 0
        else:
            merge_entropy = 0
            normalized_entropy = 0
        
        # Entropy of review distribution
        review_counts = Counter()
        for pr in prs:
            for review in pr.get('reviews', []):
                reviewer = (review.get('author') or '').lower()
                if reviewer:
                    review_counts[reviewer] += 1
        
        total_reviews = sum(review_counts.values())
        if total_reviews > 0:
            review_entropy = -sum((count/total_reviews) * math.log2(count/total_reviews)
                                 for count in review_counts.values() if count > 0)
            max_review_entropy = math.log2(len(review_counts)) if review_counts else 0
            normalized_review_entropy = review_entropy / max_review_entropy if max_review_entropy > 0 else 0
        else:
            review_entropy = 0
            normalized_review_entropy = 0
        
        return {
            'merge_entropy': merge_entropy,
            'merge_normalized_entropy': normalized_entropy,
            'merge_unique_actors': len(merge_counts),
            'review_entropy': review_entropy,
            'review_normalized_entropy': normalized_review_entropy,
            'review_unique_actors': len(review_counts),
            'interpretation': {
                'merge': 'Low entropy = concentrated power, High entropy = distributed power',
                'review': 'Low entropy = few reviewers dominate, High entropy = distributed reviewing'
            }
        }
    
    def organizational_decision_patterns(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Organizational Behavior: Analyze decision-making patterns."""
        print("Analyzing decision patterns...")
        
        # Decision speed by complexity (file count as proxy)
        decisions_by_complexity = defaultdict(list)
        
        for pr in prs:
            if not pr.get('merged', False):
                continue
            
            files_count = len(pr.get('files', []))
            created = pr.get('created_at')
            merged = pr.get('merged_at')
            
            if created and merged:
                try:
                    created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    merged_dt = datetime.fromisoformat(merged.replace('Z', '+00:00'))
                    days = (merged_dt - created_dt).total_seconds() / 86400
                    
                    if files_count <= 5:
                        complexity = 'low'
                    elif files_count <= 15:
                        complexity = 'medium'
                    else:
                        complexity = 'high'
                    
                    decisions_by_complexity[complexity].append(days)
                except:
                    pass
        
        # Decision consistency (variance in decision times)
        decision_stats = {}
        for complexity, times in decisions_by_complexity.items():
            if times:
                avg = sum(times) / len(times)
                variance = sum((t - avg) ** 2 for t in times) / len(times)
                std_dev = math.sqrt(variance)
                decision_stats[complexity] = {
                    'avg_days': avg,
                    'std_dev': std_dev,
                    'coefficient_of_variation': std_dev / avg if avg > 0 else 0,
                    'count': len(times)
                }
        
        return decision_stats
    
    def coalition_formation_analysis(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Political Science: Analyze coalition formation patterns."""
        print("Analyzing coalition patterns...")
        
        # Identify "coalitions" - groups that frequently merge each other's PRs
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
        
        # Find reciprocal relationships (A merges B, B merges A)
        coalitions = []
        maintainer_list = [m.lower() for m in self.maintainers]
        
        for i, m1 in enumerate(maintainer_list):
            for m2 in maintainer_list[i+1:]:
                m1_merges_m2 = merge_relationships[m1].get(m2, 0)
                m2_merges_m1 = merge_relationships[m2].get(m1, 0)
                
                if m1_merges_m2 > 0 and m2_merges_m1 > 0:
                    # Reciprocal relationship = potential coalition
                    total_interaction = m1_merges_m2 + m2_merges_m1
                    coalitions.append({
                        'pair': f"{m1}_{m2}",
                        'm1': m1,
                        'm2': m2,
                        'm1_merges_m2': m1_merges_m2,
                        'm2_merges_m1': m2_merges_m1,
                        'total': total_interaction,
                        'reciprocity': min(m1_merges_m2, m2_merges_m1) / max(m1_merges_m2, m2_merges_m1) if max(m1_merges_m2, m2_merges_m1) > 0 else 0
                    })
        
        coalitions.sort(key=lambda x: x['total'], reverse=True)
        
        return {
            'coalition_pairs': len(coalitions),
            'top_coalitions': coalitions[:10],
            'avg_reciprocity': sum(c['reciprocity'] for c in coalitions) / len(coalitions) if coalitions else 0
        }
    
    def complex_systems_emergence(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Complex Systems: Analyze emergent patterns."""
        print("Analyzing emergent patterns...")
        
        # Power law distribution check (many complex systems show power law distributions)
        merge_counts = Counter()
        for pr in prs:
            if pr.get('merged', False):
                merged_by = (pr.get('merged_by') or '').lower()
                if merged_by:
                    merge_counts[merged_by] += 1
        
        # Check if distribution follows power law (few have many, many have few)
        sorted_counts = sorted(merge_counts.values(), reverse=True)
        
        # Calculate if top 20% have 80% of merges (Pareto principle)
        total = sum(sorted_counts)
        top_20_pct_count = int(len(sorted_counts) * 0.2)
        top_20_pct_merges = sum(sorted_counts[:top_20_pct_count]) if top_20_pct_count > 0 else 0
        pareto_ratio = top_20_pct_merges / total if total > 0 else 0
        
        # Self-organization metric: How much does individual behavior vary?
        maintainer_self_merge_rates = {}
        for pr in prs:
            if not pr.get('merged', False):
                continue
            
            author = (pr.get('author') or '').lower()
            merged_by = (pr.get('merged_by') or '').lower()
            
            if author in [m.lower() for m in self.maintainers]:
                if author not in maintainer_self_merge_rates:
                    maintainer_self_merge_rates[author] = {'total': 0, 'self': 0}
                
                maintainer_self_merge_rates[author]['total'] += 1
                if merged_by == author:
                    maintainer_self_merge_rates[author]['self'] += 1
        
        # Calculate variance in self-merge rates
        rates = [stats['self'] / stats['total'] for stats in maintainer_self_merge_rates.values() if stats['total'] >= 50]
        if rates:
            avg_rate = sum(rates) / len(rates)
            variance = sum((r - avg_rate) ** 2 for r in rates) / len(rates)
            std_dev = math.sqrt(variance)
            coefficient_of_variation = std_dev / avg_rate if avg_rate > 0 else 0
        else:
            coefficient_of_variation = 0
        
        return {
            'pareto_ratio': pareto_ratio,
            'follows_pareto': pareto_ratio >= 0.8,
            'self_organization_variance': coefficient_of_variation,
            'interpretation': {
                'pareto': 'High ratio (>0.8) suggests power law distribution typical of complex systems',
                'variance': 'High variance suggests lack of self-organization/emergent norms'
            }
        }
    
    def run_all_analyses(self) -> Dict[str, Any]:
        """Run all interdisciplinary analyses."""
        print("="*80)
        print("INTERDISCIPLINARY ANALYSIS")
        print("="*80)
        print()
        
        prs = self.load_prs()
        print(f"Loaded {len(prs):,} PRs")
        print()
        
        results = {
            'network_centrality': self.network_centrality_analysis(prs),
            'game_theory_cooperation': self.game_theory_cooperation(prs),
            'information_entropy': self.information_theory_entropy(prs),
            'organizational_decisions': self.organizational_decision_patterns(prs),
            'coalition_formation': self.coalition_formation_analysis(prs),
            'complex_systems': self.complex_systems_emergence(prs),
            'analysis_date': datetime.now().isoformat()
        }
        
        return results
    
    def print_results(self, results: Dict[str, Any]):
        """Print results."""
        print("="*80)
        print("INTERDISCIPLINARY ANALYSIS RESULTS")
        print("="*80)
        print()
        
        # Network centrality
        print("NETWORK SCIENCE: Centrality")
        print("-" * 80)
        centrality = results['network_centrality']
        print(f"Total nodes: {centrality['total_nodes']:,}")
        print("Top merge centrality:")
        for node, score in list(centrality['merge_centrality'].items())[:5]:
            print(f"  {node}: {score}")
        print("Top betweenness (connectors):")
        for node, score in list(centrality['betweenness'].items())[:5]:
            print(f"  {node}: {score} unique authors merged")
        print()
        
        # Game theory
        print("GAME THEORY: Cooperation")
        print("-" * 80)
        coop = results['game_theory_cooperation']
        print(f"Mutual cooperation pairs: {coop['mutual_cooperation_pairs']}")
        print(f"One-way cooperation pairs: {coop['one_way_cooperation_pairs']}")
        print(f"Cooperation rate: {coop['cooperation_rate']*100:.1f}%")
        print()
        
        # Information theory
        print("INFORMATION THEORY: Entropy")
        print("-" * 80)
        entropy = results['information_entropy']
        print(f"Merge entropy: {entropy['merge_entropy']:.2f} (normalized: {entropy['merge_normalized_entropy']:.2f})")
        print(f"Review entropy: {entropy['review_entropy']:.2f} (normalized: {entropy['review_normalized_entropy']:.2f})")
        print(f"Interpretation: {entropy['interpretation']['merge']}")
        print()
        
        # Organizational behavior
        print("ORGANIZATIONAL BEHAVIOR: Decision Patterns")
        print("-" * 80)
        org = results['organizational_decisions']
        for complexity, stats in org.items():
            print(f"{complexity.capitalize()} complexity:")
            print(f"  Avg decision time: {stats['avg_days']:.1f} days")
            print(f"  Consistency (CV): {stats['coefficient_of_variation']:.2f}")
        print()
        
        # Coalition formation
        print("POLITICAL SCIENCE: Coalition Formation")
        print("-" * 80)
        coal = results['coalition_formation']
        print(f"Coalition pairs: {coal['coalition_pairs']}")
        print(f"Average reciprocity: {coal['avg_reciprocity']:.2f}")
        print("Top coalitions:")
        for c in coal['top_coalitions'][:5]:
            if 'm1' in c and 'm2' in c:
                m1, m2 = c['m1'], c['m2']
            else:
                parts = c['pair'].split('_')
                m1 = parts[0] if len(parts) > 0 else ''
                m2 = parts[1] if len(parts) > 1 else ''
            print(f"  {m1} ↔ {m2}: {c['total']} interactions")
        print()
        
        # Complex systems
        print("COMPLEX SYSTEMS: Emergent Patterns")
        print("-" * 80)
        complex_sys = results['complex_systems']
        print(f"Pareto ratio (80/20): {complex_sys['pareto_ratio']:.2f}")
        print(f"Follows Pareto principle: {complex_sys['follows_pareto']}")
        print(f"Self-organization variance: {complex_sys['self_organization_variance']:.2f}")
        print()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Interdisciplinary analysis')
    parser.add_argument('--data-dir', type=Path, default=Path(__file__).parent.parent.parent / 'data',
                       help='Data directory')
    parser.add_argument('--output', type=Path, default=Path(__file__).parent.parent.parent / 'findings' / 'interdisciplinary_analysis.json',
                       help='Output JSON file')
    
    args = parser.parse_args()
    
    analyzer = InterdisciplinaryAnalyzer(args.data_dir)
    results = analyzer.run_all_analyses()
    analyzer.print_results(results)
    
    # Save results
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nResults saved to: {args.output}")


if __name__ == '__main__':
    main()
