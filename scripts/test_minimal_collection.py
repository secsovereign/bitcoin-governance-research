#!/usr/bin/env python3
"""
Minimal test of data collection - collects just a few PRs to validate the system.

This is a safe test that won't hit rate limits or take long.
"""

import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import config
from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir

logger = setup_logger("test_collection", "INFO")

def test_github_connection():
    """Test GitHub API connection with minimal data."""
    logger.info("Testing GitHub API connection...")
    
    try:
        from github import Github
        import os
        
        token = config.get('data_collection.github.token') or os.getenv('GITHUB_TOKEN')
        repo_owner = config.get('data_collection.github.repository.owner', 'bitcoin')
        repo_name = config.get('data_collection.github.repository.name', 'bitcoin')
        
        if token:
            github = Github(token)
            logger.info("Using authenticated GitHub API")
        else:
            github = Github()
            logger.info("Using unauthenticated GitHub API (rate limited)")
        
        repo = github.get_repo(f"{repo_owner}/{repo_name}")
        logger.info(f"✓ Connected to {repo_owner}/{repo_name}")
        logger.info(f"  Repository: {repo.full_name}")
        logger.info(f"  Description: {repo.description[:60]}...")
        
        # Get just the first PR to test
        prs = repo.get_pulls(state='all', sort='created', direction='desc')
        first_pr = prs[0]
        
        logger.info(f"✓ Retrieved test PR: #{first_pr.number} - {first_pr.title[:50]}")
        logger.info(f"  State: {first_pr.state}, Created: {first_pr.created_at}")
        
        # Test rate limit status (structure varies by PyGithub version)
        rate_limit = github.get_rate_limit()
        logger.info(f"✓ Rate limit status retrieved")
        try:
            if hasattr(rate_limit, 'core') and hasattr(rate_limit.core, 'remaining'):
                logger.info(f"  Core API: {rate_limit.core.remaining}/{rate_limit.core.limit} requests remaining")
                if hasattr(rate_limit, 'search') and hasattr(rate_limit.search, 'remaining'):
                    logger.info(f"  Search API: {rate_limit.search.remaining}/{rate_limit.search.limit} requests remaining")
        except Exception as e:
            logger.debug(f"  Rate limit details unavailable (API structure may vary): {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ GitHub connection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_minimal_pr_collection():
    """Collect just 3 PRs to test the full pipeline."""
    logger.info("\nTesting minimal PR collection (3 PRs)...")
    
    try:
        from github import Github
        from src.utils.rate_limiter import RateLimiter
        import os
        
        token = config.get('data_collection.github.token') or os.getenv('GITHUB_TOKEN')
        repo_owner = config.get('data_collection.github.repository.owner', 'bitcoin')
        repo_name = config.get('data_collection.github.repository.name', 'bitcoin')
        
        if token:
            github = Github(token)
            rate_limiter = RateLimiter(max_calls=4500, time_window=3600)  # 90% of 5000
        else:
            github = Github()
            rate_limiter = RateLimiter(max_calls=54, time_window=3600)  # 90% of 60
        
        repo = github.get_repo(f"{repo_owner}/{repo_name}")
        
        # Output directory
        data_dir = get_data_dir()
        test_dir = data_dir / 'github' / 'test'
        test_dir.mkdir(parents=True, exist_ok=True)
        test_file = test_dir / 'test_prs.jsonl'
        
        # Get 3 most recent PRs
        prs = repo.get_pulls(state='all', sort='created', direction='desc')
        
        collected = []
        for i, pr in enumerate(prs[:3]):
            rate_limiter.wait_if_needed()
            
            pr_data = {
                'number': pr.number,
                'title': pr.title,
                'state': pr.state,
                'created_at': pr.created_at.isoformat() if pr.created_at else None,
                'author': pr.user.login if pr.user else None,
            }
            
            collected.append(pr_data)
            logger.info(f"  Collected PR #{pr.number}: {pr.title[:50]}")
        
        # Write to file
        with open(test_file, 'w') as f:
            for pr_data in collected:
                f.write(json.dumps(pr_data) + '\n')
        
        logger.info(f"✓ Collected {len(collected)} PRs to {test_file}")
        logger.info(f"  File size: {test_file.stat().st_size} bytes")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Minimal collection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run minimal collection tests."""
    logger.info("=" * 60)
    logger.info("Minimal Data Collection Test")
    logger.info("=" * 60)
    
    # Test 1: Connection
    if not test_github_connection():
        logger.error("Connection test failed. Cannot proceed.")
        return 1
    
    # Test 2: Minimal collection
    if not test_minimal_pr_collection():
        logger.error("Collection test failed.")
        return 1
    
    logger.info("=" * 60)
    logger.info("✓ All tests passed! Data collection system is working.")
    logger.info("=" * 60)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())

