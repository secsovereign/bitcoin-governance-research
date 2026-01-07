"""Network analysis utilities with NetworkX wrappers."""

import networkx as nx
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict

from src.utils.logger import setup_logger

logger = setup_logger()


class NetworkAnalyzer:
    """Network analysis utilities for governance analysis."""
    
    def __init__(self):
        """Initialize network analyzer."""
        self.graph = nx.DiGraph()  # Directed graph for influence relationships
    
    def build_review_network(
        self,
        prs: pd.DataFrame,
        identity_mappings: Dict[str, str]
    ) -> nx.DiGraph:
        """
        Build network from PR reviews.
        
        Args:
            prs: DataFrame with PR data including reviews
            identity_mappings: Map from platform-specific IDs to unified IDs
        
        Returns:
            Directed graph where edge (A, B) means A reviewed B's PRs
        """
        self.graph = nx.DiGraph()
        
        for _, pr in prs.iterrows():
            pr_author = identity_mappings.get(pr.get('author'), pr.get('author'))
            if not pr_author:
                continue
            
            # Add PR author as node
            self.graph.add_node(pr_author, node_type='developer')
            
            # Add reviewers
            reviews = pr.get('reviews', [])
            for review in reviews:
                reviewer = identity_mappings.get(review.get('author'), review.get('author'))
                if not reviewer or reviewer == pr_author:
                    continue
                
                # Add reviewer as node
                self.graph.add_node(reviewer, node_type='developer')
                
                # Add edge: reviewer -> PR author (reviewer reviews author's PR)
                if self.graph.has_edge(reviewer, pr_author):
                    self.graph[reviewer][pr_author]['weight'] += 1
                    self.graph[reviewer][pr_author]['pr_count'] += 1
                else:
                    self.graph.add_edge(
                        reviewer,
                        pr_author,
                        weight=1,
                        pr_count=1,
                        review_type=review.get('state', 'unknown')
                    )
        
        return self.graph
    
    def build_merge_network(
        self,
        prs: pd.DataFrame,
        identity_mappings: Dict[str, str]
    ) -> nx.DiGraph:
        """
        Build network from PR merges.
        
        Args:
            prs: DataFrame with PR data including merge information
            identity_mappings: Map from platform-specific IDs to unified IDs
        
        Returns:
            Directed graph where edge (A, B) means A merged B's PRs
        """
        self.graph = nx.DiGraph()
        
        merged_prs = prs[prs['state'] == 'merged']
        
        for _, pr in merged_prs.iterrows():
            pr_author = identity_mappings.get(pr.get('author'), pr.get('author'))
            merger = identity_mappings.get(pr.get('merged_by'), pr.get('merged_by'))
            
            if not pr_author or not merger or pr_author == merger:
                continue
            
            # Add nodes
            self.graph.add_node(pr_author, node_type='developer')
            self.graph.add_node(merger, node_type='maintainer')
            
            # Add edge: merger -> PR author (merger merged author's PR)
            if self.graph.has_edge(merger, pr_author):
                self.graph[merger][pr_author]['weight'] += 1
                self.graph[merger][pr_author]['merge_count'] += 1
            else:
                self.graph.add_edge(
                    merger,
                    pr_author,
                    weight=1,
                    merge_count=1
                )
        
        return self.graph
    
    def build_communication_network(
        self,
        communications: List[Dict[str, Any]],
        identity_mappings: Dict[str, str]
    ) -> nx.DiGraph:
        """
        Build network from communication patterns (comments, replies).
        
        Args:
            communications: List of communication records with author and reply_to fields
            identity_mappings: Map from platform-specific IDs to unified IDs
        
        Returns:
            Directed graph where edge (A, B) means A replied to B
        """
        self.graph = nx.DiGraph()
        
        for comm in communications:
            author = identity_mappings.get(comm.get('author'), comm.get('author'))
            reply_to = identity_mappings.get(comm.get('reply_to'), comm.get('reply_to'))
            
            if not author:
                continue
            
            self.graph.add_node(author, node_type='participant')
            
            if reply_to and reply_to != author:
                self.graph.add_node(reply_to, node_type='participant')
                
                if self.graph.has_edge(author, reply_to):
                    self.graph[author][reply_to]['weight'] += 1
                    self.graph[author][reply_to]['message_count'] += 1
                else:
                    self.graph.add_edge(
                        author,
                        reply_to,
                        weight=1,
                        message_count=1
                    )
        
        return self.graph
    
    def calculate_centrality_metrics(
        self,
        graph: Optional[nx.Graph] = None
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculate various centrality metrics for all nodes.
        
        Args:
            graph: NetworkX graph (uses self.graph if None)
        
        Returns:
            Dictionary mapping node -> metric -> value
        """
        if graph is None:
            graph = self.graph
        
        if len(graph) == 0:
            return {}
        
        metrics = {}
        
        # Betweenness centrality
        try:
            betweenness = nx.betweenness_centrality(graph, weight='weight')
        except Exception as e:
            logger.warning(f"Error calculating betweenness centrality: {e}")
            betweenness = {}
        
        # Eigenvector centrality
        try:
            eigenvector = nx.eigenvector_centrality(graph, max_iter=1000, weight='weight')
        except Exception as e:
            logger.warning(f"Error calculating eigenvector centrality: {e}")
            eigenvector = {}
        
        # PageRank
        try:
            pagerank = nx.pagerank(graph, weight='weight')
        except Exception as e:
            logger.warning(f"Error calculating PageRank: {e}")
            pagerank = {}
        
        # In-degree centrality (for directed graphs)
        in_degree = dict(graph.in_degree(weight='weight'))
        out_degree = dict(graph.out_degree(weight='weight'))
        
        # Closeness centrality
        try:
            closeness = nx.closeness_centrality(graph, distance='weight')
        except Exception as e:
            logger.warning(f"Error calculating closeness centrality: {e}")
            closeness = {}
        
        # Combine all metrics
        all_nodes = set(graph.nodes())
        for node in all_nodes:
            metrics[node] = {
                'betweenness_centrality': betweenness.get(node, 0.0),
                'eigenvector_centrality': eigenvector.get(node, 0.0),
                'pagerank': pagerank.get(node, 0.0),
                'in_degree': in_degree.get(node, 0),
                'out_degree': out_degree.get(node, 0),
                'closeness_centrality': closeness.get(node, 0.0),
                'total_degree': in_degree.get(node, 0) + out_degree.get(node, 0)
            }
        
        return metrics
    
    def get_top_nodes(
        self,
        metric: str,
        top_n: int = 10,
        graph: Optional[nx.Graph] = None
    ) -> List[Tuple[str, float]]:
        """
        Get top N nodes by a centrality metric.
        
        Args:
            metric: Metric name ('betweenness', 'eigenvector', 'pagerank', etc.)
            top_n: Number of top nodes to return
            graph: NetworkX graph (uses self.graph if None)
        
        Returns:
            List of (node, value) tuples sorted by value descending
        """
        if graph is None:
            graph = self.graph
        
        centrality = self.calculate_centrality_metrics(graph)
        
        # Extract metric values
        metric_key = f'{metric}_centrality' if metric != 'pagerank' else 'pagerank'
        if metric == 'in_degree' or metric == 'out_degree' or metric == 'total_degree':
            metric_key = metric
        
        node_values = [
            (node, metrics.get(metric_key, 0.0))
            for node, metrics in centrality.items()
        ]
        
        # Sort and return top N
        node_values.sort(key=lambda x: x[1], reverse=True)
        return node_values[:top_n]
    
    def calculate_concentration_metrics(
        self,
        graph: Optional[nx.Graph] = None
    ) -> Dict[str, float]:
        """
        Calculate network concentration metrics (Gini, HHI).
        
        Args:
            graph: NetworkX graph (uses self.graph if None)
        
        Returns:
            Dictionary with concentration metrics
        """
        if graph is None:
            graph = self.graph
        
        if len(graph) == 0:
            return {
                'gini_coefficient': 0.0,
                'hhi': 0.0,
                'top_5_share': 0.0,
                'top_10_share': 0.0
            }
        
        # Get degree distribution
        degrees = dict(graph.degree(weight='weight'))
        degree_values = list(degrees.values())
        
        if not degree_values or sum(degree_values) == 0:
            return {
                'gini_coefficient': 0.0,
                'hhi': 0.0,
                'top_5_share': 0.0,
                'top_10_share': 0.0
            }
        
        # Calculate Gini coefficient
        gini = self._calculate_gini(degree_values)
        
        # Calculate HHI (Herfindahl-Hirschman Index)
        total = sum(degree_values)
        shares = [d / total for d in degree_values if total > 0]
        hhi = sum(s**2 for s in shares)
        
        # Calculate top N shares
        sorted_degrees = sorted(degree_values, reverse=True)
        top_5_share = sum(sorted_degrees[:5]) / total if total > 0 else 0.0
        top_10_share = sum(sorted_degrees[:10]) / total if total > 0 else 0.0
        
        return {
            'gini_coefficient': gini,
            'hhi': hhi,
            'top_5_share': top_5_share,
            'top_10_share': top_10_share,
            'total_nodes': len(graph),
            'total_edges': graph.number_of_edges()
        }
    
    def _calculate_gini(self, values: List[float]) -> float:
        """Calculate Gini coefficient."""
        if not values or len(values) == 0:
            return 0.0
        
        values = sorted(values)
        n = len(values)
        cumsum = np.cumsum(values)
        total = cumsum[-1]
        
        if total == 0:
            return 0.0
        
        # Gini formula
        gini = (n + 1 - 2 * sum((n + 1 - i) * y for i, y in enumerate(values, 1))) / (n * total)
        
        return float(gini)
    
    def export_for_visualization(
        self,
        graph: Optional[nx.Graph] = None
    ) -> Dict[str, Any]:
        """
        Export graph in format suitable for vis-network visualization.
        
        Args:
            graph: NetworkX graph (uses self.graph if None)
        
        Returns:
            Dictionary with 'nodes' and 'edges' lists
        """
        if graph is None:
            graph = self.graph
        
        # Get centrality for node sizing
        centrality = self.calculate_centrality_metrics(graph)
        
        # Build nodes
        nodes = []
        for node in graph.nodes():
            node_data = graph.nodes[node]
            metrics = centrality.get(node, {})
            
            nodes.append({
                'id': node,
                'label': node,
                'value': metrics.get('total_degree', 0),
                'title': f"Node: {node}\\nDegree: {metrics.get('total_degree', 0)}\\nPageRank: {metrics.get('pagerank', 0):.4f}",
                'color': {
                    'background': '#F7931A' if node_data.get('node_type') == 'maintainer' else '#0066CC',
                    'border': '#1A1A1A'
                },
                'font': {'size': 12}
            })
        
        # Build edges
        edges = []
        for source, target, data in graph.edges(data=True):
            edges.append({
                'from': source,
                'to': target,
                'value': data.get('weight', 1),
                'title': f"Weight: {data.get('weight', 1)}"
            })
        
        return {
            'nodes': nodes,
            'edges': edges
        }

