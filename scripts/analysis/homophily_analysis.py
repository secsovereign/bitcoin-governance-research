#!/usr/bin/env python3
"""
Homophily Networks Analysis

Framework: "Birds of a feather" - networks cluster by similarity
Application: Analyze reviewer-author pairs for institutional/geographic clustering
Expected insight: Reviews concentrated within same employers/regions = institutional capture patterns
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict, Counter
try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger
from src.utils.paths import get_analysis_dir, get_data_dir

logger = setup_logger()


class HomophilyAnalyzer:
    """Analyzer for homophily patterns in review networks."""
    
    def __init__(self):
        self.data_dir = get_data_dir()
        self.analysis_dir = get_analysis_dir()
        self.processed_dir = self.data_dir / 'processed'
        self.output_dir = self.analysis_dir / 'homophily_analysis'
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def run_analysis(self):
        """Run homophily analysis."""
        logger.info("=" * 60)
        logger.info("Homophily Networks Analysis")
        logger.info("=" * 60)
        
        prs = self._load_enriched_prs()
        if not prs:
            logger.error("No PR data found")
            return
        
        logger.info(f"Loaded {len(prs)} PRs")
        
        # Build review network
        review_network = self._build_review_network(prs)
        
        # Analyze homophily patterns
        homophily_results = self._analyze_homophily(review_network, prs)
        
        # Analyze clustering by maintainer status
        maintainer_clustering = self._analyze_maintainer_clustering(review_network, prs)
        
        # Temporal analysis
        temporal_homophily = self._analyze_temporal_homophily(prs)
        
        # Save results
        results = {
            'analysis_name': 'homophily_networks',
            'version': '1.0',
            'metadata': {
                'total_prs': len(prs),
                'network_nodes': len(review_network.nodes()) if HAS_NETWORKX else len(review_network.get('nodes', set())),
                'network_edges': len(review_network.edges()) if HAS_NETWORKX else len(review_network.get('edges', []))
            },
            'data': {
                'homophily_metrics': homophily_results,
                'maintainer_clustering': maintainer_clustering,
                'temporal_analysis': temporal_homophily
            }
        }
        
        output_file = self.output_dir / 'homophily_analysis.json'
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Results saved to {output_file}")
        logger.info("Homophily analysis complete")
    
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
    
    def _build_review_network(self, prs: List[Dict[str, Any]]):
        """Build directed graph of reviewer-author relationships."""
        if HAS_NETWORKX:
            G = nx.DiGraph()
        else:
            # Simplified network representation
            G = {'nodes': set(), 'edges': []}
        
        for pr in prs:
            author = pr.get('author') or pr.get('user', {}).get('login', '')
            if not author:
                continue
            
            if HAS_NETWORKX:
                G.add_node(author, node_type='author')
            else:
                G['nodes'].add(author)
            
            reviews = pr.get('reviews', [])
            for review in reviews:
                reviewer = review.get('author') or review.get('user', {}).get('login', '')
                if not reviewer or reviewer == author:
                    continue
                
                if HAS_NETWORKX:
                    G.add_node(reviewer, node_type='reviewer')
                    if G.has_edge(reviewer, author):
                        G[reviewer][author]['weight'] += 1
                        G[reviewer][author]['review_count'] += 1
                    else:
                        G.add_edge(reviewer, author, weight=1, review_count=1)
                else:
                    G['nodes'].add(reviewer)
                    G['edges'].append((reviewer, author))
        
        return G
    
    def _analyze_homophily(self, network, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze homophily patterns in review network."""
        # Calculate homophily by maintainer status
        maintainer_status = {}
        
        # Identify maintainers from PR data
        for pr in prs:
            maintainer_involvement = pr.get('maintainer_involvement', {})
            author = pr.get('author') or pr.get('user', {}).get('login', '')
            if author:
                maintainer_status[author] = maintainer_involvement.get('author_is_maintainer', False)
        
        # Calculate homophily metrics
        same_status_edges = 0
        different_status_edges = 0
        maintainer_to_maintainer = 0
        non_maintainer_to_non_maintainer = 0
        maintainer_to_non_maintainer = 0
        non_maintainer_to_maintainer = 0
        
        if HAS_NETWORKX:
            edges = network.edges()
        else:
            edges = network.get('edges', [])
        
        for edge in edges:
            if HAS_NETWORKX:
                reviewer, author = edge
            else:
                reviewer, author = edge
            
            reviewer_is_maintainer = maintainer_status.get(reviewer, False)
            author_is_maintainer = maintainer_status.get(author, False)
            
            if reviewer_is_maintainer == author_is_maintainer:
                same_status_edges += 1
                if reviewer_is_maintainer:
                    maintainer_to_maintainer += 1
                else:
                    non_maintainer_to_non_maintainer += 1
            else:
                different_status_edges += 1
                if reviewer_is_maintainer:
                    maintainer_to_non_maintainer += 1
                else:
                    non_maintainer_to_maintainer += 1
        
        total_edges = len(network.edges()) if HAS_NETWORKX else len(network.get('edges', []))
        homophily_coefficient = same_status_edges / total_edges if total_edges > 0 else 0
        
        return {
            'homophily_coefficient': homophily_coefficient,
            'same_status_edges': same_status_edges,
            'different_status_edges': different_status_edges,
            'maintainer_to_maintainer': maintainer_to_maintainer,
            'non_maintainer_to_non_maintainer': non_maintainer_to_non_maintainer,
            'maintainer_to_non_maintainer': maintainer_to_non_maintainer,
            'non_maintainer_to_maintainer': non_maintainer_to_maintainer,
            'interpretation': self._interpret_homophily(homophily_coefficient)
        }
    
    def _interpret_homophily(self, coefficient: float) -> str:
        """Interpret homophily coefficient."""
        if coefficient > 0.7:
            return "Strong homophily - reviews highly clustered by maintainer status"
        elif coefficient > 0.5:
            return "Moderate homophily - some clustering by maintainer status"
        else:
            return "Weak homophily - reviews not strongly clustered by maintainer status"
    
    def _analyze_maintainer_clustering(self, network, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze clustering of maintainers in review network."""
        # Identify maintainers
        maintainers = set()
        for pr in prs:
            maintainer_involvement = pr.get('maintainer_involvement', {})
            author = pr.get('author') or pr.get('user', {}).get('login', '')
            if author and maintainer_involvement.get('author_is_maintainer', False):
                maintainers.add(author)
        
        # Calculate clustering coefficient for maintainers
        if HAS_NETWORKX:
            maintainer_subgraph = network.subgraph(maintainers)
            if len(maintainer_subgraph.nodes()) > 0:
                clustering_coefficient = nx.average_clustering(maintainer_subgraph.to_undirected())
            else:
                clustering_coefficient = 0
        else:
            # Simplified clustering calculation
            maintainer_edges = [e for e in network.get('edges', []) if e[0] in maintainers and e[1] in maintainers]
            total_maintainer_connections = len(maintainers) * (len(maintainers) - 1)
            clustering_coefficient = len(maintainer_edges) / total_maintainer_connections if total_maintainer_connections > 0 else 0
        
        # Calculate maintainer review concentration
        maintainer_reviews = 0
        total_reviews = 0
        
        edges = network.edges() if HAS_NETWORKX else network.get('edges', [])
        for edge in edges:
            if HAS_NETWORKX:
                reviewer, author = edge
                weight = network[reviewer][author].get('weight', 1)
            else:
                reviewer, author = edge
                weight = 1
            total_reviews += weight
            if reviewer in maintainers:
                maintainer_reviews += weight
        
        maintainer_review_concentration = maintainer_reviews / total_reviews if total_reviews > 0 else 0
        
        return {
            'maintainer_count': len(maintainers),
            'clustering_coefficient': clustering_coefficient,
            'maintainer_review_concentration': maintainer_review_concentration,
            'interpretation': 'Higher clustering = maintainers review each other more'
        }
    
    def _analyze_temporal_homophily(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze homophily patterns over time."""
        by_year = defaultdict(list)
        
        for pr in prs:
            created_at = pr.get('created_at', '')
            if created_at:
                try:
                    year = int(created_at[:4])
                    by_year[year].append(pr)
                except:
                    continue
        
        temporal_results = {}
        
        for year in sorted(by_year.keys()):
            year_prs = by_year[year]
            if len(year_prs) < 10:
                continue
            
            # Build network for this year
            year_network = self._build_review_network(year_prs)
            
            # Calculate homophily
            homophily = self._analyze_homophily(year_network, year_prs)
            
            temporal_results[year] = {
                'pr_count': len(year_prs),
                'homophily_coefficient': homophily['homophily_coefficient'],
                'maintainer_to_maintainer': homophily['maintainer_to_maintainer']
            }
        
        return temporal_results


def main():
    analyzer = HomophilyAnalyzer()
    analyzer.run_analysis()


if __name__ == '__main__':
    main()

