#!/usr/bin/env python3
"""
External pressure indicators extractor.

Extracts mentions of regulatory pressure, corporate influence, and external threats
from mailing lists and IRC messages.
"""

import sys
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Set
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir

logger = setup_logger()


class ExternalPressureExtractor:
    """Extractor for external pressure indicators."""
    
    def __init__(self):
        """Initialize extractor."""
        self.data_dir = get_data_dir()
        self.processed_dir = self.data_dir / "processed"
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
        # Define keywords for different pressure types
        self.regulatory_keywords = {
            'agencies': ['sec', 'cftc', 'fincen', 'fbi', 'irs', 'treasury', 'doj', 'justice department'],
            'regulation': ['regulation', 'regulatory', 'regulate', 'regulations', 'regulator', 'regulators'],
            'government': ['government', 'governments', 'federal', 'state', 'congress', 'senate', 'house'],
            'legal': ['legal', 'legislation', 'law', 'laws', 'lawsuit', 'litigation', 'court', 'judge'],
            'ban': ['ban', 'banned', 'prohibition', 'prohibit', 'restriction', 'restrict', 'restricted'],
            'compliance': ['compliance', 'comply', 'kyc', 'aml', 'know your customer', 'anti-money laundering']
        }
        
        self.corporate_keywords = {
            'funding': ['funding', 'funded', 'sponsor', 'sponsored', 'sponsorship', 'grant', 'grants', 'donation', 'donations'],
            'corporate': ['corporate', 'corporation', 'company', 'companies', 'enterprise', 'business', 'businesses'],
            'influence': ['influence', 'lobby', 'lobbying', 'lobbyist', 'pressure', 'pressured', 'coercion', 'coerce'],
            'partnership': ['partnership', 'partner', 'partners', 'alliance', 'alliances', 'collaboration']
        }
        
        self.threat_keywords = {
            'threat': ['threat', 'threats', 'threatened', 'threatening', 'risk', 'risks', 'danger', 'dangerous'],
            'attack': ['attack', 'attacks', 'attacked', 'attacking', 'target', 'targeted', 'targeting'],
            'pressure': ['pressure', 'pressured', 'pressuring', 'force', 'forced', 'forcing', 'compel', 'compelled']
        }
    
    def extract(self):
        """Extract external pressure indicators from all sources."""
        logger.info("Starting external pressure indicator extraction")
        
        # Extract from mailing lists
        mailing_list_pressure = self._extract_from_mailing_lists()
        
        # Extract from IRC
        irc_pressure = self._extract_from_irc()
        
        # Combine results
        all_pressure = {
            'mailing_lists': mailing_list_pressure,
            'irc': irc_pressure,
            'summary': self._generate_summary(mailing_list_pressure, irc_pressure)
        }
        
        # Save results
        output_file = self.processed_dir / "external_pressure_indicators.json"
        with open(output_file, 'w') as f:
            json.dump(all_pressure, f, indent=2)
        
        logger.info(f"Saved external pressure indicators to {output_file}")
        
        # Generate detailed report
        self._generate_detailed_report(all_pressure)
    
    def _extract_from_mailing_lists(self) -> Dict[str, Any]:
        """Extract pressure indicators from mailing lists."""
        logger.info("Extracting from mailing lists...")
        
        emails_file = self.data_dir / "mailing_lists" / "emails.jsonl"
        if not emails_file.exists():
            logger.warning(f"Mailing lists file not found: {emails_file}")
            return {'total_emails': 0, 'emails_with_pressure': [], 'pressure_counts': {}}
        
        emails_with_pressure = []
        pressure_counts = defaultdict(int)
        
        with open(emails_file, 'r') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    email = json.loads(line)
                    pressure_info = self._analyze_text_for_pressure(
                        email.get('body', '') + ' ' + email.get('subject', ''),
                        email.get('from', ''),
                        email.get('date', '')
                    )
                    
                    if pressure_info['has_pressure']:
                        email['pressure_indicators'] = pressure_info
                        emails_with_pressure.append({
                            'email_id': email.get('id'),
                            'date': email.get('date'),
                            'from': email.get('from'),
                            'subject': email.get('subject'),
                            'pressure_types': pressure_info['pressure_types'],
                            'keywords_found': pressure_info['keywords_found'],
                            'pressure_score': pressure_info['pressure_score']
                        })
                        
                        # Count pressure types
                        for ptype in pressure_info['pressure_types']:
                            pressure_counts[ptype] += 1
                    
                    if line_num % 1000 == 0:
                        logger.info(f"Processed {line_num} emails, found {len(emails_with_pressure)} with pressure indicators")
                
                except Exception as e:
                    logger.debug(f"Error processing email line {line_num}: {e}")
                    continue
        
        logger.info(f"Found {len(emails_with_pressure)} emails with pressure indicators")
        
        return {
            'total_emails': line_num,
            'emails_with_pressure': emails_with_pressure,
            'pressure_counts': dict(pressure_counts)
        }
    
    def _extract_from_irc(self) -> Dict[str, Any]:
        """Extract pressure indicators from IRC messages."""
        logger.info("Extracting from IRC messages...")
        
        irc_file = self.data_dir / "irc" / "messages.jsonl"
        if not irc_file.exists():
            logger.warning(f"IRC messages file not found: {irc_file}")
            return {'total_messages': 0, 'messages_with_pressure': [], 'pressure_counts': {}}
        
        messages_with_pressure = []
        pressure_counts = defaultdict(int)
        
        with open(irc_file, 'r') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    message = json.loads(line)
                    pressure_info = self._analyze_text_for_pressure(
                        message.get('message', ''),
                        message.get('nick', ''),
                        message.get('timestamp', '')
                    )
                    
                    if pressure_info['has_pressure']:
                        message['pressure_indicators'] = pressure_info
                        messages_with_pressure.append({
                            'message_id': message.get('id'),
                            'timestamp': message.get('timestamp'),
                            'nick': message.get('nick'),
                            'channel': message.get('channel'),
                            'pressure_types': pressure_info['pressure_types'],
                            'keywords_found': pressure_info['keywords_found'],
                            'pressure_score': pressure_info['pressure_score']
                        })
                        
                        # Count pressure types
                        for ptype in pressure_info['pressure_types']:
                            pressure_counts[ptype] += 1
                    
                    if line_num % 10000 == 0:
                        logger.info(f"Processed {line_num} messages, found {len(messages_with_pressure)} with pressure indicators")
                
                except Exception as e:
                    logger.debug(f"Error processing IRC message line {line_num}: {e}")
                    continue
        
        logger.info(f"Found {len(messages_with_pressure)} IRC messages with pressure indicators")
        
        return {
            'total_messages': line_num,
            'messages_with_pressure': messages_with_pressure,
            'pressure_counts': dict(pressure_counts)
        }
    
    def _analyze_text_for_pressure(self, text: str, author: str, date: str) -> Dict[str, Any]:
        """Analyze text for external pressure indicators."""
        text_lower = text.lower()
        
        pressure_types = []
        keywords_found = []
        pressure_score = 0
        
        # Check regulatory keywords
        for category, keywords in self.regulatory_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    if 'regulatory' not in pressure_types:
                        pressure_types.append('regulatory')
                    keywords_found.append(f"regulatory:{keyword}")
                    pressure_score += 1
        
        # Check corporate keywords
        for category, keywords in self.corporate_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    if 'corporate' not in pressure_types:
                        pressure_types.append('corporate')
                    keywords_found.append(f"corporate:{keyword}")
                    pressure_score += 1
        
        # Check threat keywords
        for category, keywords in self.threat_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    if 'threat' not in pressure_types:
                        pressure_types.append('threat')
                    keywords_found.append(f"threat:{keyword}")
                    pressure_score += 1
        
        return {
            'has_pressure': len(pressure_types) > 0,
            'pressure_types': pressure_types,
            'keywords_found': list(set(keywords_found)),  # Remove duplicates
            'pressure_score': pressure_score,
            'author': author,
            'date': date
        }
    
    def _generate_summary(self, mailing_list_data: Dict, irc_data: Dict) -> Dict[str, Any]:
        """Generate summary statistics."""
        total_emails = mailing_list_data.get('total_emails', 0)
        emails_with_pressure = len(mailing_list_data.get('emails_with_pressure', []))
        
        total_messages = irc_data.get('total_messages', 0)
        messages_with_pressure = len(irc_data.get('messages_with_pressure', []))
        
        # Combine pressure counts
        all_pressure_counts = defaultdict(int)
        for counts in [mailing_list_data.get('pressure_counts', {}), irc_data.get('pressure_counts', {})]:
            for ptype, count in counts.items():
                all_pressure_counts[ptype] += count
        
        return {
            'mailing_lists': {
                'total': total_emails,
                'with_pressure': emails_with_pressure,
                'percentage': (emails_with_pressure / total_emails * 100) if total_emails > 0 else 0
            },
            'irc': {
                'total': total_messages,
                'with_pressure': messages_with_pressure,
                'percentage': (messages_with_pressure / total_messages * 100) if total_messages > 0 else 0
            },
            'total_pressure_mentions': sum(all_pressure_counts.values()),
            'pressure_type_counts': dict(all_pressure_counts)
        }
    
    def _generate_detailed_report(self, all_pressure: Dict[str, Any]):
        """Generate detailed report."""
        logger.info("=== External Pressure Indicators Summary ===")
        
        summary = all_pressure.get('summary', {})
        
        logger.info(f"Mailing Lists:")
        ml_stats = summary.get('mailing_lists', {})
        logger.info(f"  Total emails: {ml_stats.get('total', 0)}")
        logger.info(f"  With pressure indicators: {ml_stats.get('with_pressure', 0)} ({ml_stats.get('percentage', 0):.2f}%)")
        
        logger.info(f"IRC:")
        irc_stats = summary.get('irc', {})
        logger.info(f"  Total messages: {irc_stats.get('total', 0)}")
        logger.info(f"  With pressure indicators: {irc_stats.get('with_pressure', 0)} ({irc_stats.get('percentage', 0):.2f}%)")
        
        logger.info(f"Pressure Types:")
        for ptype, count in sorted(summary.get('pressure_type_counts', {}).items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  {ptype}: {count} mentions")


def main():
    """Main entry point."""
    extractor = ExternalPressureExtractor()
    extractor.extract()
    logger.info("External pressure extraction complete")


if __name__ == '__main__':
    main()


