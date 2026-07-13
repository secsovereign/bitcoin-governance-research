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
    print("This will run maintainer timeline (if needed), then core analyses:")
    print()
    
    scripts_dir = project_root / "scripts" / "analysis"
    data_scripts = project_root / "scripts" / "data_processing"

    # Timeline is also auto-built by enrich_data.py; keep here so analyses work
    # even when enrichment was last run before the timeline repair.
    prerequisite = [
        (data_scripts / "maintainer_timeline.py", "Maintainer Timeline (canonical + merged_by)"),
    ]
    
    # Define analysis scripts in recommended order
    # (some may depend on others, though currently all are independent)
    analyses = [
        ("contributor_analysis.py", "Contributor Analysis"),
        ("maintainer_premium.py", "Maintainer Premium (identity vs merits)"),
        ("author_prep_phase23_finish.py", "Author-prep sensitivity + closed-outsider sample"),
        ("stalled_proposal_dossiers.py", "Stalled Proposal Dossiers"),
        ("bcap_state_of_mind.py", "BCAP State of Mind Analysis"),
        ("bcap_power_shift.py", "BCAP Power Shift Analysis"),
        ("bip_process_analysis.py", "BIP Process Analysis"),
        ("cross_platform_networks.py", "Cross-Platform Networks"),
        ("cross_repo_comparison.py", "Cross-Repository Comparison"),
        ("informal_sentiment_analysis.py", "Informal Sentiment Analysis"),
        ("release_signing_analysis.py", "Release Signing Analysis"),
        ("identity_resolution_enhanced.py", "Enhanced Identity Resolution"),
        ("funding_analysis_consolidated.py", "Funding Analysis"),
        # Architectural divergence (Phases 1–3); requires prior classification JSONL
        ("blvm_codebase_metrics.py", "Commons Codebase Metrics"),
        ("subsystem_debt_comparison.py", "Subsystem Debt Comparison"),
        ("architectural_comparison.py", "Architectural Comparison Table"),
        ("velocity_differential.py", "Architectural Velocity Differential"),
    ]
    
    success_count = 0
    failed = []

    for script_path, description in prerequisite:
        if not script_path.exists():
            print(f"⚠️  Warning: Script not found: {script_path}")
            failed.append(str(script_path))
            continue
        if run_script(script_path, description):
            success_count += 1
        else:
            failed.append(str(script_path))
    
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
    total = len(prerequisite) + len(analyses)
    print(f"Successful: {success_count}/{total}")
    
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

