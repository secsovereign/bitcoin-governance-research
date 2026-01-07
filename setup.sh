#!/bin/bash
# Setup script for Bitcoin Governance Analysis project

set -e

echo "Setting up Bitcoin Governance Communications Analysis project..."

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo ""
        echo "⚠️  Please edit .env and add your GitHub token"
        echo "   1. Get a token from: https://github.com/settings/tokens"
        echo "   2. Edit .env and replace 'your_github_token_here' with your token"
        echo "   3. See GITHUB_TOKEN_SETUP.md for detailed instructions"
    else
        echo "Creating basic .env file..."
        cat > .env << 'EOF'
# GitHub API Configuration
# Get a token from: https://github.com/settings/tokens
# No special permissions needed for public data reading
GITHUB_TOKEN=your_github_token_here
EOF
        echo ""
        echo "⚠️  Please edit .env and add your GitHub token"
        echo "   Get a token from: https://github.com/settings/tokens"
    fi
fi

# Create necessary directories
echo "Creating directories..."
mkdir -p logs
mkdir -p data/{github,mailing_lists,luke_case,processed}

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env and add your GitHub token (optional but recommended)"
echo "2. Activate the virtual environment: source venv/bin/activate"
echo "3. Run data collection: python scripts/data_collection/github_collector.py"
echo ""

