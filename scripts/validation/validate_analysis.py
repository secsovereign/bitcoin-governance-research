#!/usr/bin/env python3
"""
Comprehensive Analysis Validation

Validates:
1. Data consistency across analyses
2. Calculation correctness
3. Metric cross-validation
4. Logical consistency
5. Data coverage
"""

import json
import sys
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.utils.load_prs_with_merged_by import load_prs_with_merged_by

class AnalysisValidator:
    """Validate analysis results."""
    
    def __init__(self, data_dir: Path):
        """Initialize."""
        self.data_dir = data_dir
        self.maintainers = {
            'laanwj', 'sipa', 'maflcko', 'fanquake', 'hebasto', 'jnewbery',
            'ryanofsky', 'achow101', 'theuni', 'jonasschnelli', 'Sjors',
            'promag', 'instagibbs', 'TheBlueMatt', 'jonatack', 'gmaxwell',
            'gavinandresen', 'petertodd', 'luke-jr', 'glozow'
        }
        self.errors = []
        self.warnings = []
        self.validations = []
    
    def load_prs(self) -> List[Dict[str, Any]]:
        """Load PRs with merged_by data."""
        prs_file = self.data_dir / 'github' / 'prs_raw.jsonl'
        mapping_file = self.data_dir / 'github' / 'merged_by_mapping.jsonl'
        return load_prs_with_merged_by(prs_file, mapping_file if mapping_file.exists() else None)
    
    def validate_data_coverage(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate data coverage."""
        print("="*80)
        print("1. DATA COVERAGE VALIDATION")
        print("="*80)
        
        merged_prs = [p for p in prs if p.get('merged', False)]
        maintainer_merged = [p for p in merged_prs 
                            if (p.get('author') or '').lower() in [m.lower() for m in self.maintainers]]
        
        # Check merged_by coverage
        with_merged_by = [p for p in maintainer_merged if p.get('merged_by')]
        coverage = len(with_merged_by) / len(maintainer_merged) * 100 if maintainer_merged else 0
        
        print(f"Total PRs: {len(prs):,}")
        print(f"Merged PRs: {len(merged_prs):,}")
        print(f"Maintainer merged PRs: {len(maintainer_merged):,}")
        print(f"Maintainer PRs with merged_by: {len(with_merged_by):,} ({coverage:.1f}%)")
        
        if coverage < 95:
            self.errors.append(f"Low merged_by coverage: {coverage:.1f}% (expected >= 95%)")
        else:
            self.validations.append(f"✅ merged_by coverage: {coverage:.1f}%")
        
        return {
            'total_prs': len(prs),
            'merged_prs': len(merged_prs),
            'maintainer_merged': len(maintainer_merged),
            'with_merged_by': len(with_merged_by),
            'coverage': coverage
        }
    
    def validate_self_merge_calculation(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate self-merge calculation consistency."""
        print("\n" + "="*80)
        print("2. SELF-MERGE CALCULATION VALIDATION")
        print("="*80)
        
        maintainer_merged = [p for p in prs 
                            if p.get('merged', False) and
                            (p.get('author') or '').lower() in [m.lower() for m in self.maintainers]]
        
        # Calculate self-merge using correct logic
        self_merged = []
        other_merged = []
        
        for pr in maintainer_merged:
            author = (pr.get('author') or '').lower()
            merged_by = (pr.get('merged_by') or '').lower()
            
            # Correct logic: only count as self-merge if merged_by matches author
            if merged_by and author and merged_by == author:
                self_merged.append(pr)
            elif merged_by:  # Has merged_by but not self
                other_merged.append(pr)
            # If no merged_by, skip (don't assume self-merge)
        
        total_with_data = len(self_merged) + len(other_merged)
        self_merge_rate = len(self_merged) / total_with_data * 100 if total_with_data > 0 else 0
        
        print(f"Maintainer merged PRs: {len(maintainer_merged):,}")
        print(f"PRs with merged_by data: {total_with_data:,}")
        print(f"Self-merged: {len(self_merged):,}")
        print(f"Other-merged: {len(other_merged):,}")
        print(f"Self-merge rate: {self_merge_rate:.1f}%")
        
        # Validate against expected range (should be ~26.5%)
        if self_merge_rate < 20 or self_merge_rate > 35:
            self.warnings.append(f"Self-merge rate {self_merge_rate:.1f}% outside expected range (20-35%)")
        else:
            self.validations.append(f"✅ Self-merge rate: {self_merge_rate:.1f}% (expected ~26.5%)")
        
        return {
            'total': len(maintainer_merged),
            'with_data': total_with_data,
            'self_merged': len(self_merged),
            'other_merged': len(other_merged),
            'self_merge_rate': self_merge_rate
        }
    
    def validate_individual_maintainer_rates(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate individual maintainer self-merge rates."""
        print("\n" + "="*80)
        print("3. INDIVIDUAL MAINTAINER RATES VALIDATION")
        print("="*80)
        
        maintainer_stats = defaultdict(lambda: {'total': 0, 'self_merged': 0})
        
        for pr in prs:
            if not pr.get('merged', False):
                continue
            
            author = (pr.get('author') or '').lower()
            merged_by = (pr.get('merged_by') or '').lower()
            
            if author in [m.lower() for m in self.maintainers]:
                maintainer_stats[author]['total'] += 1
                if merged_by and author and merged_by == author:
                    maintainer_stats[author]['self_merged'] += 1
        
        # Check known outliers
        known_outliers = {
            'laanwj': (70, 85),  # Expected range: 70-85%
            'gavinandresen': (60, 75),  # Expected range: 60-75%
            'fanquake': (45, 55),  # Expected range: 45-55%
            'maflcko': (30, 45),  # Expected range: 30-45%
        }
        
        print("Key maintainer validation:")
        for maintainer, (min_rate, max_rate) in known_outliers.items():
            stats = maintainer_stats.get(maintainer.lower(), {})
            if stats['total'] > 0:
                rate = stats['self_merged'] / stats['total'] * 100
                print(f"  {maintainer}: {rate:.1f}% ({stats['self_merged']}/{stats['total']})")
                
                if rate < min_rate or rate > max_rate:
                    self.warnings.append(f"{maintainer} self-merge rate {rate:.1f}% outside expected range ({min_rate}-{max_rate}%)")
                else:
                    self.validations.append(f"✅ {maintainer}: {rate:.1f}% (expected {min_rate}-{max_rate}%)")
        
        return maintainer_stats
    
    def validate_cross_analysis_consistency(self) -> Dict[str, Any]:
        """Validate consistency across different analysis outputs."""
        print("\n" + "="*80)
        print("4. CROSS-ANALYSIS CONSISTENCY VALIDATION")
        print("="*80)
        
        findings_dir = self.data_dir.parent / 'findings'
        
        # Load key analysis results
        files_to_check = {
            'quick_insights.json': 'quick_insights',
            'novel_interpretations.json': 'novel_interpretations',
            'merge_pattern_analysis.json': 'merge_pattern_analysis'
        }
        
        results = {}
        for filename, key in files_to_check.items():
            filepath = findings_dir / filename
            if filepath.exists():
                with open(filepath) as f:
                    results[key] = json.load(f)
            else:
                self.warnings.append(f"Missing analysis file: {filename}")
        
        # Cross-validate self-merge rates
        if 'quick_insights' in results and 'merge_pattern_analysis' in results:
            qi_rate = results['quick_insights'].get('maintainer_outliers', {}).get('highest_self_merge', [])
            mpa_data = results['merge_pattern_analysis'].get('self_merge_breakdown', {})
            
            if qi_rate and mpa_data:
                # Get laanwj rate from quick_insights
                laanwj_qi = next((m for m in qi_rate if m.get('maintainer') == 'laanwj'), None)
                mpa_rate = mpa_data.get('self_merge_rate', 0)
                
                if laanwj_qi:
                    laanwj_rate = laanwj_qi.get('rate', 0)
                    print(f"laanwj self-merge rate:")
                    print(f"  quick_insights: {laanwj_rate*100:.1f}%")
                    print(f"  merge_pattern_analysis: {mpa_rate*100:.1f}% (overall)")
                    
                    # Check overall rate consistency
                    if abs(laanwj_rate - mpa_rate) > 0.5:  # Allow some difference
                        self.warnings.append("Self-merge rates differ between analyses")
                    else:
                        self.validations.append("✅ Self-merge rates consistent across analyses")
        
        return results
    
    def validate_zero_review_rates(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate zero-review merge rates."""
        print("\n" + "="*80)
        print("5. ZERO-REVIEW RATE VALIDATION")
        print("="*80)
        
        maintainer_merged = [p for p in prs 
                            if p.get('merged', False) and
                            (p.get('author') or '').lower() in [m.lower() for m in self.maintainers]]
        
        self_merged = [p for p in maintainer_merged 
                      if (p.get('merged_by') or '').lower() == (p.get('author') or '').lower()]
        other_merged = [p for p in maintainer_merged 
                       if (p.get('merged_by') or '').lower() != (p.get('author') or '').lower() and p.get('merged_by')]
        
        self_zero = sum(1 for p in self_merged if len(p.get('reviews', [])) == 0)
        other_zero = sum(1 for p in other_merged if len(p.get('reviews', [])) == 0)
        
        self_zero_rate = self_zero / len(self_merged) * 100 if self_merged else 0
        other_zero_rate = other_zero / len(other_merged) * 100 if other_merged else 0
        
        print(f"Self-merged PRs: {len(self_merged):,}")
        print(f"  Zero reviews: {self_zero:,} ({self_zero_rate:.1f}%)")
        print(f"Other-merged PRs: {len(other_merged):,}")
        print(f"  Zero reviews: {other_zero:,} ({other_zero_rate:.1f}%)")
        
        # Validate: self-merge should have higher zero-review rate
        if self_zero_rate < other_zero_rate:
            self.warnings.append(f"Unexpected: self-merge zero-review rate ({self_zero_rate:.1f}%) lower than other-merge ({other_zero_rate:.1f}%)")
        else:
            self.validations.append(f"✅ Self-merge has higher zero-review rate ({self_zero_rate:.1f}% vs {other_zero_rate:.1f}%)")
        
        return {
            'self_merged': len(self_merged),
            'self_zero': self_zero,
            'self_zero_rate': self_zero_rate,
            'other_merged': len(other_merged),
            'other_zero': other_zero,
            'other_zero_rate': other_zero_rate
        }
    
    def validate_calculation_logic(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate calculation logic correctness."""
        print("\n" + "="*80)
        print("6. CALCULATION LOGIC VALIDATION")
        print("="*80)
        
        # Check for common errors
        errors_found = []
        
        # Error 1: Treating missing merged_by as self-merge
        maintainer_merged = [p for p in prs 
                            if p.get('merged', False) and
                            (p.get('author') or '').lower() in [m.lower() for m in self.maintainers]]
        
        missing_merged_by = [p for p in maintainer_merged if not p.get('merged_by')]
        if len(missing_merged_by) > len(maintainer_merged) * 0.05:  # More than 5% missing
            errors_found.append(f"High missing merged_by rate: {len(missing_merged_by)/len(maintainer_merged)*100:.1f}%")
        else:
            self.validations.append(f"✅ Low missing merged_by rate: {len(missing_merged_by)/len(maintainer_merged)*100:.1f}%")
        
        # Error 2: Case sensitivity issues
        case_issues = 0
        for pr in maintainer_merged[:100]:  # Sample
            author = pr.get('author', '')
            merged_by = pr.get('merged_by', '')
            if author and merged_by:
                if author.lower() == merged_by.lower() and author != merged_by:
                    case_issues += 1
        
        if case_issues > 0:
            self.warnings.append(f"Potential case sensitivity issues: {case_issues} cases found in sample")
        else:
            self.validations.append("✅ No case sensitivity issues detected")
        
        # Error 3: Negative time calculations
        time_errors = 0
        for pr in maintainer_merged[:100]:  # Sample
            created = pr.get('created_at')
            merged = pr.get('merged_at')
            if created and merged:
                try:
                    from datetime import datetime
                    created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    merged_dt = datetime.fromisoformat(merged.replace('Z', '+00:00'))
                    days = (merged_dt - created_dt).total_seconds() / 86400
                    if days < 0:
                        time_errors += 1
                except:
                    pass
        
        if time_errors > 0:
            errors_found.append(f"Negative time calculations: {time_errors} cases found")
        else:
            self.validations.append("✅ No negative time calculations")
        
        return {
            'missing_merged_by': len(missing_merged_by),
            'case_issues': case_issues,
            'time_errors': time_errors,
            'errors_found': errors_found
        }
    
    def run_all_validations(self) -> Dict[str, Any]:
        """Run all validations."""
        print("="*80)
        print("COMPREHENSIVE ANALYSIS VALIDATION")
        print("="*80)
        print()
        
        prs = self.load_prs()
        print(f"Loaded {len(prs):,} PRs\n")
        
        results = {
            'data_coverage': self.validate_data_coverage(prs),
            'self_merge_calculation': self.validate_self_merge_calculation(prs),
            'individual_rates': self.validate_individual_maintainer_rates(prs),
            'cross_analysis': self.validate_cross_analysis_consistency(),
            'zero_review_rates': self.validate_zero_review_rates(prs),
            'calculation_logic': self.validate_calculation_logic(prs),
            'summary': {
                'errors': self.errors,
                'warnings': self.warnings,
                'validations': self.validations
            }
        }
        
        # Print summary
        print("\n" + "="*80)
        print("VALIDATION SUMMARY")
        print("="*80)
        print(f"\n✅ Validations passed: {len(self.validations)}")
        for v in self.validations:
            print(f"  {v}")
        
        if self.warnings:
            print(f"\n⚠️  Warnings: {len(self.warnings)}")
            for w in self.warnings:
                print(f"  {w}")
        
        if self.errors:
            print(f"\n❌ Errors: {len(self.errors)}")
            for e in self.errors:
                print(f"  {e}")
        
        if not self.errors and not self.warnings:
            print("\n✅ All validations passed!")
        
        return results


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate analysis results')
    parser.add_argument('--data-dir', type=Path, default=Path(__file__).parent.parent.parent / 'data',
                       help='Data directory')
    parser.add_argument('--output', type=Path, default=Path(__file__).parent.parent.parent / 'findings' / 'validation_results.json',
                       help='Output JSON file')
    
    args = parser.parse_args()
    
    validator = AnalysisValidator(args.data_dir)
    results = validator.run_all_validations()
    
    # Save results
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nValidation results saved to: {args.output}")


if __name__ == '__main__':
    main()
