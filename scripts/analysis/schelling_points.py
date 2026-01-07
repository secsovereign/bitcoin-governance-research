#!/usr/bin/env python3
"""
Schelling Points Analysis

Framework: Coordination defaults even without communication
Application: When do contributors coordinate around alternatives (Knots surge)?
Expected insight: 25% Knots adoption = Schelling point reached, suggests Core legitimacy threshold crossed
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger
from src.utils.paths import get_analysis_dir, get_data_dir

logger = setup_logger()


class SchellingPointsAnalyzer:
    """Analyzer for Schelling points in alternative coordination."""
    
    def __init__(self):
        self.data_dir = get_data_dir()
        self.analysis_dir = get_analysis_dir()
        self.processed_dir = self.data_dir / 'processed'
        self.output_dir = self.analysis_dir / 'schelling_points'
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def run_analysis(self):
        """Run Schelling points analysis."""
        logger.info("=" * 60)
        logger.info("Schelling Points Analysis")
        logger.info("=" * 60)
        
        prs = self._load_enriched_prs()
        if not prs:
            logger.error("No PR data found")
            return
        
        logger.info(f"Loaded {len(prs)} PRs")
        
        # Analyze coordination signals
        coordination_signals = self._analyze_coordination_signals(prs)
        
        # Analyze alternative mentions (Knots, etc.)
        alternative_mentions = self._analyze_alternative_mentions(prs)
        
        # Analyze legitimacy threshold indicators
        legitimacy_indicators = self._analyze_legitimacy_indicators(prs)
        
        # Save results
        results = {
            'analysis_name': 'schelling_points',
            'version': '1.0',
            'metadata': {
                'total_prs': len(prs)
            },
            'data': {
                'coordination_signals': coordination_signals,
                'alternative_mentions': alternative_mentions,
                'legitimacy_indicators': legitimacy_indicators
            }
        }
        
        output_file = self.output_dir / 'schelling_points.json'
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Results saved to {output_file}")
        logger.info("Schelling points analysis complete")
    
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
    
    def _analyze_coordination_signals(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze signals of coordination around alternatives."""
        # Look for mentions of alternatives, forks, etc.
        alternative_keywords = [
            'knots', 'alternative', 'fork', 'competing', 'rival',
            'switch', 'migrate', 'adopt', 'alternative implementation'
        ]
        
        mentions_by_year = defaultdict(int)
        total_by_year = defaultdict(int)
        
        for pr in prs:
            created_at = pr.get('created_at', '')
            if not created_at:
                continue
            
            try:
                year = int(created_at[:4])
            except:
                continue
            
            total_by_year[year] += 1
            
            # Check title and body
            text = f"{pr.get('title', '')} {pr.get('body', '')}".lower()
            if any(kw in text for kw in alternative_keywords):
                mentions_by_year[year] += 1
            
            # Check comments
            for comment in pr.get('comments', []):
                comment_text = (comment.get('body', '') or '').lower()
                if any(kw in comment_text for kw in alternative_keywords):
                    mentions_by_year[year] += 1
        
        coordination_rates = {}
        for year in sorted(total_by_year.keys()):
            rate = mentions_by_year[year] / total_by_year[year] if total_by_year[year] > 0 else 0
            coordination_rates[year] = {
                'mentions': mentions_by_year[year],
                'total': total_by_year[year],
                'rate': rate
            }
        
        return coordination_rates
    
    def _analyze_alternative_mentions(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze mentions of specific alternatives."""
        alternatives = {
            'knots': 0,
            'fork': 0,
            'alternative': 0,
            'competing': 0
        }
        
        for pr in prs:
            text = f"{pr.get('title', '')} {pr.get('body', '')}".lower()
            
            if 'knots' in text:
                alternatives['knots'] += 1
            if 'fork' in text:
                alternatives['fork'] += 1
            if 'alternative' in text:
                alternatives['alternative'] += 1
            if 'competing' in text:
                alternatives['competing'] += 1
        
        return alternatives
    
    def _analyze_legitimacy_indicators(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze indicators of legitimacy threshold crossing."""
        # Look for governance concerns, process complaints, etc.
        legitimacy_keywords = [
            'governance', 'process', 'unfair', 'biased', 'arbitrary',
            'legitimate', 'illegitimate', 'authority', 'power', 'control'
        ]
        
        concerns_by_year = defaultdict(int)
        total_by_year = defaultdict(int)
        
        for pr in prs:
            created_at = pr.get('created_at', '')
            if not created_at:
                continue
            
            try:
                year = int(created_at[:4])
            except:
                continue
            
            total_by_year[year] += 1
            
            text = f"{pr.get('title', '')} {pr.get('body', '')}".lower()
            if any(kw in text for kw in legitimacy_keywords):
                concerns_by_year[year] += 1
        
        concern_rates = {}
        for year in sorted(total_by_year.keys()):
            rate = concerns_by_year[year] / total_by_year[year] if total_by_year[year] > 0 else 0
            concern_rates[year] = {
                'concerns': concerns_by_year[year],
                'total': total_by_year[year],
                'rate': rate
            }
        
        return concern_rates


def main():
    analyzer = SchellingPointsAnalyzer()
    analyzer.run_analysis()


if __name__ == '__main__':
    main()

