# GitHub Token Setup Guide

## Quick Setup

### Step 1: Create a GitHub Token

1. Go to: https://github.com/settings/tokens
2. Click **"Generate new token"** → **"Generate new token (classic)"**
3. Give it a name like "Bitcoin Governance Analysis"
4. **No scopes needed** - just leave everything unchecked (public data doesn't require permissions)
5. Click **"Generate token"**
6. **Copy the token immediately** - you won't be able to see it again!

### Step 2: Add Token to Project

**Option A: Using .env file (Recommended)**

```bash
cd commons-research

# Copy the example file
cp .env.example .env

# Edit .env and replace 'your_github_token_here' with your actual token
nano .env
# or
vim .env
# or use any text editor
```

In the `.env` file, change:
```
GITHUB_TOKEN=your_github_token_here
```

To:
```
GITHUB_TOKEN=ghp_your_actual_token_here
```

**Option B: Using Environment Variable**

```bash
# Set for current session
export GITHUB_TOKEN=ghp_your_actual_token_here

# Or add to your ~/.bashrc or ~/.zshrc for persistence
echo 'export GITHUB_TOKEN=ghp_your_actual_token_here' >> ~/.bashrc
source ~/.bashrc
```

### Step 3: Verify It Works

```bash
# Test the connection
python scripts/test_minimal_collection.py
```

You should see:
- "Using authenticated GitHub API"
- Rate limit status showing higher limits (5000/hour instead of 60/hour)

## Token Format

GitHub tokens start with:
- `ghp_` for personal access tokens (classic)
- `gho_` for OAuth tokens
- `ghu_` for user-to-server tokens
- `ghs_` for server-to-server tokens

Most common: `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

## Why Use a Token?

**Without token:**
- 60 requests/hour (very slow)
- Full collection would take days/weeks

**With token:**
- 5,000 requests/hour (much faster)
- Full collection takes 4-8 hours

## Security Notes

✅ **Safe to do:**
- Store token in `.env` file (it's in `.gitignore`, won't be committed)
- Use token for public data reading (no special permissions needed)

❌ **Don't do:**
- Commit `.env` file to git (it's already in `.gitignore`)
- Share token publicly
- Give token unnecessary permissions

## Troubleshooting

### Token Not Working

1. **Check token format**: Should start with `ghp_`
2. **Check .env file**: Make sure it's in the project root
3. **Check variable name**: Must be exactly `GITHUB_TOKEN`
4. **No quotes needed**: Just `GITHUB_TOKEN=ghp_xxxxx` (no quotes around token)

### Still Getting Rate Limited

1. **Check if token is being read**:
   ```bash
   python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('Token:', os.getenv('GITHUB_TOKEN')[:10] + '...' if os.getenv('GITHUB_TOKEN') else 'NOT SET')"
   ```

2. **Verify token is valid**: Try using it in a browser:
   ```
   https://api.github.com/user?access_token=YOUR_TOKEN
   ```
   (Replace YOUR_TOKEN with your actual token)

3. **Check rate limit status**:
   ```bash
   python scripts/test_minimal_collection.py
   ```
   Should show 5000/hour if token is working

### Token Expired

If your token expires:
1. Go back to https://github.com/settings/tokens
2. Generate a new token
3. Update `.env` file with new token

## Alternative: No Token (Slower)

You can run without a token, but it will be much slower:
- 60 requests/hour instead of 5,000
- Full collection will take much longer
- Still works, just be patient!

The scripts will automatically detect if you have a token and use it if available.

