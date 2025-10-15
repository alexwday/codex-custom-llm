#!/usr/bin/env python3
"""
Enterprise Codex CLI Wrapper

This wrapper enables Codex CLI to work with enterprise authentication and SSL requirements.
The wrapper is designed to be called from any directory - it will pass through your current
working directory to Codex so it operates on the correct project.

Usage:
    python codex_wrapper.py [codex arguments...]

Example:
    cd /path/to/your/project
    python /path/to/codex_wrapper.py "fix the bug in main.py"

The wrapper will:
1. Set up SSL certificates (via rbc_security)
2. Fetch and refresh OAuth tokens
3. Configure Codex with custom LLM endpoint
4. Launch Codex in your current directory
"""

import os
import sys
import subprocess
import time
import threading
import logging
from pathlib import Path
from dotenv import load_dotenv

# Import our modules
from oauth_manager import OAuthManager
from config_generator import generate_codex_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variable name for the OAuth token
TOKEN_ENV_VAR = "CUSTOM_LLM_API_KEY"


class CodexWrapper:
    """Main wrapper class that coordinates SSL, OAuth, and Codex launching."""

    def __init__(self):
        """Initialize the wrapper and load configuration."""
        # Load environment variables from .env file
        load_dotenv()

        self.mock_mode = os.getenv('MOCK_MODE', 'false').lower() == 'true'
        self.refresh_interval = int(os.getenv('TOKEN_REFRESH_INTERVAL', '900'))  # 15 minutes
        self.oauth_manager = None
        self.refresh_thread = None
        self.stop_refresh = threading.Event()

        logger.info(f"Initializing Codex wrapper (mock_mode={self.mock_mode})")

    def setup_ssl_certificates(self):
        """Set up SSL certificates using rbc_security package."""
        if self.mock_mode:
            logger.info("Mock mode: Skipping SSL certificate setup")
            return

        try:
            import rbc_security
            logger.info("Setting up SSL certificates via rbc_security...")
            rbc_security.enable_certs()
            logger.info("SSL certificates configured successfully")
        except ImportError:
            logger.error("rbc_security package not found. Install it or enable MOCK_MODE.")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Failed to set up SSL certificates: {e}")
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
        token = self.oauth_manager.get_token()

        if not token:
            logger.error("Failed to obtain OAuth token")
            sys.exit(1)

        # Set token in environment variable
        os.environ[TOKEN_ENV_VAR] = token
        logger.info("OAuth token obtained and set in environment")

    def start_token_refresh(self):
        """Start background thread to refresh OAuth tokens."""
        def refresh_loop():
            while not self.stop_refresh.wait(self.refresh_interval):
                logger.info("Refreshing OAuth token...")
                token = self.oauth_manager.get_token()
                if token:
                    os.environ[TOKEN_ENV_VAR] = token
                    logger.info("OAuth token refreshed successfully")
                else:
                    logger.warning("Failed to refresh OAuth token")

        self.refresh_thread = threading.Thread(target=refresh_loop, daemon=True)
        self.refresh_thread.start()
        logger.info(f"Token refresh thread started (interval: {self.refresh_interval}s)")

    def setup_codex_config(self):
        """Generate Codex configuration file."""
        config_data = {
            'base_url': os.getenv('LLM_API_BASE_URL'),
            'model_name': os.getenv('LLM_MODEL_NAME', 'gpt-4-internal'),
            'env_key': TOKEN_ENV_VAR,
            'wire_api': os.getenv('WIRE_API', 'chat'),
            'query_params': os.getenv('QUERY_PARAMS', None)
        }

        logger.info("Generating Codex configuration...")
        generate_codex_config(config_data)
        logger.info("Codex configuration created")

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
            sys.exit(1)

        logger.info(f"Launching Codex from directory: {os.getcwd()}")
        logger.info(f"Codex command: {codex_binary} {' '.join(codex_args)}")

        try:
            # Launch Codex with inherited environment and current working directory
            process = subprocess.Popen(
                [codex_binary] + codex_args,
                env=os.environ.copy(),  # Inherit all environment variables
                cwd=os.getcwd(),         # Use current working directory
                stdout=sys.stdout,
                stderr=sys.stderr,
                stdin=sys.stdin
            )

            # Wait for Codex to complete
            return_code = process.wait()
            logger.info(f"Codex exited with code: {return_code}")
            return return_code

        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
            process.terminate()
            return 130
        except Exception as e:
            logger.error(f"Failed to launch Codex: {e}")
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


def main():
    """Main entry point for the script."""
    # All arguments after the script name are passed to Codex
    codex_args = sys.argv[1:]

    if not codex_args:
        print("Enterprise Codex CLI Wrapper")
        print("\nUsage: python codex_wrapper.py [codex arguments...]")
        print("\nThis wrapper will:")
        print("  1. Set up SSL certificates (via rbc_security)")
        print("  2. Manage OAuth token authentication")
        print("  3. Configure Codex for your enterprise LLM endpoint")
        print("  4. Launch Codex in your current directory")
        print("\nExample:")
        print("  cd /path/to/your/project")
        print("  python /path/to/codex_wrapper.py 'help me refactor main.py'")
        print("\nNote: Run this from your project directory, not the wrapper directory!")
        sys.exit(0)

    wrapper = CodexWrapper()
    exit_code = wrapper.run(codex_args)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
