#!/usr/bin/env python3
"""
Validation script to check project setup and dependencies.

Run this after setup.sh to verify everything is configured correctly.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all core modules can be imported."""
    print("Testing imports...")
    
    try:
        from src.config import config
        print("  ✓ Config module imported")
    except Exception as e:
        print(f"  ✗ Config module failed: {e}")
        return False
    
    try:
        from src.utils.logger import setup_logger
        print("  ✓ Logger module imported")
    except Exception as e:
        print(f"  ✗ Logger module failed: {e}")
        return False
    
    try:
        from src.utils.rate_limiter import RateLimiter
        print("  ✓ Rate limiter module imported")
    except Exception as e:
        print(f"  ✗ Rate limiter module failed: {e}")
        return False
    
    try:
        from src.utils.paths import get_data_dir, get_analysis_dir
        print("  ✓ Paths module imported")
    except Exception as e:
        print(f"  ✗ Paths module failed: {e}")
        return False
    
    return True

def test_config():
    """Test configuration loading."""
    print("\nTesting configuration...")
    
    try:
        from src.config import config
        
        # Test basic config access
        repo_owner = config.get('data_collection.github.repository.owner', 'bitcoin')
        print(f"  ✓ Config loaded: repo owner = {repo_owner}")
        
        # Test path access
        data_dir = config.get('paths.data', 'data')
        print(f"  ✓ Path config: data_dir = {data_dir}")
        
        return True
    except Exception as e:
        print(f"  ✗ Config test failed: {e}")
        return False

def test_paths():
    """Test path utilities."""
    print("\nTesting path utilities...")
    
    try:
        from src.utils.paths import (
            get_project_root, get_data_dir, get_analysis_dir,
            get_visualizations_dir, get_findings_dir, get_logs_dir
        )
        
        project_root = get_project_root()
        print(f"  ✓ Project root: {project_root}")
        
        data_dir = get_data_dir()
        print(f"  ✓ Data dir: {data_dir} (exists: {data_dir.exists()})")
        
        analysis_dir = get_analysis_dir()
        print(f"  ✓ Analysis dir: {analysis_dir} (exists: {analysis_dir.exists()})")
        
        return True
    except Exception as e:
        print(f"  ✗ Paths test failed: {e}")
        return False

def test_logger():
    """Test logging setup."""
    print("\nTesting logger...")
    
    try:
        from src.utils.logger import setup_logger
        
        logger = setup_logger("test_logger", "INFO")
        logger.info("Test log message")
        print("  ✓ Logger created and working")
        
        return True
    except Exception as e:
        print(f"  ✗ Logger test failed: {e}")
        return False

def test_rate_limiter():
    """Test rate limiter."""
    print("\nTesting rate limiter...")
    
    try:
        from src.utils.rate_limiter import RateLimiter
        
        limiter = RateLimiter(max_calls=10, time_window=60)
        can_proceed = limiter.can_proceed()
        print(f"  ✓ Rate limiter created (can proceed: {can_proceed})")
        
        return True
    except Exception as e:
        print(f"  ✗ Rate limiter test failed: {e}")
        return False

def test_dependencies():
    """Test that required dependencies are installed."""
    print("\nTesting dependencies...")
    
    required = {
        'yaml': 'pyyaml',
        'pandas': 'pandas',
        'numpy': 'numpy',
        'requests': 'requests',
    }
    
    optional = {
        'github': 'PyGithub',
        'scipy': 'scipy',
        'sklearn': 'scikit-learn',
        'networkx': 'networkx',
    }
    
    all_ok = True
    
    print("  Required dependencies:")
    for module, package in required.items():
        try:
            __import__(module)
            print(f"    ✓ {package}")
        except ImportError:
            print(f"    ✗ {package} (MISSING)")
            all_ok = False
    
    print("  Optional dependencies:")
    for module, package in optional.items():
        try:
            __import__(module)
            print(f"    ✓ {package}")
        except ImportError:
            print(f"    - {package} (not installed, optional)")
    
    return all_ok

def test_directory_structure():
    """Test that required directories exist or can be created."""
    print("\nTesting directory structure...")
    
    try:
        from src.utils.paths import (
            get_data_dir, get_analysis_dir, get_visualizations_dir,
            get_findings_dir, get_logs_dir
        )
        
        dirs = {
            'data': get_data_dir(),
            'analysis': get_analysis_dir(),
            'visualizations': get_visualizations_dir(),
            'findings': get_findings_dir(),
            'logs': get_logs_dir(),
        }
        
        for name, path in dirs.items():
            if path.exists():
                print(f"  ✓ {name}/ exists")
            else:
                print(f"  - {name}/ will be created when needed")
        
        return True
    except Exception as e:
        print(f"  ✗ Directory structure test failed: {e}")
        return False

def main():
    """Run all validation tests."""
    print("=" * 60)
    print("Bitcoin Governance Analysis - Setup Validation")
    print("=" * 60)
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("Configuration", test_config()))
    results.append(("Paths", test_paths()))
    results.append(("Logger", test_logger()))
    results.append(("Rate Limiter", test_rate_limiter()))
    results.append(("Dependencies", test_dependencies()))
    results.append(("Directory Structure", test_directory_structure()))
    
    print("\n" + "=" * 60)
    print("Validation Summary")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("✓ All tests passed! Project is ready to use.")
        return 0
    else:
        print("✗ Some tests failed. Please fix issues before proceeding.")
        return 1

if __name__ == '__main__':
    sys.exit(main())

