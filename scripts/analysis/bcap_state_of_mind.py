#!/usr/bin/env python3
"""
BCAP State of Mind (SOM) Analysis - Analyze developer engagement during consensus changes.

BCAP's State of Mind (SOM) framework classifies stakeholder engagement:
- SOM1: Passionate advocate
- SOM2: Supportive
- SOM3: Apathetic/undecided
- SOM4: Unaware
- SOM5: Not supportive, not fighting
- SOM6: Passionately against

This script analyzes Bitcoin Core developers' SOM during consensus change periods:
- SegWit (2015-2017)
- Taproot (2018-2021)
"""

import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, Counter
from datetime import datetime, timezone

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir, get_analysis_dir
from scripts.utils.load_prs_with_merged_by import load_prs_with_merged_by

logger = setup_logger()


# Consensus change periods (dates are approximate)
CONSENSUS_PERIODS = {
    'segwit': {
        'start': '2015-12-07',  # BIP141 proposal date
        'end': '2017-08-23',     # SegWit activation date
        'keywords': ['segwit', 'segregated witness', 'bip141', 'bip143', 'bip147', 'witness'],
        'bips': [141, 143, 147]
    },
    'taproot': {
        'start': '2018-01-06',   # Taproot proposal date
        'end': '2021-11-14',     # Taproot activation date
        'keywords': ['taproot', 'schnorr', 'bip340', 'bip341', 'bip342', 'maxtaproot'],
        'bips': [340, 341, 342]
    }
}


class BCAPStateOfMindAnalyzer:
    """Analyzes developer State of Mind during consensus changes."""
    
    def __init__(self):
        """Initialize analyzer."""
        self.data_dir = get_data_dir()
        self.processed_dir = self.data_dir / 'processed'
        self.analysis_dir = get_analysis_dir()
        self.findings_dir = self.analysis_dir / 'findings' / 'data'
        self.findings_dir.mkdir(parents=True, exist_ok=True)
        
        # SOM classification keywords
        self.som_keywords = {
            'som1': ['excellent', 'great', 'strongly support', 'essential', 'critical', 'important', 'strongly advocate'],
            'som2': ['support', 'good', 'helpful', 'agree', 'ack', 'approve'],
            'som3': ['maybe', 'perhaps', 'uncertain', 'not sure', 'neutral', '?'],
            'som4': [],  # Detected by absence
            'som5': ['concern', 'worried', 'skeptical', 'hesitant', 'nack', 'oppose'],
            'som6': ['strongly oppose', 'dangerous', 'harmful', 'bad idea', 'against', 'veto', 'reject']
        }
    
    def run_analysis(self):
        """Run SOM analysis."""
        logger.info("=" * 60)
        logger.info("BCAP State of Mind Analysis")
        logger.info("=" * 60)
        
        # Load data
        prs = self._load_prs()
        issues = self._load_issues()
        
        # Identify consensus-related PRs/issues
        segwit_prs, segwit_issues = self._identify_consensus_prs(prs, issues, 'segwit')
        taproot_prs, taproot_issues = self._identify_consensus_prs(prs, issues, 'taproot')
        
        logger.info(f"Identified {len(segwit_prs)} SegWit PRs and {len(segwit_issues)} SegWit issues")
        logger.info(f"Identified {len(taproot_prs)} Taproot PRs and {len(taproot_issues)} Taproot issues")
        
        # Analyze SOM for SegWit
        segwit_som = self._analyze_period_som(segwit_prs, segwit_issues, 'segwit')
        
        # Analyze SOM for Taproot
        taproot_som = self._analyze_period_som(taproot_prs, taproot_issues, 'taproot')
        
        # Track SOM shifts over time
        som_shifts = self._track_som_shifts(segwit_som, taproot_som)
        
        # Generate statistics
        statistics = self._generate_statistics(segwit_som, taproot_som, som_shifts)
        
        # Save results
        results = {
            'segwit_analysis': segwit_som,
            'taproot_analysis': taproot_som,
            'som_shifts': som_shifts,
            'statistics': statistics,
            'methodology': self._get_methodology()
        }
        
        self._save_results(results)
        
        logger.info("SOM analysis complete")
    
    def _identify_consensus_prs(
        self,
        prs: List[Dict[str, Any]],
        issues: List[Dict[str, Any]],
        period: str
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Identify PRs/issues related to consensus changes."""
        period_data = CONSENSUS_PERIODS[period]
        keywords = [k.lower() for k in period_data['keywords']]
        # Make dates timezone-aware for comparison
        start_date = datetime.fromisoformat(period_data['start']).replace(tzinfo=timezone.utc)
        end_date = datetime.fromisoformat(period_data['end']).replace(tzinfo=timezone.utc)
        
        related_prs = []
        related_issues = []
        
        # Check PRs
        for pr in prs:
            created = pr.get('created_at')
            if not created:
                continue
            
            try:
                created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                if not (start_date <= created_dt <= end_date):
                    continue
            except:
                continue
            
            # Check if PR is related to consensus change
            title = (pr.get('title', '') or '').lower()
            body = (pr.get('body', '') or '').lower()
            text = title + ' ' + body
            
            if any(kw in text for kw in keywords):
                related_prs.append(pr)
                continue
            
            # Check for BIP mentions
            for bip_num in period_data['bips']:
                if f'bip{bip_num}' in text or f'bip-{bip_num}' in text:
                    related_prs.append(pr)
                    break
        
        # Check issues
        for issue in issues:
            created = issue.get('created_at')
            if not created:
                continue
            
            try:
                created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                if not (start_date <= created_dt <= end_date):
                    continue
            except:
                continue
            
            title = (issue.get('title', '') or '').lower()
            body = (issue.get('body', '') or '').lower()
            text = title + ' ' + body
            
            if any(kw in text for kw in keywords):
                related_issues.append(issue)
                continue
            
            # Check for BIP mentions
            for bip_num in period_data['bips']:
                if f'bip{bip_num}' in text or f'bip-{bip_num}' in text:
                    related_issues.append(issue)
                    break
        
        return related_prs, related_issues
    
    def _analyze_period_som(
        self,
        prs: List[Dict[str, Any]],
        issues: List[Dict[str, Any]],
        period: str
    ) -> Dict[str, Any]:
        """Analyze SOM for a consensus change period."""
        logger.info(f"Analyzing SOM for {period}...")
        
        period_data = CONSENSUS_PERIODS[period]
        # Make dates timezone-aware for comparison
        start_date = datetime.fromisoformat(period_data['start']).replace(tzinfo=timezone.utc)
        end_date = datetime.fromisoformat(period_data['end']).replace(tzinfo=timezone.utc)
        
        # Track developer activity and sentiment
        developer_activity = defaultdict(lambda: {
            'prs': [],
            'reviews': [],
            'comments': [],
            'issues': [],
            'activity_count': 0
        })
        
        # Collect all activities
        for pr in prs:
            author = pr.get('author')
            if author:
                developer_activity[author]['prs'].append(pr)
                developer_activity[author]['activity_count'] += 1
            
            for review in pr.get('reviews', []):
                reviewer = review.get('author')
                if reviewer:
                    developer_activity[reviewer]['reviews'].append(review)
                    developer_activity[reviewer]['activity_count'] += 1
            
            for comment in pr.get('comments', []):
                commenter = comment.get('author')
                if commenter:
                    developer_activity[commenter]['comments'].append(comment)
                    developer_activity[commenter]['activity_count'] += 1
        
        for issue in issues:
            author = issue.get('author')
            if author:
                developer_activity[author]['issues'].append(issue)
                developer_activity[author]['activity_count'] += 1
            
            for comment in issue.get('comments', []):
                commenter = comment.get('author')
                if commenter:
                    developer_activity[commenter]['comments'].append(comment)
                    developer_activity[commenter]['activity_count'] += 1
        
        # Classify SOM for each developer
        developer_som = {}
        for dev_id, activities in developer_activity.items():
            som = self._classify_developer_som(dev_id, activities, prs, issues)
            if som:
                developer_som[dev_id] = som
        
        # Calculate temporal SOM distribution
        temporal_distribution = self._calculate_temporal_som_distribution(developer_som, start_date, end_date)
        
        return {
            'period': period,
            'start_date': period_data['start'],
            'end_date': period_data['end'],
            'developer_som': developer_som,
            'temporal_distribution': temporal_distribution,
            'total_developers': len(developer_som),
            'related_prs_count': len(prs),
            'related_issues_count': len(issues)
        }
    
    def _classify_developer_som(
        self,
        dev_id: str,
        activities: Dict[str, List[Dict[str, Any]]],
        prs: List[Dict[str, Any]],
        issues: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Classify a developer's SOM based on their activities."""
        
        # Collect all text from developer's activities
        all_text = []
        
        # From PRs
        for pr in activities.get('prs', []):
            all_text.append(pr.get('title', '') or '')
            all_text.append(pr.get('body', '') or '')
        
        # From reviews
        for review in activities.get('reviews', []):
            all_text.append(review.get('body', '') or '')
            state = review.get('state', '').lower()
            if state == 'approved':
                all_text.append('ack approve support')
            elif state == 'changes_requested':
                all_text.append('nack oppose concern')
        
        # From comments
        for comment in activities.get('comments', []):
            all_text.append(comment.get('body', '') or '')
        
        # From issues
        for issue in activities.get('issues', []):
            all_text.append(issue.get('title', '') or '')
            all_text.append(issue.get('body', '') or '')
        
        combined_text = ' '.join(all_text).lower()
        
        # Count keyword matches for each SOM level
        som_scores = {
            'som1': sum(1 for kw in self.som_keywords['som1'] if kw in combined_text),
            'som2': sum(1 for kw in self.som_keywords['som2'] if kw in combined_text),
            'som5': sum(1 for kw in self.som_keywords['som5'] if kw in combined_text),
            'som6': sum(1 for kw in self.som_keywords['som6'] if kw in combined_text)
        }
        
        # Calculate activity level
        activity_count = activities['activity_count']
        
        # Classify SOM
        primary_som = None
        confidence = 'low'
        
        # SOM6: Passionately against (highest priority if present)
        if som_scores['som6'] > 0 or 'veto' in combined_text or 'strongly oppose' in combined_text:
            primary_som = 'som6'
            confidence = 'high' if som_scores['som6'] >= 2 else 'medium'
        
        # SOM1: Passionate advocate
        elif som_scores['som1'] > 0 or (activity_count >= 5 and som_scores['som2'] >= 3):
            primary_som = 'som1'
            confidence = 'high' if som_scores['som1'] >= 2 or activity_count >= 10 else 'medium'
        
        # SOM5: Not supportive, not fighting
        elif som_scores['som5'] > 0:
            primary_som = 'som5'
            confidence = 'medium'
        
        # SOM2: Supportive
        elif som_scores['som2'] > 0 or activity_count >= 3:
            primary_som = 'som2'
            confidence = 'medium'
        
        # SOM3: Apathetic/undecided (low activity, neutral)
        elif activity_count >= 1:
            primary_som = 'som3'
            confidence = 'low'
        
        # SOM4: Unaware (no participation)
        else:
            primary_som = 'som4'
            confidence = 'low'
        
        if not primary_som:
            return None
        
        return {
            'som': primary_som,
            'confidence': confidence,
            'activity_count': activity_count,
            'som_scores': som_scores,
            'pr_count': len(activities.get('prs', [])),
            'review_count': len(activities.get('reviews', [])),
            'comment_count': len(activities.get('comments', []))
        }
    
    def _calculate_temporal_som_distribution(
        self,
        developer_som: Dict[str, Dict[str, Any]],
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Calculate SOM distribution over time."""
        distribution = {
            'som1': 0,
            'som2': 0,
            'som3': 0,
            'som4': 0,
            'som5': 0,
            'som6': 0
        }
        
        for dev_id, som_data in developer_som.items():
            som = som_data.get('som')
            if som:
                distribution[som] = distribution.get(som, 0) + 1
        
        total = sum(distribution.values())
        percentages = {k: (v / total * 100) if total > 0 else 0 for k, v in distribution.items()}
        
        return {
            'counts': distribution,
            'percentages': percentages,
            'total': total
        }
    
    def _track_som_shifts(
        self,
        segwit_som: Dict[str, Any],
        taproot_som: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Track SOM shifts between SegWit and Taproot."""
        logger.info("Tracking SOM shifts...")
        
        segwit_devs = segwit_som.get('developer_som', {})
        taproot_devs = taproot_som.get('developer_som', {})
        
        # Find developers who participated in both
        common_devs = set(segwit_devs.keys()) & set(taproot_devs.keys())
        
        shifts = []
        shift_matrix = defaultdict(lambda: defaultdict(int))
        
        for dev_id in common_devs:
            segwit_som_val = segwit_devs[dev_id].get('som')
            taproot_som_val = taproot_devs[dev_id].get('som')
            
            if segwit_som_val and taproot_som_val:
                shift_matrix[segwit_som_val][taproot_som_val] += 1
                
                if segwit_som_val != taproot_som_val:
                    shifts.append({
                        'developer': dev_id,
                        'segwit_som': segwit_som_val,
                        'taproot_som': taproot_som_val,
                        'shift_type': self._classify_shift_type(segwit_som_val, taproot_som_val)
                    })
        
        return {
            'common_developers': len(common_devs),
            'shifts': shifts,
            'shift_count': len(shifts),
            'shift_matrix': {k: dict(v) for k, v in shift_matrix.items()}
        }
    
    def _classify_shift_type(self, from_som: str, to_som: str) -> str:
        """Classify the type of SOM shift."""
        som_order = ['som4', 'som3', 'som5', 'som2', 'som1', 'som6']
        
        from_idx = som_order.index(from_som) if from_som in som_order else -1
        to_idx = som_order.index(to_som) if to_som in som_order else -1
        
        if from_idx == -1 or to_idx == -1:
            return 'unknown'
        
        if to_idx > from_idx:
            return 'increased_engagement'
        elif to_idx < from_idx:
            return 'decreased_engagement'
        else:
            return 'stable'
    
    def _generate_statistics(
        self,
        segwit_som: Dict[str, Any],
        taproot_som: Dict[str, Any],
        som_shifts: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate overall statistics."""
        segwit_dist = segwit_som.get('temporal_distribution', {})
        taproot_dist = taproot_som.get('temporal_distribution', {})
        
        return {
            'segwit': {
                'total_developers': segwit_som.get('total_developers', 0),
                'som_distribution': segwit_dist.get('percentages', {})
            },
            'taproot': {
                'total_developers': taproot_som.get('total_developers', 0),
                'som_distribution': taproot_dist.get('percentages', {})
            },
            'shifts': {
                'common_developers': som_shifts.get('common_developers', 0),
                'shift_count': som_shifts.get('shift_count', 0)
            }
        }
    
    def _get_methodology(self) -> Dict[str, Any]:
        """Get methodology description."""
        return {
            'framework': 'BCAP State of Mind (SOM)',
            'reference': 'https://github.com/bitcoin-cap/bcap',
            'som_levels': {
                'som1': 'Passionate advocate',
                'som2': 'Supportive',
                'som3': 'Apathetic/undecided',
                'som4': 'Unaware',
                'som5': 'Not supportive, not fighting',
                'som6': 'Passionately against'
            },
            'classification_method': {
                'activity_analysis': 'Count PRs, reviews, comments during consensus period',
                'sentiment_analysis': 'Keyword detection for advocacy/opposition',
                'confidence_levels': 'High/medium/low based on activity volume and sentiment strength'
            },
            'consensus_periods': CONSENSUS_PERIODS
        }
    
    def _load_prs(self) -> List[Dict[str, Any]]:
        """Load PR data."""
        # Try processed first, then fallback to raw
        prs_file = self.processed_dir / 'enriched_prs.jsonl'
        
        if not prs_file.exists():
            prs_file = self.processed_dir / 'cleaned_prs.jsonl'
        
        if not prs_file.exists():
            prs_file = self.data_dir / 'github' / 'prs_raw.jsonl'
        
        # Fallback to parent directory (commons-research/data/)
        if not prs_file.exists():
            parent_data_dir = self.data_dir.parent.parent / 'data'
            prs_file = parent_data_dir / 'github' / 'prs_raw.jsonl'
        
        if not prs_file.exists():
            logger.warning(f"PR data not found. Tried: {self.processed_dir / 'enriched_prs.jsonl'}, {self.data_dir / 'github' / 'prs_raw.jsonl'}, {prs_file}")
            return []
        
        # Try mapping file in both locations
        mapping_file = self.data_dir / 'github' / 'merged_by_mapping.jsonl'
        if not mapping_file.exists():
            parent_data_dir = self.data_dir.parent.parent / 'data'
            mapping_file = parent_data_dir / 'github' / 'merged_by_mapping.jsonl'
        
        prs = load_prs_with_merged_by(prs_file, mapping_file if mapping_file.exists() else None)
        
        logger.info(f"Loaded {len(prs)} PRs from {prs_file}")
        return prs
    
    def _load_issues(self) -> List[Dict[str, Any]]:
        """Load issue data."""
        issues_file = self.processed_dir / 'cleaned_issues.jsonl'
        
        if not issues_file.exists():
            logger.warning(f"Issues not found: {issues_file}")
            return []
        
        issues = []
        with open(issues_file, 'r') as f:
            for line in f:
                issues.append(json.loads(line))
        
        logger.info(f"Loaded {len(issues)} issues")
        return issues
    
    def _save_results(self, results: Dict[str, Any]):
        """Save analysis results."""
        output_file = self.findings_dir / 'bcap_som_analysis.json'
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Saved results to {output_file}")


def main():
    """Main entry point."""
    analyzer = BCAPStateOfMindAnalyzer()
    analyzer.run_analysis()


if __name__ == '__main__':
    main()

