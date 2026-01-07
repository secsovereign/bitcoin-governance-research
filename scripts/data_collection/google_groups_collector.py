#!/usr/bin/env python3
"""
Google Groups collector for bitcoin-dev mailing list.

Collects recent messages from Google Groups (Feb 2024+).
"""

import sys
import os
import json
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config import config
from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir

logger = setup_logger()


class GoogleGroupsCollector:
    """Collector for Google Groups mailing list."""
    
    def __init__(self):
        """Initialize Google Groups collector."""
        self.group_url = "https://groups.google.com/g/bitcoin-dev"
        self.data_dir = get_data_dir() / "mailing_lists"
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def collect(self):
        """Collect messages from Google Groups."""
        logger.info("Starting Google Groups collection")
        logger.warning("Google Groups may require authentication or have rate limits")
        
        emails = []
        
        try:
            # Method 1: Try Atom feed (most reliable for public groups)
            atom_url = "https://groups.google.com/g/bitcoin-dev/feed/rss_v2_0_msgs.xml"
            logger.info(f"Trying Atom/RSS feed: {atom_url}")
            try:
                atom_emails = self._collect_from_atom_feed(atom_url)
                emails.extend(atom_emails)
                logger.info(f"Collected {len(atom_emails)} emails from Atom feed")
            except Exception as e:
                logger.debug(f"Atom feed not accessible: {e}")
            
            # Method 2: Try RSS feed (alternative format)
            rss_url = "https://groups.google.com/forum/feed/bitcoin-dev/msgs/rss.xml"
            logger.info(f"Trying RSS feed: {rss_url}")
            try:
                rss_emails = self._collect_from_rss(rss_url)
                emails.extend(rss_emails)
                logger.info(f"Collected {len(rss_emails)} emails from RSS feed")
            except Exception as e:
                logger.debug(f"RSS feed not accessible: {e}")
            
            # Method 3: Try web interface (limited due to JavaScript)
            if not emails:
                logger.info("Trying web interface (may be limited)")
                try:
                    response = requests.get(self.group_url, timeout=30)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Look for RSS feed link in HTML
                        rss_link = soup.find('link', type='application/rss+xml')
                        if rss_link:
                            rss_url = rss_link.get('href', '')
                            logger.info(f"Found RSS feed in HTML: {rss_url}")
                            web_emails = self._collect_from_rss(rss_url)
                            emails.extend(web_emails)
                except Exception as e:
                    logger.debug(f"Web interface access failed: {e}")
            
            # Deduplicate
            seen_ids = set()
            unique_emails = []
            for email in emails:
                msg_id = email.get('message_id') or email.get('link', '')
                if msg_id and msg_id not in seen_ids:
                    seen_ids.add(msg_id)
                    unique_emails.append(email)
            
            # Check existing emails to avoid duplicates
            existing_ids = set()
            main_emails_file = self.data_dir / 'emails.jsonl'
            if main_emails_file.exists():
                with open(main_emails_file, 'r') as f:
                    for line in f:
                        try:
                            existing = json.loads(line)
                            if existing.get('message_id'):
                                existing_ids.add(existing['message_id'])
                        except:
                            continue
            
            # Only add new emails
            new_emails = [e for e in unique_emails if (e.get('message_id') or e.get('link', '')) not in existing_ids]
            
            if new_emails:
                # Append to main emails file
                with open(main_emails_file, 'a') as f:
                    for email in new_emails:
                        # Convert to standard format
                        email['list_name'] = 'bitcoin-dev'
                        email['source'] = 'google_groups'
                        f.write(json.dumps(email) + '\n')
                
                logger.info(f"Added {len(new_emails)} new emails from Google Groups (total unique: {len(unique_emails)})")
            else:
                logger.info(f"No new emails from Google Groups (all {len(unique_emails)} already collected)")
        
        except Exception as e:
            logger.error(f"Error collecting from Google Groups: {e}")
            import traceback
            logger.debug(traceback.format_exc())
    
    def _collect_from_atom_feed(self, atom_url: str) -> List[Dict[str, Any]]:
        """Collect messages from Atom feed."""
        emails = []
        
        try:
            response = requests.get(atom_url, timeout=30)
            if response.status_code == 200:
                # Parse Atom feed
                import xml.etree.ElementTree as ET
                root = ET.fromstring(response.text)
                
                ns = {'atom': 'http://www.w3.org/2005/Atom'}
                
                for entry in root.findall('atom:entry', ns):
                    title_elem = entry.find('atom:title', ns)
                    link_elem = entry.find('atom:link', ns)
                    id_elem = entry.find('atom:id', ns)
                    updated_elem = entry.find('atom:updated', ns)
                    author_elem = entry.find('atom:author', ns)
                    content_elem = entry.find('atom:content', ns)
                    
                    author_name = ''
                    author_email = ''
                    if author_elem is not None:
                        name_elem = author_elem.find('atom:name', ns)
                        email_elem = author_elem.find('atom:email', ns)
                        author_name = name_elem.text if name_elem is not None else ''
                        author_email = email_elem.text if email_elem is not None else ''
                    
                    email = {
                        'title': title_elem.text if title_elem is not None else '',
                        'link': link_elem.get('href', '') if link_elem is not None else '',
                        'message_id': id_elem.text if id_elem is not None else '',
                        'date': updated_elem.text if updated_elem is not None else '',
                        'from': f"{author_name} <{author_email}>" if author_name else author_email,
                        'body': content_elem.text if content_elem is not None and content_elem.text else '',
                        'subject': title_elem.text if title_elem is not None else '',
                        'source': 'google_groups_atom'
                    }
                    emails.append(email)
            
            logger.info(f"Collected {len(emails)} messages from Atom feed")
            
        except Exception as e:
            logger.debug(f"Error collecting from Atom feed: {e}")
        
        return emails
    
    def _collect_from_rss(self, rss_url: str) -> List[Dict[str, Any]]:
        """Collect messages from RSS feed."""
        emails = []
        
        try:
            response = requests.get(rss_url, timeout=30)
            if response.status_code == 200:
                # Parse RSS (basic parsing)
                soup = BeautifulSoup(response.text, 'xml')
                
                for item in soup.find_all('item'):
                    # Extract subject from title
                    title = item.find('title')
                    title_text = title.get_text() if title else ''
                    subject = re.sub(r'^\[bitcoindev\]\s*', '', title_text, flags=re.IGNORECASE).strip()
                    
                    email = {
                        'subject': subject,
                        'title': title_text,
                        'link': item.find('link').get_text() if item.find('link') else '',
                        'message_id': item.find('guid').get_text() if item.find('guid') else '',
                        'body': item.find('description').get_text() if item.find('description') else '',
                        'date': item.find('pubDate').get_text() if item.find('pubDate') else '',
                        'from': item.find('author').get_text() if item.find('author') else '',
                        'source': 'google_groups_rss'
                    }
                    emails.append(email)
            
            logger.info(f"Collected {len(emails)} messages from RSS feed")
            
        except Exception as e:
            logger.debug(f"Error collecting from RSS: {e}")
        
        return emails


def main():
    """Main entry point."""
    collector = GoogleGroupsCollector()
    collector.collect()


if __name__ == '__main__':
    main()


