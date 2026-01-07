#!/usr/bin/env python3
"""
Narrative Analysis - Track how different narratives developed over time.

Analyzes:
1. Narrative themes over time (decentralization, governance, consensus, etc.)
2. Narrative shifts (how language changes)
3. Competing narratives (different perspectives)
4. Narrative dominance (which narratives win)
5. Narrative evolution by epoch (Early Development, Blocksize Wars, Post-SegWit, Recent)
"""

import sys
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict, Counter
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir, get_analysis_dir
# Define epochs inline
def get_governance_epochs():
    """Get governance epochs."""
    return {
        "early_development": {
            "start_year": 2009,
            "end_year": 2013,
            "description": "Early development phase"
        },
        "blocksize_wars": {
            "start_year": 2014,
            "end_year": 2017,
            "description": "Blocksize wars era"
        },
        "post_segwit": {
            "start_year": 2018,
            "end_year": 2020,
            "description": "Post-SegWit consolidation"
        },
        "recent_era": {
            "start_year": 2021,
            "end_year": 2024,
            "description": "Recent era"
        }
    }
from src.schemas.analysis_results import create_result_template

logger = setup_logger()


class NarrativeAnalyzer:
    """Analyzer for narrative development over time."""
    
    def __init__(self):
        """Initialize analyzer."""
        self.data_dir = get_data_dir()
        self.processed_dir = self.data_dir / 'processed'
        self.analysis_dir = get_analysis_dir() / 'narrative_analysis'
        self.analysis_dir.mkdir(parents=True, exist_ok=True)
        
        # Define narrative themes and keywords
        self.narrative_themes = {
            "decentralization": {
                "keywords": ["decentralize", "decentralized", "decentralization", "distributed", "distribute", "distributed system"],
                "description": "Discussions about decentralization, distributed systems, avoiding centralization"
            },
            "governance": {
                "keywords": ["governance", "govern", "governing", "decision", "decide", "process", "procedure", "protocol"],
                "description": "Discussions about governance, decision-making processes, procedures"
            },
            "consensus": {
                "keywords": ["consensus", "agree", "agreement", "unanimous", "unanimity", "consensus mechanism"],
                "description": "Discussions about consensus, agreement, unanimous decisions"
            },
            "transparency": {
                "keywords": ["transparent", "transparency", "open", "public", "visible", "audit", "auditable"],
                "description": "Discussions about transparency, openness, public visibility"
            },
            "maintainer_authority": {
                "keywords": ["maintainer", "maintainers", "merge", "merging", "authority", "merge authority", "write access"],
                "description": "Discussions about maintainer authority, merge rights, write access"
            },
            "fork_threat": {
                "keywords": ["fork", "forking", "split", "hardfork", "hard fork", "soft fork", "chain split"],
                "description": "Discussions about forks, chain splits, hard forks, soft forks"
            },
            "blocksize_debate": {
                "keywords": ["blocksize", "block size", "blocksize", "segwit", "segwit", "bip141", "scaling"],
                "description": "Discussions about blocksize, SegWit, scaling solutions"
            },
            "external_pressure": {
                "keywords": ["regulatory", "regulation", "sec", "cftc", "government", "corporate", "pressure", "coercion", "threat"],
                "description": "Discussions about external pressure, regulation, government, corporate influence"
            },
            "security": {
                "keywords": ["security", "secure", "vulnerability", "exploit", "attack", "secure", "safety"],
                "description": "Discussions about security, vulnerabilities, attacks, safety"
            },
            "scaling": {
                "keywords": ["scale", "scaling", "throughput", "capacity", "transaction", "tps", "throughput"],
                "description": "Discussions about scaling, throughput, transaction capacity"
            },
            "trust": {
                "keywords": ["trust", "trusted", "trustless", "trust model", "don't trust verify", "verify"],
                "description": "Discussions about trust, trustless systems, verification"
            },
            "censorship": {
                "keywords": ["censor", "censorship", "censored", "filter", "block", "ban"],
                "description": "Discussions about censorship, filtering, blocking"
            },
            "inclusivity": {
                "keywords": ["inclusive", "inclusivity", "diversity", "welcome", "open to", "participation"],
                "description": "Discussions about inclusivity, diversity, welcoming participation"
            },
            "technical_excellence": {
                "keywords": ["quality", "excellence", "best practice", "code quality", "technical", "engineering"],
                "description": "Discussions about technical excellence, code quality, engineering standards"
            },
            "social_coordination": {
                "keywords": ["social", "coordination", "coordinate", "social layer", "social consensus"],
                "description": "Discussions about social coordination, social layer, social consensus"
            }
        }
    
    def run_analysis(self):
        """Run narrative analysis."""
        logger.info("=" * 60)
        logger.info("Narrative Analysis")
        logger.info("=" * 60)
        
        # Load data
        emails = self._load_emails()
        prs = self._load_prs()
        irc = self._load_irc()
        
        # Analyze narratives by year
        narratives_by_year = self._analyze_narratives_by_year(emails, prs, irc)
        
        # Analyze narratives by epoch
        narratives_by_epoch = self._analyze_narratives_by_epoch(emails, prs, irc)
        
        # Analyze narrative evolution
        narrative_evolution = self._analyze_narrative_evolution(narratives_by_year)
        
        # Analyze competing narratives
        competing_narratives = self._analyze_competing_narratives(emails, prs)
        
        # Analyze narrative dominance
        narrative_dominance = self._analyze_narrative_dominance(narratives_by_year)
        
        # Save results
        self._save_results({
            'narratives_by_year': narratives_by_year,
            'narratives_by_epoch': narratives_by_epoch,
            'narrative_evolution': narrative_evolution,
            'competing_narratives': competing_narratives,
            'narrative_dominance': narrative_dominance,
            'themes': self.narrative_themes
        })
        
        logger.info("Narrative analysis complete")
    
    def _load_emails(self) -> List[Dict[str, Any]]:
        """Load email data."""
        emails_file = self.processed_dir / 'cleaned_emails.jsonl'
        if not emails_file.exists():
            emails_file = self.data_dir / 'mailing_lists' / 'emails.jsonl'
        
        if not emails_file.exists():
            return []
        
        emails = []
        with open(emails_file, 'r') as f:
            for line in f:
                try:
                    emails.append(json.loads(line))
                except:
                    continue
        return emails
    
    def _load_prs(self) -> List[Dict[str, Any]]:
        """Load PR data."""
        prs_file = self.processed_dir / 'enriched_prs.jsonl'
        if not prs_file.exists():
            prs_file = self.processed_dir / 'cleaned_prs.jsonl'
        
        if not prs_file.exists():
            return []
        
        prs = []
        with open(prs_file, 'r') as f:
            for line in f:
                try:
                    prs.append(json.loads(line))
                except:
                    continue
        return prs
    
    def _load_irc(self) -> List[Dict[str, Any]]:
        """Load IRC data."""
        irc_file = self.processed_dir / 'cleaned_irc.jsonl'
        if not irc_file.exists():
            irc_file = self.data_dir / 'irc' / 'messages.jsonl'
        
        if not irc_file.exists():
            return []
        
        irc = []
        with open(irc_file, 'r') as f:
            for line in f:
                try:
                    irc.append(json.loads(line))
                except:
                    continue
        return irc
    
    def _extract_year(self, date_str: str) -> Optional[int]:
        """Extract year from date string."""
        if not date_str:
            return None
        
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.year
        except:
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                return dt.year
            except:
                return None
    
    def _detect_narratives(self, text: str) -> Dict[str, int]:
        """Detect narrative themes in text."""
        text_lower = text.lower()
        narratives = {}
        
        for theme, config in self.narrative_themes.items():
            count = 0
            for keyword in config["keywords"]:
                # Use word boundaries for better matching
                pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                count += len(re.findall(pattern, text_lower))
            narratives[theme] = count
        
        return narratives
    
    def _analyze_narratives_by_year(self, emails: List[Dict], prs: List[Dict], irc: List[Dict]) -> Dict[str, Any]:
        """Analyze narratives by year."""
        logger.info("Analyzing narratives by year...")
        logger.info(f"Processing {len(emails)} emails, {len(prs)} PRs, {len(irc)} IRC messages")
        
        narratives_by_year = defaultdict(lambda: {
            "total_items": 0,
            "themes": defaultdict(int),
            "platforms": {
                "emails": 0,
                "prs": 0,
                "irc": 0
            }
        })
        
        # Analyze emails in chunks
        logger.info("Processing emails...")
        chunk_size = 1000
        for i in range(0, len(emails), chunk_size):
            chunk = emails[i:i+chunk_size]
            logger.info(f"Processing email chunk {i//chunk_size + 1}/{(len(emails)-1)//chunk_size + 1}")
            for email in chunk:
                year = self._extract_year(email.get('date', ''))
            if not year:
                continue
            
            narratives_by_year[year]["total_items"] += 1
            narratives_by_year[year]["platforms"]["emails"] += 1
            
            content = (email.get('subject', '') + ' ' + email.get('body', ''))
            narratives = self._detect_narratives(content)
            
            for theme, count in narratives.items():
                if count > 0:
                    narratives_by_year[year]["themes"][theme] += count
        
        # Analyze PRs
        for pr in prs:
                year = self._extract_year(pr.get('created_at', ''))
                if not year:
                    continue
                
                narratives_by_year[year]["total_items"] += 1
                narratives_by_year[year]["platforms"]["prs"] += 1
                
                title = pr.get('title', '') or ''
                body = pr.get('body', '') or ''
                comments = ' '.join([c.get('body', '') or '' for c in pr.get('comments', [])])
                content = f"{title} {body} {comments}"
                narratives = self._detect_narratives(content)
                
                for theme, count in narratives.items():
                    if count > 0:
                        narratives_by_year[year]["themes"][theme] += count
        
        # Analyze IRC
        for msg in irc:
                year = self._extract_year(msg.get('timestamp', ''))
                if not year:
                    continue
                
                narratives_by_year[year]["total_items"] += 1
                narratives_by_year[year]["platforms"]["irc"] += 1
                
                content = msg.get('message', '')
                narratives = self._detect_narratives(content)
                
                for theme, count in narratives.items():
                    if count > 0:
                        narratives_by_year[year]["themes"][theme] += count
        
        # Convert to regular dict and calculate percentages
        result = {}
        for year in sorted(narratives_by_year.keys()):
            data = narratives_by_year[year]
            total_mentions = sum(data["themes"].values())
            
            result[str(year)] = {
                "year": year,
                "total_items": data["total_items"],
                "platforms": data["platforms"],
                "themes": dict(data["themes"]),
                "total_theme_mentions": total_mentions,
                "theme_percentages": {
                    theme: (count / total_mentions * 100) if total_mentions > 0 else 0
                    for theme, count in data["themes"].items()
                }
            }
        
        return result
    
    def _analyze_narratives_by_epoch(self, emails: List[Dict], prs: List[Dict], irc: List[Dict]) -> Dict[str, Any]:
        """Analyze narratives by governance epoch."""
        logger.info("Analyzing narratives by epoch...")
        
        epochs = get_governance_epochs()
        narratives_by_epoch = defaultdict(lambda: {
            "total_items": 0,
            "themes": defaultdict(int),
            "platforms": {
                "emails": 0,
                "prs": 0,
                "irc": 0
            }
        })
        
        def get_epoch(year: int) -> Optional[str]:
            for epoch_name, epoch_data in epochs.items():
                if epoch_data["start_year"] <= year <= epoch_data["end_year"]:
                    return epoch_name
            return None
        
        # Analyze emails in chunks
        logger.info("Processing emails for epoch analysis...")
        chunk_size = 1000
        for i in range(0, len(emails), chunk_size):
            chunk = emails[i:i+chunk_size]
            if i % (chunk_size * 10) == 0:
                logger.info(f"Processing email chunk {i//chunk_size + 1}/{(len(emails)-1)//chunk_size + 1}")
            for email in chunk:
                year = self._extract_year(email.get('date', ''))
            if not year:
                continue
            
            epoch = get_epoch(year)
            if not epoch:
                continue
            
            narratives_by_epoch[epoch]["total_items"] += 1
            narratives_by_epoch[epoch]["platforms"]["emails"] += 1
            
            content = (email.get('subject', '') + ' ' + email.get('body', ''))
            narratives = self._detect_narratives(content)
            
            for theme, count in narratives.items():
                if count > 0:
                    narratives_by_epoch[epoch]["themes"][theme] += count
        
        # Analyze PRs
        for pr in prs:
            year = self._extract_year(pr.get('created_at', ''))
            if not year:
                continue
            
            epoch = get_epoch(year)
            if not epoch:
                continue
            
            narratives_by_epoch[epoch]["total_items"] += 1
            narratives_by_epoch[epoch]["platforms"]["prs"] += 1
            
            title = pr.get('title', '') or ''
            body = pr.get('body', '') or ''
            comments = ' '.join([c.get('body', '') or '' for c in pr.get('comments', [])])
            content = f"{title} {body} {comments}"
            narratives = self._detect_narratives(content)
            
            for theme, count in narratives.items():
                if count > 0:
                    narratives_by_epoch[epoch]["themes"][theme] += count
        
        # Analyze IRC
        for msg in irc:
                year = self._extract_year(msg.get('timestamp', ''))
                if not year:
                    continue
                
                epoch = get_epoch(year)
                if not epoch:
                    continue
                
                narratives_by_epoch[epoch]["total_items"] += 1
                narratives_by_epoch[epoch]["platforms"]["irc"] += 1
                
                content = msg.get('message', '')
                narratives = self._detect_narratives(content)
                
                for theme, count in narratives.items():
                    if count > 0:
                        narratives_by_epoch[epoch]["themes"][theme] += count
        
        # Convert to regular dict
        result = {}
        for epoch in narratives_by_epoch.keys():
            data = narratives_by_epoch[epoch]
            total_mentions = sum(data["themes"].values())
            
            result[epoch] = {
                "epoch": epoch,
                "total_items": data["total_items"],
                "platforms": data["platforms"],
                "themes": dict(data["themes"]),
                "total_theme_mentions": total_mentions,
                "theme_percentages": {
                    theme: (count / total_mentions * 100) if total_mentions > 0 else 0
                    for theme, count in data["themes"].items()
                }
            }
        
        return result
    
    def _analyze_narrative_evolution(self, narratives_by_year: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze how narratives evolved over time."""
        logger.info("Analyzing narrative evolution...")
        
        # Track theme trends
        theme_trends = defaultdict(list)
        
        for year_str in sorted(narratives_by_year.keys()):
            year_data = narratives_by_year[year_str]
            for theme, percentage in year_data["theme_percentages"].items():
                theme_trends[theme].append({
                    "year": year_data["year"],
                    "percentage": percentage,
                    "mentions": year_data["themes"].get(theme, 0)
                })
        
        # Calculate trends (increasing, decreasing, stable)
        evolution = {}
        for theme, trend_data in theme_trends.items():
            if len(trend_data) < 2:
                continue
            
            first = trend_data[0]["percentage"]
            last = trend_data[-1]["percentage"]
            change = last - first
            
            # Calculate average
            avg = sum(d["percentage"] for d in trend_data) / len(trend_data)
            
            # Determine trend direction
            if change > 5:
                direction = "increasing"
            elif change < -5:
                direction = "decreasing"
            else:
                direction = "stable"
            
            evolution[theme] = {
                "first_year": trend_data[0]["year"],
                "last_year": trend_data[-1]["year"],
                "first_percentage": first,
                "last_percentage": last,
                "change": change,
                "average_percentage": avg,
                "direction": direction,
                "trend_data": trend_data
            }
        
        return evolution
    
    def _analyze_competing_narratives(self, emails: List[Dict], prs: List[Dict]) -> Dict[str, Any]:
        """Analyze competing narratives (different perspectives on same topics)."""
        logger.info("Analyzing competing narratives...")
        
        # This is a simplified version - could be expanded with sentiment analysis
        competing = {
            "decentralization_vs_centralization": {
                "description": "Tension between decentralization and centralization narratives",
                "examples": []
            },
            "governance_formal_vs_informal": {
                "description": "Tension between formal and informal governance",
                "examples": []
            },
            "consensus_vs_authority": {
                "description": "Tension between consensus and authority-based decisions",
                "examples": []
            }
        }
        
        # Could add more sophisticated analysis here
        # For now, return structure
        
        return competing
    
    def _analyze_narrative_dominance(self, narratives_by_year: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze which narratives dominate over time."""
        logger.info("Analyzing narrative dominance...")
        
        dominance = {}
        
        for year_str in sorted(narratives_by_year.keys()):
            year_data = narratives_by_year[year_str]
            
            # Get top themes
            themes_sorted = sorted(
                year_data["theme_percentages"].items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            top_5 = themes_sorted[:5]
            
            dominance[year_str] = {
                "year": year_data["year"],
                "top_5_themes": [
                    {"theme": theme, "percentage": pct}
                    for theme, pct in top_5
                ],
                "dominant_theme": top_5[0][0] if top_5 else None,
                "dominant_percentage": top_5[0][1] if top_5 else 0
            }
        
        return dominance
    
    def _save_results(self, results: Dict[str, Any]):
        """Save analysis results."""
        output_file = self.analysis_dir / 'narrative_analysis.json'
        
        # Create result template
        result_template = create_result_template(
            analysis_name="narrative_analysis"
        )
        
        # Add metadata
        result_template["metadata"]["data_sources"] = ["emails", "prs", "irc"]
        result_template["metadata"]["themes_analyzed"] = len(self.narrative_themes)
        result_template["metadata"]["years_analyzed"] = len(results.get('narratives_by_year', {}))
        result_template["metadata"]["epochs_analyzed"] = len(results.get('narratives_by_epoch', {}))
        
        result_template["data"] = results
        
        with open(output_file, 'w') as f:
            json.dump(result_template, f, indent=2)
        
        logger.info(f"Saved narrative analysis to {output_file}")


if __name__ == "__main__":
    analyzer = NarrativeAnalyzer()
    analyzer.run_analysis()

