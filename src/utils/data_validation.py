"""Data validation framework with schema validation, type checking, and integrity checks."""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import re

from src.utils.logger import setup_logger

logger = setup_logger()


class DataValidator:
    """Validates data against schemas and checks integrity."""
    
    def __init__(self):
        """Initialize validator."""
        self.errors = []
        self.warnings = []
    
    def validate_jsonl_file(
        self,
        file_path: Path,
        schema: Optional[Dict[str, Any]] = None,
        required_fields: Optional[List[str]] = None,
        sample_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Validate JSONL file structure and content.
        
        Args:
            file_path: Path to JSONL file
            schema: Optional JSON schema to validate against
            required_fields: List of required field names
            sample_size: Number of records to validate (None = all)
        
        Returns:
            Validation report dictionary
        """
        self.errors = []
        self.warnings = []
        
        if not file_path.exists():
            self.errors.append(f"File does not exist: {file_path}")
            return self._generate_report()
        
        record_count = 0
        valid_records = 0
        invalid_records = 0
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if sample_size and record_count >= sample_size:
                        break
                    
                    record_count += 1
                    
                    # Validate JSON structure
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError as e:
                        self.errors.append(f"Line {line_num}: Invalid JSON - {e}")
                        invalid_records += 1
                        continue
                    
                    # Validate required fields
                    if required_fields:
                        missing = [f for f in required_fields if f not in record]
                        if missing:
                            self.errors.append(
                                f"Line {line_num}: Missing required fields: {missing}"
                            )
                            invalid_records += 1
                            continue
                    
                    # Validate schema if provided
                    if schema:
                        is_valid, error = self._validate_against_schema(record, schema)
                        if not is_valid:
                            self.errors.append(f"Line {line_num}: Schema validation failed - {error}")
                            invalid_records += 1
                            continue
                    
                    valid_records += 1
                    
        except Exception as e:
            self.errors.append(f"Error reading file: {e}")
            return self._generate_report()
        
        # Generate report
        report = self._generate_report()
        report['file_path'] = str(file_path)
        report['record_count'] = record_count
        report['valid_records'] = valid_records
        report['invalid_records'] = invalid_records
        report['validation_rate'] = valid_records / record_count if record_count > 0 else 0
        
        return report
    
    def validate_pr_data(self, pr: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate PR data structure."""
        errors = []
        
        # Required fields
        required = ['number', 'author', 'created_at', 'state']
        for field in required:
            if field not in pr:
                errors.append(f"Missing required field: {field}")
        
        # Validate types
        if 'number' in pr and not isinstance(pr['number'], int):
            errors.append("Field 'number' must be integer")
        
        if 'created_at' in pr:
            if not self._validate_timestamp(pr['created_at']):
                errors.append("Field 'created_at' must be valid ISO timestamp")
        
        if 'state' in pr:
            valid_states = ['open', 'closed', 'merged']
            if pr['state'] not in valid_states:
                errors.append(f"Field 'state' must be one of {valid_states}")
        
        # Validate structure
        if 'reviews' in pr and not isinstance(pr['reviews'], list):
            errors.append("Field 'reviews' must be a list")
        
        if 'comments' in pr and not isinstance(pr['comments'], list):
            errors.append("Field 'comments' must be a list")
        
        return len(errors) == 0, errors
    
    def validate_identity_mapping(self, mapping: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate identity mapping structure."""
        errors = []
        
        # Check structure
        if not isinstance(mapping, dict):
            errors.append("Identity mapping must be a dictionary")
            return False, errors
        
        # Check each unified identity
        for unified_id, platforms in mapping.items():
            if not isinstance(platforms, dict):
                errors.append(f"Platforms for {unified_id} must be a dictionary")
                continue
            
            # Check platform structure
            for platform, ids in platforms.items():
                if not isinstance(ids, list):
                    errors.append(f"IDs for {platform} must be a list")
                elif not all(isinstance(id_val, str) for id_val in ids):
                    errors.append(f"All IDs for {platform} must be strings")
        
        return len(errors) == 0, errors
    
    def validate_maintainer_timeline(self, timeline: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate maintainer timeline structure."""
        errors = []
        
        if 'maintainer_timeline' not in timeline:
            errors.append("Missing 'maintainer_timeline' key")
            return False, errors
        
        timeline_data = timeline['maintainer_timeline']
        
        for user_id, data in timeline_data.items():
            # Check required fields
            if 'estimated_start' not in data:
                errors.append(f"Missing 'estimated_start' for {user_id}")
            
            # Check periods
            if 'periods' in data:
                if not isinstance(data['periods'], list):
                    errors.append(f"'periods' must be a list for {user_id}")
                else:
                    for period in data['periods']:
                        if 'start' not in period:
                            errors.append(f"Period missing 'start' for {user_id}")
                        if not self._validate_timestamp(period['start']):
                            errors.append(f"Invalid 'start' timestamp for {user_id}")
        
        return len(errors) == 0, errors
    
    def check_data_integrity(
        self,
        data_dir: Path,
        checks: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Perform integrity checks on data directory.
        
        Args:
            data_dir: Data directory path
            checks: List of checks to perform (None = all)
        
        Returns:
            Integrity check report
        """
        if checks is None:
            checks = ['duplicates', 'timestamps', 'references', 'completeness']
        
        report = {
            'checks_performed': checks,
            'results': {},
            'errors': [],
            'warnings': []
        }
        
        if 'duplicates' in checks:
            report['results']['duplicates'] = self._check_duplicates(data_dir)
        
        if 'timestamps' in checks:
            report['results']['timestamps'] = self._check_timestamps(data_dir)
        
        if 'references' in checks:
            report['results']['references'] = self._check_references(data_dir)
        
        if 'completeness' in checks:
            report['results']['completeness'] = self._check_completeness(data_dir)
        
        return report
    
    def _validate_against_schema(
        self,
        record: Dict[str, Any],
        schema: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """Simple schema validation (basic implementation)."""
        # Check required fields
        if 'required' in schema:
            for field in schema['required']:
                if field not in record:
                    return False, f"Missing required field: {field}"
        
        # Check field types
        if 'properties' in schema:
            for field, field_schema in schema['properties'].items():
                if field in record:
                    expected_type = field_schema.get('type')
                    if expected_type:
                        actual_type = type(record[field]).__name__
                        type_map = {
                            'string': 'str',
                            'integer': 'int',
                            'number': ('int', 'float'),
                            'boolean': 'bool',
                            'array': 'list',
                            'object': 'dict'
                        }
                        
                        if expected_type in type_map:
                            expected = type_map[expected_type]
                            if isinstance(expected, tuple):
                                if actual_type not in expected:
                                    return False, f"Field '{field}' type mismatch: expected {expected_type}, got {actual_type}"
                            elif actual_type != expected:
                                return False, f"Field '{field}' type mismatch: expected {expected_type}, got {actual_type}"
        
        return True, None
    
    def _validate_timestamp(self, timestamp: Any) -> bool:
        """Validate ISO 8601 timestamp."""
        if not isinstance(timestamp, str):
            return False
        
        try:
            datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return True
        except (ValueError, AttributeError):
            return False
    
    def _check_duplicates(self, data_dir: Path) -> Dict[str, Any]:
        """Check for duplicate records."""
        duplicates = {}
        
        # Check PRs
        prs_file = data_dir / 'processed' / 'cleaned_prs.jsonl'
        if prs_file.exists():
            pr_numbers = {}
            with open(prs_file, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        pr = json.loads(line)
                        pr_num = pr.get('number')
                        if pr_num:
                            if pr_num in pr_numbers:
                                if pr_num not in duplicates:
                                    duplicates[pr_num] = []
                                duplicates[pr_num].append(pr_numbers[pr_num])
                                duplicates[pr_num].append(line_num)
                            else:
                                pr_numbers[pr_num] = line_num
                    except Exception:
                        pass
        
        return {
            'found': len(duplicates) > 0,
            'count': len(duplicates),
            'details': duplicates
        }
    
    def _check_timestamps(self, data_dir: Path) -> Dict[str, Any]:
        """Check timestamp consistency."""
        issues = []
        
        prs_file = data_dir / 'processed' / 'cleaned_prs.jsonl'
        if prs_file.exists():
            with open(prs_file, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        pr = json.loads(line)
                        created = pr.get('created_at')
                        merged = pr.get('merged_at')
                        
                        if created and merged:
                            try:
                                created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                                merged_dt = datetime.fromisoformat(merged.replace('Z', '+00:00'))
                                if merged_dt < created_dt:
                                    issues.append({
                                        'pr': pr.get('number'),
                                        'line': line_num,
                                        'issue': 'merged_at before created_at'
                                    })
                            except Exception:
                                pass
                    except Exception:
                        pass
        
        return {
            'found': len(issues) > 0,
            'count': len(issues),
            'details': issues[:10]  # Limit to first 10
        }
    
    def _check_references(self, data_dir: Path) -> Dict[str, Any]:
        """Check reference integrity (e.g., PR references)."""
        issues = []
        
        # This would check things like:
        # - PR references in comments
        # - User references in reviews
        # - Issue references in PRs
        
        return {
            'found': len(issues) > 0,
            'count': len(issues),
            'details': issues
        }
    
    def _check_completeness(self, data_dir: Path) -> Dict[str, Any]:
        """Check data completeness."""
        completeness = {}
        
        files_to_check = [
            ('github/prs_raw.jsonl', 'PRs'),
            ('github/issues_raw.jsonl', 'Issues'),
            ('mailing_lists/emails.jsonl', 'Emails'),
            ('irc/messages.jsonl', 'IRC Messages'),
        ]
        
        for file_path, name in files_to_check:
            full_path = data_dir / file_path
            if full_path.exists():
                count = sum(1 for _ in open(full_path))
                completeness[name] = {
                    'exists': True,
                    'record_count': count
                }
            else:
                completeness[name] = {
                    'exists': False,
                    'record_count': 0
                }
        
        return completeness
    
    def _generate_report(self) -> Dict[str, Any]:
        """Generate validation report."""
        return {
            'valid': len(self.errors) == 0,
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
            'errors': self.errors,
            'warnings': self.warnings
        }

