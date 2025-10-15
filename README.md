# Enterprise Codex CLI Integration

Wrapper for OpenAI Codex CLI that integrates with enterprise authentication and SSL requirements.

## Overview

This wrapper enables Codex CLI to work with internal LLM endpoints that require:
- Custom SSL certificates (via `rbc_security` package)
- OAuth2 authentication with 15-minute token expiry
- Custom base URLs for internal APIs

## Architecture

```
┌─────────────────────────────────────────┐
│  codex_wrapper.py (Python)              │
│  ├─ SSL Setup (rbc_security)            │
│  ├─ OAuth Token Manager (background)    │
│  ├─ Config Generator                    │
│  └─ Codex Subprocess Launcher           │
└──────────────┬──────────────────────────┘
               │ Inherits environment
               ▼
┌─────────────────────────────────────────┐
│  Codex CLI (Rust binary)                │
│  ├─ Reads config.toml                   │
│  ├─ Uses SSL env vars                   │
│  └─ Reads CUSTOM_LLM_API_KEY            │
└─────────────────────────────────────────┘
```

## Project Structure

```
codex-custom-llm/
├── codex_wrapper.py          # Main entry point
├── oauth_manager.py          # Token fetching and refresh logic
├── config_generator.py       # Codex config.toml generator
├── .env.example              # Template for configuration
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## Development vs Production

### Local Development (Personal Computer)
- Uses mock mode (no rbc_security or OAuth required)
- Can test the wrapper logic without enterprise dependencies
- Set `MOCK_MODE=true` in environment

### Production (Work Computer)
- Requires `rbc_security` package installed
- Uses real OAuth endpoint and LLM API
- Set actual endpoint URLs and credentials in `.env`

## Setup Instructions

### On Personal Computer (Development)

1. **Clone and install dependencies:**
   ```bash
   cd codex-custom-llm
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Create .env file:**
   ```bash
   cp .env.example .env
   # Edit .env and set MOCK_MODE=true
   ```

3. **Test locally:**
   ```bash
   python codex_wrapper.py --help
   ```

### On Work Computer (Production)

1. **Pull the repository:**
   ```bash
   git pull origin main
   ```

2. **Create Python virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies (including rbc_security):**
   ```bash
   pip install -r requirements.txt
   pip install rbc_security  # Your internal package
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with actual values:
   # - OAUTH_ENDPOINT
   # - OAUTH_CLIENT_ID
   # - OAUTH_CLIENT_SECRET
   # - LLM_API_BASE_URL
   # - LLM_MODEL_NAME
   # Set MOCK_MODE=false
   ```

5. **Install Codex CLI:**
   ```bash
   npm install -g @openai/codex-cli
   # OR
   brew install codex
   ```

6. **Run the wrapper:**
   ```bash
   python codex_wrapper.py
   ```

## Configuration

All configuration is done via environment variables (`.env` file):

| Variable | Description | Example |
|----------|-------------|---------|
| `MOCK_MODE` | Enable mock mode for local dev | `true` or `false` |
| `OAUTH_ENDPOINT` | OAuth token endpoint | `https://internal-auth.company.com/oauth/token` |
| `OAUTH_CLIENT_ID` | OAuth client ID | `codex-cli-client` |
| `OAUTH_CLIENT_SECRET` | OAuth client secret | `your-secret-here` |
| `LLM_API_BASE_URL` | Internal LLM API base URL | `https://llm-api.company.com/v1` |
| `LLM_MODEL_NAME` | Model name for requests | `gpt-4-internal` |
| `TOKEN_REFRESH_INTERVAL` | Token refresh interval (seconds) | `900` (15 minutes) |

## How It Works

1. **SSL Configuration**: Python wrapper calls `rbc_security.enable_certs()` to set up SSL environment variables
2. **OAuth Token**: Fetches initial token and starts background refresh thread
3. **Config Generation**: Creates `~/.codex/config.toml` with custom provider settings
4. **Subprocess Launch**: Launches Codex CLI as subprocess, inheriting SSL environment
5. **Token Refresh**: Background thread refreshes token every 15 minutes, updating environment variable

## Working Directory Behavior

**Important**: The wrapper runs Codex in YOUR current working directory, not the wrapper's directory.

This means you should:
```bash
# Navigate to YOUR project
cd /path/to/your/actual/project

# Then call the wrapper (which can be anywhere)
python /path/to/codex-custom-llm/codex_wrapper.py "refactor the main function"
```

Codex will operate on files in `/path/to/your/actual/project`, not in the `codex-custom-llm` directory.

### Recommended Usage Patterns

**Option 1: Add wrapper to PATH**
```bash
# Add to ~/.bashrc or ~/.zshrc
export PATH="$PATH:/path/to/codex-custom-llm"
alias codex="python /path/to/codex-custom-llm/codex_wrapper.py"

# Then use from any project:
cd ~/my-project
codex "help me with this code"
```

**Option 2: Create a shell function**
```bash
# Add to ~/.bashrc or ~/.zshrc
codex() {
    python /path/to/codex-custom-llm/codex_wrapper.py "$@"
}

# Then use from any project:
cd ~/my-project
codex "analyze the architecture"
```

**Option 3: Direct invocation**
```bash
cd ~/my-project
python /full/path/to/codex-custom-llm/codex_wrapper.py "your prompt"
```

## Troubleshooting

### SSL Certificate Errors
- Ensure `rbc_security` is installed and accessible
- Check that `enable_certs()` runs before any network calls

### Authentication Failures
- Verify OAuth credentials in `.env`
- Check token refresh logs in console output
- Ensure OAuth endpoint is accessible from your network

### Codex Not Finding Model
- Verify `LLM_API_BASE_URL` is correct
- Check that `LLM_MODEL_NAME` matches what your API expects
- Review generated config at `~/.codex/config.toml`

### Token Expiry
- Default refresh is 15 minutes (900 seconds)
- Adjust `TOKEN_REFRESH_INTERVAL` if needed
- Monitor console logs for refresh activity

## Development Workflow

1. **Make changes on personal computer**
2. **Test in mock mode** (`MOCK_MODE=true`)
3. **Commit and push** to remote repository
4. **Pull on work computer**
5. **Test with real endpoints** (`MOCK_MODE=false`)

## Security Notes

- Never commit `.env` file (it's in `.gitignore`)
- OAuth credentials should be stored securely
- Tokens are kept in memory only (environment variables)
- SSL certificates are managed by `rbc_security` package

## License

Internal use only
