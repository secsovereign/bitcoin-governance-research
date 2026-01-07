#!/usr/bin/env python3
"""
Regulatory Arbitrage Analysis

Framework: Actors exploit gaps between formal rules and enforcement
Application: Compare stated process (BIPs, documentation) vs. actual behavior (self-merge)
Expected insight: Larger gaps = more arbitrary power exercise
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


class RegulatoryArbitrageAnalyzer:
    """Analyzer for regulatory arbitrage - gaps between stated and actual process."""
    
    def __init__(self):
        self.data_dir = get_data_dir()
        self.analysis_dir = get_analysis_dir()
        self.processed_dir = self.data_dir / 'processed'
        self.output_dir = self.analysis_dir / 'regulatory_arbitrage'
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Stated processes (from documentation/BIPs)
        self.stated_rules = {
            'review_required': True,  # PRs should be reviewed
            'approval_required': True,  # PRs need approval before merge
            'self_merge_allowed': False,  # Self-merge should not be standard
            'nack_respected': True,  # NACKs should be respected
            'formal_process': True  # Formal governance process exists
        }
    
    def run_analysis(self):
        """Run regulatory arbitrage analysis."""
        logger.info("=" * 60)
        logger.info("Regulatory Arbitrage Analysis")
        logger.info("=" * 60)
        
        prs = self._load_enriched_prs()
        if not prs:
            logger.error("No PR data found")
            return
        
        logger.info(f"Loaded {len(prs)} PRs")
        
        # Analyze actual behavior
        actual_behavior = self._analyze_actual_behavior(prs)
        
        # Calculate gaps
        gaps = self._calculate_gaps(actual_behavior)
        
        # Analyze arbitrage patterns
        arbitrage_patterns = self._analyze_arbitrage_patterns(prs)
        
        # Save results
        results = {
            'analysis_name': 'regulatory_arbitrage',
            'version': '1.0',
            'metadata': {
                'total_prs': len(prs)
            },
            'data': {
                'stated_rules': self.stated_rules,
                'actual_behavior': actual_behavior,
                'gaps': gaps,
                'arbitrage_patterns': arbitrage_patterns
            }
        }
        
        output_file = self.output_dir / 'regulatory_arbitrage.json'
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Results saved to {output_file}")
        logger.info("Regulatory arbitrage analysis complete")
    
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
    
    def _analyze_actual_behavior(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze actual behavior vs. stated rules."""
        merged_prs = [pr for pr in prs if pr.get('merged', False)]
        
        # Review requirement
        zero_reviews = sum(1 for pr in merged_prs if len(pr.get('reviews', [])) == 0)
        review_rate = 1 - (zero_reviews / len(merged_prs)) if merged_prs else 0
        
        # Approval requirement
        approved_before_merge = 0
        for pr in merged_prs:
            reviews = pr.get('reviews', [])
            merged_at = pr.get('merged_at', '')
            if merged_at:
                approvals = [r for r in reviews if r.get('state') == 'APPROVED' and r.get('submitted_at', '') < merged_at]
                if approvals:
                    approved_before_merge += 1
        
        approval_rate = approved_before_merge / len(merged_prs) if merged_prs else 0
        
        # Self-merge
        self_merged = 0
        for pr in merged_prs:
            author = pr.get('author') or pr.get('user', {}).get('login', '')
            merged_by = pr.get('merged_by', {}).get('login', '') if isinstance(pr.get('merged_by'), dict) else pr.get('merged_by_login', '')
            
            maintainer_involvement = pr.get('maintainer_involvement', {})
            author_is_maintainer = maintainer_involvement.get('author_is_maintainer', False)
            merged_by_maintainer = maintainer_involvement.get('merged_by_maintainer', False)
            
            if (merged_by and author and merged_by.lower() == author.lower()) or \
               (author_is_maintainer and merged_by_maintainer):
                self_merged += 1
        
        self_merge_rate = self_merged / len(merged_prs) if merged_prs else 0
        
        # NACK respect
        nacked_and_merged = 0
        for pr in merged_prs:
            reviews = pr.get('reviews', [])
            for review in reviews:
                body = (review.get('body', '') or '').upper()
                if 'NACK' in body:
                    nacked_and_merged += 1
                    break
        
        nack_violation_rate = nacked_and_merged / len(merged_prs) if merged_prs else 0
        
        return {
            'review_rate': review_rate,
            'approval_rate': approval_rate,
            'self_merge_rate': self_merge_rate,
            'nack_violation_rate': nack_violation_rate,
            'zero_reviews_count': zero_reviews,
            'total_merged': len(merged_prs)
        }
    
    def _calculate_gaps(self, actual: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate gaps between stated rules and actual behavior."""
        gaps = {}
        
        # Review gap
        if self.stated_rules['review_required']:
            gaps['review_gap'] = 1.0 - actual['review_rate']
        else:
            gaps['review_gap'] = 0
        
        # Approval gap
        if self.stated_rules['approval_required']:
            gaps['approval_gap'] = 1.0 - actual['approval_rate']
        else:
            gaps['approval_gap'] = 0
        
        # Self-merge gap
        if not self.stated_rules['self_merge_allowed']:
            gaps['self_merge_gap'] = actual['self_merge_rate']
        else:
            gaps['self_merge_gap'] = 0
        
        # NACK gap
        if self.stated_rules['nack_respected']:
            gaps['nack_gap'] = actual['nack_violation_rate']
        else:
            gaps['nack_gap'] = 0
        
        # Total arbitrage score (higher = more gaps)
        gaps['total_arbitrage_score'] = sum(gaps.values()) / len(gaps) if gaps else 0
        
        return gaps
    
    def _analyze_arbitrage_patterns(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze patterns of regulatory arbitrage."""
        maintainer_arbitrage = 0
        non_maintainer_arbitrage = 0
        maintainer_total = 0
        non_maintainer_total = 0
        
        for pr in prs:
            if not pr.get('merged', False):
                continue
            
            maintainer_involvement = pr.get('maintainer_involvement', {})
            author_is_maintainer = maintainer_involvement.get('author_is_maintainer', False)
            
            # Check for arbitrage (zero reviews + self-merge)
            reviews = pr.get('reviews', [])
            zero_reviews = len(reviews) == 0
            
            author = pr.get('author') or pr.get('user', {}).get('login', '')
            merged_by = pr.get('merged_by', {}).get('login', '') if isinstance(pr.get('merged_by'), dict) else pr.get('merged_by_login', '')
            merged_by_maintainer = maintainer_involvement.get('merged_by_maintainer', False)
            
            self_merged = (merged_by and author and merged_by.lower() == author.lower()) or \
                         (author_is_maintainer and merged_by_maintainer)
            
            is_arbitrage = zero_reviews and self_merged
            
            if author_is_maintainer:
                maintainer_total += 1
                if is_arbitrage:
                    maintainer_arbitrage += 1
            else:
                non_maintainer_total += 1
                if is_arbitrage:
                    non_maintainer_arbitrage += 1
        
        return {
            'maintainer_arbitrage_rate': maintainer_arbitrage / maintainer_total if maintainer_total > 0 else 0,
            'non_maintainer_arbitrage_rate': non_maintainer_arbitrage / non_maintainer_total if non_maintainer_total > 0 else 0,
            'arbitrage_ratio': (maintainer_arbitrage / maintainer_total) / (non_maintainer_arbitrage / non_maintainer_total) if maintainer_total > 0 and non_maintainer_arbitrage > 0 else None
        }


def main():
    analyzer = RegulatoryArbitrageAnalyzer()
    analyzer.run_analysis()


if __name__ == '__main__':
    main()

