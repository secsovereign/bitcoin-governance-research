# Informal Communication Sentiment Analysis Report

**Analysis Date**: 2026-01-18  
**Data Sources**: IRC messages (441,931), Mailing list emails (19,351)  
**Purpose**: Analyze sentiment and State of Mind (SOM) in informal communication channels

---

## Overview

This report analyzes sentiment and engagement patterns in IRC and mailing list communications, applying BCAP's State of Mind framework to understand informal governance dynamics.

---

## Key Findings

### 1. IRC Sentiment Distribution

**Total IRC Messages**: 441,931

| Sentiment | Percentage | Count |
|-----------|------------|-------|
| Neutral | 65.4% | 289,221 |
| Negative | 24.3% | 107,349 |
| Positive | 10.3% | 45,361 |

### 2. Email Sentiment Distribution

**Total Emails**: 19,351

| Sentiment | Percentage | Count |
|-----------|------------|-------|
| Neutral | 39.9% | 7,730 |
| Negative | 39.7% | 7,687 |
| Positive | 20.3% | 3,934 |

### 3. State of Mind (SOM) Distribution

**IRC SOM**:
| SOM | Description | Percentage |
|-----|-------------|------------|
| SOM3 | Apathetic/Undecided | 46.6% |
| SOM2 | Supportive | 45.4% |
| SOM1 | Passionate Advocate | 3.9% |
| SOM6 | Passionately Against | 3.1% |
| SOM5 | Not Supportive | 1.1% |

**Email SOM**:
| SOM | Description | Percentage |
|-----|-------------|------------|
| SOM2 | Supportive | 59.1% |
| SOM3 | Apathetic/Undecided | 23.3% |
| SOM1 | Passionate Advocate | 12.9% |
| SOM6 | Passionately Against | 2.8% |
| SOM5 | Not Supportive | 1.8% |

---

## Key Insights

1. **IRC is Primary Channel**: 441,931 IRC messages vs 19,351 emails (23:1 ratio)
2. **IRC is More Neutral**: 65.4% neutral (technical discussion)
3. **Email is More Polarized**: 40% negative vs IRC's 24%
4. **Email Shows More Passion**: 12.9% SOM1 (passionate advocate) vs IRC's 3.9%
5. **Both Channels Supportive**: SOM2 (supportive) is dominant in both

---

## Methodology Limitations

⚠️ **Keyword-Based Sentiment**: This analysis uses keyword matching, not ML/BERT. Results are indicative, not definitive.

- May miss sarcasm and context
- Keyword lists may not capture domain-specific sentiment
- Consider as directional, not precise

---

## Data Source

`analysis/findings/data/informal_sentiment.json`
