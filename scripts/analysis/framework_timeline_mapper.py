#!/usr/bin/env python3
"""
Framework Timeline Mapper

Maps all framework analyses (10 multi-framework + all earlier analyses) onto a chronological timeline.
Shows how governance patterns evolved over time.
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger
from src.utils.paths import get_analysis_dir

logger = setup_logger()


class FrameworkTimelineMapper:
    """Map all framework findings onto a chronological timeline."""
    
    def __init__(self):
        self.analysis_dir = get_analysis_dir()
        
        # All frameworks to map (10 multi-framework + earlier analyses)
        self.frameworks = {
            # Multi-framework analyses (10)
            'review_opacity_correlation': {
                'name': 'Principal-Agent Theory',
                'category': 'multi_framework',
                'file': 'review_opacity_correlation/review_opacity_correlation.json'
            },
            'homophily_analysis': {
                'name': 'Homophily Networks',
                'category': 'multi_framework',
                'file': 'homophily_analysis/homophily_analysis.json'
            },
            'attention_economics': {
                'name': 'Attention Economics',
                'category': 'multi_framework',
                'file': 'attention_economics/attention_economics.json'
            },
            'survivorship_bias': {
                'name': 'Survivorship Bias',
                'category': 'multi_framework',
                'file': 'survivorship_bias/survivorship_bias.json'
            },
            'toxicity_gradients': {
                'name': 'Toxicity Gradients',
                'category': 'multi_framework',
                'file': 'toxicity_gradients/toxicity_gradients.json'
            },
            'regulatory_arbitrage': {
                'name': 'Regulatory Arbitrage',
                'category': 'multi_framework',
                'file': 'regulatory_arbitrage/regulatory_arbitrage.json'
            },
            'institutional_isomorphism': {
                'name': 'Institutional Isomorphism',
                'category': 'multi_framework',
                'file': 'institutional_isomorphism/institutional_isomorphism.json'
            },
            'tournament_theory': {
                'name': 'Tournament Theory',
                'category': 'multi_framework',
                'file': 'tournament_theory/tournament_theory.json'
            },
            'preference_falsification': {
                'name': 'Preference Falsification',
                'category': 'multi_framework',
                'file': 'preference_falsification/preference_falsification.json'
            },
            'schelling_points': {
                'name': 'Schelling Points',
                'category': 'multi_framework',
                'file': 'schelling_points/schelling_points.json'
            },
            # Earlier analyses
            'power_concentration': {
                'name': 'Power Concentration',
                'category': 'earlier',
                'file': 'power_concentration/power_concentration_analysis.json'
            },
            'maintainer_premium': {
                'name': 'Maintainer Premium',
                'category': 'earlier',
                'file': 'maintainer_premium/statistics.json'
            },
            'nack_effectiveness': {
                'name': 'NACK Effectiveness',
                'category': 'earlier',
                'file': 'nack_effectiveness/nack_effectiveness_analysis.json'
            },
            'decision_criteria': {
                'name': 'Decision Criteria',
                'category': 'earlier',
                'file': 'decision_criteria/decision_criteria_analysis.json'
            },
            'transparency_gap': {
                'name': 'Transparency Gap',
                'category': 'earlier',
                'file': 'transparency_gap/transparency_gap_analysis.json'
            },
            'temporal_metrics': {
                'name': 'Temporal Metrics',
                'category': 'earlier',
                'file': 'temporal_metrics/temporal_analysis.json'
            },
            'communication_patterns': {
                'name': 'Communication Patterns',
                'category': 'earlier',
                'file': 'communication_patterns/communication_patterns_analysis.json'
            },
            'ostrom_compliance': {
                'name': 'Ostrom Compliance',
                'category': 'earlier',
                'file': 'ostrom_compliance/ostrom_compliance_analysis.json'
            },
            'luke_case_study': {
                'name': 'Luke Case Study',
                'category': 'earlier',
                'file': 'luke_case_study/luke_case_study_analysis.json'
            },
            'release_signing': {
                'name': 'Release Signing',
                'category': 'earlier',
                'file': 'release_signing/release_signing_analysis.json'
            }
        }
    
    def map_all_frameworks(self):
        """Map all frameworks onto timeline."""
        logger.info("=" * 60)
        logger.info("Framework Timeline Mapper")
        logger.info("=" * 60)
        
        timeline = defaultdict(lambda: {
            'year': None,
            'frameworks': {},
            'metrics': {},
            'events': []
        })
        
        # Load and map each framework
        for key, framework_info in self.frameworks.items():
            file_path = self.analysis_dir / framework_info['file']
            if not file_path.exists():
                logger.warning(f"Framework file not found: {file_path}")
                continue
            
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                logger.info(f"Mapping {framework_info['name']}...")
                self._map_framework(key, framework_info, data, timeline)
            except Exception as e:
                logger.error(f"Error mapping {framework_info['name']}: {e}")
        
        # Sort timeline by year
        timeline_sorted = dict(sorted(timeline.items()))
        
        # Generate outputs
        self._generate_timeline_json(timeline_sorted)
        self._generate_timeline_markdown(timeline_sorted)
        self._generate_metrics_timeline(timeline_sorted)
        
        logger.info("Timeline mapping complete")
        return timeline_sorted
    
    def _map_framework(self, key: str, framework_info: Dict, data: Dict, timeline: Dict):
        """Map a single framework's temporal data to timeline."""
        framework_name = framework_info['name']
        
        # Extract temporal data based on framework type
        if 'temporal_analysis' in data.get('data', {}):
            # Multi-framework with temporal_analysis
            temporal = data['data']['temporal_analysis']
            for year_str, year_data in temporal.items():
                year = int(year_str)
                if year not in timeline:
                    timeline[year]['year'] = year
                
                timeline[year]['frameworks'][framework_name] = {
                    'category': framework_info['category'],
                    'data': year_data
                }
        
        elif isinstance(data.get('data'), dict) and any(str(y).isdigit() for y in data['data'].keys()):
            # Framework with year keys in data
            for year_str, year_data in data['data'].items():
                if year_str.isdigit():
                    year = int(year_str)
                    if year not in timeline:
                        timeline[year]['year'] = year
                    
                    timeline[year]['frameworks'][framework_name] = {
                        'category': framework_info['category'],
                        'data': year_data
                    }
        
        elif key == 'temporal_metrics':
            # Temporal metrics has year keys directly
            for year_str, year_data in data.items():
                if year_str.isdigit():
                    year = int(year_str)
                    if year not in timeline:
                        timeline[year]['year'] = year
                    
                    timeline[year]['frameworks'][framework_name] = {
                        'category': framework_info['category'],
                        'data': year_data
                    }
        
        # Extract key metrics for each year
        self._extract_metrics(key, framework_name, data, timeline)
    
    def _extract_metrics(self, key: str, framework_name: str, data: Dict, timeline: Dict):
        """Extract key metrics from framework data."""
        framework_data = data.get('data', {})
        
        if key == 'review_opacity_correlation':
            # Zero reviews rate by year
            temporal = framework_data.get('temporal_analysis', {})
            for year_str, year_data in temporal.items():
                year = int(year_str)
                if 'zero_reviews_rate' in year_data:
                    timeline[year]['metrics']['zero_reviews_rate'] = year_data['zero_reviews_rate']
        
        elif key == 'homophily_analysis':
            # Homophily coefficient by year
            temporal = framework_data.get('temporal_analysis', {})
            for year_str, year_data in temporal.items():
                year = int(year_str)
                if 'homophily_coefficient' in year_data:
                    timeline[year]['metrics']['homophily_coefficient'] = year_data['homophily_coefficient']
        
        elif key == 'toxicity_gradients':
            # Toxicity scores by year
            temporal = framework_data.get('temporal_toxicity', {})
            for year_str, year_data in temporal.items():
                year = int(year_str)
                if 'non_maintainer_avg_score' in year_data:
                    timeline[year]['metrics']['toxicity_score'] = year_data['non_maintainer_avg_score']
        
        elif key == 'schelling_points':
            # Alternative mentions by year
            coordination = framework_data.get('coordination_signals', {})
            for year_str, year_data in coordination.items():
                year = int(year_str)
                if 'rate' in year_data:
                    timeline[year]['metrics']['alternative_mention_rate'] = year_data['rate']
            
            # Governance concerns by year
            legitimacy = framework_data.get('legitimacy_indicators', {})
            for year_str, year_data in legitimacy.items():
                year = int(year_str)
                if 'rate' in year_data:
                    timeline[year]['metrics']['governance_concern_rate'] = year_data['rate']
        
        elif key == 'temporal_metrics':
            # Extract all temporal metrics
            for year_str, year_data in data.items():
                if year_str.isdigit():
                    year = int(year_str)
                    if 'merge_rates' in year_data:
                        timeline[year]['metrics']['maintainer_merge_rate'] = year_data['merge_rates'].get('maintainer')
                        timeline[year]['metrics']['non_maintainer_merge_rate'] = year_data['merge_rates'].get('non_maintainer')
                    if 'self_merge_rate' in year_data:
                        timeline[year]['metrics']['self_merge_rate'] = year_data['self_merge_rate']
                    if 'review_requirements' in year_data:
                        timeline[year]['metrics']['maintainer_zero_reviews_pct'] = year_data['review_requirements'].get('maintainer_zero_pct')
                        timeline[year]['metrics']['non_maintainer_zero_reviews_pct'] = year_data['review_requirements'].get('non_maintainer_zero_pct')
                    if 'time_to_merge' in year_data:
                        timeline[year]['metrics']['maintainer_avg_time'] = year_data['time_to_merge'].get('maintainer_avg')
                        timeline[year]['metrics']['non_maintainer_avg_time'] = year_data['time_to_merge'].get('non_maintainer_avg')
        
        elif key == 'power_concentration':
            # Gini coefficient (overall, not by year, but we can add it to all years)
            review_influence = framework_data.get('review_influence', {})
            if 'gini_coefficient' in review_influence:
                gini = review_influence['gini_coefficient']
                # Add to all years (this is an overall metric)
                for year in timeline.keys():
                    timeline[year]['metrics']['review_gini'] = gini
    
    def _generate_timeline_json(self, timeline: Dict):
        """Generate JSON timeline output."""
        output_file = self.analysis_dir / 'framework_timeline.json'
        
        # Convert to list format for easier consumption
        timeline_list = []
        for year, data in timeline.items():
            timeline_list.append({
                'year': year,
                'frameworks': data['frameworks'],
                'metrics': data['metrics'],
                'events': data['events']
            })
        
        with open(output_file, 'w') as f:
            json.dump(timeline_list, f, indent=2)
        
        logger.info(f"Timeline JSON saved to {output_file}")
    
    def _generate_timeline_markdown(self, timeline: Dict):
        """Generate Markdown timeline report."""
        output_file = self.analysis_dir / 'framework_timeline.md'
        
        with open(output_file, 'w') as f:
            f.write("# Framework Timeline: Bitcoin Core Governance Evolution\n\n")
            f.write("**Generated**: " + datetime.now().isoformat() + "\n\n")
            f.write("This timeline maps all framework analyses onto a chronological view showing how governance patterns evolved over time.\n\n")
            
            f.write("## Timeline by Year\n\n")
            
            for year in sorted(timeline.keys()):
                data = timeline[year]
                f.write(f"### {year}\n\n")
                
                # Metrics
                if data['metrics']:
                    f.write("**Key Metrics:**\n")
                    for metric, value in data['metrics'].items():
                        if isinstance(value, float):
                            if value >= 1.0:
                                f.write(f"- {metric.replace('_', ' ').title()}: {value:.1%}\n")
                            else:
                                f.write(f"- {metric.replace('_', ' ').title()}: {value:.3f}\n")
                        else:
                            f.write(f"- {metric.replace('_', ' ').title()}: {value}\n")
                    f.write("\n")
                
                # Frameworks active this year
                if data['frameworks']:
                    f.write("**Active Frameworks:**\n")
                    for framework_name, framework_data in data['frameworks'].items():
                        f.write(f"- {framework_name} ({framework_data['category']})\n")
                    f.write("\n")
                
                f.write("---\n\n")
            
            # Summary statistics
            f.write("## Summary Statistics\n\n")
            f.write(f"**Years Analyzed**: {len(timeline)}\n")
            f.write(f"**Frameworks Mapped**: {sum(len(data['frameworks']) for data in timeline.values())}\n")
            f.write(f"**Total Framework-Year Observations**: {sum(len(data['frameworks']) for data in timeline.values())}\n")
        
        logger.info(f"Timeline Markdown saved to {output_file}")
    
    def _generate_metrics_timeline(self, timeline: Dict):
        """Generate metrics-only timeline for visualization."""
        output_file = self.analysis_dir / 'framework_metrics_timeline.json'
        
        metrics_timeline = []
        for year in sorted(timeline.keys()):
            data = timeline[year]
            if data['metrics']:
                metrics_timeline.append({
                    'year': year,
                    **data['metrics']
                })
        
        with open(output_file, 'w') as f:
            json.dump(metrics_timeline, f, indent=2)
        
        logger.info(f"Metrics timeline saved to {output_file}")


def main():
    mapper = FrameworkTimelineMapper()
    timeline = mapper.map_all_frameworks()
    
    print("\n" + "="*60)
    print("Framework Timeline Mapping Complete")
    print("="*60)
    print(f"\nYears mapped: {len(timeline)}")
    print(f"Frameworks: {len(mapper.frameworks)}")
    print(f"\nOutput files:")
    print(f"  - analysis/framework_timeline.json")
    print(f"  - analysis/framework_timeline.md")
    print(f"  - analysis/framework_metrics_timeline.json")


if __name__ == '__main__':
    main()

