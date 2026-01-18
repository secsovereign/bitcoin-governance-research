#!/usr/bin/env python3
"""
BIP Process Analysis - Analyze BIP (Bitcoin Improvement Proposal) governance patterns.

Analyzes:
1. BIP proposer analysis (who proposes BIPs, concentration)
2. BIP champion analysis (who champions BIPs through the process)
3. BIP opposition analysis (who opposes BIPs, effectiveness)
4. BIP-to-Core implementation pipeline (tracking BIP → Core PR)
5. BIP Repository vs Core Repository comparison (governance patterns)
"""

import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from collections import defaultdict, Counter
from datetime import datetime, timezone

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir, get_analysis_dir

logger = setup_logger()


class BIPProcessAnalyzer:
    """Analyzer for BIP governance patterns."""
    
    def __init__(self):
        """Initialize analyzer."""
        self.data_dir = get_data_dir()
        self.bips_dir = self.data_dir / 'bips'
        self.github_dir = self.data_dir / 'github'
        self.analysis_dir = get_analysis_dir()
        self.findings_dir = self.analysis_dir / 'findings' / 'data'
        self.findings_dir.mkdir(parents=True, exist_ok=True)
        
        # Maintainer list (from Core repository)
        self.maintainers = {
            'laanwj', 'sipa', 'maflcko', 'fanquake', 'hebasto', 'jnewbery',
            'ryanofsky', 'achow101', 'theuni', 'jonasschnelli', 'Sjors',
            'promag', 'instagibbs', 'TheBlueMatt', 'jonatack', 'gmaxwell',
            'gavinandresen', 'petertodd', 'luke-jr', 'glozow'
        }
    
    def run_analysis(self):
        """Run BIP process analysis."""
        logger.info("=" * 60)
        logger.info("BIP Process Analysis")
        logger.info("=" * 60)
        
        # Load data
        bips = self._load_bips()
        bip_prs = self._load_bip_prs()
        bip_issues = self._load_bip_issues()
        core_prs = self._load_core_prs()
        
        logger.info(f"Loaded {len(bips)} BIPs, {len(bip_prs)} BIP PRs, {len(bip_issues)} BIP issues")
        
        # Analyze BIP proposers
        proposer_analysis = self._analyze_proposers(bips, bip_prs)
        
        # Analyze BIP champions
        champion_analysis = self._analyze_champions(bip_prs, bip_issues)
        
        # Analyze BIP opposition
        opposition_analysis = self._analyze_opposition(bip_prs, bip_issues)
        
        # Analyze BIP-to-Core implementation pipeline
        implementation_analysis = self._analyze_implementation_pipeline(bips, core_prs)
        
        # Compare BIP repository vs Core repository
        repo_comparison = self._compare_repositories(bip_prs, core_prs)
        
        # Save results
        results = {
            'proposer_analysis': proposer_analysis,
            'champion_analysis': champion_analysis,
            'opposition_analysis': opposition_analysis,
            'implementation_analysis': implementation_analysis,
            'repo_comparison': repo_comparison,
            'statistics': self._generate_statistics(
                proposer_analysis, champion_analysis, opposition_analysis,
                implementation_analysis, repo_comparison
            ),
            'methodology': self._get_methodology()
        }
        
        self._save_results(results)
        logger.info("BIP process analysis complete")
    
    def _load_bips(self) -> List[Dict[str, Any]]:
        """Load BIP data."""
        bips_file = self.bips_dir / 'bips.jsonl'
        if not bips_file.exists():
            logger.warning(f"BIPs file not found: {bips_file}")
            return []
        
        bips = []
        with open(bips_file, 'r') as f:
            for line in f:
                bips.append(json.loads(line))
        
        return bips
    
    def _load_bip_prs(self) -> List[Dict[str, Any]]:
        """Load BIP repository PRs."""
        prs_file = self.bips_dir / 'bips_prs.jsonl'
        if not prs_file.exists():
            logger.warning(f"BIP PRs file not found: {prs_file}")
            return []
        
        prs = []
        with open(prs_file, 'r') as f:
            for line in f:
                prs.append(json.loads(line))
        
        return prs
    
    def _load_bip_issues(self) -> List[Dict[str, Any]]:
        """Load BIP repository issues."""
        issues_file = self.bips_dir / 'bips_issues.jsonl'
        if not issues_file.exists():
            logger.warning(f"BIP issues file not found: {issues_file}")
            return []
        
        issues = []
        with open(issues_file, 'r') as f:
            for line in f:
                issues.append(json.loads(line))
        
        return issues
    
    def _load_core_prs(self) -> List[Dict[str, Any]]:
        """Load Core repository PRs."""
        # Try publication-package data first, then fall back to parent commons-research data
        prs_file = self.github_dir / 'prs_raw.jsonl'
        if not prs_file.exists():
            # Fall back to parent commons-research data directory
            parent_data_dir = self.data_dir.parent / 'data' / 'github' / 'prs_raw.jsonl'
            if parent_data_dir.exists():
                prs_file = parent_data_dir
            else:
                logger.warning(f"Core PRs file not found: {prs_file}")
                return []
        
        prs = []
        with open(prs_file, 'r') as f:
            for line in f:
                prs.append(json.loads(line))
        
        return prs
    
    def _extract_bip_authors(self, bip: Dict[str, Any]) -> List[str]:
        """Extract authors from BIP content."""
        content = bip.get('content', '')
        if not content:
            return []
        
        # Look for Author: line in BIP content
        author_pattern = r'Author:\s*(.+)'
        match = re.search(author_pattern, content, re.IGNORECASE | re.MULTILINE)
        if match:
            authors_str = match.group(1).strip()
            # Split by comma and clean up
            authors = [a.strip() for a in authors_str.split(',')]
            # Extract usernames/emails (try to normalize)
            normalized = []
            for author in authors:
                # Remove email addresses if present, extract name
                author = re.sub(r'<[^>]+>', '', author).strip()
                if author:
                    normalized.append(author.lower())
            return normalized
        
        return []
    
    def _analyze_proposers(
        self,
        bips: List[Dict[str, Any]],
        bip_prs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze BIP proposers."""
        logger.info("Analyzing BIP proposers...")
        
        proposer_counts = Counter()
        proposer_bips = defaultdict(list)
        
        # Extract proposers from BIPs
        for bip in bips:
            bip_number = bip.get('bip_number')
            authors = self._extract_bip_authors(bip)
            
            for author in authors:
                proposer_counts[author] += 1
                proposer_bips[author].append(bip_number)
        
        # Calculate concentration metrics
        total_bips = len(bips)
        total_proposers = len(proposer_counts)
        
        # Top N control
        sorted_proposers = proposer_counts.most_common()
        top3_count = sum(count for _, count in sorted_proposers[:3])
        top5_count = sum(count for _, count in sorted_proposers[:5])
        top10_count = sum(count for _, count in sorted_proposers[:10])
        
        # Gini coefficient (simplified)
        gini = self._calculate_gini([count for _, count in proposer_counts.items()])
        
        # Maintainer vs non-maintainer
        maintainer_proposers = []
        non_maintainer_proposers = []
        
        for proposer, count in proposer_counts.items():
            # Check if proposer is a maintainer (fuzzy matching)
            is_maintainer = any(m.lower() in proposer or proposer in m.lower() 
                              for m in self.maintainers)
            if is_maintainer:
                maintainer_proposers.append((proposer, count))
            else:
                non_maintainer_proposers.append((proposer, count))
        
        return {
            'total_bips': total_bips,
            'total_proposers': total_proposers,
            'proposer_counts': dict(proposer_counts),
            'proposer_bips': {k: v for k, v in proposer_bips.items()},
            'concentration': {
                'top3_share': top3_count / total_bips if total_bips > 0 else 0,
                'top5_share': top5_count / total_bips if total_bips > 0 else 0,
                'top10_share': top10_count / total_bips if total_bips > 0 else 0,
                'gini_coefficient': gini
            },
            'top_proposers': sorted_proposers[:20],
            'maintainer_proposers': maintainer_proposers[:20],
            'non_maintainer_proposers': non_maintainer_proposers[:20],
            'maintainer_proposal_rate': len(maintainer_proposers) / total_proposers if total_proposers > 0 else 0
        }
    
    def _analyze_champions(
        self,
        bip_prs: List[Dict[str, Any]],
        bip_issues: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze BIP champions (active discussants/advocates)."""
        logger.info("Analyzing BIP champions...")
        
        # Champion = frequent commenter/reviewer on BIP PRs/issues
        champion_activity = defaultdict(int)
        champion_prs = defaultdict(set)
        champion_issues = defaultdict(set)
        
        # Count activity on BIP PRs (author counts as activity)
        for pr in bip_prs:
            author = (pr.get('author') or '').lower()
            if author:
                champion_activity[author] += 1
                champion_prs[author].add(pr.get('number'))
            
            # Comments count as activity (approximate with comments_count)
            comments = pr.get('comments_count', 0)
            if comments > 0:
                champion_activity[author] += comments
        
        # Count activity on BIP issues (similar pattern)
        for issue in bip_issues:
            # Assume issues have similar structure
            # This would need to be adjusted based on actual issue structure
            pass
        
        # Calculate champion metrics
        sorted_champions = sorted(champion_activity.items(), key=lambda x: x[1], reverse=True)
        top10_champions = sorted_champions[:10]
        
        return {
            'total_champions': len(champion_activity),
            'champion_activity': dict(champion_activity),
            'top_champions': top10_champions,
            'champion_pr_coverage': {k: len(v) for k, v in champion_prs.items()}
        }
    
    def _analyze_opposition(
        self,
        bip_prs: List[Dict[str, Any]],
        bip_issues: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze BIP opposition patterns."""
        logger.info("Analyzing BIP opposition...")
        
        # Opposition keywords
        opposition_keywords = ['nack', 'oppose', 'against', 'object', 'reject', 'veto']
        
        # Track opposition per BIP (simplified - would need PR/issue body content)
        opposition_counts = Counter()
        
        # For now, use PR/issue state as proxy
        rejected_prs = [pr for pr in bip_prs if pr.get('state') == 'closed' and not pr.get('merged')]
        rejected_issues = [issue for issue in bip_issues if issue.get('state') == 'closed']
        
        return {
            'rejected_prs_count': len(rejected_prs),
            'rejected_issues_count': len(rejected_issues),
            'opposition_counts': dict(opposition_counts),
            'note': 'Full opposition analysis requires PR/issue body content'
        }
    
    def _analyze_implementation_pipeline(
        self,
        bips: List[Dict[str, Any]],
        core_prs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze BIP-to-Core implementation pipeline."""
        logger.info("Analyzing BIP-to-Core implementation pipeline...")
        
        # Find BIP mentions in Core PRs
        bip_pr_mappings = defaultdict(list)
        bip_numbers = {bip.get('bip_number') for bip in bips if bip.get('bip_number')}
        
        for pr in core_prs:
            title = (pr.get('title') or '').lower()
            body = (pr.get('body') or '').lower()
            text = title + ' ' + body
            
            # Look for BIP number mentions
            for bip_num in bip_numbers:
                if re.search(rf'\bbip\s*[-]?\s*{bip_num}\b', text, re.IGNORECASE):
                    bip_pr_mappings[bip_num].append(pr.get('number'))
        
        # Calculate pipeline metrics
        bips_with_impls = len([bip_num for bip_num in bip_numbers if bip_num in bip_pr_mappings])
        impl_rate = bips_with_impls / len(bip_numbers) if bip_numbers else 0
        
        # Implementation timing (simplified - would need BIP dates)
        return {
            'total_bips': len(bip_numbers),
            'bips_with_implementations': bips_with_impls,
            'implementation_rate': impl_rate,
            'bip_to_pr_mappings': {str(k): v for k, v in bip_pr_mappings.items()},
            'note': 'Implementation timing analysis requires BIP proposal dates'
        }
    
    def _compare_repositories(
        self,
        bip_prs: List[Dict[str, Any]],
        core_prs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Compare BIP repository vs Core repository governance patterns."""
        logger.info("Comparing BIP repository vs Core repository...")
        
        # Actor overlap
        bip_authors = {pr.get('author', '').lower() for pr in bip_prs if pr.get('author')}
        core_authors = {pr.get('author', '').lower() for pr in core_prs if pr.get('author')}
        overlapping_authors = bip_authors & core_authors
        
        # Merge concentration (BIP PRs)
        bip_merged = [pr for pr in bip_prs if pr.get('merged')]
        bip_mergers = Counter(pr.get('author') for pr in bip_merged if pr.get('author'))
        
        # Core merge concentration (simplified - would need merged_by data)
        core_merged = [pr for pr in core_prs if pr.get('merged')]
        
        return {
            'actor_overlap': {
                'bip_authors': len(bip_authors),
                'core_authors': len(core_authors),
                'overlapping_authors': len(overlapping_authors),
                'overlap_rate': len(overlapping_authors) / len(bip_authors) if bip_authors else 0
            },
            'bip_merge_concentration': {
                'total_merged': len(bip_merged),
                'unique_mergers': len(bip_mergers),
                'top_mergers': dict(bip_mergers.most_common(10))
            },
            'note': 'Full comparison requires Core merge authority data'
        }
    
    def _calculate_gini(self, values: List[float]) -> float:
        """Calculate Gini coefficient."""
        if not values or sum(values) == 0:
            return 0.0
        
        sorted_values = sorted(values)
        n = len(sorted_values)
        cumsum = 0
        for i, value in enumerate(sorted_values):
            cumsum += value * (i + 1)
        
        return (2 * cumsum) / (n * sum(sorted_values)) - (n + 1) / n
    
    def _generate_statistics(
        self,
        proposer_analysis: Dict[str, Any],
        champion_analysis: Dict[str, Any],
        opposition_analysis: Dict[str, Any],
        implementation_analysis: Dict[str, Any],
        repo_comparison: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate overall statistics."""
        return {
            'summary': {
                'total_bips': proposer_analysis.get('total_bips', 0),
                'total_proposers': proposer_analysis.get('total_proposers', 0),
                'proposer_gini': proposer_analysis.get('concentration', {}).get('gini_coefficient', 0),
                'actor_overlap_rate': repo_comparison.get('actor_overlap', {}).get('overlap_rate', 0),
                'implementation_rate': implementation_analysis.get('implementation_rate', 0)
            }
        }
    
    def _get_methodology(self) -> Dict[str, Any]:
        """Get methodology description."""
        return {
            'proposer_extraction': 'Authors extracted from BIP content using Author: field',
            'champion_identification': 'Based on activity frequency (PRs authored, comments)',
            'opposition_detection': 'Based on PR/issue state (closed without merge)',
            'implementation_tracking': 'BIP number mentions in Core PR titles/bodies',
            'repo_comparison': 'Actor overlap and merge concentration comparison',
            'limitations': [
                'BIP author extraction may miss some authors',
                'Champion analysis limited by available comment data',
                'Opposition analysis requires PR/issue body content',
                'Implementation tracking based on BIP mentions (may miss some)'
            ]
        }
    
    def _save_results(self, results: Dict[str, Any]):
        """Save analysis results."""
        output_file = self.findings_dir / 'bip_analysis.json'
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to {output_file}")


def main():
    """Main entry point."""
    analyzer = BIPProcessAnalyzer()
    analyzer.run_analysis()


if __name__ == '__main__':
    main()
