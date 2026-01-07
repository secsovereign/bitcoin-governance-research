#!/usr/bin/env python3
"""
Data Enrichment Pipeline - Add maintainer tags, PR classifications, and metrics.

This script:
1. Tags maintainers (who has merge permissions)
2. Classifies PRs by type (bug fix, feature, consensus-related, etc.)
3. Extracts decision outcomes (merged, rejected, closed)
4. Calculates time-to-decision metrics
5. Adds complexity metrics (LOC, files changed, etc.)
"""

import sys
import json
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import defaultdict
import re
try:
    from tqdm import tqdm
except ImportError:
    # Fallback if tqdm not available
    def tqdm(iterable, *args, **kwargs):
        return iterable

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir, get_analysis_dir
from src.utils.data_quality import DataQualityTracker

logger = setup_logger()


class DataEnricher:
    """Enriches cleaned data with additional metadata and metrics."""
    
    def __init__(self):
        """Initialize data enricher."""
        self.data_dir = get_data_dir()
        self.processed_dir = self.data_dir / 'processed'
        self.analysis_dir = get_analysis_dir()
        
        # Load identity mappings
        self.identity_mappings = self._load_identity_mappings()
        self.maintainer_timeline = self._load_maintainer_timeline()
        self.release_signers = self._load_release_signers()
        self.contributors = self._load_contributors()
        self.external_pressure = self._load_external_pressure()
        self.commit_signing = self._load_commit_signing()
        
        self.stats = {
            'prs_enriched': 0,
            'maintainers_identified': 0,
            'prs_classified': 0
        }
    
    def enrich_all_data(self):
        """Enrich all cleaned data."""
        logger.info("=" * 60)
        logger.info("Data Enrichment Pipeline")
        logger.info("=" * 60)
        
        # Enrich PRs
        self._enrich_prs()
        
        # Enrich issues
        self._enrich_issues()
        
        logger.info("=" * 60)
        logger.info(f"Enrichment complete: {self.stats['prs_enriched']} PRs enriched")
        logger.info("=" * 60)
    
    def _enrich_prs(self):
        """Enrich GitHub PR data."""
        input_file = self.processed_dir / 'cleaned_prs.jsonl'
        output_file = self.processed_dir / 'enriched_prs.jsonl'
        
        if not input_file.exists():
            logger.warning(f"Cleaned PR data not found: {input_file}")
            return
        
        # Create backup of existing enriched file before overwriting
        if output_file.exists():
            backup_dir = self.data_dir.parent / 'backups' / 'safe'
            backup_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = backup_dir / f'enriched_prs_BACKUP_{timestamp}.jsonl'
            logger.info(f"Creating backup of existing enriched PRs to {backup_file.name}...")
            shutil.copy2(output_file, backup_file)
            logger.info(f"✅ Backup created: {backup_file}")
        
        logger.info(f"Enriching PRs from {input_file.name}...")
        
        total_lines = sum(1 for _ in open(input_file))
        
        with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
            for line in tqdm(infile, total=total_lines, desc="Enriching PRs"):
                try:
                    pr = json.loads(line)
                    enriched = self._enrich_pr(pr)
                    if enriched:
                        outfile.write(json.dumps(enriched) + '\n')
                        self.stats['prs_enriched'] += 1
                except Exception as e:
                    logger.error(f"Error enriching PR: {e}")
        
        logger.info(f"Enriched {self.stats['prs_enriched']} PRs")
    
    def _enrich_issues(self):
        """Enrich GitHub issue data."""
        input_file = self.processed_dir / 'cleaned_issues.jsonl'
        output_file = self.processed_dir / 'enriched_issues.jsonl'
        
        if not input_file.exists():
            logger.warning(f"Cleaned issue data not found: {input_file}")
            return
        
        logger.info(f"Enriching issues from {input_file.name}...")
        
        total_lines = sum(1 for _ in open(input_file))
        
        with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
            for line in tqdm(infile, total=total_lines, desc="Enriching issues"):
                try:
                    issue = json.loads(line)
                    enriched = self._enrich_issue(issue)
                    if enriched:
                        outfile.write(json.dumps(enriched) + '\n')
                except Exception as e:
                    logger.error(f"Error enriching issue: {e}")
    
    def _enrich_pr(self, pr: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Enrich a single PR with metadata and metrics."""
        enriched = pr.copy()
        
        # Add maintainer tags
        enriched['maintainer_tags'] = self._tag_maintainers(pr)
        
        # Classify PR type
        enriched['pr_type'] = self._classify_pr(pr)
        
        # Extract decision outcome
        enriched['decision_outcome'] = self._extract_decision_outcome(pr)
        
        # Calculate time-to-decision
        enriched['time_to_decision'] = self._calculate_time_to_decision(pr)
        
        # Calculate complexity metrics
        enriched['complexity'] = self._calculate_complexity(pr)
        
        # Add review metrics
        enriched['review_metrics'] = self._calculate_review_metrics(pr)
        
        # Add maintainer involvement
        enriched['maintainer_involvement'] = self._calculate_maintainer_involvement(pr)
        
        # Add contributor ranking
        enriched['contributor_ranking'] = self._get_contributor_ranking(pr.get('author'))
        
        # Add external pressure context (if PR discussion mentions external pressure)
        enriched['external_pressure_context'] = self._get_external_pressure_context(pr)
        
        # Add domain expertise mapping (NEW - HIGH IMPACT)
        enriched['domain_expertise'] = self._map_domain_expertise(pr)
        
        # Classify reviews (NEW - HIGH IMPACT)
        if 'reviews' in enriched:
            enriched['reviews'] = [
                {**review, **self._classify_review(review)}
                for review in enriched['reviews']
            ]
        
        # Extract linked issues (NEW - MEDIUM IMPACT)
        enriched['linked_issues'] = self._extract_issue_links(pr)
        
        return enriched
    
    def _enrich_issue(self, issue: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Enrich a single issue with metadata."""
        enriched = issue.copy()
        
        # Add maintainer tags
        enriched['maintainer_tags'] = self._tag_maintainers(issue)
        
        # Classify issue type
        enriched['issue_type'] = self._classify_issue(issue)
        
        # Calculate metrics
        enriched['comment_count'] = len(issue.get('comments', []))
        enriched['participant_count'] = len(set(
            [c.get('author') for c in issue.get('comments', [])] + [issue.get('author')]
        ))
        
        return enriched
    
    def _tag_maintainers(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Tag maintainer involvement in PR/issue."""
        tags = {
            'author_is_maintainer': False,
            'merged_by_maintainer': False,
            'maintainer_reviewers': [],
            'maintainer_commenters': [],
            'any_maintainer_involvement': False
        }
        
        author = item.get('author')
        if author:
            unified_id = self.identity_mappings.get(author, author)
            if self._is_maintainer(unified_id, item.get('created_at')):
                tags['author_is_maintainer'] = True
                tags['any_maintainer_involvement'] = True
        
        # Check merger
        merged_by = item.get('merged_by')
        if merged_by:
            unified_id = self.identity_mappings.get(merged_by, merged_by)
            if self._is_maintainer(unified_id, item.get('merged_at')):
                tags['merged_by_maintainer'] = True
                tags['any_maintainer_involvement'] = True
        
        # Check reviewers
        for review in item.get('reviews', []):
            reviewer = review.get('author')
            if reviewer:
                unified_id = self.identity_mappings.get(reviewer, reviewer)
                if self._is_maintainer(unified_id, review.get('submitted_at')):
                    if unified_id not in tags['maintainer_reviewers']:
                        tags['maintainer_reviewers'].append(unified_id)
                        tags['any_maintainer_involvement'] = True
        
        # Check commenters
        for comment in item.get('comments', []):
            commenter = comment.get('author')
            if commenter:
                unified_id = self.identity_mappings.get(commenter, commenter)
                if self._is_maintainer(unified_id, comment.get('created_at')):
                    if unified_id not in tags['maintainer_commenters']:
                        tags['maintainer_commenters'].append(unified_id)
                        tags['any_maintainer_involvement'] = True
        
        return tags
    
    def _is_maintainer(self, unified_id: str, date: Optional[str] = None) -> bool:
        """Check if user is/was a maintainer at given date."""
        if unified_id in self.maintainer_timeline:
            timeline = self.maintainer_timeline[unified_id]
            
            if date:
                # Check if maintainer at specific date
                item_date = datetime.fromisoformat(date.replace('Z', '+00:00'))
                for period in timeline.get('periods', []):
                    start = datetime.fromisoformat(period['start'].replace('Z', '+00:00'))
                    end = datetime.fromisoformat(period['end'].replace('Z', '+00:00')) if period.get('end') else datetime.now()
                    if start <= item_date <= end:
                        return True
            else:
                # Check if ever a maintainer
                return len(timeline.get('periods', [])) > 0
        
        return False
    
    def _classify_pr(self, pr: Dict[str, Any]) -> Dict[str, Any]:
        """Classify PR by type."""
        classification = {
            'primary_type': 'unknown',
            'subtypes': [],
            'consensus_related': False,
            'confidence': 'low'
        }
        
        title = (pr.get('title') or '').lower()
        body = (pr.get('body') or '').lower()
        # Handle labels - can be strings or dicts
        labels_raw = pr.get('labels', [])
        labels = []
        for l in labels_raw:
            if isinstance(l, str):
                labels.append(l.lower())
            elif isinstance(l, dict):
                labels.append(l.get('name', '').lower())
            else:
                labels.append(str(l).lower())
        text = f"{title} {body}"
        
        # Consensus-related keywords
        consensus_keywords = [
            'consensus', 'validation', 'block', 'transaction', 'script',
            'witness', 'segwit', 'taproot', 'soft fork', 'hard fork',
            'bip', 'checktransaction', 'connectblock'
        ]
        
        if any(kw in text for kw in consensus_keywords):
            classification['consensus_related'] = True
            classification['primary_type'] = 'consensus'
            classification['confidence'] = 'medium'
        
        # Bug fix
        bug_keywords = ['fix', 'bug', 'issue', 'error', 'crash', 'segfault']
        if any(kw in text for kw in bug_keywords) or 'bug' in labels:
            if classification['primary_type'] == 'unknown':
                classification['primary_type'] = 'bugfix'
                classification['confidence'] = 'high'
            classification['subtypes'].append('bugfix')
        
        # Feature
        feature_keywords = ['feature', 'add', 'implement', 'new', 'support']
        if any(kw in text for kw in feature_keywords) or 'feature' in labels:
            if classification['primary_type'] == 'unknown':
                classification['primary_type'] = 'feature'
                classification['confidence'] = 'medium'
            classification['subtypes'].append('feature')
        
        # Documentation
        doc_keywords = ['doc', 'documentation', 'readme', 'comment', 'typo']
        if any(kw in text for kw in doc_keywords) or 'docs' in labels:
            if classification['primary_type'] == 'unknown':
                classification['primary_type'] = 'documentation'
                classification['confidence'] = 'high'
            classification['subtypes'].append('documentation')
        
        # Refactor
        refactor_keywords = ['refactor', 'cleanup', 'reorganize', 'restructure']
        if any(kw in text for kw in refactor_keywords) or 'refactor' in labels:
            if classification['primary_type'] == 'unknown':
                classification['primary_type'] = 'refactor'
                classification['confidence'] = 'medium'
            classification['subtypes'].append('refactor')
        
        # Performance
        perf_keywords = ['performance', 'optimize', 'speed', 'faster', 'benchmark']
        if any(kw in text for kw in perf_keywords):
            classification['subtypes'].append('performance')
        
        return classification
    
    def _classify_issue(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """Classify issue by type."""
        classification = {
            'primary_type': 'question',
            'subtypes': []
        }
        
        title = (issue.get('title') or '').lower()
        body = (issue.get('body') or '').lower()
        # Handle labels - can be strings or dicts
        labels_raw = issue.get('labels', [])
        labels = []
        for l in labels_raw:
            if isinstance(l, str):
                labels.append(l.lower())
            elif isinstance(l, dict):
                labels.append(l.get('name', '').lower())
            else:
                labels.append(str(l).lower())
        text = f"{title} {body}"
        
        # Bug report
        if 'bug' in labels or any(kw in text for kw in ['bug', 'error', 'crash', 'issue']):
            classification['primary_type'] = 'bug_report'
        
        # Feature request
        if 'enhancement' in labels or 'feature' in labels:
            classification['primary_type'] = 'feature_request'
        
        return classification
    
    def _extract_decision_outcome(self, pr: Dict[str, Any]) -> Dict[str, Any]:
        """Extract decision outcome for PR."""
        outcome = {
            'final_state': pr.get('state', 'unknown'),
            'merged': pr.get('state') == 'merged',
            'closed': pr.get('state') == 'closed',
            'open': pr.get('state') == 'open',
            'merged_at': pr.get('merged_at'),
            'closed_at': pr.get('closed_at')
        }
        
        return outcome
    
    def _calculate_time_to_decision(self, pr: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Calculate time-to-decision metrics."""
        created_at = pr.get('created_at')
        merged_at = pr.get('merged_at')
        closed_at = pr.get('closed_at')
        
        if not created_at:
            return None
        
        try:
            created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            
            metrics = {
                'created_at': created_at,
                'days_to_decision': None,
                'hours_to_decision': None
            }
            
            decision_date = None
            if merged_at:
                decision_date = datetime.fromisoformat(merged_at.replace('Z', '+00:00'))
                metrics['decision_type'] = 'merge'
            elif closed_at:
                decision_date = datetime.fromisoformat(closed_at.replace('Z', '+00:00'))
                metrics['decision_type'] = 'close'
            
            if decision_date:
                delta = decision_date - created
                metrics['days_to_decision'] = delta.total_seconds() / 86400
                metrics['hours_to_decision'] = delta.total_seconds() / 3600
            
            return metrics
        except Exception as e:
            logger.warning(f"Error calculating time to decision: {e}")
            return None
    
    def _calculate_complexity(self, pr: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate PR complexity metrics."""
        return {
            'additions': pr.get('additions', 0),
            'deletions': pr.get('deletions', 0),
            'total_changes': pr.get('additions', 0) + pr.get('deletions', 0),
            'files_changed': len(pr.get('files', [])),
            'commits': pr.get('commits', 0)
        }
    
    def _calculate_review_metrics(self, pr: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate review-related metrics."""
        reviews = pr.get('reviews', [])
        
        approvals = sum(1 for r in reviews if r.get('state') == 'APPROVED')
        rejections = sum(1 for r in reviews if r.get('state') == 'CHANGES_REQUESTED')
        comments_only = sum(1 for r in reviews if r.get('state') == 'COMMENTED')
        
        # Check for NACKs
        nacks = []
        for review in reviews:
            body = (review.get('body') or '').upper()
            if 'NACK' in body or 'CONCEPT NACK' in body or 'APPROACH NACK' in body:
                nacks.append({
                    'author': review.get('author'),
                    'type': 'NACK',
                    'timestamp': review.get('submitted_at')
                })
        
        return {
            'total_reviews': len(reviews),
            'approvals': approvals,
            'rejections': rejections,
            'comments_only': comments_only,
            'nacks': nacks,
            'nack_count': len(nacks),
            'unique_reviewers': len(set(r.get('author') for r in reviews))
        }
    
    def _calculate_maintainer_involvement(self, pr: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate maintainer involvement metrics."""
        tags = self._tag_maintainers(pr)
        
        return {
            'maintainer_reviewers_count': len(tags['maintainer_reviewers']),
            'maintainer_commenters_count': len(tags['maintainer_commenters']),
            'has_maintainer_review': len(tags['maintainer_reviewers']) > 0,
            'has_maintainer_comment': len(tags['maintainer_commenters']) > 0,
            'author_is_maintainer': tags['author_is_maintainer'],
            'merged_by_maintainer': tags['merged_by_maintainer']
        }
    
    def _load_identity_mappings(self) -> Dict[str, str]:
        """Load identity mappings."""
        mapping_file = self.analysis_dir / 'user_identities' / 'identity_mappings.json'
        
        if not mapping_file.exists():
            logger.warning(f"Identity mappings not found: {mapping_file}")
            return {}
        
        try:
            with open(mapping_file, 'r') as f:
                data = json.load(f)
                # Flatten mapping structure
                mappings = {}
                for unified_id, platforms in data.items():
                    for platform, ids in platforms.items():
                        for platform_id in ids:
                            mappings[platform_id] = unified_id
                return mappings
        except Exception as e:
            logger.error(f"Error loading identity mappings: {e}")
            return {}
    
    def _load_maintainer_timeline(self) -> Dict[str, Any]:
        """Load maintainer timeline."""
        timeline_file = self.data_dir / 'processed' / 'maintainer_timeline.json'
        
        if not timeline_file.exists():
            logger.warning(f"Maintainer timeline not found: {timeline_file}")
            return {}
        
        try:
            with open(timeline_file, 'r') as f:
                return json.load(f).get('maintainer_timeline', {})
        except Exception as e:
            logger.error(f"Error loading maintainer timeline: {e}")
            return {}
    
    def _load_release_signers(self) -> Dict[str, Any]:
        """Load release signer data."""
        signers_file = self.processed_dir / 'cleaned_release_signers.jsonl'
        
        if not signers_file.exists():
            logger.warning(f"Release signers data not found: {signers_file}")
            return {}
        
        signers_data = {
            'releases': [],
            'signers': {},
            'signing_stats': {
                'total': 0,
                'signed': 0,
                'unsigned': 0,
                'unique_signers': set()
            }
        }
        
        try:
            with open(signers_file, 'r') as f:
                for line in f:
                    release = json.loads(line)
                    signers_data['releases'].append(release)
                    signers_data['signing_stats']['total'] += 1
                    
                    if release.get('is_signed'):
                        signers_data['signing_stats']['signed'] += 1
                        signer_email = release.get('signer_email')
                        if signer_email:
                            signers_data['signing_stats']['unique_signers'].add(signer_email)
                            if signer_email not in signers_data['signers']:
                                signers_data['signers'][signer_email] = {
                                    'name': release.get('signer_name'),
                                    'release_count': 0
                                }
                            signers_data['signers'][signer_email]['release_count'] += 1
                    else:
                        signers_data['signing_stats']['unsigned'] += 1
            
            # Convert set to count
            signers_data['signing_stats']['unique_signers'] = len(signers_data['signing_stats']['unique_signers'])
            
        except Exception as e:
            logger.error(f"Error loading release signers: {e}")
        
        return signers_data
    
    def _load_contributors(self) -> Dict[str, Any]:
        """Load GitHub contributors data."""
        contributors_file = self.data_dir / 'github' / 'collaborators.json'
        
        if not contributors_file.exists():
            logger.warning(f"Contributors data not found: {contributors_file}")
            return {}
        
        try:
            with open(contributors_file, 'r') as f:
                data = json.load(f)
                contributors = data.get('contributors', [])
                
                # Create lookup by login
                contributor_lookup = {}
                for i, contrib in enumerate(contributors):
                    login = contrib.get('login')
                    if login:
                        contributor_lookup[login] = {
                            'rank': i + 1,
                            'contributions': contrib.get('contributions', 0),
                            'name': contrib.get('name'),
                            'email': contrib.get('email'),
                            'profile': contrib
                        }
                
                return {
                    'total': len(contributors),
                    'lookup': contributor_lookup,
                    'top_contributors': contributors[:10]  # Top 10
                }
        except Exception as e:
            logger.error(f"Error loading contributors: {e}")
            return {}
    
    def _load_external_pressure(self) -> Dict[str, Any]:
        """Load external pressure indicators data."""
        pressure_file = self.data_dir / 'processed' / 'external_pressure_indicators.json'
        
        if not pressure_file.exists():
            logger.warning(f"External pressure indicators not found: {pressure_file}")
            return {}
        
        try:
            with open(pressure_file, 'r') as f:
                data = json.load(f)
                return data
        except Exception as e:
            logger.error(f"Error loading external pressure indicators: {e}")
            return {}
    
    def _load_commit_signing(self) -> Dict[str, Any]:
        """Load commit signing data."""
        signing_file = self.data_dir / 'github' / 'commit_signing.jsonl'
        
        if not signing_file.exists():
            logger.warning(f"Commit signing data not found: {signing_file}")
            return {}
        
        signing_data = {}
        try:
            with open(signing_file, 'r') as f:
                for line in f:
                    record = json.loads(line)
                    pr_number = record.get('pr_number')
                    if pr_number:
                        signing_data[pr_number] = record
        except Exception as e:
            logger.error(f"Error loading commit signing data: {e}")
        
        return signing_data
    
    def _get_external_pressure_context(self, pr: Dict[str, Any]) -> Dict[str, Any]:
        """Get external pressure context for a PR."""
        if not self.external_pressure:
            return {}
        
        # Check if PR discussion mentions external pressure
        # This would require matching PR dates/discussions to pressure indicators
        # For now, return summary stats
        summary = self.external_pressure.get('summary', {})
        
        return {
            'has_pressure_data': True,
            'mailing_list_pressure_rate': summary.get('mailing_lists', {}).get('percentage', 0),
            'irc_pressure_rate': summary.get('irc', {}).get('percentage', 0),
            'total_pressure_mentions': summary.get('total_pressure_mentions', 0)
        }
    
    def _map_domain_expertise(self, pr: Dict[str, Any]) -> Dict[str, Any]:
        """Map PR to code domains based on file paths."""
        domains = set()
        files = pr.get('files', [])
        
        # Domain mapping based on file paths
        domain_mapping = {
            'consensus': ['consensus', 'validation', 'checktransaction', 'connectblock', 'block', 'chainstate'],
            'networking': ['net', 'p2p', 'peer', 'connection', 'socket', 'addrman'],
            'wallet': ['wallet', 'utxo', 'coinselection'],
            'rpc': ['rpc', 'rest', 'zmq'],
            'crypto': ['crypto', 'hash', 'signature', 'ecdsa', 'secp256k1', 'sha256', 'ripemd160'],
            'script': ['script', 'interpreter', 'opcode'],
            'mining': ['mining', 'pow', 'difficulty', 'blocktemplate'],
            'testing': ['test', 'qa', 'fuzz'],
            'build': ['build', 'cmake', 'autotools', 'configure'],
            'docs': ['doc', 'readme', '.md']
        }
        
        domain_counts = defaultdict(int)
        
        for file_info in files:
            filename = file_info.get('filename', '').lower()
            path_parts = filename.split('/')
            
            # Check path parts and filename
            for domain, keywords in domain_mapping.items():
                if any(kw in filename for kw in keywords) or any(kw in path_parts for kw in keywords):
                    domains.add(domain)
                    domain_counts[domain] += 1
                    break
        
        return {
            'domains': sorted(list(domains)),
            'domain_count': len(domains),
            'is_multi_domain': len(domains) > 1,
            'domain_distribution': dict(domain_counts),
            'primary_domain': max(domain_counts.items(), key=lambda x: x[1])[0] if domain_counts else None
        }
    
    def _classify_review(self, review: Dict[str, Any]) -> Dict[str, Any]:
        """Classify review by type, sentiment, and strength."""
        state = (review.get('state') or '').lower()
        body = (review.get('body') or '').lower()
        
        # Type classification
        review_type = 'comment'
        if state == 'approved' or state == 'approve':
            review_type = 'approval'
        elif state == 'changes_requested' or state == 'request_changes':
            review_type = 'request_changes'
        elif state == 'dismissed':
            review_type = 'dismissal'
        
        # Sentiment classification (simple keyword-based)
        positive_words = ['good', 'nice', 'looks good', 'lgtm', 'approved', 'great', 'excellent', 'ack', 'utack']
        negative_words = ['nack', 'concern', 'issue', 'problem', 'wrong', 'bad', 'disagree', 'reject']
        neutral_words = ['comment', 'question', 'suggestion', 'consider']
        
        sentiment = 'neutral'
        if any(word in body for word in positive_words):
            sentiment = 'positive'
        elif any(word in body for word in negative_words):
            sentiment = 'negative'
        elif any(word in body for word in neutral_words):
            sentiment = 'neutral'
        
        # Strength classification
        strength = 'weak'
        strong_indicators = ['strong', 'critical', 'important', 'major', 'significant', 'serious']
        if len(body) > 200 or any(word in body for word in strong_indicators):
            strength = 'strong'
        elif len(body) < 50:
            strength = 'weak'
        else:
            strength = 'medium'
        
        # NACK detection
        is_nack = 'nack' in body or 'concept nack' in body or 'approach nack' in body
        
        return {
            'review_type': review_type,
            'sentiment': sentiment,
            'strength': strength,
            'is_nack': is_nack,
            'body_length': len(body)
        }
    
    def _extract_issue_links(self, pr: Dict[str, Any]) -> List[int]:
        """Extract linked issue numbers from PR."""
        import re
        
        body = pr.get('body', '')
        title = pr.get('title', '')
        text = f"{title} {body}"
        
        # Match patterns like "Fixes #123", "Closes #456", "#789"
        patterns = [
            r'(?:fixes?|closes?|resolves?|related to|refs?|references?)\s*#(\d+)',
            r'#(\d+)'
        ]
        
        issue_numbers = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            issue_numbers.extend([int(m) for m in matches if m.isdigit()])
        
        # Remove duplicates and sort
        return sorted(list(set(issue_numbers)))
    
    def _get_contributor_ranking(self, author: Optional[str]) -> Optional[Dict[str, Any]]:
        """Get contributor ranking for an author."""
        if not author or not self.contributors:
            return None
        
        contrib_info = self.contributors.get('lookup', {}).get(author)
        if contrib_info:
            return {
                'rank': contrib_info['rank'],
                'contributions': contrib_info['contributions'],
                'is_top_contributor': contrib_info['rank'] <= 10
            }
        
        return None


def main():
    """Main entry point."""
    enricher = DataEnricher()
    enricher.enrich_all_data()
    return 0


if __name__ == '__main__':
    sys.exit(main())

