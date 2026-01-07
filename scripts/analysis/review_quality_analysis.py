#!/usr/bin/env python3
"""
Comprehensive PR Review Quality Analysis

Analyzes review quality using quantitative metrics, qualitative assessment,
and temporal trends to understand review effectiveness.
"""

import json
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

class ReviewQualityAnalyzer:
    """Analyze PR review quality systematically."""
    
    def __init__(self, data_dir: Path):
        """Initialize analyzer."""
        self.data_dir = data_dir
        self.maintainers = {
            'laanwj', 'sipa', 'maflcko', 'fanquake', 'hebasto', 'jnewbery',
            'ryanofsky', 'achow101', 'theuni', 'jonasschnelli', 'Sjors',
            'promag', 'instagibbs', 'TheBlueMatt', 'jonatack', 'gmaxwell',
            'gavinandresen', 'petertodd', 'luke-jr', 'glozow'
        }
        
        # Topic keywords
        self.topic_keywords = {
            'security': ['security', 'vulnerability', 'exploit', 'attack', 'safe', 'unsafe', 'risk', 'threat'],
            'performance': ['performance', 'slow', 'fast', 'optimize', 'bottleneck', 'efficiency', 'speed'],
            'design': ['design', 'architecture', 'structure', 'pattern', 'refactor', 'cleanup'],
            'testing': ['test', 'coverage', 'unit', 'integration', 'fixture', 'mock'],
            'documentation': ['doc', 'comment', 'documentation', 'readme', 'explain', 'clarify'],
            'style': ['style', 'format', 'lint', 'indent', 'whitespace', 'naming']
        }
    
    def _calculate_review_depth(self, review: Dict[str, Any], pr: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate review depth metrics."""
        body = (review.get('body') or '').strip()
        review_comments = review.get('review_comments', []) or []
        
        # Count inline comments
        inline_comments = len(review_comments)
        
        # Calculate text metrics
        body_length = len(body)
        word_count = len(body.split()) if body else 0
        
        # Check for code references (line numbers, file paths)
        code_refs = len(re.findall(r'L\d+|line \d+|file:|\.(cpp|h|py|rs)', body, re.IGNORECASE))
        
        # Check for questions
        question_count = body.count('?')
        
        # Check for suggestions (imperative verbs)
        suggestion_patterns = ['should', 'could', 'might', 'consider', 'suggest', 'recommend']
        suggestion_count = sum(1 for pattern in suggestion_patterns if pattern in body.lower())
        
        return {
            'inline_comments': inline_comments,
            'body_length': body_length,
            'word_count': word_count,
            'code_references': code_refs,
            'question_count': question_count,
            'suggestion_count': suggestion_count,
            'has_code_reference': code_refs > 0,
            'has_question': question_count > 0,
            'has_suggestion': suggestion_count > 0
        }
    
    def _extract_review_topics(self, review: Dict[str, Any]) -> List[str]:
        """Extract topics mentioned in review."""
        body = (review.get('body') or '').lower()
        topics = []
        
        for topic, keywords in self.topic_keywords.items():
            if any(keyword in body for keyword in keywords):
                topics.append(topic)
        
        return topics
    
    def _classify_review_sentiment(self, review: Dict[str, Any]) -> Dict[str, Any]:
        """Classify review sentiment."""
        body = (review.get('body') or '').lower()
        state = review.get('state', '').upper()
        
        # Positive indicators
        positive_words = ['good', 'great', 'nice', 'excellent', 'perfect', 'lgtm', 'ack', 'utack', 'utcack']
        positive_count = sum(1 for word in positive_words if word in body)
        
        # Negative indicators
        negative_words = ['bad', 'wrong', 'incorrect', 'issue', 'problem', 'concern', 'worry', 'nack']
        negative_count = sum(1 for word in negative_words if word in body)
        
        # Determine sentiment
        if positive_count > negative_count and positive_count > 0:
            sentiment = 'positive'
        elif negative_count > positive_count and negative_count > 0:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'
        
        # Strength based on word count and length
        word_count = len(body.split())
        if word_count > 50 or abs(positive_count - negative_count) > 2:
            strength = 'strong'
        elif word_count > 20 or abs(positive_count - negative_count) > 0:
            strength = 'medium'
        else:
            strength = 'weak'
        
        return {
            'sentiment': sentiment,
            'strength': strength,
            'positive_indicators': positive_count,
            'negative_indicators': negative_count
        }
    
    def _calculate_review_coverage(self, pr: Dict[str, Any], reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate review coverage metrics."""
        # Get changed files
        files_changed = pr.get('files_changed', []) or []
        total_files = len(files_changed)
        
        if total_files == 0:
            return {
                'files_coverage': 0.0,
                'total_files': 0,
                'reviewed_files': 0
            }
        
        # Extract file paths from review comments
        reviewed_files = set()
        for review in reviews:
            review_comments = review.get('review_comments', []) or []
            for comment in review_comments:
                path = comment.get('path') or comment.get('file_path')
                if path:
                    reviewed_files.add(path)
        
        # Also check review body for file mentions
        for review in reviews:
            body = review.get('body', '') or ''
            # Look for file paths in body
            file_mentions = re.findall(r'[\w/]+\.(cpp|h|py|rs|md)', body, re.IGNORECASE)
            for mention in file_mentions:
                # Try to match with actual files
                for file_info in files_changed:
                    if isinstance(file_info, dict):
                        file_path = file_info.get('filename') or file_info.get('path', '')
                    else:
                        file_path = str(file_info)
                    if mention in file_path:
                        reviewed_files.add(file_path)
        
        reviewed_count = len(reviewed_files)
        coverage = reviewed_count / total_files if total_files > 0 else 0.0
        
        return {
            'files_coverage': coverage,
            'total_files': total_files,
            'reviewed_files': reviewed_count,
            'unreviewed_files': total_files - reviewed_count
        }
    
    def _identify_rubber_stamp(self, review: Dict[str, Any]) -> bool:
        """Identify rubber-stamp reviews."""
        body = (review.get('body') or '').strip()
        state = review.get('state', '').upper()
        
        # Rubber stamp indicators
        if state == 'APPROVED':
            # Very short approval
            if len(body) < 10:
                return True
            # Common rubber stamp phrases
            rubber_stamps = ['lgtm', 'ack', 'utack', 'utcack', 'looks good', 'ok']
            if any(phrase in body.lower() for phrase in rubber_stamps) and len(body) < 50:
                return True
        
        return False
    
    def analyze_review_quality(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze review quality across all PRs."""
        print("Analyzing review quality...")
        
        all_reviews = []
        review_quality_metrics = []
        
        for pr in prs:
            reviews = pr.get('reviews', []) or []
            if not reviews:
                continue
            
            for review in reviews:
                depth = self._calculate_review_depth(review, pr)
                topics = self._extract_review_topics(review)
                sentiment = self._classify_review_sentiment(review)
                is_rubber_stamp = self._identify_rubber_stamp(review)
                
                reviewer = (review.get('author') or '').lower()
                is_maintainer = reviewer in [m.lower() for m in self.maintainers]
                
                review_quality = {
                    'pr_number': pr.get('number'),
                    'reviewer': reviewer,
                    'is_maintainer': is_maintainer,
                    'state': review.get('state', ''),
                    'depth': depth,
                    'topics': topics,
                    'topic_count': len(topics),
                    'sentiment': sentiment,
                    'is_rubber_stamp': is_rubber_stamp,
                    'timestamp': review.get('submitted_at') or review.get('created_at')
                }
                
                review_quality_metrics.append(review_quality)
                all_reviews.append(review)
        
        # Calculate aggregate metrics
        return self._calculate_aggregate_metrics(review_quality_metrics, prs)
    
    def _calculate_aggregate_metrics(self, review_metrics: List[Dict], prs: List[Dict]) -> Dict[str, Any]:
        """Calculate aggregate review quality metrics."""
        if not review_metrics:
            return {}
        
        # Depth metrics
        body_lengths = [r['depth']['body_length'] for r in review_metrics]
        word_counts = [r['depth']['word_count'] for r in review_metrics]
        inline_counts = [r['depth']['inline_comments'] for r in review_metrics]
        code_ref_counts = [r['depth']['code_references'] for r in review_metrics]
        
        # Quality indicators
        rubber_stamps = sum(1 for r in review_metrics if r['is_rubber_stamp'])
        has_code_refs = sum(1 for r in review_metrics if r['depth']['has_code_reference'])
        has_questions = sum(1 for r in review_metrics if r['depth']['has_question'])
        has_suggestions = sum(1 for r in review_metrics if r['depth']['has_suggestion'])
        
        # Topic distribution
        all_topics = []
        for r in review_metrics:
            all_topics.extend(r['topics'])
        topic_dist = Counter(all_topics)
        
        # Sentiment distribution
        sentiment_dist = Counter(r['sentiment']['sentiment'] for r in review_metrics)
        
        # Maintainer vs non-maintainer
        maintainer_reviews = [r for r in review_metrics if r['is_maintainer']]
        non_maintainer_reviews = [r for r in review_metrics if not r['is_maintainer']]
        
        return {
            'total_reviews': len(review_metrics),
            'maintainer_reviews': len(maintainer_reviews),
            'non_maintainer_reviews': len(non_maintainer_reviews),
            'depth_metrics': {
                'avg_body_length': statistics.mean(body_lengths) if body_lengths else 0,
                'median_body_length': statistics.median(body_lengths) if body_lengths else 0,
                'avg_word_count': statistics.mean(word_counts) if word_counts else 0,
                'avg_inline_comments': statistics.mean(inline_counts) if inline_counts else 0,
                'avg_code_references': statistics.mean(code_ref_counts) if code_ref_counts else 0
            },
            'quality_indicators': {
                'rubber_stamp_rate': rubber_stamps / len(review_metrics) if review_metrics else 0,
                'code_reference_rate': has_code_refs / len(review_metrics) if review_metrics else 0,
                'question_rate': has_questions / len(review_metrics) if review_metrics else 0,
                'suggestion_rate': has_suggestions / len(review_metrics) if review_metrics else 0
            },
            'topic_distribution': dict(topic_dist),
            'sentiment_distribution': dict(sentiment_dist),
            'maintainer_vs_non_maintainer': self._compare_reviewer_types(maintainer_reviews, non_maintainer_reviews)
        }
    
    def _compare_reviewer_types(self, maintainer_reviews: List[Dict], non_maintainer_reviews: List[Dict]) -> Dict[str, Any]:
        """Compare maintainer vs non-maintainer review quality."""
        if not maintainer_reviews and not non_maintainer_reviews:
            return {}
        
        def calc_avg(metric_func):
            maint_vals = [metric_func(r) for r in maintainer_reviews]
            non_maint_vals = [metric_func(r) for r in non_maintainer_reviews]
            return {
                'maintainer': statistics.mean(maint_vals) if maint_vals else 0,
                'non_maintainer': statistics.mean(non_maint_vals) if non_maint_vals else 0
            }
        
        return {
            'body_length': calc_avg(lambda r: r['depth']['body_length']),
            'word_count': calc_avg(lambda r: r['depth']['word_count']),
            'inline_comments': calc_avg(lambda r: r['depth']['inline_comments']),
            'code_references': calc_avg(lambda r: r['depth']['code_references']),
            'rubber_stamp_rate': {
                'maintainer': sum(1 for r in maintainer_reviews if r['is_rubber_stamp']) / len(maintainer_reviews) if maintainer_reviews else 0,
                'non_maintainer': sum(1 for r in non_maintainer_reviews if r['is_rubber_stamp']) / len(non_maintainer_reviews) if non_maintainer_reviews else 0
            },
            'topic_count': calc_avg(lambda r: r['topic_count'])
        }
    
    def analyze_pr_coverage(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze review coverage across PRs."""
        print("Analyzing review coverage...")
        
        coverage_metrics = []
        for pr in prs:
            reviews = pr.get('reviews', []) or []
            if not reviews:
                continue
            
            coverage = self._calculate_review_coverage(pr, reviews)
            coverage['pr_number'] = pr.get('number')
            coverage['total_reviews'] = len(reviews)
            coverage_metrics.append(coverage)
        
        if not coverage_metrics:
            return {}
        
        avg_coverage = statistics.mean(c['files_coverage'] for c in coverage_metrics)
        median_coverage = statistics.median(c['files_coverage'] for c in coverage_metrics)
        
        return {
            'total_prs_analyzed': len(coverage_metrics),
            'avg_files_coverage': avg_coverage,
            'median_files_coverage': median_coverage,
            'prs_with_full_coverage': sum(1 for c in coverage_metrics if c['files_coverage'] >= 1.0),
            'prs_with_zero_coverage': sum(1 for c in coverage_metrics if c['files_coverage'] == 0.0)
        }
    
    def run_analysis(self) -> Dict[str, Any]:
        """Run complete review quality analysis."""
        print("="*80)
        print("PR REVIEW QUALITY ANALYSIS")
        print("="*80)
        print()
        
        # Load PRs
        prs = []
        pr_file = self.data_dir / 'github' / 'prs_raw.jsonl'
        print(f"Loading PRs from {pr_file}...")
        with open(pr_file) as f:
            for line in f:
                if line.strip():
                    prs.append(json.loads(line))
        
        print(f"Loaded {len(prs):,} PRs")
        print()
        
        # Analyze review quality
        quality_metrics = self.analyze_review_quality(prs)
        
        # Analyze coverage
        coverage_metrics = self.analyze_pr_coverage(prs)
        
        # Combine results
        results = {
            'quality_metrics': quality_metrics,
            'coverage_metrics': coverage_metrics,
            'analysis_date': datetime.now().isoformat(),
            'total_prs': len(prs)
        }
        
        return results
    
    def print_results(self, results: Dict[str, Any]):
        """Print analysis results."""
        print("="*80)
        print("REVIEW QUALITY ANALYSIS RESULTS")
        print("="*80)
        print()
        
        quality = results.get('quality_metrics', {})
        coverage = results.get('coverage_metrics', {})
        
        print("REVIEW DEPTH METRICS:")
        print("-"*80)
        depth = quality.get('depth_metrics', {})
        print(f"  Average body length: {depth.get('avg_body_length', 0):.1f} characters")
        print(f"  Median body length: {depth.get('median_body_length', 0):.1f} characters")
        print(f"  Average word count: {depth.get('avg_word_count', 0):.1f} words")
        print(f"  Average inline comments: {depth.get('avg_inline_comments', 0):.2f}")
        print(f"  Average code references: {depth.get('avg_code_references', 0):.2f}")
        print()
        
        print("QUALITY INDICATORS:")
        print("-"*80)
        indicators = quality.get('quality_indicators', {})
        print(f"  Rubber stamp rate: {indicators.get('rubber_stamp_rate', 0)*100:.1f}%")
        print(f"  Code reference rate: {indicators.get('code_reference_rate', 0)*100:.1f}%")
        print(f"  Question rate: {indicators.get('question_rate', 0)*100:.1f}%")
        print(f"  Suggestion rate: {indicators.get('suggestion_rate', 0)*100:.1f}%")
        print()
        
        print("TOPIC DISTRIBUTION:")
        print("-"*80)
        topics = quality.get('topic_distribution', {})
        for topic, count in sorted(topics.items(), key=lambda x: x[1], reverse=True):
            print(f"  {topic}: {count}")
        print()
        
        print("SENTIMENT DISTRIBUTION:")
        print("-"*80)
        sentiment = quality.get('sentiment_distribution', {})
        total = sum(sentiment.values())
        for sent, count in sorted(sentiment.items(), key=lambda x: x[1], reverse=True):
            pct = count / total * 100 if total > 0 else 0
            print(f"  {sent}: {count} ({pct:.1f}%)")
        print()
        
        print("MAINTAINER VS NON-MAINTAINER:")
        print("-"*80)
        comparison = quality.get('maintainer_vs_non_maintainer', {})
        if comparison:
            print("  Body length:")
            print(f"    Maintainer: {comparison.get('body_length', {}).get('maintainer', 0):.1f} chars")
            print(f"    Non-maintainer: {comparison.get('body_length', {}).get('non_maintainer', 0):.1f} chars")
            print()
            print("  Rubber stamp rate:")
            print(f"    Maintainer: {comparison.get('rubber_stamp_rate', {}).get('maintainer', 0)*100:.1f}%")
            print(f"    Non-maintainer: {comparison.get('rubber_stamp_rate', {}).get('non_maintainer', 0)*100:.1f}%")
        print()
        
        print("REVIEW COVERAGE:")
        print("-"*80)
        print(f"  PRs analyzed: {coverage.get('total_prs_analyzed', 0):,}")
        print(f"  Average files coverage: {coverage.get('avg_files_coverage', 0)*100:.1f}%")
        print(f"  Median files coverage: {coverage.get('median_files_coverage', 0)*100:.1f}%")
        print(f"  PRs with full coverage: {coverage.get('prs_with_full_coverage', 0):,}")
        print(f"  PRs with zero coverage: {coverage.get('prs_with_zero_coverage', 0):,}")
        print()


def main():
    """Main entry point."""
    import sys
    from pathlib import Path
    
    # Get data directory
    if len(sys.argv) > 1:
        data_dir = Path(sys.argv[1])
    else:
        # Default to commons-research/data
        script_dir = Path(__file__).parent.parent.parent
        data_dir = script_dir / 'data'
    
    analyzer = ReviewQualityAnalyzer(data_dir)
    results = analyzer.run_analysis()
    analyzer.print_results(results)
    
    # Save results
    output_file = data_dir.parent / 'findings' / 'review_quality_analysis.json'
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: {output_file}")


if __name__ == '__main__':
    main()
