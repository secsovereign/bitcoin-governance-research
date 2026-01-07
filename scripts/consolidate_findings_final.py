#!/usr/bin/env python3
"""
Final Consolidation: Remove All Redundant Documents

Removes documents that are:
1. Redundant summaries/status documents
2. Duplicate explanations of same concepts
3. Correction documents (info already in methodology)
4. Multiple documents explaining same thing
"""

import shutil
from pathlib import Path

base_dir = Path(__file__).parent.parent
findings_dir = base_dir / 'findings'

# Additional documents to REMOVE (redundant explanations, corrections, duplicates)
ADDITIONAL_REMOVE = [
    # Review-related (keep only REVIEW_QUALITY_ENHANCED_ANALYSIS.md and REVIEW_COUNTING_METHODOLOGY.md if unique)
    'REVIEW_COUNTING_FIX.md',  # Correction - info in methodology
    'REVIEW_QUALITY_WEIGHTING.md',  # Explanation - info in methodology
    'REVIEW_QUALITY_ANALYSIS.md',  # Redundant with REVIEW_QUALITY_ENHANCED_ANALYSIS.md
    'QUALITY_WEIGHTED_REVIEW_SUMMARY.md',  # Summary - redundant
    'REVIEW_QUALITY_DISTRIBUTION_TWEET.md',  # Tweet - not research content
    
    # Multiple reviews (keep only one explanation)
    'MULTIPLE_REVIEWS_EXPLANATION.md',  # Explanation
    'MULTIPLE_REVIEWS_PER_REVIEWER.md',  # Duplicate explanation
    
    # ACK-related (info in methodology)
    'ACK_COMMENTS_ANALYSIS.md',  # Analysis - info in methodology
    'ACK_TIMELINE_ANALYSIS.md',  # Timeline - info in methodology
    
    # Cross-platform (info in methodology)
    'CROSS_PLATFORM_REVIEW_ANALYSIS.md',  # Analysis - info in methodology
    'CROSS_PLATFORM_INTEGRATION_COMPLETE.md',  # Status doc
    
    # Correction tweets (not research content)
    'CORRECTION_TWEET.md',
    'CORRECTION_TWEET_QUALITY_WEIGHTED.md',
    
    # GitHub reviews update (info in methodology)
    'GITHUB_REVIEWS_SEPT_2016_UPDATE.md',  # Update doc - info in methodology
    
    # Funding (keep only ENHANCED version)
    'FUNDING_ANALYSIS.md',  # Basic version - redundant with ENHANCED
    
    # Quick insights (redundant with executive summary)
    'QUICK_INSIGHTS_COMPLETE.md',
    
    # Talking points (not research content)
    'CORE_VS_COMMONS_TALKING_POINTS.md',
    
    # Opportunities (future work, not findings)
    'INTERDISCIPLINARY_ANALYSIS_OPPORTUNITIES.md',
    
    # Validation (keep only one comprehensive)
    'ANALYSIS_VALIDATION_REPORT.md',  # Keep this one
    'COMPREHENSIVE_DATASET_VALIDATION.md',  # Remove - redundant
    'CONTRIBUTOR_TIMELINE_VALIDATION.md',  # Validation doc
    
    # Language/Quality (already applied)
    'LANGUAGE_AND_QUALITY_AUDIT.md',  # Audit doc
    'LANGUAGE_QUALITY_AUDIT_REPORT.md',  # Report
    'QUALITY_IMPROVEMENT_SUMMARY.md',  # Summary
    
    # Data cleanup/status
    'ACCURACY_VERIFICATION.md',  # Verification doc
    'DATA_CLEANUP_SUMMARY.md',  # Cleanup summary
    'DATA_INTEGRATION_STATUS.md',  # Status doc
    'STALE_DATA_REMOVAL.md',  # Removal doc
    
    # Other
    'governance_timeline_report.md',  # Lowercase, likely duplicate
]

def main():
    """Remove additional redundant documents."""
    print("="*80)
    print("FINAL CONSOLIDATION: Removing Additional Redundant Documents")
    print("="*80)
    print()
    
    removed = []
    
    for doc in ADDITIONAL_REMOVE:
        doc_path = findings_dir / doc
        if doc_path.exists():
            doc_path.unlink()
            removed.append(doc)
            print(f"  ❌ Removed: {doc}")
        else:
            print(f"  ⚠️  Not found: {doc}")
    
    print()
    print("="*80)
    print(f"Removed {len(removed)} additional redundant documents")
    print("="*80)
    
    # Show final count
    remaining = len(list(findings_dir.glob('*.md')))
    print(f"\nRemaining documents: {remaining}")
    print()

if __name__ == '__main__':
    main()
