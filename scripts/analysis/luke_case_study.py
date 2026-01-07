#!/usr/bin/env python3
"""
Luke Dashjr Case Study - Analyze maintainer removal process.

Analyzes:
1. Timeline reconstruction
2. Process documentation
3. Public vs private decision-making
4. Consistency with other maintainer actions
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from collections import defaultdict
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir, get_analysis_dir
from src.schemas.analysis_results import create_result_template

logger = setup_logger()


class LukeCaseStudyAnalyzer:
    """Analyzer for Luke Dashjr maintainer removal case study."""
    
    def __init__(self):
        """Initialize analyzer."""
        self.data_dir = get_data_dir()
        self.processed_dir = self.data_dir / 'processed'
        self.analysis_dir = get_analysis_dir() / 'luke_case_study'
        self.analysis_dir.mkdir(parents=True, exist_ok=True)
        
        # Luke-related keywords
        self.luke_keywords = ['luke', 'dashjr', 'luke-jr', 'lukejr']
    
    def run_analysis(self):
        """Run Luke case study analysis."""
        logger.info("=" * 60)
        logger.info("Luke Dashjr Case Study Analysis")
        logger.info("=" * 60)
        
        # Load data
        prs = self._load_enriched_prs()
        emails = self._load_emails()
        irc_messages = self._load_irc()
        
        # Reconstruct timeline
        timeline = self._reconstruct_timeline(prs, emails, irc_messages)
        
        # Analyze process
        process_analysis = self._analyze_process(prs, emails, irc_messages)
        
        # Compare to other maintainer actions
        comparison = self._compare_to_other_actions(prs, emails)
        
        # Analyze documentation
        documentation = self._analyze_documentation(prs, emails)
        
        # Save results
        self._save_results({
            'timeline': timeline,
            'process_analysis': process_analysis,
            'comparison': comparison,
            'documentation': documentation
        })
        
        logger.info("Luke case study analysis complete")
    
    def _load_enriched_prs(self) -> List[Dict[str, Any]]:
        """Load enriched PR data."""
        prs_file = self.processed_dir / 'enriched_prs.jsonl'
        if not prs_file.exists():
            prs_file = self.processed_dir / 'cleaned_prs.jsonl'
        
        if not prs_file.exists():
            return []
        
        prs = []
        with open(prs_file, 'r') as f:
            for line in f:
                prs.append(json.loads(line))
        return prs
    
    def _load_emails(self) -> List[Dict[str, Any]]:
        """Load email data."""
        emails_file = self.processed_dir / 'cleaned_emails.jsonl'
        if not emails_file.exists():
            return []
        
        emails = []
        with open(emails_file, 'r') as f:
            for line in f:
                emails.append(json.loads(line))
        return emails
    
    def _load_irc(self) -> List[Dict[str, Any]]:
        """Load IRC data."""
        irc_file = self.processed_dir / 'cleaned_irc.jsonl'
        if not irc_file.exists():
            return []
        
        messages = []
        with open(irc_file, 'r') as f:
            for line in f:
                messages.append(json.loads(line))
        return messages
    
    def _reconstruct_timeline(
        self,
        prs: List[Dict[str, Any]],
        emails: List[Dict[str, Any]],
        irc_messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Reconstruct timeline of events."""
        events = []
        
        # Search PRs
        for pr in prs:
            text = f"{pr.get('title', '')} {pr.get('body', '')}".lower()
            if any(keyword in text for keyword in self.luke_keywords):
                events.append({
                    'date': pr.get('created_at'),
                    'type': 'pr',
                    'platform': 'github',
                    'pr_number': pr.get('number'),
                    'title': pr.get('title'),
                    'author': pr.get('author')
                })
        
        # Search emails
        for email in emails:
            text = f"{email.get('subject', '')} {email.get('body', '')}".lower()
            if any(keyword in text for keyword in self.luke_keywords):
                events.append({
                    'date': email.get('date'),
                    'type': 'email',
                    'platform': 'mailing_list',
                    'subject': email.get('subject'),
                    'from': email.get('from')
                })
        
        # Search IRC
        for msg in irc_messages:
            text = (msg.get('content', '')).lower()
            if any(keyword in text for keyword in self.luke_keywords):
                events.append({
                    'date': msg.get('timestamp'),
                    'type': 'irc',
                    'platform': 'irc',
                    'author': msg.get('author'),
                    'content': msg.get('content', '')[:100]  # First 100 chars
                })
        
        # Sort by date
        events.sort(key=lambda x: x.get('date', ''))
        
        return events
    
    def _analyze_process(
        self,
        prs: List[Dict[str, Any]],
        emails: List[Dict[str, Any]],
        irc_messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze the process used."""
        # Check if process was documented
        process_keywords = ['procedure', 'process', 'policy', 'guideline', 'rule']
        
        documented = False
        public = False
        
        # Check emails for process documentation
        for email in emails:
            text = f"{email.get('subject', '')} {email.get('body', '')}".lower()
            if any(keyword in text for keyword in self.luke_keywords):
                if any(proc_keyword in text for proc_keyword in process_keywords):
                    documented = True
                    public = True
        
        # Check PRs
        for pr in prs:
            text = f"{pr.get('title', '')} {pr.get('body', '')}".lower()
            if any(keyword in text for keyword in self.luke_keywords):
                if any(proc_keyword in text for proc_keyword in process_keywords):
                    documented = True
                    public = True
        
        return {
            'process_documented': documented,
            'decision_public': public,
            'channels_used': ['github', 'email', 'irc'],
            'note': 'Full process analysis requires detailed review of all communications'
        }
    
    def _compare_to_other_actions(
        self,
        prs: List[Dict[str, Any]],
        emails: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Compare to other maintainer actions."""
        # This would require identifying other maintainer removals/appointments
        # For now, return structure
        
        return {
            'other_maintainer_actions': 'unknown',
            'consistency': 'requires_comparison',
            'note': 'Requires identification of other maintainer status changes'
        }
    
    def _analyze_documentation(
        self,
        prs: List[Dict[str, Any]],
        emails: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze documentation of the case."""
        # Count mentions
        pr_mentions = sum(
            1 for pr in prs
            if any(keyword in f"{pr.get('title', '')} {pr.get('body', '')}".lower() for keyword in self.luke_keywords)
        )
        
        email_mentions = sum(
            1 for email in emails
            if any(keyword in f"{email.get('subject', '')} {email.get('body', '')}".lower() for keyword in self.luke_keywords)
        )
        
        return {
            'pr_mentions': pr_mentions,
            'email_mentions': email_mentions,
            'total_mentions': pr_mentions + email_mentions,
            'documentation_level': 'high' if (pr_mentions + email_mentions) > 10 else 'low'
        }
    
    def _save_results(self, results: Dict[str, Any]):
        """Save analysis results."""
        result = create_result_template('luke_case_study_analysis', '1.0.0')
        result['metadata']['timestamp'] = datetime.now().isoformat()
        result['metadata']['data_sources'] = [
            'data/processed/enriched_prs.jsonl',
            'data/processed/cleaned_emails.jsonl',
            'data/processed/cleaned_irc.jsonl'
        ]
        result['data'] = results
        
        output_file = self.analysis_dir / 'luke_case_study_analysis.json'
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        logger.info(f"Results saved to {output_file}")
        
        # Save timeline separately
        timeline_file = self.analysis_dir / 'timeline.json'
        with open(timeline_file, 'w') as f:
            json.dump(results.get('timeline', []), f, indent=2)
        
        logger.info(f"Timeline saved to {timeline_file}")


def main():
    """Main entry point."""
    analyzer = LukeCaseStudyAnalyzer()
    analyzer.run_analysis()
    return 0


if __name__ == '__main__':
    sys.exit(main())

