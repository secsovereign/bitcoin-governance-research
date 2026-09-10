#!/usr/bin/env python3
"""
Language Evolution Analysis - Track how terminology changes over time.

Analyzes:
1. Terminology usage over time (keyword tracking)
2. New concept emergence
3. Language adoption patterns (who uses new terms first)
4. Language convergence vs divergence
"""

import json
import sys
import re
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Any, Set, Tuple, Optional
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.utils.load_prs_with_merged_by import load_prs_with_merged_by
from src.utils.cross_platform_sources import (
    extract_text_author_timestamp,
    load_all_informal_sources,
)


class LanguageEvolutionAnalyzer:
    """Analyze language evolution in Bitcoin governance."""
    
    def __init__(self, data_dir: Path):
        """Initialize."""
        self.data_dir = data_dir
        
        # Key Bitcoin terminology to track
        self.terminology = {
            'soft_fork': ['soft fork', 'softfork', 'soft-fork', 'bip9', 'versionbits'],
            'hard_fork': ['hard fork', 'hardfork', 'hard-fork'],
            'segwit': ['segwit', 'segregated witness', 'segwit2x'],
            'taproot': ['taproot', 'schnorr', 'mu sig', 'musig'],
            'lightning': ['lightning', 'lightning network', 'ln', 'payment channel'],
            'consensus': ['consensus', 'consensus rule', 'consensus change'],
            'mempool': ['mempool', 'memory pool', 'transaction pool'],
            'rbf': ['rbf', 'replace by fee', 'opt-in rbf'],
            'ctv': ['ctv', 'checktemplateverify', 'check template verify'],
            'vault': ['vault', 'covenant', 'restricted transfer'],
            'miniscript': ['miniscript', 'miniscript policy'],
            'utxo': ['utxo', 'unspent transaction output'],
            'witness': ['witness', 'witness data', 'witness program'],
            'script': ['script', 'scriptpubkey', 'script sig'],
            'bip': ['bip', 'bitcoin improvement proposal'],
            'rpc': ['rpc', 'remote procedure call', 'json-rpc'],
            'p2p': ['p2p', 'peer to peer', 'peer-to-peer'],
            'spv': ['spv', 'simplified payment verification'],
            'full_node': ['full node', 'fullnode', 'full-node'],
            'privacy': ['privacy', 'confidential', 'coinjoin', 'mixer'],
            'scaling': ['scaling', 'scalability', 'throughput', 'tps']
        }
    
    def load_prs(self) -> List[Dict[str, Any]]:
        """Load PRs with merged_by data."""
        prs_file = self.data_dir / 'github' / 'prs_raw.jsonl'
        mapping_file = self.data_dir / 'github' / 'merged_by_mapping.jsonl'
        return load_prs_with_merged_by(prs_file, mapping_file if mapping_file.exists() else None)
    
    def load_informal(self) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Load combined mailing lists, IRC, Delving, and Bitcointalk."""
        return load_all_informal_sources()
    
    def parse_timestamp(self, ts: Optional[str]) -> Optional[datetime]:
        """Parse timestamp."""
        if not ts:
            return None
        try:
            return datetime.fromisoformat(ts.replace('Z', '+00:00'))
        except:
            return None
    
    def find_terminology_mentions(self, text: str) -> Set[str]:
        """Find terminology mentions in text."""
        text_lower = text.lower()
        mentions = set()
        
        for term_key, keywords in self.terminology.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    mentions.add(term_key)
                    break
        
        return mentions
    
    def analyze_terminology_evolution(self, prs: List[Dict[str, Any]], 
                                     emails: List[Dict[str, Any]], 
                                     irc_messages: List[Dict[str, Any]],
                                     extra_informal: Optional[List[Tuple[Dict[str, Any], str]]] = None) -> Dict[str, Any]:
        """Analyze terminology usage over time."""
        print("Analyzing terminology evolution...")
        extra_informal = extra_informal or []

        # Track mentions by year
        mentions_by_year = defaultdict(lambda: defaultdict(int))
        first_mentions = {}  # term -> (year, author, platform, text_snippet)
        
        # Process PRs
        for pr in prs:
            created = self.parse_timestamp(pr.get('created_at'))
            if not created:
                continue
            
            year = created.year
            author = pr.get('author', '')
            
            # Check title and body
            text = f"{pr.get('title', '')} {pr.get('body', '')}"
            mentions = self.find_terminology_mentions(text)
            
            for term in mentions:
                mentions_by_year[year][term] += 1
                
                if term not in first_mentions:
                    snippet = text[:200] if len(text) > 200 else text
                    first_mentions[term] = {
                        'year': year,
                        'author': author,
                        'platform': 'github',
                        'snippet': snippet
                    }
            
            # Check comments
            for comment in pr.get('comments', []):
                comment_text = comment.get('body', '')
                comment_mentions = self.find_terminology_mentions(comment_text)
                comment_year = self.parse_timestamp(comment.get('created_at'))
                if comment_year:
                    comment_year = comment_year.year
                    for term in comment_mentions:
                        mentions_by_year[comment_year][term] += 1
        
        # Process emails
        for email in emails:
            date = self.parse_timestamp(email.get('date'))
            if not date:
                continue
            
            year = date.year
            author = email.get('from', '')
            
            text = f"{email.get('subject', '')} {email.get('body', '')}"
            mentions = self.find_terminology_mentions(text)
            
            for term in mentions:
                mentions_by_year[year][term] += 1
                
                if term not in first_mentions:
                    snippet = text[:200] if len(text) > 200 else text
                    first_mentions[term] = {
                        'year': year,
                        'author': author,
                        'platform': 'email',
                        'snippet': snippet
                    }
        
        # Process IRC
        for msg in irc_messages:
            timestamp = self.parse_timestamp(msg.get('timestamp') or msg.get('date'))
            if not timestamp:
                continue
            
            year = timestamp.year
            author = msg.get('nickname', '')
            
            text = msg.get('message', '')
            mentions = self.find_terminology_mentions(text)
            
            for term in mentions:
                mentions_by_year[year][term] += 1
                
                if term not in first_mentions:
                    snippet = text[:200] if len(text) > 200 else text
                    first_mentions[term] = {
                        'year': year,
                        'author': author,
                        'platform': 'irc',
                        'snippet': snippet
                    }

        for record, platform in extra_informal:
            text, author, ts = extract_text_author_timestamp(record, platform)
            parsed = self.parse_timestamp(ts)
            if not parsed:
                continue
            year = parsed.year
            mentions = self.find_terminology_mentions(text)
            for term in mentions:
                mentions_by_year[year][term] += 1
                if term not in first_mentions:
                    first_mentions[term] = {
                        'year': year,
                        'author': author,
                        'platform': platform,
                        'snippet': text[:200],
                    }
        
        # Calculate trends
        terminology_trends = {}
        for term in self.terminology.keys():
            years_data = [(year, mentions_by_year[year][term]) 
                         for year in sorted(mentions_by_year.keys())]
            
            if years_data:
                nonzero = [(year, count) for year, count in years_data if count > 0]
                if nonzero:
                    first_year, first_count = nonzero[0]
                    last_year, last_count = nonzero[-1]
                else:
                    first_year = last_year = years_data[0][0]
                    first_count = last_count = 0
                total_mentions = sum(count for _, count in years_data)

                terminology_trends[term] = {
                    'first_year': first_year,
                    'last_year': last_year,
                    'first_count': first_count,
                    'last_count': last_count,
                    'total_mentions': total_mentions,
                    'years_active': last_year - first_year + 1 if nonzero else 0,
                    'trend': (
                        'increasing' if last_count > first_count
                        else 'decreasing' if last_count < first_count
                        else 'stable'
                    ),
                    'yearly_counts': dict(years_data)
                }
        
        return {
            'terminology_trends': terminology_trends,
            'first_mentions': first_mentions,
            'total_years': len(set(mentions_by_year.keys())),
            'years_analyzed': sorted(set(mentions_by_year.keys()))
        }
    
    def analyze_language_adoption(self, prs: List[Dict[str, Any]], 
                                 emails: List[Dict[str, Any]], 
                                 irc_messages: List[Dict[str, Any]],
                                 extra_informal: Optional[List[Tuple[Dict[str, Any], str]]] = None) -> Dict[str, Any]:
        """Analyze who adopts new terminology first."""
        print("Analyzing language adoption patterns...")
        
        # Track first usage by author
        first_usage = defaultdict(lambda: defaultdict(lambda: {'year': 9999, 'platform': '', 'text': ''}))
        
        def process_text(text: str, year: int, author: str, platform: str):
            mentions = self.find_terminology_mentions(text)
            for term in mentions:
                if year < first_usage[term][author]['year']:
                    first_usage[term][author] = {
                        'year': year,
                        'platform': platform,
                        'text': text[:200]
                    }
        
        # Process all sources
        for pr in prs:
            created = self.parse_timestamp(pr.get('created_at'))
            if created:
                author = pr.get('author', '')
                text = f"{pr.get('title', '')} {pr.get('body', '')}"
                process_text(text, created.year, author, 'github')
        
        for email in emails:
            date = self.parse_timestamp(email.get('date'))
            if date:
                author = email.get('from', '')
                text = f"{email.get('subject', '')} {email.get('body', '')}"
                process_text(text, date.year, author, 'email')
        
        for msg in irc_messages:
            timestamp = self.parse_timestamp(msg.get('timestamp') or msg.get('date'))
            if timestamp:
                author = msg.get('nickname', '')
                text = msg.get('message', '')
                process_text(text, timestamp.year, author, 'irc')

        for record, platform in extra_informal or []:
            text, author, ts = extract_text_author_timestamp(record, platform)
            parsed = self.parse_timestamp(ts)
            if parsed:
                process_text(text, parsed.year, author, platform)
        
        # Find early adopters
        early_adopters = {}
        for term, authors in first_usage.items():
            if not authors:
                continue
            
            # Find earliest year
            earliest_year = min(data['year'] for data in authors.values())
            early_users = [(author, data) for author, data in authors.items() 
                          if data['year'] == earliest_year]
            
            early_adopters[term] = {
                'first_year': earliest_year,
                'early_users': [
                    {
                        'author': author,
                        'platform': data['platform'],
                        'snippet': data['text']
                    }
                    for author, data in early_users[:5]  # Top 5 early users
                ]
            }
        
        return {
            'early_adopters': early_adopters,
            'total_terms_tracked': len(self.terminology)
        }
    
    def run_analysis(self) -> Dict[str, Any]:
        """Run full analysis."""
        print("="*80)
        print("LANGUAGE EVOLUTION ANALYSIS")
        print("="*80)
        print()
        
        prs = self.load_prs()
        sources, meta = self.load_informal()
        emails = sources.get('emails') or []
        irc_messages = sources.get('irc') or []
        extra_informal = (
            [(r, 'delving') for r in (sources.get('delving') or [])]
            + [(r, 'bitcointalk') for r in (sources.get('bitcointalk') or [])]
        )

        print(
            f"Loaded {len(prs):,} PRs, {len(emails):,} emails, {len(irc_messages):,} IRC, "
            f"{len(sources.get('delving') or []):,} Delving, "
            f"{len(sources.get('bitcointalk') or []):,} Bitcointalk"
        )
        print()
        
        evolution = self.analyze_terminology_evolution(prs, emails, irc_messages, extra_informal)
        adoption = self.analyze_language_adoption(prs, emails, irc_messages, extra_informal)
        results = {
            'terminology_evolution': evolution,
            'language_adoption': adoption,
            'source_counts': {
                'prs': len(prs),
                'emails': len(emails),
                'irc': len(irc_messages),
                'delving': len(sources.get('delving') or []),
                'bitcointalk': len(sources.get('bitcointalk') or []),
                'email_meta': meta.get('email_load_meta'),
            },
            'analysis_date': datetime.now().isoformat()
        }
        
        return results
    
    def print_results(self, results: Dict[str, Any]):
        """Print results."""
        print("="*80)
        print("LANGUAGE EVOLUTION RESULTS")
        print("="*80)
        print()
        
        # Terminology trends
        print("TERMINOLOGY TRENDS")
        print("-" * 80)
        trends = results['terminology_evolution']['terminology_trends']
        for term, data in sorted(trends.items(), key=lambda x: x[1]['first_year'])[:10]:
            print(f"{term}:")
            print(f"  First year: {data['first_year']}, Last year: {data['last_year']}")
            print(f"  Total mentions: {data['total_mentions']}")
            print(f"  Trend: {data['trend']}")
            print()
        
        # Early adopters
        print("EARLY ADOPTERS (Sample)")
        print("-" * 80)
        adopters = results['language_adoption']['early_adopters']
        for term, data in list(adopters.items())[:5]:
            print(f"{term} (first used {data['first_year']}):")
            for user in data['early_users'][:3]:
                print(f"  - {user['author']} ({user['platform']})")
            print()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Language evolution analysis')
    parser.add_argument('--data-dir', type=Path, default=Path(__file__).parent.parent.parent / 'data',
                       help='Data directory')
    
    args = parser.parse_args()
    
    analyzer = LanguageEvolutionAnalyzer(args.data_dir)
    results = analyzer.run_analysis()
    analyzer.print_results(results)

    from src.utils.findings_io import save_analysis_json
    written = save_analysis_json('language_evolution.json', results)
    print(f"\nResults saved to: {', '.join(str(p) for p in written)}")


if __name__ == '__main__':
    main()

