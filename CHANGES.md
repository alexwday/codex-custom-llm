# Key Differences Fixed From Reference Implementation

This document outlines the critical fixes made to align the new dashboard with the reference implementation.

## Summary of Changes

The new `codex_dashboard.py` was updated to match the reference implementation's behavior in these key areas:

### 1. Environment Variable Name for OAuth Token ✅ FIXED

**Before:**
- Used `ANTHROPIC_API_KEY` (standard Anthropic name)

**After (matches reference):**
- Uses `CUSTOM_LLM_API_KEY` (custom name for enterprise endpoints)
- Defined as constant: `TOKEN_ENV_VAR = "CUSTOM_LLM_API_KEY"`

**Why this matters:**
- Avoids confusion with standard Anthropic API keys
- Clearly indicates this is for custom enterprise endpoints
- Matches the reference implementation exactly

### 2. Model Name Environment Variable ✅ FIXED

**Before:**
- Used `MODEL_NAME` environment variable
- Default: `gpt-4`

**After (matches reference):**
- Uses `LLM_MODEL_NAME` environment variable
- Default: `gpt-4-internal`

**Why this matters:**
- Consistent naming with `LLM_API_BASE_URL`
- More descriptive for enterprise LLM usage
- Matches reference configuration

### 3. Background Token Refresh ✅ ADDED

**Before:**
- Only refreshed tokens on-demand when expiry detected
- No automatic refresh mechanism

**After (matches reference):**
- Background thread refreshes tokens every 15 minutes (configurable)
- Uses `TOKEN_REFRESH_INTERVAL` environment variable (default: 900 seconds)
- Automatically updates `os.environ[TOKEN_ENV_VAR]` for Codex

**Why this matters:**
- **Critical for long-running Codex sessions**
- Prevents auth failures when tokens expire during active work
- Matches enterprise OAuth token lifecycle management

**Implementation:**
```python
def start_background_refresh(self):
    """Start background thread to refresh OAuth tokens periodically."""
    def refresh_loop():
        while not self.config.stop_refresh.wait(self.config.token_refresh_interval):
            token = self.get_token()
            if token:
                os.environ[TOKEN_ENV_VAR] = token
                # Log success
```

### 4. Configuration Updates ✅ UPDATED

Updated all configuration files to use correct variable names:

- `.env.example`: Updated with `LLM_MODEL_NAME`, `TOKEN_REFRESH_INTERVAL`
- `README.md`: Updated configuration table
- `QUICKSTART.md`: Updated example configurations

## Environment Variables Reference

| Variable | Purpose | Default | Notes |
|----------|---------|---------|-------|
| `CUSTOM_LLM_API_KEY` | OAuth token (set automatically) | - | Set by dashboard, read by Codex |
| `LLM_API_BASE_URL` | Enterprise LLM endpoint | - | Required |
| `LLM_MODEL_NAME` | Model identifier | `gpt-4-internal` | Matches reference |
| `MAX_TOKENS` | Max response tokens | `4096` | Increase if responses cut off |
| `TOKEN_REFRESH_INTERVAL` | Token refresh (seconds) | `900` | 15 minutes default |
| `OAUTH_ENDPOINT` | OAuth token endpoint | - | Required (unless MOCK_MODE) |
| `OAUTH_CLIENT_ID` | OAuth client ID | - | Required (unless MOCK_MODE) |
| `OAUTH_CLIENT_SECRET` | OAuth client secret | - | Required (unless MOCK_MODE) |
| `MOCK_MODE` | Skip OAuth/SSL | `false` | Set to `true` for testing |

## What Was NOT Changed

These aspects were intentionally different from the reference:

### 1. Working Directory Handling
- **Reference**: Uses caller's `os.getcwd()`, preserves current directory
- **Dashboard**: User specifies directory via web UI
- **Status**: Design choice, not a bug - different UX paradigm

### 2. Proxy Mode
- **Reference**: Optional `PROXY_MODE` env var to enable/disable proxy
- **Dashboard**: Always acts as built-in proxy
- **Status**: Simplified design - proxy is core feature, always enabled

### 3. Architecture
- **Reference**: Separate scripts (wrapper, monitor, proxy)
- **Dashboard**: Single integrated script
- **Status**: Intentional simplification, all features in one place

## Testing

Verified the fixes work correctly:

1. ✅ Environment variables use correct names (`LLM_MODEL_NAME`, etc.)
2. ✅ Config shows `TOKEN_REFRESH_INTERVAL` in dashboard
3. ✅ Generated Codex config uses `env_key = "CUSTOM_LLM_API_KEY"`
4. ✅ Background token refresh thread starts in non-mock mode
5. ✅ Mock mode sets `CUSTOM_LLM_API_KEY` with mock token

## Migration Notes

If upgrading from the old dashboard version:

1. **Update your `.env` file:**
   - Rename `MODEL_NAME` → `LLM_MODEL_NAME`
   - Add `TOKEN_REFRESH_INTERVAL=900` (optional)

2. **No code changes needed** - the dashboard handles everything

3. **Benefits you'll get:**
   - Automatic token refresh (no more mid-session auth failures)
   - Consistent naming with reference implementation
   - Better enterprise compatibility

## References

All changes align with:
- `reference/codex_wrapper.py` (main wrapper logic)
- `reference/oauth_manager.py` (token management)
- `reference/config_generator.py` (Codex config generation)
