#!/usr/bin/env python3
"""
Enhanced PR Review Quality Analysis

Adds temporal trends, reviewer profiles, PR size analysis, and review type distribution.
"""

import json
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

class EnhancedReviewQualityAnalyzer:
    """Enhanced review quality analysis with temporal and reviewer-specific metrics."""
    
    def __init__(self, data_dir: Path):
        """Initialize analyzer."""
        self.data_dir = data_dir
        self.maintainers = {
            'laanwj', 'sipa', 'maflcko', 'fanquake', 'hebasto', 'jnewbery',
            'ryanofsky', 'achow101', 'theuni', 'jonasschnelli', 'Sjors',
            'promag', 'instagibbs', 'TheBlueMatt', 'jonatack', 'gmaxwell',
            'gavinandresen', 'petertodd', 'luke-jr', 'glozow'
        }
    
    def load_prs(self) -> List[Dict[str, Any]]:
        """Load PRs from JSONL file."""
        prs_file = self.data_dir / 'github' / 'prs_raw.jsonl'
        prs = []
        with open(prs_file) as f:
            for line in f:
                if line.strip():
                    prs.append(json.loads(line))
        return prs
    
    def analyze_temporal_trends(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze review quality trends by year."""
        print("Analyzing temporal trends...")
        
        year_metrics = defaultdict(lambda: {
            'reviews': [],
            'body_lengths': [],
            'word_counts': [],
            'code_references': [],
            'rubber_stamps': 0,
            'questions': 0,
            'suggestions': 0,
            'total_reviews': 0
        })
        
        for pr in prs:
            if not pr.get('merged_at'):
                continue
            
            try:
                year = datetime.fromisoformat(pr['merged_at'].replace('Z', '+00:00')).year
            except:
                continue
            
            reviews = pr.get('reviews', [])
            for review in reviews:
                body = (review.get('body') or '').strip()
                state = review.get('state', '').lower()
                
                # Skip if not a review state
                if state not in ['approved', 'changes_requested', 'commented']:
                    continue
                
                year_metrics[year]['total_reviews'] += 1
                year_metrics[year]['body_lengths'].append(len(body))
                year_metrics[year]['word_counts'].append(len(body.split()) if body else 0)
                
                # Code references
                code_refs = len(re.findall(r'`[^`]+`|#[0-9]+|L[0-9]+', body))
                year_metrics[year]['code_references'].append(code_refs)
                
                # Rubber stamps
                if len(body) < 10 and state == 'approved':
                    year_metrics[year]['rubber_stamps'] += 1
                
                # Questions
                if '?' in body:
                    year_metrics[year]['questions'] += 1
                
                # Suggestions
                if any(word in body.lower() for word in ['suggest', 'consider', 'maybe', 'could', 'might']):
                    year_metrics[year]['suggestions'] += 1
        
        # Calculate averages
        results = {}
        for year in sorted(year_metrics.keys()):
            metrics = year_metrics[year]
            total = metrics['total_reviews']
            if total == 0:
                continue
            
            results[year] = {
                'total_reviews': total,
                'avg_body_length': statistics.mean(metrics['body_lengths']) if metrics['body_lengths'] else 0,
                'median_body_length': statistics.median(metrics['body_lengths']) if metrics['body_lengths'] else 0,
                'avg_word_count': statistics.mean(metrics['word_counts']) if metrics['word_counts'] else 0,
                'avg_code_references': statistics.mean(metrics['code_references']) if metrics['code_references'] else 0,
                'rubber_stamp_rate': metrics['rubber_stamps'] / total if total > 0 else 0,
                'question_rate': metrics['questions'] / total if total > 0 else 0,
                'suggestion_rate': metrics['suggestions'] / total if total > 0 else 0,
            }
        
        return results
    
    def analyze_reviewer_profiles(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze reviewer-specific quality metrics."""
        print("Analyzing reviewer profiles...")
        
        reviewer_metrics = defaultdict(lambda: {
            'reviews': 0,
            'body_lengths': [],
            'word_counts': [],
            'code_references': [],
            'rubber_stamps': 0,
            'questions': 0,
            'suggestions': 0,
            'approvals': 0,
            'changes_requested': 0,
            'comments_only': 0,
            'is_maintainer': False
        })
        
        for pr in prs:
            reviews = pr.get('reviews', [])
            for review in reviews:
                author = (review.get('author') or '').lower()
                if not author:
                    continue
                
                state = review.get('state', '').lower()
                if state not in ['approved', 'changes_requested', 'commented']:
                    continue
                
                body = (review.get('body') or '').strip()
                
                reviewer_metrics[author]['reviews'] += 1
                reviewer_metrics[author]['body_lengths'].append(len(body))
                reviewer_metrics[author]['word_counts'].append(len(body.split()) if body else 0)
                
                # Code references
                code_refs = len(re.findall(r'`[^`]+`|#[0-9]+|L[0-9]+', body))
                reviewer_metrics[author]['code_references'].append(code_refs)
                
                # Review type
                if state == 'approved':
                    reviewer_metrics[author]['approvals'] += 1
                elif state == 'changes_requested':
                    reviewer_metrics[author]['changes_requested'] += 1
                else:
                    reviewer_metrics[author]['comments_only'] += 1
                
                # Quality indicators
                if len(body) < 10 and state == 'approved':
                    reviewer_metrics[author]['rubber_stamps'] += 1
                if '?' in body:
                    reviewer_metrics[author]['questions'] += 1
                if any(word in body.lower() for word in ['suggest', 'consider', 'maybe', 'could', 'might']):
                    reviewer_metrics[author]['suggestions'] += 1
                
                # Maintainer status
                if author in [m.lower() for m in self.maintainers]:
                    reviewer_metrics[author]['is_maintainer'] = True
        
        # Calculate averages and get top reviewers
        results = {}
        for reviewer, metrics in reviewer_metrics.items():
            if metrics['reviews'] < 10:  # Skip reviewers with < 10 reviews
                continue
            
            results[reviewer] = {
                'total_reviews': metrics['reviews'],
                'avg_body_length': statistics.mean(metrics['body_lengths']) if metrics['body_lengths'] else 0,
                'avg_word_count': statistics.mean(metrics['word_counts']) if metrics['word_counts'] else 0,
                'avg_code_references': statistics.mean(metrics['code_references']) if metrics['code_references'] else 0,
                'rubber_stamp_rate': metrics['rubber_stamps'] / metrics['reviews'],
                'question_rate': metrics['questions'] / metrics['reviews'],
                'suggestion_rate': metrics['suggestions'] / metrics['reviews'],
                'approval_rate': metrics['approvals'] / metrics['reviews'],
                'changes_requested_rate': metrics['changes_requested'] / metrics['reviews'],
                'is_maintainer': metrics['is_maintainer']
            }
        
        # Get top reviewers by volume
        top_by_volume = sorted(results.items(), key=lambda x: x[1]['total_reviews'], reverse=True)[:20]
        
        # Get top reviewers by quality (avg body length)
        top_by_quality = sorted(results.items(), key=lambda x: x[1]['avg_body_length'], reverse=True)[:20]
        
        return {
            'all_reviewers': results,
            'top_by_volume': {k: v for k, v in top_by_volume},
            'top_by_quality': {k: v for k, v in top_by_quality}
        }
    
    def analyze_pr_size_vs_quality(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze review quality by PR size."""
        print("Analyzing PR size vs review quality...")
        
        size_categories = {
            'small': {'min': 0, 'max': 100},
            'medium': {'min': 100, 'max': 1000},
            'large': {'min': 1000, 'max': float('inf')}
        }
        
        category_metrics = defaultdict(lambda: {
            'prs': 0,
            'reviews': [],
            'body_lengths': [],
            'word_counts': [],
            'code_references': [],
            'rubber_stamps': 0,
            'total_reviews': 0
        })
        
        for pr in prs:
            if not pr.get('merged', False):
                continue
            
            # Calculate PR size
            files = pr.get('files', [])
            total_changes = sum(f.get('changes', 0) for f in files)
            
            # Categorize
            category = None
            for cat, bounds in size_categories.items():
                if bounds['min'] <= total_changes < bounds['max']:
                    category = cat
                    break
            
            if not category:
                continue
            
            category_metrics[category]['prs'] += 1
            
            reviews = pr.get('reviews', [])
            for review in reviews:
                state = review.get('state', '').lower()
                if state not in ['approved', 'changes_requested', 'commented']:
                    continue
                
                body = (review.get('body') or '').strip()
                
                category_metrics[category]['total_reviews'] += 1
                category_metrics[category]['body_lengths'].append(len(body))
                category_metrics[category]['word_counts'].append(len(body.split()) if body else 0)
                
                code_refs = len(re.findall(r'`[^`]+`|#[0-9]+|L[0-9]+', body))
                category_metrics[category]['code_references'].append(code_refs)
                
                if len(body) < 10 and state == 'approved':
                    category_metrics[category]['rubber_stamps'] += 1
        
        # Calculate averages
        results = {}
        for category in size_categories.keys():
            metrics = category_metrics[category]
            total = metrics['total_reviews']
            if total == 0:
                continue
            
            results[category] = {
                'prs': metrics['prs'],
                'total_reviews': total,
                'reviews_per_pr': total / metrics['prs'] if metrics['prs'] > 0 else 0,
                'avg_body_length': statistics.mean(metrics['body_lengths']) if metrics['body_lengths'] else 0,
                'avg_word_count': statistics.mean(metrics['word_counts']) if metrics['word_counts'] else 0,
                'avg_code_references': statistics.mean(metrics['code_references']) if metrics['code_references'] else 0,
                'rubber_stamp_rate': metrics['rubber_stamps'] / total if total > 0 else 0,
            }
        
        return results
    
    def analyze_review_types(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze distribution of review types (approvals, changes requested, comments)."""
        print("Analyzing review type distribution...")
        
        review_types = {
            'approved': 0,
            'changes_requested': 0,
            'commented': 0,
            'total': 0
        }
        
        maintainer_types = defaultdict(int)
        non_maintainer_types = defaultdict(int)
        
        for pr in prs:
            reviews = pr.get('reviews', [])
            for review in reviews:
                state = review.get('state', '').lower()
                if state not in ['approved', 'changes_requested', 'commented']:
                    continue
                
                review_types[state] += 1
                review_types['total'] += 1
                
                author = (review.get('author') or '').lower()
                is_maintainer = author in [m.lower() for m in self.maintainers]
                
                if is_maintainer:
                    maintainer_types[state] += 1
                else:
                    non_maintainer_types[state] += 1
        
        return {
            'overall': {
                'approved': review_types['approved'],
                'changes_requested': review_types['changes_requested'],
                'commented': review_types['commented'],
                'total': review_types['total'],
                'approval_rate': review_types['approved'] / review_types['total'] if review_types['total'] > 0 else 0,
                'changes_requested_rate': review_types['changes_requested'] / review_types['total'] if review_types['total'] > 0 else 0,
            },
            'maintainers': {
                'approved': maintainer_types['approved'],
                'changes_requested': maintainer_types['changes_requested'],
                'commented': maintainer_types['commented'],
                'total': sum(maintainer_types.values()),
            },
            'non_maintainers': {
                'approved': non_maintainer_types['approved'],
                'changes_requested': non_maintainer_types['changes_requested'],
                'commented': non_maintainer_types['commented'],
                'total': sum(non_maintainer_types.values()),
            }
        }
    
    def run_enhanced_analysis(self) -> Dict[str, Any]:
        """Run all enhanced analyses."""
        print("="*80)
        print("ENHANCED REVIEW QUALITY ANALYSIS")
        print("="*80)
        print()
        
        prs = self.load_prs()
        print(f"Loaded {len(prs):,} PRs")
        print()
        
        results = {
            'temporal_trends': self.analyze_temporal_trends(prs),
            'reviewer_profiles': self.analyze_reviewer_profiles(prs),
            'pr_size_analysis': self.analyze_pr_size_vs_quality(prs),
            'review_types': self.analyze_review_types(prs),
            'analysis_date': datetime.now().isoformat(),
            'total_prs': len(prs)
        }
        
        return results
    
    def print_results(self, results: Dict[str, Any]):
        """Print analysis results."""
        print("="*80)
        print("ENHANCED REVIEW QUALITY ANALYSIS RESULTS")
        print("="*80)
        print()
        
        # Temporal trends
        print("TEMPORAL TRENDS (by year):")
        print("-" * 80)
        for year in sorted(results['temporal_trends'].keys()):
            metrics = results['temporal_trends'][year]
            print(f"{year}:")
            print(f"  Reviews: {metrics['total_reviews']:,}")
            print(f"  Avg body length: {metrics['avg_body_length']:.1f} chars")
            print(f"  Rubber stamp rate: {metrics['rubber_stamp_rate']*100:.1f}%")
            print(f"  Question rate: {metrics['question_rate']*100:.1f}%")
            print()
        
        # Reviewer profiles
        print("TOP REVIEWERS BY VOLUME:")
        print("-" * 80)
        for reviewer, metrics in list(results['reviewer_profiles']['top_by_volume'].items())[:10]:
            status = "MAINTAINER" if metrics['is_maintainer'] else "contributor"
            print(f"{reviewer} ({status}):")
            print(f"  Reviews: {metrics['total_reviews']:,}")
            print(f"  Avg body length: {metrics['avg_body_length']:.1f} chars")
            print(f"  Approval rate: {metrics['approval_rate']*100:.1f}%")
            print(f"  Changes requested rate: {metrics['changes_requested_rate']*100:.1f}%")
            print()
        
        # PR size analysis
        print("PR SIZE VS REVIEW QUALITY:")
        print("-" * 80)
        for size, metrics in results['pr_size_analysis'].items():
            print(f"{size.upper()} PRs ({metrics['prs']:,} PRs):")
            print(f"  Reviews per PR: {metrics['reviews_per_pr']:.1f}")
            print(f"  Avg body length: {metrics['avg_body_length']:.1f} chars")
            print(f"  Rubber stamp rate: {metrics['rubber_stamp_rate']*100:.1f}%")
            print()
        
        # Review types
        print("REVIEW TYPE DISTRIBUTION:")
        print("-" * 80)
        types = results['review_types']['overall']
        print(f"Overall:")
        print(f"  Approved: {types['approved']:,} ({types['approval_rate']*100:.1f}%)")
        print(f"  Changes requested: {types['changes_requested']:,} ({types['changes_requested_rate']*100:.1f}%)")
        print(f"  Comments only: {types['commented']:,}")
        print()


def main():
    """Main entry point."""
    import sys
    from pathlib import Path
    
    if len(sys.argv) > 1:
        data_dir = Path(sys.argv[1])
    else:
        script_dir = Path(__file__).parent.parent.parent
        data_dir = script_dir / 'data'
    
    analyzer = EnhancedReviewQualityAnalyzer(data_dir)
    results = analyzer.run_enhanced_analysis()
    analyzer.print_results(results)
    
    # Save results
    output_file = data_dir.parent / 'findings' / 'review_quality_enhanced.json'
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: {output_file}")


if __name__ == '__main__':
    main()
