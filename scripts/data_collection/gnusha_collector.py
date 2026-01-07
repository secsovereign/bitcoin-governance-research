#!/usr/bin/env python3
"""
gnusha.org public-inbox collector for Bitcoin mailing lists.

Collects emails from gnusha.org public-inbox using Atom feed and web interface.
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
import xml.etree.ElementTree as ET

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config import config
from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir

logger = setup_logger()


class GnushaCollector:
    """Collector for gnusha.org public-inbox."""
    
    def __init__(self):
        """Initialize gnusha collector."""
        self.sources = {
            'bitcoin-dev': 'https://gnusha.org/pi/bitcoindev/',
            'bitcoin-core-dev': 'https://gnusha.org/pi/bitcoin-core-dev/',
        }
        self.data_dir = get_data_dir() / "mailing_lists"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.emails_file = self.data_dir / 'emails.jsonl'
    
    def collect(self):
        """Collect emails from gnusha.org public-inbox."""
        logger.info("Starting gnusha.org public-inbox collection")
        
        all_emails = []
        
        for list_name, base_url in self.sources.items():
            logger.info(f"Collecting {list_name} from gnusha.org")
            
            # Method 1: Collect from Atom feed (most reliable)
            atom_emails = self._collect_from_atom_feed(list_name, base_url)
            all_emails.extend(atom_emails)
            logger.info(f"Collected {len(atom_emails)} emails from Atom feed for {list_name}")
            
            # Method 2: Collect from web interface (threads)
            web_emails = self._collect_from_web_interface(list_name, base_url)
            all_emails.extend(web_emails)
            logger.info(f"Collected {len(web_emails)} emails from web interface for {list_name}")
        
        # Deduplicate by Message-ID
        seen_message_ids = set()
        unique_emails = []
        for email in all_emails:
            msg_id = email.get('message_id', '')
            if msg_id and msg_id in seen_message_ids:
                continue
            if msg_id:
                seen_message_ids.add(msg_id)
            unique_emails.append(email)
        
        # Append to existing emails file
        existing_ids = set()
        if self.emails_file.exists():
            with open(self.emails_file, 'r') as f:
                for line in f:
                    try:
                        existing_email = json.loads(line)
                        if existing_email.get('message_id'):
                            existing_ids.add(existing_email['message_id'])
                    except:
                        continue
        
        # Only add new emails
        new_emails = [e for e in unique_emails if e.get('message_id') not in existing_ids]
        
        if new_emails:
            with open(self.emails_file, 'a') as f:
                for email in new_emails:
                    f.write(json.dumps(email) + '\n')
            
            logger.info(f"Added {len(new_emails)} new emails from gnusha.org (total unique: {len(unique_emails)})")
        else:
            logger.info(f"No new emails found from gnusha.org (all {len(unique_emails)} already collected)")
    
    def _collect_from_atom_feed(self, list_name: str, base_url: str) -> List[Dict[str, Any]]:
        """Collect emails from Atom feed."""
        emails = []
        atom_url = urljoin(base_url, 'new.atom')
        
        try:
            logger.info(f"Fetching Atom feed from {atom_url}")
            response = requests.get(atom_url, timeout=30)
            response.raise_for_status()
            
            # Parse Atom feed
            root = ET.fromstring(response.text)
            
            # Atom namespace
            ns = {'atom': 'http://www.w3.org/2005/Atom', 'thr': 'http://purl.org/syndication/thread/1.0'}
            
            for entry in root.findall('atom:entry', ns):
                try:
                    # Extract entry data
                    title_elem = entry.find('atom:title', ns)
                    title = title_elem.text if title_elem is not None else ''
                    
                    link_elem = entry.find('atom:link', ns)
                    link = link_elem.get('href', '') if link_elem is not None else ''
                    
                    id_elem = entry.find('atom:id', ns)
                    message_id = id_elem.text if id_elem is not None else ''
                    
                    updated_elem = entry.find('atom:updated', ns)
                    updated = updated_elem.text if updated_elem is not None else ''
                    
                    author_elem = entry.find('atom:author', ns)
                    author_name = ''
                    author_email = ''
                    if author_elem is not None:
                        name_elem = author_elem.find('atom:name', ns)
                        email_elem = author_elem.find('atom:email', ns)
                        author_name = name_elem.text if name_elem is not None else ''
                        author_email = email_elem.text if email_elem is not None else ''
                    
                    content_elem = entry.find('atom:content', ns)
                    content = ''
                    if content_elem is not None:
                        # Content may be in xhtml format
                        if content_elem.get('type') == 'xhtml':
                            # Extract text from xhtml
                            for pre in content_elem.findall('.//{http://www.w3.org/1999/xhtml}pre'):
                                content = pre.text if pre.text else ''
                                break
                        else:
                            content = content_elem.text if content_elem.text else ''
                    
                    # Parse date
                    try:
                        date_obj = datetime.fromisoformat(updated.replace('Z', '+00:00'))
                        date_iso = date_obj.isoformat()
                    except:
                        date_iso = updated
                    
                    # Extract subject from title (remove [bitcoindev] prefix)
                    subject = re.sub(r'^\[bitcoindev\]\s*', '', title, flags=re.IGNORECASE)
                    subject = re.sub(r'^\[bitcoin-core-dev\]\s*', '', subject, flags=re.IGNORECASE)
                    subject = re.sub(r'^Re:\s*', '', subject, flags=re.IGNORECASE).strip()
                    
                    email_data = {
                        'list_name': list_name,
                        'message_id': message_id,
                        'from': f"{author_name} <{author_email}>" if author_name else author_email,
                        'date': date_iso,
                        'subject': subject,
                        'body': content,
                        'source': 'gnusha_atom',
                        'source_url': link
                    }
                    
                    emails.append(email_data)
                    
                except Exception as e:
                    logger.debug(f"Error parsing Atom entry: {e}")
                    continue
            
            logger.info(f"Parsed {len(emails)} entries from Atom feed")
            
        except Exception as e:
            logger.warning(f"Error collecting from Atom feed: {e}")
        
        return emails
    
    def _collect_from_web_interface(self, list_name: str, base_url: str) -> List[Dict[str, Any]]:
        """Collect emails from web interface (threads)."""
        emails = []
        
        try:
            logger.info(f"Fetching web interface from {base_url}")
            response = requests.get(base_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find thread links (format: href="message-id/T/#t")
            thread_links = []
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if '/T/#t' in href or '/T/#u' in href:
                    full_url = urljoin(base_url, href)
                    if full_url not in thread_links:
                        thread_links.append(full_url)
            
            logger.info(f"Found {len(thread_links)} thread links")
            
            # Limit to first 100 threads to avoid too many requests
            # (Atom feed should have most recent messages)
            for i, thread_url in enumerate(thread_links[:100]):
                try:
                    thread_emails = self._parse_thread_page(thread_url, list_name)
                    emails.extend(thread_emails)
                    
                    if (i + 1) % 20 == 0:
                        logger.info(f"Processed {i+1}/{min(100, len(thread_links))} threads")
                        
                except Exception as e:
                    logger.debug(f"Error parsing thread {thread_url}: {e}")
                    continue
            
        except Exception as e:
            logger.warning(f"Error collecting from web interface: {e}")
        
        return emails
    
    def _parse_thread_page(self, thread_url: str, list_name: str) -> List[Dict[str, Any]]:
        """Parse a thread page to extract messages."""
        emails = []
        
        try:
            response = requests.get(thread_url, timeout=30)
            if response.status_code != 200:
                return emails
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Public-inbox format: messages are in <pre> tags or specific divs
            # Look for message content
            pre_tags = soup.find_all('pre')
            for pre in pre_tags:
                text = pre.get_text()
                if 'From:' in text or 'Date:' in text or 'Subject:' in text:
                    # Try to parse as email
                    email_data = self._parse_email_text(text, list_name, thread_url)
                    if email_data:
                        emails.append(email_data)
            
        except Exception as e:
            logger.debug(f"Error parsing thread page {thread_url}: {e}")
        
        return emails
    
    def _parse_email_text(self, email_text: str, list_name: str, source_url: str) -> Optional[Dict[str, Any]]:
        """Parse email text into structured data."""
        try:
            from email import message_from_string
            from email.utils import parsedate_to_datetime
            
            msg = message_from_string(email_text)
            
            from_header = msg.get('From', '')
            date_header = msg.get('Date', '')
            subject = msg.get('Subject', '')
            message_id = msg.get('Message-ID', '')
            
            try:
                date = parsedate_to_datetime(date_header) if date_header else None
                date_iso = date.isoformat() if date else None
            except:
                date_iso = None
            
            # Extract body
            body = ''
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == 'text/plain':
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break
            else:
                body = msg.get_payload(decode=True).decode('utf-8', errors='ignore') if msg.get_payload() else ''
            
            return {
                'list_name': list_name,
                'message_id': message_id,
                'from': from_header,
                'date': date_iso,
                'subject': subject,
                'body': body,
                'source': 'gnusha_web',
                'source_url': source_url
            }
            
        except Exception as e:
            logger.debug(f"Error parsing email text: {e}")
            return None


def main():
    """Main entry point."""
    collector = GnushaCollector()
    collector.collect()
    logger.info("gnusha.org collection complete")


if __name__ == '__main__':
    main()


