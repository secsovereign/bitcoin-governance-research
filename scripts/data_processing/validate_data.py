#!/usr/bin/env python3
"""
Data validation script - checks data quality and organization.

Validates collected data files for:
- JSON validity
- Required fields
- Data completeness
- File organization
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Any
from collections import Counter

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir

logger = setup_logger("validate_data", "INFO")


class DataValidator:
    """Validator for collected data."""
    
    def __init__(self):
        """Initialize validator."""
        self.data_dir = get_data_dir()
        self.errors = []
        self.warnings = []
        self.stats = {}
    
    def validate_jsonl_file(self, file_path: Path, required_fields: List[str] = None) -> Dict[str, Any]:
        """Validate a JSONL file."""
        logger.info(f"Validating {file_path.name}...")
        
        if not file_path.exists():
            self.errors.append(f"File not found: {file_path}")
            return {}
        
        stats = {
            'file_path': str(file_path),
            'total_lines': 0,
            'valid_json': 0,
            'invalid_json': 0,
            'missing_fields': Counter(),
            'file_size_mb': file_path.stat().st_size / (1024 * 1024),
        }
        
        required_fields = required_fields or []
        
        with open(file_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                stats['total_lines'] += 1
                
                if not line.strip():
                    continue
                
                try:
                    data = json.loads(line)
                    stats['valid_json'] += 1
                    
                    # Check required fields
                    for field in required_fields:
                        if field not in data:
                            stats['missing_fields'][field] += 1
                    
                except json.JSONDecodeError as e:
                    stats['invalid_json'] += 1
                    self.errors.append(f"Line {line_num} in {file_path.name}: Invalid JSON - {e}")
        
        # Calculate percentages
        if stats['total_lines'] > 0:
            stats['valid_percent'] = (stats['valid_json'] / stats['total_lines']) * 100
            stats['invalid_percent'] = (stats['invalid_json'] / stats['total_lines']) * 100
        else:
            stats['valid_percent'] = 0
            stats['invalid_percent'] = 0
        
        # Log results
        logger.info(f"  Total lines: {stats['total_lines']:,}")
        logger.info(f"  Valid JSON: {stats['valid_json']:,} ({stats['valid_percent']:.1f}%)")
        if stats['invalid_json'] > 0:
            logger.warning(f"  Invalid JSON: {stats['invalid_json']:,} ({stats['invalid_percent']:.1f}%)")
        logger.info(f"  File size: {stats['file_size_mb']:.2f} MB")
        
        if stats['missing_fields']:
            logger.warning(f"  Missing fields: {dict(stats['missing_fields'])}")
        
        return stats
    
    def validate_github_data(self):
        """Validate GitHub data files."""
        logger.info("=" * 60)
        logger.info("Validating GitHub Data")
        logger.info("=" * 60)
        
        github_dir = self.data_dir / 'github'
        
        # Validate PRs
        prs_file = github_dir / 'prs_raw.jsonl'
        if prs_file.exists():
            pr_required = ['number', 'title', 'state', 'author', 'created_at']
            stats = self.validate_jsonl_file(prs_file, pr_required)
            self.stats['prs'] = stats
        else:
            logger.warning("PRs file not found (collection may not have started)")
        
        # Validate Issues
        issues_file = github_dir / 'issues_raw.jsonl'
        if issues_file.exists():
            issue_required = ['number', 'title', 'state', 'author', 'created_at']
            stats = self.validate_jsonl_file(issues_file, issue_required)
            self.stats['issues'] = stats
        else:
            logger.warning("Issues file not found (collection may not have started)")
    
    def validate_mailing_list_data(self):
        """Validate mailing list data files."""
        logger.info("=" * 60)
        logger.info("Validating Mailing List Data")
        logger.info("=" * 60)
        
        ml_dir = self.data_dir / 'mailing_lists'
        
        emails_file = ml_dir / 'emails.jsonl'
        if emails_file.exists():
            email_required = ['list_name', 'from', 'date', 'subject', 'body']
            stats = self.validate_jsonl_file(emails_file, email_required)
            self.stats['emails'] = stats
        else:
            logger.warning("Emails file not found (collection may not have started)")
    
    def validate_directory_structure(self):
        """Validate that directory structure is correct."""
        logger.info("=" * 60)
        logger.info("Validating Directory Structure")
        logger.info("=" * 60)
        
        required_dirs = [
            self.data_dir / 'github',
            self.data_dir / 'mailing_lists',
            self.data_dir / 'luke_case',
            self.data_dir / 'processed',
        ]
        
        for dir_path in required_dirs:
            if dir_path.exists():
                logger.info(f"  ✓ {dir_path.name}/ exists")
            else:
                logger.warning(f"  - {dir_path.name}/ does not exist (will be created when needed)")
                dir_path.mkdir(parents=True, exist_ok=True)
    
    def generate_report(self):
        """Generate validation report."""
        logger.info("=" * 60)
        logger.info("Validation Summary")
        logger.info("=" * 60)
        
        if self.errors:
            logger.error(f"Errors: {len(self.errors)}")
            for error in self.errors[:10]:  # Show first 10
                logger.error(f"  - {error}")
            if len(self.errors) > 10:
                logger.error(f"  ... and {len(self.errors) - 10} more errors")
        else:
            logger.info("✓ No errors found")
        
        if self.warnings:
            logger.warning(f"Warnings: {len(self.warnings)}")
            for warning in self.warnings[:10]:
                logger.warning(f"  - {warning}")
        
        # Summary statistics
        if self.stats:
            logger.info("\nData Statistics:")
            for data_type, stats in self.stats.items():
                logger.info(f"\n{data_type.upper()}:")
                logger.info(f"  Total records: {stats.get('total_lines', 0):,}")
                logger.info(f"  Valid JSON: {stats.get('valid_json', 0):,}")
                logger.info(f"  File size: {stats.get('file_size_mb', 0):.2f} MB")
        
        return len(self.errors) == 0


def main():
    """Main entry point."""
    validator = DataValidator()
    
    # Validate structure
    validator.validate_directory_structure()
    
    # Validate data files
    validator.validate_github_data()
    validator.validate_mailing_list_data()
    
    # Generate report
    success = validator.generate_report()
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())

