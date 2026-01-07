#!/usr/bin/env python3
"""
Synthesize Timeline - Generate comprehensive timeline of governance events and patterns.

Combines all analysis results into a coherent chronological timeline showing:
1. Important governance events
2. Power concentration changes over time
3. Decision-making pattern evolution
4. Maintainer changes
5. Major milestones and crises
6. Pattern demonstrations over time
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
from src.utils.paths import get_analysis_dir, get_findings_dir
from src.utils.temporal_markers import TEMPORAL_EVENTS, get_events_in_period

logger = setup_logger()


class TimelineSynthesizer:
    """Synthesizes all analysis results into a comprehensive timeline."""
    
    def __init__(self):
        """Initialize synthesizer."""
        self.analysis_dir = get_analysis_dir()
        self.findings_dir = get_findings_dir()
        self.findings_dir.mkdir(parents=True, exist_ok=True)
    
    def run_synthesis(self):
        """Run timeline synthesis."""
        logger.info("=" * 60)
        logger.info("Timeline Synthesis")
        logger.info("=" * 60)
        
        # Load all analysis results
        analysis_results = self._load_all_analysis_results()
        
        # Build chronological timeline
        timeline = self._build_timeline(analysis_results)
        
        # Identify patterns
        patterns = self._identify_patterns(analysis_results, timeline)
        
        # Generate narrative
        narrative = self._generate_narrative(timeline, patterns)
        
        # Save results
        self._save_timeline(timeline, patterns, narrative)
        
        logger.info("Timeline synthesis complete")
    
    def _load_all_analysis_results(self) -> Dict[str, Any]:
        """Load all analysis results."""
        results = {}
        
        # Power concentration
        power_file = self.analysis_dir / 'power_concentration' / 'power_concentration_analysis.json'
        if power_file.exists():
            with open(power_file, 'r') as f:
                results['power_concentration'] = json.load(f)
        
        # Maintainer premium
        maintainer_file = self.analysis_dir / 'maintainer_premium' / 'statistics.json'
        if maintainer_file.exists():
            with open(maintainer_file, 'r') as f:
                results['maintainer_premium'] = json.load(f)
        
        # Release signing
        release_file = self.analysis_dir / 'release_signing' / 'release_signing_analysis.json'
        if release_file.exists():
            with open(release_file, 'r') as f:
                results['release_signing'] = json.load(f)
        
        # Decision criteria
        decision_file = self.analysis_dir / 'decision_criteria' / 'decision_criteria_analysis.json'
        if decision_file.exists():
            with open(decision_file, 'r') as f:
                results['decision_criteria'] = json.load(f)
        
        # Transparency gap
        transparency_file = self.analysis_dir / 'transparency_gap' / 'transparency_gap_analysis.json'
        if transparency_file.exists():
            with open(transparency_file, 'r') as f:
                results['transparency_gap'] = json.load(f)
        
        # Luke case study
        luke_file = self.analysis_dir / 'luke_case_study' / 'luke_case_study_analysis.json'
        if luke_file.exists():
            with open(luke_file, 'r') as f:
                results['luke_case_study'] = json.load(f)
        
        # Ostrom compliance
        ostrom_file = self.analysis_dir / 'ostrom_compliance' / 'ostrom_compliance_analysis.json'
        if ostrom_file.exists():
            with open(ostrom_file, 'r') as f:
                results['ostrom_compliance'] = json.load(f)
        
        return results
    
    def _build_timeline(self, analysis_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build chronological timeline of events."""
        timeline = []
        
        # Add temporal markers (major events)
        for event in TEMPORAL_EVENTS:
            timeline.append({
                'date': event['date'],
                'type': 'major_event',
                'category': event.get('category', 'governance'),
                'event': event['event'],
                'description': event['description'],
                'source': 'temporal_markers'
            })
        
        # Add power concentration changes (from temporal evolution)
        power_data = analysis_results.get('power_concentration', {})
        temporal_evolution = power_data.get('results_payload', {}).get('temporal_evolution', {})
        
        for year_data in temporal_evolution.get('by_year', []):
            timeline.append({
                'date': f"{year_data['year']}-01-01",
                'type': 'power_concentration',
                'category': 'governance',
                'event': 'power_concentration_change',
                'description': f"Gini coefficient: {year_data.get('gini_coefficient', 0):.3f}, {year_data.get('unique_mergers', 0)} maintainers",
                'metrics': {
                    'gini_coefficient': year_data.get('gini_coefficient'),
                    'unique_mergers': year_data.get('unique_mergers'),
                    'total_merges': year_data.get('total_merges')
                },
                'source': 'power_concentration_analysis'
            })
        
        # Add maintainer changes (from maintainer timeline)
        maintainer_timeline_file = Path(get_analysis_dir().parent) / 'data' / 'processed' / 'maintainer_timeline.json'
        if maintainer_timeline_file.exists():
            with open(maintainer_timeline_file, 'r') as f:
                maintainer_data = json.load(f)
                timeline_data = maintainer_data.get('maintainer_timeline', {})
                
                for maintainer_id, timeline_info in timeline_data.items():
                    for period in timeline_info.get('periods', []):
                        start = period.get('start')
                        if start:
                            timeline.append({
                                'date': start.split('T')[0],
                                'type': 'maintainer_change',
                                'category': 'governance',
                                'event': 'maintainer_added',
                                'description': f"Maintainer added: {maintainer_id}",
                                'maintainer': maintainer_id,
                                'source': 'maintainer_timeline'
                            })
                        
                        end = period.get('end')
                        if end:
                            timeline.append({
                                'date': end.split('T')[0],
                                'type': 'maintainer_change',
                                'category': 'governance',
                                'event': 'maintainer_removed',
                                'description': f"Maintainer removed: {maintainer_id}",
                                'maintainer': maintainer_id,
                                'source': 'maintainer_timeline'
                            })
        
        # Add Luke case study events
        luke_data = analysis_results.get('luke_case_study', {})
        luke_timeline = luke_data.get('results_payload', {}).get('timeline', [])
        
        for event in luke_timeline:
            if event.get('date'):
                timeline.append({
                    'date': event['date'].split('T')[0] if 'T' in event['date'] else event['date'],
                    'type': 'governance_event',
                    'category': 'case_study',
                    'event': 'luke_case',
                    'description': f"Luke case: {event.get('type', 'unknown')} on {event.get('platform', 'unknown')}",
                    'details': event,
                    'source': 'luke_case_study'
                })
        
        # Sort by date
        timeline.sort(key=lambda x: x.get('date', ''))
        
        return timeline
    
    def _identify_patterns(
        self,
        analysis_results: Dict[str, Any],
        timeline: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Identify patterns across time."""
        patterns = {
            'power_concentration_trend': 'stable',
            'maintainer_count_trend': 'stable',
            'decision_speed_trend': 'stable',
            'transparency_trend': 'stable',
            'governance_evolution': []
        }
        
        # Analyze power concentration trend
        power_data = analysis_results.get('power_concentration', {})
        temporal_evolution = power_data.get('results_payload', {}).get('temporal_evolution', {})
        by_year = temporal_evolution.get('by_year', [])
        
        if len(by_year) >= 2:
            first_gini = by_year[0].get('gini_coefficient', 0)
            last_gini = by_year[-1].get('gini_coefficient', 0)
            
            if last_gini > first_gini + 0.1:
                patterns['power_concentration_trend'] = 'increasing'
            elif last_gini < first_gini - 0.1:
                patterns['power_concentration_trend'] = 'decreasing'
        
        # Analyze maintainer count trend
        if len(by_year) >= 2:
            first_count = by_year[0].get('unique_mergers', 0)
            last_count = by_year[-1].get('unique_mergers', 0)
            
            if last_count > first_count:
                patterns['maintainer_count_trend'] = 'increasing'
            elif last_count < first_count:
                patterns['maintainer_count_trend'] = 'decreasing'
        
        # Identify governance phases
        phases = self._identify_governance_phases(timeline)
        patterns['governance_phases'] = phases
        
        return patterns
    
    def _identify_governance_phases(self, timeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify distinct governance phases."""
        phases = []
        
        # Phase 1: Early (2009-2013) - Small team, informal
        phases.append({
            'name': 'Early Development',
            'start': '2009-01-01',
            'end': '2013-12-31',
            'characteristics': ['small_team', 'informal', 'rapid_growth'],
            'key_events': ['inflation_bug', 'version_0.8_split']
        })
        
        # Phase 2: Blocksize Wars (2014-2017)
        phases.append({
            'name': 'Blocksize Wars Era',
            'start': '2014-01-01',
            'end': '2017-12-31',
            'characteristics': ['governance_conflict', 'fork_risk', 'polarization'],
            'key_events': ['blocksize_wars_start', 'segwit_activation', 'bitcoin_cash_fork']
        })
        
        # Phase 3: Post-SegWit (2018-2021)
        phases.append({
            'name': 'Post-SegWit Consolidation',
            'start': '2018-01-01',
            'end': '2021-12-31',
            'characteristics': ['consolidation', 'security_focus', 'taproot_preparation'],
            'key_events': ['inflation_bug_2018', 'taproot_activation']
        })
        
        # Phase 4: Recent (2022-present)
        phases.append({
            'name': 'Recent Era',
            'start': '2022-01-01',
            'end': '2024-12-31',
            'characteristics': ['institutional_maturity', 'governance_challenges'],
            'key_events': ['luke_maintainer_removal']
        })
        
        return phases
    
    def _generate_narrative(
        self,
        timeline: List[Dict[str, Any]],
        patterns: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate narrative summary of patterns."""
        narrative = {
            'summary': '',
            'key_findings': [],
            'pattern_demonstrations': [],
            'governance_evolution': []
        }
        
        # Generate summary
        power_trend = patterns.get('power_concentration_trend', 'stable')
        maintainer_trend = patterns.get('maintainer_count_trend', 'stable')
        
        narrative['summary'] = f"""
Bitcoin Core governance has evolved significantly over 16+ years. Power concentration 
trends {power_trend}, while maintainer count {maintainer_trend}. The analysis reveals 
consistent patterns in decision-making, transparency, and governance structure.
        """.strip()
        
        # Key findings
        narrative['key_findings'] = [
            {
                'finding': 'Power Concentration',
                'evidence': 'Gini coefficient analysis shows concentration levels',
                'pattern': power_trend
            },
            {
                'finding': 'Maintainer Authority',
                'evidence': 'Single-digit maintainers control merge authority',
                'pattern': 'consistent'
            },
            {
                'finding': 'Decision Transparency',
                'evidence': 'All decisions public, but criteria informal',
                'pattern': 'transparency_gap'
            }
        ]
        
        # Pattern demonstrations
        narrative['pattern_demonstrations'] = [
            {
                'pattern': 'Power Concentration Over Time',
                'demonstration': 'Gini coefficient by year shows evolution',
                'evidence_source': 'power_concentration_analysis'
            },
            {
                'pattern': 'Maintainer Premium',
                'demonstration': 'Maintainer PRs merge faster and more often',
                'evidence_source': 'maintainer_premium_analysis'
            },
            {
                'pattern': 'Informal Governance',
                'demonstration': 'No formal procedures for maintainer selection/removal',
                'evidence_source': 'transparency_gap_analysis'
            }
        ]
        
        return narrative
    
    def _save_timeline(
        self,
        timeline: List[Dict[str, Any]],
        patterns: Dict[str, Any],
        narrative: Dict[str, Any]
    ):
        """Save timeline and synthesis."""
        # Save full timeline
        timeline_file = self.findings_dir / 'governance_timeline.json'
        with open(timeline_file, 'w') as f:
            json.dump({
                'timeline': timeline,
                'total_events': len(timeline),
                'date_range': {
                    'start': timeline[0]['date'] if timeline else None,
                    'end': timeline[-1]['date'] if timeline else None
                }
            }, f, indent=2)
        
        logger.info(f"Timeline saved to {timeline_file}")
        
        # Save patterns
        patterns_file = self.findings_dir / 'governance_patterns.json'
        with open(patterns_file, 'w') as f:
            json.dump(patterns, f, indent=2)
        
        logger.info(f"Patterns saved to {patterns_file}")
        
        # Save narrative
        narrative_file = self.findings_dir / 'governance_narrative.json'
        with open(narrative_file, 'w') as f:
            json.dump(narrative, f, indent=2)
        
        logger.info(f"Narrative saved to {narrative_file}")
        
        # Generate markdown report
        self._generate_markdown_report(timeline, patterns, narrative)
    
    def _generate_markdown_report(
        self,
        timeline: List[Dict[str, Any]],
        patterns: Dict[str, Any],
        narrative: Dict[str, Any]
    ):
        """Generate markdown report of timeline and patterns."""
        report_file = self.findings_dir / 'governance_timeline_report.md'
        
        with open(report_file, 'w') as f:
            f.write("# Bitcoin Core Governance Timeline & Patterns\n\n")
            f.write("**Generated**: " + datetime.now().isoformat() + "\n\n")
            
            # Summary
            f.write("## Executive Summary\n\n")
            f.write(narrative['summary'] + "\n\n")
            
            # Key Findings
            f.write("## Key Findings\n\n")
            for finding in narrative.get('key_findings', []):
                f.write(f"### {finding['finding']}\n\n")
                f.write(f"- **Evidence**: {finding['evidence']}\n")
                f.write(f"- **Pattern**: {finding['pattern']}\n\n")
            
            # Pattern Demonstrations
            f.write("## Pattern Demonstrations\n\n")
            for demo in narrative.get('pattern_demonstrations', []):
                f.write(f"### {demo['pattern']}\n\n")
                f.write(f"- **Demonstration**: {demo['demonstration']}\n")
                f.write(f"- **Source**: {demo['evidence_source']}\n\n")
            
            # Governance Phases
            f.write("## Governance Phases\n\n")
            for phase in patterns.get('governance_phases', []):
                f.write(f"### {phase['name']} ({phase['start']} - {phase['end']})\n\n")
                f.write(f"**Characteristics**: {', '.join(phase['characteristics'])}\n\n")
                f.write(f"**Key Events**: {', '.join(phase['key_events'])}\n\n")
            
            # Timeline (first 50 events)
            f.write("## Timeline of Events\n\n")
            f.write("| Date | Type | Event | Description |\n")
            f.write("|------|------|-------|-------------|\n")
            
            for event in timeline[:50]:  # First 50 events
                date = event.get('date', '')
                event_type = event.get('type', '')
                event_name = event.get('event', '')
                description = event.get('description', '')[:100]  # Truncate
                f.write(f"| {date} | {event_type} | {event_name} | {description} |\n")
            
            if len(timeline) > 50:
                f.write(f"\n*... and {len(timeline) - 50} more events*\n")
        
        logger.info(f"Markdown report saved to {report_file}")


def main():
    """Main entry point."""
    synthesizer = TimelineSynthesizer()
    synthesizer.run_synthesis()
    return 0


if __name__ == '__main__':
    sys.exit(main())

