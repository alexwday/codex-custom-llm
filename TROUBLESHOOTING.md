# Troubleshooting Guide

## ⚠️ IMPORTANT: Monitor Limitations

**The monitor dashboard only shows WRAPPER activity**, not what Codex is doing.

Once Codex launches, the wrapper just waits for it to finish. The monitor shows:
- ✅ OAuth token refresh
- ✅ SSL setup
- ✅ Configuration changes
- ❌ What Codex is doing internally
- ❌ Codex API calls
- ❌ Why Codex stopped

**If Codex is having problems, the monitor won't show it.**

## Codex Stopping Mid-Task

**Symptom:** Codex stops in the middle of a task (like reading files or analyzing code) without finishing.

**What you described:**
1. Send message → Codex shows "loading"
2. No response appears
3. Goes back to prompt without doing anything
4. OR starts doing something then stops partway through

**This is a Codex CLI issue, NOT a wrapper issue.**

The wrapper's job is done once Codex launches. After that, Codex communicates directly with your endpoint.

---

## Step 1: Test Your Endpoint Directly

**Run this diagnostic script:**
```bash
python test_endpoint.py
```

This bypasses Codex and tests your endpoint directly. It will tell you if:
- ✅ Your endpoint is working
- ✅ Responses are complete
- ✅ MAX_TOKENS is being respected
- ❌ Endpoint is timing out
- ❌ Responses are getting cut off
- ❌ OAuth is failing

**If the test fails**, your endpoint has problems. Fix those first.

**If the test passes**, the issue is with Codex CLI, not your setup.

---

## Step 2: Common Codex CLI Issues

### Issue 1: Codex CLI Timeout
Codex CLI has internal timeouts that might be too short for your endpoint.

**Solution:**
```bash
# Check if your endpoint is slow
time curl -X POST https://your-endpoint/v1/chat/completions \
  -H "Authorization: Bearer $token" \
  -H "Content-Type: application/json" \
  -d '{"model":"your-model","messages":[{"role":"user","content":"hi"}],"max_tokens":100}'

# If it takes >10 seconds, Codex might timeout
```

### Issue 2: Streaming vs Non-Streaming
Your endpoint might not properly support streaming.

**Try this test:**
```bash
# In your project directory
codex --config model_providers.enterprise_llm.stream=false "test prompt"
```

If that works better, your endpoint has streaming issues.

### Issue 3: Response Format
Your endpoint might be returning responses in a format Codex doesn't expect.

**Check your wire_api setting:**
```bash
cat ~/.codex/config.toml | grep wire_api
# Should be: wire_api = "chat"
```

If it's wrong, update `.env`:
```bash
WIRE_API=chat  # or 'responses' depending on your API
```

### Issue 4: Context Window
Even with MAX_TOKENS high, the INPUT context might be too large.

**Solution:**
- Ask shorter questions
- Don't ask Codex to analyze huge files
- Break tasks into smaller chunks

---

## Step 3: Increase MAX_TOKENS (If Not Already Done)

**Even though you set it, verify it's working:**

```bash
# Check current value
cat ~/.codex/config.toml | grep max_tokens

# Should show something like: max_tokens = 4096
```

**If it's not there or too low:**
```bash
# In .env file
MAX_TOKENS=16384  # Try 8192, 16384, or 32768

# Then run wrapper again to regenerate config
python codex_wrapper.py --help
```

---

## Step 4: Codex CLI Debugging

**Enable Codex debug mode:**
```bash
export RUST_LOG=debug
python codex_wrapper.py "your prompt"
```

Look for error messages from Codex CLI itself.

**Check Codex version:**
```bash
codex --version

# Update if needed
npm update -g @openai/codex-cli
```

---

## What Each Tool Does

### The Wrapper (`codex_wrapper.py`)
**What it does:**
- ✅ Sets up SSL certificates
- ✅ Fetches OAuth token
- ✅ Refreshes token every 15 minutes
- ✅ Generates Codex config
- ✅ Launches Codex subprocess

**What it does NOT do:**
- ❌ Handle Codex's communication with the endpoint
- ❌ Control how Codex processes responses
- ❌ See what Codex is doing internally

Once Codex launches, it's on its own. The wrapper just waits for it to exit.

### The Monitor (`--monitor`)
**What it shows:**
- ✅ Wrapper initialization
- ✅ OAuth token status
- ✅ Configuration generation
- ✅ When Codex starts/stops

**What it does NOT show:**
- ❌ Codex API calls
- ❌ Why Codex stopped
- ❌ Codex's internal state

The monitor is for debugging THE WRAPPER, not Codex CLI.

### The Diagnostic Script (`test_endpoint.py`)
**What it does:**
- ✅ Tests endpoint directly (bypasses Codex)
- ✅ Shows if responses are complete
- ✅ Measures response time
- ✅ Checks token limits
- ✅ Validates OAuth

Use this to rule out endpoint problems.

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
