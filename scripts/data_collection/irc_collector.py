#!/usr/bin/env python3
"""
IRC chat data collector for Bitcoin development channels.

Collects IRC logs from Bitcoin development channels:
- #bitcoin-core-dev (primary development channel)
- #bitcoin-dev (general development discussion)
- #bitcoin-core (technical discussions)

Sources:
- https://bitcoin-irc.chaincode.com/bitcoin-core-dev/
- https://bitcoin-irc.chaincode.com/bitcoin-dev/
- https://bitcoin-irc.chaincode.com/bitcoin-core/
- Alternative: https://freenode.logbot.info/bitcoin-core-dev/
"""

import sys
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config import config
from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir

logger = setup_logger()


class IRCCollector:
    """Collector for IRC chat logs."""
    
    def __init__(self):
        """Initialize IRC collector."""
        self.base_urls = {
            'bitcoin-core-dev': 'https://bitcoin-irc.chaincode.com/bitcoin-core-dev/',
            'bitcoin-dev': 'https://bitcoin-irc.chaincode.com/bitcoin-dev/',
            'bitcoin-core': 'https://bitcoin-irc.chaincode.com/bitcoin-core/',
        }
        
        # Output paths
        data_dir = get_data_dir()
        self.output_dir = data_dir / 'irc'
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir = self.output_dir / 'raw'
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        
        self.messages_file = self.output_dir / 'messages.jsonl'
    
    def collect_all_channels(self):
        """Collect IRC logs from all channels."""
        logger.info("Starting IRC log collection")
        
        for channel_name, base_url in self.base_urls.items():
            logger.info(f"Collecting from {channel_name}...")
            self._collect_channel(channel_name, base_url)
        
        logger.info("IRC log collection complete")
    
    def _collect_channel(self, channel_name: str, base_url: str):
        """Collect logs from a specific IRC channel."""
        try:
            # Get list of log files
            log_files = self._get_log_files(base_url)
            logger.info(f"Found {len(log_files)} log files for {channel_name}")
            
            all_messages = []
            
            for log_url in log_files:
                logger.info(f"  Processing {Path(log_url).name}...")
                messages = self._download_and_parse_log(channel_name, log_url)
                all_messages.extend(messages)
                
                # Write incrementally
                with open(self.messages_file, 'a') as f:
                    for msg in messages:
                        f.write(json.dumps(msg) + '\n')
            
            logger.info(f"Collected {len(all_messages)} messages from {channel_name}")
            
        except Exception as e:
            logger.error(f"Error collecting {channel_name}: {e}")
    
    def _get_log_files(self, base_url: str) -> List[str]:
        """Get list of log file URLs from IRC archive."""
        try:
            response = requests.get(base_url, timeout=30, allow_redirects=True)
            response.raise_for_status()
            
            log_files = []
            
            # The chaincode.com archive appears to be a searchable web interface
            # It may not have direct file downloads. Let's try multiple approaches:
            
            # Method 1: Look for date-based URLs (YYYY-MM-DD format)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for links with date patterns
            date_pattern = re.compile(r'\d{4}-\d{2}-\d{2}')
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                text = link.get_text()
                
                # Check if href or text contains a date
                if date_pattern.search(href) or date_pattern.search(text):
                    full_url = urljoin(response.url, href)
                    # These might be daily log pages, not files
                    # But we can try to access them
                    log_files.append(full_url)
            
            # Method 2: Generate date-based URLs for historical dates
            # The archive seems to use format: /bitcoin-core-dev/YYYY-MM-DD
            # Go back to 2009 (Bitcoin started in 2009) - that's ~15+ years of logs
            if len(log_files) < 100:
                logger.info("Trying date-based URL generation for IRC logs (going back to 2009)")
                from datetime import datetime, timedelta
                
                # Go back to 2009-01-01 (Bitcoin's early days)
                end_date = datetime.now()
                start_date = datetime(2009, 1, 1)
                
                logger.info(f"Generating IRC log URLs from {start_date.date()} to {end_date.date()}")
                current_date = start_date
                checked = 0
                found = 0
                
                while current_date <= end_date:
                    date_str = current_date.strftime('%Y-%m-%d')
                    # Try the date as a path
                    url = urljoin(response.url, date_str)
                    try:
                        test_response = requests.head(url, timeout=3, allow_redirects=True)
                        if test_response.status_code == 200:
                            log_files.append(url)
                            found += 1
                    except:
                        pass
                    
                    current_date += timedelta(days=1)
                    checked += 1
                    
                    # Progress logging every 1000 days checked
                    if checked % 1000 == 0:
                        logger.info(f"Checked {checked} dates, found {found} valid logs...")
                    
                    # No limit - we want all historical data
            
            # Remove duplicates and sort
            log_files = sorted(list(set(log_files)), reverse=True)
            logger.info(f"Found {len(log_files)} log URLs")
            return log_files
            
        except Exception as e:
            logger.error(f"Error getting log files from {base_url}: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return []
    
    def _download_and_parse_log(self, channel_name: str, log_url: str) -> List[Dict[str, Any]]:
        """Download and parse an IRC log file or page."""
        try:
            response = requests.get(log_url, timeout=60, allow_redirects=True)
            response.raise_for_status()
            
            # Save raw file
            # Extract date from URL for filename
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', log_url)
            if date_match:
                filename = f"{channel_name}_{date_match.group(1)}.html"
            else:
                filename = f"{channel_name}_{Path(log_url).name}"
            
            raw_file = self.raw_dir / filename
            raw_file.write_bytes(response.content)
            
            # Parse log - may be HTML page or plain text
            messages = self._parse_irc_log(channel_name, response.text, log_url)
            
            return messages
            
        except Exception as e:
            logger.error(f"Error processing log {log_url}: {e}")
            return []
    
    def _parse_irc_log(self, channel_name: str, log_text: str, source_url: str) -> List[Dict[str, Any]]:
        """Parse IRC log text into structured messages."""
        messages = []
        
        # Try to extract date from URL
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', source_url)
        current_date = date_match.group(1) if date_match else None
        
        # Check if this is HTML (chaincode.com format) or plain text
        if '<html' in log_text.lower() or '<body' in log_text.lower():
            # Parse HTML format
            messages = self._parse_irc_html(channel_name, log_text, current_date)
        else:
            # Parse plain text format
            lines = log_text.split('\n')
            for line in lines:
                if not line.strip():
                    continue
                
                message = self._parse_irc_line(channel_name, line, current_date)
                if message:
                    messages.append(message)
        
        return messages
    
    def _parse_irc_html(self, channel_name: str, html_text: str, default_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Parse IRC log from HTML format (chaincode.com style)."""
        messages = []
        
        try:
            soup = BeautifulSoup(html_text, 'html.parser')
            
            # Chaincode.com format: messages are in a div with class "log-messages"
            # Each message is a div with data-timestamp attribute
            log_container = soup.find('div', class_='log-messages')
            
            if log_container:
                # Get all message divs (direct children of log-messages)
                message_divs = log_container.find_all('div', recursive=False)
                
                for div in message_divs:
                    # Skip info/topic messages (they're not regular chat)
                    classes = div.get('class', [])
                    if 'info' in classes or 'op-topic' in classes:
                        continue
                    
                    # Extract timestamp from data-timestamp attribute or time element
                    timestamp = None
                    timestamp_attr = div.get('data-timestamp')
                    if timestamp_attr:
                        # Convert Unix timestamp to ISO format
                        try:
                            from datetime import datetime
                            dt = datetime.fromtimestamp(int(timestamp_attr), tz=None)
                            timestamp = dt.strftime('%Y-%m-%dT%H:%M:%S+00:00')
                        except:
                            pass
                    
                    # Try time element as fallback
                    if not timestamp:
                        time_elem = div.find('time')
                        if time_elem:
                            timestamp_attr = time_elem.get('timestamp')
                            if timestamp_attr:
                                timestamp = timestamp_attr
                    
                    # Extract nickname - look for spans/links with nick classes or patterns
                    nickname = None
                    nick_elem = div.find(['span', 'a'], class_=re.compile(r'nick|user|author', re.I))
                    if nick_elem:
                        nickname = nick_elem.get_text().strip()
                    else:
                        # Try to extract from text pattern: <nickname> or nickname: message
                        text = div.get_text()
                        nick_match = re.search(r'<([^>]+)>', text)
                        if nick_match:
                            nickname = nick_match.group(1)
                        else:
                            # Try pattern: nickname: message
                            nick_match = re.search(r'^(\w+):\s+', text)
                            if nick_match:
                                nickname = nick_match.group(1)
                    
                    # Extract message text
                    text = div.get_text()
                    # Remove timestamp and nickname from text if present
                    if timestamp:
                        # Remove time element text
                        for time_elem in div.find_all('time'):
                            time_elem.decompose()
                    if nickname:
                        # Remove nickname from text
                        text = re.sub(rf'<{re.escape(nickname)}>', '', text)
                        text = re.sub(rf'^{re.escape(nickname)}:\s*', '', text)
                    
                    message_text = text.strip()
                    
                    # Only create message if we have essential info
                    if timestamp and nickname and message_text:
                        messages.append({
                            'channel': channel_name,
                            'timestamp': timestamp,
                            'nickname': nickname,
                            'message': message_text,
                            'source': 'irc_html'
                        })
            
            # Fallback: if no structured messages found, try line-by-line parsing
            if not messages:
                log_container = soup.find('div', class_=re.compile(r'log', re.I))
                if log_container:
                    all_text = log_container.get_text()
                else:
                    all_text = soup.get_text()
                
                lines = all_text.split('\n')
                for line in lines:
                    if not line.strip():
                        continue
                    message = self._parse_irc_line(channel_name, line, default_date)
                    if message:
                        messages.append(message)
        
        except Exception as e:
            logger.debug(f"Error parsing HTML IRC log: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            # Fallback: extract all text and parse line by line
            try:
                soup = BeautifulSoup(html_text, 'html.parser')
                all_text = soup.get_text()
                lines = all_text.split('\n')
                for line in lines:
                    if not line.strip():
                        continue
                    message = self._parse_irc_line(channel_name, line, default_date)
                    if message:
                        messages.append(message)
            except:
                pass
        
        return messages
    
    def _parse_irc_line(self, channel_name: str, line: str, default_date: Optional[str] = None, 
                       timestamp_override: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Parse a single IRC log line."""
        # If timestamp override is provided, use it
        if timestamp_override:
            # Try to extract nickname and message from line
            nickname_match = re.search(r'<([^>]+)>', line)
            if nickname_match:
                nickname = nickname_match.group(1)
                # Extract message after nickname
                message_match = re.search(r'<[^>]+>\s+(.+)', line)
                message = message_match.group(1) if message_match else line
                return {
                    'channel': channel_name,
                    'timestamp': timestamp_override,
                    'nickname': nickname.strip(),
                    'message': message.strip(),
                }
        
        # Pattern 1: [YYYY-MM-DD HH:MM:SS] <nickname> message
        pattern1 = r'\[(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})\]\s+<([^>]+)>\s+(.+)'
        match = re.match(pattern1, line)
        if match:
            date_str, time_str, nickname, message = match.groups()
            timestamp = f"{date_str}T{time_str}+00:00"
            return {
                'channel': channel_name,
                'timestamp': timestamp,
                'nickname': nickname.strip(),
                'message': message.strip(),
                'type': 'message',
            }
        
        # Pattern 2: YYYY-MM-DD HH:MM:SS <nickname> message
        pattern2 = r'(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})\s+<([^>]+)>\s+(.+)'
        match = re.match(pattern2, line)
        if match:
            date_str, time_str, nickname, message = match.groups()
            timestamp = f"{date_str}T{time_str}+00:00"
            return {
                'channel': channel_name,
                'timestamp': timestamp,
                'nickname': nickname.strip(),
                'message': message.strip(),
                'type': 'message',
            }
        
        # Pattern 3: [HH:MM:SS] <nickname> message (use default_date)
        pattern3 = r'\[(\d{2}:\d{2}:\d{2})\]\s+<([^>]+)>\s+(.+)'
        match = re.match(pattern3, line)
        if match:
            if default_date:
                time_str, nickname, message = match.groups()
                timestamp = f"{default_date}T{time_str}+00:00"
                return {
                    'channel': channel_name,
                    'timestamp': timestamp,
                    'nickname': nickname.strip(),
                    'message': message.strip(),
                    'type': 'message',
                }
        
        # Pattern 4: Action messages (* nickname action)
        pattern4 = r'\*\s+([^\s]+)\s+(.+)'
        match = re.match(pattern4, line)
        if match:
            nickname, action = match.groups()
            return {
                'channel': channel_name,
                'timestamp': datetime.now().isoformat() if not default_date else f"{default_date}T00:00:00+00:00",
                'nickname': nickname.strip(),
                'message': action.strip(),
                'type': 'action',
            }
        
        return None


def main():
    """Main entry point."""
    collector = IRCCollector()
    collector.collect_all_channels()


if __name__ == '__main__':
    main()

