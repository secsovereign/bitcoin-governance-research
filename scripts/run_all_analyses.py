#!/usr/bin/env python3
"""
Run all current analysis scripts in the correct order.

This script runs all core analysis scripts and generates the complete
set of analysis JSON files in analysis/findings/data/.
"""

import argparse
import sys
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

CROSS_PLATFORM_SCRIPTS = {
    "cross_platform_networks.py",
    "informal_sentiment_analysis.py",
    "identity_resolution_enhanced.py",
    "funding_analysis_consolidated.py",
    "bcap_state_of_mind.py",
    "bcap_power_shift.py",
    "language_evolution_analysis.py",
    "cross_platform_reviews.py",
}

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
    parser = argparse.ArgumentParser(description="Run Bitcoin Core governance analysis pipeline")
    parser.add_argument(
        "--cross-platform-only",
        action="store_true",
        help="Run only analyses that consume informal channels (mailing lists, IRC, Delving, Bitcointalk)",
    )
    parser.add_argument(
        "--github-only",
        action="store_true",
        help="Skip informal-channel analyses",
    )
    parser.add_argument(
        "--reports",
        action="store_true",
        help="Regenerate cross-platform markdown reports after analyses",
    )
    args = parser.parse_args()

    if args.cross_platform_only and args.github_only:
        parser.error("Use only one of --cross-platform-only or --github-only")

    print("=" * 70)
    if args.cross_platform_only:
        print("BITCOIN CORE GOVERNANCE ANALYSIS - CROSS-PLATFORM PIPELINE")
    elif args.github_only:
        print("BITCOIN CORE GOVERNANCE ANALYSIS - GITHUB/BIP PIPELINE")
    else:
        print("BITCOIN CORE GOVERNANCE ANALYSIS - FULL PIPELINE")
    print("=" * 70)
    print()
    
    scripts_dir = project_root / "scripts" / "analysis"
    data_scripts = project_root / "scripts" / "data_processing"

    prerequisite = [
        (data_scripts / "maintainer_timeline.py", "Maintainer Timeline (canonical + merged_by)"),
    ]
    
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
        ("merge_pattern_analysis.py", "Merge Pattern Analysis"),
        ("review_quality_enhanced.py", "Enhanced Review Quality"),
        ("cross_platform_reviews.py", "Cross-Platform Informal Reviews"),
        ("statistical_significance_tests.py", "Statistical Significance / CIs"),
        ("max_vs_sum_comparison.py", "MAX vs SUM Review Sensitivity"),
        ("uniform_threshold_analysis.py", "Uniform Review-Threshold Sensitivity"),
        ("maintainer_timeline_analysis.py", "Maintainer Timeline Report"),
        ("contributor_timeline_analysis.py", "Contributor Timeline Report"),
        ("temporal_analysis.py", "Temporal Analysis"),
        ("language_evolution_analysis.py", "Language Evolution"),
        ("voting_bloc_conflict_analysis.py", "Voting Bloc + Conflict"),
        ("interdisciplinary_analysis.py", "Interdisciplinary Analysis"),
        ("novel_interpretations.py", "Novel Interpretations"),
        ("complexity_correlation_analysis.py", "Complexity vs Coordination Costs"),
        ("blvm_codebase_metrics.py", "Commons Codebase Metrics"),
        ("subsystem_debt_comparison.py", "Subsystem Debt Comparison"),
        ("architectural_comparison.py", "Architectural Comparison Table"),
        ("velocity_differential.py", "Architectural Velocity Differential"),
    ]

    if args.cross_platform_only:
        prerequisite = []
        analyses = [
            item for item in analyses if item[0] in CROSS_PLATFORM_SCRIPTS
        ]
    elif args.github_only:
        analyses = [
            item for item in analyses if item[0] not in CROSS_PLATFORM_SCRIPTS
        ]

    analyses.append(("governance_frames.py", "Governance reading frames"))
    
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

    if args.reports and not failed:
        report_script = project_root / "scripts" / "reporting" / "generate_findings_reports.py"
        if report_script.exists():
            print()
            run_script(report_script, "Findings markdown reports + doc patches")
        else:
            print(f"⚠️  Report script not found: {report_script}")

    return 0 if not failed else 1

if __name__ == '__main__':
    sys.exit(main())
