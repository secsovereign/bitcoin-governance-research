#!/usr/bin/env python3
"""
Transparency & Governance Gap Analysis - Identify gaps between claims and reality.

Analyzes:
1. Communication channel analysis (where decisions are made)
2. Documentation analysis
3. External pressure analysis
4. Release signing transparency
5. Cryptographic enforcement gap
6. Case study: Luke Dashjr maintainer removal
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
from src.schemas.analysis_results import create_result_template

logger = setup_logger()


class TransparencyGapAnalyzer:
    """Analyzer for transparency and governance gaps."""
    
    def __init__(self):
        """Initialize analyzer."""
        self.data_dir = get_data_dir()
        self.processed_dir = self.data_dir / 'processed'
        self.analysis_dir = get_analysis_dir() / 'transparency_gap'
        self.analysis_dir.mkdir(parents=True, exist_ok=True)
    
    def run_analysis(self):
        """Run transparency gap analysis."""
        logger.info("=" * 60)
        logger.info("Transparency & Governance Gap Analysis")
        logger.info("=" * 60)
        
        # Load data
        prs = self._load_enriched_prs()
        emails = self._load_emails()
        irc_messages = self._load_irc()
        external_pressure = self._load_external_pressure()
        release_signers = self._load_release_signers()
        commit_signing = self._load_commit_signing()
        
        # Analyze communication channels
        channel_analysis = self._analyze_communication_channels(prs, emails, irc_messages)
        
        # Analyze documentation
        documentation = self._analyze_documentation()
        
        # Analyze external pressure
        external_analysis = self._analyze_external_pressure(external_pressure)
        
        # Analyze release signing transparency
        release_transparency = self._analyze_release_transparency(release_signers)
        
        # Analyze cryptographic enforcement gap
        crypto_gap = self._analyze_cryptographic_gap(commit_signing, prs)
        
        # Luke Dashjr case study
        luke_case = self._analyze_luke_case(prs, emails, irc_messages)
        
        # Save results
        self._save_results({
            'channel_analysis': channel_analysis,
            'documentation': documentation,
            'external_pressure': external_analysis,
            'release_transparency': release_transparency,
            'cryptographic_gap': crypto_gap,
            'luke_case_study': luke_case
        })
        
        logger.info("Transparency gap analysis complete")
    
    def _load_enriched_prs(self) -> List[Dict[str, Any]]:
        """Load enriched PR data."""
        prs_file = self.processed_dir / 'enriched_prs.jsonl'
        if not prs_file.exists():
            prs_file = self.processed_dir / 'cleaned_prs.jsonl'
        
        if not prs_file.exists():
            return []
        
        prs = []
        with open(prs_file, 'r') as f:
            for line in f:
                prs.append(json.loads(line))
        return prs
    
    def _load_emails(self) -> List[Dict[str, Any]]:
        """Load email data."""
        emails_file = self.processed_dir / 'cleaned_emails.jsonl'
        if not emails_file.exists():
            return []
        
        emails = []
        with open(emails_file, 'r') as f:
            for line in f:
                emails.append(json.loads(line))
        return emails
    
    def _load_irc(self) -> List[Dict[str, Any]]:
        """Load IRC data."""
        irc_file = self.processed_dir / 'cleaned_irc.jsonl'
        if not irc_file.exists():
            return []
        
        messages = []
        with open(irc_file, 'r') as f:
            for line in f:
                messages.append(json.loads(line))
        return messages
    
    def _load_external_pressure(self) -> Dict[str, Any]:
        """Load external pressure indicators."""
        pressure_file = self.processed_dir / 'external_pressure_indicators.json'
        
        if not pressure_file.exists():
            return {}
        
        with open(pressure_file, 'r') as f:
            return json.load(f)
    
    def _load_release_signers(self) -> List[Dict[str, Any]]:
        """Load release signer data."""
        signers_file = self.processed_dir / 'cleaned_release_signers.jsonl'
        
        if not signers_file.exists():
            return []
        
        releases = []
        with open(signers_file, 'r') as f:
            for line in f:
                releases.append(json.loads(line))
        return releases
    
    def _load_commit_signing(self) -> Dict[str, Any]:
        """Load commit signing data."""
        signing_file = self.data_dir / 'github' / 'commit_signing.jsonl'
        
        if not signing_file.exists():
            return {}
        
        signing_data = {}
        with open(signing_file, 'r') as f:
            for line in f:
                record = json.loads(line)
                pr_number = record.get('pr_number')
                if pr_number:
                    signing_data[pr_number] = record
        
        return signing_data
    
    def _analyze_communication_channels(
        self,
        prs: List[Dict[str, Any]],
        emails: List[Dict[str, Any]],
        irc_messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze where decisions are made."""
        # Decisions in GitHub (PR merges)
        github_decisions = sum(1 for pr in prs if pr.get('merged'))
        
        # Decisions discussed in emails before PR
        email_discussions = 0
        for email in emails:
            # Check if email mentions PR number or discusses decision
            text = (email.get('body', '') + email.get('subject', '')).lower()
            if any(keyword in text for keyword in ['pr #', 'pull request', 'merge', 'decision']):
                email_discussions += 1
        
        # Decisions coordinated in IRC
        irc_coordination = 0
        for msg in irc_messages:
            text = (msg.get('content', '')).lower()
            if any(keyword in text for keyword in ['merge', 'approve', 'decision']):
                irc_coordination += 1
        
        return {
            'github_decisions': github_decisions,
            'email_discussions': email_discussions,
            'irc_coordination': irc_coordination,
            'total_channels': 3,
            'channel_usage': {
                'github': github_decisions,
                'email': email_discussions,
                'irc': irc_coordination
            }
        }
    
    def _analyze_documentation(self) -> Dict[str, Any]:
        """Analyze documentation status."""
        # Check for governance documentation
        # This would require checking for specific files or documentation
        # For now, return structure
        
        return {
            'governance_procedures_documented': 'unknown',
            'decision_criteria_documented': 'unknown',
            'maintainer_selection_documented': 'unknown',
            'maintainer_removal_documented': 'unknown',
            'note': 'Requires manual review of documentation'
        }
    
    def _analyze_external_pressure(self, external_pressure: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze external pressure indicators."""
        if not external_pressure:
            return {'error': 'No external pressure data available'}
        
        summary = external_pressure.get('summary', {})
        
        return {
            'mailing_list_pressure_rate': summary.get('mailing_lists', {}).get('percentage', 0),
            'irc_pressure_rate': summary.get('irc', {}).get('percentage', 0),
            'total_pressure_mentions': summary.get('total_pressure_mentions', 0),
            'pressure_type_counts': summary.get('pressure_type_counts', {}),
            'interpretation': 'Higher rates indicate more external pressure awareness'
        }
    
    def _analyze_release_transparency(self, releases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze release signing transparency."""
        if not releases:
            return {'error': 'No release signing data available'}
        
        signed = sum(1 for r in releases if r.get('is_signed'))
        total = len(releases)
        
        # Check if signers are identifiable
        identifiable = sum(1 for r in releases if r.get('is_signed') and r.get('signer_email'))
        
        return {
            'total_releases': total,
            'signed_releases': signed,
            'signing_rate': signed / total if total > 0 else 0,
            'identifiable_signers': identifiable,
            'identification_rate': identifiable / signed if signed > 0 else 0,
            'transparency_score': identifiable / total if total > 0 else 0
        }
    
    def _analyze_cryptographic_gap(
        self,
        commit_signing: Dict[str, Any],
        prs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze cryptographic enforcement gap."""
        if not commit_signing:
            return {
                'status': 'data_collection_in_progress',
                'note': 'Commit signing data collection in progress'
            }
        
        # Analyze signing rates
        signed = sum(1 for v in commit_signing.values() if v.get('is_signed'))
        total = len(commit_signing)
        
        return {
            'total_commits_checked': total,
            'signed_commits': signed,
            'signing_rate': signed / total if total > 0 else 0,
            'gap_analysis': {
                'current_system': 'GitHub commit signatures (if any)',
                'proposed_system': 'Three-layer verification (GitHub + Nostr + OpenTimestamps)',
                'gap': 'Missing real-time transparency and immutable proof layers'
            }
        }
    
    def _analyze_luke_case(
        self,
        prs: List[Dict[str, Any]],
        emails: List[Dict[str, Any]],
        irc_messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze Luke Dashjr maintainer removal case."""
        # Search for Luke-related content
        luke_keywords = ['luke', 'dashjr', 'luke-jr']
        
        luke_prs = []
        for pr in prs:
            text = f"{pr.get('title', '')} {pr.get('body', '')}".lower()
            if any(keyword in text for keyword in luke_keywords):
                luke_prs.append(pr.get('number'))
        
        luke_emails = []
        for email in emails:
            text = f"{email.get('subject', '')} {email.get('body', '')}".lower()
            if any(keyword in text for keyword in luke_keywords):
                luke_emails.append(email.get('message_id'))
        
        luke_irc = []
        for msg in irc_messages:
            text = (msg.get('content', '')).lower()
            if any(keyword in text for keyword in luke_keywords):
                luke_irc.append(msg.get('timestamp'))
        
        return {
            'prs_mentioning_luke': len(luke_prs),
            'emails_mentioning_luke': len(luke_emails),
            'irc_mentions_luke': len(luke_irc),
            'total_mentions': len(luke_prs) + len(luke_emails) + len(luke_irc),
            'note': 'Full case study requires detailed timeline reconstruction'
        }
    
    def _save_results(self, results: Dict[str, Any]):
        """Save analysis results."""
        result = create_result_template('transparency_gap_analysis', '1.0.0')
        result['metadata']['timestamp'] = datetime.now().isoformat()
        result['metadata']['data_sources'] = [
            'data/processed/enriched_prs.jsonl',
            'data/processed/cleaned_emails.jsonl',
            'data/processed/cleaned_irc.jsonl',
            'data/processed/external_pressure_indicators.json'
        ]
        result['data'] = results
        
        output_file = self.analysis_dir / 'transparency_gap_analysis.json'
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        logger.info(f"Results saved to {output_file}")


def main():
    """Main entry point."""
    analyzer = TransparencyGapAnalyzer()
    analyzer.run_analysis()
    return 0


if __name__ == '__main__':
    sys.exit(main())

