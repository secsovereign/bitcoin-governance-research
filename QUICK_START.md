# Quick Start Guide

## 1. Initial Setup (5 minutes)

```bash
./setup.sh
source venv/bin/activate
```

This will:
- Create virtual environment
- Install dependencies
- Set up directory structure

## 2. Configure (Optional, 2 minutes)

Edit `.env` and add your GitHub token (optional but recommended for higher rate limits):

```bash
GITHUB_TOKEN=your_token_here
```

Get a token from: https://github.com/settings/tokens
(No special permissions needed for public data)

## 3. Validate Setup (1 minute)

```bash
python scripts/validate_setup.py
```

Should show: ✓ All tests passed!

## 4. Test Connection (2 minutes)

```bash
python scripts/test_minimal_collection.py
```

Should:
- Connect to GitHub
- Collect 3 test PRs
- Show rate limit status

## 5. Incremental Collection (Recommended)

Use the interactive workflow:

```bash
python scripts/workflow.py
```

This will guide you through:
1. Setup validation
2. Connection test
3. Small batch (10 PRs)
4. Medium batch (100 PRs)
5. Ready for full collection

## 6. Full Collection (When Ready)

After validating with small batches:

```bash
# Collect all PRs (4-8 hours, 2-5 GB)
python scripts/data_collection/github_collector.py

# Collect all issues
python scripts/data_collection/github_collector.py --issues-only

# Or collect both (default)
python scripts/data_collection/github_collector.py
```

## Troubleshooting

### Import Errors
```bash
# Make sure venv is activated
source venv/bin/activate

# Reinstall dependencies
pip install -e .
```

### GitHub API Errors
- Check token in .env
- Verify rate limits not exceeded
- Check network connection

### Permission Errors
```bash
# Make scripts executable
chmod +x scripts/*.py
chmod +x setup.sh
```

## Next Steps

After data collection:
1. Review collected data
2. Run data processing scripts
3. Run analysis scripts
4. Generate reports

See [DATA_SOURCING_AND_REPRODUCIBILITY.md](../DATA_SOURCING_AND_REPRODUCIBILITY.md) for detailed data sourcing information.

