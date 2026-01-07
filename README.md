# Bitcoin Governance Communications Analysis

**Project**: Quantitative Analysis of Bitcoin Development Governance Through Public Communications  
**Purpose**: Empirical evidence supporting Bitcoin Commons governance framework  
**Timeline**: 2 weeks focused execution  
**Output**: Executive summary, findings report, visualizations, Twitter-ready content

## Project Overview

### Objective

Analyze 15+ years of Bitcoin's public development communications to quantitatively demonstrate:

1. Power concentration in informal governance structures
2. Gap between "transparent process" claims and actual decision-making
3. Undefined criteria for merge/rejection decisions
4. Specific case study: Luke Dashjr maintainer removal as proof of informal governance

### Core Thesis to Validate

Bitcoin's governance claims "everything happens in public" but analysis will show:

- Discussions are public, but decision-making criteria are opaque
- Power is concentrated in 5-7 individuals despite decentralization claims
- "Rough consensus" is undefined and selectively applied
- Major governance actions (like maintainer removal) lack documented procedures

## Project Structure

```
commons-research/
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── config.yaml                        # Configuration file
├── .env.example                       # Environment variables template
├── data/                              # Raw and processed data
│   ├── github/                       # GitHub PR/issue data
│   ├── mailing_lists/                # Mailing list archives
│   ├── irc/                          # IRC chat logs
│   ├── luke_case/                    # Luke Dashjr case data
│   └── processed/                    # Cleaned/processed datasets
├── scripts/                           # Executable scripts
│   ├── data_collection/              # Data collection scripts
│   ├── data_processing/              # Data cleaning/normalization
│   ├── analysis/                     # Analysis scripts
│   ├── visualization/                 # Chart generation
│   └── reporting/                     # Report generation
├── analysis/                          # Analysis outputs
│   ├── maintainer_premium/
│   ├── nack_effectiveness/
│   ├── decision_criteria/
│   ├── power_concentration/
│   ├── language_patterns/
│   └── luke_case_study/
├── findings/                          # Findings documents
├── visualizations/                    # Generated charts
├── twitter_content/                   # Twitter thread drafts
└── appendices/                        # Supporting materials
```

## Quick Start

### Setup

```bash
# Run automated setup
./setup.sh
source venv/bin/activate

# Copy environment template (if not done by setup.sh)
cp .env.example .env
# Edit .env and add your GitHub token (see GITHUB_TOKEN_SETUP.md for details)
```

### GitHub Token Setup

**Recommended**: Add a GitHub token for faster data collection (5,000 requests/hour vs 60/hour)

```bash
# Quick check if token is set
python scripts/check_token.py

# If not set, edit .env file:
nano .env
# Replace 'your_github_token_here' with your actual token

# Get token from: https://github.com/settings/tokens
# No special permissions needed - just create a token with no scopes
```

See [GITHUB_TOKEN_SETUP.md](GITHUB_TOKEN_SETUP.md) for detailed instructions.

### Validation & Incremental Testing

**Recommended approach**: Validate and expand incrementally

```bash
# Step 1: Validate setup
python scripts/validate_setup.py

# Step 2: Test minimal collection (3 PRs)
python scripts/test_minimal_collection.py

# Step 3: Interactive workflow (recommended)
python scripts/workflow.py

# Or manually test small batches:
python scripts/data_collection/github_collector.py --limit 10 --prs-only
python scripts/data_collection/github_collector.py --limit 100 --prs-only
```

See [VALIDATION_PLAN.md](VALIDATION_PLAN.md) for detailed validation steps.

### Running Analysis

```bash
# Phase 1: Data Collection
python scripts/data_collection/github_collector.py
python scripts/data_collection/mailing_list_collector.py
python scripts/data_collection/irc_collector.py
python scripts/data_collection/luke_case_collector.py

# Phase 2: Data Processing
python scripts/data_processing/clean_data.py
python scripts/data_processing/enrich_data.py
python scripts/data_processing/user_identity_resolver.py  # Cross-reference identities

# Phase 3: Analysis
python scripts/analysis/maintainer_premium.py
python scripts/analysis/nack_effectiveness.py
python scripts/analysis/decision_criteria.py
python scripts/analysis/power_concentration.py
python scripts/analysis/language_patterns.py
python scripts/analysis/luke_case_study.py
python scripts/analysis/developer_history.py  # Generate per-developer histories

# Phase 4: Reporting
python scripts/reporting/generate_executive_summary.py
python scripts/reporting/generate_full_report.py
python scripts/visualization/generate_all_charts.py
```

## Methodology

See [METHODOLOGY.md](METHODOLOGY.md) for detailed methodology documentation.

## Data Sources

We collect data from **three major public communication channels**:

1. **GitHub** (`bitcoin/bitcoin` repository)
   - ~23,455 Pull Requests with all comments and reviews
   - ~5,000 Issues with discussions
   - ~500,000+ comments and reviews
   - **Total**: ~528,000 data points

2. **Mailing Lists** (bitcoin-dev, bitcoin-core-dev)
   - ~70,000 emails from 2008-present
   - Full thread structure and discussions
   - **Total**: ~70,000 data points

3. **IRC Channels** (#bitcoin-core-dev, #bitcoin-dev, #bitcoin-core)
   - ~500,000+ messages from development channels
   - Real-time coordination and discussions
   - **Total**: ~500,000 data points

**Combined**: **~1.1 million data points** over **16+ years** of Bitcoin development history.

See [DATA_SOURCES_SUMMARY.md](DATA_SOURCES_SUMMARY.md) for detailed breakdown.

## Deliverables

1. **Executive Summary** (3-5 pages, quotable findings)
2. **Full Analysis Report** (15-20 pages with methodology, findings, conclusions)
3. **Data Visualizations** (influence networks, power concentration charts, timeline analyses)
4. **Twitter Content** (3-4 threads with key findings)
5. **Developer Histories** (per-developer comprehensive activity profiles)
6. **Raw Data Archive** (for reference, not publication)

## Timeline

- **Days 1-3**: Data Collection
- **Days 4-8**: Analysis Implementation
- **Days 9-10**: Synthesis & Reporting
- **Days 11-12**: Quality Assurance & Packaging

## License

MIT License - see LICENSE file for details.

