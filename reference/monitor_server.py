"""
Real-time Monitoring Server

Provides a live HTML dashboard showing:
- OAuth token status and refresh events
- Environment variables
- API call activity
- Wrapper status
- Configuration details

Run this in a separate terminal while using Codex to see real-time activity.
"""

import os
import json
import time
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class MonitorState:
    """Shared state for monitoring data."""

    def __init__(self):
        self.lock = threading.Lock()
        self.events = []
        self.max_events = 100
        self.start_time = datetime.now()
        self.token_refresh_count = 0
        self.last_token_refresh = None
        self.oauth_token_status = "Not initialized"
        self.codex_status = "Not started"
        self.config_path = str(Path.home() / '.codex' / 'config.toml')
        self.config_content = None
        self.env_vars = {}

        # API proxy stats
        self.api_request_count = 0
        self.api_response_count = 0
        self.api_error_count = 0
        self.last_request_time = None
        self.last_response_time = None
        self.api_requests = []  # Recent requests
        self.max_api_requests = 50

    def add_event(self, event_type, message, details=None):
        """Add an event to the log."""
        with self.lock:
            event = {
                'timestamp': datetime.now().isoformat(),
                'type': event_type,
                'message': message,
                'details': details
            }
            self.events.append(event)

            # Keep only the most recent events
            if len(self.events) > self.max_events:
                self.events = self.events[-self.max_events:]

    def add_api_request(self, request_id, model, messages_count, max_tokens):
        """Add API request info."""
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

    def update_api_response(self, request_id, finish_reason, tokens_used, elapsed_time):
        """Update API request with response info."""
        with self.lock:
            self.api_response_count += 1
            self.last_response_time = datetime.now()

            # Find and update the request
            for req in reversed(self.api_requests):
                if req['id'] == request_id:
                    req['status'] = 'success' if finish_reason == 'stop' else 'warning'
                    req['finish_reason'] = finish_reason
                    req['tokens_used'] = tokens_used
                    req['elapsed_time'] = elapsed_time
                    break

    def update_api_error(self, request_id, error_msg):
        """Update API request with error."""
        with self.lock:
            self.api_error_count += 1

            # Find and update the request
            for req in reversed(self.api_requests):
                if req['id'] == request_id:
                    req['status'] = 'error'
                    req['error'] = error_msg
                    break

    def get_state(self):
        """Get current state as JSON."""
        with self.lock:
            uptime = (datetime.now() - self.start_time).total_seconds()
            return {
                'uptime': int(uptime),
                'events': list(reversed(self.events)),  # Most recent first
                'token_refresh_count': self.token_refresh_count,
                'last_token_refresh': self.last_token_refresh.isoformat() if self.last_token_refresh else None,
                'oauth_token_status': self.oauth_token_status,
                'codex_status': self.codex_status,
                'config_path': self.config_path,
                'config_content': self.config_content,
                'env_vars': self.env_vars,
                'api_request_count': self.api_request_count,
                'api_response_count': self.api_response_count,
                'api_error_count': self.api_error_count,
                'last_request_time': self.last_request_time.isoformat() if self.last_request_time else None,
                'last_response_time': self.last_response_time.isoformat() if self.last_response_time else None,
                'api_requests': list(reversed(self.api_requests))  # Most recent first
            }

    def update_token_refresh(self):
        """Record a token refresh event."""
        with self.lock:
            self.token_refresh_count += 1
            self.last_token_refresh = datetime.now()
            self.oauth_token_status = "Active"

    def update_oauth_status(self, status):
        """Update OAuth token status."""
        with self.lock:
            self.oauth_token_status = status

    def update_codex_status(self, status):
        """Update Codex status."""
        with self.lock:
            self.codex_status = status

    def load_config(self):
        """Load current Codex configuration."""
        with self.lock:
            try:
                config_file = Path(self.config_path)
                if config_file.exists():
                    self.config_content = config_file.read_text()
                else:
                    self.config_content = "Config file not found"
            except Exception as e:
                self.config_content = f"Error reading config: {e}"

    def update_env_vars(self, env_vars):
        """Update tracked environment variables."""
        with self.lock:
            self.env_vars = env_vars


# Global monitor state
monitor_state = MonitorState()


class MonitorHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the monitoring dashboard."""

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

    def serve_dashboard(self):
        """Serve the HTML dashboard."""
        html = self.get_dashboard_html()
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())

    def serve_state(self):
        """Serve the current state as JSON."""
        state = monitor_state.get_state()
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(json.dumps(state).encode())

    def get_dashboard_html(self):
        """Generate the HTML dashboard."""
        return '''<!DOCTYPE html>
<html>
<head>
    <title>Codex Wrapper Monitor</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
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
            text-transform: uppercase;
            letter-spacing: 1px;
            sticky: top 0;
            background: #252526;
            padding-bottom: 10px;
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

        .config-content {
            background: #1e1e1e;
            padding: 15px;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            overflow-x: auto;
            white-space: pre;
            color: #d4d4d4;
            border: 1px solid #3e3e42;
        }

        .refresh-indicator {
            position: fixed;
            top: 20px;
            right: 20px;
            background: #252526;
            border: 1px solid #4ec9b0;
            padding: 8px 16px;
            border-radius: 4px;
            font-size: 12px;
            color: #4ec9b0;
        }
    </style>
</head>
<body>
    <div class="refresh-indicator" id="refresh-indicator">● Live</div>

    <div class="container">
        <h1>
            <div class="pulse"></div>
            Codex Wrapper Monitor
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
                    <span class="stat-label">Codex Status</span>
                    <span class="stat-value" id="codex-status">Unknown</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Token Refreshes</span>
                    <span class="stat-value" id="token-refreshes">0</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Last Refresh</span>
                    <span class="stat-value" id="last-refresh">Never</span>
                </div>
            </div>

            <div class="card">
                <h2>Environment</h2>
                <div id="env-vars"></div>
            </div>

            <div class="card" style="grid-column: 1 / -1;">
                <h2>Codex Configuration</h2>
                <div class="config-content" id="config-content">Loading...</div>
            </div>
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
                    document.getElementById('oauth-status').textContent = state.oauth_token_status;
                    document.getElementById('codex-status').textContent = state.codex_status;
                    document.getElementById('token-refreshes').textContent = state.token_refresh_count;
                    document.getElementById('last-refresh').textContent = formatTime(state.last_token_refresh);

                    // Update environment variables
                    const envVarsHtml = Object.entries(state.env_vars)
                        .map(([key, value]) => `
                            <div class="stat">
                                <span class="stat-label">${key}</span>
                                <span class="stat-value">${value}</span>
                            </div>
                        `).join('');
                    document.getElementById('env-vars').innerHTML = envVarsHtml || '<div class="stat-label">No environment variables tracked</div>';

                    // Update config
                    document.getElementById('config-content').textContent = state.config_content || 'No configuration loaded';

                    // Update events
                    const eventsHtml = state.events
                        .map(event => `
                            <div class="event ${getEventClass(event.type)}">
                                <div class="event-time">${formatTime(event.timestamp)}</div>
                                <div class="event-message">${event.message}</div>
                                ${event.details ? `<div class="event-details">${event.details}</div>` : ''}
                            </div>
                        `).join('');
                    document.getElementById('events').innerHTML = eventsHtml || '<div class="event-message">No events yet</div>';

                    // Flash refresh indicator
                    const indicator = document.getElementById('refresh-indicator');
                    indicator.style.opacity = '0.5';
                    setTimeout(() => indicator.style.opacity = '1', 100);
                })
                .catch(error => {
                    console.error('Error fetching state:', error);
                });
        }

        // Update every second
        updateDashboard();
        setInterval(updateDashboard, 1000);
    </script>
</body>
</html>'''


def start_monitor_server(port=8888):
    """Start the monitoring server."""
    server = HTTPServer(('localhost', port), MonitorHandler)

    logger.info(f"Monitor server starting on http://localhost:{port}")
    monitor_state.add_event('info', f'Monitor server started on port {port}')

    # Run in a separate thread
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    return server


if __name__ == '__main__':
    # Test the monitor server
    logging.basicConfig(level=logging.INFO)

    print("Starting monitor server...")
    server = start_monitor_server()

    print("\n" + "=" * 60)
    print("Monitor Dashboard: http://localhost:8888")
    print("=" * 60)
    print("\nPress Ctrl+C to stop\n")

    # Simulate some events
    monitor_state.add_event('info', 'Test event: Server started')
    monitor_state.update_oauth_status('Active')
    monitor_state.update_codex_status('Running')

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
