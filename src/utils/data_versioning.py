"""Data versioning system with timestamps, checksums, and metadata tracking."""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir

logger = setup_logger()


class DataVersionManager:
    """Manages data versioning with checksums and metadata."""
    
    def __init__(self, version_dir: Optional[Path] = None):
        """
        Initialize data version manager.
        
        Args:
            version_dir: Directory for version metadata (uses data_dir/versions if None)
        """
        self.data_dir = get_data_dir()
        
        if version_dir is None:
            version_dir = self.data_dir / 'versions'
        self.version_dir = version_dir
        self.version_dir.mkdir(parents=True, exist_ok=True)
    
    def create_version(
        self,
        file_path: Path,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a version record for a file.
        
        Args:
            file_path: Path to file to version
            metadata: Optional metadata to include
        
        Returns:
            Version record dictionary
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File does not exist: {file_path}")
        
        # Calculate checksum
        checksum = self._calculate_checksum(file_path)
        
        # Get file stats
        stat = file_path.stat()
        
        # Create version record
        version = {
            'file_path': str(file_path.relative_to(self.data_dir)),
            'absolute_path': str(file_path),
            'version_id': self._generate_version_id(file_path, checksum),
            'checksum': checksum,
            'checksum_algorithm': 'sha256',
            'size_bytes': stat.st_size,
            'created_at': datetime.now().isoformat(),
            'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'metadata': metadata or {}
        }
        
        # Save version record
        self._save_version_record(version)
        
        logger.info(f"Created version for {file_path.name}: {version['version_id']}")
        return version
    
    def get_file_versions(self, file_path: Path) -> List[Dict[str, Any]]:
        """Get all versions of a file."""
        relative_path = str(file_path.relative_to(self.data_dir))
        version_file = self.version_dir / f'{relative_path.replace("/", "_")}_versions.json'
        
        if not version_file.exists():
            return []
        
        try:
            with open(version_file, 'r') as f:
                data = json.load(f)
                return data.get('versions', [])
        except Exception as e:
            logger.warning(f"Error loading versions: {e}")
            return []
    
    def verify_file_integrity(self, file_path: Path, expected_checksum: str) -> bool:
        """
        Verify file integrity against expected checksum.
        
        Args:
            file_path: Path to file
            expected_checksum: Expected SHA256 checksum
        
        Returns:
            True if checksum matches
        """
        if not file_path.exists():
            return False
        
        actual_checksum = self._calculate_checksum(file_path)
        return actual_checksum == expected_checksum
    
    def get_latest_version(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Get the latest version of a file."""
        versions = self.get_file_versions(file_path)
        if not versions:
            return None
        
        # Sort by created_at descending
        versions.sort(key=lambda v: v.get('created_at', ''), reverse=True)
        return versions[0]
    
    def create_snapshot(
        self,
        snapshot_name: str,
        files: List[Path],
        description: str = ""
    ) -> Dict[str, Any]:
        """
        Create a snapshot of multiple files.
        
        Args:
            snapshot_name: Name for the snapshot
            files: List of files to include
            description: Optional description
        
        Returns:
            Snapshot record
        """
        snapshot = {
            'snapshot_name': snapshot_name,
            'created_at': datetime.now().isoformat(),
            'description': description,
            'files': []
        }
        
        for file_path in files:
            if file_path.exists():
                version = self.create_version(file_path)
                snapshot['files'].append({
                    'file_path': str(file_path.relative_to(self.data_dir)),
                    'version_id': version['version_id'],
                    'checksum': version['checksum']
                })
        
        # Save snapshot
        snapshot_file = self.version_dir / f'snapshot_{snapshot_name}.json'
        with open(snapshot_file, 'w') as f:
            json.dump(snapshot, f, indent=2)
        
        logger.info(f"Created snapshot '{snapshot_name}' with {len(snapshot['files'])} files")
        return snapshot
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file."""
        sha256 = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            # Read in chunks to handle large files
            while chunk := f.read(8192):
                sha256.update(chunk)
        
        return sha256.hexdigest()
    
    def _generate_version_id(self, file_path: Path, checksum: str) -> str:
        """Generate version ID from file path and checksum."""
        # Use first 8 chars of checksum + timestamp
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        file_hash = checksum[:8]
        return f"{timestamp}_{file_hash}"
    
    def _save_version_record(self, version: Dict[str, Any]):
        """Save version record to file."""
        relative_path = version['file_path']
        version_file = self.version_dir / f'{relative_path.replace("/", "_")}_versions.json'
        
        # Load existing versions
        if version_file.exists():
            try:
                with open(version_file, 'r') as f:
                    data = json.load(f)
                    versions = data.get('versions', [])
            except Exception:
                versions = []
        else:
            versions = []
        
        # Add new version
        versions.append(version)
        
        # Save
        data = {
            'file_path': relative_path,
            'versions': versions,
            'latest_version': version['version_id']
        }
        
        with open(version_file, 'w') as f:
            json.dump(data, f, indent=2)

