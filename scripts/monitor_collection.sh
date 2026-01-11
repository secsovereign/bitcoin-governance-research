#!/bin/bash
# Monitor GitHub collection progress

echo "=== GitHub Collection Monitor ==="
echo ""

# Check if collection is running
if pgrep -f "github_collector.py" > /dev/null; then
    echo "✅ Collection is running"
    echo ""
else
    echo "❌ Collection is not running"
    echo ""
fi

# Show recent log entries
echo "=== Recent Log Entries ==="
tail -20 /tmp/github_collection.log 2>/dev/null | grep -E "(INFO|ERROR|Collected|Skipped|complete)" || echo "No log entries yet"

echo ""
echo "=== File Status ==="
cd /home/acolyte/src/BitcoinCommons/commons-research
if [ -f data/github/prs_raw.jsonl ]; then
    PR_COUNT=$(wc -l < data/github/prs_raw.jsonl)
    PR_SIZE=$(du -h data/github/prs_raw.jsonl | cut -f1)
    echo "PRs: $PR_COUNT lines, $PR_SIZE"
else
    echo "PRs: File not found"
fi

if [ -f data/github/issues_raw.jsonl ]; then
    ISSUE_COUNT=$(wc -l < data/github/issues_raw.jsonl)
    ISSUE_SIZE=$(du -h data/github/issues_raw.jsonl | cut -f1)
    echo "Issues: $ISSUE_COUNT lines, $ISSUE_SIZE"
else
    echo "Issues: File not found"
fi

echo ""
echo "=== To monitor in real-time ==="
echo "  tail -f /tmp/github_collection.log"
echo ""
echo "=== To analyze new data when done ==="
echo "  python3 scripts/analyze_new_data.py"
