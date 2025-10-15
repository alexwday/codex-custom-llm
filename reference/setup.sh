#!/bin/bash
# Setup script for Enterprise Codex CLI Wrapper

set -e  # Exit on error

echo "=========================================="
echo "Enterprise Codex CLI Wrapper - Setup"
echo "=========================================="
echo ""

# Detect if we're on a work computer or personal computer
echo "Are you setting up on your work computer? (y/n)"
read -r IS_WORK_COMPUTER

# Create virtual environment
echo ""
echo "Creating Python virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo ""
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Install rbc_security on work computer
if [ "$IS_WORK_COMPUTER" = "y" ] || [ "$IS_WORK_COMPUTER" = "Y" ]; then
    echo ""
    echo "Installing rbc_security package..."
    if pip install rbc_security; then
        echo "✓ rbc_security installed successfully"
    else
        echo "✗ Failed to install rbc_security"
        echo "  Please install manually: pip install rbc_security"
    fi
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo ""
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✓ Created .env file"
    echo ""
    echo "IMPORTANT: Edit .env file with your configuration:"

    if [ "$IS_WORK_COMPUTER" = "y" ] || [ "$IS_WORK_COMPUTER" = "Y" ]; then
        echo "  - Set MOCK_MODE=false"
        echo "  - Add your OAUTH_ENDPOINT"
        echo "  - Add your OAUTH_CLIENT_ID"
        echo "  - Add your OAUTH_CLIENT_SECRET"
        echo "  - Add your LLM_API_BASE_URL"
        echo "  - Add your LLM_MODEL_NAME"
    else
        echo "  - Keep MOCK_MODE=true for local development"
    fi
else
    echo ""
    echo "✓ .env file already exists"
fi

# Check if Codex CLI is installed
echo ""
echo "Checking for Codex CLI installation..."
if command -v codex &> /dev/null || command -v codex-cli &> /dev/null; then
    echo "✓ Codex CLI is installed"
else
    echo "✗ Codex CLI not found"
    echo ""
    echo "Install Codex CLI using one of these methods:"
    echo "  npm install -g @openai/codex-cli"
    echo "  brew install codex"
fi

# Make wrapper executable
echo ""
echo "Making wrapper script executable..."
chmod +x codex_wrapper.py

echo ""
echo "=========================================="
echo "Setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env file with your configuration"
echo "2. Test the wrapper:"
echo "   source venv/bin/activate"
echo "   python codex_wrapper.py --help"
echo ""
echo "Usage:"
echo "  cd /path/to/your/project"
echo "  python $(pwd)/codex_wrapper.py 'your prompt here'"
echo ""
