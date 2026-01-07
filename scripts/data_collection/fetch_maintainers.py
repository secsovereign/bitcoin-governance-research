#!/usr/bin/env python3
"""
Fetch Current Maintainers from Bitcoin Core Repository

Fetches the MAINTAINERS file from the Bitcoin Core repository and extracts
the current list of maintainers. Can also track maintainer history if needed.
"""

import json
import sys
import base64
from pathlib import Path
from typing import List, Dict, Any, Set
from datetime import datetime

try:
    from github import Github
except ImportError:
    print("ERROR: PyGithub not installed. Install with: pip install PyGithub")
    sys.exit(1)

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class MaintainerFetcher:
    """Fetch and parse maintainers from Bitcoin Core repository."""
    
    def __init__(self, github_token: str = None):
        """Initialize maintainer fetcher."""
        self.github_token = github_token
        self.repo_name = "bitcoin/bitcoin"
        
        if github_token:
            self.github = Github(github_token)
        else:
            self.github = Github()  # Unauthenticated (rate limited)
    
    def fetch_maintainers_file(self) -> str:
        """Fetch MAINTAINERS file content from repository."""
        # Bitcoin Core may not have a MAINTAINERS file
        # Try multiple possible locations
        possible_paths = ["MAINTAINERS", "doc/MAINTAINERS", ".github/MAINTAINERS"]
        
        for path in possible_paths:
            try:
                repo = self.github.get_repo(self.repo_name)
                file = repo.get_contents(path)
                
                # Decode base64 content
                content = base64.b64decode(file.content).decode('utf-8')
                print(f"Found MAINTAINERS file at: {path}")
                return content
            except Exception as e:
                continue
        
        # If no MAINTAINERS file, try to get from GitHub API
        # Get users with write access to the repository
        try:
            repo = self.github.get_repo(self.repo_name)
            # Get collaborators with write access
            collaborators = repo.get_collaborators(affiliation='direct')
            maintainers = []
            for collab in collaborators:
                # Check if they have write or admin access
                # Note: This requires appropriate permissions
                maintainers.append(collab.login)
            
            if maintainers:
                print(f"Found {len(maintainers)} collaborators with write access")
                # Format as maintainers list
                content = "\n".join([f"@{m}" for m in maintainers])
                return content
        except Exception as e:
            print(f"Could not fetch collaborators: {e}")
        
        print("Warning: Could not find MAINTAINERS file or fetch collaborators")
        return None
    
    def parse_maintainers(self, content: str) -> Dict[str, Any]:
        """Parse MAINTAINERS file to extract maintainer list."""
        if not content:
            return None
        
        maintainers = {
            'usernames': set(),
            'emails': set(),
            'by_category': {},
            'raw_content': content,
            'fetched_at': datetime.now().isoformat()
        }
        
        lines = content.split('\n')
        current_category = None
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # Check for category headers (e.g., "General", "QA", "Build")
            if line.isupper() or (line and not line.startswith(' ') and ':' not in line):
                current_category = line
                maintainers['by_category'][current_category] = []
                continue
            
            # Parse maintainer entries
            # Format is typically: "Name <email> (@username)"
            # Or just: "@username"
            if '@' in line:
                # Extract username
                if '(@' in line:
                    username = line.split('(@')[1].split(')')[0].strip()
                    maintainers['usernames'].add(username.lower())
                    
                    if current_category:
                        maintainers['by_category'][current_category].append(username.lower())
                
                # Extract email if present
                if '<' in line and '>' in line:
                    email = line.split('<')[1].split('>')[0].strip()
                    maintainers['emails'].add(email)
        
        # Convert sets to sorted lists for JSON serialization
        maintainers['usernames'] = sorted(list(maintainers['usernames']))
        maintainers['emails'] = sorted(list(maintainers['emails']))
        
        return maintainers
    
    def get_current_maintainers(self) -> Dict[str, Any]:
        """Get current maintainers list."""
        print("Fetching MAINTAINERS file from Bitcoin Core repository...")
        content = self.fetch_maintainers_file()
        
        if not content:
            print("Failed to fetch MAINTAINERS file")
            return None
        
        print("Parsing maintainers...")
        maintainers = self.parse_maintainers(content)
        
        if maintainers:
            print(f"Found {len(maintainers['usernames'])} maintainers")
            print(f"Categories: {list(maintainers['by_category'].keys())}")
        
        return maintainers
    
    def save_maintainers(self, maintainers: Dict[str, Any], output_file: Path):
        """Save maintainers to JSON file."""
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(maintainers, f, indent=2)
        
        print(f"Maintainers saved to: {output_file}")
    
    def compare_with_hardcoded(self, maintainers: Dict[str, Any]) -> Dict[str, Any]:
        """Compare fetched maintainers with hardcoded list."""
        hardcoded = {
            'laanwj', 'sipa', 'maflcko', 'fanquake', 'hebasto', 'jnewbery',
            'ryanofsky', 'achow101', 'theuni', 'jonasschnelli', 'Sjors',
            'promag', 'instagibbs', 'TheBlueMatt', 'jonatack', 'gmaxwell',
            'gavinandresen', 'petertodd', 'luke-jr', 'glozow'
        }
        
        fetched_lower = {m.lower() for m in maintainers['usernames']}
        hardcoded_lower = {m.lower() for m in hardcoded}
        
        comparison = {
            'hardcoded_count': len(hardcoded),
            'fetched_count': len(fetched_lower),
            'in_hardcoded_not_fetched': sorted(list(hardcoded_lower - fetched_lower)),
            'in_fetched_not_hardcoded': sorted(list(fetched_lower - hardcoded_lower)),
            'in_both': sorted(list(fetched_lower & hardcoded_lower))
        }
        
        return comparison


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Fetch current maintainers from Bitcoin Core')
    parser.add_argument('--github-token', type=str, help='GitHub token (optional, for higher rate limits)')
    parser.add_argument('--output', type=Path, default=Path(__file__).parent.parent.parent / 'data' / 'maintainers' / 'current_maintainers.json',
                       help='Output JSON file')
    parser.add_argument('--compare', action='store_true', help='Compare with hardcoded list')
    
    args = parser.parse_args()
    
    fetcher = MaintainerFetcher(args.github_token)
    maintainers = fetcher.get_current_maintainers()
    
    if maintainers:
        fetcher.save_maintainers(maintainers, args.output)
        
        if args.compare:
            print("\n" + "="*80)
            print("COMPARISON WITH HARDCODED LIST")
            print("="*80)
            comparison = fetcher.compare_with_hardcoded(maintainers)
            
            print(f"Hardcoded count: {comparison['hardcoded_count']}")
            print(f"Fetched count: {comparison['fetched_count']}")
            print(f"In both: {len(comparison['in_both'])}")
            
            if comparison['in_hardcoded_not_fetched']:
                print(f"\nIn hardcoded but not in MAINTAINERS file ({len(comparison['in_hardcoded_not_fetched'])}):")
                for m in comparison['in_hardcoded_not_fetched']:
                    print(f"  - {m}")
            
            if comparison['in_fetched_not_hardcoded']:
                print(f"\nIn MAINTAINERS file but not in hardcoded list ({len(comparison['in_fetched_not_hardcoded'])}):")
                for m in comparison['in_fetched_not_hardcoded']:
                    print(f"  - {m}")
    else:
        print("Failed to fetch maintainers")
        sys.exit(1)


if __name__ == '__main__':
    main()
