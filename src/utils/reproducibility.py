"""Reproducible analysis system with random seed management and version pinning."""

import json
import random
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import platform
import sys

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

from src.utils.logger import setup_logger
from src.utils.paths import get_analysis_dir

logger = setup_logger()


class ReproducibilityManager:
    """Manages reproducibility settings for analysis."""
    
    DEFAULT_SEED = 42
    
    def __init__(self, seed: int = DEFAULT_SEED):
        """Initialize reproducibility manager."""
        self.seed = seed
        self.analysis_dir = get_analysis_dir()
        self.reproducibility_info = self._capture_environment()
    
    def set_seed(self, seed: Optional[int] = None):
        """
        Set random seed for reproducibility.
        
        Args:
            seed: Random seed (uses default if None)
        """
        if seed is None:
            seed = self.seed
        
        random.seed(seed)
        if HAS_NUMPY:
            np.random.seed(seed)
        
        logger.info(f"Random seed set to: {seed}")
    
    def capture_analysis_metadata(
        self,
        analysis_name: str,
        parameters: Dict[str, Any],
        output_file: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Capture metadata for an analysis run.
        
        Args:
            analysis_name: Name of the analysis
            parameters: Analysis parameters
            output_file: Optional path to save metadata
        
        Returns:
            Metadata dictionary
        """
        metadata = {
            'analysis_name': analysis_name,
            'timestamp': datetime.now().isoformat(),
            'random_seed': self.seed,
            'parameters': parameters,
            'environment': self.reproducibility_info,
            'reproducibility': {
                'seed_set': True,
                'seed_value': self.seed,
                'numpy_seed': self.seed,
                'python_seed': self.seed
            }
        }
        
        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            logger.info(f"Reproducibility metadata saved to {output_file}")
        
        return metadata
    
    def load_analysis_metadata(self, metadata_file: Path) -> Dict[str, Any]:
        """Load analysis metadata for reproducibility."""
        if not metadata_file.exists():
            logger.warning(f"Metadata file not found: {metadata_file}")
            return {}
        
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        # Restore seed if available
        if 'reproducibility' in metadata:
            seed = metadata['reproducibility'].get('seed_value', self.DEFAULT_SEED)
            self.set_seed(seed)
            logger.info(f"Restored random seed: {seed}")
        
        return metadata
    
    def create_reproducibility_report(
        self,
        analysis_name: str,
        output_dir: Optional[Path] = None
    ) -> Path:
        """
        Create comprehensive reproducibility report.
        
        Args:
            analysis_name: Name of the analysis
            output_dir: Output directory (uses analysis_dir if None)
        
        Returns:
            Path to report file
        """
        if output_dir is None:
            output_dir = self.analysis_dir / 'reproducibility'
        
        output_dir.mkdir(parents=True, exist_ok=True)
        report_file = output_dir / f'{analysis_name}_reproducibility.json'
        
        report = {
            'analysis_name': analysis_name,
            'generated_at': datetime.now().isoformat(),
            'random_seed': self.seed,
            'environment': self.reproducibility_info,
            'reproducibility_settings': {
                'seed': self.seed,
                'numpy_seed_set': True,
                'python_seed_set': True
            },
            'instructions': {
                'to_reproduce': [
                    f"Set random seed to {self.seed}",
                    "Use same Python version",
                    "Use same package versions",
                    "Use same data files"
                ]
            }
        }
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Reproducibility report saved to {report_file}")
        return report_file
    
    def _capture_environment(self) -> Dict[str, Any]:
        """Capture environment information."""
        try:
            import pandas as pd
            pandas_version = pd.__version__
        except ImportError:
            pandas_version = "not installed"
        
        try:
            import numpy as np
            numpy_version = np.__version__
        except ImportError:
            numpy_version = "not installed"
        
        try:
            import scipy
            scipy_version = scipy.__version__
        except ImportError:
            scipy_version = "not installed"
        
        try:
            import networkx as nx
            networkx_version = nx.__version__
        except ImportError:
            networkx_version = "not installed"
        
        return {
            'python_version': sys.version,
            'platform': platform.platform(),
            'processor': platform.processor(),
            'machine': platform.machine(),
            'package_versions': {
                'pandas': pandas_version,
                'numpy': numpy_version,
                'scipy': scipy_version,
                'networkx': networkx_version
            }
        }
    
    def verify_reproducibility(
        self,
        metadata_file: Path,
        current_environment: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Verify current environment matches metadata for reproducibility.
        
        Args:
            metadata_file: Path to metadata file
            current_environment: Current environment (captured if None)
        
        Returns:
            Verification report
        """
        if not metadata_file.exists():
            return {
                'verified': False,
                'error': 'Metadata file not found'
            }
        
        metadata = self.load_analysis_metadata(metadata_file)
        
        if current_environment is None:
            current_environment = self._capture_environment()
        
        original_env = metadata.get('environment', {})
        
        issues = []
        
        # Check Python version
        if original_env.get('python_version') != current_environment.get('python_version'):
            issues.append('Python version mismatch')
        
        # Check package versions
        orig_packages = original_env.get('package_versions', {})
        curr_packages = current_environment.get('package_versions', {})
        
        for pkg, orig_ver in orig_packages.items():
            curr_ver = curr_packages.get(pkg)
            if orig_ver != curr_ver:
                issues.append(f'Package {pkg} version mismatch: {orig_ver} vs {curr_ver}')
        
        return {
            'verified': len(issues) == 0,
            'issues': issues,
            'original_environment': original_env,
            'current_environment': current_environment
        }


# Global reproducibility manager instance
_reproducibility_manager = None


def get_reproducibility_manager(seed: int = ReproducibilityManager.DEFAULT_SEED) -> ReproducibilityManager:
    """Get global reproducibility manager instance."""
    global _reproducibility_manager
    if _reproducibility_manager is None:
        _reproducibility_manager = ReproducibilityManager(seed=seed)
    return _reproducibility_manager


def set_global_seed(seed: int = ReproducibilityManager.DEFAULT_SEED):
    """Set global random seed for reproducibility."""
    manager = get_reproducibility_manager(seed)
    manager.set_seed(seed)

