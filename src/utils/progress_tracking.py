"""Progress tracking and resumability for long-running data processing tasks."""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import hashlib

from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir

logger = setup_logger()


class ProgressTracker:
    """Tracks progress and enables resumability for long-running tasks."""
    
    def __init__(self, task_name: str, checkpoint_dir: Optional[Path] = None):
        """
        Initialize progress tracker.
        
        Args:
            task_name: Name of the task
            checkpoint_dir: Directory for checkpoints (uses data_dir/checkpoints if None)
        """
        self.task_name = task_name
        self.data_dir = get_data_dir()
        
        if checkpoint_dir is None:
            checkpoint_dir = self.data_dir / 'checkpoints'
        self.checkpoint_dir = checkpoint_dir
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        self.checkpoint_file = self.checkpoint_dir / f'{task_name}_progress.json'
        self.progress = self._load_progress()
    
    def start(self, total_items: Optional[int] = None):
        """Start tracking progress."""
        self.progress = {
            'task_name': self.task_name,
            'started_at': datetime.now().isoformat(),
            'total_items': total_items,
            'processed_items': 0,
            'failed_items': 0,
            'last_checkpoint': None,
            'checkpoints': [],
            'status': 'running'
        }
        self._save_progress()
        logger.info(f"Started progress tracking for {self.task_name}")
    
    def update(self, processed: int, failed: int = 0):
        """Update progress."""
        self.progress['processed_items'] = processed
        self.progress['failed_items'] = failed
        self.progress['last_checkpoint'] = datetime.now().isoformat()
        self._save_progress()
    
    def checkpoint(self, checkpoint_data: Dict[str, Any], description: str = ""):
        """
        Create a checkpoint.
        
        Args:
            checkpoint_data: Data to save in checkpoint
            description: Optional description of checkpoint
        """
        checkpoint = {
            'timestamp': datetime.now().isoformat(),
            'description': description,
            'processed_items': self.progress['processed_items'],
            'data': checkpoint_data
        }
        
        self.progress['checkpoints'].append(checkpoint)
        self.progress['last_checkpoint'] = checkpoint['timestamp']
        self._save_progress()
        
        logger.info(f"Checkpoint created: {description or 'No description'}")
    
    def get_last_checkpoint(self) -> Optional[Dict[str, Any]]:
        """Get the last checkpoint."""
        if self.progress.get('checkpoints'):
            return self.progress['checkpoints'][-1]
        return None
    
    def can_resume(self) -> bool:
        """Check if task can be resumed."""
        return (
            self.progress.get('status') == 'running' and
            self.progress.get('processed_items', 0) > 0
        )
    
    def resume(self) -> Optional[Dict[str, Any]]:
        """Resume from last checkpoint."""
        if not self.can_resume():
            logger.warning("Cannot resume - no valid checkpoint")
            return None
        
        last_checkpoint = self.get_last_checkpoint()
        if last_checkpoint:
            logger.info(f"Resuming from checkpoint: {last_checkpoint.get('description', 'No description')}")
            return last_checkpoint.get('data')
        
        return {
            'processed_items': self.progress.get('processed_items', 0)
        }
    
    def complete(self):
        """Mark task as complete."""
        self.progress['status'] = 'completed'
        self.progress['completed_at'] = datetime.now().isoformat()
        self._save_progress()
        logger.info(f"Task {self.task_name} completed")
    
    def fail(self, error: str):
        """Mark task as failed."""
        self.progress['status'] = 'failed'
        self.progress['failed_at'] = datetime.now().isoformat()
        self.progress['error'] = error
        self._save_progress()
        logger.error(f"Task {self.task_name} failed: {error}")
    
    def get_progress_percentage(self) -> float:
        """Get progress percentage."""
        total = self.progress.get('total_items')
        processed = self.progress.get('processed_items', 0)
        
        if total and total > 0:
            return (processed / total) * 100
        return 0.0
    
    def get_summary(self) -> Dict[str, Any]:
        """Get progress summary."""
        return {
            'task_name': self.task_name,
            'status': self.progress.get('status', 'unknown'),
            'processed': self.progress.get('processed_items', 0),
            'failed': self.progress.get('failed_items', 0),
            'total': self.progress.get('total_items'),
            'percentage': self.get_progress_percentage(),
            'checkpoints': len(self.progress.get('checkpoints', [])),
            'started_at': self.progress.get('started_at'),
            'last_checkpoint': self.progress.get('last_checkpoint')
        }
    
    def _load_progress(self) -> Dict[str, Any]:
        """Load progress from checkpoint file."""
        if not self.checkpoint_file.exists():
            return {}
        
        try:
            with open(self.checkpoint_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Error loading progress: {e}")
            return {}
    
    def _save_progress(self):
        """Save progress to checkpoint file."""
        try:
            with open(self.checkpoint_file, 'w') as f:
                json.dump(self.progress, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving progress: {e}")


class ResumableProcessor:
    """Base class for resumable data processing."""
    
    def __init__(self, task_name: str, checkpoint_interval: int = 100):
        """
        Initialize resumable processor.
        
        Args:
            task_name: Name of the processing task
            checkpoint_interval: Create checkpoint every N items
        """
        self.task_name = task_name
        self.checkpoint_interval = checkpoint_interval
        self.tracker = ProgressTracker(task_name)
    
    def process_with_resume(
        self,
        items: List[Any],
        process_func,
        start_from: Optional[int] = None
    ):
        """
        Process items with resumability.
        
        Args:
            items: List of items to process
            process_func: Function to process each item
            start_from: Index to start from (uses checkpoint if None)
        """
        total = len(items)
        self.tracker.start(total_items=total)
        
        # Check if we can resume
        if start_from is None and self.tracker.can_resume():
            resume_data = self.tracker.resume()
            if resume_data:
                start_from = resume_data.get('processed_items', 0)
                logger.info(f"Resuming from item {start_from}")
        
        if start_from is None:
            start_from = 0
        
        processed = start_from
        failed = 0
        
        try:
            for i in range(start_from, total):
                item = items[i]
                
                try:
                    process_func(item, i)
                    processed += 1
                except Exception as e:
                    logger.error(f"Error processing item {i}: {e}")
                    failed += 1
                
                # Update progress
                self.tracker.update(processed, failed)
                
                # Create checkpoint
                if processed % self.checkpoint_interval == 0:
                    self.tracker.checkpoint(
                        {'processed_items': processed, 'last_index': i},
                        f"Processed {processed} items"
                    )
            
            self.tracker.complete()
            logger.info(f"Processing complete: {processed} processed, {failed} failed")
        
        except KeyboardInterrupt:
            logger.warning("Processing interrupted by user")
            self.tracker.checkpoint(
                {'processed_items': processed, 'last_index': i},
                "Interrupted by user"
            )
            raise
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            self.tracker.fail(str(e))
            raise

