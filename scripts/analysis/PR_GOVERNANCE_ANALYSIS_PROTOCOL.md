# PR Governance Analysis Protocol

**Purpose**: Analyze specific governance situations or failures by gathering all available data about a PR and using AI agents to analyze governance patterns.

---

## Overview

This protocol allows you to:
1. **Gather all context** for a specific PR across all data sources
2. **Generate structured analysis prompts** for AI agents
3. **Analyze governance situations** with comprehensive data

---

## Step 1: Gather PR Context

Use `gather_pr_context.py` to collect all data about a specific PR:

```bash
python scripts/analysis/gather_pr_context.py <PR_NUMBER>
```

**What it collects**:
- GitHub PR data (comments, reviews, metadata)
- IRC messages mentioning the PR
- Mailing list emails mentioning the PR
- Related commits
- Timeline of events
- Participant analysis
- Governance indicators (self-merge, zero reviews, conflicts, etc.)

**Output**: `data/pr_contexts/pr_context_{PR_NUMBER}.json`

**Example**:
```bash
python scripts/analysis/gather_pr_context.py 34040
```

This will:
- Find PR #34040 in GitHub data
- Search IRC messages for mentions of "#34040" or related terms
- Search mailing list emails for mentions
- Find related commits
- Build a timeline
- Analyze participants
- Extract governance indicators

---

## Step 2: Generate Analysis Prompt

Use `analyze_pr_governance.py` to generate an AI analysis prompt:

```bash
python scripts/analysis/analyze_pr_governance.py data/pr_contexts/pr_context_{PR_NUMBER}.json
```

**Output**: `data/pr_analyses/analysis_{PR_NUMBER}.md`

**What it generates**:
- PR overview
- Governance indicators summary
- Timeline of events
- Participant list
- Structured analysis questions
- Full context summary

**Example**:
```bash
python scripts/analysis/analyze_pr_governance.py data/pr_contexts/pr_context_34040.json
```

---

## Step 3: AI Analysis

Use the generated markdown file with an AI agent (like this one) to analyze:

1. **Load the analysis file**: The markdown file contains all context and questions
2. **Answer the analysis questions**:
   - Decision-making process
   - Power dynamics
   - Transparency
   - Governance failures
   - Patterns
   - Specific people/relationships
3. **Generate comprehensive analysis**

**Example prompt to AI**:
```
Please analyze the governance situation described in data/pr_analyses/analysis_34040.md
```

---

## Analysis Framework

### Governance Indicators to Look For

1. **Self-Merge**: Author merged their own PR
2. **Zero Reviews**: No reviews before merge
3. **Maintainer Involvement**: Who was involved, how
4. **Conflict Indicators**: NACKs, rejections, concerns
5. **Transparency**: Cross-platform discussion (IRC, mailing lists)
6. **Decision Patterns**: How was the decision made?

### Key Questions

1. **Decision-Making Process**
   - How was the decision to merge/reject made?
   - Was there adequate review and discussion?
   - Were decision criteria clear and consistently applied?

2. **Power Dynamics**
   - Who had influence over this PR's outcome?
   - Were maintainers involved appropriately?
   - Was there any evidence of power concentration or abuse?

3. **Transparency**
   - Was discussion transparent and public?
   - Were concerns raised and addressed?
   - Was there cross-platform coordination?

4. **Governance Failures**
   - Were there any governance failures or red flags?
   - What could have been done better?

5. **Patterns**
   - Does this PR exhibit patterns seen in other PRs?
   - Is this typical or atypical for Bitcoin Core governance?

6. **Specific People/Relationships**
   - Analyze relationships between participants
   - Were there conflicts or tensions?
   - Did personal relationships influence the outcome?

---

## Example Workflow

### Analyze a Specific Governance Situation

```bash
# 1. Gather context for PR #34040
python scripts/analysis/gather_pr_context.py 34040

# 2. Generate analysis prompt
python scripts/analysis/analyze_pr_governance.py data/pr_contexts/pr_context_34040.json

# 3. Review the generated analysis file
cat data/pr_analyses/analysis_34040.md

# 4. Use with AI agent
# (Load the file and ask AI to analyze)
```

### Analyze Multiple PRs

```bash
# Create a batch script
for pr in 34040 34041 34042; do
    python scripts/analysis/gather_pr_context.py $pr
    python scripts/analysis/analyze_pr_governance.py data/pr_contexts/pr_context_${pr}.json
done
```

---

## Output Files

### `pr_context_{PR_NUMBER}.json`

Complete context including:
- Full GitHub PR data
- All IRC messages
- All mailing list emails
- Related commits
- Timeline
- Participants
- Governance indicators

### `analysis_{PR_NUMBER}.md`

Structured analysis prompt with:
- PR overview
- Governance indicators
- Timeline
- Participants
- Analysis questions
- Full context summary

---

## Use Cases

### 1. Analyze Governance Failures

Find PRs with red flags (self-merge, zero reviews) and analyze:

```bash
# Find self-merge PRs (from analysis)
# Then analyze specific ones
python scripts/analysis/gather_pr_context.py <PR_NUMBER>
python scripts/analysis/analyze_pr_governance.py data/pr_contexts/pr_context_<PR_NUMBER>.json
```

### 2. Analyze Specific People

Analyze PRs involving specific maintainers or contributors:

```bash
# Find PRs by/merged by specific person
# Then analyze
python scripts/analysis/gather_pr_context.py <PR_NUMBER>
python scripts/analysis/analyze_pr_governance.py data/pr_contexts/pr_context_<PR_NUMBER>.json
```

### 3. Analyze Conflicts

Find PRs with NACKs or conflicts:

```bash
# Find PRs with conflict indicators
# Then analyze
python scripts/analysis/gather_pr_context.py <PR_NUMBER>
python scripts/analysis/analyze_pr_governance.py data/pr_contexts/pr_context_<PR_NUMBER>.json
```

### 4. Compare Governance Patterns

Analyze multiple PRs to compare patterns:

```bash
# Analyze several PRs
# Compare the analysis outputs
# Look for patterns
```

---

## Tips

1. **Start with interesting PRs**: Look for PRs with governance indicators (self-merge, zero reviews, conflicts)

2. **Use the timeline**: The timeline shows the sequence of events - useful for understanding decision-making

3. **Check cross-platform**: IRC and mailing list discussions often reveal governance issues not visible in GitHub

4. **Analyze participants**: Who was involved and how? Maintainers vs. non-maintainers?

5. **Look for patterns**: Does this PR exhibit patterns seen in other PRs?

---

## Integration with AI Agents

The generated analysis files are designed to be used with AI agents:

1. **Load the context**: The JSON file has all raw data
2. **Use the prompt**: The markdown file has structured questions
3. **Generate analysis**: AI can answer questions and provide insights
4. **Iterate**: Refine questions based on findings

---

## Future Enhancements

- **Automated red flag detection**: Automatically identify PRs with governance issues
- **Comparative analysis**: Compare multiple PRs side-by-side
- **Pattern detection**: Identify recurring governance patterns
- **Visualization**: Generate timelines and relationship graphs
- **Export formats**: Support for different analysis formats
