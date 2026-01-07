#!/usr/bin/env python3
"""
Quick script to check if GitHub token is configured correctly.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def check_token():
    """Check if GitHub token is set and valid."""
    token = os.getenv('GITHUB_TOKEN')
    
    print("GitHub Token Status Check")
    print("=" * 50)
    
    if not token:
        print("❌ GITHUB_TOKEN not set")
        print("\nTo set it:")
        print("1. Edit .env file in project root")
        print("2. Add: GITHUB_TOKEN=your_token_here")
        print("3. Get token from: https://github.com/settings/tokens")
        return False
    
    if token == "your_github_token_here":
        print("⚠️  GITHUB_TOKEN is set to placeholder value")
        print("\nPlease edit .env and replace with your actual token")
        print("Get token from: https://github.com/settings/tokens")
        return False
    
    # Check token format
    if not (token.startswith('ghp_') or token.startswith('gho_') or 
            token.startswith('ghu_') or token.startswith('ghs_')):
        print(f"⚠️  Token format looks unusual (starts with: {token[:4]})")
        print("   Most tokens start with 'ghp_'")
    
    print(f"✓ GITHUB_TOKEN is set")
    print(f"  Token preview: {token[:10]}...{token[-4:]}")
    print(f"  Length: {len(token)} characters")
    
    # Test token with API
    try:
        from github import Github
        github = Github(token)
        
        # Try to get rate limit (this validates the token)
        # Just accessing get_rate_limit() validates the token
        # The API structure varies by PyGithub version, so we'll just confirm it works
        rate_limit = github.get_rate_limit()
        
        print(f"\n✓ Token is valid!")
        print(f"  Rate limit object retrieved successfully")
        
        # Try to get rate limit info (structure varies by PyGithub version)
        try:
            if hasattr(rate_limit, 'core') and hasattr(rate_limit.core, 'remaining'):
                print(f"  Core API: {rate_limit.core.remaining}/{rate_limit.core.limit} requests remaining")
                if rate_limit.core.remaining < 100:
                    print("  ⚠️  Low rate limit remaining - may need to wait")
        except:
            pass
        
        return True
        
    except Exception as e:
        print(f"\n❌ Token validation failed: {e}")
        print("   Token may be invalid or expired")
        print("   Get a new token from: https://github.com/settings/tokens")
        return False

if __name__ == '__main__':
    success = check_token()
    sys.exit(0 if success else 1)

