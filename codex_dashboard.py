#!/usr/bin/env python3
"""
Codex Proxy Dashboard - All-in-One Control Center

A single script that provides:
- Web dashboard showing OAuth config, API settings, and token info
- Integrated API proxy server for logging requests/responses
- Project folder selector to launch Codex in any directory
- Real-time monitoring of all API activity

Usage:
    python codex_dashboard.py

Then open http://localhost:8888 in your browser.
"""

import os
import sys
import json
import time
import subprocess
import threading
import webbrowser
import requests
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import parse_qs
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    logger.warning("python-dotenv not installed, using system environment only")

# Environment variable name for the OAuth token
TOKEN_ENV_VAR = "CUSTOM_LLM_API_KEY"


# ============================================================================
# Configuration
# ============================================================================

class DashboardConfig:
    """Global configuration for the dashboard."""

    def __init__(self):
        # Environment settings
        self.mock_mode = os.getenv('MOCK_MODE', 'false').lower() == 'true'
        self.llm_api_base_url = os.getenv('LLM_API_BASE_URL', 'https://api.example.com')
        self.model_name = os.getenv('LLM_MODEL_NAME', 'gpt-4-internal')
        self.max_tokens = int(os.getenv('MAX_TOKENS', '4096'))
        self.token_refresh_interval = int(os.getenv('TOKEN_REFRESH_INTERVAL', '900'))  # 15 minutes

        # OAuth settings
        self.oauth_endpoint = os.getenv('OAUTH_ENDPOINT', '')
        self.oauth_client_id = os.getenv('OAUTH_CLIENT_ID', '')
        self.oauth_client_secret = os.getenv('OAUTH_CLIENT_SECRET', '***')

        # Proxy settings
        self.proxy_port = 8889
        self.dashboard_port = 8888

        # Token cache
        self.oauth_token = None
        self.token_expiry = None

        # Token refresh thread
        self.refresh_thread = None
        self.stop_refresh = threading.Event()

        # Codex process
        self.codex_process = None
        self.codex_working_dir = None

        # Logging
        log_dir = Path.home() / '.codex' / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.log_file = log_dir / f'proxy_requests_{timestamp}.log'

    def get_env_vars(self) -> Dict[str, str]:
        """Get sanitized environment variables for display."""
        return {
            'MOCK_MODE': str(self.mock_mode),
            'LLM_API_BASE_URL': self.llm_api_base_url,
            'LLM_MODEL_NAME': self.model_name,
            'MAX_TOKENS': str(self.max_tokens),
            'TOKEN_REFRESH_INTERVAL': f'{self.token_refresh_interval}s',
            'OAUTH_ENDPOINT': self.oauth_endpoint or 'Not set',
            'OAUTH_CLIENT_ID': self.oauth_client_id or 'Not set',
        }


config = DashboardConfig()


# ============================================================================
# OAuth Manager
# ============================================================================

class OAuthManager:
    """Manages OAuth token fetching and caching."""

    def __init__(self):
        self.config = config

    def start_background_refresh(self):
        """Start background thread to refresh OAuth tokens periodically."""
        def refresh_loop():
            while not self.config.stop_refresh.wait(self.config.token_refresh_interval):
                logger.info("Background token refresh triggered...")
                state.add_event('info', 'Refreshing OAuth token (background)')

                token = self.get_token()
                if token:
                    # Update environment variable
                    os.environ[TOKEN_ENV_VAR] = token
                    logger.info("OAuth token refreshed successfully")
                    state.add_event('success', 'OAuth token refreshed')
                else:
                    logger.warning("Failed to refresh OAuth token")
                    state.add_event('warning', 'Failed to refresh OAuth token')

        self.config.refresh_thread = threading.Thread(target=refresh_loop, daemon=True)
        self.config.refresh_thread.start()
        logger.info(f"Token refresh thread started (interval: {self.config.token_refresh_interval}s)")
        state.add_event('info', f'Token refresh enabled', f'Interval: {self.config.token_refresh_interval}s')

    def get_token(self) -> Optional[str]:
        """Fetch OAuth token (or return mock token)."""
        if self.config.mock_mode:
            logger.info("Mock mode: Using mock OAuth token")
            return "mock_token_for_local_development_" + "x" * 50

        # Check if we have a cached token that's still valid
        if self.config.oauth_token and self.config.token_expiry:
            if time.time() < self.config.token_expiry:
                logger.debug("Using cached OAuth token")
                return self.config.oauth_token

        # Fetch new token
        try:
            logger.info("Fetching new OAuth token...")
            response = requests.post(
                self.config.oauth_endpoint,
                data={
                    'grant_type': 'client_credentials',
                    'client_id': self.config.oauth_client_id,
                    'client_secret': self.config.oauth_client_secret
                },
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=30
            )

            response.raise_for_status()
            token_data = response.json()

            access_token = token_data.get('access_token')
            if not access_token:
                logger.error("No access_token in OAuth response")
                return None

            # Cache token
            self.config.oauth_token = access_token
            expires_in = token_data.get('expires_in', 3600)
            self.config.token_expiry = time.time() + expires_in - 60  # Refresh 1 min early

            logger.info(f"OAuth token obtained, expires in {expires_in}s")
            state.add_event('success', 'OAuth token refreshed', f'Expires in {expires_in}s')
            state.update_token_refresh()

            return access_token

        except Exception as e:
            logger.error(f"Failed to fetch OAuth token: {e}")
            state.add_event('error', 'OAuth token fetch failed', str(e))
            return None


oauth_manager = OAuthManager()


# ============================================================================
# State Management
# ============================================================================

class DashboardState:
    """Shared state for the dashboard."""

    def __init__(self):
        self.lock = threading.Lock()
        self.start_time = datetime.now()
        self.events = []
        self.max_events = 100

        # OAuth stats
        self.token_refresh_count = 0
        self.last_token_refresh = None
        self.oauth_status = "Not initialized"

        # API stats
        self.api_request_count = 0
        self.api_response_count = 0
        self.api_error_count = 0
        self.last_request_time = None
        self.last_response_time = None
        self.api_requests = []
        self.max_api_requests = 50

        # Codex status
        self.codex_status = "Not started"
        self.codex_working_dir = None

    def add_event(self, event_type: str, message: str, details: str = None):
        """Add event to log."""
        with self.lock:
            event = {
                'timestamp': datetime.now().isoformat(),
                'type': event_type,
                'message': message,
                'details': details
            }
            self.events.append(event)
            if len(self.events) > self.max_events:
                self.events = self.events[-self.max_events:]

    def add_api_request(self, request_id: int, model: str, messages_count: int, max_tokens):
        """Log API request."""
        with self.lock:
            self.api_request_count += 1
            self.last_request_time = datetime.now()

            request_info = {
                'id': request_id,
                'timestamp': self.last_request_time.isoformat(),
                'model': model,
                'messages_count': messages_count,
                'max_tokens': max_tokens,
                'status': 'pending'
            }

            self.api_requests.append(request_info)
            if len(self.api_requests) > self.max_api_requests:
                self.api_requests = self.api_requests[-self.max_api_requests:]

    def update_api_response(self, request_id: int, finish_reason: str, tokens_used: int, elapsed_time: float):
        """Update request with response info."""
        with self.lock:
            self.api_response_count += 1
            self.last_response_time = datetime.now()

            for req in reversed(self.api_requests):
                if req['id'] == request_id:
                    req['status'] = 'success' if finish_reason == 'stop' else 'warning'
                    req['finish_reason'] = finish_reason
                    req['tokens_used'] = tokens_used
                    req['elapsed_time'] = f"{elapsed_time:.2f}s"
                    break

    def update_api_error(self, request_id: int, error_msg: str):
        """Update request with error."""
        with self.lock:
            self.api_error_count += 1

            for req in reversed(self.api_requests):
                if req['id'] == request_id:
                    req['status'] = 'error'
                    req['error'] = error_msg
                    break

    def update_token_refresh(self):
        """Record token refresh."""
        with self.lock:
            self.token_refresh_count += 1
            self.last_token_refresh = datetime.now()
            self.oauth_status = "Active"

    def update_oauth_status(self, status: str):
        """Update OAuth status."""
        with self.lock:
            self.oauth_status = status

    def update_codex_status(self, status: str, working_dir: str = None):
        """Update Codex status."""
        with self.lock:
            self.codex_status = status
            if working_dir:
                self.codex_working_dir = working_dir

    def get_state(self) -> Dict[str, Any]:
        """Get current state as JSON."""
        with self.lock:
            uptime = int((datetime.now() - self.start_time).total_seconds())
            return {
                'uptime': uptime,
                'events': list(reversed(self.events)),
                'token_refresh_count': self.token_refresh_count,
                'last_token_refresh': self.last_token_refresh.isoformat() if self.last_token_refresh else None,
                'oauth_status': self.oauth_status,
                'api_request_count': self.api_request_count,
                'api_response_count': self.api_response_count,
                'api_error_count': self.api_error_count,
                'last_request_time': self.last_request_time.isoformat() if self.last_request_time else None,
                'last_response_time': self.last_response_time.isoformat() if self.last_response_time else None,
                'api_requests': list(reversed(self.api_requests)),
                'codex_status': self.codex_status,
                'codex_working_dir': self.codex_working_dir,
                'config': config.get_env_vars(),
                'proxy_url': f'http://localhost:{config.proxy_port}',
                'log_file': str(config.log_file)
            }


state = DashboardState()


# ============================================================================
# API Proxy Handler
# ============================================================================

class ProxyHandler(BaseHTTPRequestHandler):
    """Handles API proxy requests."""

    def log_message(self, format, *args):
        """Suppress default HTTP logging."""
        pass

    def do_POST(self):
        """Handle POST requests to proxy."""
        request_id = state.api_request_count + 1

        try:
            # Read request
            content_length = int(self.headers.get('Content-Length', 0))
            request_body = self.rfile.read(content_length).decode('utf-8')
            request_data = json.loads(request_body)

            # Log request
            self.log_request_info(request_id, request_data)

            # Forward to real endpoint
            response_data = self.forward_request(request_id, request_data)

            if response_data is None:
                return

            # Send response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))

        except Exception as e:
            logger.error(f"Proxy error: {e}")
            self.send_error(500, str(e))
            state.update_api_error(request_id, str(e))

    def log_request_info(self, request_id: int, request_data: Dict):
        """Log incoming request."""
        model = request_data.get('model', 'unknown')
        messages = request_data.get('messages', [])
        max_tokens = request_data.get('max_tokens', 'not set')

        log_msg = f"Request #{request_id}: model={model}, tokens={max_tokens}, messages={len(messages)}"
        logger.info(log_msg)

        state.add_event('info', f'API Request #{request_id}', f'Model: {model}, Max tokens: {max_tokens}')
        state.add_api_request(request_id, model, len(messages), max_tokens)

        # Write to log file
        with open(config.log_file, 'a') as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"REQUEST #{request_id} at {datetime.now().strftime('%H:%M:%S')}\n")
            f.write(f"{'='*80}\n")
            f.write(json.dumps(request_data, indent=2))
            f.write("\n")

    def forward_request(self, request_id: int, request_data: Dict) -> Optional[Dict]:
        """Forward request to real endpoint."""
        start_time = time.time()

        # Build URL
        url = config.llm_api_base_url
        if not url.endswith('/'):
            url += '/'
        url += 'chat/completions'

        # Get OAuth token
        token = oauth_manager.get_token()
        if not token:
            error = "No OAuth token available"
            logger.error(error)
            self.send_error(401, error)
            state.add_event('error', f'Request #{request_id} failed', error)
            return None

        # Make request
        try:
            logger.info(f"Forwarding request #{request_id} to {url}")

            response = requests.post(
                url,
                headers={
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json'
                },
                json=request_data,
                timeout=120
            )

            elapsed = time.time() - start_time

            if response.status_code != 200:
                error = f"HTTP {response.status_code}: {response.text[:500]}"
                logger.error(f"Request #{request_id} failed: {error}")
                self.send_error(response.status_code, error)
                state.add_event('error', f'Request #{request_id} failed', error)
                state.update_api_error(request_id, error)
                return None

            response_data = response.json()

            # Log response
            self.log_response_info(request_id, response_data, elapsed)

            return response_data

        except requests.exceptions.Timeout:
            error = "Request timed out after 120s"
            logger.error(f"Request #{request_id}: {error}")
            self.send_error(504, error)
            state.add_event('error', f'Request #{request_id} timeout', error)
            state.update_api_error(request_id, error)
            return None
        except Exception as e:
            error = f"Request failed: {str(e)}"
            logger.error(f"Request #{request_id}: {error}")
            self.send_error(500, error)
            state.add_event('error', f'Request #{request_id} failed', str(e))
            state.update_api_error(request_id, str(e))
            return None

    def log_response_info(self, request_id: int, response_data: Dict, elapsed: float):
        """Log response."""
        choices = response_data.get('choices', [])
        finish_reason = 'unknown'
        content_length = 0

        if choices:
            finish_reason = choices[0].get('finish_reason', 'unknown')
            content = choices[0].get('message', {}).get('content', '')
            content_length = len(content)

        usage = response_data.get('usage', {})
        total_tokens = usage.get('total_tokens', 0)

        log_msg = f"Response #{request_id}: finish={finish_reason}, tokens={total_tokens}, time={elapsed:.2f}s"
        logger.info(log_msg)

        state.add_event(
            'success' if finish_reason == 'stop' else 'warning',
            f'API Response #{request_id} ({elapsed:.1f}s)',
            f'Finish: {finish_reason}, Tokens: {total_tokens}'
        )
        state.update_api_response(request_id, finish_reason, total_tokens, elapsed)

        # Write to log file
        with open(config.log_file, 'a') as f:
            f.write(f"\nRESPONSE #{request_id} at {datetime.now().strftime('%H:%M:%S')} (took {elapsed:.2f}s)\n")
            f.write(f"{'='*80}\n")
            f.write(json.dumps(response_data, indent=2))
            f.write("\n")

        # Check for issues
        if finish_reason == 'length':
            warning = f"WARNING: Response #{request_id} was cut off (finish_reason=length)"
            logger.warning(warning)
            state.add_event('warning', warning, 'Consider increasing MAX_TOKENS')


# ============================================================================
# Dashboard HTTP Handler
# ============================================================================

class DashboardHandler(BaseHTTPRequestHandler):
    """Handles dashboard HTTP requests."""

    def log_message(self, format, *args):
        """Suppress default HTTP logging."""
        pass

    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/':
            self.serve_dashboard()
        elif self.path == '/api/state':
            self.serve_state()
        else:
            self.send_error(404)

    def do_POST(self):
        """Handle POST requests."""
        if self.path == '/api/launch-codex':
            self.handle_launch_codex()
        else:
            self.send_error(404)

    def serve_dashboard(self):
        """Serve HTML dashboard."""
        html = self.get_dashboard_html()
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())

    def serve_state(self):
        """Serve current state as JSON."""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(json.dumps(state.get_state()).encode())

    def handle_launch_codex(self):
        """Handle Codex launch request."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)

            project_dir = data.get('project_dir')
            prompt = data.get('prompt', '')

            if not project_dir:
                self.send_error(400, "Missing project_dir")
                return

            # Launch Codex in subprocess
            success = self.launch_codex(project_dir, prompt)

            response = {'success': success}
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

        except Exception as e:
            logger.error(f"Failed to launch Codex: {e}")
            self.send_error(500, str(e))

    def launch_codex(self, project_dir: str, prompt: str) -> bool:
        """Launch Codex CLI in specified directory."""
        try:
            # Setup SSL if available
            try:
                import rbc_security
                rbc_security.enable_certs()
                logger.info("SSL certificates enabled")
            except ImportError:
                logger.info("rbc_security not available (OK for local testing)")

            # Generate Codex config
            self.generate_codex_config()

            # Build Codex command
            codex_cmd = ['codex']
            if prompt:
                codex_cmd.append(prompt)

            logger.info(f"Launching Codex in {project_dir}")
            logger.info(f"Command: {' '.join(codex_cmd)}")

            # Set environment for subprocess
            env = os.environ.copy()
            token = oauth_manager.get_token() or 'mock-token'
            env[TOKEN_ENV_VAR] = token

            logger.info(f"Setting {TOKEN_ENV_VAR} for Codex subprocess")

            # Launch subprocess
            process = subprocess.Popen(
                codex_cmd,
                cwd=project_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            config.codex_process = process
            config.codex_working_dir = project_dir

            state.update_codex_status("Running", project_dir)
            state.add_event('success', f'Codex launched in {project_dir}', f'PID: {process.pid}')

            # Monitor process in background
            threading.Thread(target=self.monitor_codex_process, args=(process,), daemon=True).start()

            return True

        except Exception as e:
            logger.error(f"Failed to launch Codex: {e}")
            state.add_event('error', 'Failed to launch Codex', str(e))
            state.update_codex_status(f"Error: {str(e)}")
            return False

    def monitor_codex_process(self, process):
        """Monitor Codex process and log output."""
        try:
            stdout, stderr = process.communicate()

            if stdout:
                logger.info(f"Codex stdout: {stdout.decode()}")
            if stderr:
                logger.error(f"Codex stderr: {stderr.decode()}")

            state.update_codex_status("Exited")
            state.add_event('info', 'Codex process exited', f'Exit code: {process.returncode}')

        except Exception as e:
            logger.error(f"Error monitoring Codex: {e}")

    def generate_codex_config(self):
        """Generate Codex config file."""
        config_dir = Path.home() / '.codex'
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / 'config.toml'

        toml_content = f'''# Codex CLI Configuration
# Generated by Codex Dashboard

model = "{config.model_name}"
model_provider = "enterprise_llm"

[model_providers.enterprise_llm]
name = "Enterprise LLM"
base_url = "{config.llm_api_base_url}"
env_key = "{TOKEN_ENV_VAR}"
wire_api = "chat"
max_tokens = {config.max_tokens}
'''

        config_file.write_text(toml_content)
        logger.info(f"Generated Codex config at {config_file}")
        state.add_event('info', 'Codex config generated', str(config_file))

    def get_dashboard_html(self):
        """Generate HTML dashboard."""
        return '''<!DOCTYPE html>
<html>
<head>
    <title>Codex Proxy Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 20px;
        }

        .container {
            max-width: 1600px;
            margin: 0 auto;
        }

        h1 {
            color: #4ec9b0;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .pulse {
            width: 12px;
            height: 12px;
            background: #4ec9b0;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }

        .card {
            background: #252526;
            border: 1px solid #3e3e42;
            border-radius: 8px;
            padding: 20px;
        }

        .card h2 {
            color: #569cd6;
            font-size: 16px;
            margin-bottom: 15px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .stat {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #3e3e42;
        }

        .stat:last-child {
            border-bottom: none;
        }

        .stat-label {
            color: #858585;
        }

        .stat-value {
            color: #d4d4d4;
            font-weight: 600;
        }

        .status-active { color: #4ec9b0; }
        .status-warning { color: #ce9178; }
        .status-error { color: #f48771; }

        .launch-section {
            background: #252526;
            border: 1px solid #3e3e42;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }

        .launch-section h2 {
            color: #569cd6;
            font-size: 16px;
            margin-bottom: 15px;
        }

        .form-group {
            margin-bottom: 15px;
        }

        .form-group label {
            display: block;
            margin-bottom: 5px;
            color: #858585;
        }

        .form-group input {
            width: 100%;
            padding: 10px;
            background: #1e1e1e;
            border: 1px solid #3e3e42;
            border-radius: 4px;
            color: #d4d4d4;
            font-size: 14px;
        }

        .btn {
            background: #4ec9b0;
            color: #1e1e1e;
            border: none;
            padding: 12px 24px;
            border-radius: 4px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
        }

        .btn:hover {
            background: #5fd4be;
        }

        .btn:disabled {
            background: #3e3e42;
            color: #858585;
            cursor: not-allowed;
        }

        .events {
            background: #252526;
            border: 1px solid #3e3e42;
            border-radius: 8px;
            padding: 20px;
            max-height: 600px;
            overflow-y: auto;
        }

        .events h2 {
            color: #569cd6;
            font-size: 16px;
            margin-bottom: 15px;
        }

        .event {
            padding: 12px;
            margin-bottom: 10px;
            border-left: 3px solid;
            background: #1e1e1e;
            border-radius: 4px;
        }

        .event-info { border-left-color: #569cd6; }
        .event-success { border-left-color: #4ec9b0; }
        .event-warning { border-left-color: #ce9178; }
        .event-error { border-left-color: #f48771; }

        .event-time {
            font-size: 11px;
            color: #858585;
            margin-bottom: 5px;
        }

        .event-message {
            color: #d4d4d4;
            margin-bottom: 5px;
        }

        .event-details {
            font-size: 12px;
            color: #858585;
            font-family: 'Courier New', monospace;
        }

        .api-requests {
            background: #252526;
            border: 1px solid #3e3e42;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }

        .api-requests h2 {
            color: #569cd6;
            font-size: 16px;
            margin-bottom: 15px;
        }

        .api-request {
            background: #1e1e1e;
            padding: 12px;
            margin-bottom: 10px;
            border-radius: 4px;
            border-left: 3px solid;
        }

        .api-request.pending { border-left-color: #ce9178; }
        .api-request.success { border-left-color: #4ec9b0; }
        .api-request.warning { border-left-color: #ce9178; }
        .api-request.error { border-left-color: #f48771; }

        .request-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 5px;
        }

        .request-id {
            color: #569cd6;
            font-weight: 600;
        }

        .request-status {
            font-size: 12px;
            padding: 2px 8px;
            border-radius: 3px;
            background: #3e3e42;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>
            <div class="pulse"></div>
            Codex Proxy Dashboard
        </h1>

        <div class="grid">
            <div class="card">
                <h2>Status</h2>
                <div class="stat">
                    <span class="stat-label">Uptime</span>
                    <span class="stat-value" id="uptime">0s</span>
                </div>
                <div class="stat">
                    <span class="stat-label">OAuth Token</span>
                    <span class="stat-value status-active" id="oauth-status">Unknown</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Token Refreshes</span>
                    <span class="stat-value" id="token-refreshes">0</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Codex Status</span>
                    <span class="stat-value" id="codex-status">Not started</span>
                </div>
            </div>

            <div class="card">
                <h2>API Statistics</h2>
                <div class="stat">
                    <span class="stat-label">Requests</span>
                    <span class="stat-value" id="api-requests">0</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Responses</span>
                    <span class="stat-value" id="api-responses">0</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Errors</span>
                    <span class="stat-value status-error" id="api-errors">0</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Last Request</span>
                    <span class="stat-value" id="last-request">Never</span>
                </div>
            </div>

            <div class="card">
                <h2>Configuration</h2>
                <div id="config-vars"></div>
            </div>
        </div>

        <div class="launch-section">
            <h2>Launch Codex</h2>
            <div class="form-group">
                <label>Project Directory</label>
                <input type="text" id="project-dir" placeholder="/path/to/your/project" />
            </div>
            <div class="form-group">
                <label>Initial Prompt (Optional)</label>
                <input type="text" id="prompt" placeholder="Enter a prompt for Codex..." />
            </div>
            <button class="btn" onclick="launchCodex()">Launch Codex</button>
            <div id="codex-working-dir" style="margin-top: 10px; color: #858585; font-size: 12px;"></div>
        </div>

        <div class="api-requests">
            <h2>Recent API Requests</h2>
            <div id="api-requests-list"></div>
        </div>

        <div class="events">
            <h2>Activity Log</h2>
            <div id="events"></div>
        </div>
    </div>

    <script>
        function formatUptime(seconds) {
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            const secs = seconds % 60;
            if (hours > 0) return `${hours}h ${minutes}m ${secs}s`;
            if (minutes > 0) return `${minutes}m ${secs}s`;
            return `${secs}s`;
        }

        function formatTime(isoString) {
            if (!isoString) return 'Never';
            const date = new Date(isoString);
            return date.toLocaleTimeString();
        }

        function getEventClass(type) {
            if (type === 'error') return 'event-error';
            if (type === 'warning') return 'event-warning';
            if (type === 'success') return 'event-success';
            return 'event-info';
        }

        function updateDashboard() {
            fetch('/api/state')
                .then(response => response.json())
                .then(state => {
                    // Update status
                    document.getElementById('uptime').textContent = formatUptime(state.uptime);
                    document.getElementById('oauth-status').textContent = state.oauth_status;
                    document.getElementById('token-refreshes').textContent = state.token_refresh_count;
                    document.getElementById('codex-status').textContent = state.codex_status;

                    // Update API stats
                    document.getElementById('api-requests').textContent = state.api_request_count;
                    document.getElementById('api-responses').textContent = state.api_response_count;
                    document.getElementById('api-errors').textContent = state.api_error_count;
                    document.getElementById('last-request').textContent = formatTime(state.last_request_time);

                    // Update config
                    const configHtml = Object.entries(state.config)
                        .map(([key, value]) => `
                            <div class="stat">
                                <span class="stat-label">${key}</span>
                                <span class="stat-value">${value}</span>
                            </div>
                        `).join('');
                    document.getElementById('config-vars').innerHTML = configHtml;

                    // Update working dir
                    if (state.codex_working_dir) {
                        document.getElementById('codex-working-dir').textContent =
                            `Working directory: ${state.codex_working_dir}`;
                    }

                    // Update API requests
                    const requestsHtml = state.api_requests
                        .map(req => `
                            <div class="api-request ${req.status}">
                                <div class="request-header">
                                    <span class="request-id">Request #${req.id}</span>
                                    <span class="request-status">${req.status.toUpperCase()}</span>
                                </div>
                                <div style="font-size: 12px; color: #858585;">
                                    ${formatTime(req.timestamp)} | Model: ${req.model} | Max tokens: ${req.max_tokens}
                                    ${req.finish_reason ? ` | Finish: ${req.finish_reason}` : ''}
                                    ${req.elapsed_time ? ` | Time: ${req.elapsed_time}` : ''}
                                    ${req.error ? `<br>Error: ${req.error}` : ''}
                                </div>
                            </div>
                        `).join('');
                    document.getElementById('api-requests-list').innerHTML =
                        requestsHtml || '<div style="color: #858585;">No requests yet</div>';

                    // Update events
                    const eventsHtml = state.events
                        .map(event => `
                            <div class="event ${getEventClass(event.type)}">
                                <div class="event-time">${formatTime(event.timestamp)}</div>
                                <div class="event-message">${event.message}</div>
                                ${event.details ? `<div class="event-details">${event.details}</div>` : ''}
                            </div>
                        `).join('');
                    document.getElementById('events').innerHTML =
                        eventsHtml || '<div class="event-message">No events yet</div>';
                })
                .catch(error => console.error('Error fetching state:', error));
        }

        function launchCodex() {
            const projectDir = document.getElementById('project-dir').value;
            const prompt = document.getElementById('prompt').value;

            if (!projectDir) {
                alert('Please enter a project directory');
                return;
            }

            fetch('/api/launch-codex', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    project_dir: projectDir,
                    prompt: prompt
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('Codex launched successfully!');
                } else {
                    alert('Failed to launch Codex');
                }
            })
            .catch(error => {
                console.error('Error launching Codex:', error);
                alert('Error launching Codex: ' + error);
            });
        }

        // Update every second
        updateDashboard();
        setInterval(updateDashboard, 1000);
    </script>
</body>
</html>'''


# ============================================================================
# Main
# ============================================================================

def start_proxy_server():
    """Start API proxy server in background."""
    server = HTTPServer(('localhost', config.proxy_port), ProxyHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info(f"Proxy server started on http://localhost:{config.proxy_port}")
    state.add_event('info', f'Proxy server started', f'Port {config.proxy_port}')
    return server


def start_dashboard_server():
    """Start dashboard server."""
    server = HTTPServer(('localhost', config.dashboard_port), DashboardHandler)
    logger.info(f"Dashboard server started on http://localhost:{config.dashboard_port}")
    state.add_event('info', f'Dashboard server started', f'Port {config.dashboard_port}')
    return server


def main():
    """Main entry point."""
    print("\n" + "=" * 80)
    print("  🚀 CODEX PROXY DASHBOARD")
    print("=" * 80)
    print(f"  Dashboard: http://localhost:{config.dashboard_port}")
    print(f"  Proxy:     http://localhost:{config.proxy_port}")
    print(f"  Log File:  {config.log_file}")
    print("=" * 80)
    print()

    # Setup SSL if available
    try:
        import rbc_security
        print("Setting up SSL certificates...")
        rbc_security.enable_certs()
        print("✓ SSL configured")
        state.add_event('success', 'SSL certificates enabled', 'rbc_security.enable_certs()')
    except ImportError:
        print("⚠️  rbc_security not available (OK for local testing)")
        state.add_event('info', 'SSL not configured', 'rbc_security not available')

    print()

    # Initialize OAuth
    if not config.mock_mode:
        print("Fetching initial OAuth token...")
        token = oauth_manager.get_token()
        if token:
            print("✓ OAuth token obtained")
            # Set in environment for immediate use
            os.environ[TOKEN_ENV_VAR] = token
            # Start background refresh
            oauth_manager.start_background_refresh()
            print(f"✓ Token auto-refresh enabled (every {config.token_refresh_interval}s)")
        else:
            print("⚠️  Failed to get OAuth token (will retry when needed)")
    else:
        print("⚠️  Running in MOCK MODE")
        state.update_oauth_status("Mock mode")
        # Set mock token in environment
        os.environ[TOKEN_ENV_VAR] = oauth_manager.get_token()

    print()

    # Start servers
    print("Starting servers...")
    proxy_server = start_proxy_server()
    print(f"✓ Proxy server running on port {config.proxy_port}")

    dashboard_server = start_dashboard_server()
    print(f"✓ Dashboard server running on port {config.dashboard_port}")

    print()
    print("=" * 80)
    print("  ✅ All systems ready!")
    print("=" * 80)
    print()
    print("  Open http://localhost:8888 in your browser")
    print("  Press Ctrl+C to stop")
    print()

    # Open browser
    try:
        webbrowser.open(f'http://localhost:{config.dashboard_port}')
    except:
        pass

    # Run dashboard server (blocks)
    try:
        dashboard_server.serve_forever()
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        dashboard_server.shutdown()
        if config.codex_process:
            config.codex_process.terminate()


if __name__ == '__main__':
    main()
