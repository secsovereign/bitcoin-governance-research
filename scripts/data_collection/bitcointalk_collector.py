#!/usr/bin/env python3
"""
Bitcoin Talk Forum collector for Development & Technical Discussion board.

Collects governance-related threads from Bitcoin Talk Forum.
Uses very conservative rate limiting to avoid triggering security measures.
"""

import sys
import json
import time
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config import config
from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir

logger = setup_logger()

# Very conservative rate limiting: 1 request per 4 seconds (start slow)
REQUEST_DELAY = 4.0
MAX_THREADS_PER_PAGE = 5  # Start with very few threads per page
MAX_PAGES = 2  # Start with just 2 pages to test
MAX_POSTS_PER_THREAD = 20  # Limit posts per thread


class BitcoinTalkCollector:
    """Collector for Bitcoin Talk Forum."""
    
    def __init__(self):
        """Initialize Bitcoin Talk collector."""
        # Development & Technical Discussion board
        self.base_url = "https://bitcointalk.org/index.php?board=6.0"
        self.data_dir = get_data_dir() / "bitcointalk"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.threads_file = self.data_dir / 'threads.jsonl'
        
        # Session with user agent
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; Bitcoin Research Bot/1.0; +https://bitcoincommons.org)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
    
    def collect(self):
        """Collect threads from Bitcoin Talk Forum."""
        logger.info("Starting Bitcoin Talk Forum collection")
        logger.info("Using very conservative rate limiting (1 request per 3 seconds)")
        logger.info(f"Limiting to {MAX_PAGES} pages and {MAX_THREADS_PER_PAGE} threads per page")
        
        try:
            # Check if forum is accessible
            logger.info(f"Checking accessibility: {self.base_url}")
            time.sleep(REQUEST_DELAY)
            
            response = self.session.get(self.base_url, timeout=30)
            
            if response.status_code != 200:
                logger.warning(f"Bitcoin Talk Forum returned status {response.status_code}")
                logger.info("Forum may not be accessible or may require different approach")
                return
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find thread links
            threads = []
            page_num = 0
            
            # Collect threads from first few pages
            while page_num < MAX_PAGES:
                logger.info(f"Processing page {page_num + 1}/{MAX_PAGES}")
                
                page_threads = self._collect_threads_from_page(soup)
                threads.extend(page_threads[:MAX_THREADS_PER_PAGE])
                
                logger.info(f"Found {len(page_threads)} threads on this page (collecting {min(MAX_THREADS_PER_PAGE, len(page_threads))})")
                
                # Find next page link
                next_page_url = self._find_next_page(soup)
                if not next_page_url or page_num >= MAX_PAGES - 1:
                    break
                
                # Conservative delay before next page
                time.sleep(REQUEST_DELAY * 2)  # 6 seconds between pages
                
                response = self.session.get(next_page_url, timeout=30)
                if response.status_code != 200:
                    break
                
                soup = BeautifulSoup(response.text, 'html.parser')
                page_num += 1
            
            # Collect posts from threads
            all_posts = []
            for i, thread in enumerate(threads):
                logger.info(f"Processing thread {i+1}/{len(threads)}: {thread.get('title', 'Unknown')[:50]}")
                
                try:
                    posts = self._collect_thread_posts(thread['url'])
                    all_posts.extend(posts)
                    
                    # Conservative delay between threads
                    if i < len(threads) - 1:
                        time.sleep(REQUEST_DELAY * 2)  # 6 seconds between threads
                        
                except Exception as e:
                    logger.warning(f"Error processing thread {thread.get('url')}: {e}")
                    continue
            
            # Save posts
            if all_posts:
                with open(self.threads_file, 'w') as f:
                    for post in all_posts:
                        f.write(json.dumps(post) + '\n')
                
                logger.info(f"Collected {len(all_posts)} posts from {len(threads)} threads")
            else:
                logger.info("No posts collected from Bitcoin Talk Forum")
        
        except Exception as e:
            logger.error(f"Error collecting from Bitcoin Talk Forum: {e}")
            import traceback
            logger.debug(traceback.format_exc())
    
    def _collect_threads_from_page(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Collect thread links from a forum page."""
        threads = []
        
        try:
            # Bitcoin Talk uses table-based layout
            # Thread links are in table rows, typically in the second column
            # Look for links with topic= parameter
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                # Thread links contain 'topic=' and are on board 6
                if 'topic=' in href and ('board=6' in href or 'board=6.0' in href or self.base_url.split('board=')[-1].split('.')[0] in href):
                    full_url = urljoin(self.base_url, href)
                    title = link.get_text().strip()
                    
                    # Filter out non-thread links (like "Last post", page numbers, etc.)
                    if title and len(title) > 5 and title not in ['Last post', 'Re:', 'New', 'Pages']:
                        # Avoid duplicates
                        if full_url not in [t['url'] for t in threads]:
                            threads.append({
                                'title': title,
                                'url': full_url
                            })
        
        except Exception as e:
            logger.debug(f"Error collecting threads from page: {e}")
        
        return threads
    
    def _find_next_page(self, soup: BeautifulSoup) -> Optional[str]:
        """Find the next page URL."""
        try:
            # Look for "Next" or page number links
            for link in soup.find_all('a', href=True):
                text = link.get_text().strip().lower()
                if 'next' in text or text.isdigit():
                    href = link.get('href', '')
                    if href:
                        return urljoin(self.base_url, href)
        except:
            pass
        
        return None
    
    def _collect_thread_posts(self, thread_url: str) -> List[Dict[str, Any]]:
        """Collect posts from a single thread."""
        posts = []
        
        try:
            time.sleep(REQUEST_DELAY)
            
            response = self.session.get(thread_url, timeout=30, allow_redirects=False)
            
            # Check if we got redirected to login
            if response.status_code in [301, 302, 303, 307, 308]:
                location = response.headers.get('Location', '')
                if 'login' in location.lower() or 'action=login' in location:
                    logger.debug(f"Thread requires login: {thread_url}")
                    return posts
            
            if response.status_code != 200:
                logger.debug(f"Thread returned {response.status_code}: {thread_url}")
                return posts
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check if we're on a login page
            if soup.title and 'login' in soup.title.string.lower():
                logger.debug(f"Thread redirected to login page: {thread_url}")
                return posts
            
            # Bitcoin Talk uses table-based layout for posts
            # Posts are typically in <td> elements with specific attributes
            # Look for post content in various possible structures
            post_tables = soup.find_all('table', class_=re.compile(r'post|message|bordercolor', re.I))
            
            # Also try looking for posts in divs with id containing "msg"
            post_divs = soup.find_all('div', id=re.compile(r'msg|post', re.I))
            
            # Try table rows with posts
            post_rows = soup.find_all('tr', class_=re.compile(r'windowbg|catbg', re.I))
            
            all_post_containers = list(post_tables) + list(post_divs) + list(post_rows)
            
            logger.debug(f"Found {len(all_post_containers)} potential post containers")
            
            for container in all_post_containers[:MAX_POSTS_PER_THREAD]:
                try:
                    # Try to extract author - could be in various places
                    author = ''
                    author_links = container.find_all('a', href=re.compile(r'action=profile'))
                    if author_links:
                        author = author_links[0].get_text().strip()
                    else:
                        # Try other author patterns
                        author_elem = container.find('b') or container.find('strong')
                        if author_elem:
                            author = author_elem.get_text().strip()
                    
                    # Try to extract content
                    content = ''
                    # Look for post content in various possible locations
                    content_divs = container.find_all('div', class_=re.compile(r'post|content|message', re.I))
                    if content_divs:
                        content = content_divs[0].get_text().strip()
                    else:
                        # Try getting all text from container
                        content = container.get_text().strip()
                    
                    # Try to extract date
                    date_str = ''
                    date_elem = container.find('div', class_=re.compile(r'date|time|smalltext', re.I))
                    if date_elem:
                        date_str = date_elem.get_text().strip()
                    
                    # Only add if we have meaningful content
                    if author and content and len(content) > 50:  # At least 50 chars of content
                        posts.append({
                            'forum': 'bitcointalk',
                            'board': 'Development & Technical Discussion',
                            'author': author,
                            'content': content[:5000],  # Limit content length
                            'date': date_str,
                            'thread_url': thread_url,
                            'source': 'bitcointalk'
                        })
                        logger.debug(f"Extracted post from {thread_url}: author={author[:20]}, content_len={len(content)}")
                
                except Exception as e:
                    logger.debug(f"Error parsing post container: {e}")
                    continue
            
            if not posts:
                logger.debug(f"No posts extracted from {thread_url} - may require authentication or have different structure")
        
        except Exception as e:
            logger.debug(f"Error collecting thread posts {thread_url}: {e}")
        
        return posts


def main():
    """Main entry point."""
    collector = BitcoinTalkCollector()
    collector.collect()
    logger.info("Bitcoin Talk Forum collection complete")


if __name__ == '__main__':
    main()

