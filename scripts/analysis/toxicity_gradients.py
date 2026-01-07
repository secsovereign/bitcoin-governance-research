#!/usr/bin/env python3
"""
Toxicity Gradients Analysis

Framework: Small incivilities compound into hostile environments
Application: Sentiment analysis on PR comments - does tone differ by author status?
Expected insight: Non-maintainers receive harsher language, creates cumulative discouragement
"""

import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict, Counter

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger
from src.utils.paths import get_analysis_dir, get_data_dir

logger = setup_logger()


class ToxicityGradientsAnalyzer:
    """Analyzer for toxicity gradients in PR comments."""
    
    def __init__(self):
        self.data_dir = get_data_dir()
        self.analysis_dir = get_analysis_dir()
        self.processed_dir = self.data_dir / 'processed'
        self.output_dir = self.analysis_dir / 'toxicity_gradients'
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Toxicity indicators (simple keyword-based approach)
        self.negative_keywords = [
            'wrong', 'bad', 'no', 'not', 'never', 'fail', 'error', 'bug', 'broken',
            'reject', 'deny', 'refuse', 'inadequate', 'insufficient', 'poor', 'terrible',
            'waste', 'pointless', 'useless', 'nonsense', 'ridiculous', 'stupid', 'dumb'
        ]
        
        self.harsh_keywords = [
            'obviously', 'clearly', 'obviously wrong', 'clearly wrong', 'obviously not',
            'you should', 'you must', 'you need to', 'you have to', 'you cannot',
            'this is wrong', 'this is bad', 'this is not', 'this does not'
        ]
        
        self.polite_keywords = [
            'please', 'thanks', 'thank you', 'appreciate', 'suggest', 'consider',
            'might', 'could', 'perhaps', 'maybe', 'if possible'
        ]
    
    def run_analysis(self):
        """Run toxicity gradients analysis."""
        logger.info("=" * 60)
        logger.info("Toxicity Gradients Analysis")
        logger.info("=" * 60)
        
        prs = self._load_enriched_prs()
        if not prs:
            logger.error("No PR data found")
            return
        
        logger.info(f"Loaded {len(prs)} PRs")
        
        # Analyze comment sentiment by author status
        sentiment_analysis = self._analyze_sentiment_by_status(prs)
        
        # Analyze toxicity gradients over time
        temporal_toxicity = self._analyze_temporal_toxicity(prs)
        
        # Analyze cumulative effects
        cumulative_effects = self._analyze_cumulative_effects(prs)
        
        # Save results
        results = {
            'analysis_name': 'toxicity_gradients',
            'version': '1.0',
            'metadata': {
                'total_prs': len(prs)
            },
            'data': {
                'sentiment_by_status': sentiment_analysis,
                'temporal_toxicity': temporal_toxicity,
                'cumulative_effects': cumulative_effects
            }
        }
        
        output_file = self.output_dir / 'toxicity_gradients.json'
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Results saved to {output_file}")
        logger.info("Toxicity gradients analysis complete")
    
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
    
    def _calculate_sentiment_score(self, text: str) -> Dict[str, Any]:
        """Calculate sentiment score for text."""
        if not text:
            return {'negative': 0, 'harsh': 0, 'polite': 0, 'score': 0}
        
        text_lower = text.lower()
        
        negative_count = sum(1 for kw in self.negative_keywords if kw in text_lower)
        harsh_count = sum(1 for kw in self.harsh_keywords if kw in text_lower)
        polite_count = sum(1 for kw in self.polite_keywords if kw in text_lower)
        
        # Sentiment score: negative + harsh - polite (higher = more toxic)
        score = negative_count + harsh_count - polite_count
        
        return {
            'negative': negative_count,
            'harsh': harsh_count,
            'polite': polite_count,
            'score': score
        }
    
    def _analyze_sentiment_by_status(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze sentiment of comments by PR author status."""
        maintainer_comments = []
        non_maintainer_comments = []
        
        for pr in prs:
            maintainer_involvement = pr.get('maintainer_involvement', {})
            author_is_maintainer = maintainer_involvement.get('author_is_maintainer', False)
            
            # Analyze comments on this PR
            comments = pr.get('comments', [])
            reviews = pr.get('reviews', [])
            
            all_feedback = []
            for comment in comments:
                body = comment.get('body', '') or ''
                if body:
                    all_feedback.append(body)
            
            for review in reviews:
                body = review.get('body', '') or ''
                if body:
                    all_feedback.append(body)
            
            # Calculate sentiment for each comment
            for feedback_text in all_feedback:
                sentiment = self._calculate_sentiment_score(feedback_text)
                
                if author_is_maintainer:
                    maintainer_comments.append(sentiment)
                else:
                    non_maintainer_comments.append(sentiment)
        
        # Calculate averages
        def avg_sentiment(comments):
            if not comments:
                return None
            return {
                'avg_negative': sum(c['negative'] for c in comments) / len(comments),
                'avg_harsh': sum(c['harsh'] for c in comments) / len(comments),
                'avg_polite': sum(c['polite'] for c in comments) / len(comments),
                'avg_score': sum(c['score'] for c in comments) / len(comments),
                'count': len(comments)
            }
        
        maintainer_avg = avg_sentiment(maintainer_comments)
        non_maintainer_avg = avg_sentiment(non_maintainer_comments)
        
        # Calculate ratio
        toxicity_ratio = None
        if maintainer_avg and non_maintainer_avg and maintainer_avg['avg_score'] != 0:
            toxicity_ratio = non_maintainer_avg['avg_score'] / maintainer_avg['avg_score']
        
        return {
            'maintainer_comments': maintainer_avg,
            'non_maintainer_comments': non_maintainer_avg,
            'toxicity_ratio': toxicity_ratio,
            'interpretation': self._interpret_toxicity_ratio(toxicity_ratio)
        }
    
    def _interpret_toxicity_ratio(self, ratio: Optional[float]) -> str:
        """Interpret toxicity ratio."""
        if ratio is None:
            return "Cannot calculate - insufficient data"
        elif ratio > 1.5:
            return "Strong toxicity gradient - non-maintainers receive much harsher language"
        elif ratio > 1.2:
            return "Moderate toxicity gradient - non-maintainers receive harsher language"
        else:
            return "Weak or no toxicity gradient - similar language for both groups"
    
    def _analyze_temporal_toxicity(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze toxicity trends over time."""
        by_year = defaultdict(lambda: {'maintainer': [], 'non_maintainer': []})
        
        for pr in prs:
            created_at = pr.get('created_at', '')
            if not created_at:
                continue
            
            try:
                year = int(created_at[:4])
            except:
                continue
            
            maintainer_involvement = pr.get('maintainer_involvement', {})
            author_is_maintainer = maintainer_involvement.get('author_is_maintainer', False)
            
            # Get all feedback
            comments = pr.get('comments', [])
            reviews = pr.get('reviews', [])
            
            for comment in comments:
                body = comment.get('body', '') or ''
                if body:
                    sentiment = self._calculate_sentiment_score(body)
                    if author_is_maintainer:
                        by_year[year]['maintainer'].append(sentiment)
                    else:
                        by_year[year]['non_maintainer'].append(sentiment)
            
            for review in reviews:
                body = review.get('body', '') or ''
                if body:
                    sentiment = self._calculate_sentiment_score(body)
                    if author_is_maintainer:
                        by_year[year]['maintainer'].append(sentiment)
                    else:
                        by_year[year]['non_maintainer'].append(sentiment)
        
        temporal_results = {}
        for year in sorted(by_year.keys()):
            maintainer_scores = [s['score'] for s in by_year[year]['maintainer']]
            non_maintainer_scores = [s['score'] for s in by_year[year]['non_maintainer']]
            
            if maintainer_scores or non_maintainer_scores:
                temporal_results[year] = {
                    'maintainer_avg_score': sum(maintainer_scores) / len(maintainer_scores) if maintainer_scores else None,
                    'non_maintainer_avg_score': sum(non_maintainer_scores) / len(non_maintainer_scores) if non_maintainer_scores else None,
                    'maintainer_count': len(maintainer_scores),
                    'non_maintainer_count': len(non_maintainer_scores)
                }
        
        return temporal_results
    
    def _analyze_cumulative_effects(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze cumulative toxicity effects on contributors."""
        author_toxicity = defaultdict(list)
        
        for pr in prs:
            author = pr.get('author') or pr.get('user', {}).get('login', '')
            if not author:
                continue
            
            # Get all feedback on this PR
            comments = pr.get('comments', [])
            reviews = pr.get('reviews', [])
            
            pr_toxicity = 0
            for comment in comments:
                body = comment.get('body', '') or ''
                if body:
                    sentiment = self._calculate_sentiment_score(body)
                    pr_toxicity += sentiment['score']
            
            for review in reviews:
                body = review.get('body', '') or ''
                if body:
                    sentiment = self._calculate_sentiment_score(body)
                    pr_toxicity += sentiment['score']
            
            author_toxicity[author].append(pr_toxicity)
        
        # Analyze cumulative effects
        high_toxicity_authors = []
        for author, toxicity_scores in author_toxicity.items():
            total_toxicity = sum(toxicity_scores)
            avg_toxicity = total_toxicity / len(toxicity_scores) if toxicity_scores else 0
            
            if avg_toxicity > 2.0:  # Threshold
                high_toxicity_authors.append({
                    'author': author,
                    'total_toxicity': total_toxicity,
                    'avg_toxicity': avg_toxicity,
                    'pr_count': len(toxicity_scores)
                })
        
        # Sort by total toxicity
        high_toxicity_authors.sort(key=lambda x: x['total_toxicity'], reverse=True)
        
        return {
            'high_toxicity_authors': high_toxicity_authors[:20],  # Top 20
            'total_authors_analyzed': len(author_toxicity),
            'high_toxicity_count': len(high_toxicity_authors)
        }


def main():
    analyzer = ToxicityGradientsAnalyzer()
    analyzer.run_analysis()


if __name__ == '__main__':
    main()

