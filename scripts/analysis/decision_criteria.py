#!/usr/bin/env python3
"""
Decision Criteria Analysis - Analyze merge/rejection criteria and consistency.

Analyzes:
1. Rejection reason patterns
2. Criteria consistency
3. Rough consensus cases
4. Decision timeline metrics
5. Factors affecting decision speed
"""

import sys
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from collections import defaultdict, Counter
from collections import Counter as CounterType
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir, get_analysis_dir
from src.utils.statistics import StatisticalAnalyzer
from src.schemas.analysis_results import create_result_template

logger = setup_logger()


class DecisionCriteriaAnalyzer:
    """Analyzer for decision criteria and consistency."""
    
    def __init__(self):
        """Initialize analyzer."""
        self.data_dir = get_data_dir()
        self.processed_dir = self.data_dir / 'processed'
        self.analysis_dir = get_analysis_dir() / 'decision_criteria'
        self.analysis_dir.mkdir(parents=True, exist_ok=True)
        
        self.stat_analyzer = StatisticalAnalyzer(random_seed=42)
        
        # Rejection reason patterns
        self.rejection_patterns = {
            'consensus': ['consensus', 'rough consensus', 'no consensus'],
            'technical': ['bug', 'error', 'issue', 'problem', 'fails', 'broken'],
            'design': ['design', 'approach', 'architecture', 'structure'],
            'security': ['security', 'vulnerability', 'risk', 'unsafe'],
            'performance': ['performance', 'slow', 'inefficient', 'optimization'],
            'maintenance': ['maintenance', 'complexity', 'hard to maintain'],
            'scope': ['scope', 'out of scope', 'not in scope'],
            'duplicate': ['duplicate', 'already', 'existing'],
            'incomplete': ['incomplete', 'missing', 'needs more']
        }
    
    def run_analysis(self):
        """Run decision criteria analysis."""
        logger.info("=" * 60)
        logger.info("Decision Criteria Analysis")
        logger.info("=" * 60)
        
        # Load data
        prs = self._load_enriched_prs()
        
        # Analyze rejection reasons
        rejection_reasons = self._analyze_rejection_reasons(prs)
        
        # Analyze consistency
        consistency = self._analyze_consistency(prs)
        
        # Identify rough consensus cases
        consensus_cases = self._identify_consensus_cases(prs)
        
        # Analyze decision timelines
        timeline_metrics = self._analyze_decision_timelines(prs)
        
        # Analyze factors affecting speed
        speed_factors = self._analyze_speed_factors(prs)
        
        # Analyze review sentiment patterns (NEW)
        review_sentiment = self._analyze_review_sentiment(prs)
        
        # Analyze label patterns (NEW)
        label_patterns = self._analyze_label_patterns(prs)
        
        # Save results
        self._save_results({
            'rejection_reasons': rejection_reasons,
            'consistency': consistency,
            'consensus_cases': consensus_cases,
            'timeline_metrics': timeline_metrics,
            'speed_factors': speed_factors,
            'review_sentiment': review_sentiment,
            'label_patterns': label_patterns
        })
        
        logger.info("Decision criteria analysis complete")
    
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
                prs.append(json.loads(line))
        
        return prs
    
    def _analyze_rejection_reasons(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze rejection reason patterns."""
        rejection_reasons = Counter()
        pr_reasons = {}
        
        for pr in prs:
            if pr.get('state') == 'closed' and not pr.get('merged'):
                # Extract reasons from comments and reviews
                reasons = self._extract_rejection_reasons(pr)
                pr_reasons[pr.get('number')] = reasons
                
                for reason in reasons:
                    rejection_reasons[reason] += 1
        
        return {
            'distribution': dict(rejection_reasons),
            'total_rejections': len(pr_reasons),
            'pr_reasons': pr_reasons
        }
    
    def _extract_rejection_reasons(self, pr: Dict[str, Any]) -> List[str]:
        """Extract rejection reasons from PR."""
        reasons = []
        text = f"{pr.get('title', '')} {pr.get('body', '')}".lower()
        
        # Check all comments and reviews
        for comment in pr.get('comments', []):
            text += f" {comment.get('body', '')}".lower()
        
        for review in pr.get('reviews', []):
            text += f" {review.get('body', '')}".lower()
        
        # Match patterns
        for category, keywords in self.rejection_patterns.items():
            if any(keyword in text for keyword in keywords):
                reasons.append(category)
        
        return list(set(reasons))  # Remove duplicates
    
    def _analyze_consistency(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze decision consistency."""
        # Group PRs by similar characteristics
        similar_prs = defaultdict(list)
        
        for pr in prs:
            # Create key from PR characteristics
            key = (
                pr.get('classification', {}).get('primary_type', 'unknown'),
                pr.get('additions', 0) // 100,  # Bucket by size
                pr.get('deletions', 0) // 100
            )
            similar_prs[key].append(pr)
        
        # Check consistency within similar PRs
        consistent = 0
        inconsistent = 0
        
        for key, group_prs in similar_prs.items():
            if len(group_prs) < 2:
                continue
            
            outcomes = [pr.get('merged', False) for pr in group_prs]
            if len(set(outcomes)) == 1:  # All same outcome
                consistent += 1
            else:
                inconsistent += 1
        
        consistency_score = consistent / (consistent + inconsistent) if (consistent + inconsistent) > 0 else 0
        
        return {
            'consistency_score': consistency_score,
            'consistent_groups': consistent,
            'inconsistent_groups': inconsistent,
            'total_groups': consistent + inconsistent
        }
    
    def _identify_consensus_cases(self, prs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify rough consensus cases."""
        consensus_cases = []
        
        for pr in prs:
            # Check for consensus indicators
            reviews = pr.get('reviews', [])
            approved = sum(1 for r in reviews if r.get('state', '').lower() == 'approved')
            changes_requested = sum(1 for r in reviews if r.get('state', '').lower() == 'changes_requested')
            
            # Rough consensus: multiple approvals, few objections
            if approved >= 2 and changes_requested <= 1:
                consensus_cases.append({
                    'pr_number': pr.get('number'),
                    'outcome': 'merged' if pr.get('merged') else 'closed',
                    'approved_count': approved,
                    'changes_requested_count': changes_requested,
                    'consensus_indicators': {
                        'multiple_approvals': approved >= 2,
                        'few_objections': changes_requested <= 1,
                        'approval_ratio': approved / len(reviews) if reviews else 0
                    },
                    'decision_maker': pr.get('merged_by')
                })
        
        return consensus_cases[:50]  # Top 50 cases
    
    def _analyze_decision_timelines(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze decision timeline metrics."""
        times_to_decision = []
        
        for pr in prs:
            if pr.get('created_at') and (pr.get('merged_at') or pr.get('closed_at')):
                try:
                    created = datetime.fromisoformat(pr['created_at'].replace('Z', '+00:00'))
                    decision_date = pr.get('merged_at') or pr.get('closed_at')
                    if decision_date:
                        decided = datetime.fromisoformat(decision_date.replace('Z', '+00:00'))
                        days = (decided - created).days
                        if days >= 0:
                            times_to_decision.append({
                                'days': days,
                                'merged': pr.get('merged', False),
                                'pr_number': pr.get('number')
                            })
                except Exception:
                    continue
        
        if not times_to_decision:
            return {'error': 'No timeline data available'}
        
        merged_times = [t['days'] for t in times_to_decision if t['merged']]
        closed_times = [t['days'] for t in times_to_decision if not t['merged']]
        
        return {
            'avg_time_to_decision': sum(t['days'] for t in times_to_decision) / len(times_to_decision),
            'median_time_to_decision': sorted([t['days'] for t in times_to_decision])[len(times_to_decision) // 2],
            'avg_time_to_merge': sum(merged_times) / len(merged_times) if merged_times else None,
            'avg_time_to_close': sum(closed_times) / len(closed_times) if closed_times else None,
            'total_decisions': len(times_to_decision)
        }
    
    def _analyze_speed_factors(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze factors affecting decision speed."""
        # Group by factors
        by_maintainer_author = {'maintainer': [], 'non_maintainer': []}
        by_size = {'small': [], 'medium': [], 'large': []}
        by_type = defaultdict(list)
        
        for pr in prs:
            if pr.get('created_at') and (pr.get('merged_at') or pr.get('closed_at')):
                try:
                    created = datetime.fromisoformat(pr['created_at'].replace('Z', '+00:00'))
                    decision_date = pr.get('merged_at') or pr.get('closed_at')
                    if decision_date:
                        decided = datetime.fromisoformat(decision_date.replace('Z', '+00:00'))
                        days = (decided - created).days
                        
                        # By maintainer status
                        if pr.get('maintainer_involvement', {}).get('author_is_maintainer'):
                            by_maintainer_author['maintainer'].append(days)
                        else:
                            by_maintainer_author['non_maintainer'].append(days)
                        
                        # By size
                        additions = pr.get('additions', 0)
                        if additions < 100:
                            by_size['small'].append(days)
                        elif additions < 500:
                            by_size['medium'].append(days)
                        else:
                            by_size['large'].append(days)
                        
                        # By type
                        pr_type = pr.get('classification', {}).get('primary_type', 'unknown')
                        by_type[pr_type].append(days)
                except Exception:
                    continue
        
        # Calculate averages
        factors = {
            'by_maintainer_status': {
                'maintainer_avg': sum(by_maintainer_author['maintainer']) / len(by_maintainer_author['maintainer']) if by_maintainer_author['maintainer'] else None,
                'non_maintainer_avg': sum(by_maintainer_author['non_maintainer']) / len(by_maintainer_author['non_maintainer']) if by_maintainer_author['non_maintainer'] else None
            },
            'by_size': {
                'small_avg': sum(by_size['small']) / len(by_size['small']) if by_size['small'] else None,
                'medium_avg': sum(by_size['medium']) / len(by_size['medium']) if by_size['medium'] else None,
                'large_avg': sum(by_size['large']) / len(by_size['large']) if by_size['large'] else None
            },
            'by_type': {
                k: sum(v) / len(v) if v else None
                for k, v in by_type.items()
            }
        }
        
        return factors
    
    def _analyze_review_sentiment(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze review sentiment patterns."""
        sentiment_by_outcome = defaultdict(lambda: {'positive': 0, 'negative': 0, 'neutral': 0})
        
        for pr in prs:
            outcome = 'merged' if pr.get('merged') else 'closed'
            reviews = pr.get('reviews', [])
            
            for review in reviews:
                sentiment = review.get('sentiment', 'neutral')
                sentiment_by_outcome[outcome][sentiment] += 1
        
        # Calculate sentiment ratios
        sentiment_ratios = {}
        for outcome, counts in sentiment_by_outcome.items():
            total = sum(counts.values())
            if total > 0:
                sentiment_ratios[outcome] = {
                    'positive_rate': counts['positive'] / total,
                    'negative_rate': counts['negative'] / total,
                    'neutral_rate': counts['neutral'] / total
                }
        
        return {
            'sentiment_by_outcome': dict(sentiment_by_outcome),
            'sentiment_ratios': sentiment_ratios
        }
    
    def _analyze_label_patterns(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze label patterns and their correlation with outcomes."""
        label_counts = Counter()
        label_outcomes = defaultdict(lambda: {'merged': 0, 'closed': 0})
        
        for pr in prs:
            labels = pr.get('labels', [])
            outcome = 'merged' if pr.get('merged') else 'closed'
            
            for label in labels:
                label_name = label if isinstance(label, str) else label.get('name', '')
                if label_name:
                    label_counts[label_name] += 1
                    label_outcomes[label_name][outcome] += 1
        
        # Calculate merge rates by label
        label_merge_rates = {}
        for label, outcomes in label_outcomes.items():
            total = sum(outcomes.values())
            if total > 0:
                label_merge_rates[label] = {
                    'merge_rate': outcomes['merged'] / total,
                    'total_prs': total
                }
        
        return {
            'most_common_labels': dict(label_counts.most_common(20)),
            'label_merge_rates': label_merge_rates
        }
    
    def _save_results(self, results: Dict[str, Any]):
        """Save analysis results."""
        result = create_result_template('decision_criteria_analysis', '1.0.0')
        result['metadata']['timestamp'] = datetime.now().isoformat()
        result['metadata']['data_sources'] = ['data/processed/enriched_prs.jsonl']
        result['data'] = results
        
        output_file = self.analysis_dir / 'decision_criteria_analysis.json'
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        logger.info(f"Results saved to {output_file}")
        
        # Generate summary
        rejection = results.get('rejection_reasons', {})
        consistency = results.get('consistency', {})
        logger.info(f"Decision Criteria Summary:")
        logger.info(f"  Total Rejections: {rejection.get('total_rejections', 0)}")
        logger.info(f"  Consistency Score: {consistency.get('consistency_score', 0):.3f}")


def main():
    """Main entry point."""
    analyzer = DecisionCriteriaAnalyzer()
    analyzer.run_analysis()
    return 0


if __name__ == '__main__':
    sys.exit(main())

