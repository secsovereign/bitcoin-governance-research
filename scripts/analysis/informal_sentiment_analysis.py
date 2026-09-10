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
from src.utils.cross_platform_sources import (
    audit_source_overlap,
    extract_pr_numbers,
    extract_text_author_timestamp,
    load_bitcointalk_posts,
    load_delving_posts,
    load_mailing_lists,
    split_mailing_lists_by_name,
)

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
        
        from src.utils.maintainers import load_maintainer_login_set
        self.maintainers = load_maintainer_login_set()
    
    def run_analysis(self):
        """Run informal sentiment analysis."""
        logger.info("=" * 60)
        logger.info("IRC/Email Sentiment Analysis")
        logger.info("=" * 60)
        
        source_audit = audit_source_overlap()

        # Load data
        irc_messages = self._load_irc_messages()
        all_emails, email_meta = load_mailing_lists(dedupe=True)
        emails_by_list = split_mailing_lists_by_name(all_emails)
        bitcoin_dev_emails = emails_by_list.get("bitcoin-dev", [])
        cryptography_emails = emails_by_list.get("cryptography", [])
        delving_posts, _ = load_delving_posts()
        bitcointalk_posts, _ = load_bitcointalk_posts()
        core_prs = self._load_core_prs()

        logger.info(
            "Loaded %s IRC, %s emails (%s deduped), %s Delving, %s Bitcointalk",
            len(irc_messages),
            len(all_emails),
            email_meta.get("duplicates_removed", 0),
            len(delving_posts),
            len(bitcointalk_posts),
        )

        # Analyze sentiment
        irc_sentiment = self._analyze_channel_sentiment(irc_messages, 'irc')
        email_sentiment = self._analyze_channel_sentiment(all_emails, 'email')
        bitcoin_dev_sentiment = self._analyze_channel_sentiment(bitcoin_dev_emails, 'email')
        cryptography_sentiment = self._analyze_channel_sentiment(cryptography_emails, 'email')
        delving_sentiment = self._analyze_channel_sentiment(delving_posts, 'delving')
        bitcointalk_sentiment = self._analyze_channel_sentiment(bitcointalk_posts, 'bitcointalk')

        # Analyze SOM on informal channels
        irc_som = self._analyze_channel_som(irc_messages, 'irc')
        email_som = self._analyze_channel_som(all_emails, 'email')
        bitcoin_dev_som = self._analyze_channel_som(bitcoin_dev_emails, 'email')
        cryptography_som = self._analyze_channel_som(cryptography_emails, 'email')
        delving_som = self._analyze_channel_som(delving_posts, 'delving')
        bitcointalk_som = self._analyze_channel_som(bitcointalk_posts, 'bitcointalk')

        # Analyze influence networks
        irc_influence = self._analyze_influence_network(irc_messages, 'irc')
        email_influence = self._analyze_influence_network(all_emails, 'email')
        delving_influence = self._analyze_influence_network(delving_posts, 'delving')
        bitcointalk_influence = self._analyze_influence_network(bitcointalk_posts, 'bitcointalk')

        # Cross-reference with GitHub PRs
        correlation_analysis = self._analyze_pr_correlation(
            irc_messages,
            all_emails,
            delving_posts,
            bitcointalk_posts,
            core_prs,
        )

        # Save results
        results = {
            'source_audit': source_audit,
            'email_load_meta': email_meta,
            'irc_sentiment': irc_sentiment,
            'email_sentiment': email_sentiment,
            'bitcoin_dev_sentiment': bitcoin_dev_sentiment,
            'cryptography_sentiment': cryptography_sentiment,
            'delving_sentiment': delving_sentiment,
            'bitcointalk_sentiment': bitcointalk_sentiment,
            'irc_som': irc_som,
            'email_som': email_som,
            'bitcoin_dev_som': bitcoin_dev_som,
            'cryptography_som': cryptography_som,
            'delving_som': delving_som,
            'bitcointalk_som': bitcointalk_som,
            'irc_influence': irc_influence,
            'email_influence': email_influence,
            'delving_influence': delving_influence,
            'bitcointalk_influence': bitcointalk_influence,
            'pr_correlation': correlation_analysis,
            'statistics': self._generate_statistics(
                irc_sentiment,
                email_sentiment,
                delving_sentiment,
                bitcointalk_sentiment,
                cryptography_sentiment,
                irc_som,
                email_som,
                irc_influence,
                email_influence,
                correlation_analysis,
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
            raw_text, author, timestamp = extract_text_author_timestamp(msg, channel_type)
            text = raw_text.lower()
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
            raw_text, author, _ = extract_text_author_timestamp(msg, channel_type)
            text = raw_text.lower()
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
            raw_text, author, _ = extract_text_author_timestamp(msg, channel_type)
            text = raw_text.lower()
            if not author:
                continue

            if channel_type == 'email':
                if msg.get('in_reply_to'):
                    reply_network[author]['replies_sent'] += 1
                for mention in self._extract_mentions(text):
                    mention_network[author][mention] += 1
            elif channel_type == 'delving':
                reply_network[author]['posts'] += 1
                if msg.get('reply_to_post_number'):
                    reply_network[author]['replies_sent'] += 1
            elif channel_type == 'bitcointalk':
                reply_network[author]['posts'] += 1
            else:  # IRC
                for mention in re.findall(r'@(\w+)', text):
                    mention_network[author][mention.lower()] += 1
        
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
        delving_posts: List[Dict[str, Any]],
        bitcointalk_posts: List[Dict[str, Any]],
        core_prs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze correlation between informal channels and GitHub PR outcomes."""
        logger.info("Analyzing PR correlation...")
        
        # Extract PR numbers from IRC/email (simplified)
        pr_mentions_irc = defaultdict(lambda: Counter())
        pr_mentions_email = defaultdict(lambda: Counter())
        pr_mentions_delving = defaultdict(lambda: Counter())
        pr_mentions_bitcointalk = defaultdict(lambda: Counter())

        for msg in irc_messages:
            _, author, _ = extract_text_author_timestamp(msg, 'irc')
            for pr_num in extract_pr_numbers(msg.get('message', '') or ''):
                pr_mentions_irc[pr_num][author] += 1

        for email in emails:
            text = f"{email.get('subject', '')} {email.get('body', '')}"
            _, author, _ = extract_text_author_timestamp(email, 'email')
            for pr_num in extract_pr_numbers(text):
                pr_mentions_email[pr_num][author] += 1

        for post in delving_posts:
            text = f"{post.get('content', '')} {post.get('cooked_html', '')}"
            _, author, _ = extract_text_author_timestamp(post, 'delving')
            for pr_num in extract_pr_numbers(text):
                pr_mentions_delving[pr_num][author] += 1

        for post in bitcointalk_posts:
            _, author, _ = extract_text_author_timestamp(post, 'bitcointalk')
            for pr_num in extract_pr_numbers(post.get('content', '') or ''):
                pr_mentions_bitcointalk[pr_num][author] += 1
        
        # Correlate with PR outcomes
        pr_outcomes = {}
        for pr in core_prs:
            pr_num = str(pr.get('number', ''))
            merged = pr.get('merged', False)
            pr_outcomes[pr_num] = merged
        
        # Calculate correlation
        mentioned_prs_irc = set(pr_mentions_irc.keys())
        mentioned_prs_email = set(pr_mentions_email.keys())
        mentioned_prs_delving = set(pr_mentions_delving.keys())
        mentioned_prs_bitcointalk = set(pr_mentions_bitcointalk.keys())
        all_mentioned = (
            mentioned_prs_irc
            | mentioned_prs_email
            | mentioned_prs_delving
            | mentioned_prs_bitcointalk
        )
        
        merged_mentioned = sum(1 for pr_num in all_mentioned if pr_outcomes.get(pr_num))
        merged_rate_mentioned = merged_mentioned / len(all_mentioned) if all_mentioned else 0
        
        # Overall merge rate for comparison
        all_prs_merged = sum(1 for pr in core_prs if pr.get('merged', False))
        overall_merge_rate = all_prs_merged / len(core_prs) if core_prs else 0
        
        return {
            'prs_mentioned_in_irc': len(mentioned_prs_irc),
            'prs_mentioned_in_email': len(mentioned_prs_email),
            'prs_mentioned_in_delving': len(mentioned_prs_delving),
            'prs_mentioned_in_bitcointalk': len(mentioned_prs_bitcointalk),
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
        delving_sentiment: Dict[str, Any],
        bitcointalk_sentiment: Dict[str, Any],
        cryptography_sentiment: Dict[str, Any],
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
                'cryptography_messages': cryptography_sentiment.get('total_messages', 0),
                'delving_messages': delving_sentiment.get('total_messages', 0),
                'bitcointalk_messages': bitcointalk_sentiment.get('total_messages', 0),
                'irc_sentiment_positive': irc_sentiment.get('sentiment_distribution', {}).get('positive', 0),
                'email_sentiment_positive': email_sentiment.get('sentiment_distribution', {}).get('positive', 0),
                'prs_mentioned_informally': correlation.get('total_unique_prs_mentioned', 0),
                'prs_mentioned_in_delving': correlation.get('prs_mentioned_in_delving', 0),
                'merge_rate_mentioned': correlation.get('merged_rate_mentioned', 0)
            }
        }
    
    def _get_methodology(self) -> Dict[str, Any]:
        """Get methodology description."""
        return {
            'sentiment_analysis': 'Keyword-based classification (positive/negative/neutral)',
            'som_classification': 'BCAP SOM framework applied to informal channels using keyword detection',
            'influence_network': 'Reply patterns (email/forums) and @mentions (IRC)',
            'mailing_lists': 'bitcoin-dev + cryptography with message_id dedupe for combined email metrics',
            'forums': 'Delving and Bitcointalk scored as separate channels',
            'pr_correlation': 'PR number mentions across informal channels correlated with merge outcomes',
            'limitations': [
                'Keyword-based sentiment may miss nuanced sentiment',
                'Email author extraction may be incomplete',
                'PR correlation requires PR number mentions (may miss some)',
                'Large dataset requires efficient processing',
                'Cryptography list is mostly pre-bitcoin-dev era; kept separate in per-list breakdowns',
            ]
        }
    
    def _save_results(self, results: Dict[str, Any]):
        """Save analysis results."""
        from src.utils.findings_io import save_analysis_json
        written = save_analysis_json('informal_sentiment.json', results)
        logger.info(f"Results saved to {', '.join(str(p) for p in written)}")


def main():
    """Main entry point."""
    analyzer = InformalSentimentAnalyzer()
    analyzer.run_analysis()


if __name__ == '__main__':
    main()
