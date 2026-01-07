#!/usr/bin/env python3
"""Preference Falsification Analysis - Compare GitHub vs IRC discussions"""
import sys, json
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
from src.utils.logger import setup_logger
from src.utils.paths import get_analysis_dir, get_data_dir
logger = setup_logger()

class PreferenceFalsificationAnalyzer:
    def __init__(self):
        self.data_dir = get_data_dir()
        self.analysis_dir = get_analysis_dir()
        self.processed_dir = self.data_dir / 'processed'
        self.output_dir = self.analysis_dir / 'preference_falsification'
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def run_analysis(self):
        logger.info("Preference Falsification Analysis")
        prs = self._load_prs()
        irc = self._load_irc()
        
        github_sentiment = self._analyze_github_sentiment(prs)
        irc_sentiment = self._analyze_irc_sentiment(irc)
        
        results = {
            'analysis_name': 'preference_falsification',
            'version': '1.0',
            'data': {
                'github_sentiment': github_sentiment,
                'irc_sentiment': irc_sentiment,
                'comparison': self._compare_channels(github_sentiment, irc_sentiment)
            }
        }
        
        output_file = self.output_dir / 'preference_falsification.json'
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to {output_file}")
    
    def _load_prs(self):
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
    
    def _load_irc(self):
        irc_file = self.processed_dir / 'cleaned_irc.jsonl'
        if not irc_file.exists():
            return []
        messages = []
        with open(irc_file, 'r') as f:
            for line in f:
                try:
                    messages.append(json.loads(line))
                except:
                    continue
        return messages
    
    def _analyze_github_sentiment(self, prs):
        governance_keywords = ['governance', 'maintainer', 'process', 'decision', 'authority']
        mentions = 0
        for pr in prs:
            text = f"{pr.get('title', '')} {pr.get('body', '')}".lower()
            if any(kw in text for kw in governance_keywords):
                mentions += 1
        return {'governance_mentions': mentions, 'total_prs': len(prs)}
    
    def _analyze_irc_sentiment(self, irc):
        governance_keywords = ['governance', 'maintainer', 'process', 'decision', 'authority']
        mentions = 0
        for msg in irc:
            text = msg.get('message', '').lower()
            if any(kw in text for kw in governance_keywords):
                mentions += 1
        return {'governance_mentions': mentions, 'total_messages': len(irc)}
    
    def _compare_channels(self, github, irc):
        github_rate = github['governance_mentions'] / github['total_prs'] if github['total_prs'] > 0 else 0
        irc_rate = irc['governance_mentions'] / irc['total_messages'] if irc['total_messages'] > 0 else 0
        return {
            'github_governance_rate': github_rate,
            'irc_governance_rate': irc_rate,
            'ratio': irc_rate / github_rate if github_rate > 0 else None
        }

if __name__ == '__main__':
    analyzer = PreferenceFalsificationAnalyzer()
    analyzer.run_analysis()
