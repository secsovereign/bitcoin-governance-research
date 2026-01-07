#!/usr/bin/env python3
"""
Archive.org Wayback Machine collector for Bitcoin mailing list archives.

Attempts to recover historical pipermail archives from Wayback Machine snapshots.
Uses very conservative rate limiting to respect Archive.org's servers.
"""

import sys
import json
import time
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote
import re

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config import config
from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir

logger = setup_logger()

# Very conservative rate limiting: 1 request per 4 seconds (Archive.org is slow)
REQUEST_DELAY = 4.0
MAX_SNAPSHOTS = 20  # Limit number of snapshots to check


class ArchiveOrgCollector:
    """Collector for Archive.org Wayback Machine."""
    
    def __init__(self):
        """Initialize Archive.org collector."""
        self.wayback_api = "https://web.archive.org/web/"
        self.original_url = "https://lists.linuxfoundation.org/pipermail/bitcoin-dev/"
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
            'User-Agent': 'Mozilla/5.0 (compatible; Bitcoin Research Bot/1.0; +https://bitcoincommons.org)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })
    
    def collect(self):
        """Collect emails from Archive.org snapshots."""
        logger.info("Starting Archive.org Wayback Machine collection")
        logger.info("Using very conservative rate limiting (1 request per 4 seconds)")
        logger.info(f"Limiting to {MAX_SNAPSHOTS} snapshots to be safe")
        
        try:
            # Get available snapshots for the URL
            logger.info(f"Checking for snapshots of: {self.original_url}")
            snapshots = self._get_available_snapshots()
            
            if not snapshots:
                logger.info("No snapshots found in Wayback Machine")
                logger.info("Archive.org may not have archived the pipermail archives")
                return
            
            logger.info(f"Found {len(snapshots)} snapshots (checking first {MAX_SNAPSHOTS})")
            
            emails = []
            for i, snapshot in enumerate(snapshots[:MAX_SNAPSHOTS]):
                logger.info(f"Processing snapshot {i+1}/{min(MAX_SNAPSHOTS, len(snapshots))}: {snapshot.get('timestamp', 'unknown')}")
                
                try:
                    snapshot_emails = self._collect_from_snapshot(snapshot)
                    emails.extend(snapshot_emails)
                    logger.info(f"Collected {len(snapshot_emails)} emails from this snapshot")
                    
                    # Very conservative delay between snapshots
                    if i < len(snapshots) - 1:
                        time.sleep(REQUEST_DELAY * 2)  # 8 seconds between snapshots
                        
                except Exception as e:
                    logger.warning(f"Error processing snapshot: {e}")
                    # Continue with next snapshot
                    continue
            
            # Deduplicate
            new_emails = [e for e in emails if e.get('message_id') not in self.existing_ids]
            
            if new_emails:
                with open(self.emails_file, 'a') as f:
                    for email in new_emails:
                        f.write(json.dumps(email) + '\n')
                
                logger.info(f"Added {len(new_emails)} new emails from Archive.org (total unique: {len(emails)})")
            else:
                logger.info(f"No new emails from Archive.org (all {len(emails)} already collected)")
        
        except Exception as e:
            logger.error(f"Error collecting from Archive.org: {e}")
            import traceback
            logger.debug(traceback.format_exc())
    
    def _get_available_snapshots(self) -> List[Dict[str, Any]]:
        """Get list of available snapshots from Wayback Machine."""
        snapshots = []
        
        try:
            # Use Wayback Machine CDX API to get snapshots
            # Format: https://web.archive.org/cdx/search/cdx?url=URL&output=json
            cdx_url = f"https://web.archive.org/cdx/search/cdx"
            params = {
                'url': self.original_url,
                'output': 'json',
                'limit': MAX_SNAPSHOTS  # Limit results
            }
            
            time.sleep(REQUEST_DELAY)
            
            response = self.session.get(cdx_url, params=params, timeout=60)
            if response.status_code != 200:
                logger.warning(f"CDX API returned {response.status_code}")
                return snapshots
            
            try:
                data = response.json()
                # CDX API returns array of arrays: [timestamp, original-url, ...]
                # Skip header row if present
                for row in data[1:] if len(data) > 1 and isinstance(data[0], list) else data:
                    if len(row) >= 2:
                        timestamp = row[0]
                        original = row[1]
                        # Build snapshot URL
                        snapshot_url = f"{self.wayback_api}{timestamp}/{original}"
                        snapshots.append({
                            'timestamp': timestamp,
                            'url': snapshot_url,
                            'original': original
                        })
            except json.JSONDecodeError:
                logger.warning("CDX API did not return JSON")
                # Try alternative: just get a few recent snapshots manually
                # Generate some likely snapshot dates (monthly from 2009-2023)
                for year in range(2009, 2024):
                    for month in [1, 6, 12]:  # Just a few months per year
                        timestamp = f"{year}{month:02d}01000000"  # First of month
                        snapshot_url = f"{self.wayback_api}{timestamp}/{self.original_url}"
                        snapshots.append({
                            'timestamp': timestamp,
                            'url': snapshot_url,
                            'original': self.original_url
                        })
                        if len(snapshots) >= MAX_SNAPSHOTS:
                            break
                    if len(snapshots) >= MAX_SNAPSHOTS:
                        break
        
        except Exception as e:
            logger.debug(f"Error getting snapshots: {e}")
        
        return snapshots
    
    def _collect_from_snapshot(self, snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect emails from a single Wayback Machine snapshot."""
        emails = []
        
        try:
            time.sleep(REQUEST_DELAY)
            
            snapshot_url = snapshot['url']
            logger.debug(f"Fetching snapshot: {snapshot_url}")
            
            # Wayback Machine can have redirect loops, limit redirects
            response = self.session.get(snapshot_url, timeout=60, allow_redirects=True, max_redirects=5)
            if response.status_code != 200:
                logger.debug(f"Snapshot returned {response.status_code}")
                return emails
            
            # Wayback Machine may return HTML wrapper, try to extract content
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check if this is a pipermail archive page or just HTML wrapper
            # Pipermail archives typically have links to monthly archives or messages
            archive_links = []
            
            # First, try to find links to actual archive files (.txt.gz, .txt)
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                text = link.get_text().strip()
                
                # Look for links to archive files
                if any(ext in href.lower() for ext in ['.txt.gz', '.txt', '.gz']):
                    # Make absolute URL
                    if href.startswith('http'):
                        full_url = href
                    else:
                        full_url = urljoin(snapshot_url, href)
                    archive_links.append(full_url)
                    logger.debug(f"Found archive file link: {full_url}")
            
            # Also look for monthly archive directory links (YYYY-MM format)
            if not archive_links:
                for link in soup.find_all('a', href=True):
                    href = link.get('href', '')
                    text = link.get_text().strip()
                    # Look for monthly archive links (format: 2015-01, etc.)
                    if re.search(r'\d{4}-\d{2}', href) or re.search(r'\d{4}-\d{2}', text):
                        if href.startswith('http'):
                            full_url = href
                        else:
                            full_url = urljoin(snapshot_url, href)
                        if full_url not in archive_links:
                            archive_links.append(full_url)
                            logger.debug(f"Found monthly archive link: {full_url}")
            
            # Also look for individual message links
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if 'msg' in href.lower() and ('html' in href.lower() or 'txt' in href.lower()):
                    if href.startswith('http'):
                        full_url = href
                    else:
                        full_url = urljoin(snapshot_url, href)
                    if full_url not in archive_links:
                        archive_links.append(full_url)
            
            if not archive_links:
                # May be HTML wrapper - try to find actual content
                # Wayback Machine often wraps content in iframes or divs
                iframe = soup.find('iframe', {'id': 'playback'})
                if iframe:
                    iframe_src = iframe.get('src', '')
                    if iframe_src:
                        # Fetch the iframe content
                        time.sleep(REQUEST_DELAY)
                        iframe_response = self.session.get(iframe_src, timeout=60)
                        if iframe_response.status_code == 200:
                            soup = BeautifulSoup(iframe_response.text, 'html.parser')
                            # Now look for archive links again
                            for link in soup.find_all('a', href=True):
                                href = link.get('href', '')
                                if re.search(r'\d{4}-\d{2}', href) or 'msg' in href.lower():
                                    full_url = urljoin(iframe_src, href)
                                    archive_links.append(full_url)
            
            logger.debug(f"Found {len(archive_links)} archive links in snapshot")
            
            # Limit processing to first 5 links per snapshot
            for link_url in archive_links[:5]:
                try:
                    # Try to parse as email archive
                    link_emails = self._parse_archive_link(link_url)
                    emails.extend(link_emails)
                    
                    time.sleep(REQUEST_DELAY)
                    
                except Exception as e:
                    logger.debug(f"Error parsing archive link {link_url}: {e}")
                    continue
        
        except Exception as e:
            logger.debug(f"Error collecting from snapshot: {e}")
        
        return emails
    
    def _parse_archive_link(self, link_url: str) -> List[Dict[str, Any]]:
        """Parse an archive link to extract emails."""
        emails = []
        
        try:
            # This is a simplified parser - actual implementation would need
            # to handle different archive formats (txt.gz, mbox, etc.)
            # For now, just try to extract any email-like content
            
            response = self.session.get(link_url, timeout=60)
            if response.status_code != 200:
                return emails
            
            # Check content type
            content_type = response.headers.get('Content-Type', '').lower()
            
            if 'text/plain' in content_type or link_url.endswith('.txt'):
                # Try to parse as text email archive
                text = response.text
                # Split by "From " lines (common email archive format)
                email_texts = re.split(r'\n(?=From )', text)
                
                for email_text in email_texts[:10]:  # Limit to 10 per link
                    if 'From:' in email_text and 'Date:' in email_text:
                        email = self._parse_email_text(email_text)
                        if email and email.get('message_id') not in self.existing_ids:
                            emails.append(email)
        
        except Exception as e:
            logger.debug(f"Error parsing archive link: {e}")
        
        return emails
    
    def _parse_email_text(self, email_text: str) -> Optional[Dict[str, Any]]:
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
            
            if not message_id:
                return None
            
            return {
                'list_name': 'bitcoin-dev',
                'message_id': message_id,
                'from': from_header,
                'date': date_iso,
                'subject': subject,
                'body': body,
                'source': 'archive_org',
                'source_url': ''
            }
        
        except Exception as e:
            logger.debug(f"Error parsing email text: {e}")
            return None


def main():
    """Main entry point."""
    collector = ArchiveOrgCollector()
    collector.collect()
    logger.info("Archive.org collection complete")


if __name__ == '__main__':
    main()

