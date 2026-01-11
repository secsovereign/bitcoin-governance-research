#!/usr/bin/env python3
"""
Mailing list data collector for Bitcoin development mailing lists.

Collects emails from bitcoin-dev and bitcoin-core-dev mailing lists.
"""

import sys
import json
import re
import gzip
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from email import message_from_string
from email.utils import parsedate_to_datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config import config
from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir

logger = setup_logger()


class MailingListCollector:
    """Collector for mailing list data."""
    
    def __init__(self):
        """Initialize mailing list collector."""
        self.bitcoin_dev_url = config.get(
            'data_collection.mailing_lists.bitcoin_dev.archive_url',
            'https://lists.linuxfoundation.org/pipermail/bitcoin-dev/'
        )
        self.bitcoin_core_dev_url = config.get(
            'data_collection.mailing_lists.bitcoin_core_dev.archive_url',
            'https://lists.linuxfoundation.org/pipermail/bitcoin-core-dev/'
        )
        
        # Alternative archive sources (primary sources are no longer accessible)
        self.alternative_sources = {
            'marc_info': {
                'bitcoin-dev': 'https://marc.info/?l=bitcoin-dev',
                'bitcoin-core-dev': 'https://marc.info/?l=bitcoin-core-dev',
            },
            'mail_archive': {
                'bitcoin-dev': 'https://www.mail-archive.com/bitcoin-dev@lists.linuxfoundation.org/',
                'bitcoin-core-dev': 'https://www.mail-archive.com/bitcoin-core-dev@lists.linuxfoundation.org/',
            },
            'gnusha_public_inbox': {
                'bitcoin-dev': 'https://gnusha.org/pi/bitcoindev/',
                'bitcoin-core-dev': 'https://gnusha.org/pi/bitcoin-core-dev/',
            },
        }
        
        # Note: Mailing list migrated to Google Groups in February 2024
        # Historical archives (2009-2023) use alternative sources above
        # Recent emails (2024+) may need Google Groups API access
        
        # Output paths
        data_dir = get_data_dir()
        self.output_dir = data_dir / 'mailing_lists'
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir = self.output_dir / 'raw'
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        
        self.emails_file = self.output_dir / 'emails.jsonl'
    
    def collect_all_emails(self, skip_existing: bool = True):
        """Collect all emails from both mailing lists.
        
        Args:
            skip_existing: If True, skip emails that already exist. If False, collect all emails.
        """
        logger.info("Starting mailing list collection")
        
        # Load existing emails to avoid duplicates
        existing_emails = set()
        if skip_existing and self.emails_file.exists():
            logger.info(f"Loading existing emails from {self.emails_file}...")
            try:
                with open(self.emails_file, 'r') as f:
                    for line in f:
                        try:
                            email = json.loads(line)
                            # Use Message-ID as primary identifier, fallback to date+subject+from
                            email_id = self._get_email_id(email)
                            if email_id:
                                existing_emails.add(email_id)
                        except:
                            continue
                logger.info(f"Loaded {len(existing_emails)} existing email IDs")
            except Exception as e:
                logger.warning(f"Error loading existing emails: {e}")
        
        self.existing_emails = existing_emails
        
        # Collect bitcoin-dev
        logger.info("Collecting bitcoin-dev mailing list")
        self._collect_list('bitcoin-dev', self.bitcoin_dev_url, skip_existing)
        
        # Collect bitcoin-core-dev
        logger.info("Collecting bitcoin-core-dev mailing list")
        self._collect_list('bitcoin-core-dev', self.bitcoin_core_dev_url, skip_existing)
        
        logger.info("Mailing list collection complete")
    
    def _get_email_id(self, email: Dict[str, Any]) -> Optional[str]:
        """Generate a unique identifier for an email."""
        try:
            # Primary: Use Message-ID if available
            msg_id = email.get('message_id', '')
            if msg_id:
                return f"msgid:{msg_id}"
            
            # Fallback: Use date + subject + from
            date = email.get('date', '')
            subject = email.get('subject', '')
            from_addr = email.get('from', '')
            
            if date and subject and from_addr:
                import hashlib
                # Create hash of subject+from for uniqueness
                content_hash = hashlib.md5(f"{subject}:{from_addr}".encode()).hexdigest()[:8]
                return f"fallback:{date}:{content_hash}"
            
            return None
        except:
            return None
    
    def _collect_list(self, list_name: str, base_url: str, skip_existing: bool = True):
        """Collect emails from a specific mailing list.
        
        Args:
            list_name: Name of the mailing list
            base_url: Base URL for the mailing list archive
            skip_existing: If True, skip emails that already exist
        """
        logger.info(f"Collecting from {list_name} using alternative sources")
        
        all_emails = []
        
        # Try alternative sources in order of preference
        # 1. marc.info (most reliable, well-indexed)
        stopped_early = False
        if list_name in self.alternative_sources['marc_info']:
            logger.info(f"Trying marc.info for {list_name}")
            emails = self._collect_from_marc_info(list_name, skip_existing)
            all_emails.extend(emails)
            logger.info(f"Collected {len(emails)} emails from marc.info")
            
            # Check if we stopped early (this is handled inside _collect_from_marc_info)
            # For now, if we got emails, continue to other sources if needed
        
        # 2. mail-archive.com (skip if we stopped early from marc.info)
        if list_name in self.alternative_sources['mail_archive'] and not stopped_early:
            logger.info(f"Trying mail-archive.com for {list_name}")
            emails = self._collect_from_mail_archive(list_name, skip_existing)
            all_emails.extend(emails)
            logger.info(f"Collected {len(emails)} emails from mail-archive.com")
        
        # 3. Try original pipermail (may find some accessible archives)
        # Get archive URLs starting from most recent
        archive_urls = self._get_archive_urls(base_url, list_name)
        if archive_urls:
            logger.info(f"Found {len(archive_urls)} accessible pipermail archives (processing most recent first)")
            consecutive_existing_archives = 0
            for archive_url in archive_urls:
                logger.info(f"Processing {archive_url}")
                emails = self._download_and_parse_archive(archive_url, list_name)
                
                # Check if this archive had any new emails
                archive_new = 0
                for email in emails:
                    email_id = self._get_email_id(email)
                    if not (skip_existing and email_id and email_id in self.existing_emails):
                        archive_new += 1
                
                all_emails.extend(emails)
                
                # If archive had no new emails and we've collected some, stop
                if archive_new == 0 and len(emails) > 0:
                    consecutive_existing_archives += 1
                    if consecutive_existing_archives >= 3 and len(all_emails) > 0:
                        logger.info(f"Hit {consecutive_existing_archives} consecutive archives with only existing emails. Stopping.")
                        break
                else:
                    consecutive_existing_archives = 0
        
        # Deduplicate within this batch first
        seen_message_ids = set()
        batch_unique = []
        for email in all_emails:
            msg_id = email.get('message_id', '')
            if msg_id and msg_id in seen_message_ids:
                continue
            if msg_id:
                seen_message_ids.add(msg_id)
            batch_unique.append(email)
        
        # Filter out existing emails
        collected = 0
        skipped = 0
        new_emails = []
        for email in batch_unique:
            email_id = self._get_email_id(email)
            if skip_existing and email_id and email_id in self.existing_emails:
                skipped += 1
                continue
            new_emails.append(email)
            if email_id:
                self.existing_emails.add(email_id)
            collected += 1
        
        # Write only new emails
        if new_emails:
            with open(self.emails_file, 'a') as f:
                for email in new_emails:
                    f.write(json.dumps(email) + '\n')
        
        logger.info(f"Collected {collected} new emails from {list_name}, skipped {skipped} existing")
    
    def _get_archive_urls(self, base_url: str, list_name: str = "") -> List[str]:
        """Get list of monthly archive URLs."""
        try:
            # Follow redirects
            response = requests.get(base_url, timeout=30, allow_redirects=True)
            response.raise_for_status()
            
            archive_urls = []
            
            # Method 1: Try to parse HTML for links
            soup = BeautifulSoup(response.text, 'html.parser')
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                # Look for .txt.gz or .mbox files with date patterns
                if ('.txt.gz' in href or '.mbox' in href) and re.search(r'\d{4}-[A-Za-z]{3}', href):
                    full_url = urljoin(response.url, href)  # Use response.url to handle redirects
                    archive_urls.append(full_url)
            
            # Method 2: Generate URLs based on standard pipermail format
            # Pipermail uses: YYYY-MonthName.txt.gz (e.g., 2024-December.txt.gz)
            # Use direct pipermail URL to avoid gnusha redirect issues
            direct_base_url = base_url
            if 'gnusha.org' in response.url:
                # Extract the actual pipermail URL
                if 'bitcoin-dev' in base_url:
                    direct_base_url = 'https://lists.linuxfoundation.org/pipermail/bitcoin-dev/'
                elif 'bitcoin-core-dev' in base_url:
                    direct_base_url = 'https://lists.linuxfoundation.org/pipermail/bitcoin-core-dev/'
            
            if len(archive_urls) < 50:  # If we didn't find many, try generating
                logger.info(f"Trying date-based URL generation for pipermail archives (going back to 2009)")
                logger.warning("Note: Mailing list migrated to Google Groups in Feb 2024. Historical archives may need alternative sources.")
                
                from datetime import datetime
                months = ['January', 'February', 'March', 'April', 'May', 'June',
                         'July', 'August', 'September', 'October', 'November', 'December']
                
                # Go back to 2009 (Bitcoin started in 2009)
                # Note: Archives before 2024 may need Archive.org or other sources
                current_year = datetime.now().year
                current_month_idx = datetime.now().month - 1
                start_year = 2009
                
                logger.info(f"Generating archive URLs from {start_year} to {current_year}")
                logger.info("Trying multiple methods: direct access, Archive.org snapshots, and alternative mirrors")
                
                for year in range(current_year, start_year - 1, -1):
                    # For current year, only try months up to current
                    month_range = range(12) if year < current_year else range(current_month_idx + 1)
                    
                    for month_idx in month_range:
                        month = months[month_idx]
                        # Skip months after migration (Feb 2024+)
                        if year == 2024 and month_idx >= 1:  # February = index 1
                            logger.debug(f"Skipping {year}-{month} (post-migration to Google Groups)")
                            continue
                        
                        # Method 1: Try direct .txt.gz URL
                        url = urljoin(direct_base_url, f"{year}-{month}.txt.gz")
                        try:
                            # Use GET with stream=True to check first few bytes
                            test_response = requests.get(url, timeout=10, allow_redirects=True, stream=True)
                            if test_response.status_code == 200:
                                # Check first 2 bytes for gzip magic number
                                first_bytes = next(test_response.iter_content(2))
                                if first_bytes == b'\x1f\x8b':  # Gzip magic number
                                    if url not in archive_urls:
                                        archive_urls.append(url)
                                        if len(archive_urls) % 20 == 0:
                                            logger.info(f"Found {len(archive_urls)} valid archives so far...")
                            test_response.close()
                        except:
                            pass
                        
                        # Method 2: Try Archive.org Wayback Machine snapshot
                        # Format: https://web.archive.org/web/YYYYMMDDHHMMSS/https://lists.linuxfoundation.org/...
                        if url not in archive_urls and list_name:
                            # Extract list name from base_url if not provided
                            archive_list_name = list_name
                            if not archive_list_name:
                                if 'bitcoin-dev' in base_url:
                                    archive_list_name = 'bitcoin-dev'
                                elif 'bitcoin-core-dev' in base_url:
                                    archive_list_name = 'bitcoin-core-dev'
                            
                            # Try a snapshot from mid-month of that year
                            wayback_url = f"https://web.archive.org/web/{year}{month_idx+1:02d}15/https://lists.linuxfoundation.org/pipermail/{archive_list_name}/{year}-{month}.txt.gz"
                            try:
                                test_response = requests.get(wayback_url, timeout=10, allow_redirects=True, stream=True)
                                if test_response.status_code == 200:
                                    first_bytes = next(test_response.iter_content(2))
                                    if first_bytes == b'\x1f\x8b':
                                        if wayback_url not in archive_urls:
                                            archive_urls.append(wayback_url)
                                            logger.debug(f"Found archive via Wayback Machine: {year}-{month}")
                                test_response.close()
                            except:
                                pass
                        
                        # Method 3: Try .mbox format
                        url = urljoin(direct_base_url, f"{year}-{month}.mbox")
                        if url not in archive_urls:
                            try:
                                test_response = requests.head(url, timeout=10, allow_redirects=True)
                                if test_response.status_code == 200:
                                    content_type = test_response.headers.get('Content-Type', '').lower()
                                    content_length = test_response.headers.get('Content-Length', '0')
                                    # Check if it's a real archive (not HTML error page)
                                    if (any(x in content_type for x in ['mbox', 'text/plain', 'octet-stream', 'application/octet']) and
                                        int(content_length) > 1000):
                                        if url not in archive_urls:
                                            archive_urls.append(url)
                            except:
                                pass
            
            logger.info(f"Found {len(archive_urls)} archive files")
            return sorted(archive_urls, reverse=True)  # Most recent first
            
        except Exception as e:
            logger.error(f"Error getting archive URLs from {base_url}: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return []
    
    def _download_and_parse_archive(self, archive_url: str, list_name: str) -> List[Dict[str, Any]]:
        """Download and parse a monthly archive file."""
        error_log_file = self.raw_dir.parent / 'archive_errors.jsonl'
        
        try:
            # Download archive with redirects
            response = requests.get(archive_url, timeout=60, allow_redirects=True)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('Content-Type', '').lower()
            
            # Check if response is an error page
            response_text = response.text[:500].lower() if len(response.content) < 10000 else ""
            is_error_page = any(keyword in response_text for keyword in [
                'error', 'not found', '404', 'redirect not found', 'no redirect found'
            ])
            
            # Save raw file
            filename = Path(archive_url).name
            raw_file = self.raw_dir / filename
            raw_file.write_bytes(response.content)
            
            # Log error pages/dead links for analysis
            if is_error_page or response.status_code >= 400:
                error_entry = {
                    'archive_url': archive_url,
                    'list_name': list_name,
                    'status_code': response.status_code,
                    'content_type': content_type,
                    'is_error_page': is_error_page,
                    'response_preview': response_text[:200] if response_text else '',
                    'timestamp': datetime.now().isoformat()
                }
                with open(error_log_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(error_entry) + '\n')
                logger.warning(f"Error page/dead link detected: {archive_url} (Status: {response.status_code})")
                return []
            
            # Check if file is actually gzipped by trying to read it
            is_gzipped = False
            if filename.endswith('.txt.gz') or 'gzip' in content_type:
                try:
                    # Try to read first few bytes to check if it's gzipped
                    with open(raw_file, 'rb') as f:
                        magic = f.read(2)
                        if magic == b'\x1f\x8b':  # Gzip magic number
                            is_gzipped = True
                except:
                    pass
            
            # Parse based on file type
            if filename.endswith('.txt.gz') and is_gzipped:
                return self._parse_txt_gz_archive(raw_file, list_name)
            elif filename.endswith('.mbox') or 'mbox' in content_type:
                return self._parse_mbox_archive(raw_file, list_name)
            elif filename.endswith('.txt.gz') and not is_gzipped:
                # Might be HTML redirect page, try to extract actual URL
                logger.warning(f"Expected gzip but got {content_type} for {filename}, trying to find actual archive")
                # Try direct pipermail URL (avoid gnusha redirect)
                if 'gnusha.org' in archive_url or 'gnusha.org' in response.url:
                    # Extract the actual pipermail URL from gnusha redirect
                    # Format: https://gnusha.org/url/https:/lists.linuxfoundation.org/...
                    direct_url = archive_url
                    if 'gnusha.org/url/' in direct_url:
                        direct_url = direct_url.split('gnusha.org/url/')[-1]
                        if direct_url.startswith('https:/') and not direct_url.startswith('https://'):
                            direct_url = direct_url.replace('https:/', 'https://')
                    
                    # If still not a proper URL, construct it from the filename
                    if 'gnusha.org' in direct_url:
                        filename = Path(archive_url).name
                        if 'bitcoin-dev' in list_name.lower() or 'bitcoin-dev' in archive_url:
                            direct_url = f"https://lists.linuxfoundation.org/pipermail/bitcoin-dev/{filename}"
                        elif 'bitcoin-core-dev' in list_name.lower() or 'bitcoin-core-dev' in archive_url:
                            direct_url = f"https://lists.linuxfoundation.org/pipermail/bitcoin-core-dev/{filename}"
                    
                    try:
                        logger.debug(f"Trying direct pipermail URL: {direct_url}")
                        direct_response = requests.get(direct_url, timeout=60, allow_redirects=True)
                        if direct_response.status_code == 200:
                            # Verify it's actually a gzip file
                            content_type = direct_response.headers.get('Content-Type', '').lower()
                            if 'gzip' in content_type or 'octet-stream' in content_type:
                                raw_file.write_bytes(direct_response.content)
                                # Check again if it's gzipped
                                with open(raw_file, 'rb') as f:
                                    magic = f.read(2)
                                    if magic == b'\x1f\x8b':
                                        return self._parse_txt_gz_archive(raw_file, list_name)
                    except Exception as e:
                        logger.debug(f"Could not get direct URL: {e}")
                
                # Log as error if we couldn't parse it
                error_entry = {
                    'archive_url': archive_url,
                    'list_name': list_name,
                    'status_code': response.status_code,
                    'content_type': content_type,
                    'is_error_page': False,
                    'issue': 'Expected gzip but got non-gzip content',
                    'timestamp': datetime.now().isoformat()
                }
                with open(error_log_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(error_entry) + '\n')
                return []
            else:
                logger.warning(f"Unknown archive format: {filename} (Content-Type: {content_type})")
                # Log unknown format
                error_entry = {
                    'archive_url': archive_url,
                    'list_name': list_name,
                    'status_code': response.status_code,
                    'content_type': content_type,
                    'is_error_page': False,
                    'issue': 'Unknown archive format',
                    'timestamp': datetime.now().isoformat()
                }
                with open(error_log_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(error_entry) + '\n')
                return []
                
        except Exception as e:
            logger.error(f"Error processing archive {archive_url}: {e}")
            # Log exception
            error_entry = {
                'archive_url': archive_url,
                'list_name': list_name,
                'status_code': None,
                'content_type': None,
                'is_error_page': False,
                'issue': f'Exception: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }
            with open(error_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(error_entry) + '\n')
            return []
    
    def _parse_txt_gz_archive(self, archive_file: Path, list_name: str) -> List[Dict[str, Any]]:
        """Parse a .txt.gz archive file."""
        emails = []
        
        try:
            with gzip.open(archive_file, 'rt', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # Split into individual emails (separated by "From " at start of line)
                email_texts = re.split(r'\n(?=From )', content)
                
                for email_text in email_texts:
                    if not email_text.strip():
                        continue
                    
                    email_data = self._parse_email_text(email_text, list_name)
                    if email_data:
                        emails.append(email_data)
        
        except Exception as e:
            logger.error(f"Error parsing {archive_file}: {e}")
        
        return emails
    
    def _parse_mbox_archive(self, archive_file: Path, list_name: str) -> List[Dict[str, Any]]:
        """Parse an mbox archive file."""
        emails = []
        
        try:
            with open(archive_file, 'rb') as f:
                content = f.read().decode('utf-8', errors='ignore')
                
                # Split into individual emails
                email_texts = re.split(r'\n(?=From )', content)
                
                for email_text in email_texts:
                    if not email_text.strip():
                        continue
                    
                    email_data = self._parse_email_text(email_text, list_name)
                    if email_data:
                        emails.append(email_data)
        
        except Exception as e:
            logger.error(f"Error parsing {archive_file}: {e}")
        
        return emails
    
    def _parse_email_text(self, email_text: str, list_name: str) -> Optional[Dict[str, Any]]:
        """Parse email text into structured data."""
        try:
            # Parse email message
            msg = message_from_string(email_text)
            
            # Extract headers
            from_header = msg.get('From', '')
            date_header = msg.get('Date', '')
            subject = msg.get('Subject', '')
            message_id = msg.get('Message-ID', '')
            in_reply_to = msg.get('In-Reply-To', '')
            references = msg.get('References', '')
            
            # Parse date
            try:
                date = parsedate_to_datetime(date_header) if date_header else None
                date_iso = date.isoformat() if date else None
            except:
                date_iso = None
            
            # Extract body
            body = self._extract_body(msg)
            
            # Identify quoted text
            quoted_text = self._identify_quoted_text(body)
            original_text = self._remove_quoted_text(body)
            
            email_data = {
                'list_name': list_name,
                'message_id': message_id,
                'from': from_header,
                'date': date_iso,
                'subject': subject,
                'body': body,
                'original_text': original_text,
                'quoted_text': quoted_text,
                'in_reply_to': in_reply_to,
                'references': references,
            }
            
            return email_data
            
        except Exception as e:
            logger.debug(f"Error parsing email: {e}")
            return None
    
    def _collect_from_marc_info(self, list_name: str, skip_existing: bool = True) -> List[Dict[str, Any]]:
        """Collect emails from marc.info archive.
        
        Args:
            list_name: Name of the mailing list
            skip_existing: If True, skip emails that already exist
        """
        emails = []
        base_url = self.alternative_sources['marc_info'][list_name]
        
        try:
            # Get the main page to find monthly archives
            response = requests.get(base_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find monthly archive links (format: ?l=list&r=1&b=YYYYMM&w=2)
            archive_links = []
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if '&b=' in href and '&w=2' in href:  # Monthly archive link
                    full_url = urljoin(base_url, href)
                    # Extract date from URL for sorting
                    date_match = re.search(r'&b=(\d{6})', href)
                    if date_match:
                        archive_links.append((date_match.group(1), full_url))
            
            # Sort by date (most recent first) - YYYYMM format sorts correctly
            archive_links.sort(key=lambda x: x[0], reverse=True)
            archive_links = [url for _, url in archive_links]  # Extract just URLs
            
            logger.info(f"Found {len(archive_links)} monthly archives on marc.info (processing most recent first)")
            
            # Process each monthly archive starting from most recent
            consecutive_existing_months = 0
            for archive_url in archive_links:
                try:
                    month_emails = self._parse_marc_info_archive(archive_url, list_name)
                    
                    # Check how many are new (not in existing_emails)
                    month_new = 0
                    for email in month_emails:
                        email_id = self._get_email_id(email)
                        if not (skip_existing and email_id and email_id in self.existing_emails):
                            month_new += 1
                    
                    emails.extend(month_emails)
                    
                    # If this month had no new emails and we've collected some, increment counter
                    if month_new == 0 and len(month_emails) > 0:
                        consecutive_existing_months += 1
                        # Stop if we hit 3 consecutive months with only existing emails
                        if consecutive_existing_months >= 3 and len(emails) > 0:
                            logger.info(f"Hit {consecutive_existing_months} consecutive months with only existing emails. Stopping marc.info collection.")
                            break
                    else:
                        consecutive_existing_months = 0
                    
                    if len(emails) % 100 == 0:
                        logger.info(f"Collected {len(emails)} emails from marc.info so far (working backwards)...")
                except Exception as e:
                    logger.debug(f"Error processing {archive_url}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error collecting from marc.info: {e}")
        
        return emails
    
    def _parse_marc_info_archive(self, archive_url: str, list_name: str) -> List[Dict[str, Any]]:
        """Parse a marc.info monthly archive page (handles pagination)."""
        emails = []
        
        try:
            # marc.info uses ?r=N for pagination (r=1, r=2, etc.)
            # We need to fetch all pages for this month
            page_num = 1
            all_message_links = []
            
            while True:
                # Build URL with page number
                if '&r=' in archive_url:
                    page_url = re.sub(r'&r=\d+', f'&r={page_num}', archive_url)
                else:
                    page_url = f"{archive_url}&r={page_num}"
                
                response = requests.get(page_url, timeout=30)
                if response.status_code != 200:
                    break
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find message links on this page
                page_message_links = []
                for link in soup.find_all('a', href=True):
                    href = link.get('href', '')
                    # Message links have &m= parameter
                    if '&m=' in href:
                        full_url = urljoin(page_url, href)
                        if full_url not in all_message_links:
                            page_message_links.append(full_url)
                            all_message_links.append(full_url)
                
                logger.debug(f"Page {page_num}: Found {len(page_message_links)} messages")
                
                # If no messages found on this page, we've reached the end
                if not page_message_links:
                    break
                
                # Check if there's a "next" link or higher page numbers
                has_next = False
                max_page_found = page_num
                
                for link in soup.find_all('a', href=True):
                    text = link.get_text().lower()
                    href = link.get('href', '')
                    # Look for "next" link
                    if 'next' in text and '&r=' in href:
                        next_page_match = re.search(r'&r=(\d+)', href)
                        if next_page_match:
                            next_page = int(next_page_match.group(1))
                            if next_page > page_num:
                                has_next = True
                                max_page_found = max(max_page_found, next_page)
                    # Look for "last" link to find the actual last page
                    elif 'last' in text and '&r=' in href:
                        last_page_match = re.search(r'&r=(\d+)', href)
                        if last_page_match:
                            last_page = int(last_page_match.group(1))
                            max_page_found = max(max_page_found, last_page)
                    # Check for any links with higher page numbers
                    elif '&r=' in href and '&b=' in href:
                        page_match = re.search(r'&r=(\d+)', href)
                        if page_match:
                            link_page = int(page_match.group(1))
                            if link_page > page_num:
                                max_page_found = max(max_page_found, link_page)
                
                # marc.info typically shows ~30 messages per page
                # Continue if we got 30 messages (likely more pages) or found a next/last link
                if len(page_message_links) < 30 and not has_next and max_page_found == page_num:
                    # Likely last page - no more messages and no next page found
                    break
                
                # If we found a "last" link with a higher page number, we know there are more pages
                # Continue fetching until we reach that page
                if max_page_found > page_num:
                    has_next = True
                
                page_num += 1
                
                # Safety limit: don't fetch more than 100 pages (shouldn't be needed)
                if page_num > 100:
                    logger.warning(f"Reached page limit (100) for {archive_url}")
                    break
            
            logger.info(f"Found {len(all_message_links)} total messages across {page_num-1} pages for {archive_url}")
            
            # Fetch each individual message
            for i, msg_url in enumerate(all_message_links):
                try:
                    msg_response = requests.get(msg_url, timeout=30)
                    if msg_response.status_code == 200:
                        email_dict = self._parse_marc_info_message(msg_response.text, list_name, msg_url)
                        if email_dict:
                            emails.append(email_dict)
                    
                    # Progress logging every 100 messages
                    if (i + 1) % 100 == 0:
                        logger.info(f"Processed {i+1}/{len(all_message_links)} messages from {archive_url}")
                        
                except Exception as e:
                    logger.debug(f"Error fetching message {msg_url}: {e}")
                    continue
        
        except Exception as e:
            logger.debug(f"Error parsing marc.info archive {archive_url}: {e}")
        
        return emails
    
    def _parse_marc_info_message(self, html_content: str, list_name: str, source_url: str) -> Optional[Dict[str, Any]]:
        """Parse a single marc.info message page."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # marc.info messages are typically in <pre> tags
            pre_tags = soup.find_all('pre')
            message_text = ''
            for pre in pre_tags:
                text = pre.get_text()
                # Look for email headers
                if 'From:' in text or 'Date:' in text:
                    message_text = text
                    break
            
            if not message_text:
                # Try to get all text
                message_text = soup.get_text()
            
            # Parse the email text
            return self._parse_email_text(message_text, list_name, source_url)
        
        except Exception as e:
            logger.debug(f"Error parsing marc.info message: {e}")
            return None
    
    def _collect_from_mail_archive(self, list_name: str, skip_existing: bool = True) -> List[Dict[str, Any]]:
        """Collect emails from mail-archive.com - FULL IMPLEMENTATION.
        
        Args:
            list_name: Name of the mailing list
            skip_existing: If True, skip emails that already exist
        """
        emails = []
        base_url = self.alternative_sources['mail_archive'][list_name]
        
        try:
            logger.info(f"Collecting from mail-archive.com for {list_name}")
            
            # Method 1: Parse maillist.html and follow pagination
            all_message_links = []
            pages_visited = set()
            current_page = "maillist.html"
            
            # Follow pagination to collect all message links
            while current_page:
                if current_page in pages_visited:
                    break
                pages_visited.add(current_page)
                
                page_url = urljoin(base_url, current_page)
                response = requests.get(page_url, timeout=30)
                if response.status_code != 200:
                    break
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract all message links (format: msgXXXXX.html)
                page_message_links = []
                for link in soup.find_all('a', href=True):
                    href = link.get('href', '')
                    if 'msg' in href and href.endswith('.html'):
                        full_url = urljoin(page_url, href)
                        if full_url not in all_message_links:
                            page_message_links.append(full_url)
                            all_message_links.append(full_url)
                
                logger.info(f"Page {current_page}: Found {len(page_message_links)} message links (total: {len(all_message_links)})")
                
                # Find "Earlier messages" link for next page
                next_page = None
                for link in soup.find_all('a', href=True):
                    text = link.get_text().lower()
                    if 'earlier' in text:
                        next_page = link.get('href', '')
                        break
                
                current_page = next_page
                
                # Safety limit
                if len(pages_visited) > 1000:
                    logger.warning(f"Reached page limit (1000) for mail-archive.com")
                    break
            
            logger.info(f"Found {len(all_message_links)} total message links from mail-archive.com")
            
            # Method 2: Also try sequential access (msg00001.html, msg00002.html, etc.)
            # This is a backup method in case pagination misses some
            # Work backwards from most recent (20000) to find new messages faster
            logger.info("Also trying sequential message access (working backwards from most recent)...")
            sequential_found = 0
            consecutive_404s = 0
            max_consecutive_404s = 50  # Stop after 50 consecutive 404s
            
            # Start from 20000 and work backwards
            for msg_num in range(20000, 0, -1):
                msg_url = urljoin(base_url, f"msg{msg_num:05d}.html")
                try:
                    resp = requests.head(msg_url, timeout=5)
                    if resp.status_code == 200:
                        consecutive_404s = 0  # Reset counter on success
                        if msg_url not in all_message_links:
                            all_message_links.append(msg_url)
                            sequential_found += 1
                            if sequential_found % 100 == 0:
                                logger.info(f"Found {sequential_found} additional messages via sequential access (checking {msg_num}...)...")
                    else:
                        consecutive_404s += 1
                        # Stop early if we hit many consecutive 404s (reached end of messages)
                        if consecutive_404s >= max_consecutive_404s:
                            logger.info(f"Hit {consecutive_404s} consecutive 404s, stopping sequential access at message {msg_num}")
                            break
                except:
                    consecutive_404s += 1
                    if consecutive_404s >= max_consecutive_404s:
                        logger.info(f"Hit {consecutive_404s} consecutive errors, stopping sequential access at message {msg_num}")
                        break
                    pass
            
            logger.info(f"Sequential access found {sequential_found} additional messages")
            logger.info(f"Total unique message URLs: {len(all_message_links)}")
            
            # Fetch each message
            for i, msg_url in enumerate(all_message_links):
                try:
                    msg_response = requests.get(msg_url, timeout=30)
                    if msg_response.status_code == 200:
                        email_dict = self._parse_mail_archive_message(msg_response.text, list_name, msg_url)
                        if email_dict:
                            emails.append(email_dict)
                    
                    # Progress logging
                    if (i + 1) % 100 == 0:
                        logger.info(f"Processed {i+1}/{len(all_message_links)} messages from mail-archive.com...")
                        
                except Exception as e:
                    logger.debug(f"Error fetching message {msg_url}: {e}")
                    continue
            
            logger.info(f"Collected {len(emails)} emails from mail-archive.com")
            
        except Exception as e:
            logger.error(f"Error collecting from mail-archive.com: {e}")
            import traceback
            logger.debug(traceback.format_exc())
        
        return emails
    
    def _parse_mail_archive_message(self, html_content: str, list_name: str, source_url: str) -> Optional[Dict[str, Any]]:
        """Parse a single mail-archive.com message page."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # mail-archive.com uses specific HTML structure:
            # - Subject in <span class="subject"> or <a class="subject">
            # - Date in <span class="date">
            # - Sender in <span class="sender"> or in <pre> tag as "From: ..."
            # - Body in <pre> tag (but skip footer)
            
            # Find subject
            subject_elem = soup.find(class_='subject')
            if not subject_elem:
                # Try in title
                title = soup.find('title')
                if title:
                    subject_text = title.get_text().strip()
                    # Remove list name prefix if present
                    subject_text = re.sub(r'^\[bitcoin-dev\]\s*', '', subject_text, flags=re.I)
                    subject_header = subject_text
                else:
                    subject_header = ""
            else:
                subject_header = subject_elem.get_text().strip()
                # Remove list name prefix if present
                subject_header = re.sub(r'^\[bitcoin-dev\]\s*', '', subject_header, flags=re.I)
            
            # Find date
            date_elem = soup.find(class_='date')
            date_header = date_elem.get_text().strip() if date_elem else None
            
            # Find sender/from
            from_header = None
            sender_elem = soup.find(class_='sender')
            if sender_elem:
                from_header = sender_elem.get_text().strip()
                # Remove "via bitcoin-dev" suffix if present
                from_header = re.sub(r'\s+via\s+bitcoin-dev.*$', '', from_header, flags=re.I)
            
            # If no sender class, look in <pre> tags for "From:"
            if not from_header:
                pre_tags = soup.find_all('pre')
                for pre in pre_tags:
                    text = pre.get_text()
                    from_match = re.search(r'From:\s*(.+?)(?:\n|$)', text)
                    if from_match:
                        from_header = from_match.group(1).strip()
                        # Remove "via bitcoin-dev" suffix
                        from_header = re.sub(r'\s+via\s+bitcoin-dev.*$', '', from_header, flags=re.I)
                        break
            
            # Find body - could be in <pre> tag or in msgBody div
            body = ""
            
            # First try msgBody div (articleBody)
            msg_body_elem = soup.find(class_='msgBody') or soup.find(itemprop='articleBody')
            if msg_body_elem:
                # Get text but skip navigation/button elements
                for elem in msg_body_elem.find_all(['div', 'p', 'pre']):
                    text = elem.get_text().strip()
                    # Skip if it's navigation or buttons
                    if any(x in text.lower() for x in ['previous', 'next', 'view by', 'reply', 'forward']):
                        continue
                    # Skip if it's just the mailing list footer
                    if 'Bitcoin-dev mailing list' in text or 'mailman/listinfo' in text:
                        continue
                    if len(text) > 50:  # Likely actual content
                        body = text
                        break
            
            # If no body found, try <pre> tags
            if not body:
                pre_tags = soup.find_all('pre')
                for pre in pre_tags:
                    text = pre.get_text().strip()
                    # Skip if it's just the mailing list footer
                    if 'Bitcoin-dev mailing list' in text or 'mailman/listinfo' in text or text.count('_') > 10:
                        continue
                    # This is likely the message body
                    if len(text) > 20:  # Must have some content
                        body = text
                        # Remove footer if present
                        footer_match = re.search(r'(__+|Bitcoin-dev mailing list)', body, re.I)
                        if footer_match:
                            body = body[:footer_match.start()].strip()
                        break
            
            # Find Message-ID - might be in a link or meta tag
            message_id = None
            # Try to extract from URL
            msg_match = re.search(r'msg(\d+)\.html', source_url)
            if msg_match:
                message_id = f"<mail-archive-{msg_match.group(1)}>"
            
            # Parse date to ISO format if possible
            date_iso = None
            if date_header:
                try:
                    from email.utils import parsedate_to_datetime
                    date_iso = parsedate_to_datetime(date_header).isoformat()
                except:
                    # Try alternative date formats
                    try:
                        from dateutil import parser as date_parser
                        date_iso = date_parser.parse(date_header).isoformat()
                    except:
                        date_iso = date_header
            
            # We need at least date and either from or subject to consider this valid
            if date_header and (from_header or subject_header):
                return {
                    'list_name': list_name,
                    'message_id': message_id or '',
                    'from': from_header or 'unknown',
                    'date': date_iso or date_header,
                    'subject': subject_header or '',
                    'body': body,
                    'source': 'mail_archive',
                    'source_url': source_url,
                }
        
        except Exception as e:
            logger.debug(f"Error parsing mail-archive.com message: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None
    
    def _parse_email_text(self, text: str, list_name: str, source_url: str) -> Optional[Dict[str, Any]]:
        """Parse email text into structured format."""
        try:
            # Try to extract headers
            from_match = re.search(r'From:\s*(.+)', text)
            date_match = re.search(r'Date:\s*(.+)', text)
            subject_match = re.search(r'Subject:\s*(.+)', text)
            message_id_match = re.search(r'Message-ID:\s*(.+)', text)
            
            if not from_match or not date_match:
                return None
            
            # Extract body (everything after headers)
            body_start = text.find('\n\n')
            body = text[body_start:].strip() if body_start > 0 else text
            
            return {
                'list_name': list_name,
                'message_id': message_id_match.group(1).strip() if message_id_match else '',
                'from': from_match.group(1).strip(),
                'date': date_match.group(1).strip(),
                'subject': subject_match.group(1).strip() if subject_match else '',
                'body': body,
                'source': 'marc_info',
                'source_url': source_url,
            }
        except Exception as e:
            logger.debug(f"Error parsing email text: {e}")
            return None
    
    def _extract_body(self, msg) -> str:
        """Extract body text from email message."""
        body = ""
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == 'text/plain':
                    payload = part.get_payload(decode=True)
                    if payload:
                        body += payload.decode('utf-8', errors='ignore')
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode('utf-8', errors='ignore')
        
        return body
    
    def _identify_quoted_text(self, text: str) -> str:
        """Identify quoted text in email body."""
        # Common quote patterns
        patterns = [
            r'^>.*$',  # Lines starting with >
            r'^On .* wrote:.*$',  # "On date, person wrote:"
            r'^-----Original Message-----.*$',  # Outlook style
        ]
        
        quoted_lines = []
        for line in text.split('\n'):
            for pattern in patterns:
                if re.match(pattern, line):
                    quoted_lines.append(line)
                    break
        
        return '\n'.join(quoted_lines)
    
    def _remove_quoted_text(self, text: str) -> str:
        """Remove quoted text from email body."""
        # Remove lines starting with >
        lines = text.split('\n')
        original_lines = [line for line in lines if not re.match(r'^>', line)]
        return '\n'.join(original_lines)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Collect emails from Bitcoin development mailing lists')
    parser.add_argument('--skip-existing', action='store_true', default=True,
                       help='Skip emails that already exist (default: True)')
    parser.add_argument('--no-skip-existing', dest='skip_existing', action='store_false',
                       help='Collect all emails, including duplicates')
    
    args = parser.parse_args()
    
    collector = MailingListCollector()
    collector.collect_all_emails(skip_existing=args.skip_existing)


if __name__ == '__main__':
    main()

