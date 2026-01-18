#!/usr/bin/env python3
"""
Run all current analysis scripts in the correct order.

This script runs all core analysis scripts and generates the complete
set of analysis JSON files in analysis/findings/data/.
"""

import sys
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def run_script(script_path, description):
    """Run an analysis script and report results."""
    print(f"\n{'=' * 70}")
    print(f"Running: {description}")
    print(f"{'=' * 70}")
    print(f"Script: {script_path}")
    
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            check=True,
            cwd=project_root
        )
        print(f"✓ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed with exit code {e.returncode}")
        return False
    except FileNotFoundError:
        print(f"✗ Script not found: {script_path}")
        return False

def main():
    """Run all analysis scripts."""
    print("=" * 70)
    print("BITCOIN CORE GOVERNANCE ANALYSIS - FULL PIPELINE")
    print("=" * 70)
    print()
    print("This will run all 10 core analysis scripts:")
    print()
    
    scripts_dir = project_root / "scripts" / "analysis"
    
    # Define analysis scripts in recommended order
    # (some may depend on others, though currently all are independent)
    analyses = [
        ("contributor_analysis.py", "Contributor Analysis"),
        ("bcap_state_of_mind.py", "BCAP State of Mind Analysis"),
        ("bcap_power_shift.py", "BCAP Power Shift Analysis"),
        ("bip_process_analysis.py", "BIP Process Analysis"),
        ("cross_platform_networks.py", "Cross-Platform Networks"),
        ("cross_repo_comparison.py", "Cross-Repository Comparison"),
        ("informal_sentiment_analysis.py", "Informal Sentiment Analysis"),
        ("release_signing_analysis.py", "Release Signing Analysis"),
        ("identity_resolution_enhanced.py", "Enhanced Identity Resolution"),
        ("funding_analysis_consolidated.py", "Funding Analysis"),
    ]
    
    success_count = 0
    failed = []
    
    for script_name, description in analyses:
        script_path = scripts_dir / script_name
        if not script_path.exists():
            print(f"⚠️  Warning: Script not found: {script_path}")
            failed.append(script_name)
            continue
        
        if run_script(script_path, description):
            success_count += 1
        else:
            failed.append(script_name)
    
    print()
    print("=" * 70)
    print("PIPELINE SUMMARY")
    print("=" * 70)
    print(f"Successful: {success_count}/{len(analyses)}")
    
    if failed:
        print(f"Failed: {len(failed)}")
        for script in failed:
            print(f"  - {script}")
        return 1
    else:
        print("✓ All analyses completed successfully")
        print()
        print("Results saved to: analysis/findings/data/")
        return 0

if __name__ == '__main__':
    sys.exit(main())

