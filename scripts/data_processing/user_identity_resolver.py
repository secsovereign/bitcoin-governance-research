#!/usr/bin/env python3
"""
User Identity Resolver - Cross-reference usernames across all data sources.

Maps usernames from different sources (GitHub, mailing lists, IRC) to unified identities.
Identifies maintainers and builds comprehensive user profiles.
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
from collections import defaultdict
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir, get_analysis_dir
import re

logger = setup_logger()


class UserIdentityResolver:
    """Resolves user identities across multiple data sources."""
    
    def __init__(self):
        """Initialize resolver."""
        self.data_dir = get_data_dir()
        self.analysis_dir = get_analysis_dir()
        
        # User identity mappings
        self.github_to_unified = {}  # GitHub username -> unified ID
        self.email_to_unified = {}   # Email -> unified ID
        self.irc_to_unified = {}     # IRC nickname -> unified ID
        self.unified_profiles = {}   # unified ID -> full profile
        
        # Maintainer information
        self.maintainers = set()  # Set of unified IDs who are/were maintainers
        self.maintainer_timeline = {}  # unified ID -> list of (start_date, end_date, source)
    
    def resolve_all_identities(self):
        """Resolve identities across all data sources."""
        logger.info("=" * 60)
        logger.info("User Identity Resolution")
        logger.info("=" * 60)
        
        # Load data from all sources
        github_users = self._extract_github_users()
        email_users = self._extract_email_users()
        irc_users = self._extract_irc_users()
        release_signer_users = self._extract_release_signer_users()
        contributor_users = self._extract_contributor_users()
        
        logger.info(f"Found {len(github_users)} GitHub users")
        logger.info(f"Found {len(email_users)} email users")
        logger.info(f"Found {len(irc_users)} IRC users")
        logger.info(f"Found {len(release_signer_users)} release signer users")
        logger.info(f"Found {len(contributor_users)} contributor users")
        
        # Build identity mappings (including new sources)
        self._build_identity_mappings(
            github_users, email_users, irc_users,
            release_signer_users, contributor_users
        )
        
        # Load maintainer information
        self._load_maintainer_data()
        
        # Build unified profiles
        self._build_unified_profiles(
            github_users, email_users, irc_users,
            release_signer_users, contributor_users
        )
        
        # Save results
        self._save_identity_mappings()
        
        logger.info(f"Resolved {len(self.unified_profiles)} unique identities")
        logger.info(f"Identified {len(self.maintainers)} maintainers")
    
    def _extract_github_users(self) -> Dict[str, Dict[str, Any]]:
        """Extract users from GitHub data."""
        users = {}
        
        prs_file = self.data_dir / 'github' / 'prs_raw.jsonl'
        issues_file = self.data_dir / 'github' / 'issues_raw.jsonl'
        
        for file_path in [prs_file, issues_file]:
            if not file_path.exists():
                continue
            
            logger.info(f"Extracting users from {file_path.name}...")
            with open(file_path, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        
                        # Extract author
                        if 'author' in data and data['author']:
                            username = data['author']
                            if username not in users:
                                users[username] = {
                                    'github_username': username,
                                    'github_id': data.get('author_id'),
                                    'first_seen': data.get('created_at'),
                                    'sources': ['github'],
                                    'prs': [],
                                    'issues': [],
                                }
                            
                            if 'number' in data:
                                if file_path.name.startswith('prs'):
                                    users[username]['prs'].append(data['number'])
                                else:
                                    users[username]['issues'].append(data['number'])
                        
                        # Extract comment authors
                        for comment in data.get('comments', []):
                            if 'author' in comment and comment['author']:
                                username = comment['author']
                                if username not in users:
                                    users[username] = {
                                        'github_username': username,
                                        'sources': ['github'],
                                        'prs': [],
                                        'issues': [],
                                    }
                        
                        # Extract review authors
                        for review in data.get('reviews', []):
                            if 'author' in review and review['author']:
                                username = review['author']
                                if username not in users:
                                    users[username] = {
                                        'github_username': username,
                                        'sources': ['github'],
                                        'prs': [],
                                        'issues': [],
                                    }
                    
                    except json.JSONDecodeError:
                        continue
        
        return users
    
    def _extract_email_users(self) -> Dict[str, Dict[str, Any]]:
        """Extract users from mailing list data."""
        users = {}
        
        emails_file = self.data_dir / 'mailing_lists' / 'emails.jsonl'
        if not emails_file.exists():
            return users
        
        logger.info(f"Extracting users from {emails_file.name}...")
        with open(emails_file, 'r') as f:
            for line in f:
                try:
                    email = json.loads(line)
                    
                    # Parse "From" field
                    from_field = email.get('from', '')
                    # Format: "Name <email@example.com>" or "email@example.com"
                    
                    email_match = re.search(r'<([^>]+)>', from_field)
                    if email_match:
                        email_addr = email_match.group(1)
                        name = from_field.split('<')[0].strip().strip('"')
                    else:
                        email_addr = from_field.strip()
                        name = None
                    
                    if email_addr and '@' in email_addr:
                        if email_addr not in users:
                            users[email_addr] = {
                                'email': email_addr,
                                'name': name,
                                'first_seen': email.get('date'),
                                'sources': ['mailing_list'],
                                'emails': [],
                            }
                        
                        users[email_addr]['emails'].append(email.get('message_id'))
                
                except json.JSONDecodeError:
                    continue
        
        return users
    
    def _extract_irc_users(self) -> Dict[str, Dict[str, Any]]:
        """Extract users from IRC data."""
        users = {}
        
        messages_file = self.data_dir / 'irc' / 'messages.jsonl'
        if not messages_file.exists():
            return users
        
        logger.info(f"Extracting users from {messages_file.name}...")
        with open(messages_file, 'r') as f:
            for line in f:
                try:
                    msg = json.loads(line)
                    nickname = msg.get('nickname')
                    
                    if nickname:
                        if nickname not in users:
                            users[nickname] = {
                                'irc_nickname': nickname,
                                'first_seen': msg.get('timestamp'),
                                'sources': ['irc'],
                                'messages': [],
                            }
                        
                        users[nickname]['messages'].append(msg.get('timestamp'))
                
                except json.JSONDecodeError:
                    continue
        
        return users
    
    def _extract_release_signer_users(self) -> Dict[str, Dict[str, Any]]:
        """Extract users from release signer data."""
        users = {}
        
        signers_file = self.data_dir / 'releases' / 'release_signers.jsonl'
        if not signers_file.exists():
            return users
        
        logger.info(f"Extracting users from {signers_file.name}...")
        with open(signers_file, 'r') as f:
            for line in f:
                try:
                    release = json.loads(line)
                    
                    if not release.get('is_signed'):
                        continue
                    
                    signer_email = release.get('signer_email')
                    signer_name = release.get('signer_name')
                    
                    if signer_email:
                        if signer_email not in users:
                            users[signer_email] = {
                                'email': signer_email,
                                'name': signer_name,
                                'first_seen': release.get('tagger_date_iso'),
                                'sources': ['release_signing'],
                                'release_count': 0,
                                'releases': []
                            }
                        
                        users[signer_email]['release_count'] += 1
                        users[signer_email]['releases'].append(release.get('tag'))
                
                except json.JSONDecodeError:
                    continue
        
        return users
    
    def _extract_contributor_users(self) -> Dict[str, Dict[str, Any]]:
        """Extract users from contributors data."""
        users = {}
        
        contributors_file = self.data_dir / 'github' / 'collaborators.json'
        if not contributors_file.exists():
            return users
        
        logger.info(f"Extracting users from {contributors_file.name}...")
        try:
            with open(contributors_file, 'r') as f:
                data = json.load(f)
                contributors = data.get('contributors', [])
                
                for i, contrib in enumerate(contributors):
                    login = contrib.get('login')
                    if login:
                        users[login] = {
                            'github_username': login,
                            'name': contrib.get('name'),
                            'email': contrib.get('email'),
                            'contributions': contrib.get('contributions', 0),
                            'rank': i + 1,
                            'sources': ['contributors'],
                            'first_seen': contrib.get('created_at')
                        }
        except Exception as e:
            logger.warning(f"Error extracting contributors: {e}")
        
        return users
    
    def _build_identity_mappings(
        self,
        github_users: Dict,
        email_users: Dict,
        irc_users: Dict,
        release_signer_users: Dict = None,
        contributor_users: Dict = None
    ):
        """Build mappings between different identity representations."""
        import re
        
        # Strategy 1: Direct matches (same username/email across sources)
        # Strategy 2: Email extraction from GitHub profiles (if available)
        # Strategy 3: Name matching
        # Strategy 4: Activity correlation (same person active in same time periods)
        
        unified_id_counter = 0
        
        # Create unified IDs
        for github_username, github_data in github_users.items():
            unified_id = f"user_{unified_id_counter}"
            unified_id_counter += 1
            
            self.github_to_unified[github_username] = unified_id
            self.unified_profiles[unified_id] = {
                'unified_id': unified_id,
                'github_username': github_username,
                'sources': ['github'],
                **github_data
            }
        
        # Try to match emails to GitHub users
        # Also match release signer emails
        for email, email_data in email_users.items():
            # Try to find matching GitHub user or release signer
            matched = False
            matched_unified_id = None
            
            # Check release signers first (more specific)
            if release_signer_users and email in release_signer_users:
                # Try to match to existing profile
                for unified_id, profile in self.unified_profiles.items():
                    if profile.get('email') == email or profile.get('github_username') in email:
                        matched_unified_id = unified_id
                        matched = True
                        break
                
                if not matched:
                    # Create new unified ID for release signer
                    unified_id = f"user_{unified_id_counter}"
                    unified_id_counter += 1
                    matched_unified_id = unified_id
                    matched = True
            
            # If not matched, try GitHub users
            if not matched:
                for unified_id, profile in self.unified_profiles.items():
                    # Simple heuristic: check if email domain matches common patterns
                    # In practice, would need GitHub profile emails
                    pass
            
            if not matched:
                unified_id = f"user_{unified_id_counter}"
                unified_id_counter += 1
                matched_unified_id = unified_id
            
            self.email_to_unified[email] = matched_unified_id
            if matched_unified_id in self.unified_profiles:
                # Merge email data
                profile = self.unified_profiles[matched_unified_id]
                if 'mailing_list' not in profile.get('sources', []):
                    profile.setdefault('sources', []).append('mailing_list')
                profile.update({k: v for k, v in email_data.items() if k not in profile})
            else:
                # Create new profile
                self.unified_profiles[matched_unified_id] = {
                    'unified_id': matched_unified_id,
                    'email': email,
                    'sources': ['mailing_list'],
                    **email_data
                }
        
        # Add release signers
        if release_signer_users:
            for email, signer_data in release_signer_users.items():
                unified_id = self.email_to_unified.get(email)
                if unified_id:
                    # Merge into existing profile
                    profile = self.unified_profiles[unified_id]
                    if 'release_signing' not in profile.get('sources', []):
                        profile.setdefault('sources', []).append('release_signing')
                    profile['release_signing_count'] = signer_data.get('release_count', 0)
                    profile['release_signing_authority'] = True
                else:
                    # Create new profile
                    unified_id = f"user_{unified_id_counter}"
                    unified_id_counter += 1
                    self.email_to_unified[email] = unified_id
                    self.unified_profiles[unified_id] = {
                        'unified_id': unified_id,
                        'email': email,
                        'sources': ['release_signing'],
                        'release_signing_count': signer_data.get('release_count', 0),
                        'release_signing_authority': True,
                        **signer_data
                    }
        
        # Add contributors (match to GitHub users)
        if contributor_users:
            for login, contrib_data in contributor_users.items():
                unified_id = self.github_to_unified.get(login)
                if unified_id:
                    # Merge contributor data
                    profile = self.unified_profiles[unified_id]
                    profile['contributions'] = contrib_data.get('contributions', 0)
                    profile['contributor_rank'] = contrib_data.get('rank')
                    if 'contributors' not in profile.get('sources', []):
                        profile.setdefault('sources', []).append('contributors')
                else:
                    # Create new profile
                    unified_id = f"user_{unified_id_counter}"
                    unified_id_counter += 1
                    self.github_to_unified[login] = unified_id
                    self.unified_profiles[unified_id] = {
                        'unified_id': unified_id,
                        'github_username': login,
                        'sources': ['contributors'],
                        'contributions': contrib_data.get('contributions', 0),
                        'contributor_rank': contrib_data.get('rank'),
                        **contrib_data
                    }
        
        # Match IRC users
        for nickname, irc_data in irc_users.items():
            # Try to match to GitHub username (common pattern: same username)
            matched_unified_id = None
            
            # Direct username match
            if nickname in self.github_to_unified:
                matched_unified_id = self.github_to_unified[nickname]
            else:
                # Create new unified ID
                unified_id = f"user_{unified_id_counter}"
                unified_id_counter += 1
                matched_unified_id = unified_id
            
            self.irc_to_unified[nickname] = matched_unified_id
            
            if matched_unified_id in self.unified_profiles:
                # Merge IRC data into existing profile
                profile = self.unified_profiles[matched_unified_id]
                profile['irc_nickname'] = nickname
                if 'irc' not in profile['sources']:
                    profile['sources'].append('irc')
                profile.update({k: v for k, v in irc_data.items() if k not in profile})
            else:
                # Create new profile
                self.unified_profiles[matched_unified_id] = {
                    'unified_id': matched_unified_id,
                    'irc_nickname': nickname,
                    'sources': ['irc'],
                    **irc_data
                }
    
    def _load_maintainer_data(self):
        """Load maintainer information from MAINTAINERS file history."""
        # This would parse git log of MAINTAINERS file
        # For now, use a known maintainer list or parse from GitHub data
        
        # Known maintainers (would be loaded from MAINTAINERS file git history)
        known_maintainers = [
            'sipa', 'laanwj', 'MarcoFalke', 'achow101', 'gmaxwell',
            'jnewbery', 'fanquake', 'hebasto', 'ryanofsky', 'Sjors',
            # Add more as identified
        ]
        
        for maintainer in known_maintainers:
            # Find unified ID for this maintainer
            for unified_id, profile in self.unified_profiles.items():
                if profile.get('github_username') == maintainer:
                    self.maintainers.add(unified_id)
                    break
    
    def _build_unified_profiles(
        self,
        github_users: Dict,
        email_users: Dict,
        irc_users: Dict,
        release_signer_users: Dict = None,
        contributor_users: Dict = None
    ):
        """Build comprehensive unified user profiles."""
        for unified_id, profile in self.unified_profiles.items():
            # Add maintainer status
            profile['is_maintainer'] = unified_id in self.maintainers
            
            # Calculate activity metrics
            profile['total_prs'] = len(profile.get('prs', []))
            profile['total_issues'] = len(profile.get('issues', []))
            profile['total_emails'] = len(profile.get('emails', []))
            profile['total_irc_messages'] = len(profile.get('messages', []))
            
            # Determine primary identity
            if profile.get('github_username'):
                profile['primary_identity'] = profile['github_username']
            elif profile.get('email'):
                profile['primary_identity'] = profile['email']
            elif profile.get('irc_nickname'):
                profile['primary_identity'] = profile['irc_nickname']
    
    def _save_identity_mappings(self):
        """Save identity mappings and profiles."""
        output_dir = self.analysis_dir / 'user_identities'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save mappings
        mappings = {
            'github_to_unified': self.github_to_unified,
            'email_to_unified': self.email_to_unified,
            'irc_to_unified': self.irc_to_unified,
        }
        
        with open(output_dir / 'identity_mappings.json', 'w') as f:
            json.dump(mappings, f, indent=2)
        
        # Save unified profiles
        profiles_list = list(self.unified_profiles.values())
        with open(output_dir / 'unified_profiles.json', 'w') as f:
            json.dump(profiles_list, f, indent=2)
        
        # Save maintainer list
        maintainer_list = [
            self.unified_profiles[mid] for mid in self.maintainers
            if mid in self.unified_profiles
        ]
        with open(output_dir / 'maintainers.json', 'w') as f:
            json.dump(maintainer_list, f, indent=2)
        
        logger.info(f"Saved identity mappings to {output_dir}")


def main():
    """Main entry point."""
    resolver = UserIdentityResolver()
    resolver.resolve_all_identities()


if __name__ == '__main__':
    import re
    main()

