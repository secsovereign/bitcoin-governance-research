#!/usr/bin/env python3
"""
Bitcoin Core release notes collector.

Collects release notes and announcements from GitHub releases and
the Bitcoin Core website.
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

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config import config
from src.utils.logger import setup_logger
from src.utils.rate_limiter import RateLimiter
from src.utils.paths import get_data_dir

try:
    from github import Github
except ImportError:
    print("Error: PyGithub package not installed.")
    print("Run: pip install PyGithub")
    sys.exit(1)

logger = setup_logger()


class ReleaseNotesCollector:
    """Collector for Bitcoin Core release notes."""
    
    def __init__(self):
        """Initialize release notes collector."""
        self.token = config.get('data_collection.github.token') or os.getenv('GITHUB_TOKEN')
        self.repo_owner = config.get('data_collection.github.repository.owner', 'bitcoin')
        self.repo_name = config.get('data_collection.github.repository.name', 'bitcoin')
        self.data_dir = get_data_dir() / "releases"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize GitHub API client
        if self.token:
            self.github = Github(self.token)
            self.rate_limiter = RateLimiter(max_calls=4500, time_window=3600)  # 5000/hour with buffer
        else:
            logger.warning("No GitHub token provided. Rate limits will be stricter.")
            self.github = Github()
            self.rate_limiter = RateLimiter(max_calls=60, time_window=3600)
        
        self.repo = self.github.get_repo(f"{self.repo_owner}/{self.repo_name}")
    
    def collect(self):
        """Collect all release notes."""
        logger.info("Starting release notes collection")
        
        # Collect from GitHub releases
        self._collect_github_releases()
        
        # Collect from Bitcoin Core website
        self._collect_website_releases()
        
        logger.info("Release notes collection complete")
    
    def _collect_github_releases(self):
        """Collect releases from GitHub."""
        logger.info("Collecting releases from GitHub")
        
        try:
            releases = []
            for release in self.repo.get_releases():
                self.rate_limiter.wait_if_needed()
                
                release_data = {
                    'tag_name': release.tag_name,
                    'name': release.title or release.tag_name,
                    'body': release.body,
                    'created_at': release.created_at.isoformat() if release.created_at else None,
                    'published_at': release.published_at.isoformat() if release.published_at else None,
                    'author': release.author.login if release.author else None,
                    'prerelease': release.prerelease,
                    'draft': release.draft,
                    'url': release.html_url,
                    'assets': [
                        {
                            'name': asset.name,
                            'size': asset.size,
                            'download_count': asset.download_count,
                            'url': asset.browser_download_url
                        }
                        for asset in release.assets
                    ]
                }
                
                releases.append(release_data)
                
                if len(releases) % 10 == 0:
                    logger.info(f"Collected {len(releases)} releases from GitHub")
            
            # Save releases
            releases_file = self.data_dir / "github_releases.jsonl"
            with open(releases_file, 'w') as f:
                for release in releases:
                    f.write(json.dumps(release) + '\n')
            
            logger.info(f"Saved {len(releases)} releases to {releases_file}")
            
        except Exception as e:
            logger.error(f"Error collecting GitHub releases: {e}")
            import traceback
            logger.debug(traceback.format_exc())
    
    def _collect_website_releases(self):
        """Collect release notes from Bitcoin Core website."""
        logger.info("Collecting releases from Bitcoin Core website")
        
        try:
            base_url = "https://bitcoincore.org/en/releases/"
            
            response = requests.get(base_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find release links
            releases = []
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                text = link.get_text().strip()
                
                # Look for version links (e.g., /en/releases/24.0.0/)
                version_match = re.search(r'releases/([\d.]+)', href)
                if version_match:
                    version = version_match.group(1)
                    release_url = f"https://bitcoincore.org{href}" if href.startswith('/') else href
                    
                    # Fetch release page
                    try:
                        release_response = requests.get(release_url, timeout=30)
                        if release_response.status_code == 200:
                            release_soup = BeautifulSoup(release_response.text, 'html.parser')
                            
                            # Extract release notes
                            release_data = {
                                'version': version,
                                'url': release_url,
                                'title': text,
                                'content': release_soup.get_text(),
                                'html': str(release_soup)
                            }
                            
                            releases.append(release_data)
                            
                            if len(releases) % 10 == 0:
                                logger.info(f"Collected {len(releases)} releases from website")
                    except Exception as e:
                        logger.debug(f"Error fetching release {release_url}: {e}")
                        continue
            
            # Save website releases
            website_releases_file = self.data_dir / "website_releases.jsonl"
            with open(website_releases_file, 'w') as f:
                for release in releases:
                    f.write(json.dumps(release) + '\n')
            
            logger.info(f"Saved {len(releases)} releases from website to {website_releases_file}")
            
        except Exception as e:
            logger.error(f"Error collecting website releases: {e}")
            import traceback
            logger.debug(traceback.format_exc())


def main():
    """Main entry point."""
    collector = ReleaseNotesCollector()
    collector.collect()


if __name__ == '__main__':
    main()

