#!/usr/bin/env python3
"""
Funding Analysis: Extract and analyze funding mentions from existing data.

Since most funding data is private, this focuses on what can be extracted
from public discussions, code, and documentation.
"""

import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

class FundingAnalyzer:
    """Analyze funding mentions and patterns."""
    
    def __init__(self, data_dir: Path):
        """Initialize analyzer."""
        self.data_dir = data_dir
        self.maintainers = {
            'laanwj', 'sipa', 'maflcko', 'fanquake', 'hebasto', 'jnewbery',
            'ryanofsky', 'achow101', 'theuni', 'jonasschnelli', 'Sjors',
            'promag', 'instagibbs', 'TheBlueMatt', 'jonatack', 'gmaxwell',
            'gavinandresen', 'petertodd', 'luke-jr', 'glozow'
        }
        
        # Funding-related keywords
        self.funding_keywords = {
            'grant': ['grant', 'grants', 'funding', 'funded', 'sponsor', 'sponsorship', 'sponsored'],
            'corporate': ['corporate', 'company', 'business', 'enterprise', 'commercial'],
            'foundation': ['foundation', 'non-profit', 'nonprofit', 'ngo'],
            'donation': ['donation', 'donate', 'donor', 'contribute', 'contribution'],
            'salary': ['salary', 'paid', 'payment', 'compensation', 'wage'],
            'research': ['research grant', 'academic', 'university', 'institution'],
            'bounty': ['bounty', 'bounties', 'reward', 'prize']
        }
        
        # Funding source patterns
        self.funding_sources = [
            'bitcoin foundation', 'human rights foundation', 'hrf',
            'open technology fund', 'otf', 'chaincode', 'blockstream',
            'square', 'coinbase', 'kraken', 'binance', 'mit', 'stanford'
        ]
    
    def _extract_funding_mentions(self, text: str) -> Dict[str, Any]:
        """Extract funding mentions from text."""
        if not text:
            return {}
        
        text_lower = text.lower()
        mentions = {
            'has_funding_mention': False,
            'keywords_found': [],
            'sources_mentioned': [],
            'funding_type': None
        }
        
        # Check for funding keywords
        for category, keywords in self.funding_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    mentions['has_funding_mention'] = True
                    if category not in mentions['keywords_found']:
                        mentions['keywords_found'].append(category)
                    mentions['funding_type'] = category
                    break
        
        # Check for funding sources
        for source in self.funding_sources:
            if source in text_lower:
                mentions['sources_mentioned'].append(source)
        
        return mentions
    
    def analyze_prs(self) -> Dict[str, Any]:
        """Analyze funding mentions in PRs."""
        print("Analyzing funding mentions in PRs...")
        
        prs = []
        pr_file = self.data_dir / 'github' / 'prs_raw.jsonl'
        with open(pr_file) as f:
            for line in f:
                if line.strip():
                    prs.append(json.loads(line))
        
        funding_mentions = []
        prs_with_funding = []
        
        for pr in prs:
            # Check PR body
            body = pr.get('body', '') or ''
            title = pr.get('title', '') or ''
            combined_text = f"{title} {body}"
            
            mentions = self._extract_funding_mentions(combined_text)
            if mentions.get('has_funding_mention'):
                prs_with_funding.append({
                    'pr_number': pr.get('number'),
                    'author': pr.get('author', ''),
                    'mentions': mentions,
                    'source': 'pr_body'
                })
                funding_mentions.append(mentions)
            
            # Check comments
            comments = pr.get('comments', []) or []
            for comment in comments:
                comment_body = comment.get('body', '') or ''
                mentions = self._extract_funding_mentions(comment_body)
                if mentions.get('has_funding_mention'):
                    prs_with_funding.append({
                        'pr_number': pr.get('number'),
                        'author': comment.get('author', ''),
                        'mentions': mentions,
                        'source': 'comment'
                    })
                    funding_mentions.append(mentions)
        
        return {
            'total_prs': len(prs),
            'prs_with_funding_mentions': len(prs_with_funding),
            'funding_mentions': prs_with_funding,
            'keyword_distribution': self._count_keywords(funding_mentions),
            'source_distribution': self._count_sources(funding_mentions)
        }
    
    def analyze_issues(self) -> Dict[str, Any]:
        """Analyze funding mentions in issues."""
        print("Analyzing funding mentions in issues...")
        
        issues = []
        issues_file = self.data_dir / 'github' / 'issues_raw.jsonl'
        if issues_file.exists():
            with open(issues_file) as f:
                for line in f:
                    if line.strip():
                        issues.append(json.loads(line))
        
        funding_mentions = []
        issues_with_funding = []
        
        for issue in issues:
            body = issue.get('body', '') or ''
            title = issue.get('title', '') or ''
            combined_text = f"{title} {body}"
            
            mentions = self._extract_funding_mentions(combined_text)
            if mentions.get('has_funding_mention'):
                issues_with_funding.append({
                    'issue_number': issue.get('number'),
                    'author': issue.get('author', ''),
                    'mentions': mentions
                })
                funding_mentions.append(mentions)
            
            # Check comments
            comments = issue.get('comments', []) or []
            for comment in comments:
                comment_body = comment.get('body', '') or ''
                mentions = self._extract_funding_mentions(comment_body)
                if mentions.get('has_funding_mention'):
                    issues_with_funding.append({
                        'issue_number': issue.get('number'),
                        'author': comment.get('author', ''),
                        'mentions': mentions
                    })
                    funding_mentions.append(mentions)
        
        return {
            'total_issues': len(issues),
            'issues_with_funding_mentions': len(issues_with_funding),
            'funding_mentions': issues_with_funding,
            'keyword_distribution': self._count_keywords(funding_mentions),
            'source_distribution': self._count_sources(funding_mentions)
        }
    
    def analyze_emails(self) -> Dict[str, Any]:
        """Analyze funding mentions in mailing list emails."""
        print("Analyzing funding mentions in emails...")
        
        emails = []
        emails_file = self.data_dir / 'mailing_lists' / 'emails.jsonl'
        if emails_file.exists():
            with open(emails_file) as f:
                for line in f:
                    if line.strip():
                        emails.append(json.loads(line))
        
        funding_mentions = []
        emails_with_funding = []
        
        for email in emails:
            subject = email.get('subject', '') or ''
            body = email.get('body', '') or ''
            combined_text = f"{subject} {body}"
            
            mentions = self._extract_funding_mentions(combined_text)
            if mentions.get('has_funding_mention'):
                emails_with_funding.append({
                    'email_id': email.get('id'),
                    'author': email.get('from', ''),
                    'date': email.get('date', ''),
                    'mentions': mentions
                })
                funding_mentions.append(mentions)
        
        return {
            'total_emails': len(emails),
            'emails_with_funding_mentions': len(emails_with_funding),
            'funding_mentions': emails_with_funding,
            'keyword_distribution': self._count_keywords(funding_mentions),
            'source_distribution': self._count_sources(funding_mentions)
        }
    
    def _count_keywords(self, mentions: List[Dict]) -> Dict[str, int]:
        """Count keyword occurrences."""
        keyword_counts = Counter()
        for mention in mentions:
            for keyword in mention.get('keywords_found', []):
                keyword_counts[keyword] += 1
        return dict(keyword_counts)
    
    def _count_sources(self, mentions: List[Dict]) -> Dict[str, int]:
        """Count source occurrences."""
        source_counts = Counter()
        for mention in mentions:
            for source in mention.get('sources_mentioned', []):
                source_counts[source] += 1
        return dict(source_counts)
    
    def run_analysis(self) -> Dict[str, Any]:
        """Run complete funding analysis."""
        print("="*80)
        print("FUNDING ANALYSIS")
        print("="*80)
        print()
        
        results = {
            'analysis_date': datetime.now().isoformat(),
            'prs': self.analyze_prs(),
            'issues': self.analyze_issues(),
            'emails': self.analyze_emails()
        }
        
        return results
    
    def print_results(self, results: Dict[str, Any]):
        """Print analysis results."""
        print("="*80)
        print("FUNDING ANALYSIS RESULTS")
        print("="*80)
        print()
        
        prs = results.get('prs', {})
        issues = results.get('issues', {})
        emails = results.get('emails', {})
        
        print("PRs:")
        print("-"*80)
        print(f"  Total PRs: {prs.get('total_prs', 0):,}")
        print(f"  PRs with funding mentions: {prs.get('prs_with_funding_mentions', 0):,}")
        print(f"  Keyword distribution:")
        for keyword, count in sorted(prs.get('keyword_distribution', {}).items(), key=lambda x: x[1], reverse=True):
            print(f"    {keyword}: {count}")
        print(f"  Sources mentioned:")
        for source, count in sorted(prs.get('source_distribution', {}).items(), key=lambda x: x[1], reverse=True):
            print(f"    {source}: {count}")
        print()
        
        print("Issues:")
        print("-"*80)
        print(f"  Total issues: {issues.get('total_issues', 0):,}")
        print(f"  Issues with funding mentions: {issues.get('issues_with_funding_mentions', 0):,}")
        print()
        
        print("Emails:")
        print("-"*80)
        print(f"  Total emails: {emails.get('total_emails', 0):,}")
        print(f"  Emails with funding mentions: {emails.get('emails_with_funding_mentions', 0):,}")
        print(f"  Keyword distribution:")
        for keyword, count in sorted(emails.get('keyword_distribution', {}).items(), key=lambda x: x[1], reverse=True):
            print(f"    {keyword}: {count}")
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
    
    analyzer = FundingAnalyzer(data_dir)
    results = analyzer.run_analysis()
    analyzer.print_results(results)
    
    # Save results
    output_file = data_dir.parent / 'findings' / 'funding_analysis.json'
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: {output_file}")


if __name__ == '__main__':
    main()
