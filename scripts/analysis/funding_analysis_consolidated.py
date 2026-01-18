#!/usr/bin/env python3
"""
Consolidated Funding Analysis - Analyze funding mentions in Bitcoin Core governance.

Combines functionality from funding_analysis.py and enhanced_funding_analysis.py.

Analyzes:
1. Funding mentions in PRs, issues, and emails
2. Funding source identification
3. Temporal funding patterns
4. Correlation with PR outcomes
5. Maintainer vs non-maintainer funding mentions
"""

import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import Counter, defaultdict
from datetime import datetime, timezone

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir, get_analysis_dir
from src.utils.temporal_utils import get_year, count_by_period, calculate_trend
from scripts.utils.load_prs_with_merged_by import load_prs_with_merged_by

logger = setup_logger()


# Funding patterns
FUNDING_PATTERNS = {
    'grant': r'\b(grant|grants|funding|funded|sponsor|sponsorship|sponsored)\b',
    'corporate': r'\b(corporate|company|business|enterprise|commercial|employer)\b',
    'foundation': r'\b(foundation|non-profit|nonprofit|ngo)\b',
    'donation': r'\b(donation|donate|donor|contribute|contribution)\b',
    'salary': r'\b(salary|paid|payment|compensation|wage|stipend)\b',
    'research': r'\b(research grant|academic|university|institution)\b',
    'bounty': r'\b(bounty|bounties|reward|prize)\b'
}

# Known funding sources
FUNDING_SOURCES = [
    'bitcoin foundation', 'human rights foundation', 'hrf',
    'open technology fund', 'otf', 'chaincode', 'blockstream',
    'square', 'block', 'coinbase', 'kraken', 'binance', 'mit', 'stanford',
    'digital currency group', 'dcg', 'bitmain', 'bitmaintech',
    'gemini', 'okcoin', 'grayscale', 'spiral', 'brink'
]

# Maintainer list
MAINTAINERS = {
    'laanwj', 'sipa', 'maflcko', 'fanquake', 'hebasto', 'jnewbery',
    'ryanofsky', 'achow101', 'theuni', 'jonasschnelli', 'Sjors',
    'promag', 'instagibbs', 'TheBlueMatt', 'jonatack', 'gmaxwell',
    'gavinandresen', 'petertodd', 'luke-jr', 'glozow'
}


class FundingAnalyzer:
    """Consolidated funding analysis for Bitcoin Core governance."""
    
    def __init__(self):
        """Initialize analyzer."""
        self.data_dir = get_data_dir()
        self.github_dir = self.data_dir / 'github'
        self.analysis_dir = get_analysis_dir()
        self.findings_dir = self.analysis_dir / 'findings' / 'data'
        self.findings_dir.mkdir(parents=True, exist_ok=True)
    
    def run_analysis(self):
        """Run comprehensive funding analysis."""
        logger.info("=" * 70)
        logger.info("Funding Analysis (Consolidated)")
        logger.info("=" * 70)
        
        # Load data
        prs = self._load_prs()
        issues = self._load_issues()
        emails = self._load_emails()
        
        # Analyze funding mentions
        pr_analysis = self._analyze_prs(prs)
        issue_analysis = self._analyze_issues(issues)
        email_analysis = self._analyze_emails(emails)
        
        # Analyze temporal patterns
        temporal_analysis = self._analyze_temporal_patterns(prs)
        
        # Analyze funding correlation with outcomes
        correlation_analysis = self._analyze_funding_correlation(prs)
        
        # Analyze maintainer vs non-maintainer
        maintainer_analysis = self._analyze_maintainer_funding(prs)
        
        # Save results
        results = {
            'pr_analysis': pr_analysis,
            'issue_analysis': issue_analysis,
            'email_analysis': email_analysis,
            'temporal_analysis': temporal_analysis,
            'correlation_analysis': correlation_analysis,
            'maintainer_analysis': maintainer_analysis,
            'methodology': self._get_methodology()
        }
        
        self._save_results(results)
        self._print_summary(results)
        
        logger.info("Funding analysis complete")
    
    def _load_prs(self) -> List[Dict[str, Any]]:
        """Load PR data."""
        prs_file = self.github_dir / 'prs_raw.jsonl'
        if not prs_file.exists():
            prs_file = self.data_dir.parent.parent / 'data' / 'github' / 'prs_raw.jsonl'
        
        if not prs_file.exists():
            logger.warning("PRs file not found")
            return []
        
        mapping_file = self.github_dir / 'merged_by_mapping.jsonl'
        if not mapping_file.exists():
            mapping_file = self.data_dir.parent.parent / 'data' / 'github' / 'merged_by_mapping.jsonl'
        
        return load_prs_with_merged_by(prs_file, mapping_file if mapping_file.exists() else None)
    
    def _load_issues(self) -> List[Dict[str, Any]]:
        """Load issues data."""
        issues_file = self.github_dir / 'issues_raw.jsonl'
        if not issues_file.exists():
            issues_file = self.data_dir.parent.parent / 'data' / 'github' / 'issues_raw.jsonl'
        
        if not issues_file.exists():
            logger.warning("Issues file not found")
            return []
        
        issues = []
        with open(issues_file) as f:
            for line in f:
                if line.strip():
                    issues.append(json.loads(line))
        return issues
    
    def _load_emails(self) -> List[Dict[str, Any]]:
        """Load email data."""
        emails_file = self.data_dir / 'mailing_lists' / 'emails.jsonl'
        if not emails_file.exists():
            emails_file = self.data_dir.parent.parent / 'data' / 'mailing_lists' / 'emails.jsonl'
        
        if not emails_file.exists():
            logger.warning("Emails file not found")
            return []
        
        emails = []
        with open(emails_file) as f:
            for line in f:
                if line.strip():
                    emails.append(json.loads(line))
        return emails
    
    def _extract_funding_info(self, text: str) -> Dict[str, Any]:
        """Extract funding information from text."""
        if not text:
            return {'has_funding': False, 'types': [], 'sources': []}
        
        text_lower = text.lower()
        result = {
            'has_funding': False,
            'types': [],
            'sources': []
        }
        
        # Check funding patterns
        for funding_type, pattern in FUNDING_PATTERNS.items():
            if re.search(pattern, text_lower):
                result['has_funding'] = True
                result['types'].append(funding_type)
        
        # Check funding sources
        for source in FUNDING_SOURCES:
            if source in text_lower:
                result['sources'].append(source)
        
        return result
    
    def _analyze_prs(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze funding mentions in PRs."""
        logger.info(f"Analyzing {len(prs):,} PRs for funding mentions...")
        
        prs_with_funding = []
        funding_types = Counter()
        funding_sources = Counter()
        
        for pr in prs:
            body = pr.get('body', '') or ''
            title = pr.get('title', '') or ''
            combined = f"{title} {body}"
            
            # Also check comments
            for comment in pr.get('comments', []):
                combined += ' ' + (comment.get('body', '') or '')
            
            funding_info = self._extract_funding_info(combined)
            
            if funding_info['has_funding']:
                prs_with_funding.append({
                    'number': pr.get('number'),
                    'author': pr.get('author'),
                    'merged': pr.get('merged', False),
                    'types': funding_info['types'],
                    'sources': funding_info['sources']
                })
                
                for t in funding_info['types']:
                    funding_types[t] += 1
                for s in funding_info['sources']:
                    funding_sources[s] += 1
        
        total = len(prs)
        with_funding = len(prs_with_funding)
        
        return {
            'total_prs': total,
            'prs_with_funding_mentions': with_funding,
            'funding_mention_rate': with_funding / total if total > 0 else 0.0,
            'top_funding_types': dict(funding_types.most_common(10)),
            'top_funding_sources': dict(funding_sources.most_common(10)),
            'sample_prs': prs_with_funding[:10]
        }
    
    def _analyze_issues(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze funding mentions in issues."""
        logger.info(f"Analyzing {len(issues):,} issues for funding mentions...")
        
        issues_with_funding = 0
        funding_types = Counter()
        
        for issue in issues:
            body = issue.get('body', '') or ''
            title = issue.get('title', '') or ''
            combined = f"{title} {body}"
            
            funding_info = self._extract_funding_info(combined)
            
            if funding_info['has_funding']:
                issues_with_funding += 1
                for t in funding_info['types']:
                    funding_types[t] += 1
        
        total = len(issues)
        
        return {
            'total_issues': total,
            'issues_with_funding_mentions': issues_with_funding,
            'funding_mention_rate': issues_with_funding / total if total > 0 else 0.0,
            'top_funding_types': dict(funding_types.most_common(10))
        }
    
    def _analyze_emails(self, emails: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze funding mentions in emails."""
        logger.info(f"Analyzing {len(emails):,} emails for funding mentions...")
        
        emails_with_funding = 0
        funding_types = Counter()
        funding_sources = Counter()
        
        for email in emails:
            body = email.get('body', '') or email.get('content', '') or ''
            subject = email.get('subject', '') or ''
            combined = f"{subject} {body}"
            
            funding_info = self._extract_funding_info(combined)
            
            if funding_info['has_funding']:
                emails_with_funding += 1
                for t in funding_info['types']:
                    funding_types[t] += 1
                for s in funding_info['sources']:
                    funding_sources[s] += 1
        
        total = len(emails)
        
        return {
            'total_emails': total,
            'emails_with_funding_mentions': emails_with_funding,
            'funding_mention_rate': emails_with_funding / total if total > 0 else 0.0,
            'top_funding_types': dict(funding_types.most_common(10)),
            'top_funding_sources': dict(funding_sources.most_common(10))
        }
    
    def _analyze_temporal_patterns(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze funding mention patterns over time."""
        logger.info("Analyzing temporal funding patterns...")
        
        yearly_stats = defaultdict(lambda: {'total': 0, 'with_funding': 0})
        
        for pr in prs:
            created_at = pr.get('created_at')
            if not created_at:
                continue
            
            year = get_year(created_at)
            if not year:
                continue
            
            yearly_stats[str(year)]['total'] += 1
            
            body = pr.get('body', '') or ''
            title = pr.get('title', '') or ''
            funding_info = self._extract_funding_info(f"{title} {body}")
            
            if funding_info['has_funding']:
                yearly_stats[str(year)]['with_funding'] += 1
        
        # Calculate rates
        temporal_data = {}
        for year, stats in sorted(yearly_stats.items()):
            rate = stats['with_funding'] / stats['total'] if stats['total'] > 0 else 0.0
            temporal_data[year] = {
                'total_prs': stats['total'],
                'prs_with_funding': stats['with_funding'],
                'funding_mention_rate': rate
            }
        
        # Calculate trend
        rates = {y: d['funding_mention_rate'] for y, d in temporal_data.items()}
        trend = calculate_trend(rates)
        
        return {
            'yearly_data': temporal_data,
            'trend': trend
        }
    
    def _analyze_funding_correlation(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze correlation between funding mentions and PR outcomes."""
        logger.info("Analyzing funding correlation with outcomes...")
        
        with_funding = {'merged': 0, 'total': 0, 'review_counts': []}
        without_funding = {'merged': 0, 'total': 0, 'review_counts': []}
        
        for pr in prs:
            body = pr.get('body', '') or ''
            title = pr.get('title', '') or ''
            funding_info = self._extract_funding_info(f"{title} {body}")
            
            is_merged = pr.get('merged', False)
            review_count = len(pr.get('reviews', []))
            
            if funding_info['has_funding']:
                with_funding['total'] += 1
                if is_merged:
                    with_funding['merged'] += 1
                with_funding['review_counts'].append(review_count)
            else:
                without_funding['total'] += 1
                if is_merged:
                    without_funding['merged'] += 1
                without_funding['review_counts'].append(review_count)
        
        def calc_stats(group):
            if group['total'] == 0:
                return {'merge_rate': 0.0, 'avg_reviews': 0.0, 'count': 0}
            return {
                'merge_rate': group['merged'] / group['total'],
                'avg_reviews': sum(group['review_counts']) / len(group['review_counts']) if group['review_counts'] else 0.0,
                'count': group['total']
            }
        
        return {
            'with_funding': calc_stats(with_funding),
            'without_funding': calc_stats(without_funding),
            'interpretation': 'Compares PR outcomes for PRs with vs without funding mentions'
        }
    
    def _analyze_maintainer_funding(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze funding mentions by maintainer status."""
        logger.info("Analyzing maintainer vs non-maintainer funding mentions...")
        
        maintainer_prs = {'total': 0, 'with_funding': 0}
        non_maintainer_prs = {'total': 0, 'with_funding': 0}
        
        for pr in prs:
            author = (pr.get('author') or '').lower()
            if not author:
                continue
            
            body = pr.get('body', '') or ''
            title = pr.get('title', '') or ''
            funding_info = self._extract_funding_info(f"{title} {body}")
            
            if author in MAINTAINERS or author in {m.lower() for m in MAINTAINERS}:
                maintainer_prs['total'] += 1
                if funding_info['has_funding']:
                    maintainer_prs['with_funding'] += 1
            else:
                non_maintainer_prs['total'] += 1
                if funding_info['has_funding']:
                    non_maintainer_prs['with_funding'] += 1
        
        def calc_rate(group):
            if group['total'] == 0:
                return 0.0
            return group['with_funding'] / group['total']
        
        return {
            'maintainer': {
                'total_prs': maintainer_prs['total'],
                'with_funding': maintainer_prs['with_funding'],
                'funding_mention_rate': calc_rate(maintainer_prs)
            },
            'non_maintainer': {
                'total_prs': non_maintainer_prs['total'],
                'with_funding': non_maintainer_prs['with_funding'],
                'funding_mention_rate': calc_rate(non_maintainer_prs)
            }
        }
    
    def _get_methodology(self) -> Dict[str, Any]:
        """Return methodology description."""
        return {
            'description': 'Analysis of funding mentions in Bitcoin Core PRs, issues, and emails',
            'data_sources': ['GitHub PRs', 'GitHub Issues', 'Mailing Lists'],
            'funding_patterns': list(FUNDING_PATTERNS.keys()),
            'funding_sources_checked': FUNDING_SOURCES,
            'limitations': [
                'Funding mentions are extracted from public text only',
                'Cannot verify actual funding relationships',
                'Keyword matching may have false positives/negatives',
                'Most funding arrangements are private and undisclosed'
            ]
        }
    
    def _save_results(self, results: Dict[str, Any]):
        """Save analysis results."""
        output_file = self.findings_dir / 'funding_analysis.json'
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        logger.info(f"Results saved to {output_file}")
    
    def _print_summary(self, results: Dict[str, Any]):
        """Print analysis summary."""
        print()
        print("=" * 70)
        print("FUNDING ANALYSIS SUMMARY")
        print("=" * 70)
        print()
        
        pr = results['pr_analysis']
        print(f"PRs: {pr['prs_with_funding_mentions']:,}/{pr['total_prs']:,} "
              f"({pr['funding_mention_rate']*100:.1f}%) have funding mentions")
        
        issue = results['issue_analysis']
        print(f"Issues: {issue['issues_with_funding_mentions']:,}/{issue['total_issues']:,} "
              f"({issue['funding_mention_rate']*100:.1f}%) have funding mentions")
        
        email = results['email_analysis']
        print(f"Emails: {email['emails_with_funding_mentions']:,}/{email['total_emails']:,} "
              f"({email['funding_mention_rate']*100:.1f}%) have funding mentions")
        
        print()
        print("Top funding types mentioned:")
        for ftype, count in list(pr['top_funding_types'].items())[:5]:
            print(f"  • {ftype}: {count:,}")
        
        print()
        corr = results['correlation_analysis']
        print(f"Correlation with outcomes:")
        print(f"  With funding: {corr['with_funding']['merge_rate']*100:.1f}% merge rate, "
              f"{corr['with_funding']['avg_reviews']:.1f} avg reviews")
        print(f"  Without funding: {corr['without_funding']['merge_rate']*100:.1f}% merge rate, "
              f"{corr['without_funding']['avg_reviews']:.1f} avg reviews")


def main():
    """Main entry point."""
    analyzer = FundingAnalyzer()
    analyzer.run_analysis()


if __name__ == '__main__':
    main()

