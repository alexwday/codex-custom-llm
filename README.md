# Codex Proxy Dashboard

A unified control center for running OpenAI's Codex CLI with enterprise LLM endpoints. Everything you need in one Python script with a beautiful web dashboard.

## Features

- **Integrated API Proxy** - Intercepts and logs all API calls between Codex and your endpoint
- **OAuth2 Management** - Automatic token fetching and refresh with status display
- **Real-time Monitoring** - Live dashboard showing all requests, responses, and events
- **Project Launcher** - Select any project folder and launch Codex with one click
- **Request/Response Logging** - Complete visibility into API communication
- **Configuration Display** - See all your settings at a glance
- **SSL Certificate Support** - Works with enterprise SSL requirements (via rbc_security)

## Quick Start

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**

   Create a `.env` file:
   ```bash
   # Enterprise settings
   LLM_API_BASE_URL=https://your-llm-endpoint.com/v1
   LLM_MODEL_NAME=gpt-4-internal
   MAX_TOKENS=4096

   OAUTH_ENDPOINT=https://your-oauth-endpoint.com/token
   OAUTH_CLIENT_ID=your-client-id
   OAUTH_CLIENT_SECRET=your-client-secret

   # Token refresh interval (seconds)
   TOKEN_REFRESH_INTERVAL=900

   # For local testing
   MOCK_MODE=false
   ```

3. **Run the Dashboard**
   ```bash
   python codex_dashboard.py
   ```

4. **Open Browser**

   The dashboard will automatically open at http://localhost:8888

## Usage

### Dashboard Overview

The dashboard shows:
- **Status Card**: Uptime, OAuth token status, Codex status
- **API Statistics**: Request/response counts, errors, timing
- **Configuration**: All your environment variables and settings
- **Launch Section**: Enter a project directory and launch Codex
- **Recent API Requests**: Real-time view of all API calls
- **Activity Log**: Detailed event log with timestamps

### Launching Codex

1. In the dashboard, enter your project directory path
2. (Optional) Enter an initial prompt
3. Click "Launch Codex"
4. Codex will start in that directory with the proxy configured
5. All API calls will appear in the dashboard in real-time

### How It Works

```
┌─────────────────┐
│  Codex CLI      │
│  (your project) │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  Dashboard      │ ← http://localhost:8888 (Web UI)
│  Proxy Server   │ ← http://localhost:8889 (API Proxy)
└────────┬────────┘
         │
         ↓ (with OAuth token)
┌─────────────────┐
│  Enterprise     │
│  LLM Endpoint   │
└─────────────────┘
```

The dashboard:
1. Fetches OAuth tokens automatically
2. Generates Codex config pointing to the proxy
3. Launches Codex with the config
4. Intercepts all API calls through the proxy
5. Logs everything to the dashboard and log files

### Configuration

All settings are controlled via environment variables in `.env`:

| Variable | Description | Example |
|----------|-------------|---------|
| `LLM_API_BASE_URL` | Your LLM endpoint | `https://api.example.com/v1` |
| `LLM_MODEL_NAME` | Model to use | `gpt-4-internal` |
| `MAX_TOKENS` | Max tokens per response | `4096` |
| `OAUTH_ENDPOINT` | OAuth token endpoint | `https://oauth.example.com/token` |
| `OAUTH_CLIENT_ID` | OAuth client ID | Your client ID |
| `OAUTH_CLIENT_SECRET` | OAuth client secret | Your secret |
| `TOKEN_REFRESH_INTERVAL` | Token refresh interval (seconds) | `900` (15 min) |
| `MOCK_MODE` | Use mock tokens (testing) | `true` or `false` |

### Logs

All API requests and responses are logged to:
```
~/.codex/logs/proxy_requests_YYYYMMDD_HHMMSS.log
```

The log file contains:
- Full request bodies (model, messages, tokens)
- Full response bodies (content, finish_reason, usage)
- Timestamps and request IDs
- Error messages and warnings

### Mock Mode

For local testing without enterprise dependencies:

```bash
MOCK_MODE=true
LLM_API_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-4
```

Mock mode will:
- Skip OAuth token fetching (use fake token)
- Skip SSL certificate setup
- Still run the proxy and dashboard for testing

## Troubleshooting

### "Failed to get OAuth token"

- Check your `OAUTH_ENDPOINT`, `OAUTH_CLIENT_ID`, and `OAUTH_CLIENT_SECRET`
- Verify network connectivity to the OAuth endpoint
- Check if SSL certificates are required (install rbc_security)

### "Codex not found"

Make sure Codex CLI is installed:
```bash
npm install -g @anthropic-ai/codex
```

### Response Cut Off

If responses are being truncated, increase `MAX_TOKENS`:
```bash
MAX_TOKENS=8192
```

### Port Already in Use

If ports 8888 or 8889 are in use, edit `codex_dashboard.py`:
```python
self.proxy_port = 8889      # Change this
self.dashboard_port = 8888  # And this
```

## Project Structure

```
codex-custom-llm/
├── codex_dashboard.py    # Main script (run this)
├── requirements.txt      # Python dependencies
├── .env                  # Your configuration
├── .env.example          # Example configuration
└── README.md             # This file
```

## Enterprise Setup

For work computers with enterprise dependencies:

1. Install rbc_security package (if required):
   ```bash
   pip install rbc_security
   ```

2. The dashboard will automatically:
   - Enable SSL certificates
   - Fetch OAuth tokens
   - Handle token refresh
   - Configure Codex

3. Just run and go:
   ```bash
   python codex_dashboard.py
   ```

## Development

The dashboard integrates several components:

- **OAuth Manager**: Handles token fetching and caching
- **Proxy Server**: Intercepts API calls on port 8889
- **Dashboard Server**: Serves web UI on port 8888
- **State Manager**: Thread-safe state sharing
- **Codex Launcher**: Subprocess management with config generation

All in one script for easy deployment and maintenance.

## License

MIT
