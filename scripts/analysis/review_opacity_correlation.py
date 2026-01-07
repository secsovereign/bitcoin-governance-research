#!/usr/bin/env python3
"""
Review Opacity vs Self-Merge Rate Correlation Analysis

Measures correlation between review opacity (monitoring difficulty) 
and self-merge rate (agent divergence) to test Principal-Agent Theory.
"""

import json
import sys
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


class ReviewOpacityCorrelationAnalyzer:
    """Analyzer for review opacity vs self-merge correlation."""
    
    def __init__(self):
        from src.utils.paths import get_data_dir
        self.data_dir = get_data_dir()
        self.analysis_dir = get_analysis_dir()
        self.processed_dir = self.data_dir / 'processed'
        self.output_dir = self.analysis_dir / 'review_opacity_correlation'
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def run_analysis(self):
        """Run review opacity correlation analysis."""
        logger.info("=" * 60)
        logger.info("Review Opacity vs Self-Merge Rate Correlation Analysis")
        logger.info("=" * 60)
        
        prs = self._load_enriched_prs()
        if not prs:
            logger.error("No PR data found")
            return
        
        logger.info(f"Loaded {len(prs)} PRs")
        
        # Filter to merged PRs only
        merged_prs = [pr for pr in prs if pr.get('merged', False)]
        logger.info(f"Analyzing {len(merged_prs)} merged PRs")
        
        # Calculate review opacity metrics
        opacity_metrics = self._calculate_opacity_metrics(merged_prs)
        
        # Calculate self-merge rates by opacity level
        correlation_results = self._calculate_correlation(merged_prs, opacity_metrics)
        
        # Temporal analysis
        temporal_results = self._analyze_temporal_correlation(merged_prs)
        
        # Save results
        results = {
            'analysis_name': 'review_opacity_correlation',
            'version': '1.0',
            'metadata': {
                'total_prs': len(prs),
                'merged_prs': len(merged_prs),
                'analysis_date': '2025-12-10'
            },
            'data': {
                'opacity_metrics': opacity_metrics,
                'correlation_results': correlation_results,
                'temporal_analysis': temporal_results
            }
        }
        
        output_file = self.output_dir / 'review_opacity_correlation.json'
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Results saved to {output_file}")
        logger.info("Review opacity correlation analysis complete")
    
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
    
    def _calculate_opacity_metrics(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate review opacity metrics for each PR."""
        metrics = {
            'zero_reviews_rate': 0,
            'avg_review_count': 0,
            'avg_review_comment_length': 0,
            'avg_review_depth': 0,
            'approval_without_comment_rate': 0
        }
        
        total_prs = len(prs)
        zero_reviews = 0
        review_counts = []
        comment_lengths = []
        review_depths = []
        approval_without_comment = 0
        total_approvals = 0
        
        for pr in prs:
            reviews = pr.get('reviews', [])
            review_count = len(reviews)
            review_counts.append(review_count)
            
            if review_count == 0:
                zero_reviews += 1
            else:
                # Calculate review comment metrics
                for review in reviews:
                    body = review.get('body', '') or ''
                    comment_lengths.append(len(body))
                    
                    # Review depth: number of review comments (inline comments)
                    review_comments = review.get('review_comments', []) or []
                    review_depth = len(review_comments)
                    review_depths.append(review_depth)
                    
                    # Approval without comment
                    if review.get('state') == 'APPROVED':
                        total_approvals += 1
                        if len(body.strip()) == 0:
                            approval_without_comment += 1
        
        metrics['zero_reviews_rate'] = zero_reviews / total_prs if total_prs > 0 else 0
        metrics['avg_review_count'] = statistics.mean(review_counts) if review_counts else 0
        metrics['avg_review_comment_length'] = statistics.mean(comment_lengths) if comment_lengths else 0
        metrics['avg_review_depth'] = statistics.mean(review_depths) if review_depths else 0
        metrics['approval_without_comment_rate'] = approval_without_comment / total_approvals if total_approvals > 0 else 0
        
        return metrics
    
    def _calculate_correlation(self, prs: List[Dict[str, Any]], opacity_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate correlation between review opacity and self-merge rate."""
        
        # Group PRs by opacity level
        opacity_groups = {
            'zero_reviews': [],
            'low_reviews': [],  # 1-2 reviews
            'medium_reviews': [],  # 3-5 reviews
            'high_reviews': []  # 6+ reviews
        }
        
        for pr in prs:
            reviews = pr.get('reviews', [])
            review_count = len(reviews)
            
            if review_count == 0:
                opacity_groups['zero_reviews'].append(pr)
            elif review_count <= 2:
                opacity_groups['low_reviews'].append(pr)
            elif review_count <= 5:
                opacity_groups['medium_reviews'].append(pr)
            else:
                opacity_groups['high_reviews'].append(pr)
        
        # Calculate self-merge rates by opacity level
        results = {}
        
        for group_name, group_prs in opacity_groups.items():
            if not group_prs:
                continue
            
            # Determine if PR was self-merged
            # Self-merge: merged_by == author
            self_merged = 0
            total_merged = len(group_prs)
            
            for pr in group_prs:
                author = pr.get('user', {}).get('login', '') if isinstance(pr.get('user'), dict) else pr.get('author', '')
                merged_by = pr.get('merged_by', {}).get('login', '') if isinstance(pr.get('merged_by'), dict) else pr.get('merged_by_login', '')
                
                # Also check maintainer involvement
                maintainer_involvement = pr.get('maintainer_involvement', {})
                author_is_maintainer = maintainer_involvement.get('author_is_maintainer', False)
                merged_by_maintainer = maintainer_involvement.get('merged_by_maintainer', False)
                
                # Self-merge if: merged_by == author OR (author is maintainer AND merged by maintainer)
                if (merged_by and author and merged_by.lower() == author.lower()) or \
                   (author_is_maintainer and merged_by_maintainer):
                    self_merged += 1
            
            self_merge_rate = self_merged / total_merged if total_merged > 0 else 0
            
            # Calculate average review opacity metrics for this group
            avg_review_count = statistics.mean([len(pr.get('reviews', [])) for pr in group_prs]) if group_prs else 0
            avg_comment_length = 0
            total_comments = 0
            for pr in group_prs:
                for review in pr.get('reviews', []):
                    body = review.get('body', '') or ''
                    avg_comment_length += len(body)
                    total_comments += 1
            avg_comment_length = avg_comment_length / total_comments if total_comments > 0 else 0
            
            results[group_name] = {
                'pr_count': total_merged,
                'self_merged_count': self_merged,
                'self_merge_rate': self_merge_rate,
                'avg_review_count': avg_review_count,
                'avg_comment_length': avg_comment_length,
                'opacity_level': self._get_opacity_level(group_name, avg_review_count, avg_comment_length)
            }
        
        # Calculate correlation coefficient
        # Simple correlation: as opacity increases (fewer reviews), self-merge rate should increase
        opacity_scores = []
        self_merge_rates = []
        
        for group_name, group_data in results.items():
            # Opacity score: higher = more opaque (fewer reviews, shorter comments)
            opacity_score = 1.0 / (group_data['avg_review_count'] + 1)  # Inverse of review count
            opacity_scores.append(opacity_score)
            self_merge_rates.append(group_data['self_merge_rate'])
        
        # Calculate Pearson correlation
        correlation = self._pearson_correlation(opacity_scores, self_merge_rates) if len(opacity_scores) > 1 else 0
        
        return {
            'by_opacity_level': results,
            'correlation_coefficient': correlation,
            'interpretation': self._interpret_correlation(correlation)
        }
    
    def _get_opacity_level(self, group_name: str, avg_review_count: float, avg_comment_length: float) -> str:
        """Determine opacity level."""
        if group_name == 'zero_reviews':
            return 'maximum'
        elif avg_review_count < 2 and avg_comment_length < 100:
            return 'high'
        elif avg_review_count < 4:
            return 'medium'
        else:
            return 'low'
    
    def _pearson_correlation(self, x: List[float], y: List[float]) -> float:
        """Calculate Pearson correlation coefficient."""
        if len(x) != len(y) or len(x) < 2:
            return 0.0
        
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(x[i] * y[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))
        sum_y2 = sum(y[i] ** 2 for i in range(n))
        
        numerator = n * sum_xy - sum_x * sum_y
        denominator = ((n * sum_x2 - sum_x ** 2) * (n * sum_y2 - sum_y ** 2)) ** 0.5
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator
    
    def _interpret_correlation(self, correlation: float) -> str:
        """Interpret correlation coefficient."""
        abs_corr = abs(correlation)
        
        if abs_corr < 0.3:
            strength = "weak"
        elif abs_corr < 0.7:
            strength = "moderate"
        else:
            strength = "strong"
        
        direction = "positive" if correlation > 0 else "negative"
        
        return f"{strength} {direction} correlation"
    
    def _analyze_temporal_correlation(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze correlation over time."""
        # Group by year
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
            if len(year_prs) < 10:  # Skip years with too few PRs
                continue
            
            # Calculate opacity and self-merge for this year
            zero_reviews = sum(1 for pr in year_prs if len(pr.get('reviews', [])) == 0)
            zero_reviews_rate = zero_reviews / len(year_prs) if year_prs else 0
            
            self_merged = 0
            for pr in year_prs:
                author = pr.get('user', {}).get('login', '') if isinstance(pr.get('user'), dict) else pr.get('author', '')
                merged_by = pr.get('merged_by', {}).get('login', '') if isinstance(pr.get('merged_by'), dict) else pr.get('merged_by_login', '')
                
                maintainer_involvement = pr.get('maintainer_involvement', {})
                author_is_maintainer = maintainer_involvement.get('author_is_maintainer', False)
                merged_by_maintainer = maintainer_involvement.get('merged_by_maintainer', False)
                
                if (merged_by and author and merged_by.lower() == author.lower()) or \
                   (author_is_maintainer and merged_by_maintainer):
                    self_merged += 1
            
            self_merge_rate = self_merged / len(year_prs) if year_prs else 0
            
            temporal_results[year] = {
                'pr_count': len(year_prs),
                'zero_reviews_rate': zero_reviews_rate,
                'self_merge_rate': self_merge_rate,
                'opacity_score': 1.0 - zero_reviews_rate  # Lower zero reviews = lower opacity
            }
        
        return temporal_results


def main():
    analyzer = ReviewOpacityCorrelationAnalyzer()
    analyzer.run_analysis()


if __name__ == '__main__':
    main()

