#!/usr/bin/env python3
"""
SourceForge Mailman archive collector for Bitcoin mailing lists.

Collects emails from SourceForge Mailman archives (early archives, pre-Linux Foundation).
Uses conservative rate limiting to avoid triggering security measures.
"""

import sys
import json
import time
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config import config
from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir

logger = setup_logger()

# Conservative rate limiting: 1 request per 2 seconds
REQUEST_DELAY = 2.0


class SourceForgeCollector:
    """Collector for SourceForge Mailman archives."""
    
    def __init__(self):
        """Initialize SourceForge collector."""
        self.base_url = "https://sourceforge.net/p/bitcoin/mailman/bitcoin-dev/"
        self.data_dir = get_data_dir() / "mailing_lists"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.emails_file = self.data_dir / 'emails.jsonl'
        
        # Load existing message IDs to avoid duplicates
        self.existing_ids = set()
        if self.emails_file.exists():
            with open(self.emails_file, 'r') as f:
                for line in f:
                    try:
                        email = json.loads(line)
                        if email.get('message_id'):
                            self.existing_ids.add(email['message_id'])
                    except:
                        continue
        
        # Session with user agent
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; Bitcoin Research Bot/1.0; +https://bitcoincommons.org)'
        })
    
    def collect(self):
        """Collect emails from SourceForge archives."""
        logger.info("Starting SourceForge Mailman archive collection")
        logger.info("Using conservative rate limiting (1 request per 2 seconds)")
        
        try:
            # Check if archive is accessible
            logger.info(f"Checking accessibility: {self.base_url}")
            response = self.session.get(self.base_url, timeout=30)
            
            if response.status_code != 200:
                logger.warning(f"SourceForge archive returned status {response.status_code}")
                logger.info("Archive may not be accessible or may have limited content")
                return
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find archive links (monthly archives)
            # SourceForge Mailman archives are typically in a specific structure
            archive_links = []
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                text = link.get_text().strip().lower()
                
                # Filter out image links and other non-archive links
                if any(skip in href.lower() for skip in ['screenshot', 'image', '.jpg', '.png', 'icon', 'logo']):
                    continue
                
                # Look for archive links (typically contain dates, "archive", or "mailman")
                if ('archive' in href.lower() or 'mailman' in href.lower() or 
                    re.search(r'\d{4}', href) or 'list' in href.lower()):
                    full_url = urljoin(self.base_url, href)
                    if full_url not in archive_links and 'sourceforge.net' in full_url:
                        archive_links.append(full_url)
            
            logger.info(f"Found {len(archive_links)} potential archive links")
            
            if not archive_links:
                logger.info("No archive links found. Archive may be empty or use different structure.")
                logger.info("SourceForge archives may have limited historical content.")
                return
            
            # Collect from archives (limit to first 10 to be safe)
            emails = []
            for i, archive_url in enumerate(archive_links[:10]):
                logger.info(f"Processing archive {i+1}/{min(10, len(archive_links))}: {archive_url}")
                
                try:
                    archive_emails = self._collect_from_archive(archive_url)
                    emails.extend(archive_emails)
                    logger.info(f"Collected {len(archive_emails)} emails from this archive")
                    
                    # Conservative delay between archives
                    if i < len(archive_links) - 1:
                        time.sleep(REQUEST_DELAY * 2)  # 4 seconds between archives
                        
                except Exception as e:
                    logger.warning(f"Error processing archive {archive_url}: {e}")
                    # Continue with next archive
                    continue
            
            # Deduplicate
            new_emails = [e for e in emails if e.get('message_id') not in self.existing_ids]
            
            if new_emails:
                with open(self.emails_file, 'a') as f:
                    for email in new_emails:
                        f.write(json.dumps(email) + '\n')
                
                logger.info(f"Added {len(new_emails)} new emails from SourceForge (total unique: {len(emails)})")
            else:
                logger.info(f"No new emails from SourceForge (all {len(emails)} already collected)")
        
        except Exception as e:
            logger.error(f"Error collecting from SourceForge: {e}")
            import traceback
            logger.debug(traceback.format_exc())
    
    def _collect_from_archive(self, archive_url: str) -> List[Dict[str, Any]]:
        """Collect emails from a single archive page."""
        emails = []
        
        try:
            # Conservative delay before each request
            time.sleep(REQUEST_DELAY)
            
            response = self.session.get(archive_url, timeout=30)
            if response.status_code != 200:
                logger.debug(f"Archive page returned {response.status_code}: {archive_url}")
                return emails
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find message links
            message_links = []
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                # Look for message links (typically contain message IDs or dates)
                if 'msg' in href.lower() or re.search(r'\d{6}', href):
                    full_url = urljoin(archive_url, href)
                    if full_url not in message_links:
                        message_links.append(full_url)
            
            logger.debug(f"Found {len(message_links)} message links in archive")
            
            # Process messages (limit to 50 per archive to be safe)
            for i, msg_url in enumerate(message_links[:50]):
                try:
                    # Conservative delay between messages
                    if i > 0:
                        time.sleep(REQUEST_DELAY)
                    
                    email = self._parse_message(msg_url)
                    if email and email.get('message_id') not in self.existing_ids:
                        emails.append(email)
                    
                except Exception as e:
                    logger.debug(f"Error parsing message {msg_url}: {e}")
                    continue
        
        except Exception as e:
            logger.debug(f"Error collecting from archive {archive_url}: {e}")
        
        return emails
    
    def _parse_message(self, msg_url: str) -> Optional[Dict[str, Any]]:
        """Parse a single message page."""
        try:
            time.sleep(REQUEST_DELAY)
            
            response = self.session.get(msg_url, timeout=30)
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract email content (structure varies by Mailman version)
            # Try to find email headers and body
            from_header = ''
            date_header = ''
            subject = ''
            message_id = ''
            body = ''
            
            # Look for common Mailman archive structures
            pre_tags = soup.find_all('pre')
            for pre in pre_tags:
                text = pre.get_text()
                if 'From:' in text or 'Date:' in text:
                    # Parse email from pre tag
                    lines = text.split('\n')
                    for line in lines:
                        if line.startswith('From:'):
                            from_header = line[5:].strip()
                        elif line.startswith('Date:'):
                            date_header = line[5:].strip()
                        elif line.startswith('Subject:'):
                            subject = line[8:].strip()
                        elif line.startswith('Message-ID:'):
                            message_id = line[11:].strip()
                        elif line.startswith('Message-Id:'):
                            message_id = line[11:].strip()
                    
                    # Body is everything after headers
                    body_start = False
                    for line in lines:
                        if body_start:
                            body += line + '\n'
                        elif line.strip() == '' and (from_header or date_header):
                            body_start = True
            
            if not message_id and not from_header:
                # Try alternative parsing
                body = soup.get_text()
            
            if not message_id:
                # Generate a message ID from URL if not found
                message_id = f"<sourceforge-{hash(msg_url)}@sourceforge.net>"
            
            # Parse date
            date_iso = None
            if date_header:
                try:
                    from email.utils import parsedate_to_datetime
                    date_obj = parsedate_to_datetime(date_header)
                    date_iso = date_obj.isoformat()
                except:
                    pass
            
            if not from_header and not body:
                return None
            
            return {
                'list_name': 'bitcoin-dev',
                'message_id': message_id,
                'from': from_header,
                'date': date_iso,
                'subject': subject,
                'body': body,
                'source': 'sourceforge',
                'source_url': msg_url
            }
        
        except Exception as e:
            logger.debug(f"Error parsing message {msg_url}: {e}")
            return None


def main():
    """Main entry point."""
    collector = SourceForgeCollector()
    collector.collect()
    logger.info("SourceForge collection complete")


if __name__ == '__main__':
    main()

