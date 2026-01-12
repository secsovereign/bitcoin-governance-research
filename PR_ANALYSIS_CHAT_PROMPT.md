# Prompt for PR Governance Analysis Chat

Use this prompt when starting a new chat to analyze specific PRs for governance situations or failures.

---

## Context

I'm working on a Bitcoin Core governance research project. We have collected comprehensive data from:
- **GitHub**: ~23,478 PRs with all comments, reviews, and metadata
- **IRC**: ~441,931 messages from development channels
- **Mailing Lists**: ~19,908 emails from bitcoin-dev and bitcoin-core-dev
- **Commits**: ~5,000+ commits (collection ongoing)

The project is located at: `/home/acolyte/src/BitcoinCommons/commons-research/`

## PR Analysis Protocol

We have a protocol for analyzing specific PRs to understand governance situations or failures:

### Step 1: Gather PR Context

```bash
cd /home/acolyte/src/BitcoinCommons/commons-research
python3 scripts/analysis/gather_pr_context.py <PR_NUMBER>
```

This script:
- Finds the PR in GitHub data
- Searches IRC messages for mentions (by PR number, title keywords, author)
- Searches mailing list emails for mentions
- Finds related commits (merge commits, commits by PR author)
- Builds a chronological timeline
- Analyzes participants and their roles
- Extracts governance indicators (self-merge, zero reviews, conflicts, etc.)

**Output**: `data/pr_contexts/pr_context_{PR_NUMBER}.json`

### Step 2: Generate Analysis Prompt

```bash
python3 scripts/analysis/analyze_pr_governance.py data/pr_contexts/pr_context_{PR_NUMBER}.json
```

This generates a structured markdown file with:
- PR overview
- Governance indicators summary
- Timeline of events
- Participant list
- Structured analysis questions
- Full context summary

**Output**: `data/pr_analyses/analysis_{PR_NUMBER}.md`

### Step 3: AI Analysis

Use the generated markdown file to analyze the governance situation. The file contains structured questions about:
1. Decision-making process
2. Power dynamics
3. Transparency
4. Governance failures
5. Patterns
6. Specific people/relationships

## Key Files

- **Scripts**:
  - `scripts/analysis/gather_pr_context.py` - Collects all PR context
  - `scripts/analysis/analyze_pr_governance.py` - Generates analysis prompts
  - `scripts/analysis/PR_GOVERNANCE_ANALYSIS_PROTOCOL.md` - Full protocol documentation

- **Data**:
  - `data/github/prs_raw.jsonl` - All PRs
  - `data/github/commits_raw.jsonl` - Commits
  - `data/irc/messages.jsonl` - IRC messages
  - `data/mailing_lists/emails.jsonl` - Mailing list emails
  - `data/pr_contexts/` - Generated PR context files
  - `data/pr_analyses/` - Generated analysis files

## Governance Indicators to Look For

1. **Self-Merge**: Author merged their own PR
2. **Zero Reviews**: No reviews before merge
3. **Maintainer Involvement**: Who was involved, how
4. **Conflict Indicators**: NACKs, rejections, concerns
5. **Transparency**: Cross-platform discussion (IRC, mailing lists)
6. **Decision Patterns**: How was the decision made?

## Maintainer List

The following are identified maintainers (people with merge authority):
- laanwj, sipa, maflcko, fanquake, hebasto, jnewbery
- ryanofsky, achow101, theuni, jonasschnelli, Sjors
- promag, instagibbs, TheBlueMatt, jonatack, gmaxwell
- gavinandresen, petertodd, luke-jr, glozow

## Analysis Framework

When analyzing a PR, consider:

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
   - Was there cross-platform coordination (IRC, mailing lists)?

4. **Governance Failures**
   - Were there any governance failures or red flags?
   - Examples: self-merge, zero reviews, lack of transparency, conflicts ignored
   - What could have been done better?

5. **Patterns**
   - Does this PR exhibit patterns seen in other PRs?
   - Is this typical or atypical for Bitcoin Core governance?
   - What does this tell us about the governance system?

6. **Specific People/Relationships**
   - Analyze relationships between participants
   - Were there conflicts or tensions?
   - Did personal relationships influence the outcome?

## Example Workflow

```bash
# 1. Gather context for PR #34040
cd /home/acolyte/src/BitcoinCommons/commons-research
python3 scripts/analysis/gather_pr_context.py 34040

# 2. Generate analysis prompt
python3 scripts/analysis/analyze_pr_governance.py data/pr_contexts/pr_context_34040.json

# 3. Review the analysis file
cat data/pr_analyses/analysis_34040.md

# 4. Use with AI to analyze
# (The markdown file contains all context and questions)
```

## Important Notes

- **Data Quality**: Some PRs (especially old ones) may have `None` for user.login fields. This is a data quality issue, not a protocol issue. The protocol handles this gracefully.

- **Cross-Platform Identity**: IRC nicks, email addresses, and GitHub usernames don't always match. The protocol attempts to link them but may miss some connections.

- **Timeline**: Events are sorted chronologically. IRC messages and emails are included if they mention the PR number or related terms within the PR's timeframe.

## Your Task

I want you to help me analyze specific PRs for governance situations or failures. When I give you a PR number:

1. Run the context gathering script
2. Generate the analysis file
3. Review the data and provide insights
4. Answer the analysis questions
5. Identify any governance issues or patterns

You have full access to:
- All the data files
- The analysis scripts
- The protocol documentation
- The ability to run Python scripts and read files

Let me know when you're ready to analyze a specific PR!
