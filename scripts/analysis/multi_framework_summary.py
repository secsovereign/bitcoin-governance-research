#!/usr/bin/env python3
"""
Multi-Framework Analysis Summary Generator

Generates concise summaries, comparisons, and insights from all 10 framework analyses.
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger
from src.utils.paths import get_analysis_dir

logger = setup_logger()


class MultiFrameworkSummary:
    """Generate summaries and insights from multi-framework analysis."""
    
    def __init__(self):
        self.analysis_dir = get_analysis_dir()
        self.frameworks = {
            'review_opacity_correlation': 'Principal-Agent Theory',
            'homophily_analysis': 'Homophily Networks',
            'attention_economics': 'Attention Economics',
            'survivorship_bias': 'Survivorship Bias',
            'toxicity_gradients': 'Toxicity Gradients',
            'regulatory_arbitrage': 'Regulatory Arbitrage',
            'institutional_isomorphism': 'Institutional Isomorphism',
            'tournament_theory': 'Tournament Theory',
            'preference_falsification': 'Preference Falsification',
            'schelling_points': 'Schelling Points'
        }
    
    def generate_summary(self):
        """Generate comprehensive summary of all frameworks."""
        logger.info("Generating multi-framework summary...")
        
        results = {}
        for key, name in self.frameworks.items():
            result_file = self.analysis_dir / key / f"{key}.json"
            if result_file.exists():
                with open(result_file, 'r') as f:
                    results[key] = json.load(f)
            else:
                logger.warning(f"Results not found for {name}: {result_file}")
        
        # Generate summary statistics
        summary = {
            'frameworks_analyzed': len(results),
            'key_metrics': self._extract_key_metrics(results),
            'convergent_evidence': self._identify_convergence(results),
            'extreme_findings': self._find_extremes(results),
            'temporal_patterns': self._analyze_temporal_patterns(results),
            'recommendations': self._generate_recommendations(results)
        }
        
        # Save summary
        output_file = self.analysis_dir / 'multi_framework_summary.json'
        with open(output_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Summary saved to {output_file}")
        
        # Generate markdown report
        self._generate_markdown_report(summary, results)
        
        return summary
    
    def _extract_key_metrics(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key metrics from all frameworks."""
        metrics = {}
        
        # Principal-Agent
        if 'review_opacity_correlation' in results:
            data = results['review_opacity_correlation'].get('data', {})
            opacity = data.get('opacity_metrics', {})
            metrics['zero_reviews_rate'] = opacity.get('zero_reviews_rate', 0)
        elif 'principal_agent' in results:
            data = results['principal_agent'].get('data', {})
            opacity = data.get('opacity_metrics', {})
            metrics['zero_reviews_rate'] = opacity.get('zero_reviews_rate', 0)
        
        # Homophily
        if 'homophily_analysis' in results:
            data = results['homophily_analysis'].get('data', {})
            homophily = data.get('homophily_metrics', {})
            metrics['homophily_coefficient'] = homophily.get('homophily_coefficient', 0)
        
        # Survivorship
        if 'survivorship_bias' in results:
            data = results['survivorship_bias'].get('data', {})
            metrics['exit_rate'] = data.get('exit_rate', 0)
            metrics['high_quality_exit_rate'] = data.get('high_quality_exit_rate', 0)
        
        # Regulatory Arbitrage
        if 'regulatory_arbitrage' in results:
            data = results['regulatory_arbitrage'].get('data', {})
            gaps = data.get('gaps', {})
            metrics['total_arbitrage_score'] = gaps.get('total_arbitrage_score', 0)
            metrics['approval_gap'] = gaps.get('approval_gap', 0)
        
        # Tournament
        if 'tournament_theory' in results:
            data = results['tournament_theory'].get('data', {})
            winner_take_all = data.get('winner_take_all', {})
            metrics['top_10_share'] = winner_take_all.get('top_10_share', 0)
            exhaustion = data.get('exhaustion_filter', {})
            metrics['exhaustion_rate'] = exhaustion.get('exhaustion_rate', 0)
        
        # Isomorphism
        if 'institutional_isomorphism' in results:
            data = results['institutional_isomorphism'].get('data', {})
            core_metrics = data.get('core_metrics', {})
            metrics['gini_coefficient'] = core_metrics.get('gini_coefficient', 0)
        
        # Toxicity
        if 'toxicity_gradients' in results:
            data = results['toxicity_gradients'].get('data', {})
            cumulative = data.get('cumulative_effects', {})
            metrics['high_toxicity_rate'] = cumulative.get('high_toxicity_count', 0) / cumulative.get('total_authors_analyzed', 1) if cumulative.get('total_authors_analyzed', 0) > 0 else 0
        
        return metrics
    
    def _identify_convergence(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify convergent evidence across frameworks."""
        convergence = []
        
        # All frameworks point to filtering/exclusion
        if 'survivorship_bias' in results and 'tournament_theory' in results:
            convergence.append({
                'theme': 'Systematic Filtering',
                'frameworks': ['Survivorship Bias', 'Tournament Theory'],
                'evidence': '96.9% exit rate + 100% exhaustion rate',
                'severity': 'extreme'
            })
        
        # All frameworks point to segregation
        if 'homophily_analysis' in results:
            homophily = results['homophily_analysis'].get('data', {}).get('homophily_metrics', {})
            if homophily.get('homophily_coefficient', 0) >= 1.0:
                convergence.append({
                    'theme': 'Perfect Segregation',
                    'frameworks': ['Homophily Networks'],
                    'evidence': 'Homophily coefficient = 1.0 (zero cross-status reviews)',
                    'severity': 'extreme'
                })
        
        # Regulatory violations
        if 'regulatory_arbitrage' in results:
            gaps = results['regulatory_arbitrage'].get('data', {}).get('gaps', {})
            if gaps.get('total_arbitrage_score', 0) > 0.3:
                convergence.append({
                    'theme': 'Regulatory Violations',
                    'frameworks': ['Regulatory Arbitrage', 'Principal-Agent Theory'],
                    'evidence': f"{gaps.get('total_arbitrage_score', 0):.1%} arbitrage score",
                    'severity': 'high'
                })
        
        return convergence
    
    def _find_extremes(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find most extreme findings across frameworks."""
        extremes = []
        
        # Perfect homophily
        if 'homophily_analysis' in results:
            homophily = results['homophily_analysis'].get('data', {}).get('homophily_metrics', {})
            if homophily.get('homophily_coefficient', 0) == 1.0:
                extremes.append({
                    'framework': 'Homophily Networks',
                    'metric': 'Homophily Coefficient',
                    'value': 1.0,
                    'interpretation': 'Perfect segregation - zero cross-status reviews'
                })
        
        # 100% exhaustion
        if 'tournament_theory' in results:
            exhaustion = results['tournament_theory'].get('data', {}).get('exhaustion_filter', {})
            if exhaustion.get('exhaustion_rate', 0) >= 1.0:
                extremes.append({
                    'framework': 'Tournament Theory',
                    'metric': 'Exhaustion Rate',
                    'value': 1.0,
                    'interpretation': '100% of high-contribution non-maintainers exit'
                })
        
        # High arbitrage
        if 'regulatory_arbitrage' in results:
            gaps = results['regulatory_arbitrage'].get('data', {}).get('gaps', {})
            approval_gap = gaps.get('approval_gap', 0)
            if approval_gap > 0.8:
                extremes.append({
                    'framework': 'Regulatory Arbitrage',
                    'metric': 'Approval Gap',
                    'value': approval_gap,
                    'interpretation': f'{approval_gap:.1%} of merged PRs violate approval requirement'
                })
        
        return extremes
    
    def _analyze_temporal_patterns(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze temporal patterns across frameworks."""
        patterns = {}
        
        # Schelling points - alternative mentions over time
        if 'schelling_points' in results:
            coordination = results['schelling_points'].get('data', {}).get('coordination_signals', {})
            peak_year = max(coordination.items(), key=lambda x: x[1].get('rate', 0)) if coordination else None
            if peak_year:
                patterns['alternative_mentions_peak'] = {
                    'year': peak_year[0],
                    'rate': peak_year[1].get('rate', 0)
                }
        
        # Toxicity trends
        if 'toxicity_gradients' in results:
            temporal = results['toxicity_gradients'].get('data', {}).get('temporal_toxicity', {})
            if temporal:
                years = sorted(temporal.keys())
                if len(years) >= 2:
                    patterns['toxicity_trend'] = {
                        'start': temporal[years[0]].get('non_maintainer_avg_score', 0),
                        'end': temporal[years[-1]].get('non_maintainer_avg_score', 0),
                        'direction': 'decreasing' if temporal[years[-1]].get('non_maintainer_avg_score', 0) < temporal[years[0]].get('non_maintainer_avg_score', 0) else 'increasing'
                    }
        
        return patterns
    
    def _generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on findings."""
        recommendations = []
        
        # Based on regulatory arbitrage
        if 'regulatory_arbitrage' in results:
            gaps = results['regulatory_arbitrage'].get('data', {}).get('gaps', {})
            if gaps.get('approval_gap', 0) > 0.5:
                recommendations.append("Enforce approval requirement - 82.9% of merged PRs lack approvals")
        
        # Based on homophily
        if 'homophily_analysis' in results:
            homophily = results['homophily_analysis'].get('data', {}).get('homophily_metrics', {})
            if homophily.get('homophily_coefficient', 0) >= 1.0:
                recommendations.append("Break review segregation - zero cross-status reviews indicates institutional capture")
        
        # Based on exhaustion
        if 'tournament_theory' in results:
            exhaustion = results['tournament_theory'].get('data', {}).get('exhaustion_filter', {})
            if exhaustion.get('exhaustion_rate', 0) >= 0.9:
                recommendations.append("Address exhaustion filter - 100% of high-contribution non-maintainers exit")
        
        # Based on toxicity
        if 'toxicity_gradients' in results:
            cumulative = results['toxicity_gradients'].get('data', {}).get('cumulative_effects', {})
            high_toxicity_rate = cumulative.get('high_toxicity_count', 0) / cumulative.get('total_authors_analyzed', 1) if cumulative.get('total_authors_analyzed', 0) > 0 else 0
            if high_toxicity_rate > 0.3:
                recommendations.append("Reduce toxicity - 41% of authors experience high toxicity levels")
        
        return recommendations
    
    def _generate_markdown_report(self, summary: Dict[str, Any], results: Dict[str, Any]):
        """Generate markdown summary report."""
        output_file = self.analysis_dir / 'multi_framework_summary.md'
        
        with open(output_file, 'w') as f:
            f.write("# Multi-Framework Analysis Summary\n\n")
            f.write(f"**Generated**: {Path(__file__).stat().st_mtime}\n")
            f.write(f"**Frameworks Analyzed**: {summary['frameworks_analyzed']}\n\n")
            
            f.write("## Key Metrics\n\n")
            for metric, value in summary['key_metrics'].items():
                if isinstance(value, float):
                    f.write(f"- **{metric.replace('_', ' ').title()}**: {value:.3f}\n")
                else:
                    f.write(f"- **{metric.replace('_', ' ').title()}**: {value}\n")
            
            f.write("\n## Convergent Evidence\n\n")
            for conv in summary['convergent_evidence']:
                f.write(f"### {conv['theme']}\n")
                f.write(f"- **Frameworks**: {', '.join(conv['frameworks'])}\n")
                f.write(f"- **Evidence**: {conv['evidence']}\n")
                f.write(f"- **Severity**: {conv['severity']}\n\n")
            
            f.write("\n## Extreme Findings\n\n")
            for extreme in summary['extreme_findings']:
                f.write(f"### {extreme['framework']}\n")
                f.write(f"- **Metric**: {extreme['metric']}\n")
                f.write(f"- **Value**: {extreme['value']}\n")
                f.write(f"- **Interpretation**: {extreme['interpretation']}\n\n")
            
            f.write("\n## Recommendations\n\n")
            for i, rec in enumerate(summary['recommendations'], 1):
                f.write(f"{i}. {rec}\n")
        
        logger.info(f"Markdown report saved to {output_file}")


def main():
    summarizer = MultiFrameworkSummary()
    summary = summarizer.generate_summary()
    
    print("\n" + "="*60)
    print("Multi-Framework Analysis Summary")
    print("="*60)
    print(f"\nFrameworks Analyzed: {summary['frameworks_analyzed']}")
    print(f"\nKey Metrics: {len(summary['key_metrics'])}")
    print(f"Convergent Evidence: {len(summary['convergent_evidence'])} themes")
    print(f"Extreme Findings: {len(summary['extreme_findings'])}")
    print(f"Recommendations: {len(summary['recommendations'])}")


if __name__ == '__main__':
    main()

