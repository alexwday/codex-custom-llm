# Quick Start Guide

Get up and running in 3 steps:

## 1. Install

```bash
pip install -r requirements.txt
```

## 2. Configure

Copy `.env.example` to `.env` and fill in your settings:

```bash
cp .env.example .env
```

For local testing:
```bash
MOCK_MODE=true
LLM_API_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-4
MAX_TOKENS=4096
```

For enterprise:
```bash
MOCK_MODE=false
LLM_API_BASE_URL=https://your-llm-endpoint.com/v1
LLM_MODEL_NAME=gpt-4-internal
MAX_TOKENS=4096
TOKEN_REFRESH_INTERVAL=900
OAUTH_ENDPOINT=https://your-oauth-endpoint.com/token
OAUTH_CLIENT_ID=your-client-id
OAUTH_CLIENT_SECRET=your-client-secret
```

## 3. Run

```bash
python codex_dashboard.py
```

The dashboard will open automatically at http://localhost:8888

## Using the Dashboard

1. **Check Status** - Verify OAuth token and API settings are configured
2. **Enter Project Path** - Type the full path to your project directory
3. **Add Prompt (Optional)** - Enter an initial prompt for Codex
4. **Click Launch** - Start Codex with the proxy configured
5. **Monitor Activity** - Watch all API requests and responses in real-time

## What You'll See

- **Status**: OAuth token status, uptime, Codex state
- **API Stats**: Request/response counts, timing, errors
- **Config**: All your environment settings
- **Recent Requests**: Live view of API calls with response details
- **Activity Log**: Detailed event timeline

## Tips

- Logs are saved to `~/.codex/logs/proxy_requests_*.log`
- Increase `MAX_TOKENS` if responses are cut off
- Use `MOCK_MODE=true` for testing without enterprise setup
- The dashboard auto-refreshes every second

## Troubleshooting

**Port in use?**
Edit `codex_dashboard.py` and change the port numbers.

**OAuth fails?**
Check your credentials and network connectivity. Use `MOCK_MODE=true` to test without OAuth.

**Codex not found?**
Install it: `npm install -g @anthropic-ai/codex`

For more details, see [README.md](README.md)
