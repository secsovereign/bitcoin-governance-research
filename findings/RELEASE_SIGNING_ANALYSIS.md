# Release Signing Authority Analysis Report

**Analysis Date**: 2026-01-18  
**Data Sources**: Bitcoin Core release signatures  
**Purpose**: Analyze release signing authority concentration and patterns

---

## Overview

This report analyzes who signs Bitcoin Core releases, tracking signing authority concentration over time and examining the relationship between release signers and contributors.

---

## Key Findings

### 1. Signing Authority Concentration

**Total Releases**: 339  
**Signed Releases**: 286 (84.4%)  
**Unique Signers**: 9

**Concentration Metrics**:
- Gini Coefficient: 0.545
- Top 5 Signers: 92.0% of all signed releases
- Top 10 Signers: 98.6% of all signed releases

**Top Signers**:
1. Wladimir J. van der Laan: 105 releases (36.7%)
2. fanquake: 55 releases (19.2%)
3. Gavin Andresen: 53 releases (18.5%)
4. W. J. van der Laan (ProtonMail): 35 releases (12.2%)
5. glozow: 15 releases (5.2%)

### 2. Temporal Patterns

Release signing has been **consistently high** across all years (100% signing rate from 2011-2025), with most releases signed by 1-3 unique signers per year.

---

## Implications

1. **High Concentration**: 92.0% of releases signed by top 5 signers indicates extreme signing authority concentration
2. **Historical Continuity**: Wladimir J. van der Laan signed 105 releases, demonstrating long-term signing authority
3. **Recent Transition**: fanquake has signed 55 recent releases, indicating transition of signing authority

**Data Source**: `analysis/findings/data/release_signing.json`
