# Project Summary: Enterprise Codex CLI Integration

## What Was Built

A Python wrapper that enables OpenAI's Codex CLI to work with enterprise LLM endpoints requiring custom SSL certificates and OAuth2 authentication.

## Key Features

### 1. **Enterprise Authentication Support**
- OAuth2 client credentials flow
- Automatic token refresh every 15 minutes
- Tokens passed via environment variables

### 2. **SSL Certificate Management**
- Integration with `rbc_security` package
- SSL environment variables inherited by subprocess
- Works with internal corporate certificate authorities

### 3. **Dual-Mode Operation**
- **Mock Mode**: For local development without enterprise dependencies
- **Production Mode**: Full enterprise authentication and SSL

### 4. **Transparent Directory Handling**
- Wrapper preserves your current working directory
- Codex operates on YOUR project, not the wrapper's location
- Call from anywhere, works on files in `$PWD`

### 5. **Dynamic Configuration**
- Auto-generates `~/.codex/config.toml`
- Configures custom model provider
- Supports both "chat" and "responses" wire APIs

## File Structure

```
codex-custom-llm/
├── codex_wrapper.py       # Main entry point (orchestrates everything)
├── oauth_manager.py       # OAuth token fetching and refresh
├── config_generator.py    # Generates Codex configuration
├── test_wrapper.py        # Setup verification tool
├── setup.sh               # Automated setup script
├── requirements.txt       # Python dependencies
├── .env.example           # Configuration template
├── .gitignore            # Git ignore rules
├── README.md             # Overview and setup guide
├── USAGE.md              # Detailed usage instructions
└── PROJECT_SUMMARY.md    # This file
```

## How It Works

```
┌─────────────────────────────────────────┐
│  User's Terminal (in project dir)      │
│  $ python /path/to/codex_wrapper.py    │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  Python Wrapper Process                 │
│  ├─ Load .env config                    │
│  ├─ Call rbc_security.enable_certs()    │
│  ├─ Fetch OAuth token                   │
│  ├─ Set CUSTOM_LLM_API_KEY env var      │
│  ├─ Start background token refresh      │
│  ├─ Generate ~/.codex/config.toml       │
│  └─ Launch Codex subprocess             │
└──────────────┬──────────────────────────┘
               │ Inherits:
               │  - SSL env vars
               │  - OAuth token env var
               │  - Current working directory
               ▼
┌─────────────────────────────────────────┐
│  Codex CLI (Rust binary)                │
│  ├─ Reads config.toml                   │
│  ├─ Uses SSL env vars for HTTPS         │
│  ├─ Reads CUSTOM_LLM_API_KEY            │
│  ├─ Makes API calls to enterprise LLM   │
│  └─ Operates on files in current dir    │
└─────────────────────────────────────────┘
```

## Configuration

All configuration via `.env` file:

| Variable | Purpose | Required |
|----------|---------|----------|
| `MOCK_MODE` | Enable mock mode (true/false) | Yes |
| `OAUTH_ENDPOINT` | OAuth token URL | Production only |
| `OAUTH_CLIENT_ID` | OAuth client ID | Production only |
| `OAUTH_CLIENT_SECRET` | OAuth client secret | Production only |
| `LLM_API_BASE_URL` | LLM API base URL | Yes |
| `LLM_MODEL_NAME` | Model to use | Yes |
| `TOKEN_REFRESH_INTERVAL` | Token refresh interval (seconds) | Optional (default: 900) |
| `WIRE_API` | API format (chat/responses) | Optional (default: chat) |

## Usage Patterns

### Development (Personal Computer)
```bash
# Set MOCK_MODE=true in .env
cd ~/my-project
python /path/to/codex-custom-llm/codex_wrapper.py "help me refactor this"
```

### Production (Work Computer)
```bash
# Set MOCK_MODE=false and configure OAuth in .env
cd ~/my-project
python /path/to/codex-custom-llm/codex_wrapper.py "analyze the codebase"
```

### With Shell Alias
```bash
# Add to ~/.bashrc or ~/.zshrc:
alias codex="python /path/to/codex-custom-llm/codex_wrapper.py"

# Then use from any project:
cd ~/my-project
codex "implement user authentication"
```

## Testing

1. **Run setup script:**
   ```bash
   ./setup.sh
   ```

2. **Verify installation:**
   ```bash
   python test_wrapper.py
   ```

3. **Test wrapper:**
   ```bash
   python codex_wrapper.py --help
   ```

## Deployment Workflow

### On Personal Computer
1. Make changes
2. Test in mock mode (`MOCK_MODE=true`)
3. Commit and push to GitHub

### On Work Computer
1. Pull from GitHub
2. Run `./setup.sh`
3. Configure `.env` with real credentials
4. Run `python test_wrapper.py`
5. Test with real endpoints

## Security Considerations

- `.env` file is in `.gitignore` (never committed)
- OAuth tokens stored only in memory (environment variables)
- Tokens auto-refresh before expiry
- SSL certificates managed by `rbc_security`
- No credentials in code or logs

## Dependencies

### Required (both environments)
- Python 3.8+
- `requests` library
- `python-dotenv` library

### Required (work environment only)
- `rbc_security` package (internal)
- Codex CLI binary
- Access to OAuth and LLM endpoints

### Optional
- Codex CLI (for testing, required for actual use)

## Key Design Decisions

1. **Subprocess approach**: Wrapper launches Codex as subprocess rather than trying to modify it
2. **Environment inheritance**: SSL and auth passed via environment variables
3. **Current directory preservation**: Codex runs in user's project directory
4. **Mock mode**: Allows development and testing without enterprise dependencies
5. **Background token refresh**: Non-blocking, automatic, prevents expiry
6. **Dynamic config generation**: No manual Codex configuration needed

## Troubleshooting

See [USAGE.md](USAGE.md#troubleshooting) for detailed troubleshooting guide.

Common issues:
- **SSL errors**: Install `rbc_security` or enable mock mode
- **Auth failures**: Check `.env` OAuth credentials
- **Wrong directory**: Ensure you're in your project directory when calling wrapper
- **Codex not found**: Install Codex CLI

## Future Enhancements

Possible improvements:
- [ ] Support for Azure AD authentication
- [ ] Token caching to disk (with encryption)
- [ ] Config file validation
- [ ] Better error messages and recovery
- [ ] Support for multiple model providers
- [ ] Logging to file option
- [ ] Health check command
- [ ] Integration tests

## Resources

- GitHub: https://github.com/alexwday/codex-custom-llm
- README: Comprehensive setup and overview
- USAGE: Detailed usage patterns and examples
- Test script: `python test_wrapper.py`

## Support

For issues or questions:
1. Check [USAGE.md](USAGE.md) troubleshooting section
2. Run `python test_wrapper.py` to diagnose issues
3. Review logs (wrapper prints detailed debug info)
4. Open an issue on GitHub

## License

Internal use only
