#!/usr/bin/env python3
"""
Analyze Satoshi Nakamoto's communications for governance insights.

This script extracts governance-related patterns, decision-making processes,
authority statements, and community interaction patterns from Satoshi's
public communications.
"""

import json
import re
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime
from typing import Dict, List, Any, Optional
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger

logger = setup_logger()

# Governance-related keywords and patterns
GOVERNANCE_KEYWORDS = [
    'governance', 'decision', 'consensus', 'vote', 'voting', 'proposal',
    'change', 'upgrade', 'fork', 'hard fork', 'soft fork', 'protocol',
    'rule', 'rule change', 'authority', 'control', 'power', 'leadership',
    'maintainer', 'developer', 'core', 'bitcoin core', 'bip', 'improvement',
    'standard', 'specification', 'compatibility', 'backward compatible',
    'backwards compatible', 'decentralized', 'centralized', 'trust',
    'trustless', 'permissionless', 'permissioned', 'mining', 'miner',
    'node', 'full node', 'client', 'implementation', 'compatibility',
    'network', 'upgrade path', 'activation', 'deployment', 'rollout'
]

DECISION_PATTERNS = [
    r'i (decide|decided|will|should|must|need to)',
    r'we (should|must|need to|will|decided)',
    r'this (should|must|will|needs to)',
    r'proposal',
    r'suggest',
    r'recommend',
    r'consensus',
    r'agreement',
    r'disagreement',
    r'oppose',
    r'support'
]

AUTHORITY_PATTERNS = [
    r'i (control|own|manage|maintain|run)',
    r'my (decision|choice|project|code|software)',
    r'i (am|was) (responsible|in charge|the (creator|founder|developer))',
    r'bitcoin (is|was) (my|mine)',
    r'i (created|designed|built|wrote)'
]

COMMUNITY_PATTERNS = [
    r'community',
    r'users?',
    r'developers?',
    r'miners?',
    r'everyone',
    r'anyone',
    r'people',
    r'others?',
    r'we',
    r'you'
]


def load_communications(data_path: Path) -> List[Dict[str, Any]]:
    """Load Satoshi communications from JSONL file."""
    communications = []
    
    if not data_path.exists():
        logger.error(f"Data file not found: {data_path}")
        return communications
    
    try:
        with open(data_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    comm = json.loads(line)
                    communications.append(comm)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse line: {e}")
                    continue
    except Exception as e:
        logger.error(f"Error loading communications: {e}")
    
    logger.info(f"Loaded {len(communications)} communications")
    return communications


def filter_satoshi_communications(comms: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter for actual Satoshi communications."""
    satoshi_comms = []
    
    satoshi_emails = [
        'satoshi@vistomail.com',
        'satoshi@anonymousspeech.com',
        'satoshi@bitcoin.org',
        'satoshi nakamoto'
    ]
    
    for comm in comms:
        from_field = str(comm.get('from', '')).lower()
        content = str(comm.get('content', ''))
        content_lower = content.lower()
        subject = str(comm.get('subject', '')).lower()
        source = comm.get('source', '')
        file_path = str(comm.get('file_path', '')).lower()
        filename = comm.get('filename', '').lower()
        
        # Check if it's from Satoshi
        is_satoshi = False
        
        # Check from field
        if any(email in from_field for email in satoshi_emails):
            is_satoshi = True
        
        # Check if it's a known Satoshi communication
        if source == 'mailing_list' and 'satoshi' in from_field:
            is_satoshi = True
        
        # Check content for Satoshi signatures or patterns
        if 'satoshi' in from_field and ('nakamoto' in from_field or 'bitcoin' in content_lower[:200]):
            is_satoshi = True
        
        # Check filename patterns (known Satoshi files)
        if any(pattern in filename for pattern in ['satoshi', 'nakamoto', 'bitcoin-0.1']):
            if 'email' in filename or 'txt' in filename:
                is_satoshi = True
        
        # Check for forum posts from Satoshi (doc/bitcoin-forum/*.md files)
        if 'doc/bitcoin-forum' in file_path or 'bitcoin-forum' in file_path:
            # Look for "Post by: satoshi" pattern in markdown
            if 'post by: satoshi' in content_lower[:500] or 'post by satoshi' in content_lower[:500]:
                is_satoshi = True
            # Or if it's in the bitcoin-forum directory and has substantial content
            elif 'bitcoin-forum' in file_path and len(content) > 100:
                # Check if content looks like a forum post (has post metadata)
                if 'post by:' in content_lower or 'posted:' in content_lower:
                    is_satoshi = True
        
        # Check for emails in src/ directory that are from Satoshi
        if 'src/' in file_path and ('satoshi' in filename or 'nakamoto' in filename):
            if 'email' in content_lower[:200] or 'from:' in content_lower[:200]:
                is_satoshi = True
        
        # Check content for Satoshi's writing style or signatures
        if not is_satoshi and len(content) > 200:
            # Look for patterns that indicate Satoshi authorship
            satoshi_indicators = [
                'post by: satoshi',
                'from: "satoshi nakamoto"',
                'from: satoshi@',
                'satoshi nakamoto <satoshi@',
                'by satoshi on',
                'signed: satoshi'
            ]
            if any(indicator in content_lower[:1000] for indicator in satoshi_indicators):
                is_satoshi = True
        
        if is_satoshi:
            satoshi_comms.append(comm)
    
    logger.info(f"Filtered to {len(satoshi_comms)} Satoshi communications")
    return satoshi_comms


def extract_governance_insights(comms: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Extract governance insights from communications."""
    insights = {
        'total_communications': len(comms),
        'governance_mentions': [],
        'decision_statements': [],
        'authority_statements': [],
        'community_interactions': [],
        'protocol_discussions': [],
        'timeline': [],
        'communication_patterns': {},
        'key_themes': {}
    }
    
    for comm in comms:
        content = str(comm.get('content', ''))
        content_lower = content.lower()
        subject = str(comm.get('subject', ''))
        from_field = str(comm.get('from', ''))
        date = comm.get('date')
        
        # Skip if content is too short or is a PDF placeholder
        if len(content) < 30 or content.startswith('[PDF file:'):
            continue
        
        # For forum posts, extract the actual post content (may have metadata)
        if 'post by: satoshi' in content_lower or 'post by satoshi' in content_lower:
            # Try to extract just the post content, not the metadata
            # Look for patterns like "Post by: satoshi on..." followed by actual content
            post_match = re.search(r'post by:?\s*satoshi[^\n]*\n(.*)', content, re.IGNORECASE | re.DOTALL)
            if post_match:
                content = post_match.group(1)
                # Remove HTML tags and clean up
                content = re.sub(r'<[^>]+>', '', content)
                content = re.sub(r'<br\s*/?>', '\n', content, flags=re.IGNORECASE)
                full_text = f"{subject} {content}".lower()
            else:
                full_text = f"{subject} {content}".lower()
        else:
            full_text = f"{subject} {content}".lower()
        
        full_text = f"{subject} {content}".lower()
        
        # Check for governance keywords
        governance_matches = []
        for keyword in GOVERNANCE_KEYWORDS:
            if keyword in full_text:
                governance_matches.append(keyword)
        
        if governance_matches:
            insights['governance_mentions'].append({
                'date': date,
                'subject': subject,
                'from': from_field,
                'keywords': governance_matches,
                'excerpt': content[:500] if len(content) > 500 else content
            })
        
        # Check for decision patterns
        for pattern in DECISION_PATTERNS:
            matches = re.findall(pattern, full_text, re.IGNORECASE)
            if matches:
                insights['decision_statements'].append({
                    'date': date,
                    'subject': subject,
                    'from': from_field,
                    'pattern': pattern,
                    'matches': matches[:3],  # First 3 matches
                    'excerpt': _extract_context(content, pattern, 200)
                })
        
        # Check for authority patterns
        for pattern in AUTHORITY_PATTERNS:
            matches = re.findall(pattern, full_text, re.IGNORECASE)
            if matches:
                insights['authority_statements'].append({
                    'date': date,
                    'subject': subject,
                    'from': from_field,
                    'pattern': pattern,
                    'matches': matches[:3],
                    'excerpt': _extract_context(content, pattern, 200)
                })
        
        # Check for community interaction patterns
        community_matches = []
        for pattern in COMMUNITY_PATTERNS:
            if re.search(pattern, full_text, re.IGNORECASE):
                community_matches.append(pattern)
        
        if community_matches:
            insights['community_interactions'].append({
                'date': date,
                'subject': subject,
                'from': from_field,
                'patterns': community_matches,
                'excerpt': content[:500] if len(content) > 500 else content
            })
        
        # Protocol discussions (mentions of protocol, fork, upgrade, etc.)
        protocol_keywords = ['protocol', 'fork', 'upgrade', 'version', 'release', 'compatibility', 'bip']
        if any(kw in full_text for kw in protocol_keywords):
            insights['protocol_discussions'].append({
                'date': date,
                'subject': subject,
                'from': from_field,
                'excerpt': content[:500] if len(content) > 500 else content
            })
        
        # Add to timeline
        if date:
            insights['timeline'].append({
                'date': date,
                'subject': subject,
                'type': comm.get('type', 'unknown')
            })
    
    return insights


def _extract_context(text: str, pattern: str, context_length: int = 200) -> str:
    """Extract context around a pattern match."""
    matches = list(re.finditer(pattern, text, re.IGNORECASE))
    if not matches:
        return text[:context_length] if len(text) > context_length else text
    
    # Get context around first match
    match = matches[0]
    start = max(0, match.start() - context_length // 2)
    end = min(len(text), match.end() + context_length // 2)
    return text[start:end]


def analyze_communication_patterns(comms: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze communication patterns and frequencies."""
    patterns = {
        'by_year': Counter(),
        'by_type': Counter(),
        'by_recipient': Counter(),
        'communication_frequency': [],
        'topics': Counter(),
        'tone_indicators': Counter()
    }
    
    for comm in comms:
        date = comm.get('date')
        if date:
            # Try to extract year
            year_match = re.search(r'(\d{4})', date)
            if year_match:
                year = year_match.group(1)
                patterns['by_year'][year] += 1
        
        comm_type = comm.get('type', 'unknown')
        patterns['by_type'][comm_type] += 1
        
        # Extract recipient from To field or content
        to_field = str(comm.get('to', ''))
        content = str(comm.get('content', ''))
        
        # Look for email addresses or names
        email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
        emails = re.findall(email_pattern, to_field + ' ' + content[:500])
        for email in emails[:3]:  # First 3 emails
            if 'satoshi' not in email.lower():
                patterns['by_recipient'][email] += 1
        
        # Extract topics from subject/content
        subject = str(comm.get('subject', '')).lower()
        if 'bitcoin' in subject:
            patterns['topics']['bitcoin'] += 1
        if 'release' in subject or 'version' in subject:
            patterns['topics']['releases'] += 1
        if 'bug' in subject or 'fix' in subject:
            patterns['topics']['bugs'] += 1
        if 'question' in subject or 'help' in subject:
            patterns['topics']['support'] += 1
    
    return patterns


def identify_key_governance_moments(insights: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Identify key governance moments from insights."""
    key_moments = []
    
    # Look for significant authority statements
    for stmt in insights['authority_statements']:
        if any(keyword in stmt['excerpt'].lower() for keyword in ['control', 'maintain', 'responsible', 'decision']):
            key_moments.append({
                'type': 'authority',
                'date': stmt['date'],
                'subject': stmt['subject'],
                'excerpt': stmt['excerpt'],
                'significance': 'Authority/control statement'
            })
    
    # Look for protocol change discussions
    for disc in insights['protocol_discussions']:
        if any(keyword in disc['excerpt'].lower() for keyword in ['fork', 'upgrade', 'change', 'compatibility']):
            key_moments.append({
                'type': 'protocol',
                'date': disc['date'],
                'subject': disc['subject'],
                'excerpt': disc['excerpt'][:300],
                'significance': 'Protocol change discussion'
            })
    
    # Sort by date (handle None values)
    key_moments.sort(key=lambda x: x.get('date') or '')
    
    return key_moments


def generate_report(insights: Dict[str, Any], patterns: Dict[str, Any], key_moments: List[Dict[str, Any]]) -> str:
    """Generate a markdown report of governance insights."""
    report = []
    report.append("# Satoshi Nakamoto Governance Analysis")
    report.append("")
    report.append(f"**Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"**Total Communications Analyzed:** {insights['total_communications']}")
    report.append("")
    
    # Summary
    report.append("## Executive Summary")
    report.append("")
    report.append(f"- **Governance Mentions:** {len(insights['governance_mentions'])} communications")
    report.append(f"- **Decision Statements:** {len(insights['decision_statements'])} instances")
    report.append(f"- **Authority Statements:** {len(insights['authority_statements'])} instances")
    report.append(f"- **Community Interactions:** {len(insights['community_interactions'])} communications")
    report.append(f"- **Protocol Discussions:** {len(insights['protocol_discussions'])} communications")
    report.append(f"- **Key Governance Moments:** {len(key_moments)} identified")
    report.append("")
    
    # Communication Patterns
    report.append("## Communication Patterns")
    report.append("")
    report.append("### By Year")
    for year, count in sorted(patterns['by_year'].items()):
        report.append(f"- **{year}:** {count} communications")
    report.append("")
    
    report.append("### By Type")
    for comm_type, count in patterns['by_type'].most_common():
        report.append(f"- **{comm_type}:** {count}")
    report.append("")
    
    report.append("### Top Recipients")
    for recipient, count in patterns['by_recipient'].most_common(10):
        report.append(f"- **{recipient}:** {count} communications")
    report.append("")
    
    # Key Governance Moments
    report.append("## Key Governance Moments")
    report.append("")
    for i, moment in enumerate(key_moments[:20], 1):  # Top 20
        report.append(f"### {i}. {moment.get('subject', 'No Subject')}")
        report.append("")
        report.append(f"- **Date:** {moment.get('date', 'Unknown')}")
        report.append(f"- **Type:** {moment.get('type', 'unknown')}")
        report.append(f"- **Significance:** {moment.get('significance', 'N/A')}")
        report.append("")
        report.append(f"**Excerpt:**")
        report.append("```")
        report.append(moment.get('excerpt', '')[:500])
        report.append("```")
        report.append("")
    
    # Authority Statements
    report.append("## Authority and Control Statements")
    report.append("")
    for i, stmt in enumerate(insights['authority_statements'][:15], 1):
        report.append(f"### {i}. {stmt.get('subject', 'No Subject')}")
        report.append("")
        report.append(f"- **Date:** {stmt.get('date', 'Unknown')}")
        report.append(f"- **Pattern:** `{stmt.get('pattern', 'N/A')}`")
        report.append("")
        report.append("**Excerpt:**")
        report.append("```")
        report.append(stmt.get('excerpt', '')[:400])
        report.append("```")
        report.append("")
    
    # Decision Statements
    report.append("## Decision-Making Statements")
    report.append("")
    for i, stmt in enumerate(insights['decision_statements'][:15], 1):
        report.append(f"### {i}. {stmt.get('subject', 'No Subject')}")
        report.append("")
        report.append(f"- **Date:** {stmt.get('date', 'Unknown')}")
        report.append("")
        report.append("**Excerpt:**")
        report.append("```")
        report.append(stmt.get('excerpt', '')[:400])
        report.append("```")
        report.append("")
    
    # Protocol Discussions
    report.append("## Protocol and Technical Discussions")
    report.append("")
    for i, disc in enumerate(insights['protocol_discussions'][:15], 1):
        report.append(f"### {i}. {disc.get('subject', 'No Subject')}")
        report.append("")
        report.append(f"- **Date:** {disc.get('date', 'Unknown')}")
        report.append("")
        report.append("**Excerpt:**")
        report.append("```")
        report.append(disc.get('excerpt', '')[:400])
        report.append("```")
        report.append("")
    
    # Governance Keywords Analysis
    report.append("## Governance Keywords Frequency")
    report.append("")
    keyword_counts = Counter()
    for mention in insights['governance_mentions']:
        for keyword in mention.get('keywords', []):
            keyword_counts[keyword] += 1
    
    for keyword, count in keyword_counts.most_common(20):
        report.append(f"- **{keyword}:** {count} mentions")
    report.append("")
    
    return "\n".join(report)


def main():
    """Main analysis function."""
    data_dir = project_root / "data" / "satoshi_archive"
    data_file = data_dir / "satoshi_communications.jsonl"
    output_dir = project_root / "findings"
    
    logger.info("Starting Satoshi governance analysis")
    
    # Load communications
    comms = load_communications(data_file)
    if not comms:
        logger.error("No communications loaded. Exiting.")
        return
    
    # Filter for Satoshi communications
    satoshi_comms = filter_satoshi_communications(comms)
    if not satoshi_comms:
        logger.warning("No Satoshi communications found. Analyzing all communications.")
        satoshi_comms = comms
    
    # Extract insights
    logger.info("Extracting governance insights...")
    insights = extract_governance_insights(satoshi_comms)
    
    # Analyze patterns
    logger.info("Analyzing communication patterns...")
    patterns = analyze_communication_patterns(satoshi_comms)
    
    # Identify key moments
    logger.info("Identifying key governance moments...")
    key_moments = identify_key_governance_moments(insights)
    
    # Generate report
    logger.info("Generating report...")
    report = generate_report(insights, patterns, key_moments)
    
    # Save report
    output_file = output_dir / "SATOSHI_GOVERNANCE_ANALYSIS.md"
    output_file.write_text(report, encoding='utf-8')
    logger.info(f"Report saved to: {output_file}")
    
    # Save structured data
    structured_data = {
        'insights': insights,
        'patterns': {k: dict(v) if isinstance(v, Counter) else v for k, v in patterns.items()},
        'key_moments': key_moments,
        'analysis_date': datetime.now().isoformat(),
        'total_communications': len(satoshi_comms)
    }
    
    data_output = data_dir / "governance_analysis.json"
    with open(data_output, 'w', encoding='utf-8') as f:
        json.dump(structured_data, f, indent=2, default=str)
    logger.info(f"Structured data saved to: {data_output}")
    
    # Print summary
    print("\n" + "="*60)
    print("SATOSHI GOVERNANCE ANALYSIS COMPLETE")
    print("="*60)
    print(f"\n✅ Analyzed {len(satoshi_comms)} communications")
    print(f"✅ Found {len(insights['governance_mentions'])} governance mentions")
    print(f"✅ Identified {len(key_moments)} key governance moments")
    print(f"✅ Generated report: {output_file}")
    print(f"✅ Saved structured data: {data_output}")
    print()


if __name__ == "__main__":
    main()
