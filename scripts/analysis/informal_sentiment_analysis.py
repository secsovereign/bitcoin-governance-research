#!/usr/bin/env python3
"""
IRC/Mailing List Sentiment Analysis - Analyze informal channel sentiment and influence.

Analyzes:
1. Sentiment analysis on IRC/email (positive/negative/neutral)
2. SOM analysis on informal channels (BCAP framework)
3. Influence network analysis (reply patterns, mentions)
4. Cross-channel correlation (IRC/Email → GitHub PR outcomes)
"""

import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from collections import defaultdict, Counter
from datetime import datetime, timezone

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir, get_analysis_dir

logger = setup_logger()


# SOM keywords (from BCAP framework)
SOM_KEYWORDS = {
    'som1': ['excellent', 'great', 'strongly support', 'essential', 'critical', 'important', 
             'strongly advocate', 'fantastic', 'amazing', 'perfect'],
    'som2': ['support', 'good', 'helpful', 'agree', 'ack', 'approve', 'yes', 'sounds good'],
    'som3': ['maybe', 'perhaps', 'uncertain', 'not sure', 'neutral', '?', 'unclear', 'unsure'],
    'som5': ['concern', 'worried', 'skeptical', 'hesitant', 'nack', 'oppose', 'not ideal'],
    'som6': ['strongly oppose', 'dangerous', 'harmful', 'bad idea', 'against', 'veto', 
             'reject', 'terrible', 'wrong', 'horrible']
}

# Sentiment keywords
POSITIVE_KEYWORDS = ['good', 'great', 'excellent', 'perfect', 'awesome', 'nice', 'cool', 
                     'thanks', 'agree', 'support', 'ack', 'approve', 'yes']
NEGATIVE_KEYWORDS = ['bad', 'wrong', 'terrible', 'horrible', 'disagree', 'oppose', 'nack',
                     'concern', 'worried', 'skeptical', 'problem', 'issue', 'bug', 'no']


class InformalSentimentAnalyzer:
    """Analyzer for IRC/Email sentiment and influence patterns."""
    
    def __init__(self):
        """Initialize analyzer."""
        self.data_dir = get_data_dir()
        self.irc_dir = self.data_dir / 'irc'
        self.mailing_dir = self.data_dir / 'mailing_lists'
        self.github_dir = self.data_dir / 'github'
        self.analysis_dir = get_analysis_dir()
        self.findings_dir = self.analysis_dir / 'findings' / 'data'
        self.findings_dir.mkdir(parents=True, exist_ok=True)
        
        # Maintainer list (for cross-reference)
        self.maintainers = {
            'laanwj', 'sipa', 'maflcko', 'fanquake', 'hebasto', 'jnewbery',
            'ryanofsky', 'achow101', 'theuni', 'jonasschnelli', 'Sjors',
            'promag', 'instagibbs', 'TheBlueMatt', 'jonatack', 'gmaxwell',
            'gavinandresen', 'petertodd', 'luke-jr', 'glozow'
        }
    
    def run_analysis(self):
        """Run informal sentiment analysis."""
        logger.info("=" * 60)
        logger.info("IRC/Email Sentiment Analysis")
        logger.info("=" * 60)
        
        # Load data
        irc_messages = self._load_irc_messages()
        emails = self._load_emails()
        core_prs = self._load_core_prs()
        
        logger.info(f"Loaded {len(irc_messages)} IRC messages, {len(emails)} emails")
        
        # Analyze sentiment
        irc_sentiment = self._analyze_channel_sentiment(irc_messages, 'irc')
        email_sentiment = self._analyze_channel_sentiment(emails, 'email')
        
        # Analyze SOM on informal channels
        irc_som = self._analyze_channel_som(irc_messages, 'irc')
        email_som = self._analyze_channel_som(emails, 'email')
        
        # Analyze influence networks
        irc_influence = self._analyze_influence_network(irc_messages, 'irc')
        email_influence = self._analyze_influence_network(emails, 'email')
        
        # Cross-reference with GitHub PRs
        correlation_analysis = self._analyze_pr_correlation(irc_messages, emails, core_prs)
        
        # Save results
        results = {
            'irc_sentiment': irc_sentiment,
            'email_sentiment': email_sentiment,
            'irc_som': irc_som,
            'email_som': email_som,
            'irc_influence': irc_influence,
            'email_influence': email_influence,
            'pr_correlation': correlation_analysis,
            'statistics': self._generate_statistics(
                irc_sentiment, email_sentiment, irc_som, email_som,
                irc_influence, email_influence, correlation_analysis
            ),
            'methodology': self._get_methodology()
        }
        
        self._save_results(results)
        logger.info("Informal sentiment analysis complete")
    
    def _load_irc_messages(self) -> List[Dict[str, Any]]:
        """Load IRC messages."""
        irc_file = self.irc_dir / 'messages.jsonl'
        if not irc_file.exists():
            # Fall back to parent commons-research data directory
            parent_data_dir = self.data_dir.parent.parent / 'data' / 'irc' / 'messages.jsonl'
            if parent_data_dir.exists():
                irc_file = parent_data_dir
            else:
                logger.warning(f"IRC messages file not found: {irc_file}")
                return []
        
        messages = []
        # Load in chunks to handle large file
        with open(irc_file, 'r') as f:
            for i, line in enumerate(f):
                try:
                    messages.append(json.loads(line))
                    if (i + 1) % 50000 == 0:
                        logger.info(f"Loaded {i + 1} IRC messages...")
                except json.JSONDecodeError:
                    continue
        
        return messages
    
    def _load_emails(self) -> List[Dict[str, Any]]:
        """Load mailing list emails."""
        email_file = self.mailing_dir / 'emails.jsonl'
        if not email_file.exists():
            # Fall back to parent commons-research data directory
            # get_data_dir() returns publication-package/data, so parent.parent is commons-research
            parent_data_dir = self.data_dir.parent.parent / 'data' / 'mailing_lists' / 'emails.jsonl'
            if parent_data_dir.exists():
                email_file = parent_data_dir
            else:
                # Try one more level up
                alt_path = Path('/home/acolyte/src/BitcoinCommons/commons-research/data/mailing_lists/emails.jsonl')
                if alt_path.exists():
                    email_file = alt_path
                else:
                    logger.warning(f"Email file not found: {email_file}")
                    return []
        
        emails = []
        with open(email_file, 'r') as f:
            for i, line in enumerate(f):
                try:
                    emails.append(json.loads(line))
                    if (i + 1) % 5000 == 0:
                        logger.info(f"Loaded {i + 1} emails...")
                except json.JSONDecodeError:
                    continue
        
        return emails
    
    def _load_core_prs(self) -> List[Dict[str, Any]]:
        """Load Core repository PRs."""
        # Try publication-package data first, then fall back to parent commons-research data
        prs_file = self.github_dir / 'prs_raw.jsonl'
        if not prs_file.exists():
            # Fall back to parent commons-research data directory
            parent_data_dir = self.data_dir.parent.parent / 'data' / 'github' / 'prs_raw.jsonl'
            if parent_data_dir.exists():
                prs_file = parent_data_dir
            else:
                logger.warning(f"Core PRs file not found: {prs_file}")
                return []
        
        prs = []
        with open(prs_file, 'r') as f:
            for line in f:
                try:
                    prs.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        
        return prs
    
    def _analyze_channel_sentiment(
        self,
        messages: List[Dict[str, Any]],
        channel_type: str
    ) -> Dict[str, Any]:
        """Analyze sentiment on a channel (IRC or email)."""
        logger.info(f"Analyzing {channel_type} sentiment...")
        
        sentiment_counts = Counter()
        sentiment_by_author = defaultdict(lambda: Counter())
        sentiment_over_time = defaultdict(lambda: Counter())
        
        for msg in messages:
            # Extract text based on channel type
            if channel_type == 'irc':
                text = (msg.get('message', '') or '').lower()
                author = (msg.get('nickname', '') or '').lower()
                timestamp = msg.get('timestamp')
            else:  # email
                text = ((msg.get('body', '') or '') + ' ' + (msg.get('subject', '') or '')).lower()
                from_field = msg.get('from', '')
                # Extract email/name from from field
                author = self._extract_email_author(from_field).lower()
                timestamp = msg.get('date')
            
            if not text or not author:
                continue
            
            # Classify sentiment
            sentiment = self._classify_sentiment(text)
            sentiment_counts[sentiment] += 1
            sentiment_by_author[author][sentiment] += 1
            
            # Track sentiment over time (by month)
            if timestamp:
                try:
                    if isinstance(timestamp, str):
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    else:
                        continue
                    month_key = f"{dt.year}-{dt.month:02d}"
                    sentiment_over_time[month_key][sentiment] += 1
                except:
                    pass
        
        total = sum(sentiment_counts.values())
        sentiment_dist = {k: (v / total if total > 0 else 0) 
                         for k, v in sentiment_counts.items()}
        
        # Top authors by sentiment
        top_positive = sorted(
            [(author, counts.get('positive', 0)) for author, counts in sentiment_by_author.items()],
            key=lambda x: x[1], reverse=True
        )[:10]
        
        top_negative = sorted(
            [(author, counts.get('negative', 0)) for author, counts in sentiment_by_author.items()],
            key=lambda x: x[1], reverse=True
        )[:10]
        
        return {
            'total_messages': total,
            'sentiment_distribution': sentiment_dist,
            'sentiment_counts': dict(sentiment_counts),
            'top_positive_authors': top_positive,
            'top_negative_authors': top_negative,
            'sentiment_over_time': {k: dict(v) for k, v in sentiment_over_time.items()}
        }
    
    def _analyze_channel_som(
        self,
        messages: List[Dict[str, Any]],
        channel_type: str
    ) -> Dict[str, Any]:
        """Analyze State of Mind (SOM) on a channel."""
        logger.info(f"Analyzing {channel_type} SOM...")
        
        author_som = defaultdict(lambda: Counter())
        som_counts = Counter()
        
        for msg in messages:
            # Extract text and author
            if channel_type == 'irc':
                text = (msg.get('message', '') or '').lower()
                author = (msg.get('nickname', '') or '').lower()
            else:  # email
                text = ((msg.get('body', '') or '') + ' ' + (msg.get('subject', '') or '')).lower()
                from_field = msg.get('from', '')
                author = self._extract_email_author(from_field).lower()
            
            if not text or not author:
                continue
            
            # Classify SOM
            som = self._classify_som(text)
            if som:
                author_som[author][som] += 1
                som_counts[som] += 1
        
        # Determine primary SOM per author
        author_primary_som = {}
        for author, som_counts_author in author_som.items():
            if som_counts_author:
                primary_som = som_counts_author.most_common(1)[0][0]
                author_primary_som[author] = {
                    'som': primary_som,
                    'count': sum(som_counts_author.values()),
                    'som_distribution': dict(som_counts_author)
                }
        
        total_author_messages = sum(sum(counts.values()) for counts in author_som.values())
        som_distribution = {k: (v / total_author_messages if total_author_messages > 0 else 0)
                           for k, v in som_counts.items()}
        
        return {
            'total_authors': len(author_primary_som),
            'som_distribution': som_distribution,
            'som_counts': dict(som_counts),
            'author_som': {k: v for k, v in list(author_primary_som.items())[:100]}  # Limit output
        }
    
    def _analyze_influence_network(
        self,
        messages: List[Dict[str, Any]],
        channel_type: str
    ) -> Dict[str, Any]:
        """Analyze influence networks (reply patterns, mentions)."""
        logger.info(f"Analyzing {channel_type} influence network...")
        
        # Reply patterns (for email: in_reply_to, for IRC: @mentions or reply context)
        reply_network = defaultdict(lambda: Counter())
        mention_network = defaultdict(lambda: Counter())
        
        for msg in messages:
            if channel_type == 'email':
                from_field = msg.get('from', '')
                author = self._extract_email_author(from_field).lower()
                in_reply_to = msg.get('in_reply_to', '')
                
                # Extract original author from in_reply_to (simplified)
                if in_reply_to:
                    # This is a reply - but we need to find the original author
                    # For now, we'll track reply frequency
                    reply_network[author]['replies_sent'] += 1
                
                # Count mentions in body
                body = (msg.get('body', '') or '').lower()
                mentions = self._extract_mentions(body)
                for mention in mentions:
                    mention_network[author][mention] += 1
            
            else:  # IRC
                author = (msg.get('nickname', '') or '').lower()
                message = (msg.get('message', '') or '').lower()
                
                # Extract @mentions
                mentions = re.findall(r'@(\w+)', message)
                for mention in mentions:
                    mention_network[author][mention] += 1
        
        # Calculate network metrics
        top_repliers = sorted(
            [(author, counts.get('replies_sent', 0)) 
             for author, counts in reply_network.items()],
            key=lambda x: x[1], reverse=True
        )[:10]
        
        top_mentioned = {}
        for author, mentions in mention_network.items():
            total_mentions = sum(mentions.values())
            if total_mentions > 0:
                top_mentioned[author] = total_mentions
        
        top_mentioned_sorted = sorted(top_mentioned.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'reply_network': {k: dict(v) for k, v in list(reply_network.items())[:50]},
            'mention_network': {k: dict(v) for k, v in list(mention_network.items())[:50]},
            'top_repliers': top_repliers,
            'top_mentioned': top_mentioned_sorted
        }
    
    def _analyze_pr_correlation(
        self,
        irc_messages: List[Dict[str, Any]],
        emails: List[Dict[str, Any]],
        core_prs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze correlation between informal channels and GitHub PR outcomes."""
        logger.info("Analyzing PR correlation...")
        
        # Extract PR numbers from IRC/email (simplified)
        pr_mentions_irc = defaultdict(lambda: Counter())
        pr_mentions_email = defaultdict(lambda: Counter())
        
        # Look for PR mentions in IRC
        for msg in irc_messages:
            message = msg.get('message', '') or ''
            pr_numbers = re.findall(r'(?:PR|#)(\d{4,})', message, re.IGNORECASE)
            for pr_num in pr_numbers:
                author = (msg.get('nickname', '') or '').lower()
                pr_mentions_irc[pr_num][author] += 1
        
        # Look for PR mentions in emails
        for email in emails:
            subject = (email.get('subject', '') or '').lower()
            body = (email.get('body', '') or '').lower()
            text = subject + ' ' + body
            pr_numbers = re.findall(r'(?:PR|#)(\d{4,})', text, re.IGNORECASE)
            for pr_num in pr_numbers:
                from_field = email.get('from', '')
                author = self._extract_email_author(from_field).lower()
                pr_mentions_email[pr_num][author] += 1
        
        # Correlate with PR outcomes
        pr_outcomes = {}
        for pr in core_prs:
            pr_num = str(pr.get('number', ''))
            merged = pr.get('merged', False)
            pr_outcomes[pr_num] = merged
        
        # Calculate correlation
        mentioned_prs_irc = set(pr_mentions_irc.keys())
        mentioned_prs_email = set(pr_mentions_email.keys())
        all_mentioned = mentioned_prs_irc | mentioned_prs_email
        
        merged_mentioned = sum(1 for pr_num in all_mentioned if pr_outcomes.get(pr_num))
        merged_rate_mentioned = merged_mentioned / len(all_mentioned) if all_mentioned else 0
        
        # Overall merge rate for comparison
        all_prs_merged = sum(1 for pr in core_prs if pr.get('merged', False))
        overall_merge_rate = all_prs_merged / len(core_prs) if core_prs else 0
        
        return {
            'prs_mentioned_in_irc': len(mentioned_prs_irc),
            'prs_mentioned_in_email': len(mentioned_prs_email),
            'total_unique_prs_mentioned': len(all_mentioned),
            'merged_rate_mentioned': merged_rate_mentioned,
            'overall_merge_rate': overall_merge_rate,
            'correlation_note': 'PRs mentioned in informal channels may have different merge rates'
        }
    
    def _classify_sentiment(self, text: str) -> str:
        """Classify sentiment (positive/negative/neutral)."""
        positive_count = sum(1 for kw in POSITIVE_KEYWORDS if kw in text)
        negative_count = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text)
        
        if positive_count > negative_count:
            return 'positive'
        elif negative_count > positive_count:
            return 'negative'
        else:
            return 'neutral'
    
    def _classify_som(self, text: str) -> Optional[str]:
        """Classify State of Mind (SOM) from text."""
        som_scores = {}
        
        for som, keywords in SOM_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                som_scores[som] = score
        
        if not som_scores:
            return None
        
        # Return SOM with highest score
        return max(som_scores.items(), key=lambda x: x[1])[0]
    
    def _extract_email_author(self, from_field: str) -> str:
        """Extract author from email 'from' field."""
        if not from_field:
            return ''
        
        # Extract email address or name
        email_match = re.search(r'[\w\.-]+@[\w\.-]+', from_field)
        if email_match:
            return email_match.group(0).split('@')[0]  # Return username part
        
        # Extract name if no email
        name_match = re.search(r'^([^<]+)', from_field)
        if name_match:
            return name_match.group(1).strip()
        
        return from_field.strip()
    
    def _extract_mentions(self, text: str) -> List[str]:
        """Extract mentions from text."""
        # Email mentions (simplified)
        mentions = re.findall(r'@([\w\.-]+)', text)
        return [m.lower() for m in mentions]
    
    def _generate_statistics(
        self,
        irc_sentiment: Dict[str, Any],
        email_sentiment: Dict[str, Any],
        irc_som: Dict[str, Any],
        email_som: Dict[str, Any],
        irc_influence: Dict[str, Any],
        email_influence: Dict[str, Any],
        correlation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate overall statistics."""
        return {
            'summary': {
                'irc_messages': irc_sentiment.get('total_messages', 0),
                'email_messages': email_sentiment.get('total_messages', 0),
                'irc_sentiment_positive': irc_sentiment.get('sentiment_distribution', {}).get('positive', 0),
                'email_sentiment_positive': email_sentiment.get('sentiment_distribution', {}).get('positive', 0),
                'prs_mentioned_informally': correlation.get('total_unique_prs_mentioned', 0),
                'merge_rate_mentioned': correlation.get('merged_rate_mentioned', 0)
            }
        }
    
    def _get_methodology(self) -> Dict[str, Any]:
        """Get methodology description."""
        return {
            'sentiment_analysis': 'Keyword-based classification (positive/negative/neutral)',
            'som_classification': 'BCAP SOM framework applied to informal channels using keyword detection',
            'influence_network': 'Reply patterns (email) and @mentions (IRC)',
            'pr_correlation': 'PR number mentions in IRC/email correlated with merge outcomes',
            'limitations': [
                'Keyword-based sentiment may miss nuanced sentiment',
                'Email author extraction may be incomplete',
                'PR correlation requires PR number mentions (may miss some)',
                'Large dataset requires efficient processing'
            ]
        }
    
    def _save_results(self, results: Dict[str, Any]):
        """Save analysis results."""
        output_file = self.findings_dir / 'informal_sentiment.json'
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to {output_file}")


def main():
    """Main entry point."""
    analyzer = InformalSentimentAnalyzer()
    analyzer.run_analysis()


if __name__ == '__main__':
    main()
