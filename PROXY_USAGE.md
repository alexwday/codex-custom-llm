# Proxy Server Usage Guide

## What is the Proxy?

The proxy server sits between Codex and your real LLM endpoint:

```
Codex CLI → localhost:8889 (proxy) → Your Real Endpoint → Response → Codex
```

**Why use it?**
- See EVERY request Codex makes
- See EVERY response your endpoint returns
- Log everything to a file
- Find out exactly where/why Codex stops

## Setup

### Step 1: Start the Proxy Server

**Terminal 1:**
```bash
cd ~/Projects/codex-custom-llm
python proxy_server.py
```

You'll see:
```
==============================================================================
  🔄 LLM API PROXY SERVER
==============================================================================
  Proxy: http://localhost:8889
  Real Endpoint: https://your-endpoint.com/v1
  Log File: /Users/you/.codex/logs/proxy_requests_20251015_163000.log
==============================================================================

  ✅ Proxy server is running...
     All API calls will be logged here in real-time.
     Press Ctrl+C to stop
```

**Keep this terminal open!**

### Step 2: Enable Proxy Mode

Edit `.env`:
```bash
PROXY_MODE=true
```

### Step 3: Run Codex Wrapper

**Terminal 2:**
```bash
cd ~/your-project
python ~/Projects/codex-custom-llm/codex_wrapper.py --monitor "test prompt"
```

### Step 4: Watch the Logs

**Terminal 1** (proxy) will show:
```
================================================================================
REQUEST #1 at 16:30:45
================================================================================
Model: gpt-4-internal
Max Tokens: 4096
Streaming: False
Messages: 2
Last Message: Please analyze this codebase...

Full Request:
{
  "model": "gpt-4-internal",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant"},
    {"role": "user", "content": "Please analyze this codebase"}
  ],
  "max_tokens": 4096,
  "stream": false
}

[REQUEST #1] Forwarding to https://your-endpoint.com/v1/chat/completions...

RESPONSE #1 at 16:30:47 (took 2.34s)
================================================================================
Finish Reason: stop
Content Length: 1234 characters
Prompt Tokens: 45
Completion Tokens: 156
Total Tokens: 201

Full Response:
{
  "id": "chatcmpl-123",
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "Based on my analysis of the codebase..."
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 45,
    "completion_tokens": 156,
    "total_tokens": 201
  }
}
```

## What You'll See

### Normal Request/Response
```
REQUEST #1 → Your prompt
RESPONSE #1 → Full response, finish_reason: stop
```

### Timeout
```
REQUEST #2 → Your prompt
❌ ERROR #2: Request timed out after 120 seconds
```

### Incomplete Response
```
REQUEST #3 → Your prompt
RESPONSE #3 → Partial response
⚠️  WARNING: Response was cut off! (finish_reason=length)
```

### API Error
```
REQUEST #4 → Your prompt
❌ ERROR #4: HTTP 429: Too Many Requests
```

### Connection Error
```
REQUEST #5 → Your prompt
❌ ERROR #5: Connection refused
```

## Troubleshooting with Proxy

### Scenario 1: Codex Sends Request, No Response

**Proxy shows:**
```
REQUEST #1 → Sent
[waiting...]
❌ ERROR #1: Request timed out after 120 seconds
```

**Diagnosis:** Your endpoint is too slow (>2 minutes)

**Solution:**
- Contact API team about slow responses
- Try smaller requests
- Check if endpoint is overloaded

### Scenario 2: Response Cut Off

**Proxy shows:**
```
RESPONSE #1 → finish_reason: length
⚠️  WARNING: Response was cut off!
```

**Diagnosis:** Hit max_tokens limit

**Solution:**
```bash
# In .env
MAX_TOKENS=16384  # Increase
```

### Scenario 3: No Requests at All

**Proxy shows:** Nothing

**Diagnosis:** Codex never made a request

**Solution:**
- Check Codex CLI logs (with --monitor)
- Codex might have crashed before making request
- Check Codex configuration

### Scenario 4: Requests Work, But Codex Freezes

**Proxy shows:**
```
REQUEST #1 → Success
RESPONSE #1 → Full response, finish_reason: stop
REQUEST #2 → Success
RESPONSE #2 → Full response, finish_reason: stop
REQUEST #3 → Success
RESPONSE #3 → Partial response, finish_reason: stop
[then nothing...]
```

**Diagnosis:** Codex CLI bug - stopped processing responses

**Solution:**
- Update Codex CLI
- Check Codex version
- Report bug to Codex team

## Log Files

All requests/responses are saved to:
```
~/.codex/logs/proxy_requests_TIMESTAMP.log
```

You can review this after Codex stops to see:
- How many requests were made
- If responses were complete
- If any errors occurred
- Timing information

## Disabling Proxy

When you're done debugging:

```bash
# In .env
PROXY_MODE=false
```

Then stop the proxy server (Ctrl+C in Terminal 1).

## Proxy + Monitor

Use both together for maximum visibility:

**Terminal 1:** Proxy server
```bash
python proxy_server.py
```

**Terminal 2:** Codex with monitor
```bash
python codex_wrapper.py --monitor "your prompt"
```

**Browser:** Monitor dashboard
```
http://localhost:8888
```

Now you see:
- **Terminal 1**: All API requests/responses
- **Terminal 2**: Codex errors
- **Browser**: Wrapper activity
- **Log files**: Everything persisted

This gives you COMPLETE visibility into what's happening!

## Example Session

```bash
# Terminal 1
cd ~/Projects/codex-custom-llm
python proxy_server.py

# Terminal 2
cd ~/your-work-project
nano .env  # Set PROXY_MODE=true
python ~/Projects/codex-custom-llm/codex_wrapper.py --monitor "analyze main.py"

# Watch Terminal 1 for requests
# Watch Terminal 2 for Codex errors
# Open http://localhost:8888 for dashboard

# When done
# Terminal 2: Ctrl+C
# Terminal 1: Ctrl+C
# Set PROXY_MODE=false in .env
```

## What This Solves

Before: "Codex stops, no errors, no idea why"

After: "Codex stopped because:"
- ✅ Request #5 timed out after 120s
- ✅ Response #3 was cut off (hit max_tokens)
- ✅ Request #7 got HTTP 429 (rate limited)
- ✅ Request #10 never got a response
- ✅ etc.

**Now you'll FINALLY know what's wrong!**
