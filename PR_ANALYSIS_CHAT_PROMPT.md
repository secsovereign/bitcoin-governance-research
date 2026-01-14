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

## Critical Analysis Requirements

### Deductions vs Inferences

**You MUST explicitly differentiate between deductions and inferences in your analysis:**

- **[DEDUCTION]**: A conclusion that follows necessarily from the data. Facts that can be directly observed.
  - Example: "Commit 0bf7b38b on 2020-07-13 contains `fs::remove_all()`" (can be verified in commit diff)
  - Example: "PR has 98 reviews" (countable from data)
  - Example: "Sjors left a review comment on 2022-08-26" (directly observable)
  - **Format**: State as fact: "The data shows..." or "Commit X contains..." or "[DEDUCTION]..."

- **[INFERENCE]**: A conclusion drawn from available evidence but not directly observable.
  - Example: "The comment 'Latest push adds cleanup' likely refers to cleanup code" (inference from comment)
  - Example: "The cleanup code was probably added late" (inference, not directly observable)
  - Example: "This suggests the code wasn't reviewed" (inference from absence of evidence)
  - **Format**: Explicitly state as inference: "Based on [evidence], I infer..." or "[INFERENCE]..." or "This suggests..."

**When making ANY claim, you MUST label it as either [DEDUCTION] or [INFERENCE].**

### Commit History Analysis

**You MUST unwind the complete commit history of PRs:**

1. **Get ALL commits in the PR** - Not just merge commits or commits by author
   - Use GitHub API: `GET /repos/{owner}/{repo}/pulls/{pull_number}/commits`
   - This gives you every commit that's part of the PR

2. **Trace code changes to specific commits**:
   - For any code pattern or change mentioned, identify the exact commit that introduced it
   - Check each commit's diff to see what code was added/removed
   - Don't infer from comments - verify in commit diffs

3. **Build complete timeline of code changes**:
   - When was each piece of code added?
   - When was it modified?
   - When was it removed?
   - Which commits contain which changes?

4. **Don't make unnecessary inferences**:
   - If you can see the commit, state it as a deduction
   - If you can't see the commit but have a comment, state it as an inference
   - Don't infer when you can verify

### Example of Proper Analysis

**WRONG** (making inference without labeling):
> "The cleanup code was added on 2022-08-17 based on the comment."

**CORRECT** (explicitly labeled):
> "[DEDUCTION] Commit 0bf7b38b on 2020-07-13 contains `fs::remove_all()` in the diff.
> [INFERENCE] The comment on 2022-08-17 saying 'Latest push adds cleanup on failure' likely refers to refinement of cleanup logic, not the initial addition, since the code existed in commit 0bf7b38b from 2020."

## Important Notes

- **Data Quality**: Some PRs (especially old ones) may have `None` for user.login fields. This is a data quality issue, not a protocol issue. The protocol handles this gracefully.

- **Cross-Platform Identity**: IRC nicks, email addresses, and GitHub usernames don't always match. The protocol attempts to link them but may miss some connections.

- **Timeline**: Events are sorted chronologically. IRC messages and emails are included if they mention the PR number or related terms within the PR's timeframe.

- **Commit History**: Always fetch ALL commits in the PR via GitHub API, not just merge commits or commits by author. Trace every code change to its specific commit.

## Your Task

I want you to help me analyze specific PRs for governance situations or failures. When I give you a PR number:

1. **Fetch ALL commits in the PR** using GitHub API (not just merge commits)
2. **Trace every code change to its specific commit** - don't infer, verify
3. **Run the context gathering script** (which should include all commits)
4. **Generate the analysis file**
5. **Review the data and provide insights** - explicitly labeling deductions vs inferences
6. **Answer the analysis questions** - with proper deduction/inference labeling
7. **Identify any governance issues or patterns**

**Critical Requirements:**
- **Every claim must be labeled** as [DEDUCTION] or [INFERENCE]
- **Don't infer when you can verify** - check commit diffs directly
- **Unwind complete commit history** - get all commits, trace all code changes
- **State evidence explicitly** - show what data supports each claim

You have full access to:
- All the data files
- The analysis scripts
- The protocol documentation
- The ability to run Python scripts and read files
- GitHub API access (via curl or Python requests)

Let me know when you're ready to analyze a specific PR!
