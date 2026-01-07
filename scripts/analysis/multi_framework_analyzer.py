#!/usr/bin/env python3
"""
Multi-Framework Analysis Orchestrator

Runs all 10 analytical frameworks on Bitcoin Core governance data.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger

logger = setup_logger()


class MultiFrameworkAnalyzer:
    """Orchestrates all framework analyses."""
    
    def __init__(self):
        self.frameworks = {
            'principal_agent': 'Principal-Agent Theory (Economics)',
            'homophily': 'Homophily Networks (Sociology)',
            'attention_economics': 'Attention Economics (Cognitive Science)',
            'survivorship_bias': 'Survivorship Bias (Statistics)',
            'toxicity_gradients': 'Toxicity Gradients (Social Psychology)',
            'regulatory_arbitrage': 'Regulatory Arbitrage (Law & Economics)',
            'institutional_isomorphism': 'Institutional Isomorphism (Organizational Theory)',
            'tournament_theory': 'Tournament Theory (Labor Economics)',
            'preference_falsification': 'Preference Falsification (Political Science)',
            'schelling_points': 'Schelling Points (Game Theory)'
        }
    
    def run_all(self):
        """Run all framework analyses."""
        logger.info("=" * 80)
        logger.info("Multi-Framework Analysis: Bitcoin Core Governance")
        logger.info("=" * 80)
        
        results = {}
        
        for framework_id, framework_name in self.frameworks.items():
            logger.info(f"\n{'=' * 80}")
            logger.info(f"Framework: {framework_name}")
            logger.info(f"{'=' * 80}")
            
            try:
                # Import and run each framework analyzer
                if framework_id == 'principal_agent':
                    # Already complete, just load results
                    logger.info("Principal-Agent Theory: Already complete")
                    results[framework_id] = {'status': 'complete', 'note': 'See PRINCIPAL_AGENT_ANALYSIS.md'}
                elif framework_id == 'homophily':
                    from scripts.analysis.homophily_analysis import HomophilyAnalyzer
                    analyzer = HomophilyAnalyzer()
                    analyzer.run_analysis()
                    results[framework_id] = {'status': 'complete'}
                elif framework_id == 'attention_economics':
                    from scripts.analysis.attention_economics import AttentionEconomicsAnalyzer
                    analyzer = AttentionEconomicsAnalyzer()
                    analyzer.run_analysis()
                    results[framework_id] = {'status': 'complete'}
                elif framework_id == 'survivorship_bias':
                    from scripts.analysis.survivorship_bias import SurvivorshipBiasAnalyzer
                    analyzer = SurvivorshipBiasAnalyzer()
                    analyzer.run_analysis()
                    results[framework_id] = {'status': 'complete'}
                elif framework_id == 'toxicity_gradients':
                    from scripts.analysis.toxicity_gradients import ToxicityGradientsAnalyzer
                    analyzer = ToxicityGradientsAnalyzer()
                    analyzer.run_analysis()
                    results[framework_id] = {'status': 'complete'}
                elif framework_id == 'regulatory_arbitrage':
                    from scripts.analysis.regulatory_arbitrage import RegulatoryArbitrageAnalyzer
                    analyzer = RegulatoryArbitrageAnalyzer()
                    analyzer.run_analysis()
                    results[framework_id] = {'status': 'complete'}
                elif framework_id == 'institutional_isomorphism':
                    from scripts.analysis.institutional_isomorphism import InstitutionalIsomorphismAnalyzer
                    analyzer = InstitutionalIsomorphismAnalyzer()
                    analyzer.run_analysis()
                    results[framework_id] = {'status': 'complete'}
                elif framework_id == 'tournament_theory':
                    from scripts.analysis.tournament_theory import TournamentTheoryAnalyzer
                    analyzer = TournamentTheoryAnalyzer()
                    analyzer.run_analysis()
                    results[framework_id] = {'status': 'complete'}
                elif framework_id == 'preference_falsification':
                    from scripts.analysis.preference_falsification import PreferenceFalsificationAnalyzer
                    analyzer = PreferenceFalsificationAnalyzer()
                    analyzer.run_analysis()
                    results[framework_id] = {'status': 'complete'}
                elif framework_id == 'schelling_points':
                    from scripts.analysis.schelling_points import SchellingPointsAnalyzer
                    analyzer = SchellingPointsAnalyzer()
                    analyzer.run_analysis()
                    results[framework_id] = {'status': 'complete'}
                
            except ImportError as e:
                logger.warning(f"Framework {framework_id} not yet implemented: {e}")
                results[framework_id] = {'status': 'pending', 'error': str(e)}
            except Exception as e:
                logger.error(f"Error running {framework_id}: {e}")
                results[framework_id] = {'status': 'error', 'error': str(e)}
        
        logger.info("\n" + "=" * 80)
        logger.info("Multi-Framework Analysis Complete")
        logger.info("=" * 80)
        
        return results


def main():
    analyzer = MultiFrameworkAnalyzer()
    results = analyzer.run_all()
    
    # Print summary
    logger.info("\nSummary:")
    for framework_id, result in results.items():
        status = result.get('status', 'unknown')
        logger.info(f"  {framework_id}: {status}")


if __name__ == '__main__':
    main()

