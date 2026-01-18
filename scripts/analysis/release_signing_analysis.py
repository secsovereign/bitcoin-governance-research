#!/usr/bin/env python3
"""
Release Signing Analysis - Analyze release signing authority and patterns.

Analyzes:
1. Who signs releases (concentration of signing authority)
2. Signing patterns over time
3. Relationship between release signers and maintainers
4. Signing transparency and process
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from collections import defaultdict, Counter
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir, get_analysis_dir

logger = setup_logger()


class ReleaseSigningAnalyzer:
    """Analyzer for release signing authority and patterns."""
    
    def __init__(self):
        """Initialize analyzer."""
        self.data_dir = get_data_dir()
        self.processed_dir = self.data_dir / 'processed'
        self.releases_dir = self.data_dir / 'releases'
        self.analysis_dir = get_analysis_dir()
        self.findings_dir = self.analysis_dir / 'findings' / 'data'
        self.findings_dir.mkdir(parents=True, exist_ok=True)
    
    def run_analysis(self):
        """Run release signing analysis."""
        logger.info("=" * 60)
        logger.info("Release Signing Analysis")
        logger.info("=" * 60)
        
        # Load data
        release_signers = self._load_release_signers()
        maintainer_timeline = self._load_maintainer_timeline()
        contributors = self._load_contributors()
        
        # Analyze signing concentration
        concentration = self._analyze_signing_concentration(release_signers)
        
        # Analyze signing patterns over time
        temporal_patterns = self._analyze_temporal_patterns(release_signers)
        
        # Analyze relationship to maintainers
        maintainer_relationship = self._analyze_maintainer_relationship(
            release_signers, maintainer_timeline
        )
        
        # Analyze relationship to contributors
        contributor_relationship = self._analyze_contributor_relationship(
            release_signers, contributors
        )
        
        # Calculate transparency metrics
        transparency = self._analyze_transparency(release_signers)
        
        # Save results
        self._save_results({
            'concentration': concentration,
            'temporal_patterns': temporal_patterns,
            'maintainer_relationship': maintainer_relationship,
            'contributor_relationship': contributor_relationship,
            'transparency': transparency
        })
        
        logger.info("Release signing analysis complete")
    
    def _load_release_signers(self) -> List[Dict[str, Any]]:
        """Load release signer data."""
        # Try releases directory first (raw data), then fall back to processed
        signers_file = self.releases_dir / 'release_signers.jsonl'
        if not signers_file.exists():
            signers_file = self.processed_dir / 'cleaned_release_signers.jsonl'
            if not signers_file.exists():
                logger.warning(f"Release signers file not found: {signers_file}")
                return []
        
        releases = []
        with open(signers_file, 'r') as f:
            for line in f:
                releases.append(json.loads(line))
        
        logger.info(f"Loaded {len(releases)} release records")
        return releases
    
    def _load_maintainer_timeline(self) -> Dict[str, Any]:
        """Load maintainer timeline."""
        timeline_file = self.processed_dir / 'maintainer_timeline.json'
        
        if not timeline_file.exists():
            logger.warning(f"Maintainer timeline not found: {timeline_file}")
            return {}
        
        with open(timeline_file, 'r') as f:
            data = json.load(f)
            return data.get('maintainer_timeline', {})
    
    def _load_contributors(self) -> Dict[str, Any]:
        """Load contributors data."""
        contributors_file = self.data_dir / 'github' / 'collaborators.json'
        
        if not contributors_file.exists():
            logger.warning(f"Contributors file not found: {contributors_file}")
            return {}
        
        with open(contributors_file, 'r') as f:
            data = json.load(f)
            contributors = data.get('contributors', [])
            
            # Create lookup
            lookup = {}
            for i, contrib in enumerate(contributors):
                login = contrib.get('login')
                if login:
                    lookup[login] = {
                        'rank': i + 1,
                        'contributions': contrib.get('contributions', 0)
                    }
            
            return {'lookup': lookup, 'total': len(contributors)}
    
    def _analyze_signing_concentration(
        self,
        releases: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze concentration of release signing authority."""
        signed_releases = [r for r in releases if r.get('is_signed')]
        
        # Count signings per signer
        signer_counts = Counter()
        signer_details = defaultdict(lambda: {'count': 0, 'releases': []})
        
        for release in signed_releases:
            signer_email = release.get('signer_email')
            signer_name = release.get('signer_name')
            
            if signer_email:
                signer_key = signer_email.lower()
                signer_counts[signer_key] += 1
                signer_details[signer_key]['count'] += 1
                signer_details[signer_key]['name'] = signer_name
                signer_details[signer_key]['releases'].append(release.get('tag'))
        
        # Calculate concentration metrics
        total_signed = len(signed_releases)
        signer_shares = {k: v / total_signed for k, v in signer_counts.items()}
        
        # Top N shares
        sorted_shares = sorted(signer_shares.values(), reverse=True)
        top_5_share = sum(sorted_shares[:5])
        top_10_share = sum(sorted_shares[:10]) if len(sorted_shares) >= 10 else sum(sorted_shares)
        
        # Gini coefficient
        gini = self._calculate_gini(list(signer_counts.values()))
        
        # HHI
        hhi = sum(s**2 for s in signer_shares.values())
        
        return {
            'total_releases': len(releases),
            'signed_releases': total_signed,
            'unsigned_releases': len(releases) - total_signed,
            'signing_rate': total_signed / len(releases) if releases else 0,
            'unique_signers': len(signer_counts),
            'signer_counts': dict(signer_counts),
            'signer_details': dict(signer_details),
            'concentration_metrics': {
                'gini_coefficient': gini,
                'hhi': hhi,
                'top_5_share': top_5_share,
                'top_10_share': top_10_share
            },
            'top_signers': [
                {
                    'email': email,
                    'name': signer_details[email]['name'],
                    'count': count,
                    'share': signer_shares[email]
                }
                for email, count in signer_counts.most_common(10)
            ]
        }
    
    def _analyze_temporal_patterns(
        self,
        releases: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze signing patterns over time."""
        # Group by year
        by_year = defaultdict(lambda: {'total': 0, 'signed': 0, 'signers': set()})
        
        for release in releases:
            tagger_date = release.get('tagger_date_iso')
            if not tagger_date:
                continue
            
            try:
                year = datetime.fromisoformat(tagger_date.replace('Z', '+00:00')).year
                by_year[year]['total'] += 1
                
                if release.get('is_signed'):
                    by_year[year]['signed'] += 1
                    signer = release.get('signer_email')
                    if signer:
                        by_year[year]['signers'].add(signer)
            except Exception:
                continue
        
        # Convert to serializable format
        temporal_data = {}
        for year in sorted(by_year.keys()):
            data = by_year[year]
            temporal_data[year] = {
                'total': data['total'],
                'signed': data['signed'],
                'unsigned': data['total'] - data['signed'],
                'signing_rate': data['signed'] / data['total'] if data['total'] > 0 else 0,
                'unique_signers': len(data['signers'])
            }
        
        return temporal_data
    
    def _analyze_maintainer_relationship(
        self,
        releases: List[Dict[str, Any]],
        maintainer_timeline: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze relationship between release signers and maintainers."""
        # Map signer emails to maintainer status
        signer_maintainer_status = {}
        
        for release in releases:
            if not release.get('is_signed'):
                continue
            
            signer_email = release.get('signer_email')
            if not signer_email:
                continue
            
            # Check if signer is a maintainer
            # Need to match email to maintainer timeline
            is_maintainer = False
            for maintainer_id, data in maintainer_timeline.items():
                # This would need identity mapping - simplified for now
                if signer_email.lower() in maintainer_id.lower():
                    is_maintainer = True
                    break
            
            if signer_email not in signer_maintainer_status:
                signer_maintainer_status[signer_email] = {
                    'is_maintainer': is_maintainer,
                    'release_count': 0
                }
            signer_maintainer_status[signer_email]['release_count'] += 1
        
        maintainer_signers = sum(1 for s in signer_maintainer_status.values() if s['is_maintainer'])
        non_maintainer_signers = len(signer_maintainer_status) - maintainer_signers
        
        return {
            'total_signers': len(signer_maintainer_status),
            'maintainer_signers': maintainer_signers,
            'non_maintainer_signers': non_maintainer_signers,
            'maintainer_signing_rate': maintainer_signers / len(signer_maintainer_status) if signer_maintainer_status else 0,
            'signer_details': signer_maintainer_status
        }
    
    def _analyze_contributor_relationship(
        self,
        releases: List[Dict[str, Any]],
        contributors: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze relationship between release signers and top contributors."""
        if not contributors:
            return {}
        
        contributor_lookup = contributors.get('lookup', {})
        
        signer_contributions = []
        top_contributor_signers = []
        
        for release in releases:
            if not release.get('is_signed'):
                continue
            
            signer_email = release.get('signer_email')
            signer_name = release.get('signer_name')
            
            # Try to match signer to contributor
            # Match by email or name
            matched_contrib = None
            for login, contrib_data in contributor_lookup.items():
                # Simple matching - would need better identity resolution
                if signer_name and signer_name.lower() in login.lower():
                    matched_contrib = contrib_data
                    break
            
            if matched_contrib:
                signer_contributions.append(matched_contrib['contributions'])
                if matched_contrib['rank'] <= 10:
                    top_contributor_signers.append({
                        'signer': signer_email,
                        'contributor_rank': matched_contrib['rank'],
                        'contributions': matched_contrib['contributions']
                    })
        
        return {
            'signers_with_contributions': len(signer_contributions),
            'top_contributor_signers': top_contributor_signers,
            'avg_contributions': sum(signer_contributions) / len(signer_contributions) if signer_contributions else 0
        }
    
    def _analyze_transparency(
        self,
        releases: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze transparency of release signing process."""
        signed_releases = [r for r in releases if r.get('is_signed')]
        
        # Check verification status
        verified = sum(1 for r in signed_releases if r.get('verification_returncode') == 0)
        unverified = len(signed_releases) - verified
        
        # Check signer identification
        identified = sum(1 for r in signed_releases if r.get('signer_email'))
        unidentified = len(signed_releases) - identified
        
        return {
            'total_signed': len(signed_releases),
            'verified_signatures': verified,
            'unverified_signatures': unverified,
            'verification_rate': verified / len(signed_releases) if signed_releases else 0,
            'identified_signers': identified,
            'unidentified_signers': unidentified,
            'identification_rate': identified / len(signed_releases) if signed_releases else 0
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
    
    def _save_results(self, results: Dict[str, Any]):
        """Save analysis results."""
        output_file = self.findings_dir / 'release_signing.json'
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Results saved to {output_file}")
        
        # Generate summary
        self._generate_summary(results)
    
    def _generate_summary(self, results: Dict[str, Any]):
        """Generate analysis summary."""
        conc = results['concentration']
        
        logger.info("Release Signing Analysis Summary:")
        logger.info(f"  Total releases: {conc['total_releases']}")
        logger.info(f"  Signed releases: {conc['signed_releases']} ({conc['signing_rate']*100:.1f}%)")
        logger.info(f"  Unique signers: {conc['unique_signers']}")
        logger.info(f"  Gini coefficient: {conc['concentration_metrics']['gini_coefficient']:.3f}")
        logger.info(f"  Top 5 signers share: {conc['concentration_metrics']['top_5_share']*100:.1f}%")


def main():
    """Main entry point."""
    analyzer = ReleaseSigningAnalyzer()
    analyzer.run_analysis()
    return 0


if __name__ == '__main__':
    sys.exit(main())

