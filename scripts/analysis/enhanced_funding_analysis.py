#!/usr/bin/env python3
"""
Enhanced Funding Analysis

Extracts more structured data from funding mentions, including:
- Temporal patterns
- Funding source identification
- Maintainer vs non-maintainer funding mentions
- Correlation with PR outcomes
"""

import json
import sys
import re
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Any
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.utils.load_prs_with_merged_by import load_prs_with_merged_by

class EnhancedFundingAnalyzer:
    """Enhanced funding analysis with temporal and structured data extraction."""
    
    def __init__(self, data_dir: Path):
        """Initialize."""
        self.data_dir = data_dir
        self.maintainers = {
            'laanwj', 'sipa', 'maflcko', 'fanquake', 'hebasto', 'jnewbery',
            'ryanofsky', 'achow101', 'theuni', 'jonasschnelli', 'Sjors',
            'promag', 'instagibbs', 'TheBlueMatt', 'jonatack', 'gmaxwell',
            'gavinandresen', 'petertodd', 'luke-jr', 'glozow'
        }
        
        # Enhanced funding patterns
        self.funding_patterns = {
            'grant': r'\b(grant|grants|funding|funded|sponsor|sponsorship|sponsored)\b',
            'corporate': r'\b(corporate|company|business|enterprise|commercial|employer)\b',
            'foundation': r'\b(foundation|non-profit|nonprofit|ngo)\b',
            'donation': r'\b(donation|donate|donor|contribute|contribution)\b',
            'salary': r'\b(salary|paid|payment|compensation|wage|stipend)\b',
            'research': r'\b(research grant|academic|university|institution)\b',
            'bounty': r'\b(bounty|bounties|reward|prize)\b'
        }
        
        self.funding_sources = [
            'bitcoin foundation', 'human rights foundation', 'hrf',
            'open technology fund', 'otf', 'chaincode', 'blockstream',
            'square', 'block', 'coinbase', 'kraken', 'binance', 'mit', 'stanford',
            'digital currency group', 'dcg', 'bitmain', 'bitmaintech'
        ]
    
    def load_prs(self) -> List[Dict[str, Any]]:
        """Load PRs with merged_by data."""
        prs_file = self.data_dir / 'github' / 'prs_raw.jsonl'
        mapping_file = self.data_dir / 'github' / 'merged_by_mapping.jsonl'
        return load_prs_with_merged_by(prs_file, mapping_file if mapping_file.exists() else None)
    
    def extract_structured_funding(self, text: str) -> Dict[str, Any]:
        """Extract structured funding information from text."""
        if not text:
            return {}
        
        text_lower = text.lower()
        result = {
            'has_funding': False,
            'funding_types': [],
            'sources_mentioned': [],
            'amount_mentions': [],
            'temporal_indicators': []
        }
        
        # Check funding patterns
        for funding_type, pattern in self.funding_patterns.items():
            if re.search(pattern, text_lower):
                result['has_funding'] = True
                result['funding_types'].append(funding_type)
        
        # Check funding sources
        for source in self.funding_sources:
            if source in text_lower:
                result['sources_mentioned'].append(source)
        
        # Try to extract amounts (if mentioned)
        amount_patterns = [
            r'\$[\d,]+',
            r'\d+[km]?\s*(usd|dollars?)',
            r'[\d,]+\s*(usd|dollars?)'
        ]
        for pattern in amount_patterns:
            matches = re.findall(pattern, text_lower)
            if matches:
                result['amount_mentions'].extend(matches)
        
        # Temporal indicators
        temporal_patterns = [
            r'\d{4}',  # Years
            r'(this year|last year|next year)',
            r'(q[1-4]|quarter)'
        ]
        for pattern in temporal_patterns:
            if re.search(pattern, text_lower):
                result['temporal_indicators'].append(pattern)
        
        return result
    
    def analyze_temporal_funding_patterns(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze funding mentions over time."""
        print("Analyzing temporal funding patterns...")
        
        by_year = defaultdict(lambda: {
            'total_prs': 0,
            'with_funding': 0,
            'maintainer_with_funding': 0,
            'non_maintainer_with_funding': 0,
            'funding_types': Counter(),
            'sources': Counter()
        })
        
        for pr in prs:
            created = pr.get('created_at')
            if not created:
                continue
            
            try:
                year = datetime.fromisoformat(created.replace('Z', '+00:00')).year
            except:
                continue
            
            by_year[year]['total_prs'] += 1
            
            # Check for funding
            body = (pr.get('body') or '').lower()
            title = (pr.get('title') or '').lower()
            combined = f"{title} {body}"
            
            funding_data = self.extract_structured_funding(combined)
            
            if funding_data.get('has_funding'):
                by_year[year]['with_funding'] += 1
                
                author = (pr.get('author') or '').lower()
                is_maintainer = author in [m.lower() for m in self.maintainers]
                
                if is_maintainer:
                    by_year[year]['maintainer_with_funding'] += 1
                else:
                    by_year[year]['non_maintainer_with_funding'] += 1
                
                for funding_type in funding_data.get('funding_types', []):
                    by_year[year]['funding_types'][funding_type] += 1
                
                for source in funding_data.get('sources_mentioned', []):
                    by_year[year]['sources'][source] += 1
        
        # Calculate rates
        results = {}
        for year in sorted(by_year.keys()):
            stats = by_year[year]
            if stats['total_prs'] < 50:
                continue
            
            results[year] = {
                'total_prs': stats['total_prs'],
                'funding_mention_rate': stats['with_funding'] / stats['total_prs'] if stats['total_prs'] > 0 else 0,
                'maintainer_funding_rate': stats['maintainer_with_funding'] / stats['with_funding'] if stats['with_funding'] > 0 else 0,
                'top_funding_types': dict(stats['funding_types'].most_common(5)),
                'top_sources': dict(stats['sources'].most_common(5))
            }
        
        return results
    
    def analyze_funding_correlation_enhanced(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Enhanced funding correlation analysis."""
        print("Analyzing enhanced funding correlations...")
        
        with_funding = []
        without_funding = []
        
        for pr in prs:
            body = (pr.get('body') or '').lower()
            title = (pr.get('title') or '').lower()
            combined = f"{title} {body}"
            
            funding_data = self.extract_structured_funding(combined)
            
            pr_data = {
                'pr': pr,
                'funding_data': funding_data,
                'is_maintainer': (pr.get('author') or '').lower() in [m.lower() for m in self.maintainers]
            }
            
            if funding_data.get('has_funding'):
                with_funding.append(pr_data)
            else:
                without_funding.append(pr_data)
        
        def analyze_group(group, group_name):
            merged = [p for p in group if p['pr'].get('merged', False)]
            
            # Time to merge
            times = []
            for p in merged:
                created = p['pr'].get('created_at')
                merged_at = p['pr'].get('merged_at')
                if created and merged_at:
                    try:
                        created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                        merged_dt = datetime.fromisoformat(merged_at.replace('Z', '+00:00'))
                        days = (merged_dt - created_dt).total_seconds() / 86400
                        if days >= 0:
                            times.append(days)
                    except:
                        pass
            
            # Funding types distribution
            funding_types = Counter()
            sources = Counter()
            for p in group:
                for ft in p['funding_data'].get('funding_types', []):
                    funding_types[ft] += 1
                for s in p['funding_data'].get('sources_mentioned', []):
                    sources[s] += 1
            
            return {
                'total': len(group),
                'merged': len(merged),
                'merge_rate': len(merged) / len(group) if group else 0,
                'avg_time_to_merge': sum(times) / len(times) if times else 0,
                'avg_reviews': sum(len(p['pr'].get('reviews', [])) for p in merged) / len(merged) if merged else 0,
                'funding_types': dict(funding_types.most_common(10)),
                'sources': dict(sources.most_common(10)),
                'maintainer_rate': sum(1 for p in group if p['is_maintainer']) / len(group) if group else 0
            }
        
        return {
            'with_funding': analyze_group(with_funding, 'with_funding'),
            'without_funding': analyze_group(without_funding, 'without_funding')
        }
    
    def run_all_analyses(self) -> Dict[str, Any]:
        """Run all enhanced funding analyses."""
        print("="*80)
        print("ENHANCED FUNDING ANALYSIS")
        print("="*80)
        print()
        
        prs = self.load_prs()
        print(f"Loaded {len(prs):,} PRs")
        print()
        
        results = {
            'temporal_patterns': self.analyze_temporal_funding_patterns(prs),
            'enhanced_correlation': self.analyze_funding_correlation_enhanced(prs),
            'analysis_date': datetime.now().isoformat()
        }
        
        return results
    
    def print_results(self, results: Dict[str, Any]):
        """Print results."""
        print("="*80)
        print("ENHANCED FUNDING ANALYSIS RESULTS")
        print("="*80)
        print()
        
        # Temporal patterns
        print("TEMPORAL FUNDING PATTERNS")
        print("-" * 80)
        temporal = results['temporal_patterns']
        print("Year | Total PRs | Funding Rate | Top Type | Top Source")
        print("-" * 80)
        for year in sorted(temporal.keys())[-10:]:
            stats = temporal[year]
            top_type = list(stats['top_funding_types'].keys())[0] if stats['top_funding_types'] else 'N/A'
            top_source = list(stats['top_sources'].keys())[0] if stats['top_sources'] else 'N/A'
            print(f"{year} | {stats['total_prs']:9d} | {stats['funding_mention_rate']*100:11.1f}% | {top_type:8s} | {top_source}")
        print()
        
        # Enhanced correlation
        print("ENHANCED FUNDING CORRELATION")
        print("-" * 80)
        corr = results['enhanced_correlation']
        print("With funding mentions:")
        print(f"  Merge rate: {corr['with_funding']['merge_rate']*100:.1f}%")
        print(f"  Avg time to merge: {corr['with_funding']['avg_time_to_merge']:.1f} days")
        print(f"  Avg reviews: {corr['with_funding']['avg_reviews']:.1f}")
        print(f"  Top funding type: {list(corr['with_funding']['funding_types'].keys())[0] if corr['with_funding']['funding_types'] else 'N/A'}")
        print()
        print("Without funding mentions:")
        print(f"  Merge rate: {corr['without_funding']['merge_rate']*100:.1f}%")
        print(f"  Avg time to merge: {corr['without_funding']['avg_time_to_merge']:.1f} days")
        print(f"  Avg reviews: {corr['without_funding']['avg_reviews']:.1f}")
        print()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced funding analysis')
    parser.add_argument('--data-dir', type=Path, default=Path(__file__).parent.parent.parent / 'data',
                       help='Data directory')
    parser.add_argument('--output', type=Path, default=Path(__file__).parent.parent.parent / 'findings' / 'enhanced_funding_analysis.json',
                       help='Output JSON file')
    
    args = parser.parse_args()
    
    analyzer = EnhancedFundingAnalyzer(args.data_dir)
    results = analyzer.run_all_analyses()
    analyzer.print_results(results)
    
    # Save results
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nResults saved to: {args.output}")


if __name__ == '__main__':
    main()
