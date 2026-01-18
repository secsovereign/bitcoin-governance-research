# BIP Process Analysis Report

**Analysis Date**: 2026-01-18  
**Data Sources**: BIP repository (GitHub), Bitcoin Core repository  
**Purpose**: Analyze governance patterns in the Bitcoin Improvement Proposal (BIP) process and compare to Core repository governance

---

## Overview

This report analyzes the governance patterns within the Bitcoin Improvement Proposal (BIP) repository, examining how proposals are made, reviewed, and championed. The analysis compares BIP governance to Bitcoin Core repository governance to understand power distribution and process differences.

---

## Key Findings

### 1. Proposer Concentration

**Total BIPs**: 189  
**Total Proposers**: 91  
**Proposal Concentration**:
- Top 3 proposers: 23.3% of all BIPs
- Top 5 proposers: 30.2% of all BIPs
- Top 10 proposers: 41.8% of all BIPs
- Gini Coefficient: 0.433

**Top Proposers**:
- Pieter Wuille: 21 BIPs (11.1%)
- Gavin Andresen: 12 BIPs (6.3%)
- Luke Dashjr: 11 BIPs (5.8%)

### 2. Champion Activity

**Total Champions**: 684 unique participants in BIP PRs

**Top Champions** (by PR activity):
1. achow101: 314 activities
2. kallewoof: 246 activities
3. nicolasdorier: 236 activities
4. luke-jr: 214 activities
5. ysangkok: 203 activities

### 3. Repository Comparison

**Actor Overlap**:
- BIP authors: 684
- Core authors: 0
- Overlapping authors: 0
- Overlap rate: 0.0%

**BIP Merge Concentration**:
- Total merged PRs: 1,208
- Unique mergers: 419
- Top mergers include achow101 (54 merges), jl2012 (44 merges), sipa (36 merges)

---

## Methodology

- **Proposer Extraction**: Authors extracted from BIP content using Author: field
- **Champion Identification**: Based on activity frequency (PRs authored, comments)
- **Implementation Tracking**: BIP number mentions in Core PR titles/bodies
- **Repo Comparison**: Actor overlap and merge concentration comparison

**Limitations**:
- BIP author extraction may miss some authors
- Champion analysis limited by available comment data
- Implementation tracking based on BIP mentions (may miss some)

---

## Implications

1. **Proposal Concentration**: 23.3% of BIPs proposed by top 3 individuals indicates significant proposal concentration
2. **Actor Overlap**: Low overlap between BIP and Core repositories suggests separate governance processes
3. **Champion Network**: Large champion network (684 participants) suggests active community engagement in BIP review

**Data Source**: `analysis/findings/data/bip_analysis.json`
