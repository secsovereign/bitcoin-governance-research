"""Data quality tracking and reporting utilities."""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import defaultdict

from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir, get_project_root

logger = setup_logger()


class DataQualityTracker:
    """Tracks and reports data quality metrics."""
    
    def __init__(self):
        """Initialize quality tracker."""
        self.data_dir = get_data_dir()
        self.project_root = get_project_root()
        self.metrics = {
            'collection_date': datetime.now().isoformat(),
            'completeness': {},
            'identity_resolution': {},
            'maintainer_identification': {},
            'consistency': {},
            'accuracy': {}
        }
    
    def track_completeness(self, source: str, collected: int, expected: int = None):
        """Track data completeness for a source."""
        percentage = (collected / expected * 100) if expected else None
        
        self.metrics['completeness'][source] = {
            'collected': collected,
            'expected': expected,
            'percentage': round(percentage, 2) if percentage else None,
            'status': 'complete' if (expected is None or collected >= expected) else 'partial'
        }
    
    def track_identity_resolution(
        self,
        total_identities: int,
        high_confidence: int,
        medium_confidence: int,
        low_confidence: int,
        unmatched: int = 0
    ):
        """Track identity resolution quality."""
        self.metrics['identity_resolution'] = {
            'total_identities': total_identities,
            'high_confidence_matches': high_confidence,
            'medium_confidence_matches': medium_confidence,
            'low_confidence_matches': low_confidence,
            'unmatched': unmatched,
            'high_confidence_rate': round(high_confidence / total_identities * 100, 2) if total_identities > 0 else 0,
            'match_rate': round((total_identities - unmatched) / total_identities * 100, 2) if total_identities > 0 else 0
        }
    
    def track_maintainer_identification(
        self,
        identified_maintainers: int,
        high_confidence: int,
        medium_confidence: int,
        timeline_completeness: float
    ):
        """Track maintainer identification quality."""
        self.metrics['maintainer_identification'] = {
            'identified_maintainers': identified_maintainers,
            'high_confidence': high_confidence,
            'medium_confidence': medium_confidence,
            'low_confidence': identified_maintainers - high_confidence - medium_confidence,
            'timeline_completeness': round(timeline_completeness, 2),
            'high_confidence_rate': round(high_confidence / identified_maintainers * 100, 2) if identified_maintainers > 0 else 0
        }
    
    def track_consistency(self, checks: Dict[str, bool], details: Dict[str, Any] = None):
        """Track data consistency checks."""
        passed = sum(1 for v in checks.values() if v)
        total = len(checks)
        
        self.metrics['consistency'] = {
            'checks': checks,
            'passed': passed,
            'total': total,
            'pass_rate': round(passed / total * 100, 2) if total > 0 else 0,
            'details': details or {}
        }
    
    def track_accuracy(self, validation_errors: int, total_records: int, error_rate: float = None):
        """Track data accuracy."""
        if error_rate is None and total_records > 0:
            error_rate = validation_errors / total_records
        
        self.metrics['accuracy'] = {
            'validation_errors': validation_errors,
            'total_records': total_records,
            'error_rate': round(error_rate * 100, 4) if error_rate else None,
            'accuracy_rate': round((1 - error_rate) * 100, 4) if error_rate else None
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get quality summary."""
        return {
            'overall_status': self._calculate_overall_status(),
            'metrics': self.metrics,
            'recommendations': self._generate_recommendations()
        }
    
    def _calculate_overall_status(self) -> str:
        """Calculate overall quality status."""
        issues = []
        
        # Check completeness
        for source, data in self.metrics.get('completeness', {}).items():
            if data.get('percentage') and data['percentage'] < 50:
                issues.append(f"{source} completeness low ({data['percentage']}%)")
        
        # Check identity resolution
        id_res = self.metrics.get('identity_resolution', {})
        if id_res.get('match_rate', 100) < 80:
            issues.append(f"Identity resolution low ({id_res.get('match_rate', 0)}%)")
        
        # Check maintainer identification
        maint_id = self.metrics.get('maintainer_identification', {})
        if maint_id.get('high_confidence_rate', 100) < 70:
            issues.append(f"Maintainer identification confidence low ({maint_id.get('high_confidence_rate', 0)}%)")
        
        if not issues:
            return 'excellent'
        elif len(issues) <= 2:
            return 'good'
        elif len(issues) <= 4:
            return 'fair'
        else:
            return 'poor'
    
    def _generate_recommendations(self) -> List[str]:
        """Generate quality improvement recommendations."""
        recommendations = []
        
        # Completeness recommendations
        for source, data in self.metrics.get('completeness', {}).items():
            if data.get('percentage') and data['percentage'] < 100:
                recommendations.append(f"Continue collecting {source} data (currently {data['percentage']}% complete)")
        
        # Identity resolution recommendations
        id_res = self.metrics.get('identity_resolution', {})
        if id_res.get('unmatched', 0) > 0:
            recommendations.append(f"Review {id_res['unmatched']} unmatched identities for potential matches")
        
        # Maintainer identification recommendations
        maint_id = self.metrics.get('maintainer_identification', {})
        if maint_id.get('timeline_completeness', 1.0) < 0.8:
            recommendations.append("Improve maintainer timeline tracking for better historical accuracy")
        
        return recommendations
    
    def save_report(self, output_path: Optional[Path] = None):
        """Save quality report to file."""
        if output_path is None:
            output_path = self.data_dir / 'processed' / 'data_quality_report.json'
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        report = self.get_summary()
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Data quality report saved to {output_path}")
        return output_path
    
    def load_report(self, report_path: Optional[Path] = None) -> Dict[str, Any]:
        """Load existing quality report."""
        if report_path is None:
            report_path = self.data_dir / 'processed' / 'data_quality_report.json'
        
        if not report_path.exists():
            logger.warning(f"No existing quality report found at {report_path}")
            return {}
        
        with open(report_path, 'r') as f:
            return json.load(f)

