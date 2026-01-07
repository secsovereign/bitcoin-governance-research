#!/usr/bin/env python3
"""
Detailed Merge Pattern Analysis

Analyzes:
1. Self-merge rate breakdown
2. Self-merge by review count (0, 1, 2+ reviews)
3. Merge relationships (who merges whose PRs)
4. "Friend" patterns (consistent merger-author pairs)
5. "Janitor" patterns (one person merges many different people's PRs)
"""

import json
import sys
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Any, Tuple
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.utils.load_prs_with_merged_by import load_prs_with_merged_by

class MergePatternAnalyzer:
    """Analyze merge patterns in detail."""
    
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
        """Load PRs with merged_by data."""
        prs_file = self.data_dir / 'github' / 'prs_raw.jsonl'
        mapping_file = self.data_dir / 'github' / 'merged_by_mapping.jsonl'
        
        return load_prs_with_merged_by(prs_file, mapping_file if mapping_file.exists() else None)
    
    def analyze_self_merge_breakdown(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Break down self-merge by review count."""
        print("Analyzing self-merge breakdown...")
        
        maintainer_merged = []
        for pr in prs:
            if not pr.get('merged', False):
                continue
            author = (pr.get('author') or '').lower()
            if author in [m.lower() for m in self.maintainers]:
                maintainer_merged.append(pr)
        
        # Categorize by self-merge and review count
        self_merge_by_reviews = {
            'zero_reviews': [],
            'one_review': [],
            'two_plus_reviews': []
        }
        
        other_merge_by_reviews = {
            'zero_reviews': [],
            'one_review': [],
            'two_plus_reviews': []
        }
        
        for pr in maintainer_merged:
            author = (pr.get('author') or '').lower()
            merged_by = (pr.get('merged_by') or '').lower()
            reviews = pr.get('reviews', [])
            review_count = len([r for r in reviews if r.get('state', '').lower() in ['approved', 'changes_requested', 'commented']])
            
            is_self_merge = merged_by and author and merged_by == author
            
            if review_count == 0:
                category = 'zero_reviews'
            elif review_count == 1:
                category = 'one_review'
            else:
                category = 'two_plus_reviews'
            
            if is_self_merge:
                self_merge_by_reviews[category].append(pr)
            else:
                other_merge_by_reviews[category].append(pr)
        
        total_self_merged = sum(len(v) for v in self_merge_by_reviews.values())
        total_other_merged = sum(len(v) for v in other_merge_by_reviews.values())
        
        return {
            'total_maintainer_merged': len(maintainer_merged),
            'total_self_merged': total_self_merged,
            'total_other_merged': total_other_merged,
            'self_merge_rate': total_self_merged / len(maintainer_merged) if maintainer_merged else 0,
            'self_merge_by_reviews': {
                'zero_reviews': {
                    'count': len(self_merge_by_reviews['zero_reviews']),
                    'rate': len(self_merge_by_reviews['zero_reviews']) / total_self_merged if total_self_merged > 0 else 0,
                    'rate_of_all': len(self_merge_by_reviews['zero_reviews']) / len(maintainer_merged) if maintainer_merged else 0
                },
                'one_review': {
                    'count': len(self_merge_by_reviews['one_review']),
                    'rate': len(self_merge_by_reviews['one_review']) / total_self_merged if total_self_merged > 0 else 0,
                    'rate_of_all': len(self_merge_by_reviews['one_review']) / len(maintainer_merged) if maintainer_merged else 0
                },
                'two_plus_reviews': {
                    'count': len(self_merge_by_reviews['two_plus_reviews']),
                    'rate': len(self_merge_by_reviews['two_plus_reviews']) / total_self_merged if total_self_merged > 0 else 0,
                    'rate_of_all': len(self_merge_by_reviews['two_plus_reviews']) / len(maintainer_merged) if maintainer_merged else 0
                }
            },
            'other_merge_by_reviews': {
                'zero_reviews': {
                    'count': len(other_merge_by_reviews['zero_reviews']),
                    'rate': len(other_merge_by_reviews['zero_reviews']) / total_other_merged if total_other_merged > 0 else 0
                },
                'one_review': {
                    'count': len(other_merge_by_reviews['one_review']),
                    'rate': len(other_merge_by_reviews['one_review']) / total_other_merged if total_other_merged > 0 else 0
                },
                'two_plus_reviews': {
                    'count': len(other_merge_by_reviews['two_plus_reviews']),
                    'rate': len(other_merge_by_reviews['two_plus_reviews']) / total_other_merged if total_other_merged > 0 else 0
                }
            }
        }
    
    def analyze_merge_relationships(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze who merges whose PRs."""
        print("Analyzing merge relationships...")
        
        merged_prs = [p for p in prs if p.get('merged', False) and p.get('merged_by')]
        
        # Build relationship maps
        author_to_merger = defaultdict(Counter)  # For each author, who merges their PRs
        merger_to_authors = defaultdict(Counter)  # For each merger, whose PRs they merge
        merger_author_pairs = Counter()  # (merger, author) pairs
        
        for pr in merged_prs:
            author = (pr.get('author') or '').lower()
            merged_by = (pr.get('merged_by') or '').lower()
            
            if not author or not merged_by:
                continue
            
            author_to_merger[author][merged_by] += 1
            merger_to_authors[merged_by][author] += 1
            merger_author_pairs[(merged_by, author)] += 1
        
        # Identify "friend" patterns (consistent merger-author pairs)
        # A "friend" is someone who merges a specific person's PRs frequently
        friend_patterns = []
        for (merger, author), count in merger_author_pairs.most_common():
            if merger == author:  # Skip self-merges
                continue
            
            # Calculate what % of author's PRs this merger handles
            author_total = sum(author_to_merger[author].values())
            if author_total > 0:
                pct = count / author_total * 100
                if pct >= 20:  # Merger handles 20%+ of author's PRs
                    friend_patterns.append({
                        'merger': merger,
                        'author': author,
                        'count': count,
                        'pct_of_author_prs': pct,
                        'is_maintainer_merger': merger in [m.lower() for m in self.maintainers],
                        'is_maintainer_author': author in [m.lower() for m in self.maintainers]
                    })
        
        # Sort by count
        friend_patterns.sort(key=lambda x: x['count'], reverse=True)
        
        # Identify "janitor" patterns (one person merges many different people's PRs)
        janitor_patterns = []
        for merger, authors in merger_to_authors.items():
            if merger in [m.lower() for m in self.maintainers]:
                unique_authors = len(authors)
                total_merges = sum(authors.values())
                if unique_authors >= 10:  # Merges PRs from 10+ different authors
                    janitor_patterns.append({
                        'merger': merger,
                        'unique_authors': unique_authors,
                        'total_merges': total_merges,
                        'avg_per_author': total_merges / unique_authors if unique_authors > 0 else 0,
                        'top_authors': dict(authors.most_common(5))
                    })
        
        # Sort by unique authors
        janitor_patterns.sort(key=lambda x: x['unique_authors'], reverse=True)
        
        # Top mergers overall
        merger_counts = Counter()
        for pr in merged_prs:
            merged_by = (pr.get('merged_by') or '').lower()
            if merged_by:
                merger_counts[merged_by] += 1
        
        return {
            'total_merged_prs': len(merged_prs),
            'unique_mergers': len(merger_counts),
            'top_mergers': dict(merger_counts.most_common(20)),
            'friend_patterns': friend_patterns[:50],  # Top 50
            'janitor_patterns': janitor_patterns,
            'merger_author_matrix': {
                'total_pairs': len(merger_author_pairs),
                'top_pairs': {f"{k[0]}_merges_{k[1]}": v for k, v in merger_author_pairs.most_common(30)}
            }
        }
    
    def analyze_individual_self_merge_patterns(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze self-merge patterns by individual maintainer."""
        print("Analyzing individual self-merge patterns...")
        
        maintainer_merged = []
        for pr in prs:
            if not pr.get('merged', False):
                continue
            author = (pr.get('author') or '').lower()
            if author in [m.lower() for m in self.maintainers]:
                maintainer_merged.append(pr)
        
        # Group by maintainer
        maintainer_stats = defaultdict(lambda: {
            'total_merged': 0,
            'self_merged': 0,
            'other_merged': 0,
            'self_merge_by_reviews': {
                'zero': 0,
                'one': 0,
                'two_plus': 0
            }
        })
        
        for pr in maintainer_merged:
            author = (pr.get('author') or '').lower()
            merged_by = (pr.get('merged_by') or '').lower()
            reviews = pr.get('reviews', [])
            review_count = len([r for r in reviews if r.get('state', '').lower() in ['approved', 'changes_requested', 'commented']])
            
            maintainer_stats[author]['total_merged'] += 1
            
            if merged_by and author and merged_by == author:
                maintainer_stats[author]['self_merged'] += 1
                if review_count == 0:
                    maintainer_stats[author]['self_merge_by_reviews']['zero'] += 1
                elif review_count == 1:
                    maintainer_stats[author]['self_merge_by_reviews']['one'] += 1
                else:
                    maintainer_stats[author]['self_merge_by_reviews']['two_plus'] += 1
            else:
                maintainer_stats[author]['other_merged'] += 1
        
        # Convert to list and calculate rates
        results = []
        for maintainer, stats in maintainer_stats.items():
            if stats['total_merged'] == 0:
                continue
            
            results.append({
                'maintainer': maintainer,
                'total_merged': stats['total_merged'],
                'self_merged': stats['self_merged'],
                'other_merged': stats['other_merged'],
                'self_merge_rate': stats['self_merged'] / stats['total_merged'] if stats['total_merged'] > 0 else 0,
                'self_merge_by_reviews': {
                    'zero': stats['self_merge_by_reviews']['zero'],
                    'one': stats['self_merge_by_reviews']['one'],
                    'two_plus': stats['self_merge_by_reviews']['two_plus']
                },
                'self_merge_zero_review_rate': stats['self_merge_by_reviews']['zero'] / stats['self_merged'] if stats['self_merged'] > 0 else 0
            })
        
        # Sort by total merged
        results.sort(key=lambda x: x['total_merged'], reverse=True)
        
        return {
            'maintainers': results,
            'summary': {
                'total_maintainers': len(results),
                'avg_self_merge_rate': sum(r['self_merge_rate'] for r in results) / len(results) if results else 0,
                'avg_zero_review_self_merge_rate': sum(r['self_merge_zero_review_rate'] for r in results) / len(results) if results else 0
            }
        }
    
    def run_analysis(self) -> Dict[str, Any]:
        """Run all analyses."""
        print("="*80)
        print("DETAILED MERGE PATTERN ANALYSIS")
        print("="*80)
        print()
        
        prs = self.load_prs()
        print(f"Loaded {len(prs):,} PRs")
        print()
        
        results = {
            'self_merge_breakdown': self.analyze_self_merge_breakdown(prs),
            'merge_relationships': self.analyze_merge_relationships(prs),
            'individual_patterns': self.analyze_individual_self_merge_patterns(prs),
            'analysis_date': datetime.now().isoformat()
        }
        
        return results
    
    def print_results(self, results: Dict[str, Any]):
        """Print analysis results."""
        print("="*80)
        print("MERGE PATTERN ANALYSIS RESULTS")
        print("="*80)
        print()
        
        # Self-merge breakdown
        sm = results['self_merge_breakdown']
        print("SELF-MERGE BREAKDOWN")
        print("-" * 80)
        print(f"Total maintainer merged PRs: {sm['total_maintainer_merged']:,}")
        print(f"Self-merged: {sm['total_self_merged']:,} ({sm['self_merge_rate']*100:.1f}%)")
        print(f"Other-merged: {sm['total_other_merged']:,} ({100-sm['self_merge_rate']*100:.1f}%)")
        print()
        print("Self-merge by review count:")
        for category, data in sm['self_merge_by_reviews'].items():
            print(f"  {category.replace('_', ' ').title()}:")
            print(f"    Count: {data['count']:,} ({data['rate']*100:.1f}% of self-merges, {data['rate_of_all']*100:.1f}% of all maintainer PRs)")
        print()
        
        # Merge relationships
        mr = results['merge_relationships']
        print("MERGE RELATIONSHIPS")
        print("-" * 80)
        print(f"Total merged PRs: {mr['total_merged_prs']:,}")
        print(f"Unique mergers: {mr['unique_mergers']:,}")
        print()
        print("Top 10 mergers:")
        for merger, count in list(mr['top_mergers'].items())[:10]:
            print(f"  {merger}: {count:,} merges")
        print()
        
        # Friend patterns
        print("FRIEND PATTERNS (consistent merger-author pairs)")
        print("-" * 80)
        print(f"Found {len(mr['friend_patterns'])} significant patterns")
        print()
        print("Top 20 friend patterns:")
        for i, pattern in enumerate(mr['friend_patterns'][:20], 1):
            print(f"  {i}. {pattern['merger']} merges {pattern['author']}'s PRs:")
            print(f"     {pattern['count']:,} merges ({pattern['pct_of_author_prs']:.1f}% of {pattern['author']}'s PRs)")
        print()
        
        # Janitor patterns
        print("JANITOR PATTERNS (one person merges many different authors)")
        print("-" * 80)
        print(f"Found {len(mr['janitor_patterns'])} janitors")
        print()
        for pattern in mr['janitor_patterns'][:10]:
            print(f"  {pattern['merger']}:")
            print(f"    Merges PRs from {pattern['unique_authors']:,} different authors")
            print(f"    Total merges: {pattern['total_merges']:,}")
            print(f"    Avg per author: {pattern['avg_per_author']:.1f}")
            print(f"    Top authors: {', '.join(pattern['top_authors'].keys())}")
        print()
        
        # Individual patterns
        ip = results['individual_patterns']
        print("INDIVIDUAL MAINTAINER SELF-MERGE PATTERNS")
        print("-" * 80)
        print(f"Total maintainers analyzed: {ip['summary']['total_maintainers']}")
        print(f"Average self-merge rate: {ip['summary']['avg_self_merge_rate']*100:.1f}%")
        print(f"Average zero-review self-merge rate: {ip['summary']['avg_zero_review_self_merge_rate']*100:.1f}%")
        print()
        print("Top 15 maintainers by total merges:")
        for maintainer in ip['maintainers'][:15]:
            print(f"  {maintainer['maintainer']}:")
            print(f"    Total merged: {maintainer['total_merged']:,}")
            print(f"    Self-merge rate: {maintainer['self_merge_rate']*100:.1f}% ({maintainer['self_merged']:,}/{maintainer['total_merged']:,})")
            print(f"    Self-merge by reviews: 0={maintainer['self_merge_by_reviews']['zero']}, 1={maintainer['self_merge_by_reviews']['one']}, 2+={maintainer['self_merge_by_reviews']['two_plus']}")
        print()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze merge patterns in detail')
    parser.add_argument('--data-dir', type=Path, default=Path(__file__).parent.parent.parent / 'data',
                       help='Data directory')
    parser.add_argument('--output', type=Path, default=Path(__file__).parent.parent.parent / 'findings' / 'merge_pattern_analysis.json',
                       help='Output JSON file')
    
    args = parser.parse_args()
    
    analyzer = MergePatternAnalyzer(args.data_dir)
    results = analyzer.run_analysis()
    analyzer.print_results(results)
    
    # Save results
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: {args.output}")


if __name__ == '__main__':
    main()
