#!/usr/bin/env python3
"""
Interactive workflow script for incremental validation and expansion.

Guides the user through the validation and expansion process step by step.
"""

import sys
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60)

def print_step(step_num, description):
    """Print a step description."""
    print(f"\n[Step {step_num}] {description}")
    print("-" * 60)

def run_command(cmd, description):
    """Run a command and return success status."""
    print(f"\nRunning: {description}")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Command failed with exit code {e.returncode}")
        print(e.stdout)
        print(e.stderr)
        return False
    except FileNotFoundError:
        print(f"ERROR: Command not found: {cmd[0]}")
        return False

def ask_continue(prompt="Continue? (y/n): "):
    """Ask user if they want to continue."""
    response = input(prompt).strip().lower()
    return response in ['y', 'yes', '']

def main():
    """Main workflow."""
    print_header("Bitcoin Governance Analysis - Incremental Validation Workflow")
    
    print("\nThis script will guide you through validating and expanding the project.")
    print("Each step will be validated before proceeding to the next.")
    
    if not ask_continue("\nReady to begin? (y/n): "):
        print("Exiting.")
        return 0
    
    # Step 1: Setup Validation
    print_step(1, "Validate Project Setup")
    if not run_command(
        [sys.executable, "scripts/validate_setup.py"],
        "Validating project setup"
    ):
        print("\n❌ Setup validation failed. Please fix issues before continuing.")
        return 1
    
    if not ask_continue("\n✓ Setup validation passed. Continue to connection test? (y/n): "):
        return 0
    
    # Step 2: Connection Test
    print_step(2, "Test GitHub Connection (Minimal)")
    if not run_command(
        [sys.executable, "scripts/test_minimal_collection.py"],
        "Testing GitHub API connection"
    ):
        print("\n❌ Connection test failed. Check your GitHub token and network.")
        return 1
    
    if not ask_continue("\n✓ Connection test passed. Continue to small batch collection? (y/n): "):
        return 0
    
    # Step 3: Small Batch Collection
    print_step(3, "Small Batch Collection (10 PRs)")
    print("\nThis will collect 10 PRs to validate the full collection pipeline.")
    
    if not ask_continue("Proceed with 10 PR collection? (y/n): "):
        return 0
    
    if not run_command(
        [sys.executable, "scripts/data_collection/github_collector.py", "--limit", "10", "--prs-only"],
        "Collecting 10 test PRs"
    ):
        print("\n❌ Small batch collection failed.")
        return 1
    
    # Check results
    data_dir = project_root / "data" / "github"
    prs_file = data_dir / "prs_raw.jsonl"
    
    if prs_file.exists():
        line_count = sum(1 for _ in open(prs_file))
        print(f"\n✓ Collected {line_count} PRs to {prs_file}")
        file_size = prs_file.stat().st_size
        print(f"  File size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
    else:
        print("\n❌ PR file not found. Collection may have failed.")
        return 1
    
    if not ask_continue("\n✓ Small batch successful. Continue to medium batch (100 PRs)? (y/n): "):
        return 0
    
    # Step 4: Medium Batch Collection
    print_step(4, "Medium Batch Collection (100 PRs)")
    print("\nThis will collect 100 PRs to test with a more realistic batch size.")
    
    if not ask_continue("Proceed with 100 PR collection? (y/n): "):
        return 0
    
    if not run_command(
        [sys.executable, "scripts/data_collection/github_collector.py", "--limit", "100", "--prs-only"],
        "Collecting 100 test PRs"
    ):
        print("\n❌ Medium batch collection failed.")
        return 1
    
    # Check results
    if prs_file.exists():
        line_count = sum(1 for _ in open(prs_file))
        print(f"\n✓ Collected {line_count} PRs to {prs_file}")
        file_size = prs_file.stat().st_size
        print(f"  File size: {file_size:,} bytes ({file_size/1024/1024:.1f} MB)")
    else:
        print("\n❌ PR file not found.")
        return 1
    
    print("\n" + "=" * 60)
    print("✓ Incremental Validation Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Review collected data in data/github/prs_raw.jsonl")
    print("2. If data looks good, proceed to full collection:")
    print("   python scripts/data_collection/github_collector.py")
    print("3. Then proceed to data processing and analysis")
    print("\nSee VALIDATION_PLAN.md for detailed next steps.")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())

