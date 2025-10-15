#!/usr/bin/env python3
"""
Enterprise Codex CLI Wrapper

This wrapper enables Codex CLI to work with enterprise authentication and SSL requirements.
The wrapper is designed to be called from any directory - it will pass through your current
working directory to Codex so it operates on the correct project.

Usage:
    python codex_wrapper.py [codex arguments...]
    python codex_wrapper.py --monitor [codex arguments...]  # Enable monitoring dashboard

Example:
    cd /path/to/your/project
    python /path/to/codex_wrapper.py "fix the bug in main.py"

    # With monitoring dashboard
    python /path/to/codex_wrapper.py --monitor "analyze this codebase"

The wrapper will:
1. Set up SSL certificates (via rbc_security)
2. Fetch and refresh OAuth tokens
3. Configure Codex with custom LLM endpoint
4. Launch Codex in your current directory
5. Optional: Start monitoring dashboard at http://localhost:8888
"""

import os
import sys
import subprocess
import time
import threading
import logging
import webbrowser
from pathlib import Path
from dotenv import load_dotenv

# Import our modules
from oauth_manager import OAuthManager
from config_generator import generate_codex_config
from monitor_server import start_monitor_server, monitor_state

# Logging will be configured in __init__ based on VERBOSE_MODE
logger = logging.getLogger(__name__)

# Environment variable name for the OAuth token
TOKEN_ENV_VAR = "CUSTOM_LLM_API_KEY"


class CodexWrapper:
    """Main wrapper class that coordinates SSL, OAuth, and Codex launching."""

    def __init__(self, enable_monitor=False):
        """Initialize the wrapper and load configuration."""
        # Load environment variables from .env file
        load_dotenv()

        self.mock_mode = os.getenv('MOCK_MODE', 'false').lower() == 'true'
        self.verbose_mode = os.getenv('VERBOSE_MODE', 'false').lower() == 'true'
        self.enable_monitor = enable_monitor
        self.refresh_interval = int(os.getenv('TOKEN_REFRESH_INTERVAL', '900'))  # 15 minutes
        self.oauth_manager = None
        self.refresh_thread = None
        self.stop_refresh = threading.Event()
        self.monitor_server = None
        self.codex_log_file = None

        # Configure logging based on verbose mode
        log_level = logging.DEBUG if self.verbose_mode else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            force=True  # Override any existing config
        )

        # If monitoring, create log file for Codex output
        if self.enable_monitor:
            log_dir = Path.home() / '.codex' / 'logs'
            log_dir.mkdir(parents=True, exist_ok=True)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            self.codex_log_file = log_dir / f'codex_output_{timestamp}.log'

        logger.info(f"Initializing Codex wrapper (mock_mode={self.mock_mode}, verbose_mode={self.verbose_mode}, monitor={self.enable_monitor})")

        if self.enable_monitor:
            monitor_state.add_event('info', 'Codex wrapper initializing', f'mock_mode={self.mock_mode}')
            logger.info(f"Codex output will be logged to: {self.codex_log_file}")

    def setup_ssl_certificates(self):
        """Set up SSL certificates using rbc_security package."""
        if self.mock_mode:
            logger.info("Mock mode: Skipping SSL certificate setup")
            if self.enable_monitor:
                monitor_state.add_event('info', 'SSL setup skipped (mock mode)')
            return

        try:
            import rbc_security
            logger.info("Setting up SSL certificates via rbc_security...")
            if self.enable_monitor:
                monitor_state.add_event('info', 'Setting up SSL certificates')

            rbc_security.enable_certs()
            logger.info("SSL certificates configured successfully")

            if self.enable_monitor:
                monitor_state.add_event('success', 'SSL certificates configured')
                monitor_state.update_env_vars({
                    'SSL_CERT_FILE': os.environ.get('SSL_CERT_FILE', 'Not set'),
                    'REQUESTS_CA_BUNDLE': os.environ.get('REQUESTS_CA_BUNDLE', 'Not set')
                })
        except ImportError:
            logger.error("rbc_security package not found. Install it or enable MOCK_MODE.")
            if self.enable_monitor:
                monitor_state.add_event('error', 'rbc_security not found')
            sys.exit(1)
        except Exception as e:
            logger.error(f"Failed to set up SSL certificates: {e}")
            if self.enable_monitor:
                monitor_state.add_event('error', f'SSL setup failed: {e}')
            sys.exit(1)

    def setup_oauth(self):
        """Initialize OAuth manager and fetch initial token."""
        self.oauth_manager = OAuthManager(
            endpoint=os.getenv('OAUTH_ENDPOINT'),
            client_id=os.getenv('OAUTH_CLIENT_ID'),
            client_secret=os.getenv('OAUTH_CLIENT_SECRET'),
            mock_mode=self.mock_mode
        )

        # Fetch initial token
        logger.info("Fetching initial OAuth token...")
        if self.enable_monitor:
            monitor_state.add_event('info', 'Fetching initial OAuth token')

        token = self.oauth_manager.get_token()

        if not token:
            logger.error("Failed to obtain OAuth token")
            if self.enable_monitor:
                monitor_state.add_event('error', 'Failed to obtain OAuth token')
                monitor_state.update_oauth_status('Failed')
            sys.exit(1)

        # Set token in environment variable
        os.environ[TOKEN_ENV_VAR] = token
        logger.info("OAuth token obtained and set in environment")

        if self.enable_monitor:
            monitor_state.add_event('success', 'OAuth token obtained')
            monitor_state.update_oauth_status('Active')
            monitor_state.update_token_refresh()
            monitor_state.update_env_vars({
                'CUSTOM_LLM_API_KEY': token[:20] + '...',
                'OAUTH_ENDPOINT': os.getenv('OAUTH_ENDPOINT', 'Not set'),
                'LLM_API_BASE_URL': os.getenv('LLM_API_BASE_URL', 'Not set')
            })

    def start_token_refresh(self):
        """Start background thread to refresh OAuth tokens."""
        def refresh_loop():
            while not self.stop_refresh.wait(self.refresh_interval):
                logger.info("Refreshing OAuth token...")
                if self.enable_monitor:
                    monitor_state.add_event('info', 'Refreshing OAuth token')

                token = self.oauth_manager.get_token()
                if token:
                    os.environ[TOKEN_ENV_VAR] = token
                    logger.info("OAuth token refreshed successfully")
                    if self.enable_monitor:
                        monitor_state.add_event('success', 'OAuth token refreshed')
                        monitor_state.update_token_refresh()
                        monitor_state.update_env_vars({
                            'CUSTOM_LLM_API_KEY': token[:20] + '...',
                        })
                else:
                    logger.warning("Failed to refresh OAuth token")
                    if self.enable_monitor:
                        monitor_state.add_event('warning', 'Failed to refresh OAuth token')
                        monitor_state.update_oauth_status('Refresh failed')

        self.refresh_thread = threading.Thread(target=refresh_loop, daemon=True)
        self.refresh_thread.start()
        logger.info(f"Token refresh thread started (interval: {self.refresh_interval}s)")

        if self.enable_monitor:
            monitor_state.add_event('info', f'Token refresh thread started (interval: {self.refresh_interval}s)')

    def setup_codex_config(self):
        """Generate Codex configuration file."""
        max_tokens_str = os.getenv('MAX_TOKENS')
        max_tokens = int(max_tokens_str) if max_tokens_str else None

        config_data = {
            'base_url': os.getenv('LLM_API_BASE_URL'),
            'model_name': os.getenv('LLM_MODEL_NAME', 'gpt-4-internal'),
            'env_key': TOKEN_ENV_VAR,
            'wire_api': os.getenv('WIRE_API', 'chat'),
            'query_params': os.getenv('QUERY_PARAMS', None),
            'max_tokens': max_tokens
        }

        logger.info("Generating Codex configuration...")
        if max_tokens:
            logger.info(f"Setting max_tokens to {max_tokens} for longer responses")
            if self.enable_monitor:
                monitor_state.add_event('info', f'Setting max_tokens to {max_tokens}')

        generate_codex_config(config_data)
        logger.info("Codex configuration created")

        if self.enable_monitor:
            monitor_state.add_event('success', 'Codex configuration generated')
            monitor_state.load_config()

    def launch_codex(self, codex_args):
        """
        Launch Codex CLI as a subprocess.

        The subprocess will:
        - Inherit all environment variables (including SSL and OAuth token)
        - Run in the current working directory (user's project)
        - Receive all command-line arguments passed to this wrapper
        """
        # Find codex binary
        codex_binary = self._find_codex_binary()

        if not codex_binary:
            logger.error("Codex CLI not found. Install it with: npm install -g @openai/codex-cli")
            if self.enable_monitor:
                monitor_state.add_event('error', 'Codex CLI not found')
            sys.exit(1)

        logger.info(f"Launching Codex from directory: {os.getcwd()}")
        logger.info(f"Codex command: {codex_binary} {' '.join(codex_args)}")

        if self.enable_monitor:
            monitor_state.add_event('info', f'Launching Codex from: {os.getcwd()}')
            monitor_state.add_event('info', f'Codex command: {" ".join(codex_args)}')
            monitor_state.update_codex_status('Running')

        if self.verbose_mode:
            logger.debug("=" * 60)
            logger.debug("VERBOSE MODE: Monitoring API calls")
            logger.debug("=" * 60)
            logger.debug(f"Environment variables set:")
            logger.debug(f"  CUSTOM_LLM_API_KEY: {os.environ.get(TOKEN_ENV_VAR, 'NOT SET')[:20]}...")
            logger.debug(f"  SSL_CERT_FILE: {os.environ.get('SSL_CERT_FILE', 'NOT SET')}")
            logger.debug(f"  Current directory: {os.getcwd()}")
            logger.debug("=" * 60)

        try:
            # Launch Codex with inherited environment and current working directory
            # If monitoring, capture stderr to log errors
            if self.enable_monitor:
                process = subprocess.Popen(
                    [codex_binary] + codex_args,
                    env=os.environ.copy(),
                    cwd=os.getcwd(),
                    stdout=sys.stdout,
                    stderr=subprocess.PIPE,  # Capture stderr
                    stdin=sys.stdin,
                    text=True,
                    bufsize=1  # Line buffered
                )

                # Monitor stderr in background thread
                def log_stderr():
                    with open(self.codex_log_file, 'w') as log_file:
                        log_file.write(f"Codex CLI Output Log\n")
                        log_file.write(f"Started: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                        log_file.write(f"Command: {' '.join([codex_binary] + codex_args)}\n")
                        log_file.write(f"Working Directory: {os.getcwd()}\n")
                        log_file.write("=" * 70 + "\n\n")

                        for line in process.stderr:
                            line = line.strip()
                            if line:
                                # Log to file
                                log_file.write(f"{time.strftime('%H:%M:%S')} | {line}\n")
                                log_file.flush()

                                # Log to wrapper logs
                                logger.error(f"CODEX: {line}")

                                # Add to monitor
                                monitor_state.add_event('error', f'Codex: {line[:100]}')

                                # Print to terminal
                                print(f"[CODEX ERROR] {line}", file=sys.stderr)

                stderr_thread = threading.Thread(target=log_stderr, daemon=True)
                stderr_thread.start()
            else:
                # Normal mode - pass through all output
                process = subprocess.Popen(
                    [codex_binary] + codex_args,
                    env=os.environ.copy(),
                    cwd=os.getcwd(),
                    stdout=sys.stdout,
                    stderr=sys.stderr,
                    stdin=sys.stdin
                )

            # Wait for Codex to complete
            return_code = process.wait()
            logger.info(f"Codex exited with code: {return_code}")

            if self.enable_monitor:
                if return_code == 0:
                    monitor_state.add_event('success', f'Codex exited successfully')
                else:
                    monitor_state.add_event('warning', f'Codex exited with code: {return_code}')
                monitor_state.update_codex_status('Stopped')

            return return_code

        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
            if self.enable_monitor:
                monitor_state.add_event('warning', 'Received interrupt signal')
                monitor_state.update_codex_status('Interrupted')
            process.terminate()
            return 130
        except Exception as e:
            logger.error(f"Failed to launch Codex: {e}")
            if self.enable_monitor:
                monitor_state.add_event('error', f'Failed to launch Codex: {e}')
                monitor_state.update_codex_status('Failed')
            return 1

    def _find_codex_binary(self):
        """Find the codex binary in PATH."""
        # Try common names
        for name in ['codex', 'codex-cli']:
            binary = self._which(name)
            if binary:
                return binary
        return None

    def _which(self, program):
        """Find program in PATH (cross-platform)."""
        def is_exe(fpath):
            return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

        fpath, fname = os.path.split(program)
        if fpath:
            if is_exe(program):
                return program
        else:
            for path in os.environ.get("PATH", "").split(os.pathsep):
                exe_file = os.path.join(path, program)
                if is_exe(exe_file):
                    return exe_file
        return None

    def run(self, codex_args):
        """Main entry point - run the complete wrapper flow."""
        try:
            # Optional: Start monitor server
            if self.enable_monitor:
                self.monitor_server = start_monitor_server()
                print("\n" + "=" * 70)
                print("  🖥️  MONITOR DASHBOARD: http://localhost:8888")
                print("=" * 70)
                print("  Opening dashboard in your browser...")
                print("  Codex errors will be logged to:")
                print(f"    {self.codex_log_file}")
                print("  Keep this window open to see real-time activity!")
                print("=" * 70 + "\n")

                # Open browser
                time.sleep(0.5)  # Give server time to start
                try:
                    webbrowser.open('http://localhost:8888')
                except:
                    pass  # If browser open fails, that's okay

                time.sleep(1)  # Let user see the message

            # Step 1: Set up SSL certificates
            self.setup_ssl_certificates()

            # Step 2: Set up OAuth and get initial token
            self.setup_oauth()

            # Step 3: Start token refresh thread
            self.start_token_refresh()

            # Step 4: Generate Codex configuration
            self.setup_codex_config()

            # Step 5: Launch Codex
            return self.launch_codex(codex_args)

        finally:
            # Clean shutdown
            self.stop_refresh.set()
            if self.refresh_thread:
                self.refresh_thread.join(timeout=1)

            if self.enable_monitor:
                monitor_state.add_event('info', 'Wrapper shutting down')
                print("\n" + "=" * 70)
                print("  Monitor dashboard: http://localhost:8888")
                if self.codex_log_file and self.codex_log_file.exists():
                    print(f"  Codex error log: {self.codex_log_file}")
                print("  (Press Ctrl+C again to fully exit)")
                print("=" * 70 + "\n")


def main():
    """Main entry point for the script."""
    # Check for --monitor flag
    enable_monitor = False
    codex_args = []

    for arg in sys.argv[1:]:
        if arg == '--monitor':
            enable_monitor = True
        else:
            codex_args.append(arg)

    if not codex_args:
        print("Enterprise Codex CLI Wrapper")
        print("\nUsage: python codex_wrapper.py [--monitor] [codex arguments...]")
        print("\nThis wrapper will:")
        print("  1. Set up SSL certificates (via rbc_security)")
        print("  2. Manage OAuth token authentication")
        print("  3. Configure Codex for your enterprise LLM endpoint")
        print("  4. Launch Codex in your current directory")
        print("  5. [Optional] Start real-time monitoring dashboard")
        print("\nOptions:")
        print("  --monitor    Launch monitoring dashboard at http://localhost:8888")
        print("\nExamples:")
        print("  cd /path/to/your/project")
        print("  python /path/to/codex_wrapper.py 'help me refactor main.py'")
        print("  python /path/to/codex_wrapper.py --monitor 'analyze this codebase'")
        print("\nNote: Run this from your project directory, not the wrapper directory!")
        sys.exit(0)

    wrapper = CodexWrapper(enable_monitor=enable_monitor)
    exit_code = wrapper.run(codex_args)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
