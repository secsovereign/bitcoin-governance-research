# Bitcoin Core Governance Research

**Project**: Comprehensive Quantitative Analysis of Bitcoin Core Development Governance  
**Purpose**: Empirical analysis of Bitcoin Core governance patterns through public data  
**Data Coverage**: 2010-2026 (15 years of development history)

## Project Overview

### Objective

Analyze 15+ years of Bitcoin Core's public development data to quantitatively examine:

1. Power concentration in governance structures
2. Review and merge decision patterns
3. Self-merge authority and usage
4. Temporal evolution of governance practices

## Project Structure

```
bitcoin-governance-research/
├── README.md                          # This file
├── pyproject.toml                     # Python project configuration
├── setup.sh                           # Setup script
├── comprehensive_recent_analysis.py   # Legacy analysis script
├── scripts/                           # Executable scripts
│   └── run_all_analyses.py            # Main analysis pipeline (runs 9 core scripts)
├── data/                              # Data files
│   ├── github/                       # GitHub PR/issue data
│   ├── mailing_lists/                # Mailing list archives
│   ├── irc/                          # IRC chat logs
│   └── processed/                    # Processed datasets
├── scripts/                           # Executable scripts
│   ├── data_collection/              # Data collection scripts
│   ├── data_processing/              # Data processing scripts
│   ├── analysis/                     # Analysis scripts
│   ├── reporting/                    # Report generation
│   └── validation/                   # Validation scripts
├── findings/                          # Research findings and reports
│   └── data/                         # Analysis result JSON files
├── src/                               # Source utilities
└── tests/                             # Test files
```

## Quick Start

### Setup

```bash
# Run automated setup
./setup.sh
source venv/bin/activate

# See GITHUB_TOKEN_SETUP.md for GitHub token configuration (optional but recommended)
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

### Validation & Testing

```bash
# Validate setup
python scripts/validate_setup.py

# Test minimal collection
python scripts/test_minimal_collection.py

# Interactive workflow
python scripts/workflow.py
```

### Running Analysis

The main analysis pipeline runs all 9 core analysis scripts:

```bash
python scripts/run_all_analyses.py
```

This runs:
- Contributor Analysis
- BCAP State of Mind & Power Shift Analysis
- BIP Process Analysis
- Cross-Platform Networks & Cross-Repository Comparison
- Informal Sentiment Analysis (IRC/Email)
- Release Signing Analysis
- Enhanced Identity Resolution

Individual analysis scripts are available in `scripts/analysis/` for specific analyses.

**Note**: `comprehensive_recent_analysis.py` is a legacy script for historical analysis. Use `scripts/run_all_analyses.py` for current analyses.

## Methodology

See [findings/RESEARCH_METHODOLOGY.md](findings/RESEARCH_METHODOLOGY.md) for detailed methodology documentation.

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

**Combined**: **~1.1 million data points** over **15 years** of Bitcoin development history (2010-2026).

See [DATA_SOURCING_AND_REPRODUCIBILITY.md](DATA_SOURCING_AND_REPRODUCIBILITY.md) for detailed data sourcing and reproducibility information.

## Getting Started

**Start here**: See [`findings/README.md`](findings/README.md) for complete navigation guide to all research findings and reports.

**Quick overview**: See [`findings/EXECUTIVE_SUMMARY.md`](findings/EXECUTIVE_SUMMARY.md) for comprehensive findings, including:

- **Power Concentration**: Top 3 maintainers control 81.1% of merges
- **Self-Merge Patterns**: 26.5% self-merge rate with significant variation
- **Review Quality**: Zero-review merges reduced from 30.2% (historical) to 3.4% (recent)
- **Temporal Evolution**: Process improvements while structural concentration persists

## Deliverables

1. **Executive Summary** - High-level findings and key metrics
2. **Research Methodology** - Complete methodology documentation
3. **Detailed Analysis Reports** - Comprehensive analysis across multiple dimensions
4. **Data Files** - Analysis results and processed data
5. **Reproducibility** - All scripts and data sources documented

## Related Research and Frameworks

### BCAP (Bitcoin Consensus Analysis Project)

Some of our research applies theoretical frameworks from **BCAP (Bitcoin Consensus Analysis Project)**, particularly:

- **State of Mind (SOM) Framework**: Analyzing developer engagement levels during consensus changes
- **Power Shift Concepts**: Understanding how governance changes during consensus change periods

**BCAP Repository**: https://github.com/bitcoin-cap/bcap  
**BCAP Website**: https://bitcoin-cap.github.io/bcap/  
**BCAP Integration Report**: See [`findings/BCAP_INTEGRATION_REPORT.md`](findings/BCAP_INTEGRATION_REPORT.md)

Our analysis applies BCAP's theoretical concepts to Bitcoin Core governance data, providing quantitative validation of theoretical claims about stakeholder engagement during consensus changes.

## License

MIT License - see LICENSE file for details.

