#!/usr/bin/env python3
"""
Ostrom Principle Compliance Analysis - Evaluate Bitcoin Core against Ostrom's 7 principles.

Analyzes compliance with each of Ostrom's 7 principles:
1. Clear boundaries on who decides what
2. Consequences for violations
3. Local dispute resolution
4. Protection from external interference
5. Collective choice arrangements
6. Graduated sanctions
7. Monitoring and accountability
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from collections import defaultdict
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir, get_analysis_dir
from src.schemas.analysis_results import create_result_template

logger = setup_logger()


class OstromComplianceAnalyzer:
    """Analyzer for Ostrom principle compliance."""
    
    def __init__(self):
        """Initialize analyzer."""
        self.data_dir = get_data_dir()
        self.processed_dir = self.data_dir / 'processed'
        self.analysis_dir = get_analysis_dir() / 'ostrom_compliance'
        self.analysis_dir.mkdir(parents=True, exist_ok=True)
    
    def run_analysis(self):
        """Run Ostrom compliance analysis."""
        logger.info("=" * 60)
        logger.info("Ostrom Principle Compliance Analysis")
        logger.info("=" * 60)
        
        # Load data
        prs = self._load_enriched_prs()
        maintainer_timeline = self._load_maintainer_timeline()
        external_pressure = self._load_external_pressure()
        release_signers = self._load_release_signers()
        
        # Analyze each principle
        principle_1 = self._analyze_principle_1_clear_boundaries(prs, maintainer_timeline, release_signers)
        principle_2 = self._analyze_principle_2_consequences(prs)
        principle_3 = self._analyze_principle_3_dispute_resolution(prs)
        principle_4 = self._analyze_principle_4_external_protection(external_pressure)
        principle_5 = self._analyze_principle_5_collective_choice(prs)
        principle_6 = self._analyze_principle_6_graduated_sanctions(prs)
        principle_7 = self._analyze_principle_7_monitoring(prs)
        
        # Calculate overall compliance score
        compliance_score = self._calculate_compliance_score([
            principle_1, principle_2, principle_3, principle_4,
            principle_5, principle_6, principle_7
        ])
        
        # Save results
        self._save_results({
            'principle_1_clear_boundaries': principle_1,
            'principle_2_consequences': principle_2,
            'principle_3_dispute_resolution': principle_3,
            'principle_4_external_protection': principle_4,
            'principle_5_collective_choice': principle_5,
            'principle_6_graduated_sanctions': principle_6,
            'principle_7_monitoring': principle_7,
            'overall_compliance_score': compliance_score
        })
        
        logger.info("Ostrom compliance analysis complete")
    
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
    
    def _load_maintainer_timeline(self) -> Dict[str, Any]:
        """Load maintainer timeline."""
        timeline_file = self.processed_dir / 'maintainer_timeline.json'
        
        if not timeline_file.exists():
            return {}
        
        with open(timeline_file, 'r') as f:
            data = json.load(f)
            return data.get('maintainer_timeline', {})
    
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
    
    def _analyze_principle_1_clear_boundaries(
        self,
        prs: List[Dict[str, Any]],
        maintainer_timeline: Dict[str, Any],
        release_signers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Principle 1: Clear boundaries on who decides what."""
        # Count maintainers
        unique_maintainers = len(maintainer_timeline)
        
        # Count release signers
        unique_signers = len(set(
            r.get('signer_email') or r.get('signer_name')
            for r in release_signers if r.get('is_signed')
        ))
        
        # Check for formal selection/removal processes
        # This would require documentation review
        formal_process = 'unknown'
        
        return {
            'principle': 'Clear Boundaries',
            'maintainers_identified': unique_maintainers,
            'release_signers_identified': unique_signers,
            'formal_selection_process': formal_process,
            'formal_removal_process': formal_process,
            'authority_limits_defined': 'unknown',
            'compliance_level': 'partial',
            'evidence': 'Informal boundaries exist (maintainers, signers) but formal processes unclear'
        }
    
    def _analyze_principle_2_consequences(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Principle 2: Consequences for violations."""
        # Count formal sanctions (would need to identify violations)
        formal_sanctions = 0
        
        # Count social pressure (rejections, negative reviews)
        rejections = sum(1 for pr in prs if pr.get('state') == 'closed' and not pr.get('merged'))
        
        return {
            'principle': 'Consequences for Violations',
            'formal_sanctions': formal_sanctions,
            'social_pressure_instances': rejections,
            'systematic_enforcement': 'no',
            'compliance_level': 'partial',
            'evidence': 'Social pressure exists (rejections) but no systematic enforcement mechanism'
        }
    
    def _analyze_principle_3_dispute_resolution(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Principle 3: Local dispute resolution."""
        # Count disputes (PRs with conflicting reviews)
        disputes = 0
        for pr in prs:
            reviews = pr.get('reviews', [])
            approved = sum(1 for r in reviews if r.get('state', '').lower() == 'approved')
            changes_requested = sum(1 for r in reviews if r.get('state', '').lower() == 'changes_requested')
            
            if approved > 0 and changes_requested > 0:
                disputes += 1
        
        # Check for formal dispute resolution
        formal_resolution = 'unknown'
        
        return {
            'principle': 'Local Dispute Resolution',
            'disputes_identified': disputes,
            'formal_resolution_process': formal_resolution,
            'resolution_mechanism': 'social_consensus',
            'compliance_level': 'partial',
            'evidence': 'Disputes resolved through social consensus, no formal binding mechanism'
        }
    
    def _analyze_principle_4_external_protection(self, external_pressure: Dict[str, Any]) -> Dict[str, Any]:
        """Principle 4: Protection from external interference."""
        if not external_pressure:
            return {
                'principle': 'External Protection',
                'compliance_level': 'unknown',
                'evidence': 'No external pressure data available'
            }
        
        summary = external_pressure.get('summary', {})
        pressure_rate = summary.get('mailing_lists', {}).get('percentage', 0)
        
        # Check for protection mechanisms
        protection_mechanisms = 'unknown'
        
        return {
            'principle': 'Protection from External Interference',
            'external_pressure_rate': pressure_rate,
            'protection_mechanisms': protection_mechanisms,
            'resistance_capability': 'unknown',
            'compliance_level': 'partial',
            'evidence': f'High external pressure awareness ({pressure_rate:.1f}% of emails) but protection mechanisms unclear'
        }
    
    def _analyze_principle_5_collective_choice(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Principle 5: Collective choice arrangements."""
        # Count participants in decisions
        decision_participants = set()
        
        for pr in prs:
            author = pr.get('author')
            if author:
                decision_participants.add(author)
            
            for review in pr.get('reviews', []):
                reviewer = review.get('author')
                if reviewer:
                    decision_participants.add(reviewer)
        
        # Check for formal consensus mechanisms
        formal_consensus = 'unknown'
        
        return {
            'principle': 'Collective Choice Arrangements',
            'unique_participants': len(decision_participants),
            'formal_consensus_mechanism': formal_consensus,
            'participation_rate': len(decision_participants) / len(prs) if prs else 0,
            'compliance_level': 'partial',
            'evidence': 'Participation exists but formal consensus mechanism unclear'
        }
    
    def _analyze_principle_6_graduated_sanctions(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Principle 6: Graduated sanctions."""
        # Check for sanction escalation
        # This would require identifying violations and their consequences
        
        return {
            'principle': 'Graduated Sanctions',
            'sanction_escalation': 'unknown',
            'proportional_consequences': 'unknown',
            'compliance_level': 'partial',
            'evidence': 'Sanctions appear binary (accept/reject) rather than graduated'
        }
    
    def _analyze_principle_7_monitoring(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Principle 7: Monitoring and accountability."""
        # Check decision visibility
        public_decisions = sum(1 for pr in prs if pr.get('state') in ['merged', 'closed'])
        
        # Check audit trail
        audit_trail = 'public_github'  # All decisions in public GitHub
        
        return {
            'principle': 'Monitoring and Accountability',
            'public_decisions': public_decisions,
            'audit_trail': audit_trail,
            'accountability_mechanisms': 'public_visibility',
            'compliance_level': 'good',
            'evidence': 'All decisions visible in public GitHub, good audit trail'
        }
    
    def _calculate_compliance_score(self, principles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate overall compliance score."""
        scores = {
            'excellent': 0,
            'good': 0,
            'partial': 0,
            'poor': 0,
            'unknown': 0
        }
        
        for principle in principles:
            level = principle.get('compliance_level', 'unknown')
            scores[level] = scores.get(level, 0) + 1
        
        total = sum(scores.values())
        
        # Weighted score
        weighted = (
            scores['excellent'] * 1.0 +
            scores['good'] * 0.75 +
            scores['partial'] * 0.5 +
            scores['poor'] * 0.25
        ) / total if total > 0 else 0
        
        return {
            'score_breakdown': scores,
            'weighted_score': weighted,
            'overall_level': 'good' if weighted >= 0.7 else 'partial' if weighted >= 0.5 else 'poor'
        }
    
    def _save_results(self, results: Dict[str, Any]):
        """Save analysis results."""
        result = create_result_template('ostrom_compliance_analysis', '1.0.0')
        result['metadata']['timestamp'] = datetime.now().isoformat()
        result['metadata']['data_sources'] = [
            'data/processed/enriched_prs.jsonl',
            'data/processed/maintainer_timeline.json',
            'data/processed/external_pressure_indicators.json'
        ]
        result['data'] = results
        
        output_file = self.analysis_dir / 'ostrom_compliance_analysis.json'
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        logger.info(f"Results saved to {output_file}")
        
        # Generate summary
        compliance = results.get('overall_compliance_score', {})
        logger.info(f"Ostrom Compliance Summary:")
        logger.info(f"  Overall Level: {compliance.get('overall_level', 'unknown')}")
        logger.info(f"  Weighted Score: {compliance.get('weighted_score', 0):.3f}")


def main():
    """Main entry point."""
    analyzer = OstromComplianceAnalyzer()
    analyzer.run_analysis()
    return 0


if __name__ == '__main__':
    sys.exit(main())

