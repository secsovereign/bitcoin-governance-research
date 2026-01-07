#!/usr/bin/env python3
"""
Institutional Isomorphism Analysis

Framework: Organizations become similar under same pressures (mimetic, coercive, normative)
Application: Compare Core to other FOSS governance - is Core more/less concentrated?
Expected insight: Core may be outlier even among similar projects
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger
from src.utils.paths import get_analysis_dir, get_data_dir

logger = setup_logger()


class InstitutionalIsomorphismAnalyzer:
    """Analyzer for institutional isomorphism patterns."""
    
    def __init__(self):
        self.data_dir = get_data_dir()
        self.analysis_dir = get_analysis_dir()
        self.processed_dir = self.data_dir / 'processed'
        self.output_dir = self.analysis_dir / 'institutional_isomorphism'
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Benchmark data (would need external FOSS project data)
        # For now, using theoretical benchmarks
        self.foss_benchmarks = {
            'typical_gini': 0.6,  # Typical FOSS project Gini
            'typical_top_5_share': 0.25,  # Typical top 5 contributor share
            'typical_top_10_share': 0.40  # Typical top 10 contributor share
        }
    
    def run_analysis(self):
        """Run institutional isomorphism analysis."""
        logger.info("=" * 60)
        logger.info("Institutional Isomorphism Analysis")
        logger.info("=" * 60)
        
        prs = self._load_enriched_prs()
        if not prs:
            logger.error("No PR data found")
            return
        
        logger.info(f"Loaded {len(prs)} PRs")
        
        # Calculate Core's concentration metrics
        core_metrics = self._calculate_core_metrics(prs)
        
        # Compare to benchmarks
        comparison = self._compare_to_benchmarks(core_metrics)
        
        # Analyze isomorphism pressures
        isomorphism_pressures = self._analyze_isomorphism_pressures(prs)
        
        # Save results
        results = {
            'analysis_name': 'institutional_isomorphism',
            'version': '1.0',
            'metadata': {
                'total_prs': len(prs)
            },
            'data': {
                'core_metrics': core_metrics,
                'benchmark_comparison': comparison,
                'isomorphism_pressures': isomorphism_pressures
            }
        }
        
        output_file = self.output_dir / 'institutional_isomorphism.json'
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Results saved to {output_file}")
        logger.info("Institutional isomorphism analysis complete")
    
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
    
    def _calculate_core_metrics(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate Bitcoin Core's concentration metrics."""
        from collections import Counter
        
        author_contributions = Counter()
        
        for pr in prs:
            author = pr.get('author') or pr.get('user', {}).get('login', '')
            if author:
                author_contributions[author] += 1
        
        if not author_contributions:
            return {}
        
        total_contributions = sum(author_contributions.values())
        sorted_authors = author_contributions.most_common()
        
        # Calculate Gini coefficient (simplified)
        n = len(sorted_authors)
        if n == 0:
            gini = 0
        else:
            cumsum = 0
            for i, (_, count) in enumerate(sorted_authors):
                cumsum += count
            # Simplified Gini calculation
            gini = 1 - (2 * sum((i + 1) * count for i, (_, count) in enumerate(sorted_authors)) / (n * total_contributions))
        
        top_5_share = sum(count for _, count in sorted_authors[:5]) / total_contributions
        top_10_share = sum(count for _, count in sorted_authors[:10]) / total_contributions
        
        return {
            'gini_coefficient': gini,
            'top_5_share': top_5_share,
            'top_10_share': top_10_share,
            'total_contributors': len(author_contributions),
            'total_contributions': total_contributions
        }
    
    def _compare_to_benchmarks(self, core_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Compare Core metrics to FOSS benchmarks."""
        if not core_metrics:
            return {}
        
        gini_ratio = core_metrics.get('gini_coefficient', 0) / self.foss_benchmarks['typical_gini'] if self.foss_benchmarks['typical_gini'] > 0 else 0
        top_5_ratio = core_metrics.get('top_5_share', 0) / self.foss_benchmarks['typical_top_5_share'] if self.foss_benchmarks['typical_top_5_share'] > 0 else 0
        top_10_ratio = core_metrics.get('top_10_share', 0) / self.foss_benchmarks['typical_top_10_share'] if self.foss_benchmarks['typical_top_10_share'] > 0 else 0
        
        is_outlier = gini_ratio > 1.5 or top_5_ratio > 1.5 or top_10_ratio > 1.5
        
        return {
            'gini_ratio': gini_ratio,
            'top_5_ratio': top_5_ratio,
            'top_10_ratio': top_10_ratio,
            'is_outlier': is_outlier,
            'interpretation': 'Ratio > 1.5 = Core is outlier compared to typical FOSS projects'
        }
    
    def _analyze_isomorphism_pressures(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze pressures toward isomorphism."""
        # Look for mentions of external pressures, standards, etc.
        pressure_keywords = {
            'mimetic': ['similar', 'like', 'same as', 'follow', 'model'],
            'coercive': ['require', 'must', 'comply', 'regulation', 'standard'],
            'normative': ['should', 'best practice', 'professional', 'expert']
        }
        
        pressure_counts = {k: 0 for k in pressure_keywords.keys()}
        total_prs = len(prs)
        
        for pr in prs:
            text = f"{pr.get('title', '')} {pr.get('body', '')}".lower()
            
            for pressure_type, keywords in pressure_keywords.items():
                if any(kw in text for kw in keywords):
                    pressure_counts[pressure_type] += 1
        
        pressure_rates = {
            k: v / total_prs if total_prs > 0 else 0
            for k, v in pressure_counts.items()
        }
        
        return {
            'pressure_counts': pressure_counts,
            'pressure_rates': pressure_rates,
            'dominant_pressure': max(pressure_rates.items(), key=lambda x: x[1])[0] if pressure_rates else None
        }


def main():
    analyzer = InstitutionalIsomorphismAnalyzer()
    analyzer.run_analysis()


if __name__ == '__main__':
    main()

