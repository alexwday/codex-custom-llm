# Troubleshooting Guide

## Codex Stopping Mid-Task

**Symptom:** Codex stops in the middle of a task (like reading files or analyzing code) without finishing.

**Possible Causes:**

### 1. Token Limit Reached
Even though you set `MAX_TOKENS`, Codex might be hitting other limits:

**Solution:**
- Increase `MAX_TOKENS` further (try 8192, 16384, or even higher)
- Your model supports up to 256000 input tokens
- Check the generated config:
  ```bash
  cat ~/.codex/config.toml
  # Look for: max_tokens = ?
  ```

### 2. Streaming Timeout
The LLM might be taking too long to respond, causing Codex to timeout.

**Solution:**
- This is usually a Codex CLI issue, not the wrapper
- Try breaking your request into smaller chunks
- Ask Codex to "continue" after it stops

### 3. API Rate Limiting
Your enterprise endpoint might be rate-limiting requests.

**Solution:**
- Use `--monitor` flag to see API activity:
  ```bash
  python codex_wrapper.py --monitor "your prompt"
  ```
- Check if OAuth tokens are refreshing properly
- Contact your API team about rate limits

### 4. Connection Issues
Network interruptions or SSL problems.

**Solution:**
- Check SSL certificates are set up correctly
- Verify network connectivity to your endpoint
- Use `VERBOSE_MODE=true` to see detailed logs

## How to Debug with Monitor

The monitoring dashboard shows you exactly what's happening:

```bash
# Launch with monitoring
python codex_wrapper.py --monitor "analyze this codebase"
```

This will:
1. Open http://localhost:8888 in your browser
2. Show real-time events (OAuth tokens, config generation, etc.)
3. Display Codex status
4. Log all wrapper activity

**What to look for:**
- **OAuth Token Status**: Should be "Active"
- **Token Refreshes**: Should happen every 15 minutes
- **Codex Status**: Should show "Running" while active
- **Activity Log**: Shows all events in real-time

## Common Issues

### "Codex CLI not found"
```bash
# Install Codex
npm install -g @openai/codex-cli
# OR
brew install codex
```

### "rbc_security not found" (Work Computer)
```bash
# Activate your venv
source ~/Projects/codex-custom-llm/venv/bin/activate

# Install rbc_security
pip install rbc_security
```

### OAuth Token Failures
Check your `.env` file:
```bash
MOCK_MODE=false  # Must be false on work computer
OAUTH_ENDPOINT=https://your-endpoint...  # Correct endpoint
OAUTH_CLIENT_ID=your-id  # Correct ID
OAUTH_CLIENT_SECRET=your-secret  # Correct secret
```

### Responses Still Cut Off
1. **Check current max_tokens:**
   ```bash
   cat ~/.codex/config.toml | grep max_tokens
   ```

2. **Increase it:**
   ```bash
   # In .env
   MAX_TOKENS=16384  # or higher
   ```

3. **Regenerate config:**
   ```bash
   python codex_wrapper.py --help  # This regenerates the config
   ```

4. **Verify the change:**
   ```bash
   cat ~/.codex/config.toml | grep max_tokens
   # Should show your new value
   ```

### Monitor Dashboard Won't Load
```bash
# Check if port 8888 is in use
lsof -i :8888

# Kill any process using port 8888
kill -9 <PID>

# Try again
python codex_wrapper.py --monitor "your prompt"
```

### Token Refresh Not Working
Enable verbose mode to see what's happening:

```bash
# In .env
VERBOSE_MODE=true
```

Then run normally:
```bash
python codex_wrapper.py "your prompt"
```

Watch the logs for:
```
Refreshing OAuth token...
OAuth token refreshed successfully
```

If you see failures, check:
- OAuth credentials in `.env`
- Network connectivity
- VPN connection (if required)

## Codex Behavior Issues

### Codex Stops Without Error
This is usually NOT a wrapper issue - it's Codex CLI behavior.

**Try:**
1. Just type "continue" to resume
2. Break your task into smaller requests
3. Use more specific prompts

### Codex Using Wrong Directory
Make sure you're calling the wrapper from your project directory:

```bash
# ✓ Correct
cd ~/my-project
python ~/path/to/codex_wrapper.py "your prompt"

# ✗ Wrong
cd ~/path/to/codex_wrapper
python codex_wrapper.py "your prompt"
```

### Codex Not Using Enterprise LLM
Check the generated config:

```bash
cat ~/.codex/config.toml
```

Should look like:
```toml
model = "gpt-4-internal"
model_provider = "enterprise_llm"

[model_providers.enterprise_llm]
name = "Enterprise LLM"
base_url = "https://your-llm-endpoint.com/v1"
env_key = "CUSTOM_LLM_API_KEY"
wire_api = "chat"
max_tokens = 4096
```

If it's wrong:
1. Check your `.env` file
2. Run the wrapper again (it regenerates the config)

## Getting More Help

### 1. Enable Monitoring
```bash
python codex_wrapper.py --monitor "your prompt"
```

Visit http://localhost:8888 to see real-time activity.

### 2. Enable Verbose Mode
```bash
# In .env
VERBOSE_MODE=true
```

This shows detailed logs in the terminal.

### 3. Check Logs
The wrapper prints detailed information about:
- SSL certificate setup
- OAuth token fetching
- Configuration generation
- Codex launching

Look for error messages or warnings.

### 4. Test Individual Components

**Test OAuth:**
```python
python -c "from oauth_manager import OAuthManager; import os; from dotenv import load_dotenv; load_dotenv(); m = OAuthManager(os.getenv('OAUTH_ENDPOINT'), os.getenv('OAUTH_CLIENT_ID'), os.getenv('OAUTH_CLIENT_SECRET'), False); print(m.get_token()[:50])"
```

**Test Config Generation:**
```python
python -c "from config_generator import generate_codex_config; generate_codex_config({'base_url': 'https://test.com', 'model_name': 'test', 'env_key': 'TEST', 'wire_api': 'chat', 'max_tokens': 4096}); print('Config generated')"
```

### 5. Contact Your Team
If wrapper issues persist:
- **SSL/Certificates**: Contact security team
- **OAuth**: Contact auth team
- **LLM API**: Contact AI/ML team
- **Wrapper itself**: Check GitHub issues or update to latest version

## Quick Diagnostic Checklist

Run through this checklist:

- [ ] `.env` file configured correctly
- [ ] `MOCK_MODE=false` on work computer
- [ ] OAuth credentials are correct
- [ ] `rbc_security` installed (work computer)
- [ ] Codex CLI installed (`which codex`)
- [ ] Can access OAuth endpoint (VPN?)
- [ ] Can access LLM API endpoint
- [ ] `MAX_TOKENS` set appropriately (4096+)
- [ ] Config file looks correct (`cat ~/.codex/config.toml`)
- [ ] Running from project directory (not wrapper directory)
- [ ] Test script passes (`python test_wrapper.py`)

If all checked and still having issues, enable monitor mode and verbose logging to gather more information.
