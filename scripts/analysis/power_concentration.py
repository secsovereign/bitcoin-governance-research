#!/usr/bin/env python3
"""
Power Concentration Analysis - Quantify power concentration in Bitcoin Core governance.

Analyzes:
1. Merge authority concentration (who can merge PRs)
2. Review influence concentration
3. Release signing authority concentration
4. Contributor concentration
5. Combined power metrics
6. Network centrality
7. Temporal evolution of power concentration
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
from src.utils.network_analysis import NetworkAnalyzer
from src.schemas.analysis_results import create_result_template, validate_result, POWER_CONCENTRATION_SCHEMA

logger = setup_logger()


class PowerConcentrationAnalyzer:
    """Analyzer for power concentration in Bitcoin Core governance."""
    
    def __init__(self):
        """Initialize analyzer."""
        self.data_dir = get_data_dir()
        self.processed_dir = self.data_dir / 'processed'
        self.analysis_dir = get_analysis_dir() / 'power_concentration'
        self.analysis_dir.mkdir(parents=True, exist_ok=True)
        
        self.stat_analyzer = StatisticalAnalyzer(random_seed=42)
        self.network_analyzer = NetworkAnalyzer()
    
    def run_analysis(self):
        """Run power concentration analysis."""
        logger.info("=" * 60)
        logger.info("Power Concentration Analysis")
        logger.info("=" * 60)
        
        # Load data
        prs = self._load_enriched_prs()
        maintainer_timeline = self._load_maintainer_timeline()
        release_signers = self._load_release_signers()
        contributors = self._load_contributors()
        identity_mappings = self._load_identity_mappings()
        
        # Analyze merge authority concentration
        merge_concentration = self._analyze_merge_authority(prs, maintainer_timeline)
        
        # Analyze review influence concentration
        review_concentration = self._analyze_review_influence(prs, maintainer_timeline)
        
        # Analyze release signing concentration
        release_concentration = self._analyze_release_signing(release_signers)
        
        # Analyze contributor concentration
        contributor_concentration = self._analyze_contributor_concentration(contributors)
        
        # Calculate combined power metrics
        combined_power = self._calculate_combined_power(
            merge_concentration,
            release_concentration,
            contributor_concentration
        )
        
        # Build and analyze networks
        network_analysis = self._analyze_networks(prs, identity_mappings, maintainer_timeline)
        
        # Analyze temporal evolution
        temporal_evolution = self._analyze_temporal_evolution(prs, maintainer_timeline)
        
        # Analyze domain expertise concentration (NEW)
        domain_concentration = self._analyze_domain_concentration(prs)
        
        # Save results
        self._save_results({
            'merge_authority': merge_concentration,
            'review_influence': review_concentration,
            'release_signing': release_concentration,
            'contributor_concentration': contributor_concentration,
            'domain_concentration': domain_concentration,
            'combined_power': combined_power,
            'network_analysis': network_analysis,
            'temporal_evolution': temporal_evolution
        })
        
        logger.info("Power concentration analysis complete")
    
    def _load_enriched_prs(self) -> List[Dict[str, Any]]:
        """Load enriched PR data with merged_by mapping."""
        from scripts.utils.load_prs_with_merged_by import load_prs_with_merged_by
        
        prs_file = self.processed_dir / 'enriched_prs.jsonl'
        
        if not prs_file.exists():
            # Fallback to cleaned PRs
            prs_file = self.processed_dir / 'cleaned_prs.jsonl'
        
        if not prs_file.exists():
            logger.warning(f"PR data not found: {prs_file}")
            return []
        
        # Load with merged_by mapping
        mapping_file = self.data_dir / 'github' / 'merged_by_mapping.jsonl'
        prs = load_prs_with_merged_by(prs_file, mapping_file if mapping_file.exists() else None)
        
        logger.info(f"Loaded {len(prs)} PRs")
        return prs
    
    def _load_maintainer_timeline(self) -> Dict[str, Any]:
        """Load maintainer timeline."""
        timeline_file = self.processed_dir / 'maintainer_timeline.json'
        
        if not timeline_file.exists():
            logger.warning(f"Maintainer timeline not found: {timeline_file}")
            return {}
        
        with open(timeline_file, 'r') as f:
            data = json.load(f)
            return data.get('maintainer_timeline', {})
    
    def _load_release_signers(self) -> List[Dict[str, Any]]:
        """Load release signer data."""
        signers_file = self.processed_dir / 'cleaned_release_signers.jsonl'
        
        if not signers_file.exists():
            logger.warning(f"Release signers not found: {signers_file}")
            return []
        
        releases = []
        with open(signers_file, 'r') as f:
            for line in f:
                releases.append(json.loads(line))
        
        return releases
    
    def _load_contributors(self) -> Dict[str, Any]:
        """Load contributors data."""
        contributors_file = self.data_dir / 'github' / 'collaborators.json'
        
        if not contributors_file.exists():
            logger.warning(f"Contributors not found: {contributors_file}")
            return {}
        
        with open(contributors_file, 'r') as f:
            data = json.load(f)
            return data
    
    def _load_identity_mappings(self) -> Dict[str, str]:
        """Load identity mappings."""
        mappings_file = get_analysis_dir() / 'user_identities' / 'identity_mappings.json'
        
        if not mappings_file.exists():
            logger.warning(f"Identity mappings not found: {mappings_file}")
            return {}
        
        with open(mappings_file, 'r') as f:
            data = json.load(f)
            # Extract GitHub to unified mapping
            github_to_unified = {}
            for unified_id, profile in data.get('unified_profiles', {}).items():
                for gh_user in profile.get('github_usernames', []):
                    github_to_unified[gh_user] = unified_id
            return github_to_unified
    
    def _analyze_merge_authority(self, prs: List[Dict[str, Any]], maintainer_timeline: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze merge authority concentration."""
        # Count merges by maintainer
        merge_counts = Counter()
        merge_by_maintainer = defaultdict(list)
        
        for pr in prs:
            if pr.get('merged') and pr.get('merged_by'):
                merger = pr['merged_by']
                merge_counts[merger] += 1
                merge_by_maintainer[merger].append(pr.get('number'))
        
        total_merges = sum(merge_counts.values())
        
        if total_merges == 0:
            return {'error': 'No merge data available'}
        
        # Calculate concentration metrics
        maintainer_shares = {k: v / total_merges for k, v in merge_counts.items()}
        sorted_shares = sorted(maintainer_shares.values(), reverse=True)
        
        # Top N shares
        top_5_share = sum(sorted_shares[:5])
        top_10_share = sum(sorted_shares[:10]) if len(sorted_shares) >= 10 else sum(sorted_shares)
        
        # Gini coefficient
        gini = self._calculate_gini(list(merge_counts.values()))
        
        # HHI
        hhi = sum(s**2 for s in maintainer_shares.values())
        
        # Top maintainers
        top_maintainers = [
            {
                'maintainer': maintainer,
                'merge_count': count,
                'share': maintainer_shares[maintainer],
                'prs': merge_by_maintainer[maintainer][:10]  # Sample PRs
            }
            for maintainer, count in merge_counts.most_common(10)
        ]
        
        return {
            'total_merges': total_merges,
            'unique_mergers': len(merge_counts),
            'gini_coefficient': gini,
            'hhi_index': hhi,
            'top_5_share': top_5_share,
            'top_10_share': top_10_share,
            'top_maintainers': top_maintainers,
            'merge_distribution': dict(merge_counts)
        }
    
    def _analyze_review_influence(self, prs: List[Dict[str, Any]], maintainer_timeline: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze review influence concentration."""
        reviewer_counts = Counter()
        reviewer_outcomes = defaultdict(lambda: {'approved': 0, 'rejected': 0, 'total': 0})
        
        for pr in prs:
            reviews = pr.get('reviews', [])
            for review in reviews:
                reviewer = review.get('author')
                if reviewer:
                    reviewer_counts[reviewer] += 1
                    reviewer_outcomes[reviewer]['total'] += 1
                    
                    state = review.get('state', '').lower()
                    if state == 'approved':
                        reviewer_outcomes[reviewer]['approved'] += 1
                    elif state in ['changes_requested', 'rejected']:
                        reviewer_outcomes[reviewer]['rejected'] += 1
        
        total_reviews = sum(reviewer_counts.values())
        
        if total_reviews == 0:
            return {'error': 'No review data available'}
        
        # Calculate influence metrics
        reviewer_shares = {k: v / total_reviews for k, v in reviewer_counts.items()}
        sorted_shares = sorted(reviewer_shares.values(), reverse=True)
        
        top_5_share = sum(sorted_shares[:5])
        gini = self._calculate_gini(list(reviewer_counts.values()))
        
        # Top reviewers
        top_reviewers = [
            {
                'reviewer': reviewer,
                'review_count': count,
                'share': reviewer_shares[reviewer],
                'approval_rate': reviewer_outcomes[reviewer]['approved'] / reviewer_outcomes[reviewer]['total'] if reviewer_outcomes[reviewer]['total'] > 0 else 0
            }
            for reviewer, count in reviewer_counts.most_common(10)
        ]
        
        return {
            'total_reviews': total_reviews,
            'unique_reviewers': len(reviewer_counts),
            'gini_coefficient': gini,
            'top_5_share': top_5_share,
            'top_reviewers': top_reviewers
        }
    
    def _analyze_release_signing(self, releases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze release signing concentration."""
        if not releases:
            return {'error': 'No release signing data available'}
        
        signed_releases = [r for r in releases if r.get('is_signed')]
        signer_counts = Counter()
        
        for release in signed_releases:
            signer = release.get('signer_email') or release.get('signer_name')
            if signer:
                signer_counts[signer] += 1
        
        total_signed = len(signed_releases)
        
        if total_signed == 0:
            return {'error': 'No signed releases'}
        
        signer_shares = {k: v / total_signed for k, v in signer_counts.items()}
        sorted_shares = sorted(signer_shares.values(), reverse=True)
        
        top_5_share = sum(sorted_shares[:5])
        gini = self._calculate_gini(list(signer_counts.values()))
        
        return {
            'total_signed': total_signed,
            'unique_signers': len(signer_counts),
            'gini_coefficient': gini,
            'top_5_share': top_5_share,
            'top_signers': [
                {'signer': signer, 'count': count, 'share': signer_shares[signer]}
                for signer, count in signer_counts.most_common(10)
            ]
        }
    
    def _analyze_contributor_concentration(self, contributors: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze contributor concentration."""
        contrib_list = contributors.get('contributors', [])
        
        if not contrib_list:
            return {'error': 'No contributor data available'}
        
        total_contributions = sum(c.get('contributions', 0) for c in contrib_list)
        
        if total_contributions == 0:
            return {'error': 'No contribution data'}
        
        contrib_shares = {c.get('login'): c.get('contributions', 0) / total_contributions for c in contrib_list}
        sorted_shares = sorted(contrib_shares.values(), reverse=True)
        
        top_5_share = sum(sorted_shares[:5])
        top_10_share = sum(sorted_shares[:10]) if len(sorted_shares) >= 10 else sum(sorted_shares)
        
        contrib_values = [c.get('contributions', 0) for c in contrib_list]
        gini = self._calculate_gini(contrib_values)
        
        return {
            'total_contributors': len(contrib_list),
            'total_contributions': total_contributions,
            'gini_coefficient': gini,
            'top_5_share': top_5_share,
            'top_10_share': top_10_share,
            'top_contributors': [
                {
                    'contributor': c.get('login'),
                    'contributions': c.get('contributions', 0),
                    'share': contrib_shares[c.get('login')]
                }
                for c in contrib_list[:10]
            ]
        }
    
    def _calculate_combined_power(
        self,
        merge_concentration: Dict[str, Any],
        release_concentration: Dict[str, Any],
        contributor_concentration: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate combined power metrics."""
        # Normalize metrics to 0-1 scale for combination
        metrics = {}
        
        if 'gini_coefficient' in merge_concentration:
            metrics['merge_gini'] = merge_concentration['gini_coefficient']
        
        if 'gini_coefficient' in release_concentration:
            metrics['release_gini'] = release_concentration['gini_coefficient']
        
        if 'gini_coefficient' in contributor_concentration:
            metrics['contributor_gini'] = contributor_concentration['gini_coefficient']
        
        # Average Gini (simple combination)
        gini_values = [v for v in metrics.values() if isinstance(v, (int, float)) and 0 <= v <= 1]
        avg_gini = sum(gini_values) / len(gini_values) if gini_values else None
        
        return {
            'individual_metrics': metrics,
            'average_gini': avg_gini,
            'interpretation': 'Higher Gini = more concentration'
        }
    
    def _analyze_networks(
        self,
        prs: List[Dict[str, Any]],
        identity_mappings: Dict[str, str],
        maintainer_timeline: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build and analyze influence networks."""
        # Build review network
        nodes = set()
        edges = []
        
        for pr in prs:
            author = pr.get('author')
            if not author:
                continue
            
            author_unified = identity_mappings.get(author, author)
            nodes.add(author_unified)
            
            reviews = pr.get('reviews', [])
            for review in reviews:
                reviewer = review.get('author')
                if reviewer:
                    reviewer_unified = identity_mappings.get(reviewer, reviewer)
                    nodes.add(reviewer_unified)
                    edges.append({
                        'source': reviewer_unified,
                        'target': author_unified,
                        'weight': 1,
                        'type': 'review'
                    })
        
        # Build network graph directly
        import networkx as nx
        G = nx.DiGraph()
        G.add_nodes_from(nodes)
        for edge in edges:
            G.add_edge(edge['source'], edge['target'], weight=edge.get('weight', 1))
        
        # Calculate centrality using NetworkAnalyzer methods
        centrality = {}
        if len(G.nodes()) > 0:
            try:
                betweenness = nx.betweenness_centrality(G)
                eigenvector = nx.eigenvector_centrality(G, max_iter=1000)
                pagerank = nx.pagerank(G)
                
                for node in G.nodes():
                    centrality[node] = {
                        'betweenness': betweenness.get(node, 0),
                        'eigenvector': eigenvector.get(node, 0),
                        'pagerank': pagerank.get(node, 0)
                    }
            except Exception as e:
                logger.warning(f"Error calculating centrality: {e}")
                centrality = {}
        
        # Top nodes by centrality
        top_nodes = {}
        for metric in ['betweenness', 'eigenvector', 'pagerank']:
            if centrality:
                sorted_nodes = sorted(
                    [(node, scores.get(metric, 0)) for node, scores in centrality.items()],
                    key=lambda x: x[1],
                    reverse=True
                )[:10]
                top_nodes[metric] = [{'node': node, 'score': score} for node, score in sorted_nodes]
        
        return {
            'network_size': {'nodes': len(nodes), 'edges': len(edges)},
            'centrality_metrics': top_nodes,
            'full_centrality': centrality
        }
    
    def _analyze_temporal_evolution(
        self,
        prs: List[Dict[str, Any]],
        maintainer_timeline: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze temporal evolution of power concentration."""
        # Group PRs by year
        merges_by_year = defaultdict(Counter)
        
        for pr in prs:
            if pr.get('merged') and pr.get('merged_by') and pr.get('merged_at'):
                try:
                    merge_date = datetime.fromisoformat(pr['merged_at'].replace('Z', '+00:00'))
                    year = merge_date.year
                    merger = pr['merged_by']
                    merges_by_year[year][merger] += 1
                except Exception:
                    continue
        
        # Calculate Gini by year
        temporal_data = []
        for year in sorted(merges_by_year.keys()):
            year_merges = merges_by_year[year]
            if year_merges:
                gini = self._calculate_gini(list(year_merges.values()))
                total = sum(year_merges.values())
                unique_mergers = len(year_merges)
                
                temporal_data.append({
                    'year': year,
                    'total_merges': total,
                    'unique_mergers': unique_mergers,
                    'gini_coefficient': gini
                })
        
        return {
            'by_year': temporal_data,
            'trend': 'increasing' if len(temporal_data) > 1 and temporal_data[-1]['gini_coefficient'] > temporal_data[0]['gini_coefficient'] else 'stable'
        }
    
    def _analyze_domain_concentration(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze domain expertise concentration."""
        # Map contributors to domains
        contributor_domains = defaultdict(set)
        domain_contributors = defaultdict(set)
        
        for pr in prs:
            author = pr.get('author')
            domain_info = pr.get('domain_expertise', {})
            domains = domain_info.get('domains', [])
            
            if author and domains:
                for domain in domains:
                    contributor_domains[author].add(domain)
                    domain_contributors[domain].add(author)
        
        # Calculate multi-domain expertise
        multi_domain_contributors = [
            author for author, domains in contributor_domains.items()
            if len(domains) > 1
        ]
        
        # Domain concentration (how many contributors per domain)
        domain_concentration = {
            domain: len(contributors)
            for domain, contributors in domain_contributors.items()
        }
        
        return {
            'total_contributors_with_domains': len(contributor_domains),
            'multi_domain_contributors': len(multi_domain_contributors),
            'multi_domain_rate': len(multi_domain_contributors) / len(contributor_domains) if contributor_domains else 0,
            'domain_concentration': domain_concentration,
            'top_domains': sorted(domain_concentration.items(), key=lambda x: x[1], reverse=True)[:10]
        }
    
    def _calculate_gini(self, values: List[float]) -> float:
        """Calculate Gini coefficient."""
        if not values or len(values) == 0:
            return 0.0
        
        values = sorted([float(v) for v in values if v > 0])
        n = len(values)
        
        if n == 0:
            return 0.0
        
        cumsum = 0
        for i, value in enumerate(values):
            cumsum += value * (i + 1)
        
        gini = (2 * cumsum) / (n * sum(values)) - (n + 1) / n
        
        return max(0.0, min(1.0, gini))  # Clamp to [0, 1]
    
    def _save_results(self, results: Dict[str, Any]):
        """Save analysis results."""
        # Create result template
        result = create_result_template('power_concentration_analysis', '1.0.0')
        result['metadata']['timestamp'] = datetime.now().isoformat()
        result['metadata']['data_sources'] = [
            'data/processed/enriched_prs.jsonl',
            'data/processed/maintainer_timeline.json',
            'data/releases/release_signers.jsonl',
            'data/github/collaborators.json'
        ]
        result['data'] = results
        
        # Save to file
        output_file = self.analysis_dir / 'power_concentration_analysis.json'
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        logger.info(f"Results saved to {output_file}")
        
        # Validate against schema
        is_valid, error = validate_result(result, POWER_CONCENTRATION_SCHEMA)
        if not is_valid:
            logger.warning(f"Schema validation warning: {error}")
        
        # Generate summary
        self._generate_summary(results)
    
    def _generate_summary(self, results: Dict[str, Any]):
        """Generate analysis summary."""
        merge = results.get('merge_authority', {})
        release = results.get('release_signing', {})
        contributor = results.get('contributor_concentration', {})
        
        logger.info("Power Concentration Analysis Summary:")
        if 'gini_coefficient' in merge:
            logger.info(f"  Merge Authority Gini: {merge['gini_coefficient']:.3f}")
        if 'gini_coefficient' in release:
            logger.info(f"  Release Signing Gini: {release['gini_coefficient']:.3f}")
        if 'gini_coefficient' in contributor:
            logger.info(f"  Contributor Gini: {contributor['gini_coefficient']:.3f}")


def main():
    """Main entry point."""
    analyzer = PowerConcentrationAnalyzer()
    analyzer.run_analysis()
    return 0


if __name__ == '__main__':
    sys.exit(main())

