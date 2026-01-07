#!/usr/bin/env python3
"""
Generate Pattern Demonstration - Create clear visualizations of governance patterns over time.

Demonstrates patterns consistently and clearly:
1. Power concentration evolution
2. Decision-making pattern changes
3. Maintainer authority evolution
4. Transparency changes
5. Governance phase transitions
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
from src.utils.paths import get_analysis_dir, get_findings_dir, get_visualizations_dir
from src.utils.temporal_markers import TEMPORAL_EVENTS, get_events_in_period
from src.utils.visualization_templates import HTMLTemplateGenerator

logger = setup_logger()


class PatternDemonstrator:
    """Demonstrates governance patterns clearly over time."""
    
    def __init__(self):
        """Initialize demonstrator."""
        self.analysis_dir = get_analysis_dir()
        self.findings_dir = get_findings_dir()
        self.visualizations_dir = get_visualizations_dir()
        self.visualizations_dir.mkdir(parents=True, exist_ok=True)
        
        self.template_gen = HTMLTemplateGenerator()
    
    def run_demonstration(self):
        """Generate pattern demonstrations."""
        logger.info("=" * 60)
        logger.info("Pattern Demonstration Generation")
        logger.info("=" * 60)
        
        # Load analysis results
        analysis_results = self._load_analysis_results()
        
        # Generate pattern demonstrations
        self._demonstrate_power_concentration(analysis_results)
        self._demonstrate_decision_patterns(analysis_results)
        self._demonstrate_maintainer_evolution(analysis_results)
        self._demonstrate_transparency_evolution(analysis_results)
        self._demonstrate_governance_phases(analysis_results)
        
        # Generate summary visualization
        self._generate_summary_visualization(analysis_results)
        
        logger.info("Pattern demonstration complete")
    
    def _load_analysis_results(self) -> Dict[str, Any]:
        """Load all analysis results."""
        results = {}
        
        analysis_files = {
            'power_concentration': 'power_concentration/power_concentration_analysis.json',
            'maintainer_premium': 'maintainer_premium/statistics.json',
            'release_signing': 'release_signing/release_signing_analysis.json',
            'decision_criteria': 'decision_criteria/decision_criteria_analysis.json',
            'transparency_gap': 'transparency_gap/transparency_gap_analysis.json',
            'ostrom_compliance': 'ostrom_compliance/ostrom_compliance_analysis.json'
        }
        
        for key, file_path in analysis_files.items():
            full_path = self.analysis_dir / file_path
            if full_path.exists():
                with open(full_path, 'r') as f:
                    results[key] = json.load(f)
        
        return results
    
    def _demonstrate_power_concentration(self, analysis_results: Dict[str, Any]):
        """Demonstrate power concentration pattern over time."""
        power_data = analysis_results.get('power_concentration', {})
        temporal = power_data.get('results_payload', {}).get('temporal_evolution', {})
        by_year = temporal.get('by_year', [])
        
        if not by_year:
            logger.warning("No temporal power concentration data available")
            return
        
        # Prepare data for visualization
        years = [d['year'] for d in by_year]
        gini_values = [d.get('gini_coefficient', 0) for d in by_year]
        maintainer_counts = [d.get('unique_mergers', 0) for d in by_year]
        
        # Create visualization
        chart_data = {
            'type': 'scatter',
            'mode': 'lines+markers',
            'data': [
                {
                    'x': years,
                    'y': gini_values,
                    'name': 'Gini Coefficient',
                    'type': 'scatter',
                    'mode': 'lines+markers'
                },
                {
                    'x': years,
                    'y': maintainer_counts,
                    'name': 'Unique Maintainers',
                    'type': 'scatter',
                    'mode': 'lines+markers',
                    'yaxis': 'y2'
                }
            ],
            'layout': {
                'title': 'Power Concentration Evolution Over Time',
                'xaxis': {'title': 'Year'},
                'yaxis': {'title': 'Gini Coefficient'},
                'yaxis2': {'title': 'Maintainer Count', 'overlaying': 'y', 'side': 'right'}
            }
        }
        
        output_file = self.visualizations_dir / 'patterns' / 'power_concentration_evolution.html'
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.template_gen.generate_plotly_page(
            chart_data,
            output_file,
            title='Power Concentration Evolution',
            description='Shows how power concentration (Gini) and maintainer count have changed over time'
        )
        
        logger.info(f"Power concentration visualization saved to {output_file}")
    
    def _demonstrate_decision_patterns(self, analysis_results: Dict[str, Any]):
        """Demonstrate decision-making pattern evolution."""
        decision_data = analysis_results.get('decision_criteria', {})
        timeline_metrics = decision_data.get('results_payload', {}).get('timeline_metrics', {})
        
        # This would show decision speed, consistency, etc. over time
        # For now, create structure
        
        logger.info("Decision pattern demonstration prepared")
    
    def _demonstrate_maintainer_evolution(self, analysis_results: Dict[str, Any]):
        """Demonstrate maintainer authority evolution."""
        # Load maintainer timeline
        maintainer_file = Path(get_analysis_dir().parent) / 'data' / 'processed' / 'maintainer_timeline.json'
        
        if maintainer_file.exists():
            with open(maintainer_file, 'r') as f:
                maintainer_data = json.load(f)
                timeline_data = maintainer_data.get('maintainer_timeline', {})
                
                # Create timeline visualization
                logger.info(f"Maintainer evolution: {len(timeline_data)} maintainers tracked")
        
        logger.info("Maintainer evolution demonstration prepared")
    
    def _demonstrate_transparency_evolution(self, analysis_results: Dict[str, Any]):
        """Demonstrate transparency pattern evolution."""
        transparency_data = analysis_results.get('transparency_gap', {})
        
        # This would show transparency metrics over time
        logger.info("Transparency evolution demonstration prepared")
    
    def _demonstrate_governance_phases(self, analysis_results: Dict[str, Any]):
        """Demonstrate governance phase transitions."""
        # Create phase visualization with event markers
        phases = [
            {'name': 'Early Development', 'start': 2009, 'end': 2013},
            {'name': 'Blocksize Wars', 'start': 2014, 'end': 2017},
            {'name': 'Post-SegWit', 'start': 2018, 'end': 2021},
            {'name': 'Recent Era', 'start': 2022, 'end': 2024}
        ]
        
        # Add major events
        events = [
            {'year': 2015, 'event': 'Blocksize Wars Start'},
            {'year': 2017, 'event': 'SegWit Activation'},
            {'year': 2021, 'event': 'Taproot Activation'},
            {'year': 2022, 'event': 'Luke Maintainer Removal'}
        ]
        
        logger.info(f"Governance phases: {len(phases)} phases identified")
        logger.info(f"Major events: {len(events)} events marked")
    
    def _generate_summary_visualization(self, analysis_results: Dict[str, Any]):
        """Generate summary visualization showing all patterns."""
        # Create comprehensive pattern summary
        summary = {
            'patterns_identified': [
                'Power concentration evolution',
                'Maintainer authority changes',
                'Decision-making pattern shifts',
                'Transparency evolution',
                'Governance phase transitions'
            ],
            'key_insights': [
                'Power concentration shows [trend]',
                'Maintainer count [trend]',
                'Decision speed [trend]',
                'Transparency [trend]'
            ]
        }
        
        summary_file = self.findings_dir / 'pattern_summary.json'
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Pattern summary saved to {summary_file}")


def main():
    """Main entry point."""
    demonstrator = PatternDemonstrator()
    demonstrator.run_demonstration()
    return 0


if __name__ == '__main__':
    sys.exit(main())

