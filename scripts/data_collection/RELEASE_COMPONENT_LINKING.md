# Release Component Linking

**Purpose**: Link releases to their components (commits, PRs, issues) to track what goes into each release.

---

## Overview

This system tracks which commits, PRs, and issues go into each Bitcoin Core release. This enables analysis of:
- Which PRs make it into releases
- Release composition (what types of changes)
- Release timelines (when PRs go into releases)
- Release patterns (who gets PRs into releases)

---

## How It Works

### 1. Commits → Releases

Uses GitHub API `repo.compare()` to find commits between release tags:
- Compares `previous_tag..current_tag` (e.g., `v28.2..v28.3`)
- Gets all commits in that range
- Each release contains commits since the previous release

### 2. PRs → Releases

Extracts PR numbers from two sources:

**A. Merge Commits**
- Identifies merge commits (commits with multiple parents)
- Extracts PR numbers from merge commit messages
- Pattern: `Merge bitcoin/bitcoin#12345` or `Merge #12345`

**B. Release Notes**
- Parses release notes (body text) for PR mentions
- Pattern: `#12345` (any PR number mention)
- Combines with merge commit PRs (deduplicates)

### 3. Issues → Releases

Extracts issue numbers from release notes:
- Pattern: `Fixes #123`, `Closes #123`, `Resolves #123`
- Only explicit issue references (not PRs)

---

## Usage

### Basic Linking

```bash
python3 scripts/data_collection/link_release_components.py
```

This will:
1. Load releases from `data/releases/github_releases.jsonl`
2. For each release, compare with previous release tag
3. Extract commits, PRs, and issues
4. Save to `data/releases/release_components.jsonl`

### Enrichment with PR Data

By default, the script also enriches with PR data from our collection:
- Loads PR data from `data/github/prs_raw.jsonl`
- Adds PR metadata (title, author, merged_at, merged_by) to each release
- Saves enriched version to `data/releases/release_components_enriched.jsonl`

### Enrichment Only

If you just want to re-enrich existing component data:

```bash
python3 scripts/data_collection/link_release_components.py --enrich
```

---

## Output Files

### `release_components.jsonl`

Basic mapping with:
- `tag_name`: Release tag (e.g., "v28.3")
- `name`: Release name
- `published_at`: Release date
- `commits`: List of commit SHAs
- `commit_count`: Number of commits
- `prs`: List of PR numbers
- `pr_count`: Number of PRs
- `issues`: List of issue numbers
- `issue_count`: Number of issues

### `release_components_enriched.jsonl`

Enriched version with PR details:
- All fields from basic version
- `pr_details`: Array of PR metadata objects with:
  - `number`: PR number
  - `title`: PR title
  - `author`: PR author
  - `merged_at`: Merge date
  - `merged_by`: Who merged the PR

---

## Example Output

```json
{
  "tag_name": "v28.3",
  "name": "Bitcoin Core 28.3",
  "published_at": "2025-10-30T...",
  "commits": ["abc123...", "def456..."],
  "commit_count": 42,
  "prs": [34040, 34039, 34038],
  "pr_count": 3,
  "issues": [123, 456],
  "issue_count": 2,
  "pr_details": [
    {
      "number": 34040,
      "title": "test: Detect truncated download...",
      "author": "maflcko",
      "merged_at": "2025-12-10T...",
      "merged_by": "fanquake"
    }
  ]
}
```

---

## Limitations

1. **First Release**: The first release in the list cannot be compared (no previous tag), so it may have incomplete data.

2. **Rate Limits**: GitHub API rate limits apply. With a token, you get 5,000 requests/hour. Without a token, 60 requests/hour.

3. **Large Releases**: For releases with many commits (>1000), only the first 1000 are tracked to avoid rate limits.

4. **PR Extraction**: PR numbers are extracted from merge commit messages and release notes. Some PRs might be missed if:
   - Merge commit message format is unusual
   - PR is not mentioned in release notes
   - PR was merged differently (squash/rebase)

5. **Issue Extraction**: Only issues explicitly mentioned in release notes are tracked (Fixes #123, Closes #123). Issues closed by PRs are not automatically linked.

---

## Use Cases

### 1. Release Composition Analysis

Analyze what types of changes go into each release:
- How many PRs per release
- Average commits per release
- Types of changes (based on PR classification)

### 2. PR-to-Release Timeline

Track how long PRs take to reach releases:
- PR merged → Release published
- Which PRs make it into releases
- Which PRs are excluded

### 3. Maintainer Release Patterns

Analyze which maintainers get PRs into releases:
- Who merges PRs that make it into releases
- Maintainer PRs vs. non-maintainer PRs in releases
- Release participation patterns

### 4. Release Analysis

Link PR analysis to releases:
- Analyze PRs in a specific release
- Compare releases (what changed)
- Track governance patterns across releases

---

## Integration with PR Analysis

This system complements the PR governance analysis protocol:

1. **Find PRs in a release**: Use `release_components.jsonl` to get PR numbers
2. **Analyze specific PRs**: Use `gather_pr_context.py` for each PR
3. **Release-level analysis**: Analyze all PRs in a release together

Example workflow:
```bash
# 1. Link releases to components
python3 scripts/data_collection/link_release_components.py

# 2. Get PRs for a specific release
python3 -c "
import json
releases = [json.loads(l) for l in open('data/releases/release_components.jsonl')]
v28_3 = [r for r in releases if r['tag_name'] == 'v28.3'][0]
print('PRs in v28.3:', v28_3['prs'])
"

# 3. Analyze specific PRs
for pr_num in [34040, 34039, 34038]:
    python3 scripts/analysis/gather_pr_context.py $pr_num
```

---

## Future Enhancements

- **Issue linking via PRs**: Automatically link issues closed by PRs in releases
- **Release notes parsing**: More sophisticated parsing of release notes structure
- **Commit categorization**: Categorize commits by type (bug fix, feature, refactor)
- **Release comparison**: Compare releases side-by-side
- **Visualization**: Generate release timelines and charts

---

## Technical Details

### GitHub API Compare Endpoint

Uses `repo.compare(base, head)`:
- `base`: Previous release tag (e.g., "v28.2")
- `head`: Current release tag (e.g., "v28.3")
- Returns: Comparison object with commits, files changed, etc.

### PR Number Extraction

**From merge commits:**
- Pattern: `Merge bitcoin/bitcoin#12345` or `Merge #12345`
- Fallback: Any `#12345` pattern in commit message

**From release notes:**
- Pattern: `#12345` (any mention)
- Deduplicates with merge commit PRs

### Issue Number Extraction

**From release notes:**
- Pattern: `(Fixes|Closes|Resolves) #123`
- Case-insensitive matching
- Only explicit issue references

---

## Data Quality

- **Accuracy**: High for PRs (extracted from merge commits and release notes)
- **Completeness**: May miss some PRs if merge format is unusual
- **Issues**: Lower completeness (only explicit mentions in release notes)
- **Commits**: Complete (from GitHub API compare)

---

## Maintenance

- **Run after new releases**: Link new releases as they're published
- **Re-run for updates**: If release notes are updated, re-run to get new PR/issue links
- **Periodic updates**: Refresh enriched data if PR collection is updated
