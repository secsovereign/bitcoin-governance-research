# Cross-Platform Influence Networks Report

**Analysis Date**: 2026-01-18  
**Data Sources**: GitHub PRs (23,615), IRC messages (441,931), Emails (19,908)  
**Purpose**: Build comprehensive influence networks across platforms and identify hidden influencers

---

## Overview

This report analyzes influence networks across GitHub, IRC, and mailing lists, identifying actors who span multiple platforms and those who operate primarily in informal channels.

---

## Key Findings

### 1. Platform Actor Counts

| Platform | Unique Actors |
|----------|---------------|
| **GitHub** | 2,989 |
| **IRC** | 2,666 |
| **Email** | 1,820 |

### 2. Identity Overlap

#### Exact Username Matching (Lower Bound)

| Overlap | Count | % of GitHub |
|---------|-------|-------------|
| GitHub-IRC | 236 | 9.8% |
| GitHub-Email | 21 | 0.9% |
| IRC-Email | 24 | 0.9% |
| All Platforms | 10 | 0.4% |

#### Enhanced Resolution (Verified Maintainers)

Using documented maintainer aliases, we verified **20 core maintainers** are present across all platforms:

| Maintainer | GitHub | IRC | Email |
|------------|--------|-----|-------|
| laanwj | ✓ | ✓ (wumpus) | ✓ |
| sipa | ✓ | ✓ | ✓ |
| gavinandresen | ✓ | ✓ | ✓ |
| gmaxwell | ✓ | ✓ (nullc) | ✓ |
| TheBlueMatt | ✓ | ✓ | ✓ |
| ... and 15 more | | | |

---

## Implications

1. **Core Governance Verified**: 20 maintainers confirmed across all platforms
2. **Lower Bound**: 236 exact-match overlap is minimum; actual overlap likely higher
3. **Platform Separation**: Non-maintainer overlap rates suggest distinct communities
4. **Hidden Influencers**: Many IRC/email participants are not on GitHub

---

## Methodology

### Identity Resolution Methods

1. **Exact Username Matching**: Baseline overlap (236 GitHub-IRC)
2. **Enhanced Resolution**: Documented maintainer aliases verified 20 core contributors

### Data Sources

- **Maintainer Aliases**: Publicly documented (GitHub profiles, mailing list signatures, IRC registrations)
- **GitHub**: 23,615 PRs
- **IRC**: 441,931 messages
- **Email**: 19,351 messages

### Limitations

- Non-maintainer identity resolution requires manual research
- Email format ("Name via bitcoin-dev") loses original email addresses
- IRC nickname variations beyond documented ones not captured

### Data Files

- `analysis/findings/data/cross_platform_networks.json` - Basic network analysis
- `analysis/findings/data/enhanced_identity_resolution.json` - Verified maintainer identities

---

## Data Source

`analysis/findings/data/cross_platform_networks.json`
