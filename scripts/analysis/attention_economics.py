#!/usr/bin/env python3
"""
Attention Economics Analysis

Framework: Attention is scarce resource, allocation reveals priorities
Application: Response time × PR complexity interaction - do maintainers prioritize simple or complex PRs?
Expected insight: If maintainer PRs get fast responses regardless of complexity = privilege, not efficiency
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict
import statistics

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger
from src.utils.paths import get_analysis_dir, get_data_dir

logger = setup_logger()


class AttentionEconomicsAnalyzer:
    """Analyzer for attention allocation patterns."""
    
    def __init__(self):
        self.data_dir = get_data_dir()
        self.analysis_dir = get_analysis_dir()
        self.processed_dir = self.data_dir / 'processed'
        self.output_dir = self.analysis_dir / 'attention_economics'
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def run_analysis(self):
        """Run attention economics analysis."""
        logger.info("=" * 60)
        logger.info("Attention Economics Analysis")
        logger.info("=" * 60)
        
        prs = self._load_enriched_prs()
        if not prs:
            logger.error("No PR data found")
            return
        
        logger.info(f"Loaded {len(prs)} PRs")
        
        # Analyze response time by complexity
        complexity_analysis = self._analyze_complexity_response_time(prs)
        
        # Analyze maintainer vs non-maintainer attention allocation
        attention_allocation = self._analyze_attention_allocation(prs)
        
        # Analyze priority patterns
        priority_patterns = self._analyze_priority_patterns(prs)
        
        # Save results
        results = {
            'analysis_name': 'attention_economics',
            'version': '1.0',
            'metadata': {
                'total_prs': len(prs)
            },
            'data': {
                'complexity_response_time': complexity_analysis,
                'attention_allocation': attention_allocation,
                'priority_patterns': priority_patterns
            }
        }
        
        output_file = self.output_dir / 'attention_economics.json'
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Results saved to {output_file}")
        logger.info("Attention economics analysis complete")
    
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
    
    def _get_pr_complexity(self, pr: Dict[str, Any]) -> str:
        """Categorize PR complexity."""
        additions = pr.get('additions', 0)
        deletions = pr.get('deletions', 0)
        files_changed = pr.get('changed_files', 0)
        
        total_changes = additions + deletions
        
        if total_changes < 50 and files_changed <= 2:
            return 'simple'
        elif total_changes < 500 and files_changed <= 10:
            return 'medium'
        else:
            return 'complex'
    
    def _get_response_time(self, pr: Dict[str, Any]) -> Optional[float]:
        """Get first response time in hours."""
        created_at = pr.get('created_at', '')
        if not created_at:
            return None
        
        # Find first comment or review
        first_response = None
        
        comments = pr.get('comments', [])
        reviews = pr.get('reviews', [])
        
        for comment in comments:
            comment_time = comment.get('created_at', '')
            if comment_time and comment_time > created_at:
                if not first_response or comment_time < first_response:
                    first_response = comment_time
        
        for review in reviews:
            review_time = review.get('submitted_at', '')
            if review_time and review_time > created_at:
                if not first_response or review_time < first_response:
                    first_response = review_time
        
        if not first_response:
            return None
        
        # Calculate hours difference
        try:
            from datetime import datetime
            created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            responded = datetime.fromisoformat(first_response.replace('Z', '+00:00'))
            delta = responded - created
            return delta.total_seconds() / 3600
        except:
            return None
    
    def _analyze_complexity_response_time(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze response time by PR complexity and author status."""
        results = {
            'maintainer_prs': {'simple': [], 'medium': [], 'complex': []},
            'non_maintainer_prs': {'simple': [], 'medium': [], 'complex': []}
        }
        
        for pr in prs:
            maintainer_involvement = pr.get('maintainer_involvement', {})
            is_maintainer = maintainer_involvement.get('author_is_maintainer', False)
            
            complexity = self._get_pr_complexity(pr)
            response_time = self._get_response_time(pr)
            
            if response_time is not None:
                if is_maintainer:
                    results['maintainer_prs'][complexity].append(response_time)
                else:
                    results['non_maintainer_prs'][complexity].append(response_time)
        
        # Calculate averages
        analysis = {}
        for author_type in ['maintainer_prs', 'non_maintainer_prs']:
            analysis[author_type] = {}
            for complexity in ['simple', 'medium', 'complex']:
                times = results[author_type][complexity]
                if times:
                    analysis[author_type][complexity] = {
                        'count': len(times),
                        'avg_response_time_hours': statistics.mean(times),
                        'median_response_time_hours': statistics.median(times)
                    }
                else:
                    analysis[author_type][complexity] = {
                        'count': 0,
                        'avg_response_time_hours': None,
                        'median_response_time_hours': None
                    }
        
        # Calculate privilege indicator: if maintainer PRs get fast responses regardless of complexity
        maintainer_simple = analysis['maintainer_prs']['simple'].get('avg_response_time_hours')
        maintainer_complex = analysis['maintainer_prs']['complex'].get('avg_response_time_hours')
        non_maintainer_simple = analysis['non_maintainer_prs']['simple'].get('avg_response_time_hours')
        non_maintainer_complex = analysis['non_maintainer_prs']['complex'].get('avg_response_time_hours')
        
        privilege_ratio = None
        if maintainer_simple and non_maintainer_simple:
            privilege_ratio = non_maintainer_simple / maintainer_simple
        
        return {
            'by_complexity': analysis,
            'privilege_ratio': privilege_ratio,
            'interpretation': self._interpret_attention_allocation(analysis, privilege_ratio)
        }
    
    def _interpret_attention_allocation(self, analysis: Dict, privilege_ratio: Optional[float]) -> str:
        """Interpret attention allocation patterns."""
        if privilege_ratio and privilege_ratio > 2.0:
            return "Strong privilege pattern - maintainer PRs get much faster responses regardless of complexity"
        elif privilege_ratio and privilege_ratio > 1.5:
            return "Moderate privilege pattern - maintainer PRs get faster responses"
        else:
            return "Weak or no privilege pattern - response times similar by author status"
    
    def _analyze_attention_allocation(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze overall attention allocation patterns."""
        maintainer_prs = []
        non_maintainer_prs = []
        
        for pr in prs:
            maintainer_involvement = pr.get('maintainer_involvement', {})
            is_maintainer = maintainer_involvement.get('author_is_maintainer', False)
            
            response_time = self._get_response_time(pr)
            if response_time is not None:
                if is_maintainer:
                    maintainer_prs.append(response_time)
                else:
                    non_maintainer_prs.append(response_time)
        
        return {
            'maintainer_avg_response_hours': statistics.mean(maintainer_prs) if maintainer_prs else None,
            'non_maintainer_avg_response_hours': statistics.mean(non_maintainer_prs) if non_maintainer_prs else None,
            'response_time_ratio': statistics.mean(non_maintainer_prs) / statistics.mean(maintainer_prs) if maintainer_prs and non_maintainer_prs else None
        }
    
    def _analyze_priority_patterns(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze what types of PRs get priority attention."""
        # Group by various characteristics
        priority_indicators = {
            'maintainer_authored': [],
            'non_maintainer_authored': [],
            'high_complexity': [],
            'low_complexity': []
        }
        
        for pr in prs:
            maintainer_involvement = pr.get('maintainer_involvement', {})
            is_maintainer = maintainer_involvement.get('author_is_maintainer', False)
            complexity = self._get_pr_complexity(pr)
            response_time = self._get_response_time(pr)
            
            if response_time is not None:
                if is_maintainer:
                    priority_indicators['maintainer_authored'].append(response_time)
                else:
                    priority_indicators['non_maintainer_authored'].append(response_time)
                
                if complexity == 'complex':
                    priority_indicators['high_complexity'].append(response_time)
                elif complexity == 'simple':
                    priority_indicators['low_complexity'].append(response_time)
        
        return {
            'maintainer_avg': statistics.mean(priority_indicators['maintainer_authored']) if priority_indicators['maintainer_authored'] else None,
            'non_maintainer_avg': statistics.mean(priority_indicators['non_maintainer_authored']) if priority_indicators['non_maintainer_authored'] else None,
            'high_complexity_avg': statistics.mean(priority_indicators['high_complexity']) if priority_indicators['high_complexity'] else None,
            'low_complexity_avg': statistics.mean(priority_indicators['low_complexity']) if priority_indicators['low_complexity'] else None
        }


def main():
    analyzer = AttentionEconomicsAnalyzer()
    analyzer.run_analysis()


if __name__ == '__main__':
    main()

