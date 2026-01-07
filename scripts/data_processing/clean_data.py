#!/usr/bin/env python3
"""
Data Cleaning Pipeline - Clean and normalize all collected data.

This script:
1. Normalizes timestamps across all sources
2. Cleans text content (removes formatting artifacts)
3. Handles missing data
4. Validates data integrity
5. Tracks data quality metrics
"""

import sys
import json
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import re
try:
    from tqdm import tqdm
except ImportError:
    # Fallback if tqdm not available
    def tqdm(iterable, *args, **kwargs):
        return iterable

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir
from src.utils.data_quality import DataQualityTracker

logger = setup_logger()


class DataCleaner:
    """Cleans and normalizes data from all sources."""
    
    def __init__(self):
        """Initialize data cleaner."""
        self.data_dir = get_data_dir()
        self.processed_dir = self.data_dir / 'processed'
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
        self.quality_tracker = DataQualityTracker()
        self.stats = {
            'github_prs': {'processed': 0, 'errors': 0},
            'github_issues': {'processed': 0, 'errors': 0},
            'github_commits': {'processed': 0, 'errors': 0},
            'emails': {'processed': 0, 'errors': 0},
            'irc_messages': {'processed': 0, 'errors': 0},
            'release_signers': {'processed': 0, 'errors': 0}
        }
    
    def clean_all_data(self):
        """Clean all data sources."""
        logger.info("=" * 60)
        logger.info("Data Cleaning Pipeline")
        logger.info("=" * 60)
        
        # Clean each data source
        self._clean_github_prs()
        self._clean_github_issues()
        self._clean_github_commits()
        self._clean_emails()
        self._clean_irc_messages()
        self._clean_release_signers()
        
        # Generate quality report
        self._generate_quality_report()
        
        logger.info("=" * 60)
        logger.info("Data cleaning complete")
        logger.info("=" * 60)
    
    def _clean_github_prs(self):
        """Clean GitHub PR data."""
        input_file = self.data_dir / 'github' / 'prs_raw.jsonl'
        output_file = self.processed_dir / 'cleaned_prs.jsonl'
        
        if not input_file.exists():
            logger.warning(f"PR data file not found: {input_file}")
            return
        
        # Create backup of existing cleaned file before overwriting
        if output_file.exists():
            backup_dir = self.data_dir.parent / 'backups' / 'safe'
            backup_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = backup_dir / f'cleaned_prs_BACKUP_{timestamp}.jsonl'
            logger.info(f"Creating backup of existing cleaned PRs to {backup_file.name}...")
            shutil.copy2(output_file, backup_file)
            logger.info(f"✅ Backup created: {backup_file}")
        
        logger.info(f"Cleaning GitHub PRs from {input_file.name}...")
        
        total_lines = sum(1 for _ in open(input_file))
        
        with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
            for line in tqdm(infile, total=total_lines, desc="Cleaning PRs"):
                try:
                    pr = json.loads(line)
                    cleaned = self._clean_pr(pr)
                    if cleaned:
                        outfile.write(json.dumps(cleaned) + '\n')
                        self.stats['github_prs']['processed'] += 1
                    else:
                        self.stats['github_prs']['errors'] += 1
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON decode error: {e}")
                    self.stats['github_prs']['errors'] += 1
                except Exception as e:
                    logger.error(f"Error cleaning PR: {e}")
                    self.stats['github_prs']['errors'] += 1
        
        logger.info(f"Cleaned {self.stats['github_prs']['processed']} PRs")
        if self.stats['github_prs']['errors'] > 0:
            logger.warning(f"Encountered {self.stats['github_prs']['errors']} errors")
    
    def _clean_github_issues(self):
        """Clean GitHub issue data."""
        input_file = self.data_dir / 'github' / 'issues_raw.jsonl'
        output_file = self.processed_dir / 'cleaned_issues.jsonl'
        
        if not input_file.exists():
            logger.warning(f"Issue data file not found: {input_file}")
            return
        
        logger.info(f"Cleaning GitHub issues from {input_file.name}...")
        
        total_lines = sum(1 for _ in open(input_file))
        
        with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
            for line in tqdm(infile, total=total_lines, desc="Cleaning issues"):
                try:
                    issue = json.loads(line)
                    cleaned = self._clean_issue(issue)
                    if cleaned:
                        outfile.write(json.dumps(cleaned) + '\n')
                        self.stats['github_issues']['processed'] += 1
                    else:
                        self.stats['github_issues']['errors'] += 1
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON decode error: {e}")
                    self.stats['github_issues']['errors'] += 1
                except Exception as e:
                    logger.error(f"Error cleaning issue: {e}")
                    self.stats['github_issues']['errors'] += 1
        
        logger.info(f"Cleaned {self.stats['github_issues']['processed']} issues")
        if self.stats['github_issues']['errors'] > 0:
            logger.warning(f"Encountered {self.stats['github_issues']['errors']} errors")
    
    def _clean_emails(self):
        """Clean mailing list email data."""
        input_file = self.data_dir / 'mailing_lists' / 'emails.jsonl'
        output_file = self.processed_dir / 'cleaned_emails.jsonl'
        
        if not input_file.exists():
            logger.warning(f"Email data file not found: {input_file}")
            return
        
        logger.info(f"Cleaning emails from {input_file.name}...")
        
        total_lines = sum(1 for _ in open(input_file))
        
        with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
            for line in tqdm(infile, total=total_lines, desc="Cleaning emails"):
                try:
                    email = json.loads(line)
                    cleaned = self._clean_email(email)
                    if cleaned:
                        outfile.write(json.dumps(cleaned) + '\n')
                        self.stats['emails']['processed'] += 1
                    else:
                        self.stats['emails']['errors'] += 1
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON decode error: {e}")
                    self.stats['emails']['errors'] += 1
                except Exception as e:
                    logger.error(f"Error cleaning email: {e}")
                    self.stats['emails']['errors'] += 1
        
        logger.info(f"Cleaned {self.stats['emails']['processed']} emails")
        if self.stats['emails']['errors'] > 0:
            logger.warning(f"Encountered {self.stats['emails']['errors']} errors")
    
    def _clean_irc_messages(self):
        """Clean IRC message data."""
        input_file = self.data_dir / 'irc' / 'messages.jsonl'
        output_file = self.processed_dir / 'cleaned_irc.jsonl'
        
        if not input_file.exists():
            logger.warning(f"IRC data file not found: {input_file}")
            return
        
        logger.info(f"Cleaning IRC messages from {input_file.name}...")
        
        total_lines = sum(1 for _ in open(input_file))
        
        with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
            for line in tqdm(infile, total=total_lines, desc="Cleaning IRC"):
                try:
                    message = json.loads(line)
                    cleaned = self._clean_irc_message(message)
                    if cleaned:
                        outfile.write(json.dumps(cleaned) + '\n')
                        self.stats['irc_messages']['processed'] += 1
                    else:
                        self.stats['irc_messages']['errors'] += 1
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON decode error: {e}")
                    self.stats['irc_messages']['errors'] += 1
                except Exception as e:
                    logger.error(f"Error cleaning IRC message: {e}")
                    self.stats['irc_messages']['errors'] += 1
        
        logger.info(f"Cleaned {self.stats['irc_messages']['processed']} IRC messages")
        if self.stats['irc_messages']['errors'] > 0:
            logger.warning(f"Encountered {self.stats['irc_messages']['errors']} errors")
    
    def _clean_github_commits(self):
        """Clean GitHub commit data."""
        input_file = self.data_dir / 'github' / 'commits_raw.jsonl'
        output_file = self.processed_dir / 'cleaned_commits.jsonl'
        
        if not input_file.exists():
            logger.warning(f"Commit data file not found: {input_file}")
            return
        
        logger.info(f"Cleaning GitHub commits from {input_file.name}...")
        
        total_lines = sum(1 for _ in open(input_file))
        
        with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
            for line in tqdm(infile, total=total_lines, desc="Cleaning commits"):
                try:
                    commit = json.loads(line)
                    cleaned = self._clean_commit(commit)
                    if cleaned:
                        outfile.write(json.dumps(cleaned) + '\n')
                        self.stats['github_commits']['processed'] += 1
                    else:
                        self.stats['github_commits']['errors'] += 1
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON decode error: {e}")
                    self.stats['github_commits']['errors'] += 1
                except Exception as e:
                    logger.error(f"Error cleaning commit: {e}")
                    self.stats['github_commits']['errors'] += 1
        
        logger.info(f"Cleaned {self.stats['github_commits']['processed']} commits")
        if self.stats['github_commits']['errors'] > 0:
            logger.warning(f"Encountered {self.stats['github_commits']['errors']} errors")
    
    def _clean_commit(self, commit: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Clean a single commit record."""
        cleaned = commit.copy()
        
        # Normalize timestamp
        if 'commit' in cleaned and 'author' in cleaned['commit']:
            if 'date' in cleaned['commit']['author']:
                cleaned['commit']['author']['date'] = self._normalize_timestamp(
                    cleaned['commit']['author']['date']
                )
        
        # Ensure required fields
        if not cleaned.get('sha'):
            return None
        
        # Clean commit message
        if 'commit' in cleaned and 'message' in cleaned['commit']:
            cleaned['commit']['message'] = self._clean_text(cleaned['commit']['message'])
        
        return cleaned
    
    def _clean_release_signers(self):
        """Clean release signer data."""
        input_file = self.data_dir / 'releases' / 'release_signers.jsonl'
        output_file = self.processed_dir / 'cleaned_release_signers.jsonl'
        
        if not input_file.exists():
            logger.warning(f"Release signer data file not found: {input_file}")
            return
        
        logger.info(f"Cleaning release signers from {input_file.name}...")
        
        total_lines = sum(1 for _ in open(input_file))
        
        with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
            for line in tqdm(infile, total=total_lines, desc="Cleaning release signers"):
                try:
                    release = json.loads(line)
                    cleaned = self._clean_release_signer(release)
                    if cleaned:
                        outfile.write(json.dumps(cleaned) + '\n')
                        self.stats['release_signers']['processed'] += 1
                    else:
                        self.stats['release_signers']['errors'] += 1
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON decode error: {e}")
                    self.stats['release_signers']['errors'] += 1
                except Exception as e:
                    logger.error(f"Error cleaning release signer: {e}")
                    self.stats['release_signers']['errors'] += 1
        
        logger.info(f"Cleaned {self.stats['release_signers']['processed']} release signers")
        if self.stats['release_signers']['errors'] > 0:
            logger.warning(f"Encountered {self.stats['release_signers']['errors']} errors")
    
    def _clean_release_signer(self, release: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Clean a single release signer record."""
        cleaned = release.copy()
        
        # Normalize timestamp
        if 'tagger_date_iso' in cleaned and cleaned['tagger_date_iso']:
            cleaned['tagger_date_iso'] = self._normalize_timestamp(cleaned['tagger_date_iso'])
        
        # Ensure required fields
        if not cleaned.get('tag'):
            return None
        
        # Clean signer information
        if 'signer_email' in cleaned:
            cleaned['signer_email'] = cleaned['signer_email'].lower().strip() if cleaned['signer_email'] else None
        
        if 'signer_name' in cleaned:
            cleaned['signer_name'] = cleaned['signer_name'].strip() if cleaned['signer_name'] else None
        
        return cleaned
    
    def _clean_pr(self, pr: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Clean a single PR."""
        cleaned = pr.copy()
        
        # Normalize timestamps
        for date_field in ['created_at', 'updated_at', 'closed_at', 'merged_at']:
            if date_field in cleaned and cleaned[date_field]:
                cleaned[date_field] = self._normalize_timestamp(cleaned[date_field])
        
        # Clean text fields
        for text_field in ['title', 'body']:
            if text_field in cleaned and cleaned[text_field]:
                cleaned[text_field] = self._clean_text(cleaned[text_field])
        
        # Clean comments
        if 'comments' in cleaned:
            for comment in cleaned.get('comments', []):
                if 'body' in comment:
                    comment['body'] = self._clean_text(comment['body'])
        
        # Clean reviews
        if 'reviews' in cleaned:
            for review in cleaned.get('reviews', []):
                if 'body' in review:
                    review['body'] = self._clean_text(review['body'])
        
        # Ensure required fields
        if not cleaned.get('number') or not cleaned.get('author'):
            return None
        
        return cleaned
    
    def _clean_issue(self, issue: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Clean a single issue."""
        cleaned = issue.copy()
        
        # Normalize timestamps
        for date_field in ['created_at', 'updated_at', 'closed_at']:
            if date_field in cleaned and cleaned[date_field]:
                cleaned[date_field] = self._normalize_timestamp(cleaned[date_field])
        
        # Clean text fields
        for text_field in ['title', 'body']:
            if text_field in cleaned and cleaned[text_field]:
                cleaned[text_field] = self._clean_text(cleaned[text_field])
        
        # Clean comments
        if 'comments' in cleaned:
            for comment in cleaned.get('comments', []):
                if 'body' in comment:
                    comment['body'] = self._clean_text(comment['body'])
        
        # Ensure required fields
        if not cleaned.get('number') or not cleaned.get('author'):
            return None
        
        return cleaned
    
    def _clean_email(self, email: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Clean a single email."""
        cleaned = email.copy()
        
        # Normalize timestamp
        if 'date' in cleaned and cleaned['date']:
            cleaned['date'] = self._normalize_timestamp(cleaned['date'])
        
        # Clean text fields
        for text_field in ['subject', 'body']:
            if text_field in cleaned and cleaned[text_field]:
                cleaned[text_field] = self._clean_text(cleaned[text_field])
        
        # Ensure required fields
        if not cleaned.get('from') or not cleaned.get('date'):
            return None
        
        return cleaned
    
    def _clean_irc_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Clean a single IRC message."""
        cleaned = message.copy()
        
        # Normalize timestamp
        if 'timestamp' in cleaned and cleaned['timestamp']:
            cleaned['timestamp'] = self._normalize_timestamp(cleaned['timestamp'])
        
        # Clean text
        if 'content' in cleaned and cleaned['content']:
            cleaned['content'] = self._clean_text(cleaned['content'])
        
        # Ensure required fields
        if not cleaned.get('author') or not cleaned.get('timestamp'):
            return None
        
        return cleaned
    
    def _normalize_timestamp(self, timestamp: Any) -> Optional[str]:
        """Normalize timestamp to ISO 8601 format."""
        if not timestamp:
            return None
        
        if isinstance(timestamp, str):
            # Try to parse various formats
            try:
                # ISO format
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                return dt.isoformat()
            except ValueError:
                try:
                    # Common formats
                    for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d']:
                        try:
                            dt = datetime.strptime(timestamp, fmt)
                            return dt.isoformat()
                        except ValueError:
                            continue
                except Exception:
                    pass
        
        return None
    
    def _clean_text(self, text: str) -> str:
        """Clean text content."""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove control characters (keep newlines and tabs)
        text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F]', '', text)
        
        # Normalize unicode
        text = text.encode('utf-8', errors='ignore').decode('utf-8')
        
        return text.strip()
    
    def _generate_quality_report(self):
        """Generate data quality report."""
        # Track completeness
        for source, stats in self.stats.items():
            total = stats['processed'] + stats['errors']
            if total > 0:
                self.quality_tracker.track_completeness(
                    source,
                    stats['processed'],
                    total
                )
        
        # Track accuracy
        total_errors = sum(s['errors'] for s in self.stats.values())
        total_processed = sum(s['processed'] for s in self.stats.values())
        total_records = total_processed + total_errors
        
        if total_records > 0:
            self.quality_tracker.track_accuracy(
                total_errors,
                total_records
            )
        
        # Save report
        self.quality_tracker.save_report()


def main():
    """Main entry point."""
    cleaner = DataCleaner()
    cleaner.clean_all_data()
    return 0


if __name__ == '__main__':
    sys.exit(main())

