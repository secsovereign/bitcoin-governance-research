#!/usr/bin/env python3
"""
Developer History Generator - Generate comprehensive histories for maintainers/developers.

Creates per-developer timelines combining all public sources:
- GitHub activity (PRs, issues, comments, reviews)
- Mailing list participation
- IRC chat activity
- Maintainer status changes
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir, get_analysis_dir

logger = setup_logger()


class DeveloperHistoryGenerator:
    """Generates comprehensive developer histories."""
    
    def __init__(self):
        """Initialize generator."""
        self.data_dir = get_data_dir()
        self.analysis_dir = get_analysis_dir()
        
        # Load identity mappings
        self.identity_mappings = self._load_identity_mappings()
        self.unified_profiles = self._load_unified_profiles()
        
        # Developer histories
        self.histories = {}
    
    def generate_all_histories(self):
        """Generate histories for all developers."""
        logger.info("=" * 60)
        logger.info("Generating Developer Histories")
        logger.info("=" * 60)
        
        # Generate for all users - save immediately to avoid memory issues
        output_dir = self.analysis_dir / 'developer_histories'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Prioritize maintainers and active developers
        maintainers = [uid for uid, prof in self.unified_profiles.items() 
                      if prof.get('is_maintainer', False)]
        
        # Process maintainers first, then others (limit to top 1000 most active to avoid timeout)
        priority_ids = maintainers.copy()
        other_ids = [uid for uid in self.unified_profiles.keys() if uid not in priority_ids]
        
        # Limit to 1000 most active non-maintainers to keep runtime reasonable
        MAX_NON_MAINTAINERS = 1000
        if len(other_ids) > MAX_NON_MAINTAINERS:
            logger.info(f"Limiting to {MAX_NON_MAINTAINERS} most active non-maintainers (out of {len(other_ids)})")
            # Sort by activity level if available, otherwise just take first N
            other_ids = other_ids[:MAX_NON_MAINTAINERS]
        
        all_ids = priority_ids + other_ids
        logger.info(f"Processing {len(priority_ids)} maintainers + {len(other_ids)} other developers = {len(all_ids)} total")
        
        saved_count = 0
        skipped_count = 0
        for unified_id in all_ids:
            profile = self.unified_profiles[unified_id]
            
            # Quick check: skip if no activity at all (unless maintainer)
            is_maintainer = profile.get('is_maintainer', False)
            has_github = len(profile.get('github_usernames', [])) > 0
            has_email = len(profile.get('emails', [])) > 0
            has_irc = len(profile.get('irc_nicknames', [])) > 0
            has_any_identity = has_github or has_email or has_irc
            
            # Skip if no identities at all (unless maintainer)
            if not is_maintainer and not has_any_identity:
                skipped_count += 1
                continue
            
            history = self._generate_history(unified_id, profile)
            if history and history.get('statistics', {}).get('total_activities', 0) > 0:
                self.histories[unified_id] = history
                
                # Save immediately to avoid memory buildup
                primary_identity = history.get('primary_identity', unified_id)
                safe_name = "".join(c for c in primary_identity if c.isalnum() or c in ('-', '_'))[:50]
                safe_id = unified_id.replace('/', '_').replace('\\', '_').replace(':', '_')[:20]
                filename = f"{safe_name}_{safe_id}.json"
                
                with open(output_dir / filename, 'w') as f:
                    json.dump(history, f, indent=2)
                
                saved_count += 1
                if saved_count % 50 == 0:
                    logger.info(f"Processed {saved_count} histories, skipped {skipped_count} low-activity...")
        
        logger.info(f"Completed: {saved_count} saved, {skipped_count} skipped (low activity)")
        
        # Generate for maintainers specifically
        maintainers = [uid for uid, prof in self.unified_profiles.items() 
                      if prof.get('is_maintainer', False)]
        
        logger.info(f"Generated {len(self.histories)} developer histories")
        logger.info(f"Including {len(maintainers)} maintainer histories")
        
        # Save all histories
        self._save_histories()
        
        # Generate maintainer-specific reports
        self._generate_maintainer_reports(maintainers)
    
    def _load_identity_mappings(self) -> Dict[str, Any]:
        """Load identity mappings."""
        mappings_file = self.analysis_dir / 'user_identities' / 'identity_mappings.json'
        if mappings_file.exists():
            with open(mappings_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _load_unified_profiles(self) -> Dict[str, Dict[str, Any]]:
        """Load unified user profiles."""
        profiles_file = self.analysis_dir / 'user_identities' / 'unified_profiles.json'
        if profiles_file.exists():
            with open(profiles_file, 'r') as f:
                profiles_list = json.load(f)
                return {p['unified_id']: p for p in profiles_list}
        return {}
    
    def _generate_history(self, unified_id: str, profile: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate history for a single developer."""
        history = {
            'unified_id': unified_id,
            'primary_identity': profile.get('primary_identity', unified_id),
            'is_maintainer': profile.get('is_maintainer', False),
            'sources': profile.get('sources', []),
            'timeline': [],
            'statistics': {},
        }
        
        # Collect GitHub activity
        github_username = profile.get('github_username')
        if github_username:
            github_activity = self._collect_github_activity(github_username)
            history['timeline'].extend(github_activity)
        
        # Collect mailing list activity
        email = profile.get('email')
        if email:
            email_activity = self._collect_email_activity(email)
            history['timeline'].extend(email_activity)
        
        # Collect IRC activity
        irc_nickname = profile.get('irc_nickname')
        if irc_nickname:
            irc_activity = self._collect_irc_activity(irc_nickname)
            history['timeline'].extend(irc_activity)
        
        # Sort timeline chronologically
        history['timeline'].sort(key=lambda x: x.get('timestamp') or '')
        
        # Calculate statistics
        history['statistics'] = self._calculate_statistics(history['timeline'])
        
        return history
    
    def _collect_github_activity(self, username: str) -> List[Dict[str, Any]]:
        """Collect GitHub activity for a user."""
        activities = []
        
        # Use enriched PRs data (complete dataset)
        processed_dir = self.data_dir / 'processed'
        prs_file = processed_dir / 'enriched_prs.jsonl'
        if not prs_file.exists():
            prs_file = processed_dir / 'cleaned_prs.jsonl'
        if not prs_file.exists():
            prs_file = self.data_dir / 'github' / 'prs_raw.jsonl'
        
        issues_file = self.data_dir / 'github' / 'issues_raw.jsonl'
        
        for file_path in [prs_file, issues_file]:
            if not file_path.exists():
                continue
            
            with open(file_path, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        
                        # PR/Issue authored
                        if data.get('author') == username:
                            activities.append({
                                'timestamp': data.get('created_at'),
                                'type': 'pr_authored' if 'number' in data and file_path.name.startswith('prs') else 'issue_authored',
                                'source': 'github',
                                'title': data.get('title'),
                                'number': data.get('number'),
                                'state': data.get('state'),
                                'merged': data.get('merged', False),
                            })
                        
                        # Comments
                        for comment in data.get('comments', []):
                            if comment.get('author') == username:
                                activities.append({
                                    'timestamp': comment.get('created_at'),
                                    'type': 'comment',
                                    'source': 'github',
                                    'pr_number': data.get('number'),
                                    'body_preview': comment.get('body', '')[:100],
                                })
                        
                        # Reviews
                        for review in data.get('reviews', []):
                            if review.get('author') == username:
                                activities.append({
                                    'timestamp': review.get('created_at'),
                                    'type': 'review',
                                    'source': 'github',
                                    'pr_number': data.get('number'),
                                    'state': review.get('state'),
                                    'body_preview': review.get('body', '')[:100] if review.get('body') else None,
                                })
                    
                    except json.JSONDecodeError:
                        continue
        
        return activities
    
    def _collect_email_activity(self, email: str) -> List[Dict[str, Any]]:
        """Collect mailing list activity for a user."""
        activities = []
        
        emails_file = self.data_dir / 'mailing_lists' / 'emails.jsonl'
        if not emails_file.exists():
            return activities
        
        with open(emails_file, 'r') as f:
            for line in f:
                try:
                    email_data = json.loads(line)
                    
                    # Check if this email matches
                    from_field = email_data.get('from', '')
                    if email in from_field:
                        activities.append({
                            'timestamp': email_data.get('date'),
                            'type': 'email',
                            'source': 'mailing_list',
                            'list_name': email_data.get('list_name'),
                            'subject': email_data.get('subject'),
                            'body_preview': email_data.get('original_text', '')[:100],
                        })
                
                except json.JSONDecodeError:
                    continue
        
        return activities
    
    def _collect_irc_activity(self, nickname: str) -> List[Dict[str, Any]]:
        """Collect IRC activity for a user."""
        activities = []
        
        messages_file = self.data_dir / 'irc' / 'messages.jsonl'
        if not messages_file.exists():
            return activities
        
        with open(messages_file, 'r') as f:
            for line in f:
                try:
                    msg = json.loads(line)
                    
                    if msg.get('nickname') == nickname:
                        activities.append({
                            'timestamp': msg.get('timestamp'),
                            'type': 'irc_message',
                            'source': 'irc',
                            'channel': msg.get('channel'),
                            'message_preview': msg.get('message', '')[:100],
                        })
                
                except json.JSONDecodeError:
                    continue
        
        return activities
    
    def _calculate_statistics(self, timeline: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate statistics from timeline."""
        stats = {
            'total_activities': len(timeline),
            'first_activity': timeline[0].get('timestamp') if timeline else None,
            'last_activity': timeline[-1].get('timestamp') if timeline else None,
            'by_type': defaultdict(int),
            'by_source': defaultdict(int),
            'by_year': defaultdict(int),
        }
        
        for activity in timeline:
            stats['by_type'][activity.get('type', 'unknown')] += 1
            stats['by_source'][activity.get('source', 'unknown')] += 1
            
            timestamp = activity.get('timestamp', '')
            if timestamp:
                try:
                    year = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).year
                    stats['by_year'][year] += 1
                except:
                    pass
        
        # Convert defaultdicts to regular dicts
        stats['by_type'] = dict(stats['by_type'])
        stats['by_source'] = dict(stats['by_source'])
        stats['by_year'] = dict(stats['by_year'])
        
        return stats
    
    def _save_histories(self):
        """Save all developer histories - individual files only, no massive combined file."""
        output_dir = self.analysis_dir / 'developer_histories'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save individual history files only - NO massive all_histories.json
        saved_count = 0
        for unified_id, history in self.histories.items():
            primary_identity = history.get('primary_identity', unified_id)
            safe_name = "".join(c for c in primary_identity if c.isalnum() or c in ('-', '_'))[:50]  # Limit length
            safe_id = unified_id.replace('/', '_').replace('\\', '_').replace(':', '_')[:20]
            filename = f"{safe_name}_{safe_id}.json"
            
            with open(output_dir / filename, 'w') as f:
                json.dump(history, f, indent=2)
            
            saved_count += 1
            if saved_count % 100 == 0:
                logger.info(f"Saved {saved_count} developer histories...")
        
        # Create a lightweight summary index instead of full data
        summary = {
            unified_id: {
                'primary_identity': h.get('primary_identity', unified_id),
                'is_maintainer': h.get('is_maintainer', False),
                'total_activities': h.get('statistics', {}).get('total_activities', 0),
                'first_activity': h.get('statistics', {}).get('first_activity'),
                'last_activity': h.get('statistics', {}).get('last_activity'),
            }
            for unified_id, h in self.histories.items()
        }
        
        with open(output_dir / 'developer_summary_index.json', 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Saved {saved_count} individual developer histories (no massive combined file)")
        logger.info(f"Created summary index with {len(summary)} developers")
    
    def _generate_maintainer_reports(self, maintainer_ids: List[str]):
        """Generate detailed reports for maintainers."""
        output_dir = self.analysis_dir / 'developer_histories' / 'maintainers'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for unified_id in maintainer_ids:
            if unified_id in self.histories:
                history = self.histories[unified_id]
                
                # Generate markdown report
                report = self._generate_markdown_report(history)
                
                primary_identity = history['primary_identity']
                safe_name = "".join(c for c in primary_identity if c.isalnum() or c in ('-', '_'))
                filename = f"{safe_name}_report.md"
                
                with open(output_dir / filename, 'w') as f:
                    f.write(report)
        
        logger.info(f"Generated {len(maintainer_ids)} maintainer reports")
    
    def _generate_markdown_report(self, history: Dict[str, Any]) -> str:
        """Generate markdown report for a developer."""
        lines = []
        lines.append(f"# Developer History: {history['primary_identity']}")
        lines.append("")
        lines.append(f"**Unified ID**: {history['unified_id']}")
        lines.append(f"**Maintainer**: {'Yes' if history['is_maintainer'] else 'No'}")
        lines.append(f"**Sources**: {', '.join(history['sources'])}")
        lines.append("")
        
        stats = history['statistics']
        lines.append("## Statistics")
        lines.append("")
        lines.append(f"- **Total Activities**: {stats['total_activities']:,}")
        lines.append(f"- **First Activity**: {stats['first_activity']}")
        lines.append(f"- **Last Activity**: {stats['last_activity']}")
        lines.append("")
        
        lines.append("### Activity by Type")
        for activity_type, count in sorted(stats['by_type'].items(), key=lambda x: -x[1]):
            lines.append(f"- **{activity_type}**: {count:,}")
        lines.append("")
        
        lines.append("### Activity by Source")
        for source, count in sorted(stats['by_source'].items(), key=lambda x: -x[1]):
            lines.append(f"- **{source}**: {count:,}")
        lines.append("")
        
        lines.append("### Activity by Year")
        for year, count in sorted(stats['by_year'].items()):
            lines.append(f"- **{year}**: {count:,}")
        lines.append("")
        
        lines.append("## Timeline")
        lines.append("")
        lines.append("(First 100 activities)")
        lines.append("")
        
        for activity in history['timeline'][:100]:
            timestamp = activity.get('timestamp', 'Unknown')
            activity_type = activity.get('type', 'unknown')
            lines.append(f"- **{timestamp}** [{activity_type}]: {activity.get('title', activity.get('subject', activity.get('message_preview', '')))}")
        
        if len(history['timeline']) > 100:
            lines.append(f"\n... and {len(history['timeline']) - 100} more activities")
        
        return "\n".join(lines)


def main():
    """Main entry point."""
    generator = DeveloperHistoryGenerator()
    generator.generate_all_histories()


if __name__ == '__main__':
    main()

