"""Path utilities for consistent path handling across the project."""

from pathlib import Path
from typing import Optional
from src.config import config


def get_project_root() -> Path:
    """Get the project root directory."""
    # This file is in src/utils/, so go up 2 levels
    return Path(__file__).parent.parent.parent


def get_data_dir() -> Path:
    """Get the data directory path."""
    project_root = get_project_root()
    data_dir = project_root / config.get('paths.data', 'data')
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_analysis_dir() -> Path:
    """Get the analysis output directory path."""
    project_root = get_project_root()
    analysis_dir = project_root / config.get('paths.analysis', 'analysis')
    analysis_dir.mkdir(parents=True, exist_ok=True)
    return analysis_dir


def get_visualizations_dir() -> Path:
    """Get the visualizations directory path."""
    project_root = get_project_root()
    viz_dir = project_root / config.get('paths.visualizations', 'visualizations')
    viz_dir.mkdir(parents=True, exist_ok=True)
    return viz_dir


def get_findings_dir() -> Path:
    """Get the findings directory path."""
    project_root = get_project_root()
    findings_dir = project_root / config.get('paths.findings', 'findings')
    findings_dir.mkdir(parents=True, exist_ok=True)
    return findings_dir


def get_logs_dir() -> Path:
    """Get the logs directory path."""
    project_root = get_project_root()
    logs_dir = project_root / config.get('paths.logs', 'logs')
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir

