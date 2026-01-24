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
    
    def load_emails(self) -> List[Dict[str, Any]]:
        """Load email data."""
        emails_file = self.data_dir / 'processed' / 'cleaned_emails.jsonl'
        if not emails_file.exists():
            return []
        
        emails = []
        with open(emails_file, 'r') as f:
            for line in f:
                emails.append(json.loads(line))
        return emails
    
    def load_irc(self) -> List[Dict[str, Any]]:
        """Load IRC data."""
        irc_file = self.data_dir / 'processed' / 'cleaned_irc.jsonl'
        if not irc_file.exists():
            return []
        
        messages = []
        with open(irc_file, 'r') as f:
            for line in f:
                messages.append(json.loads(line))
        return messages
    
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
                                     irc_messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze terminology usage over time."""
        print("Analyzing terminology evolution...")
        
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
        
        # Calculate trends
        terminology_trends = {}
        for term in self.terminology.keys():
            years_data = [(year, mentions_by_year[year][term]) 
                         for year in sorted(mentions_by_year.keys())]
            
            if years_data:
                first_year = years_data[0][0]
                last_year = years_data[-1][0]
                first_count = years_data[0][1]
                last_count = years_data[-1][1]
                total_mentions = sum(count for _, count in years_data)
                
                terminology_trends[term] = {
                    'first_year': first_year,
                    'last_year': last_year,
                    'first_count': first_count,
                    'last_count': last_count,
                    'total_mentions': total_mentions,
                    'years_active': last_year - first_year + 1,
                    'trend': 'increasing' if last_count > first_count else 'decreasing' if last_count < first_count else 'stable',
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
                                 irc_messages: List[Dict[str, Any]]) -> Dict[str, Any]:
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
        emails = self.load_emails()
        irc_messages = self.load_irc()
        
        print(f"Loaded {len(prs):,} PRs, {len(emails):,} emails, {len(irc_messages):,} IRC messages")
        print()
        
        evolution = self.analyze_terminology_evolution(prs, emails, irc_messages)
        adoption = self.analyze_language_adoption(prs, emails, irc_messages)
        
        results = {
            'terminology_evolution': evolution,
            'language_adoption': adoption,
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
    parser.add_argument('--output', type=Path, default=Path(__file__).parent.parent.parent / 'findings' / 'data' / 'language_evolution.json',
                       help='Output JSON file')
    
    args = parser.parse_args()
    
    analyzer = LanguageEvolutionAnalyzer(args.data_dir)
    results = analyzer.run_analysis()
    analyzer.print_results(results)
    
    # Save results
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nResults saved to: {args.output}")


if __name__ == '__main__':
    main()

