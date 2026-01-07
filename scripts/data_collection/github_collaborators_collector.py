#!/usr/bin/env python3
"""
GitHub collaborators collector for Bitcoin Core repository.

Collects information about who has write access to the repository.
"""

import sys
import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

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


class GitHubCollaboratorsCollector:
    """Collector for GitHub repository collaborators."""
    
    def __init__(self):
        """Initialize collaborators collector."""
        self.token = config.get('data_collection.github.token') or os.getenv('GITHUB_TOKEN')
        self.repo_owner = config.get('data_collection.github.repository.owner', 'bitcoin')
        self.repo_name = config.get('data_collection.github.repository.name', 'bitcoin')
        self.data_dir = get_data_dir() / "github"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize GitHub API client
        if self.token:
            self.github = Github(self.token)
            self.rate_limiter = RateLimiter(max_calls=4500, time_window=3600)
        else:
            logger.warning("No GitHub token provided. Rate limits will be stricter.")
            self.github = Github()
            self.rate_limiter = RateLimiter(max_calls=60, time_window=3600)
        
        self.repo = self.github.get_repo(f"{self.repo_owner}/{self.repo_name}")
    
    def collect(self):
        """Collect collaborators information."""
        logger.info("Starting GitHub collaborators collection")
        
        collaborators_data = {
            'repository': f"{self.repo_owner}/{self.repo_name}",
            'collected_at': datetime.now().isoformat(),
            'collaborators': [],
            'contributors': [],
            'organization_members': []
        }
        
        try:
            # Get collaborators (who has write access)
            logger.info("Collecting repository collaborators...")
            try:
                collaborators = self.repo.get_collaborators()
                for collab in collaborators:
                    self.rate_limiter.wait_if_needed()
                    
                    collab_data = {
                        'login': collab.login,
                        'id': collab.id,
                        'type': collab.type,
                        'permissions': collab.permissions.raw_data if hasattr(collab, 'permissions') else None,
                        'site_admin': collab.site_admin if hasattr(collab, 'site_admin') else None
                    }
                    
                    # Try to get more details
                    try:
                        user = self.github.get_user(collab.login)
                        collab_data['name'] = user.name
                        collab_data['email'] = user.email
                        collab_data['company'] = user.company
                        collab_data['blog'] = user.blog
                        collab_data['bio'] = user.bio
                        collab_data['public_repos'] = user.public_repos
                        collab_data['followers'] = user.followers
                        collab_data['created_at'] = user.created_at.isoformat() if user.created_at else None
                    except Exception as e:
                        logger.debug(f"Could not get full user details for {collab.login}: {e}")
                    
                    collaborators_data['collaborators'].append(collab_data)
                
                logger.info(f"Found {len(collaborators_data['collaborators'])} collaborators")
            except Exception as e:
                logger.warning(f"Could not get collaborators (may require admin access): {e}")
            
            # Get contributors (who has contributed)
            logger.info("Collecting repository contributors...")
            try:
                contributors = self.repo.get_contributors()
                contributor_logins = set()
                
                for contrib in contributors:
                    self.rate_limiter.wait_if_needed()
                    
                    if contrib.login in contributor_logins:
                        continue
                    contributor_logins.add(contrib.login)
                    
                    contrib_data = {
                        'login': contrib.login,
                        'id': contrib.id,
                        'contributions': contrib.contributions,
                        'type': contrib.type,
                        'site_admin': contrib.site_admin if hasattr(contrib, 'site_admin') else None
                    }
                    
                    # Try to get more details
                    try:
                        user = self.github.get_user(contrib.login)
                        contrib_data['name'] = user.name
                        contrib_data['email'] = user.email
                        contrib_data['company'] = user.company
                        contrib_data['blog'] = user.blog
                        contrib_data['bio'] = user.bio
                        contrib_data['public_repos'] = user.public_repos
                        contrib_data['followers'] = user.followers
                        contrib_data['created_at'] = user.created_at.isoformat() if user.created_at else None
                    except Exception as e:
                        logger.debug(f"Could not get full user details for {contrib.login}: {e}")
                    
                    collaborators_data['contributors'].append(contrib_data)
                    
                    # Limit to top 100 contributors to avoid rate limits
                    if len(collaborators_data['contributors']) >= 100:
                        logger.info("Limiting to top 100 contributors")
                        break
                
                logger.info(f"Found {len(collaborators_data['contributors'])} contributors")
            except Exception as e:
                logger.warning(f"Could not get contributors: {e}")
            
            # Try to get organization members (if repository is in an org)
            logger.info("Checking for organization members...")
            try:
                org = self.github.get_organization(self.repo_owner)
                members = org.get_members()
                
                member_logins = set()
                for member in members:
                    self.rate_limiter.wait_if_needed()
                    
                    if member.login in member_logins:
                        continue
                    member_logins.add(member.login)
                    
                    member_data = {
                        'login': member.login,
                        'id': member.id,
                        'type': member.type,
                        'site_admin': member.site_admin if hasattr(member, 'site_admin') else None
                    }
                    
                    collaborators_data['organization_members'].append(member_data)
                    
                    # Limit to avoid rate limits
                    if len(collaborators_data['organization_members']) >= 50:
                        logger.info("Limiting organization members collection")
                        break
                
                logger.info(f"Found {len(collaborators_data['organization_members'])} organization members")
            except Exception as e:
                logger.debug(f"Could not get organization members (may not be in org or no access): {e}")
            
            # Save data
            output_file = self.data_dir / "collaborators.json"
            with open(output_file, 'w') as f:
                json.dump(collaborators_data, f, indent=2)
            
            logger.info(f"Saved collaborators data to {output_file}")
            
            # Generate summary
            self._generate_summary(collaborators_data)
            
        except Exception as e:
            logger.error(f"Error collecting collaborators: {e}")
            import traceback
            logger.debug(traceback.format_exc())
    
    def _generate_summary(self, data: Dict[str, Any]):
        """Generate summary of collected data."""
        logger.info("=== Collaborators Collection Summary ===")
        logger.info(f"Repository: {data['repository']}")
        logger.info(f"Collected at: {data['collected_at']}")
        logger.info(f"Collaborators (write access): {len(data['collaborators'])}")
        logger.info(f"Contributors: {len(data['contributors'])}")
        logger.info(f"Organization members: {len(data['organization_members'])}")
        
        if data['collaborators']:
            logger.info("\nCollaborators (write access):")
            for collab in data['collaborators'][:10]:  # Show first 10
                perms = collab.get('permissions', {})
                logger.info(f"  - {collab['login']}: admin={perms.get('admin', False)}, push={perms.get('push', False)}, pull={perms.get('pull', False)}")
        
        if data['contributors']:
            logger.info(f"\nTop 10 Contributors:")
            for contrib in sorted(data['contributors'], key=lambda x: x.get('contributions', 0), reverse=True)[:10]:
                logger.info(f"  - {contrib['login']}: {contrib.get('contributions', 0)} contributions")


def main():
    """Main entry point."""
    collector = GitHubCollaboratorsCollector()
    collector.collect()
    logger.info("GitHub collaborators collection complete")


if __name__ == '__main__':
    main()

