# Quick Start Guide - Work Computer

This is a condensed guide for getting up and running on your work computer.

## Prerequisites

- Access to internal OAuth endpoint
- Access to internal LLM API endpoint
- OAuth client ID and client secret
- Network access (VPN if needed)

## Setup Steps

### 1. Clone the repository
```bash
cd ~/Projects  # or wherever you keep code
git clone https://github.com/alexwday/codex-custom-llm.git
cd codex-custom-llm
```

### 2. Run setup script
```bash
./setup.sh
# Answer 'y' when asked if this is a work computer
```

This will:
- Create Python virtual environment
- Install dependencies
- Install `rbc_security` package
- Create `.env` file from template

### 3. Configure environment

Edit the `.env` file with your actual values:

```bash
nano .env  # or vim, code, etc.
```

Required changes:
```bash
MOCK_MODE=false

# OAuth Configuration (get these from your team)
OAUTH_ENDPOINT=https://your-oauth-endpoint.company.com/oauth/token
OAUTH_CLIENT_ID=your-client-id-here
OAUTH_CLIENT_SECRET=your-secret-here

# LLM API Configuration (get these from your team)
LLM_API_BASE_URL=https://your-llm-api.company.com/v1
LLM_MODEL_NAME=gpt-4-internal  # or whatever model name

# Token refresh (15 minutes is good default)
TOKEN_REFRESH_INTERVAL=900

# Wire API format (usually 'chat')
WIRE_API=chat
```

### 4. Install Codex CLI

```bash
npm install -g @openai/codex-cli
# OR
brew install codex
```

### 5. Verify setup

```bash
source venv/bin/activate
python test_wrapper.py
```

You should see all checks pass ✓

### 6. Set up shell alias (optional but recommended)

Add to `~/.bashrc` or `~/.zshrc`:
```bash
alias codex="python ~/Projects/codex-custom-llm/codex_wrapper.py"
```

Then:
```bash
source ~/.bashrc  # or source ~/.zshrc
```

## Usage

### With alias (if you set it up):
```bash
cd ~/your-actual-project
codex "help me refactor this code"
```

### Without alias:
```bash
cd ~/your-actual-project
python ~/Projects/codex-custom-llm/codex_wrapper.py "analyze this codebase"
```

## Troubleshooting

### rbc_security import error
```bash
# Make sure you're in the venv
source ~/Projects/codex-custom-llm/venv/bin/activate

# Install rbc_security
pip install rbc_security
```

### OAuth token errors
- Verify credentials in `.env`
- Check you're on the corporate network (VPN if needed)
- Test OAuth endpoint with curl:
  ```bash
  curl -X POST https://your-oauth-endpoint/oauth/token \
    -d "grant_type=client_credentials" \
    -d "client_id=your-id" \
    -d "client_secret=your-secret"
  ```

### SSL certificate errors
- Ensure `rbc_security` is installed in the venv
- Check with your team about certificate setup
- Look at wrapper logs for details

### Codex not found
```bash
# Check if installed
which codex

# Install if needed
npm install -g @openai/codex-cli
```

### Wrong project directory
Remember: Run the wrapper FROM your project directory!
```bash
# ✓ Correct
cd ~/my-project
python ~/Projects/codex-custom-llm/codex_wrapper.py "help"

# ✗ Wrong
cd ~/Projects/codex-custom-llm
python codex_wrapper.py "help"
```

## Getting Help

1. **Read the logs**: The wrapper prints detailed information about what it's doing
2. **Run tests**: `python test_wrapper.py` to diagnose issues
3. **Check docs**:
   - [README.md](README.md) - Overview and setup
   - [USAGE.md](USAGE.md) - Detailed usage guide
   - [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - Architecture details

## Quick Reference

```bash
# Activate venv (if needed)
source ~/Projects/codex-custom-llm/venv/bin/activate

# Navigate to your project
cd ~/my-actual-project

# Use Codex (with alias)
codex "your prompt here"

# Use Codex (without alias)
python ~/Projects/codex-custom-llm/codex_wrapper.py "your prompt here"

# Check wrapper status
python ~/Projects/codex-custom-llm/test_wrapper.py

# View generated config
cat ~/.codex/config.toml
```

## Tips

- Keep the wrapper repo up to date: `git pull` regularly
- Check logs if something isn't working
- Token refresh runs automatically in the background
- You don't need to restart Codex when tokens refresh
- The wrapper inherits your current directory

## Security Reminders

- Never commit your `.env` file (it's in `.gitignore`)
- Keep your OAuth credentials secure
- Don't share your token or credentials
- If you suspect credentials are compromised, rotate them immediately

## Support

If you encounter issues specific to:
- **OAuth/SSL**: Contact your security team
- **LLM API**: Contact your AI/ML team
- **Wrapper itself**: Check GitHub issues or update to latest version

---

That's it! You should now be able to use Codex with your enterprise LLM endpoint. 🚀
