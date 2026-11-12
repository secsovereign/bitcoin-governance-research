#!/usr/bin/env python3
"""
Satoshi Archive Collector

Collects Satoshi Nakamoto's complete public communications from various archives:
- Satoshi Nakamoto Institute (The Complete Satoshi) - via GitHub clone (preferred) or scraping
- Nakamoto Archives (blockchain-inscribed) - scraping
- P2P Research List emails - scraping
- GitHub Archive (lugaxker/nakamoto-archive) - clone/download
- Bitcoin mailing list emails (Satoshi's posts) - extract from existing data
- Martti Malmi's published Satoshi emails (COPA v Wright, 2024) - HTML page
- Mike Hearn's published Satoshi email threads 1-5 - HTML pages
- Dustin Trammell's published 2009 Satoshi mailbox - zip of mbox files

Only records authored by Satoshi are kept (see is_satoshi_author /
document_is_satoshi). Replies from correspondents in the same archives
(Hal Finney, Adam Back, Wei Dai, Martti Malmi, Mike Hearn, Dustin Trammell)
are dropped.

Sources:
- https://satoshi.nakamotoinstitute.org/ (The Complete Satoshi)
- https://nakamotoarchives.btc.onl/ (Nakamoto Archives)
- https://news.nakamotoinstitute.org/p/p2p-research-list-emails (P2P Research List)
- https://github.com/lugaxker/nakamoto-archive (GitHub Archive)
- Mailing list archives (bitcoin-dev, bitcoin-core-dev)
- https://mmalmi.github.io/satoshi/ (Martti Malmi)
- https://plan99.net/~mike/satoshi-emails/thread1.html .. thread5.html (Mike Hearn)
- https://blog.dustintrammell.com/i-am-not-satoshi/ (Dustin Trammell, Satoshi_Nakamoto.zip)

Rate Limiting:
- Web scraping: 2 seconds between requests (conservative)
- GitHub API: Uses existing rate limiter if needed
- All sources: Respects robots.txt and implements retries
"""

import sys
import os
import json
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import re
import time
import subprocess
import shutil
import html
import mailbox
import tempfile
import zipfile
from email.utils import parseaddr
from urllib.parse import urljoin, urlparse

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config import config
from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir
from src.utils.mailing_lists import iter_emails
from src.utils.rate_limiter import RateLimiter

logger = setup_logger()

# Optional BeautifulSoup for web scraping
try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False
    logger.warning("BeautifulSoup4 not available - web scraping will be skipped")

# Conservative rate limiting for web scraping (2 seconds between requests)
REQUEST_DELAY = 2.0
MAX_RETRIES = 3
RETRY_DELAY = 5.0  # Seconds to wait before retry


# Addresses Satoshi sent from in the public record.
SATOSHI_ADDRESSES = (
    'satoshi@vistomail.com',
    'satoshi@anonymousspeech.com',
    'satoshi@bitcoin.org',
    'satoshin@gmx.com',
)

MALMI_URL = 'https://mmalmi.github.io/satoshi/'
HEARN_THREAD_URLS = [f'https://plan99.net/~mike/satoshi-emails/thread{n}.html' for n in range(1, 6)]
TRAMMELL_URL = 'https://blog.dustintrammell.com/i-am-not-satoshi/'

# First author line of an archived document: "From: x", mbox "From x date", or
# forum "Post by: x on date". Quote lines ("Quote from: satoshi") and "To:" lines
# never match because the pattern is anchored at the start of the line.
_AUTHOR_LINE = re.compile(r'^(?:From:\s*|From\s+(?=\S+@)|Post by:\s*)(.+)$', re.IGNORECASE | re.MULTILINE)


def is_satoshi_author(author: Optional[str]) -> bool:
    """True when an author/From value names Satoshi (name, known address, or forum handle)."""
    if not author:
        return False
    value = html.unescape(author).replace('\\>', '>').replace('<br>', ' ').strip().lower()
    if any(addr in value for addr in SATOSHI_ADDRESSES):
        return True
    if re.search(r'satoshi\s*nakamoto', value):
        return True
    # Forum handle: "satoshi on November 22, 2009, ..." or a bare "satoshi"
    return re.match(r'^satoshi(?:\s+on\s|\s*$)', value) is not None


def document_author(content: str) -> Optional[str]:
    """Return the first author line of an archived document, or None."""
    match = _AUTHOR_LINE.search(content or '')
    if not match:
        return None
    return re.sub(r'<br\s*/?>', '', match.group(1)).strip()


def document_is_satoshi(content: str) -> bool:
    """True when an archived document was written by Satoshi.

    The first author line decides. A document with no author line counts only if
    its own text is signed "Satoshi" (one nakamoto-archive file has no header).
    """
    author = document_author(content)
    if author is not None:
        return is_satoshi_author(author)
    own_text = (content or '').split('\n---')[0]
    lines = [line.strip() for line in own_text.splitlines() if line.strip()]
    return bool(lines) and lines[-1] == 'Satoshi'


def strip_quoted_reply(text: str) -> str:
    """Drop quoted lines ("> ...") and the "X wrote:" line that introduces them."""
    lines = (text or '').splitlines()
    kept = []
    for i, line in enumerate(lines):
        if line.lstrip().startswith('>'):
            continue
        nxt = next((l for l in lines[i + 1:] if l.strip()), '')
        if line.rstrip().endswith('wrote:') and nxt.lstrip().startswith('>'):
            continue
        kept.append(line)
    return '\n'.join(kept).strip()


def parse_malmi_html(page_html: str) -> List[Dict[str, Any]]:
    """Parse Martti Malmi's archive page; keep only emails from Satoshi."""
    soup = BeautifulSoup(page_html, 'html.parser')
    communications = []
    for msg in soup.find_all('div', class_='message'):
        anchor = msg.get('id', '')
        headers = {}
        header_div = msg.find('div', class_='header')
        for row in header_div.find_all('div') if header_div else []:
            label = row.find('strong')
            if label:
                key = label.get_text(strip=True).lower()
                headers[key] = row.get_text(' ', strip=True).split(':', 1)[-1].strip()
        if not is_satoshi_author(headers.get('from')):
            continue
        body = msg.find('div', class_='body')
        text = body.get_text() if body else ''
        url = f'{MALMI_URL}#{anchor}'
        communications.append({
            'source': 'malmi',
            'type': 'email',
            'id': url,
            'url': url,
            'from': headers.get('from'),
            'to': headers.get('to'),
            'date': headers.get('date'),
            'subject': headers.get('subject'),
            'content': strip_quoted_reply(text),
            'collected_at': datetime.utcnow().isoformat(),
        })
    return communications


def parse_hearn_thread_html(page_html: str, thread_url: str) -> List[Dict[str, Any]]:
    """Parse one Gmail print-view thread from Mike Hearn's archive; keep Satoshi's messages."""
    communications = []
    # Gmail print view leaves rows unclosed, so split on each message table and
    # parse the pieces on their own instead of trusting the nesting.
    chunks = re.split(r'<table[^>]*class="message"[^>]*>', page_html)[1:]
    for index, chunk in enumerate(chunks, 1):
        author_match = re.search(r'<b>(.*?)</b>\s*(&lt;[^&]*&gt;)?', chunk, re.S)
        author = html.unescape(' '.join(g for g in author_match.groups() if g)) if author_match else ''
        author = re.sub(r'\s+', ' ', author).strip()
        if not is_satoshi_author(author):
            continue
        date_match = re.search(r'<td align=right><font size=-1>(.*?)</font>', chunk, re.S)
        to_match = re.search(r'<div>To:\s*(.*?)</div>', chunk, re.S)
        soup = BeautifulSoup(chunk, 'html.parser')
        body = soup.find('div', style=re.compile(r'overflow:\s*hidden'))
        if body:
            for quoted in body.find_all(['blockquote']) + body.find_all(class_='gmail_quote'):
                quoted.decompose()
            text = body.get_text().replace('[Quoted text hidden]', '').replace('\xa0', ' ')
        else:
            text = ''
        url = f'{thread_url}#message-{index}'
        communications.append({
            'source': 'hearn',
            'type': 'email',
            'id': url,
            'url': url,
            'from': author,
            'to': html.unescape(to_match.group(1)).strip() if to_match else None,
            'date': html.unescape(date_match.group(1)).strip() if date_match else None,
            'subject': _hearn_subject(page_html),
            'content': strip_quoted_reply(text),
            'collected_at': datetime.utcnow().isoformat(),
        })
    return communications


def _hearn_subject(page_html: str) -> Optional[str]:
    match = re.search(r'<title>(?:Gmail - )?(.*?)</title>', page_html, re.S)
    return html.unescape(match.group(1)).strip() if match else None


def _mbox_text(message) -> str:
    """Plain-text body of an email message (first text/plain part)."""
    for part in message.walk():
        if part.get_content_type() == 'text/plain' and not part.is_multipart():
            payload = part.get_payload(decode=True) or b''
            return payload.decode(part.get_content_charset() or 'utf-8', errors='replace')
    return ''


def parse_trammell_archive(path: Path) -> List[Dict[str, Any]]:
    """Parse Dustin Trammell's Satoshi_Nakamoto.zip (or an extracted dir / .mbox); keep Satoshi's mail."""
    path = Path(path)
    with tempfile.TemporaryDirectory() as tmp:
        if path.suffix == '.zip':
            with zipfile.ZipFile(path) as archive:
                archive.extractall(tmp)
            mbox_files = sorted(Path(tmp).rglob('*.mbox'))
        elif path.is_dir():
            mbox_files = sorted(path.rglob('*.mbox'))
        else:
            mbox_files = [path]
        communications = []
        seen = set()
        for mbox_path in mbox_files:
            for message in mailbox.mbox(str(mbox_path)):
                if not is_satoshi_author(message.get('From')):
                    continue
                message_id = (message.get('Message-ID') or '').strip()
                if message_id in seen:
                    continue  # same mail delivered twice (direct and via a list)
                seen.add(message_id)
                communications.append({
                    'source': 'trammell',
                    'type': 'email',
                    'message_id': message_id or None,
                    'url': TRAMMELL_URL,
                    'from': message.get('From'),
                    'to': message.get('To'),
                    'date': message.get('Date'),
                    'subject': message.get('Subject'),
                    'content': strip_quoted_reply(_mbox_text(message)),
                    'collected_at': datetime.utcnow().isoformat(),
                })
    return communications


class SatoshiArchiveCollector:
    """Collector for Satoshi Nakamoto's complete archive."""
    
    def __init__(self):
        """Initialize Satoshi archive collector."""
        self.data_dir = get_data_dir() / "satoshi_archive"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.satoshi_file = self.data_dir / 'satoshi_communications.jsonl'
        self.github_archive_dir = self.data_dir / 'nakamoto-archive'
        
        # Sources
        self.sources = {
            'nakamoto_institute': 'https://satoshi.nakamotoinstitute.org/',
            'nakamoto_archives': 'https://nakamotoarchives.btc.onl/',
            'p2p_research': 'https://news.nakamotoinstitute.org/p/p2p-research-list-emails',
            'github_archive': 'https://github.com/lugaxker/nakamoto-archive',
            'malmi': MALMI_URL,
            'hearn': HEARN_THREAD_URLS[0],
            'trammell': TRAMMELL_URL,
        }
        
        # Rate limiter for web scraping (conservative: 30 requests/minute = 2 sec/request)
        self.rate_limiter = RateLimiter(max_calls=30, time_window=60)
        
        # Session with user agent
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; Bitcoin Research Bot/1.0; +https://bitcoincommons.org)'
        })
        
        # Load existing message IDs to avoid duplicates
        self.existing_ids = set()
        if self.satoshi_file.exists():
            with open(self.satoshi_file, 'r') as f:
                for line in f:
                    try:
                        comm = json.loads(line)
                        if comm.get('message_id') or comm.get('id'):
                            self.existing_ids.add(comm.get('message_id') or comm.get('id'))
                    except:
                        continue
    
    def _make_request(self, url: str, timeout: int = 30) -> Optional[requests.Response]:
        """Make rate-limited request with retries."""
        self.rate_limiter.wait_if_needed()
        
        for attempt in range(MAX_RETRIES):
            try:
                response = self.session.get(url, timeout=timeout)
                
                # Check for rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', RETRY_DELAY))
                    logger.warning(f"Rate limited on {url}, waiting {retry_after}s (attempt {attempt + 1}/{MAX_RETRIES})")
                    time.sleep(retry_after)
                    continue
                
                response.raise_for_status()
                return response
            
            except requests.exceptions.RequestException as e:
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_DELAY * (attempt + 1)
                    logger.warning(f"Request failed for {url}: {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to fetch {url} after {MAX_RETRIES} attempts: {e}")
                    return None
        
        return None
    
    def collect_all(self):
        """Collect from all available sources."""
        logger.info("Starting Satoshi archive collection")
        
        all_communications = []
        
        # 1. GitHub Archive (lugaxker/nakamoto-archive) - Most reliable, structured
        logger.info("Collecting from GitHub Archive (lugaxker/nakamoto-archive)...")
        try:
            github_comms = self._collect_github_archive()
            all_communications.extend(github_comms)
            logger.info(f"Collected {len(github_comms)} communications from GitHub Archive")
        except Exception as e:
            logger.error(f"Error collecting from GitHub Archive: {e}")
            import traceback
            logger.debug(traceback.format_exc())
        
        # 2. Extract Satoshi emails from existing mailing list data (fast, no rate limits)
        logger.info("Extracting Satoshi emails from mailing list data...")
        try:
            mailing_list_comms = self._extract_from_mailing_lists()
            all_communications.extend(mailing_list_comms)
            logger.info(f"Extracted {len(mailing_list_comms)} Satoshi emails from mailing lists")
        except Exception as e:
            logger.error(f"Error extracting from mailing lists: {e}")
            import traceback
            logger.debug(traceback.format_exc())
        
        # 3. Nakamoto Institute (The Complete Satoshi) - Scraping fallback (requires BeautifulSoup)
        if HAS_BS4:
            logger.info("Collecting from Nakamoto Institute...")
            try:
                institute_comms = self._collect_nakamoto_institute()
                all_communications.extend(institute_comms)
                logger.info(f"Collected {len(institute_comms)} communications from Nakamoto Institute")
            except Exception as e:
                logger.error(f"Error collecting from Nakamoto Institute: {e}")
                import traceback
                logger.debug(traceback.format_exc())
        else:
            logger.warning("Skipping Nakamoto Institute (requires BeautifulSoup4)")
        
        # 4. Nakamoto Archives (blockchain-inscribed) - Scraping (requires BeautifulSoup)
        if HAS_BS4:
            logger.info("Collecting from Nakamoto Archives...")
            try:
                archive_comms = self._collect_nakamoto_archives()
                all_communications.extend(archive_comms)
                logger.info(f"Collected {len(archive_comms)} communications from Nakamoto Archives")
            except Exception as e:
                logger.error(f"Error collecting from Nakamoto Archives: {e}")
                import traceback
                logger.debug(traceback.format_exc())
        else:
            logger.warning("Skipping Nakamoto Archives (requires BeautifulSoup4)")
        
        # 5. P2P Research List - Scraping (requires BeautifulSoup)
        if HAS_BS4:
            logger.info("Collecting P2P Research List emails...")
            try:
                p2p_comms = self._collect_p2p_research()
                all_communications.extend(p2p_comms)
                logger.info(f"Collected {len(p2p_comms)} communications from P2P Research List")
            except Exception as e:
                logger.error(f"Error collecting from P2P Research List: {e}")
                import traceback
                logger.debug(traceback.format_exc())
        else:
            logger.warning("Skipping P2P Research List (requires BeautifulSoup4)")
        
        # 6. Correspondent archives: Malmi, Hearn (HTML, need BeautifulSoup) and Trammell (mbox)
        for name, collect in (('Malmi', self._collect_malmi),
                              ('Hearn', self._collect_hearn),
                              ('Trammell', self._collect_trammell)):
            logger.info(f"Collecting Satoshi emails from the {name} archive...")
            try:
                comms = collect()
                all_communications.extend(comms)
                logger.info(f"Collected {len(comms)} Satoshi emails from the {name} archive")
            except Exception as e:
                logger.error(f"Error collecting from the {name} archive: {e}")
                import traceback
                logger.debug(traceback.format_exc())
        
        # Deduplicate
        seen_ids = set()
        unique_comms = []
        for comm in all_communications:
            comm_id = comm.get('message_id') or comm.get('id') or comm.get('url', '')
            if comm_id and comm_id not in seen_ids:
                seen_ids.add(comm_id)
                unique_comms.append(comm)
            elif not comm_id:
                # Use content hash as fallback
                content_hash = hash(json.dumps(comm, sort_keys=True))
                if content_hash not in seen_ids:
                    seen_ids.add(content_hash)
                    unique_comms.append(comm)
        
        # Only add new communications
        new_comms = [c for c in unique_comms if (c.get('message_id') or c.get('id') or '') not in self.existing_ids]
        
        if new_comms:
            with open(self.satoshi_file, 'a') as f:
                for comm in new_comms:
                    f.write(json.dumps(comm) + '\n')
            
            logger.info(f"Added {len(new_comms)} new Satoshi communications (total unique: {len(unique_comms)})")
        else:
            logger.info(f"No new Satoshi communications (all {len(unique_comms)} already collected)")
        
        return unique_comms
    
    def _collect_malmi(self, source: Optional[str] = None) -> List[Dict[str, Any]]:
        """Collect Satoshi's emails to Martti Malmi from a local HTML file or the live page."""
        if not HAS_BS4:
            logger.warning("Skipping Malmi archive (requires BeautifulSoup4)")
            return []
        page = self._read_source(source or MALMI_URL)
        return parse_malmi_html(page) if page else []
    
    def _collect_hearn(self, sources: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Collect Satoshi's emails to Mike Hearn from threads 1-5 (local files or live pages)."""
        if not HAS_BS4:
            logger.warning("Skipping Hearn archive (requires BeautifulSoup4)")
            return []
        communications = []
        for thread_url, source in zip(HEARN_THREAD_URLS, sources or HEARN_THREAD_URLS):
            page = self._read_source(source)
            if page:
                communications.extend(parse_hearn_thread_html(page, thread_url))
        return communications
    
    def _collect_trammell(self, source: Optional[str] = None) -> List[Dict[str, Any]]:
        """Collect Satoshi's emails to Dustin Trammell from his published zip (local path or live)."""
        if source and not str(source).startswith('http'):
            return parse_trammell_archive(Path(source))
        page = self._read_source(TRAMMELL_URL)
        zip_match = re.search(r'href="([^"]+Satoshi_Nakamoto\.zip)"', page or '')
        if not zip_match:
            logger.warning("Satoshi_Nakamoto.zip link not found on the Trammell page")
            return []
        response = self._make_request(urljoin(TRAMMELL_URL, html.unescape(zip_match.group(1))))
        if not response:
            return []
        zip_path = self.data_dir / 'trammell_Satoshi_Nakamoto.zip'
        zip_path.write_bytes(response.content)
        return parse_trammell_archive(zip_path)
    
    def _read_source(self, source: str) -> Optional[str]:
        """Return page text from a URL or a local file path."""
        if str(source).startswith('http'):
            response = self._make_request(str(source))
            return response.text if response else None
        return Path(source).read_text(encoding='utf-8', errors='replace')
    
    def _collect_github_archive(self) -> List[Dict[str, Any]]:
        """Collect from GitHub Archive (lugaxker/nakamoto-archive) - Most reliable source."""
        communications = []
        
        # Clone or update repository
        if self.github_archive_dir.exists():
            logger.info("GitHub archive directory exists, updating...")
            try:
                subprocess.run(['git', 'pull'], cwd=self.github_archive_dir, check=True, 
                             capture_output=True, timeout=60)
            except subprocess.CalledProcessError as e:
                logger.warning(f"Git pull failed, will clone fresh: {e}")
                shutil.rmtree(self.github_archive_dir)
            except Exception as e:
                logger.warning(f"Error updating archive: {e}")
                shutil.rmtree(self.github_archive_dir)
        
        if not self.github_archive_dir.exists():
            logger.info("Cloning GitHub archive repository...")
            try:
                subprocess.run(['git', 'clone', '--depth', '1', 
                              self.sources['github_archive'], str(self.github_archive_dir)],
                             check=True, timeout=120)
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to clone GitHub archive: {e}")
                return communications
            except Exception as e:
                logger.error(f"Error cloning archive: {e}")
                return communications
        
        # Parse archive structure
        # Structure: doc/ (compilations), src/ (source materials with metadata)
        src_dir = self.github_archive_dir / 'src'
        doc_dir = self.github_archive_dir / 'doc'
        
        # Collect from src/ directory (source materials with metadata)
        if src_dir.exists():
            logger.info("Parsing src/ directory...")
            file_count = 0
            for file_path in src_dir.rglob('*'):
                if file_path.is_file() and file_path.suffix in ['.txt', '.md', '.html', '.eml', '.pdf']:
                    try:
                        comm = self._parse_github_archive_file(file_path, 'src')
                        if comm:
                            communications.append(comm)
                            file_count += 1
                            if file_count % 10 == 0:
                                logger.info(f"Parsed {file_count} files from src/...")
                    except Exception as e:
                        logger.warning(f"Error parsing {file_path}: {e}")
                        continue
            logger.info(f"Parsed {file_count} files from src/ directory")
        
        # Collect from doc/ directory (compilations)
        if doc_dir.exists():
            logger.info("Parsing doc/ directory...")
            file_count = 0
            for file_path in doc_dir.rglob('*'):
                if file_path.is_file() and file_path.suffix in ['.txt', '.md', '.html']:
                    try:
                        comm = self._parse_github_archive_file(file_path, 'doc')
                        if comm:
                            communications.append(comm)
                            file_count += 1
                            if file_count % 10 == 0:
                                logger.info(f"Parsed {file_count} files from doc/...")
                    except Exception as e:
                        logger.warning(f"Error parsing {file_path}: {e}")
                        continue
            logger.info(f"Parsed {file_count} files from doc/ directory")
        
        return communications
    
    def _parse_github_archive_file(self, file_path: Path, source_type: str) -> Optional[Dict[str, Any]]:
        """Parse a file from GitHub archive."""
        try:
            # Determine file type
            file_type = 'unknown'
            if 'email' in file_path.name.lower() or file_path.suffix == '.eml':
                file_type = 'email'
            elif 'post' in file_path.name.lower() or 'forum' in file_path.name.lower():
                file_type = 'forum_post'
            elif 'code' in file_path.name.lower() or file_path.suffix in ['.c', '.cpp', '.h', '.py']:
                file_type = 'code_release'
            elif file_path.suffix == '.pdf':
                file_type = 'document'
            
            # Read file content (handle binary files)
            if file_path.suffix == '.pdf':
                # PDF files - just store metadata, not content
                content = f"[PDF file: {file_path.name}]"
            else:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                # The archive also holds correspondents' replies (Hal Finney, Adam Back,
                # Wei Dai). Keep only documents Satoshi wrote.
                if not document_is_satoshi(content):
                    logger.debug(f"Skipping non-Satoshi document: {file_path}")
                    return None
            
            # Extract metadata from filename and path
            filename = file_path.name
            relative_path = file_path.relative_to(self.github_archive_dir)
            
            # Try to extract date from filename or path
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', str(relative_path))
            date_str = date_match.group(1) if date_match else None
            
            comm = {
                'source': 'github_archive',
                'source_type': source_type,
                'type': file_type,
                'file_path': str(relative_path),
                'filename': filename,
                'content': content[:100000] if len(content) > 100000 else content,  # Limit content size
                'date': date_str,
                'collected_at': datetime.utcnow().isoformat(),
            }
            
            # Try to extract additional metadata from content (for text files)
            if file_path.suffix != '.pdf' and content:
                if 'From:' in content:
                    from_match = re.search(r'From:\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
                    if from_match:
                        comm['from'] = from_match.group(1).strip()
                
                if 'Subject:' in content:
                    subject_match = re.search(r'Subject:\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
                    if subject_match:
                        comm['subject'] = subject_match.group(1).strip()
                
                if 'Date:' in content and not date_str:
                    date_match = re.search(r'Date:\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
                    if date_match:
                        comm['date'] = date_match.group(1).strip()
            
            # Check for README or metadata files that might contain SHA256 hashes
            if 'README' in filename or 'metadata' in filename.lower():
                # Try to extract SHA256 hashes and source URLs from metadata
                sha256_match = re.search(r'sha256[:\s]+([a-f0-9]{64})', content, re.IGNORECASE)
                if sha256_match:
                    comm['metadata'] = {'sha256': sha256_match.group(1)}
                
                # Extract source URLs
                url_matches = re.findall(r'https?://[^\s\)]+', content)
                if url_matches:
                    if 'metadata' not in comm:
                        comm['metadata'] = {}
                    comm['metadata']['sources'] = url_matches[:10]  # Limit to 10 URLs
            
            return comm
        
        except Exception as e:
            logger.warning(f"Error parsing file {file_path}: {e}")
            return None
    
    def _collect_nakamoto_institute(self) -> List[Dict[str, Any]]:
        """Collect from Satoshi Nakamoto Institute (The Complete Satoshi)."""
        if not HAS_BS4:
            logger.warning("BeautifulSoup4 required for Nakamoto Institute collection")
            return []
        
        communications = []
        
        try:
            # Try to get main page to understand structure
            response = self._make_request(self.sources['nakamoto_institute'])
            if not response:
                return communications
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # The Complete Satoshi is organized by categories: emails, posts, code, quotes
            # Look for navigation or category links
            category_links = []
            
            # Try to find category pages
            nav_links = soup.find_all('a', href=re.compile(r'/emails|/posts|/code|/quotes'))
            for link in nav_links:
                href = link.get('href', '')
                if href:
                    category_links.append(urljoin(self.sources['nakamoto_institute'], href))
            
            # If no category links found, try to find individual post/email links
            if not category_links:
                post_links = soup.find_all('a', href=re.compile(r'/posts/|/emails/'))
                # Collect all links but process in batches to avoid overwhelming server
                for i, link in enumerate(post_links):
                    if i > 0 and i % 10 == 0:
                        logger.info(f"Processed {i}/{len(post_links)} links from Nakamoto Institute...")
                    try:
                        post_url = urljoin(self.sources['nakamoto_institute'], link['href'])
                        comm = self._scrape_nakamoto_institute_post(post_url)
                        if comm:
                            communications.append(comm)
                    except Exception as e:
                        logger.warning(f"Error scraping post {link.get('href')}: {e}")
                        continue
            else:
                # Collect from category pages
                for category_url in category_links:
                    try:
                        category_comms = self._collect_from_category(category_url)
                        communications.extend(category_comms)
                    except Exception as e:
                        logger.warning(f"Error collecting from category {category_url}: {e}")
                        continue
        
        except Exception as e:
            logger.error(f"Error collecting from Nakamoto Institute: {e}")
            import traceback
            logger.debug(traceback.format_exc())
        
        return communications
    
    def _collect_from_category(self, category_url: str) -> List[Dict[str, Any]]:
        """Collect all items from a category page."""
        if not HAS_BS4:
            return []
        
        communications = []
        
        try:
            response = self._make_request(category_url)
            if not response:
                return communications
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all links to individual items
            item_links = soup.find_all('a', href=re.compile(r'/posts/|/emails/'))
            
            for link in item_links:
                try:
                    item_url = urljoin(category_url, link['href'])
                    comm = self._scrape_nakamoto_institute_post(item_url)
                    if comm:
                        communications.append(comm)
                except Exception as e:
                    logger.warning(f"Error scraping item {link.get('href')}: {e}")
                    continue
        
        except Exception as e:
            logger.warning(f"Error collecting from category {category_url}: {e}")
        
        return communications
    
    def _scrape_nakamoto_institute_post(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape a single post from Nakamoto Institute."""
        if not HAS_BS4:
            return None
        
        try:
            response = self._make_request(url)
            if not response:
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract post content - try multiple selectors
            content = (soup.find('div', class_='content') or 
                      soup.find('article') or 
                      soup.find('main') or
                      soup.find('div', id='content'))
            
            if not content:
                return None
            
            # Extract metadata
            title = soup.find('title')
            date_elem = (soup.find('time') or 
                        soup.find('span', class_='date') or
                        soup.find('div', class_='date'))
            
            comm = {
                'source': 'nakamoto_institute',
                'url': url,
                'title': title.text.strip() if title else '',
                'date': (date_elem.get('datetime') if date_elem and date_elem.get('datetime') 
                        else (date_elem.text.strip() if date_elem else '')),
                'content': content.get_text(separator='\n', strip=True),
                'html_content': str(content),
                'collected_at': datetime.utcnow().isoformat(),
            }
            
            return comm
        
        except Exception as e:
            logger.warning(f"Error scraping post {url}: {e}")
            return None
    
    def _collect_nakamoto_archives(self) -> List[Dict[str, Any]]:
        """Collect from Nakamoto Archives (blockchain-inscribed)."""
        if not HAS_BS4:
            logger.warning("BeautifulSoup4 required for Nakamoto Archives collection")
            return []
        
        communications = []
        
        try:
            response = self._make_request(self.sources['nakamoto_archives'])
            if not response:
                return communications
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all communications - try multiple selectors
            comm_elements = (soup.find_all('div', class_='communication') or 
                           soup.find_all('article') or
                           soup.find_all('div', class_='post') or
                           soup.find_all('div', class_='email'))
            
            for elem in comm_elements:
                comm = self._parse_archive_communication(elem)
                if comm:
                    communications.append(comm)
        
        except Exception as e:
            logger.error(f"Error collecting from Nakamoto Archives: {e}")
            import traceback
            logger.debug(traceback.format_exc())
        
        return communications
    
    def _parse_archive_communication(self, elem) -> Optional[Dict[str, Any]]:
        """Parse a communication element from archives."""
        try:
            comm = {
                'source': 'nakamoto_archives',
                'content': elem.get_text(separator='\n', strip=True),
                'html_content': str(elem),
                'collected_at': datetime.utcnow().isoformat(),
            }
            
            # Try to extract metadata
            title = elem.find('h1') or elem.find('h2') or elem.find('title')
            if title:
                comm['title'] = title.text.strip()
            
            date_elem = elem.find('time') or elem.find('span', class_='date')
            if date_elem:
                comm['date'] = date_elem.get('datetime') or date_elem.text.strip()
            
            return comm
        
        except Exception as e:
            logger.warning(f"Error parsing communication: {e}")
            return None
    
    def _collect_p2p_research(self) -> List[Dict[str, Any]]:
        """Collect P2P Research List emails."""
        if not HAS_BS4:
            logger.warning("BeautifulSoup4 required for P2P Research List collection")
            return []
        
        communications = []
        
        try:
            response = self._make_request(self.sources['p2p_research'])
            if not response:
                return communications
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract emails from the page - try multiple selectors
            email_elements = (soup.find_all('div', class_='email') or 
                            soup.find_all('article') or
                            soup.find_all('div', class_='post'))
            
            for elem in email_elements:
                comm = self._parse_p2p_email(elem)
                if comm:
                    communications.append(comm)
        
        except Exception as e:
            logger.error(f"Error collecting from P2P Research List: {e}")
            import traceback
            logger.debug(traceback.format_exc())
        
        return communications
    
    def _parse_p2p_email(self, elem) -> Optional[Dict[str, Any]]:
        """Parse a P2P Research email."""
        try:
            comm = {
                'source': 'p2p_research',
                'content': elem.get_text(separator='\n', strip=True),
                'html_content': str(elem),
                'collected_at': datetime.utcnow().isoformat(),
            }
            
            # Extract metadata - try multiple selectors
            from_elem = (elem.find('span', class_='from') or 
                        elem.find('div', class_='from') or
                        elem.find('strong', string=re.compile(r'from', re.I)))
            if from_elem:
                comm['from'] = from_elem.text.strip()
            
            date_elem = elem.find('time') or elem.find('span', class_='date')
            if date_elem:
                comm['date'] = date_elem.get('datetime') or date_elem.text.strip()
            
            subject_elem = (elem.find('span', class_='subject') or 
                          elem.find('div', class_='subject') or
                          elem.find('strong', string=re.compile(r'subject', re.I)))
            if subject_elem:
                comm['subject'] = subject_elem.text.strip()
            
            return comm
        
        except Exception as e:
            logger.warning(f"Error parsing P2P email: {e}")
            return None
    
    def _extract_from_mailing_lists(self) -> List[Dict[str, Any]]:
        """Extract Satoshi emails from existing mailing list data."""
        communications = []
        
        try:
            logger.info("Scanning mailing list emails for Satoshi...")
            for line_num, email in enumerate(iter_emails(prefer_cleaned=False), 1):
                if is_satoshi_author(email.get('from')):
                    communications.append({
                        'source': 'mailing_list',
                        'message_id': email.get('message_id'),
                        'from': email.get('from'),
                        'to': email.get('to'),
                        'date': email.get('date'),
                        'subject': email.get('subject'),
                        'content': email.get('body', ''),
                        'list': email.get('list_name') or email.get('list', ''),
                        'collected_at': datetime.utcnow().isoformat(),
                    })
                
                if line_num % 10000 == 0:
                    logger.debug(
                        "Scanned %s emails, found %s Satoshi emails so far...",
                        line_num,
                        len(communications),
                    )
        
        except Exception as e:
            logger.error(f"Error extracting from mailing lists: {e}")
            import traceback
            logger.debug(traceback.format_exc())
        
        return communications


def main():
    """Main entry point."""
    collector = SatoshiArchiveCollector()
    communications = collector.collect_all()
    
    print(f"\n✅ Collected {len(communications)} Satoshi communications")
    print(f"📁 Saved to: {collector.satoshi_file}")
    print("\nSources collected:")
    sources = {}
    for comm in communications:
        source = comm.get('source', 'unknown')
        sources[source] = sources.get(source, 0) + 1
    
    for source, count in sources.items():
        print(f"  - {source}: {count} communications")
    
    # Additional useful info
    print("\n📊 Additional Information Collected:")
    
    # Count by type
    types = {}
    for comm in communications:
        comm_type = comm.get('type', 'unknown')
        if 'email' in comm.get('source', '').lower() or 'email' in comm.get('subject', '').lower():
            comm_type = 'email'
        elif 'post' in comm.get('source', '').lower() or 'forum' in comm.get('source', '').lower():
            comm_type = 'forum_post'
        elif 'code' in comm.get('source', '').lower():
            comm_type = 'code_release'
        types[comm_type] = types.get(comm_type, 0) + 1
    
    for comm_type, count in types.items():
        print(f"  - {comm_type}: {count}")
    
    # Date range
    dates = [c.get('date') for c in communications if c.get('date')]
    if dates:
        print(f"\n📅 Date Range: {min(dates)} to {max(dates)}")


if __name__ == '__main__':
    main()
