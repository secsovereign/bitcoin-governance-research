#!/usr/bin/env python3
"""
Prepare Publication Package

Creates a clean publication-ready package by:
1. Excluding development artifacts (planning docs, status markers)
2. Excluding Python artifacts (__pycache__, *.pyc)
3. Excluding backup files
4. Keeping only essential research files
"""

import shutil
from pathlib import Path
from datetime import datetime

base_dir = Path(__file__).parent.parent
pub_dir = base_dir / 'publication-package'

# Files/directories to EXCLUDE
EXCLUDE_PATTERNS = [
    # Python artifacts
    '__pycache__',
    '*.pyc',
    '*.pyo',
    '*.pyd',
    
    # Development artifacts
    'backups',
    'commons-research',  # Nested directory
    '.git',
    '.vscode',
    '.idea',
    
    # Old ZIP files (keep only latest)
    'bitcoin_core_governance_*_20251214.zip',
    'bitcoin_core_governance_analysis_*.zip',
    
    # Large raw data (samples included instead)
    'data/github/prs_raw.jsonl',
    'data/github/issues_raw.jsonl',
    'data/github/commits_raw.jsonl',
    'data/irc/messages.jsonl',  # Full file, sample included
    'data/mailing_lists/emails.jsonl',  # Full file, sample included
]

# Planning/status documents to EXCLUDE (development artifacts)
PLANNING_DOCS = [
    'CORE_VS_COMMONS_GOVERNANCE_COMPARISON.md',  # Removed from publication per user request
    'ANALYSIS_PLAN.md',
    'PROJECT_STATUS.md',
    'EXECUTION_PLAN.md',
    'COLLECTION_STATUS.md',
    'ANALYSIS_COMPLETE.md',
    'EXECUTION_COMPLETE.md',
    'FOUNDATION_COMPLETE.md',
    'IMPLEMENTATION_GUIDE.md',
    'VALIDATION_PLAN.md',
    'DATA_REQUIREMENTS_ANALYSIS.md',
    'COLLECTION_PRIORITY.md',
    'ANALYSIS_SCRIPTS_COMPLETE.md',
    'READY_TO_EXECUTE.md',
    'EXECUTION_READINESS.md',
    'PACKAGE_VALIDATION.md',
    'PLAN_VALIDATION.md',
    'IMPLEMENTATION_VALIDATION_COMPLETE.md',
    'NEW_DATA_INTEGRATION_STATUS.md',
    'NEW_DATA_INTEGRATION_COMPLETE.md',
    'DATA_INTEGRATION_SUMMARY.md',
    'COLLECTION_IN_PROGRESS.md',
    'CURRENT_COLLECTION_STATUS.md',
    'DATA_COMPLETENESS_SUMMARY.md',
    'DATA_CONSISTENCY_CHECK.md',
    'DATA_OPTIMIZATION_AND_DEFENSIBILITY.md',
    'DATA_ORGANIZATION.md',
    'DATA_SYNTHESIS.md',
    'DOCUMENT_CONSOLIDATION_PLAN.md',
    'EXECUTION_PROGRESS.md',
    'FOUNDATION_STATUS.md',
    'FUNDING_ANALYSIS_PLAN.md',
    'HIGH_IMPACT_IMPROVEMENTS.md',
    'MASTER_INDEX.md',
    'OPPOSITIONAL_SYNTHESIS.md',
    'PATTERN_DEMONSTRATION_STRATEGY.md',
    'PR_REVIEW_QUALITY_ANALYSIS_PLAN.md',
    'QUICK_WINS_IMLEMENTED.md',
    'RATE_LIMIT_STATUS.md',
    'REORGANIZATION_PLAN.md',
    'STATUS.md',
    'STATUS_UPDATE.md',
    'USER_IDENTITY_PLAN.md',
    'VALIDATION_AND_ORGANIZATION_SUMMARY.md',
    'VALIDATION_SUMMARY.md',
    'COLLECTOR_STATUS.md',
    'RESULTS_PATHS.md',
]

# Files to KEEP (essential research)
KEEP_FILES = [
    'README.md',
    'LICENSE',
    'DATA_SOURCING_AND_REPRODUCIBILITY.md',
    'comprehensive_recent_analysis.py',
    'pyproject.toml',
    'setup.sh',
    'CHANGELOG.md',
    'QUICK_START.md',  # May be useful
    'GITHUB_TOKEN_SETUP.md',  # May be useful for reproducibility
]

# Optional files (review case-by-case)
OPTIONAL_FILES = [
    'TWEET_CORRECTION.md',
    'TWEET_FINAL.md',
    'TWEET_IMPROVEMENTS_AND_ANALYSIS.md',
    'TWEET_UPDATE.md',
    'TWEET_SELF_MERGE_REFRAMED.md',
    'calculate_gini.py',
    'check_nack_timeline.py',
    'check_open_prs.py',
    'check_release_signers.py',
    'check_trusted_signers.py',
    'temporal_analysis.py',
    'verify_claims.py',
    'verify_counter_claims.py',
    'verify_open_pr_wait_times.py',
    'validate_signer_extraction.py',
    'FINAL_REPORT_2025.md',
    'FINAL_REPORT_2025.txt',
    'FINAL_VALIDATION_REPORT.md',
    'GUILD_CHARACTERIZATION_ANALYSIS.md',
    'MERGE_ANALYSIS_STRUCTURAL_PATTERNS.md',
    'MERGE_BREAKDOWN.md',
    'SELF_MERGE_CORRECTION.md',
    'SELF_MERGE_OVERVIEW.md',
    'SELF_MERGE_VALIDATION_ERROR.md',
    'SELF_MERGE_VERIFICATION.md',
    'SIGNER_COUNT_DISCREPANCY_ANALYSIS.md',
    'SIGNER_DATA_VALIDATION_SUMMARY.md',
    'SIGNER_EXTRACTION_VALIDATION.md',
    'RELEASE_DATA_VERIFICATION.md',
    'RELEASE_SIGNER_CORRECTION.md',
    'RESPONSE_TIME_EXPLANATION.md',
    'RECONCILIATION_SUMMARY.md',
    'COMPELLING_SYNTHESIS.md',
    'COMPLETENESS_CHECK.md',
    'FAIRNESS_AND_OBJECTIVITY_ASSESSMENT.md',
    'FINAL_RELEASE_CHECKLIST.md',
    'FINAL_RELEASE_VALIDATION.md',
    'TECHNICAL_NOTES.md',
    'TEST_VALIDATION_REPORT.md',
    'TOP_10_CONTROL_EXPLANATION.md',
    'SCRIPT_VALIDATION_REPORT.md',
    'EASY_DATA_COLLECTION.md',
    'ERROR_ANALYSIS.md',
    'COLLECTED_DATA_INVENTORY.md',
    'DATA_SOURCES_SUMMARY.md',
    'METHODOLOGY.md',
    'MAILING_LIST_NOTE.md',
    'BACKFILL_MERGED_BY_INSTRUCTIONS.md',
    'ADDENDUM_FILES_LIST.md',
    'ADDENDUM_README.md',
]

def should_exclude(filepath: Path) -> bool:
    """Check if file should be excluded."""
    name = filepath.name
    path_str = str(filepath)
    
    # Check planning docs
    if name in PLANNING_DOCS:
        return True
    
    # Check Python artifacts
    if filepath.is_dir() and name == '__pycache__':
        return True
    if name.endswith('.pyc') or name.endswith('.pyo') or name.endswith('.pyd'):
        return True
    
    # Check excluded directories
    if name in ['backups', 'commons-research', '.git', '.vscode', '.idea']:
        return True
    
    # Check old ZIP files
    if name.startswith('bitcoin_core_governance_') and '20251214' in name:
        return True
    if name.startswith('bitcoin_core_governance_analysis_'):
        return True
    
    # Check large raw data files (samples included instead)
    large_data_files = [
        'data/github/prs_raw.jsonl',
        'data/github/issues_raw.jsonl',
        'data/github/commits_raw.jsonl',
        'data/irc/messages.jsonl',
        'data/mailing_lists/emails.jsonl',
    ]
    # Convert to relative path for comparison
    try:
        rel_path = filepath.relative_to(base_dir)
        if str(rel_path) in large_data_files:
            return True
    except ValueError:
        pass  # Not relative to base_dir, skip
    
    return False

def should_keep(filepath: Path) -> bool:
    """Check if file should definitely be kept."""
    name = filepath.name
    
    # Always keep these
    if name in KEEP_FILES:
        return True
    
    # Always keep findings/
    if 'findings' in str(filepath):
        return True
    
    # Always keep scripts/
    if 'scripts' in str(filepath):
        return True
    
    # Always keep critical data
    if 'merged_by_mapping.jsonl' in str(filepath):
        return True
    if 'samples' in str(filepath):
        return True
    if 'maintainers' in str(filepath):
        return True
    if 'processed' in str(filepath) and filepath.suffix == '.json':
        return True
    
    # Keep latest ZIP
    if name.startswith('bitcoin_core_governance_FULL_20251217.zip'):
        return True
    if name.startswith('bitcoin_core_governance_addendum_20251217.zip'):
        return True
    
    return False

def copy_tree(src: Path, dst: Path, organize_findings: bool = False):
    """Copy directory tree, excluding unwanted files."""
    if src.is_file():
        if should_exclude(src):
            return False
        if should_keep(src):
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            return True
        # Check if optional (review case-by-case)
        if src.name in OPTIONAL_FILES:
            # Include optional files for now (can be removed later)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            return True
        # Exclude everything else in root
        if src.parent == base_dir and src.suffix == '.md':
            return False  # Exclude root markdown files not in KEEP or OPTIONAL
        
        # Organize findings directory: JSON files go to data/ subdirectory
        if organize_findings and src.parent.name == 'findings' and src.suffix == '.json':
            # JSON files go to findings/data/
            data_dir = dst.parent / 'data'
            data_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, data_dir / src.name)
            return True
        
        # Include everything else
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return True
    
    if src.is_dir():
        if should_exclude(src):
            return False
        
        # Special handling for findings directory
        if src.name == 'findings' and organize_findings:
            dst.mkdir(parents=True, exist_ok=True)
            # Create data subdirectory for JSON files
            data_dir = dst / 'data'
            data_dir.mkdir(parents=True, exist_ok=True)
            
            for item in src.iterdir():
                if item.is_file() and item.suffix == '.json':
                    # Copy JSON files to data/ subdirectory
                    shutil.copy2(item, data_dir / item.name)
                elif item.is_dir():
                    # Copy subdirectories (like archive/) normally
                    copy_tree(item, dst / item.name, organize_findings=False)
                elif item.name == 'CORE_VS_COMMONS_GOVERNANCE_COMPARISON.md':
                    # Skip Commons doc - removed from publication
                    continue
                else:
                    # Copy markdown and other files to findings root
                    shutil.copy2(item, dst / item.name)
            return True
        
        dst.mkdir(parents=True, exist_ok=True)
        for item in src.iterdir():
            copy_tree(item, dst / item.name, organize_findings=organize_findings if src.name != 'findings' else False)
        return True
    
    return False

def main():
    """Create clean publication package."""
    print("="*80)
    print("PREPARING PUBLICATION PACKAGE")
    print("="*80)
    print()
    
    # Remove existing publication directory
    if pub_dir.exists():
        print(f"Removing existing {pub_dir}...")
        shutil.rmtree(pub_dir)
    
    pub_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy essential directories
    print("Copying essential directories...")
    essential_dirs = ['findings', 'scripts', 'data', 'src', 'tests']
    for dirname in essential_dirs:
        src_dir = base_dir / dirname
        if src_dir.exists():
            print(f"  Copying {dirname}/...")
            # Organize findings directory (JSON files to data/ subdirectory)
            copy_tree(src_dir, pub_dir / dirname, organize_findings=(dirname == 'findings'))
    
    # Copy essential files
    print("Copying essential files...")
    for filename in KEEP_FILES:
        src_file = base_dir / filename
        if src_file.exists():
            print(f"  Copying {filename}...")
            shutil.copy2(src_file, pub_dir / filename)
    
    # Copy main analysis script
    main_script = base_dir / 'comprehensive_recent_analysis.py'
    if main_script.exists():
        print("  Copying comprehensive_recent_analysis.py...")
        shutil.copy2(main_script, pub_dir / main_script.name)
    
    # Create exclusion list document
    exclusion_list = pub_dir / 'EXCLUDED_FILES.md'
    with open(exclusion_list, 'w') as f:
        f.write("# Excluded Files from Publication\n\n")
        f.write("**Date**: 2026-01-07\n\n")
        f.write("This document lists files excluded from the publication package.\n\n")
        f.write("## Excluded Categories\n\n")
        f.write("### 1. Planning/Status Documents (Development Artifacts)\n\n")
        for doc in PLANNING_DOCS:
            f.write(f"- `{doc}`\n")
        f.write("\n### 2. Python Artifacts\n\n")
        f.write("- All `__pycache__/` directories\n")
        f.write("- All `*.pyc` files\n")
        f.write("\n### 3. Backup Files\n\n")
        f.write("- `backups/` directory\n")
        f.write("\n### 4. Old ZIP Files\n\n")
        f.write("- `bitcoin_core_governance_*_20251214.zip` (old versions)\n")
        f.write("- `bitcoin_core_governance_analysis_*.zip` (old versions)\n")
        f.write("\n### 5. Large Raw Data Files\n\n")
        f.write("- `data/github/prs_raw.jsonl` (230MB - can be regenerated)\n")
        f.write("- `data/github/issues_raw.jsonl` (50MB - can be regenerated)\n")
        f.write("- `data/irc/messages.jsonl` (99MB - sample included instead)\n")
        f.write("- `data/mailing_lists/emails.jsonl` (54MB - sample included instead)\n")
        f.write("\n### 6. Nested Directory\n\n")
        f.write("- `commons-research/commons-research/` (copy error)\n")
    
    print()
    print("="*80)
    print("PUBLICATION PACKAGE CREATED")
    print("="*80)
    print(f"Location: {pub_dir.absolute()}")
    print()
    print("Package includes:")
    print("  ✅ All findings/ documents")
    print("  ✅ All scripts/")
    print("  ✅ Critical data files")
    print("  ✅ Essential documentation")
    print("  ✅ Latest ZIP packets")
    print()
    print("Package excludes:")
    print("  ❌ Planning/status documents (50+ files)")
    print("  ❌ Python artifacts (__pycache__)")
    print("  ❌ Backup files")
    print("  ❌ Old ZIP files")
    print("  ❌ Large raw data (samples included)")
    print()
    print("Review optional files in publication package if needed.")
    print("="*80)

if __name__ == '__main__':
    main()
