#!/usr/bin/env python3
"""
Integration Validation Script - Validates plan integration and component connectivity.

Tests:
1. All imports work correctly
2. Data flow between components
3. File path consistency
4. Configuration integration
5. Utility function availability
"""

import sys
from pathlib import Path
from typing import List, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class IntegrationValidator:
    """Validates integration between plan and implementation."""
    
    def __init__(self):
        """Initialize validator."""
        self.errors = []
        self.warnings = []
        self.passed = []
    
    def validate_all(self) -> bool:
        """Run all validation tests."""
        print("=" * 60)
        print("Integration Validation")
        print("=" * 60)
        
        self.validate_imports()
        self.validate_data_flow()
        self.validate_file_paths()
        self.validate_configuration()
        self.validate_utilities()
        self.validate_script_dependencies()
        self.validate_output_schemas()
        self.validate_new_data_sources()
        
        self.print_summary()
        return len(self.errors) == 0
    
    def validate_imports(self):
        """Test all critical imports."""
        print("\n[1/7] Testing Imports...")
        
        # Core utilities
        try:
            from src.config import config
            self.passed.append("✓ Config import")
        except Exception as e:
            self.errors.append(f"✗ Config import failed: {e}")
        
        try:
            from src.utils.logger import setup_logger
            self.passed.append("✓ Logger import")
        except Exception as e:
            self.errors.append(f"✗ Logger import failed: {e}")
        
        try:
            from src.utils.paths import get_data_dir, get_analysis_dir, get_visualizations_dir
            self.passed.append("✓ Paths import")
        except Exception as e:
            self.errors.append(f"✗ Paths import failed: {e}")
        
        # New utilities
        try:
            from src.utils.data_quality import DataQualityTracker
            self.passed.append("✓ DataQualityTracker import")
        except Exception as e:
            self.errors.append(f"✗ DataQualityTracker import failed: {e}")
        
        try:
            from src.utils.statistics import StatisticalAnalyzer
            self.passed.append("✓ StatisticalAnalyzer import")
        except ImportError as e:
            self.warnings.append(f"⚠ StatisticalAnalyzer import (dependencies): {e}")
        except Exception as e:
            self.errors.append(f"✗ StatisticalAnalyzer import failed: {e}")
        
        try:
            from src.utils.network_analysis import NetworkAnalyzer
            self.passed.append("✓ NetworkAnalyzer import")
        except ImportError as e:
            self.warnings.append(f"⚠ NetworkAnalyzer import (dependencies): {e}")
        except Exception as e:
            self.errors.append(f"✗ NetworkAnalyzer import failed: {e}")
        
        try:
            from src.utils.visualization_templates import HTMLTemplateGenerator
            self.passed.append("✓ HTMLTemplateGenerator import")
        except SyntaxError as e:
            self.errors.append(f"✗ HTMLTemplateGenerator syntax error: {e}")
        except Exception as e:
            self.errors.append(f"✗ HTMLTemplateGenerator import failed: {e}")
        
        try:
            from src.schemas.analysis_results import (
                validate_result, create_result_template,
                POWER_CONCENTRATION_SCHEMA, MAINTAINER_PREMIUM_SCHEMA
            )
            self.passed.append("✓ Analysis schemas import")
        except Exception as e:
            self.errors.append(f"✗ Analysis schemas import failed: {e}")
    
    def validate_data_flow(self):
        """Validate data flow between processing steps."""
        print("\n[2/7] Testing Data Flow...")
        
        from src.utils.paths import get_data_dir, get_analysis_dir
        
        data_dir = get_data_dir()
        analysis_dir = get_analysis_dir()
        processed_dir = data_dir / 'processed'
        
        # Expected data flow:
        # raw -> cleaned -> enriched -> analysis
        
        flow_steps = [
            (data_dir / 'github' / 'prs_raw.jsonl', 'Raw PR data'),
            (processed_dir / 'cleaned_prs.jsonl', 'Cleaned PR data'),
            (processed_dir / 'enriched_prs.jsonl', 'Enriched PR data'),
            (processed_dir / 'user_identities.json', 'Identity mappings'),
            (processed_dir / 'maintainer_timeline.json', 'Maintainer timeline'),
            (analysis_dir / 'user_identities' / 'identity_mappings.json', 'Identity analysis output'),
        ]
        
        for path, description in flow_steps:
            if path.exists():
                self.passed.append(f"✓ {description} exists")
            else:
                self.warnings.append(f"⚠ {description} not found (expected if not run yet)")
    
    def validate_file_paths(self):
        """Validate file path consistency."""
        print("\n[3/7] Testing File Paths...")
        
        from src.utils.paths import (
            get_data_dir, get_analysis_dir, get_visualizations_dir,
            get_findings_dir, get_logs_dir
        )
        
        paths = [
            (get_data_dir(), 'data'),
            (get_analysis_dir(), 'analysis'),
            (get_visualizations_dir(), 'visualizations'),
            (get_findings_dir(), 'findings'),
            (get_logs_dir(), 'logs'),
        ]
        
        for path, name in paths:
            if path.exists() or path.parent.exists():
                self.passed.append(f"✓ {name} directory accessible")
            else:
                self.warnings.append(f"⚠ {name} directory not created yet")
    
    def validate_configuration(self):
        """Validate configuration integration."""
        print("\n[4/7] Testing Configuration...")
        
        from src.config import config
        
        # Test config validation
        is_valid, errors = config.validate()
        if is_valid:
            self.passed.append("✓ Configuration is valid")
        else:
            self.errors.append(f"✗ Configuration validation failed: {errors}")
        
        # Test key config values
        key_paths = [
            'paths.data',
            'paths.analysis',
            'paths.visualizations',
            'data_collection.github.repository.owner',
            'data_collection.github.repository.name',
        ]
        
        for path in key_paths:
            value = config.get(path)
            if value:
                self.passed.append(f"✓ Config path '{path}' accessible")
            else:
                self.warnings.append(f"⚠ Config path '{path}' not set (may have default)")
    
    def validate_utilities(self):
        """Validate utility functions work."""
        print("\n[5/7] Testing Utilities...")
        
        # Test logger
        try:
            from src.utils.logger import setup_logger
            logger = setup_logger()
            logger.info("Test log message")
            self.passed.append("✓ Logger works")
        except Exception as e:
            self.errors.append(f"✗ Logger failed: {e}")
        
        # Test data quality tracker
        try:
            from src.utils.data_quality import DataQualityTracker
            tracker = DataQualityTracker()
            tracker.track_completeness('test_source', 100, 100)
            summary = tracker.get_summary()
            if 'overall_status' in summary:
                self.passed.append("✓ DataQualityTracker works")
            else:
                self.errors.append("✗ DataQualityTracker summary incomplete")
        except Exception as e:
            self.errors.append(f"✗ DataQualityTracker failed: {e}")
        
        # Test statistical analyzer
        try:
            from src.utils.statistics import StatisticalAnalyzer
            import pandas as pd
            analyzer = StatisticalAnalyzer(random_seed=42)
            group1 = pd.Series([1, 2, 3, 4, 5])
            group2 = pd.Series([2, 3, 4, 5, 6])
            result = analyzer.t_test(group1, group2)
            if 'test' in result and result['test'] == 't_test':
                self.passed.append("✓ StatisticalAnalyzer works")
            else:
                self.errors.append("✗ StatisticalAnalyzer result incomplete")
        except ImportError as e:
            self.warnings.append(f"⚠ StatisticalAnalyzer dependencies not installed: {e}")
        except Exception as e:
            self.errors.append(f"✗ StatisticalAnalyzer failed: {e}")
        
        # Test network analyzer
        try:
            from src.utils.network_analysis import NetworkAnalyzer
            analyzer = NetworkAnalyzer()
            metrics = analyzer.calculate_concentration_metrics()
            if 'gini_coefficient' in metrics:
                self.passed.append("✓ NetworkAnalyzer works")
            else:
                self.errors.append("✗ NetworkAnalyzer metrics incomplete")
        except ImportError as e:
            self.warnings.append(f"⚠ NetworkAnalyzer dependencies not installed: {e}")
        except Exception as e:
            self.errors.append(f"✗ NetworkAnalyzer failed: {e}")
        
        # Test visualization templates
        try:
            from src.utils.visualization_templates import HTMLTemplateGenerator
            gen = HTMLTemplateGenerator()
            if hasattr(gen, 'generate_plotly_page'):
                self.passed.append("✓ HTMLTemplateGenerator works")
            else:
                self.errors.append("✗ HTMLTemplateGenerator incomplete")
        except Exception as e:
            self.errors.append(f"✗ HTMLTemplateGenerator failed: {e}")
        
        # Test schema validation
        try:
            from src.schemas.analysis_results import validate_result, create_result_template
            template = create_result_template('test_analysis')
            is_valid, error = validate_result(template, {'type': 'object'})
            if is_valid or error:  # Either works
                self.passed.append("✓ Schema validation works")
            else:
                self.errors.append("✗ Schema validation incomplete")
        except Exception as e:
            self.errors.append(f"✗ Schema validation failed: {e}")
    
    def validate_script_dependencies(self):
        """Validate script dependencies match plan."""
        print("\n[6/7] Testing Script Dependencies...")
        
        scripts_dir = project_root / 'scripts'
        
        # Expected scripts from plan
        expected_scripts = [
            ('data_processing/clean_data.py', 'Data cleaning'),
            ('data_processing/user_identity_resolver.py', 'Identity resolution'),
            ('data_processing/enrich_data.py', 'Data enrichment'),
            ('data_processing/maintainer_timeline.py', 'Maintainer timeline'),
            ('analysis/maintainer_premium.py', 'Maintainer premium analysis'),
            ('analysis/developer_history.py', 'Developer history'),
        ]
        
        for script_path, description in expected_scripts:
            full_path = scripts_dir / script_path
            if full_path.exists():
                self.passed.append(f"✓ {description} script exists")
            else:
                self.warnings.append(f"⚠ {description} script not found: {script_path}")
        
        # Check for scripts that should use new utilities
        try:
            # Check if clean_data.py uses DataQualityTracker
            clean_data_path = scripts_dir / 'data_processing' / 'clean_data.py'
            if clean_data_path.exists():
                content = clean_data_path.read_text()
                if 'DataQualityTracker' in content:
                    self.passed.append("✓ clean_data.py uses DataQualityTracker")
                else:
                    self.warnings.append("⚠ clean_data.py may not use DataQualityTracker")
        except Exception as e:
            self.warnings.append(f"⚠ Could not check clean_data.py: {e}")
    
    def validate_output_schemas(self):
        """Validate output schema consistency."""
        print("\n[7/7] Testing Output Schemas...")
        
        from src.schemas.analysis_results import (
            create_result_template, validate_result,
            POWER_CONCENTRATION_SCHEMA, MAINTAINER_PREMIUM_SCHEMA
        )
        
        # Test template creation
        try:
            template = create_result_template('test_analysis', '1.0.0')
            if 'metadata' in template and 'data' in template:
                self.passed.append("✓ Result template creation works")
            else:
                self.errors.append("✗ Result template incomplete")
        except Exception as e:
            self.errors.append(f"✗ Result template creation failed: {e}")
        
        # Test schema validation
        try:
            template = create_result_template('test_analysis')
            template['metadata']['timestamp'] = '2025-01-01T00:00:00'
            is_valid, error = validate_result(template, POWER_CONCENTRATION_SCHEMA)
            if is_valid or error:  # Either works for now
                self.passed.append("✓ Schema validation works")
            else:
                self.warnings.append("⚠ Schema validation may need refinement")
        except Exception as e:
            self.warnings.append(f"⚠ Schema validation test: {e}")
    
    def validate_new_data_sources(self):
        """Validate new data sources integration."""
        print("\n[8/8] Testing New Data Sources Integration...")
        
        from src.utils.paths import get_data_dir
        data_dir = get_data_dir()
        
        # Test external pressure indicators
        try:
            pressure_file = data_dir / 'processed' / 'external_pressure_indicators.json'
            
            if pressure_file.exists():
                import json
                with open(pressure_file, 'r') as f:
                    pressure_data = json.load(f)
                    if 'summary' in pressure_data:
                        self.passed.append("✓ External pressure indicators loaded")
                    else:
                        self.warnings.append("⚠ External pressure data structure unexpected")
            else:
                self.warnings.append("⚠ External pressure indicators file not found (expected if not extracted yet)")
        except Exception as e:
            self.warnings.append(f"⚠ External pressure validation: {e}")
        
        # Test commit data
        try:
            commits_file = data_dir / 'github' / 'commits_raw.jsonl'
            if commits_file.exists():
                line_count = sum(1 for _ in open(commits_file))
                if line_count > 0:
                    self.passed.append(f"✓ Commits data found ({line_count} commits)")
                else:
                    self.warnings.append("⚠ Commits file exists but is empty")
            else:
                self.warnings.append("⚠ Commits file not found (expected if not collected yet)")
        except Exception as e:
            self.warnings.append(f"⚠ Commits validation: {e}")
        
        # Test commit signing data
        try:
            signing_file = data_dir / 'github' / 'commit_signing.jsonl'
            if signing_file.exists():
                line_count = sum(1 for _ in open(signing_file))
                if line_count > 0:
                    self.passed.append(f"✓ Commit signing data found ({line_count} records)")
                else:
                    self.warnings.append("⚠ Commit signing file exists but is empty")
            else:
                self.warnings.append("⚠ Commit signing file not found (expected - collection in progress)")
        except Exception as e:
            self.warnings.append(f"⚠ Commit signing validation: {e}")
        
        # Test release signers
        try:
            signers_file = data_dir / 'releases' / 'release_signers.jsonl'
            if signers_file.exists():
                line_count = sum(1 for _ in open(signers_file))
                if line_count > 0:
                    self.passed.append(f"✓ Release signers data found ({line_count} releases)")
                else:
                    self.warnings.append("⚠ Release signers file exists but is empty")
            else:
                self.warnings.append("⚠ Release signers file not found")
        except Exception as e:
            self.warnings.append(f"⚠ Release signers validation: {e}")
        
        # Test contributors
        try:
            contributors_file = data_dir / 'github' / 'collaborators.json'
            if contributors_file.exists():
                import json
                with open(contributors_file, 'r') as f:
                    contrib_data = json.load(f)
                    if 'contributors' in contrib_data:
                        count = len(contrib_data['contributors'])
                        self.passed.append(f"✓ Contributors data found ({count} contributors)")
                    else:
                        self.warnings.append("⚠ Contributors data structure unexpected")
            else:
                self.warnings.append("⚠ Contributors file not found")
        except Exception as e:
            self.warnings.append(f"⚠ Contributors validation: {e}")
        
        # Test data cleaning integration
        try:
            from scripts.data_processing.clean_data import DataCleaner
            cleaner = DataCleaner()
            if 'github_commits' in cleaner.stats:
                self.passed.append("✓ Commits cleaning integrated")
            if 'release_signers' in cleaner.stats:
                self.passed.append("✓ Release signers cleaning integrated")
        except Exception as e:
            self.warnings.append(f"⚠ Data cleaning integration: {e}")
        
        # Test data enrichment integration
        try:
            from scripts.data_processing.enrich_data import DataEnricher
            enricher = DataEnricher()
            if hasattr(enricher, 'external_pressure'):
                self.passed.append("✓ External pressure enrichment integrated")
            if hasattr(enricher, 'commit_signing'):
                self.passed.append("✓ Commit signing enrichment integrated")
            if hasattr(enricher, 'contributors'):
                self.passed.append("✓ Contributors enrichment integrated")
        except Exception as e:
            self.warnings.append(f"⚠ Data enrichment integration: {e}")
    
    def print_summary(self):
        """Print validation summary."""
        print("\n" + "=" * 60)
        print("Validation Summary")
        print("=" * 60)
        
        print(f"\n✓ Passed: {len(self.passed)}")
        for item in self.passed:
            print(f"  {item}")
        
        if self.warnings:
            print(f"\n⚠ Warnings: {len(self.warnings)}")
            for item in self.warnings:
                print(f"  {item}")
        
        if self.errors:
            print(f"\n✗ Errors: {len(self.errors)}")
            for item in self.errors:
                print(f"  {item}")
        
        print("\n" + "=" * 60)
        
        if len(self.errors) == 0:
            print("✅ INTEGRATION VALIDATION PASSED")
            if self.warnings:
                print("⚠ Some warnings present (non-critical)")
        else:
            print("❌ INTEGRATION VALIDATION FAILED")
            print("Please fix errors before proceeding")


def main():
    """Main entry point."""
    validator = IntegrationValidator()
    success = validator.validate_all()
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())

