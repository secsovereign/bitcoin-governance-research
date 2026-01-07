#!/usr/bin/env python3
"""
Consolidate Findings Documents

Removes redundant documents and creates minimum viable package.
"""

import shutil
from pathlib import Path
from datetime import datetime

base_dir = Path(__file__).parent.parent
findings_dir = base_dir / 'findings'

# Documents to REMOVE (redundant or development artifacts)
DOCUMENTS_TO_REMOVE = [
    # Statistical Defense (keep only RESULTS, remove others)
    'STATISTICAL_VALIDATION_SUMMARY.md',
    'STATISTICAL_DEFENSE_COMPLETE.md',
    'STATISTICAL_DEFENSE_PLAN.md',
    'STATISTICAL_DEFENSE_IMPLEMENTATION.md',
    'STATISTICAL_DEFENSE_PLAN_VALIDATION.md',
    
    # Critical Review (keep only CRITICAL_REVIEW_ADVERSARIAL, remove others)
    'ADVERSARIAL_REVIEW_SUMMARY.md',
    'METHODOLOGY_VULNERABILITIES_AND_FIXES.md',
    'PUBLICATION_READINESS_ASSESSMENT.md',
    
    # Status/Development Documents
    'IMPLEMENTATION_COMPLETE.md',
    'PUBLICATION_PACKAGE_REVIEW.md',
    'PUBLICATION_PACKAGE_COMPLETENESS.md',
    'PUBLICATION_PACKAGE_FINAL_REVIEW.md',
    'PUBLICATION_PACKAGE_VERIFICATION.md',
    'FINAL_STATUS.md',
    'ACK_INTEGRATION_STATUS.md',
    'CONSISTENCY_AUDIT_COMPLETE.md',
    'DOCUMENT_CONSOLIDATION_PLAN.md',
    'MINIMUM_VIABLE_PACKAGE.md',  # This planning doc itself
    
    # Validation/Audit (keep only one comprehensive, remove others)
    'FINAL_VALIDATION_SUMMARY.md',
    'COMPREHENSIVE_VALIDATION_FINAL_REPORT.md',
    'DATASET_AUDIT_REPORT.md',
    'LANGUAGE_QUALITY_IMPROVEMENTS.md',
    
    # Correction Documents (if info already in methodology)
    'ACK_CORRECTION_SUMMARY.md',  # Info in methodology
    'CROSS_PLATFORM_REVIEW_IMPACT.md',  # Info in methodology
    
    # Other redundant documents
    'COMPLETE_ANALYSIS_WITH_CORRECTED_DATA.md',  # Superseded by other documents
]

# Documents to KEEP (essential)
DOCUMENTS_TO_KEEP = [
    # Primary
    'EXECUTIVE_SUMMARY.md',
    'RESEARCH_METHODOLOGY.md',
    'README.md',
    
    # Core Analysis
    'CORE_VS_COMMONS_GOVERNANCE_COMPARISON.md',
    'MERGE_PATTERN_BREAKDOWN.md',
    'TEMPORAL_ANALYSIS_REPORT.md',
    'INTERDISCIPLINARY_ANALYSIS_REPORT.md',
    'NOVEL_INTERPRETATIONS.md',
    'GLOSSARY_AND_CONTEXT.md',
    
    # Supporting Analysis
    'GINI_COEFFICIENT_EXPLANATION.md',
    'PR_IMPORTANCE_ANALYSIS.md',
    'REVIEW_QUALITY_ENHANCED_ANALYSIS.md',
    'ENHANCED_FUNDING_ANALYSIS_REPORT.md',
    'MAINTAINER_TIMELINE_ANALYSIS.md',
    'CONTRIBUTOR_TIMELINE_ANALYSIS.md',
    'EXTERNAL_RESEARCH_COMPARISON.md',
    
    # Validation (keep comprehensive ones)
    'CRITICAL_REVIEW_ADVERSARIAL.md',
    'STATISTICAL_DEFENSE_RESULTS.md',
    
    # Supporting
    'CURRENT_VS_HISTORICAL_MAINTAINERS.md',
    'REVIEW_COUNTING_METHODOLOGY.md',  # Keep if unique
    'LIMITATIONS_AND_IMPROVEMENTS.md',  # Keep if unique
    'ACK_COMMENTS_ANALYSIS.md',  # Keep if unique analysis
    'REVIEW_COVERAGE_INVESTIGATION.md',  # Keep if unique
    'ANALYSIS_VALIDATION_REPORT.md',  # Keep if comprehensive
]

def backup_before_removal():
    """Create backup of findings before removal."""
    backup_dir = base_dir / 'findings_backup'
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    shutil.copytree(findings_dir, backup_dir)
    print(f"✅ Backup created: {backup_dir}")

def remove_redundant_documents():
    """Remove redundant documents."""
    removed = []
    kept = []
    
    for doc in DOCUMENTS_TO_REMOVE:
        doc_path = findings_dir / doc
        if doc_path.exists():
            doc_path.unlink()
            removed.append(doc)
            print(f"  ❌ Removed: {doc}")
        else:
            print(f"  ⚠️  Not found: {doc}")
    
    for doc in DOCUMENTS_TO_KEEP:
        doc_path = findings_dir / doc
        if doc_path.exists():
            kept.append(doc)
        else:
            print(f"  ⚠️  Expected but missing: {doc}")
    
    return removed, kept

def update_readme():
    """Update README to reflect new structure."""
    readme_path = findings_dir / 'README.md'
    if not readme_path.exists():
        return
    
    # Read current README
    with open(readme_path) as f:
        content = f.read()
    
    # Remove references to deleted documents
    for doc in DOCUMENTS_TO_REMOVE:
        # Remove lines containing the document name
        lines = content.split('\n')
        content = '\n'.join([line for line in lines if doc not in line])
    
    # Write updated README
    with open(readme_path, 'w') as f:
        f.write(content)
    
    print(f"✅ Updated README.md")

def main():
    """Main entry point."""
    print("="*80)
    print("CONSOLIDATING FINDINGS DOCUMENTS")
    print("="*80)
    print()
    
    # Create backup
    print("Creating backup...")
    backup_before_removal()
    print()
    
    # Remove redundant documents
    print("Removing redundant documents...")
    removed, kept = remove_redundant_documents()
    print()
    
    # Update README
    print("Updating README...")
    update_readme()
    print()
    
    # Summary
    print("="*80)
    print("CONSOLIDATION COMPLETE")
    print("="*80)
    print(f"Removed: {len(removed)} documents")
    print(f"Kept: {len(kept)} documents")
    print()
    print("Removed documents:")
    for doc in removed:
        print(f"  - {doc}")
    print()
    print("Backup location: findings_backup/")
    print("="*80)

if __name__ == '__main__':
    main()
