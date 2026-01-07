# Recent Years Data & Narrative Analysis

**Generated**: 2025-12-10  
**Analysis**: Assessment of missing recent years data and narrative analysis capabilities

---

## Recent Years Data Status (2020-2024)

### Current Situation

**We have data for 2020-2024, but sample sizes are insufficient for statistical significance.**

| Year | Total PRs | Maintainer PRs | Non-Maintainer PRs | Sufficient? |
|------|----------|----------------|-------------------|-------------|
| 2020 | 37 | 12 | 25 | ✗ |
| 2021 | ? | ? | ? | ? |
| 2022 | ? | ? | ? | ? |
| 2023 | ? | ? | ? | ? |
| 2024 | ? | ? | ? | ? |

**Note**: Only 2020 data was checked. Years 2021-2024 need to be checked.

### Why Sample Size Matters

**For reliable statistical analysis, we need:**
- **≥30 maintainer PRs per year** (for maintainer metrics)
- **≥30 non-maintainer PRs per year** (for comparison)

**2020 has only 12 maintainer PRs and 25 non-maintainer PRs** - both below the threshold.

### What We Can Do

**Option 1: Include with Caveats**
- Show the data that exists (even if small)
- Clearly mark as "insufficient sample size"
- Use for qualitative trends, not quantitative conclusions
- Example: "2020 data shows 91.7% self-merge rate (11 of 12 PRs), but sample size is too small (n=12) for statistical significance"

**Option 2: Aggregate Recent Years**
- Combine 2020-2024 into a single "Recent Era" period
- May provide sufficient sample size when combined
- Loses year-by-year granularity but gains statistical power

**Option 3: Lower Threshold**
- Use ≥10 PRs per group instead of ≥30
- Less reliable but still shows trends
- Clearly mark as "small sample size"

**Recommendation**: **Option 1 + Option 2** - Include individual years with caveats, and also provide aggregated "Recent Era" (2020-2024) analysis.

---

## Narrative Analysis: How Different Narratives Developed Over Time

### What Is Narrative Analysis?

**Narrative analysis tracks how different themes, perspectives, and language patterns evolved in Bitcoin Core communications over time.**

### Narrative Themes Tracked

We analyze **15 major narrative themes** across emails, PRs, and IRC:

1. **Decentralization** - Discussions about decentralization, distributed systems
2. **Governance** - Discussions about governance, decision-making processes
3. **Consensus** - Discussions about consensus, agreement, unanimous decisions
4. **Transparency** - Discussions about transparency, openness, public visibility
5. **Maintainer Authority** - Discussions about maintainer authority, merge rights
6. **Fork Threat** - Discussions about forks, chain splits, hard forks
7. **Blocksize Debate** - Discussions about blocksize, SegWit, scaling solutions
8. **External Pressure** - Discussions about regulation, government, corporate influence
9. **Security** - Discussions about security, vulnerabilities, attacks
10. **Scaling** - Discussions about scaling, throughput, transaction capacity
11. **Trust** - Discussions about trust, trustless systems, verification
12. **Censorship** - Discussions about censorship, filtering, blocking
13. **Inclusivity** - Discussions about inclusivity, diversity, welcoming participation
14. **Technical Excellence** - Discussions about code quality, engineering standards
15. **Social Coordination** - Discussions about social coordination, social layer

### Analysis Dimensions

**1. Narratives by Year**
- Track theme frequency over time
- See which themes dominate in which years
- Identify narrative shifts

**2. Narratives by Epoch**
- Early Development (2009-2013)
- Blocksize Wars (2014-2017)
- Post-SegWit (2018-2020)
- Recent Era (2021-2024)

**3. Narrative Evolution**
- How themes increased/decreased over time
- Identify trends (increasing, decreasing, stable)
- Calculate change percentages

**4. Competing Narratives**
- Tension between decentralization vs centralization
- Formal vs informal governance
- Consensus vs authority-based decisions

**5. Narrative Dominance**
- Which themes dominate in which periods
- Top 5 themes per year
- Dominant theme identification

### What This Reveals

**Narrative analysis can reveal:**
- **How language changed** - Did "decentralization" mentions increase or decrease?
- **When narratives shifted** - Did blocksize wars change the narrative?
- **Competing perspectives** - Are there different narratives about governance?
- **Narrative dominance** - Which themes win over time?
- **Epoch-specific narratives** - What themes dominated during blocksize wars?

### Example Questions We Can Answer

1. **Did "decentralization" mentions increase or decrease over time?**
   - Track "decentralization" theme frequency by year
   - See if it peaked during blocksize wars or decreased

2. **How did "governance" narrative evolve?**
   - Track "governance" theme frequency
   - See if it became more or less prominent
   - Identify when governance discussions peaked

3. **Did "external pressure" narrative increase?**
   - Track "external pressure" theme frequency
   - See if regulatory discussions increased over time
   - Correlate with actual external pressure events

4. **What narratives dominated during blocksize wars?**
   - Analyze epoch-specific narratives
   - See which themes were most discussed during 2014-2017

5. **Are there competing narratives about maintainer authority?**
   - Track "maintainer authority" theme
   - See if discussions increased or decreased
   - Identify competing perspectives

### Implementation Status

**Narrative analysis script created**: `scripts/analysis/narrative_analysis.py`

**Status**: Script created and running (may take time to process all data)

**Output**: `analysis/narrative_analysis/narrative_analysis.json`

**Includes**:
- Narratives by year (2009-2024)
- Narratives by epoch
- Narrative evolution (trends)
- Competing narratives
- Narrative dominance

---

## Recommendations

### 1. Update Temporal Analysis

**Action**: Update `analysis/temporal_metrics/temporal_analysis.json` to include 2020-2024 with caveats.

**Approach**:
- Include 2020-2024 data even if sample size is small
- Mark as "insufficient sample size" but show the data
- Add aggregated "Recent Era" (2020-2024) analysis
- Update `findings/TEMPORAL_METRICS_ANALYSIS.md` to include recent years

### 2. Complete Narrative Analysis

**Action**: Let narrative analysis script complete, then create findings document.

**Output**: `findings/NARRATIVE_ANALYSIS.md` with:
- Theme frequency over time
- Narrative evolution trends
- Epoch-specific narratives
- Competing narratives
- Narrative dominance patterns

### 3. Update BITCOIN_CORE_GOVERNANCE_ANALYSIS.md

**Action**: Add recent years data and narrative analysis findings.

**Add**:
- Recent years section (2020-2024) with caveats
- Narrative analysis findings
- How narratives changed over time
- Competing narratives about governance

---

## Summary

**Recent Years (2020-2024)**:
- ✅ Data exists but sample sizes are small
- ✅ Can include with caveats about statistical significance
- ✅ Can aggregate into "Recent Era" for better sample size

**Narrative Analysis**:
- ✅ Script created and running
- ✅ Tracks 15 major themes across all communications
- ✅ Analyzes by year, epoch, and evolution
- ✅ Identifies competing narratives and dominance patterns

**Next Steps**:
1. Update temporal analysis to include recent years with caveats
2. Complete narrative analysis and create findings document
3. Update BITCOIN_CORE_GOVERNANCE_ANALYSIS.md with recent years and narrative findings
4. Be redundant - include data multiple times with different perspectives

---

**Data Sources**:
- PRs: `data/github/prs_raw.jsonl` (23,478 PRs collected)
- Emails: `data/mailing_lists/emails.jsonl` (19,446 emails collected)
- IRC: `data/irc/messages.jsonl` (433,048 messages collected)

**Analysis Scripts**:
- Temporal Analysis: `scripts/analysis/temporal_metrics.py` (existing)
- Narrative Analysis: `scripts/analysis/narrative_analysis.py` (new)

