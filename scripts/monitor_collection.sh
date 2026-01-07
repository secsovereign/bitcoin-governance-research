#!/bin/bash
# Monitor all data collection processes

echo "Data Collection Monitor"
echo "======================"
echo ""

# Check running processes
echo "Running Collection Processes:"
ps aux | grep -E "(github_collector|mailing_list|irc_collector)" | grep -v grep | awk '{print "  PID:", $2, "|", $11, $12, $13}'
echo ""

# GitHub progress
if [ -f "data/github/prs_raw.jsonl" ]; then
    pr_count=$(wc -l < data/github/prs_raw.jsonl)
    pr_size=$(du -h data/github/prs_raw.jsonl | awk '{print $1}')
    echo "GitHub PRs:"
    echo "  Collected: $pr_count / 23,455"
    echo "  Progress: $(echo "scale=1; $pr_count * 100 / 23455" | bc)%"
    echo "  File size: $pr_size"
    
    if [ -f "logs/github_pr_collection.log" ]; then
        echo "  Latest log:"
        tail -3 logs/github_pr_collection.log | sed 's/^/    /'
    fi
else
    echo "GitHub PRs: Not started"
fi
echo ""

# Mailing list progress
if [ -f "data/mailing_lists/emails.jsonl" ]; then
    email_count=$(wc -l < data/mailing_lists/emails.jsonl)
    email_size=$(du -h data/mailing_lists/emails.jsonl | awk '{print $1}')
    echo "Mailing Lists:"
    echo "  Collected: $email_count emails"
    echo "  File size: $email_size"
    
    if [ -f "logs/mailing_list_collection.log" ]; then
        echo "  Latest log:"
        tail -3 logs/mailing_list_collection.log | sed 's/^/    /'
    fi
else
    echo "Mailing Lists: Not started or in progress"
fi
echo ""

# IRC progress
if [ -f "data/irc/messages.jsonl" ]; then
    irc_count=$(wc -l < data/irc/messages.jsonl)
    irc_size=$(du -h data/irc/messages.jsonl | awk '{print $1}')
    echo "IRC Messages:"
    echo "  Collected: $irc_count messages"
    echo "  File size: $irc_size"
    
    if [ -f "logs/irc_collection.log" ]; then
        echo "  Latest log:"
        tail -3 logs/irc_collection.log | sed 's/^/    /'
    fi
else
    echo "IRC Messages: Not started or in progress"
fi
echo ""

# Overall progress
total_files=$(ls -1 data/github/*.jsonl data/mailing_lists/*.jsonl data/irc/*.jsonl 2>/dev/null | wc -l)
total_size=$(du -sh data/ 2>/dev/null | awk '{print $1}')

echo "Overall:"
echo "  Data files: $total_files"
echo "  Total size: $total_size"
echo ""
echo "To watch continuously: watch -n 30 ./scripts/monitor_collection.sh"


