#!/usr/bin/env python3
"""
Maintainer Timeline Tracker - Infer maintainer status from PR merge permissions.

This script:
1. Analyzes PR merge data to identify who can merge PRs
2. Builds timeline of maintainer status changes
3. Assigns confidence scores to inferences
4. Tracks maintainer activity patterns
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir, get_analysis_dir

logger = setup_logger()


class MaintainerTimelineTracker:
    """Tracks maintainer status changes over time."""
    
    def __init__(self):
        """Initialize tracker."""
        self.data_dir = get_data_dir()
        self.processed_dir = self.data_dir / 'processed'
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
        # Merge data by user
        self.user_merges = defaultdict(list)  # user -> list of (date, pr_number)
        self.user_activity = defaultdict(list)  # user -> list of (date, activity_type)
        
        # Maintainer timeline
        self.maintainer_timeline = {}
    
    def build_timeline(self):
        """Build maintainer timeline from PR data."""
        logger.info("=" * 60)
        logger.info("Maintainer Timeline Tracking")
        logger.info("=" * 60)
        
        # Load cleaned PR data
        prs_file = self.processed_dir / 'cleaned_prs.jsonl'
        
        # Also load contributors data for additional context
        contributors_file = self.data_dir / 'github' / 'collaborators.json'
        self.contributors = self._load_contributors(contributors_file)
        
        if not prs_file.exists():
            logger.warning(f"Cleaned PR data not found: {prs_file}")
            logger.info("Run clean_data.py first")
            return
        
        logger.info("Analyzing PR merge data...")
        
        # Collect merge data
        self._collect_merge_data(prs_file)
        
        # Infer maintainer status
        self._infer_maintainer_status()
        
        # Build timeline
        self._build_timeline()
        
        # Save results
        self._save_timeline()
        
        logger.info(f"Identified {len(self.maintainer_timeline)} maintainers")
        logger.info("=" * 60)
    
    def _collect_merge_data(self, prs_file: Path):
        """Collect merge data from PRs."""
        merge_count = 0
        
        with open(prs_file, 'r') as f:
            for line in f:
                try:
                    pr = json.loads(line)
                    
                    # Only process merged PRs
                    if pr.get('state') != 'merged' or not pr.get('merged_at'):
                        continue
                    
                    merged_by = pr.get('merged_by')
                    if not merged_by:
                        # Try to infer from merge commit author
                        merged_by = pr.get('merge_commit_author')
                    
                    if merged_by:
                        merge_date = pr.get('merged_at')
                        pr_number = pr.get('number')
                        
                        self.user_merges[merged_by].append((merge_date, pr_number))
                        merge_count += 1
                
                except Exception as e:
                    logger.warning(f"Error processing PR: {e}")
        
        logger.info(f"Collected {merge_count} merges from {len(self.user_merges)} users")
    
    def _infer_maintainer_status(self):
        """Infer maintainer status from merge patterns."""
        logger.info("Inferring maintainer status...")
        
        for user, merges in self.user_merges.items():
            if len(merges) < 3:  # Need at least 3 merges to be considered maintainer
                continue
            
            # Sort merges by date
            merges.sort(key=lambda x: x[0])
            
            # Calculate merge frequency
            first_merge = merges[0][0]
            last_merge = merges[-1][0]
            
            try:
                first_date = datetime.fromisoformat(first_merge.replace('Z', '+00:00'))
                last_date = datetime.fromisoformat(last_merge.replace('Z', '+00:00'))
                days_active = (last_date - first_date).days
                
                if days_active == 0:
                    days_active = 1
                
                merge_rate = len(merges) / days_active
                
                # Criteria for maintainer:
                # 1. At least 10 merges total
                # 2. Or at least 5 merges and merge rate > 0.1 per day
                # 3. Or at least 3 merges spanning > 90 days (consistent activity)
                
                is_maintainer = False
                confidence = 'low'
                
                if len(merges) >= 10:
                    is_maintainer = True
                    confidence = 'high'
                elif len(merges) >= 5 and merge_rate > 0.1:
                    is_maintainer = True
                    confidence = 'medium'
                elif len(merges) >= 3 and days_active > 90:
                    is_maintainer = True
                    confidence = 'medium'
                
                if is_maintainer:
                    # Add contributor ranking if available
                    contrib_info = None
                    if self.contributors and user in self.contributors.get('lookup', {}):
                        contrib_data = self.contributors['lookup'][user]
                        contrib_info = {
                            'rank': contrib_data['rank'],
                            'contributions': contrib_data['contributions']
                        }
                    
                    self.maintainer_timeline[user] = {
                        'estimated_start': first_merge,
                        'estimated_end': None,  # Will be updated if activity stops
                        'confidence': confidence,
                        'evidence': ['merge_pattern'],
                        'merge_count': len(merges),
                        'merge_rate': merge_rate,
                        'days_active': days_active,
                        'first_merge': first_merge,
                        'last_merge': last_merge,
                        'contributor_ranking': contrib_info
                    }
            
            except Exception as e:
                logger.warning(f"Error processing user {user}: {e}")
    
    def _build_timeline(self):
        """Build detailed timeline with periods."""
        logger.info("Building detailed timeline...")
        
        for user, data in self.maintainer_timeline.items():
            merges = self.user_merges[user]
            merges.sort(key=lambda x: x[0])
            
            # Identify active periods
            periods = []
            current_period_start = None
            current_period_end = None
            
            for merge_date, _ in merges:
                try:
                    merge_dt = datetime.fromisoformat(merge_date.replace('Z', '+00:00'))
                    
                    if current_period_start is None:
                        current_period_start = merge_dt
                        current_period_end = merge_dt
                    else:
                        # If gap > 180 days, start new period
                        if (merge_dt - current_period_end).days > 180:
                            periods.append({
                                'start': current_period_start.isoformat(),
                                'end': current_period_end.isoformat(),
                                'type': 'inferred'
                            })
                            current_period_start = merge_dt
                            current_period_end = merge_dt
                        else:
                            current_period_end = merge_dt
                
                except Exception as e:
                    logger.warning(f"Error processing merge date: {e}")
            
            # Add final period
            if current_period_start:
                # If last merge was recent (< 90 days), period is ongoing
                if (datetime.now() - current_period_end).days < 90:
                    periods.append({
                        'start': current_period_start.isoformat(),
                        'end': None,  # Ongoing
                        'type': 'inferred'
                    })
                else:
                    periods.append({
                        'start': current_period_start.isoformat(),
                        'end': current_period_end.isoformat(),
                        'type': 'inferred'
                    })
            
            # Update timeline with periods
            data['periods'] = periods
            data['estimated_start'] = periods[0]['start'] if periods else data['estimated_start']
            data['estimated_end'] = periods[-1]['end'] if periods and periods[-1]['end'] else None
            
            # Calculate merge count by year
            merge_count_by_year = defaultdict(int)
            for merge_date, _ in merges:
                try:
                    year = datetime.fromisoformat(merge_date.replace('Z', '+00:00')).year
                    merge_count_by_year[year] += 1
                except Exception:
                    pass
            
            data['merge_count_by_year'] = dict(merge_count_by_year)
    
    def _load_contributors(self, contributors_file: Path) -> Optional[Dict[str, Any]]:
        """Load contributors data for context."""
        if not contributors_file.exists():
            return None
        
        try:
            with open(contributors_file, 'r') as f:
                data = json.load(f)
                contributors = data.get('contributors', [])
                
                # Create lookup by login
                lookup = {}
                for contrib in contributors:
                    login = contrib.get('login')
                    if login:
                        lookup[login] = {
                            'rank': contributors.index(contrib) + 1,
                            'contributions': contrib.get('contributions', 0),
                            'name': contrib.get('name'),
                            'email': contrib.get('email')
                        }
                
                return {'lookup': lookup, 'total': len(contributors)}
        except Exception as e:
            logger.warning(f"Error loading contributors: {e}")
            return None
    
    def _save_timeline(self):
        """Save maintainer timeline to file."""
        output_file = self.processed_dir / 'maintainer_timeline.json'
        
        output_data = {
            'generated_at': datetime.now().isoformat(),
            'total_maintainers': len(self.maintainer_timeline),
            'maintainer_timeline': self.maintainer_timeline
        }
        
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        logger.info(f"Maintainer timeline saved to {output_file}")
        
        # Generate summary
        self._generate_summary()
    
    def _generate_summary(self):
        """Generate summary statistics."""
        summary = {
            'total_maintainers': len(self.maintainer_timeline),
            'high_confidence': sum(1 for d in self.maintainer_timeline.values() if d['confidence'] == 'high'),
            'medium_confidence': sum(1 for d in self.maintainer_timeline.values() if d['confidence'] == 'medium'),
            'low_confidence': sum(1 for d in self.maintainer_timeline.values() if d['confidence'] == 'low'),
            'active_maintainers': sum(1 for d in self.maintainer_timeline.values() if d['estimated_end'] is None),
            'total_merges': sum(d['merge_count'] for d in self.maintainer_timeline.values())
        }
        
        logger.info("Maintainer Timeline Summary:")
        logger.info(f"  Total maintainers: {summary['total_maintainers']}")
        logger.info(f"  High confidence: {summary['high_confidence']}")
        logger.info(f"  Medium confidence: {summary['medium_confidence']}")
        logger.info(f"  Active maintainers: {summary['active_maintainers']}")
        logger.info(f"  Total merges: {summary['total_merges']}")


def main():
    """Main entry point."""
    tracker = MaintainerTimelineTracker()
    tracker.build_timeline()
    return 0


if __name__ == '__main__':
    sys.exit(main())

