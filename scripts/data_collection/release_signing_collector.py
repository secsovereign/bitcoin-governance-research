#!/usr/bin/env python3
"""
Release signing information collector for Bitcoin Core.

Extracts signed git tags to identify who has release signing authority.
"""

import sys
import os
import json
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import re

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config import config
from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir

logger = setup_logger()


class ReleaseSigningCollector:
    """Collector for release signing information."""
    
    def __init__(self):
        """Initialize release signing collector."""
        self.repo_url = "https://github.com/bitcoin/bitcoin.git"
        self.data_dir = get_data_dir() / "releases"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir = None
        
    def collect(self):
        """Collect release signing information."""
        logger.info("Starting release signing information collection")
        
        try:
            # Clone repository to temp directory
            self.temp_dir = tempfile.mkdtemp(prefix="bitcoin_releases_")
            logger.info(f"Cloning repository to {self.temp_dir}")
            
            # Clone repository (shallow clone for speed)
            logger.info("Cloning repository (this may take a minute)...")
            subprocess.run(
                ["git", "clone", "--depth=1", self.repo_url, self.temp_dir],
                check=True,
                capture_output=True,
                timeout=300
            )
            
            # Fetch all tags (tags aren't included in shallow clone)
            logger.info("Fetching all tags...")
            subprocess.run(
                ["git", "fetch", "--tags", "--depth=1"],
                cwd=self.temp_dir,
                check=True,
                capture_output=True,
                timeout=120
            )
            
            # Get all tags
            logger.info("Getting all release tags")
            result = subprocess.run(
                ["git", "tag", "-l"],
                cwd=self.temp_dir,
                capture_output=True,
                text=True,
                check=True
            )
            
            tags = [tag.strip() for tag in result.stdout.strip().split('\n') if tag.strip()]
            logger.info(f"Found {len(tags)} tags")
            
            # Filter for version tags (v0.x.x format)
            version_tags = [tag for tag in tags if re.match(r'^v?\d+\.\d+', tag)]
            logger.info(f"Found {len(version_tags)} version tags")
            
            # Extract signing information from each tag
            signing_data = []
            for i, tag in enumerate(sorted(version_tags, reverse=True)):  # Most recent first
                try:
                    tag_info = self._extract_tag_signing_info(tag)
                    if tag_info:
                        signing_data.append(tag_info)
                    
                    if (i + 1) % 10 == 0:
                        logger.info(f"Processed {i+1}/{len(version_tags)} tags")
                        
                except Exception as e:
                    logger.warning(f"Error processing tag {tag}: {e}")
                    continue
            
            # Save signing data
            output_file = self.data_dir / "release_signers.jsonl"
            with open(output_file, 'w') as f:
                for data in signing_data:
                    f.write(json.dumps(data) + '\n')
            
            logger.info(f"Collected signing information for {len(signing_data)} releases")
            logger.info(f"Saved to {output_file}")
            
            # Generate summary
            if signing_data:
                self._generate_summary(signing_data)
            
        except Exception as e:
            logger.error(f"Error collecting release signing information: {e}")
            import traceback
            logger.debug(traceback.format_exc())
        finally:
            # Cleanup
            if self.temp_dir and os.path.exists(self.temp_dir):
                logger.info(f"Cleaning up temp directory: {self.temp_dir}")
                shutil.rmtree(self.temp_dir)
    
    def _extract_tag_signing_info(self, tag: str) -> Optional[Dict[str, Any]]:
        """Extract signing information from a git tag."""
        try:
            # Get tag object
            result = subprocess.run(
                ["git", "cat-file", "-p", tag],
                cwd=self.temp_dir,
                capture_output=True,
                text=True,
                check=True
            )
            
            tag_content = result.stdout
            
            # Try to verify tag signature
            verify_result = subprocess.run(
                ["git", "tag", "-v", tag],
                cwd=self.temp_dir,
                capture_output=True,
                text=True
            )
            
            tag_info = {
                'tag': tag,
                'tag_content': tag_content,
                'is_signed': False,
                'signer_key_id': None,
                'signer_email': None,
                'signer_name': None,
                'verification_output': verify_result.stdout,
                'verification_stderr': verify_result.stderr,
                'verification_returncode': verify_result.returncode
            }
            
            # Parse tag content for signer information
            if '-----BEGIN PGP SIGNATURE-----' in tag_content:
                tag_info['is_signed'] = True
                
                # Try to extract signer info from tag content
                # Tag format: "object <hash>\ntype commit\ntag <tag>\ntagger <name> <email> <date>\n\n<message>\n-----BEGIN PGP SIGNATURE-----"
                tagger_match = re.search(r'tagger\s+([^<]+)\s+<([^>]+)>\s+(\d+)', tag_content)
                if tagger_match:
                    tag_info['signer_name'] = tagger_match.group(1).strip()
                    tag_info['signer_email'] = tagger_match.group(2).strip()
                    tag_info['tagger_date'] = int(tagger_match.group(3))
                    tag_info['tagger_date_iso'] = datetime.fromtimestamp(int(tagger_match.group(3))).isoformat()
            
            # Parse verification output for key ID
            if verify_result.returncode == 0:
                # Look for "Good signature from" or key ID
                key_match = re.search(r'key ID\s+([A-F0-9]+)', verify_result.stdout + verify_result.stderr, re.IGNORECASE)
                if key_match:
                    tag_info['signer_key_id'] = key_match.group(1).upper()
                
                good_sig_match = re.search(r'Good signature from\s+"?([^"]+)"?', verify_result.stdout + verify_result.stderr, re.IGNORECASE)
                if good_sig_match:
                    signer_info = good_sig_match.group(1)
                    # Try to parse name and email
                    email_match = re.search(r'<([^>]+)>', signer_info)
                    if email_match:
                        tag_info['signer_email'] = email_match.group(1)
                        tag_info['signer_name'] = signer_info.split('<')[0].strip()
            
            return tag_info
            
        except subprocess.CalledProcessError as e:
            logger.debug(f"Error extracting tag info for {tag}: {e}")
            return None
        except Exception as e:
            logger.debug(f"Error processing tag {tag}: {e}")
            return None
    
    def _generate_summary(self, signing_data: List[Dict[str, Any]]):
        """Generate summary of collected signing data."""
        logger.info("=== Release Signing Collection Summary ===")
        logger.info(f"Total releases processed: {len(signing_data)}")
        
        signed_count = sum(1 for d in signing_data if d.get('is_signed', False))
        logger.info(f"Signed releases: {signed_count}")
        logger.info(f"Unsigned releases: {len(signing_data) - signed_count}")
        
        # Count unique signers
        signers = set()
        for data in signing_data:
            if data.get('signer_email'):
                signers.add(data['signer_email'])
            elif data.get('signer_name'):
                signers.add(data['signer_name'])
        
        logger.info(f"Unique signers identified: {len(signers)}")
        
        if signers:
            logger.info("Signers:")
            for signer in sorted(signers)[:10]:  # Show first 10
                logger.info(f"  - {signer}")


def main():
    """Main entry point."""
    collector = ReleaseSigningCollector()
    collector.collect()
    logger.info("Release signing collection complete")


if __name__ == '__main__':
    main()

