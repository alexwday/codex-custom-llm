# Usage Guide

## Quick Start

### First Time Setup

1. **Install dependencies:**
   ```bash
   ./setup.sh
   ```
   OR manually:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   nano .env  # Edit with your settings
   ```

3. **Test the setup:**
   ```bash
   python test_wrapper.py
   ```

### Using the Wrapper

The wrapper is designed to be called from YOUR project directory:

```bash
# Navigate to your project
cd ~/my-awesome-project

# Call the wrapper (adjust path as needed)
python /path/to/codex-custom-llm/codex_wrapper.py "help me refactor this code"
```

## Usage Patterns

### Pattern 1: Direct Invocation

Best for: Testing, one-off usage

```bash
cd /path/to/your/project
python /path/to/codex-custom-llm/codex_wrapper.py "analyze the codebase structure"
```

### Pattern 2: Shell Alias

Best for: Regular use, convenience

Add to `~/.bashrc` or `~/.zshrc`:
```bash
alias codex="python /path/to/codex-custom-llm/codex_wrapper.py"
```

Then use from any project:
```bash
cd ~/my-project
codex "fix the bug in main.py"
```

### Pattern 3: Shell Function

Best for: Advanced usage, with environment activation

Add to `~/.bashrc` or `~/.zshrc`:
```bash
codex() {
    # Activate the wrapper's venv
    source /path/to/codex-custom-llm/venv/bin/activate

    # Run the wrapper
    python /path/to/codex-custom-llm/codex_wrapper.py "$@"

    # Deactivate venv
    deactivate
}
```

Then use from any project:
```bash
cd ~/my-project
codex "implement user authentication"
```

### Pattern 4: Add to PATH

Best for: System-wide availability

```bash
# Add to ~/.bashrc or ~/.zshrc
export PATH="$PATH:/path/to/codex-custom-llm"

# Create a symlink or wrapper script
ln -s /path/to/codex-custom-llm/codex_wrapper.py /path/to/codex-custom-llm/codex
```

Then use from anywhere:
```bash
cd ~/my-project
codex "write unit tests"
```

## Example Commands

### Code Analysis
```bash
codex "explain what this module does"
codex "find potential bugs in auth.py"
codex "review the architecture"
```

### Code Generation
```bash
codex "create a new User model with email and password fields"
codex "add error handling to the API endpoints"
codex "implement a cache layer for database queries"
```

### Refactoring
```bash
codex "refactor this function to be more readable"
codex "extract this logic into a separate module"
codex "improve the performance of this loop"
```

### Testing
```bash
codex "write unit tests for the UserService class"
codex "add integration tests for the API"
codex "create test fixtures for the database"
```

### Documentation
```bash
codex "add docstrings to all functions"
codex "create a README for this module"
codex "document the API endpoints"
```

## Working Directory Behavior

**Critical**: The wrapper runs Codex in your current working directory (where you run the command), NOT in the wrapper's directory.

### Correct ✓
```bash
cd ~/my-project              # Your project
python ~/tools/codex-custom-llm/codex_wrapper.py "help"
# Codex operates on ~/my-project
```

### Incorrect ✗
```bash
cd ~/tools/codex-custom-llm  # Wrapper directory
python codex_wrapper.py "help"
# Codex operates on the wrapper directory (not what you want!)
```

## Environment Modes

### Mock Mode (Local Development)

Use on personal computer without enterprise dependencies:

**.env:**
```bash
MOCK_MODE=true
LLM_API_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-4
```

**What happens:**
- No SSL setup (rbc_security not required)
- Mock OAuth tokens
- Can test wrapper logic

### Production Mode (Work Computer)

Use on work computer with real endpoints:

**.env:**
```bash
MOCK_MODE=false
OAUTH_ENDPOINT=https://auth.company.com/oauth/token
OAUTH_CLIENT_ID=your-client-id
OAUTH_CLIENT_SECRET=your-secret
LLM_API_BASE_URL=https://llm.company.com/v1
LLM_MODEL_NAME=gpt-4-internal
```

**What happens:**
- SSL setup via rbc_security
- Real OAuth tokens (auto-refreshed every 15 min)
- Connects to enterprise LLM

## Troubleshooting

### "Codex CLI not found"

Install Codex CLI:
```bash
npm install -g @openai/codex-cli
# OR
brew install codex
```

### "rbc_security not found"

Two options:
1. **On work computer**: Install the package
   ```bash
   pip install rbc_security
   ```

2. **On personal computer**: Enable mock mode
   ```bash
   # In .env
   MOCK_MODE=true
   ```

### "OAuth token failed"

Check your `.env` file:
- Verify `OAUTH_ENDPOINT` is correct
- Verify `OAUTH_CLIENT_ID` and `OAUTH_CLIENT_SECRET` are correct
- Ensure you're on the work network (VPN if needed)
- Check the console logs for detailed error messages

### "SSL certificate error"

This usually means:
- `rbc_security` is not installed (install it or use mock mode)
- `enable_certs()` failed (check rbc_security documentation)
- You're not on the work network

### "Model not found" or "Invalid API response"

Check:
- `LLM_API_BASE_URL` is correct
- `LLM_MODEL_NAME` matches what your API expects
- Review `~/.codex/config.toml` to see the generated config
- Test the API endpoint directly with curl

### Codex operates on wrong directory

Make sure you're in your project directory when calling the wrapper:
```bash
pwd  # Should show your project directory
python /path/to/wrapper/codex_wrapper.py "your command"
```

## Advanced Usage

### Verbose Monitoring Mode

**Problem:** You want to see what the wrapper is doing in real-time.

**Solution:** Enable verbose mode to monitor all wrapper activity:

**.env:**
```bash
VERBOSE_MODE=true
```

**What you'll see:**
- OAuth token fetch and refresh activity
- Configuration generation details
- Environment variables being set
- SSL certificate setup
- Real-time logging of wrapper operations
- Token refresh notifications every 15 minutes

**Example output:**
```
2025-10-15 15:44:43 - __main__ - INFO - Initializing Codex wrapper (mock_mode=True, verbose_mode=True)
2025-10-15 15:44:43 - __main__ - INFO - Mock mode: Skipping SSL certificate setup
2025-10-15 15:44:43 - __main__ - INFO - Fetching initial OAuth token...
2025-10-15 15:44:43 - oauth_manager - INFO - Mock mode: Using mock OAuth token
2025-10-15 15:44:43 - __main__ - DEBUG - ============================================================
2025-10-15 15:44:43 - __main__ - DEBUG - VERBOSE MODE: Monitoring API calls
2025-10-15 15:44:43 - __main__ - DEBUG - ============================================================
2025-10-15 15:44:43 - __main__ - DEBUG - Environment variables set:
2025-10-15 15:44:43 - __main__ - DEBUG -   CUSTOM_LLM_API_KEY: mock_token_for_loca...
2025-10-15 15:44:43 - __main__ - DEBUG -   Current directory: /Users/you/my-project
```

### Increasing Max Tokens

**Problem:** Responses are being cut off because your endpoint has a low default limit.

**Solution:** Set MAX_TOKENS to increase response length:

**.env:**
```bash
MAX_TOKENS=4096   # or 8192, 16384, etc.
```

Your model supports up to 256000 input tokens, so you can set this quite high.

**Verify it's working:**
```bash
cat ~/.codex/config.toml
# You should see: max_tokens = 4096
```

### Custom Token Refresh Interval

Default is 15 minutes (900 seconds). To change:

**.env:**
```bash
TOKEN_REFRESH_INTERVAL=600  # 10 minutes
```

### Custom Wire API

If your LLM uses a different API format:

**.env:**
```bash
WIRE_API=responses  # or 'chat' (default)
```

### Query Parameters (Azure-style APIs)

For APIs that need query parameters:

**.env:**
```bash
QUERY_PARAMS=api-version=2024-01-01
```

### Viewing the Generated Config

```bash
cat ~/.codex/config.toml
```

This shows the configuration that Codex is using.

## Tips and Best Practices

1. **Always test with mock mode first** before using on work computer
2. **Use the test script** (`python test_wrapper.py`) to verify setup
3. **Keep the wrapper updated** - pull latest changes regularly
4. **Don't commit `.env`** - it contains secrets
5. **Use descriptive prompts** - better prompts = better results
6. **Check the logs** - wrapper prints helpful debugging info
7. **Set up an alias** - makes usage much more convenient

## Getting Help

Run without arguments to see usage:
```bash
python codex_wrapper.py
```

Run tests to verify setup:
```bash
python test_wrapper.py
```

Check the logs - the wrapper prints detailed information about:
- SSL setup
- OAuth token fetching
- Config generation
- Codex launching
