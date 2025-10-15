#!/usr/bin/env python3
"""
LLM API Proxy Server

This proxy sits between Codex and your real LLM endpoint.
It logs EVERY request and response so you can see exactly what's happening.

Flow:
  Codex → http://localhost:8889 (proxy) → Real LLM Endpoint → Response → Codex

Usage:
  1. Start the proxy: python proxy_server.py
  2. Update .env: PROXY_MODE=true
  3. Run Codex wrapper as normal

The proxy will log everything to:
  - Terminal (real-time)
  - Monitor dashboard (if --monitor is used)
  - Log file: ~/.codex/logs/proxy_requests_*.log
"""

import os
import sys
import json
import time
import requests
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Try to import monitor state if available
try:
    from monitor_server import monitor_state
    HAS_MONITOR = True
except ImportError:
    HAS_MONITOR = False


class ProxyConfig:
    """Configuration for the proxy server."""

    def __init__(self):
        self.real_endpoint = os.getenv('LLM_API_BASE_URL')
        self.mock_mode = os.getenv('MOCK_MODE', 'false').lower() == 'true'
        self.oauth_token = None
        self.request_count = 0
        self.log_file = None

        # Create log file
        log_dir = Path.home() / '.codex' / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.log_file = log_dir / f'proxy_requests_{timestamp}.log'

        print(f"Proxy logging to: {self.log_file}")

    def get_oauth_token(self):
        """Get OAuth token."""
        if self.mock_mode:
            return "mock_token_for_proxy"

        if self.oauth_token:
            return self.oauth_token

        # Fetch token
        try:
            from oauth_manager import OAuthManager
            oauth = OAuthManager(
                endpoint=os.getenv('OAUTH_ENDPOINT'),
                client_id=os.getenv('OAUTH_CLIENT_ID'),
                client_secret=os.getenv('OAUTH_CLIENT_SECRET'),
                mock_mode=False
            )
            self.oauth_token = oauth.get_token()
            return self.oauth_token
        except Exception as e:
            print(f"Failed to get OAuth token: {e}")
            return None


# Global config
proxy_config = ProxyConfig()


class ProxyHandler(BaseHTTPRequestHandler):
    """HTTP request handler that proxies to the real endpoint."""

    def log_message(self, format, *args):
        """Suppress default HTTP logging."""
        pass

    def do_POST(self):
        """Handle POST requests."""
        proxy_config.request_count += 1
        request_id = proxy_config.request_count

        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            request_body = self.rfile.read(content_length).decode('utf-8')

            # Parse request
            try:
                request_data = json.loads(request_body)
            except json.JSONDecodeError:
                self.send_error(400, "Invalid JSON")
                return

            # Log request
            self.log_request_info(request_id, request_data)

            # Forward to real endpoint
            response_data = self.forward_request(request_id, request_data)

            if response_data is None:
                # Error already sent
                return

            # Send response back to Codex
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))

        except Exception as e:
            self.log_error_info(request_id, str(e))
            self.send_error(500, str(e))

    def log_request_info(self, request_id, request_data):
        """Log incoming request."""
        timestamp = datetime.now().strftime('%H:%M:%S')

        # Extract key info
        model = request_data.get('model', 'unknown')
        messages = request_data.get('messages', [])
        max_tokens = request_data.get('max_tokens', 'not set')
        stream = request_data.get('stream', False)

        # Last message content
        last_message = ""
        if messages:
            last_message = messages[-1].get('content', '')[:100]

        log_entry = f"""
{'=' * 80}
REQUEST #{request_id} at {timestamp}
{'=' * 80}
Model: {model}
Max Tokens: {max_tokens}
Streaming: {stream}
Messages: {len(messages)}
Last Message: {last_message}...

Full Request:
{json.dumps(request_data, indent=2)}
"""

        # Print to terminal
        print(log_entry)

        # Write to log file
        with open(proxy_config.log_file, 'a') as f:
            f.write(log_entry + '\n')

        # Add to monitor if available
        if HAS_MONITOR:
            try:
                monitor_state.add_event('info', f'API Request #{request_id}', f'Model: {model}, Tokens: {max_tokens}')
            except:
                pass

    def forward_request(self, request_id, request_data):
        """Forward request to real endpoint."""
        timestamp_start = time.time()

        # Build URL
        real_url = proxy_config.real_endpoint
        if not real_url.endswith('/'):
            real_url += '/'
        real_url += 'chat/completions'

        # Get OAuth token
        token = proxy_config.get_oauth_token()
        if not token:
            self.log_error_info(request_id, "No OAuth token available")
            self.send_error(401, "No OAuth token")
            return None

        # Prepare headers
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        # Make request
        print(f"\n[REQUEST #{request_id}] Forwarding to {real_url}...")

        try:
            response = requests.post(
                real_url,
                headers=headers,
                json=request_data,
                timeout=120  # 2 minute timeout
            )

            elapsed = time.time() - timestamp_start

            # Check response
            if response.status_code != 200:
                error_msg = f"HTTP {response.status_code}: {response.text[:500]}"
                self.log_error_info(request_id, error_msg)
                self.send_error(response.status_code, error_msg)
                return None

            # Parse response
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                error_msg = f"Invalid JSON response: {response.text[:500]}"
                self.log_error_info(request_id, error_msg)
                self.send_error(500, error_msg)
                return None

            # Log response
            self.log_response_info(request_id, response_data, elapsed)

            return response_data

        except requests.exceptions.Timeout:
            error_msg = f"Request timed out after 120 seconds"
            self.log_error_info(request_id, error_msg)
            self.send_error(504, error_msg)
            return None
        except Exception as e:
            error_msg = f"Request failed: {str(e)}"
            self.log_error_info(request_id, error_msg)
            self.send_error(500, error_msg)
            return None

    def log_response_info(self, request_id, response_data, elapsed):
        """Log response."""
        timestamp = datetime.now().strftime('%H:%M:%S')

        # Extract key info
        choices = response_data.get('choices', [])
        finish_reason = 'unknown'
        content_length = 0

        if choices:
            finish_reason = choices[0].get('finish_reason', 'unknown')
            content = choices[0].get('message', {}).get('content', '')
            content_length = len(content)

        usage = response_data.get('usage', {})
        prompt_tokens = usage.get('prompt_tokens', 0)
        completion_tokens = usage.get('completion_tokens', 0)

        log_entry = f"""
RESPONSE #{request_id} at {timestamp} (took {elapsed:.2f}s)
{'=' * 80}
Finish Reason: {finish_reason}
Content Length: {content_length} characters
Prompt Tokens: {prompt_tokens}
Completion Tokens: {completion_tokens}
Total Tokens: {prompt_tokens + completion_tokens}

Full Response:
{json.dumps(response_data, indent=2)[:2000]}
...

"""

        # Print to terminal
        print(log_entry)

        # Write to log file
        with open(proxy_config.log_file, 'a') as f:
            f.write(log_entry + '\n')

        # Add to monitor if available
        if HAS_MONITOR:
            try:
                status = 'success' if finish_reason == 'stop' else 'warning'
                monitor_state.add_event(
                    status,
                    f'API Response #{request_id} ({elapsed:.1f}s)',
                    f'Finish: {finish_reason}, Tokens: {completion_tokens}'
                )
            except:
                pass

        # Check for issues
        if finish_reason == 'length':
            warning = f"\n⚠️  WARNING: Response was cut off! (finish_reason=length)"
            print(warning)
            with open(proxy_config.log_file, 'a') as f:
                f.write(warning + '\n')

    def log_error_info(self, request_id, error_msg):
        """Log error."""
        timestamp = datetime.now().strftime('%H:%M:%S')

        log_entry = f"""
❌ ERROR #{request_id} at {timestamp}
{'=' * 80}
{error_msg}

"""

        # Print to terminal
        print(log_entry, file=sys.stderr)

        # Write to log file
        with open(proxy_config.log_file, 'a') as f:
            f.write(log_entry + '\n')

        # Add to monitor if available
        if HAS_MONITOR:
            try:
                monitor_state.add_event('error', f'API Error #{request_id}', error_msg[:200])
            except:
                pass


def start_proxy_server(port=8889):
    """Start the proxy server."""
    server = HTTPServer(('localhost', port), ProxyHandler)

    print("\n" + "=" * 80)
    print("  🔄 LLM API PROXY SERVER")
    print("=" * 80)
    print(f"  Proxy: http://localhost:{port}")
    print(f"  Real Endpoint: {proxy_config.real_endpoint}")
    print(f"  Log File: {proxy_config.log_file}")
    print("=" * 80)
    print("\n  ✅ Proxy server is running...")
    print("     All API calls will be logged here in real-time.")
    print("     Press Ctrl+C to stop\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\nShutting down proxy server...")
        server.shutdown()


if __name__ == '__main__':
    # Setup SSL if needed
    mock_mode = os.getenv('MOCK_MODE', 'false').lower() == 'true'
    if not mock_mode:
        try:
            import rbc_security
            print("Setting up SSL certificates...")
            rbc_security.enable_certs()
            print("✓ SSL configured\n")
        except ImportError:
            print("⚠️  rbc_security not available\n")

    start_proxy_server()
