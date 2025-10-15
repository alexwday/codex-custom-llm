#!/usr/bin/env python3
"""
Test script for Enterprise Codex Wrapper

Run this to verify your setup is working correctly.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'


def print_check(message, status, details=None):
    """Print a check result."""
    symbol = "✓" if status else "✗"
    color = GREEN if status else RED
    print(f"{color}{symbol}{RESET} {message}")
    if details:
        print(f"  {details}")


def test_python_version():
    """Check Python version."""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print_check("Python version", True, f"Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print_check("Python version", False, f"Python {version.major}.{version.minor} (need 3.8+)")
        return False


def test_dependencies():
    """Check if required dependencies are installed."""
    all_ok = True

    # Check requests
    try:
        import requests
        print_check("requests library", True, f"version {requests.__version__}")
    except ImportError:
        print_check("requests library", False, "Not installed")
        all_ok = False

    # Check dotenv
    try:
        import dotenv
        print_check("python-dotenv library", True, f"version {dotenv.__version__}")
    except ImportError:
        print_check("python-dotenv library", False, "Not installed")
        all_ok = False

    return all_ok


def test_rbc_security():
    """Check if rbc_security is available (work computer only)."""
    try:
        import rbc_security
        print_check("rbc_security package", True, "Available")
        return True
    except ImportError:
        print_check("rbc_security package", False, "Not available (expected on personal computer)")
        return False


def test_env_file():
    """Check if .env file exists and is configured."""
    env_path = Path(__file__).parent / '.env'

    if not env_path.exists():
        print_check(".env file", False, "File not found. Copy .env.example to .env")
        return False

    load_dotenv()

    mock_mode = os.getenv('MOCK_MODE', '').lower() == 'true'
    print_check(".env file", True, f"Found (MOCK_MODE={mock_mode})")

    # Check required variables
    required_vars = {
        'MOCK_MODE': os.getenv('MOCK_MODE'),
        'LLM_API_BASE_URL': os.getenv('LLM_API_BASE_URL'),
        'LLM_MODEL_NAME': os.getenv('LLM_MODEL_NAME'),
    }

    if not mock_mode:
        required_vars.update({
            'OAUTH_ENDPOINT': os.getenv('OAUTH_ENDPOINT'),
            'OAUTH_CLIENT_ID': os.getenv('OAUTH_CLIENT_ID'),
            'OAUTH_CLIENT_SECRET': os.getenv('OAUTH_CLIENT_SECRET'),
        })

    all_set = True
    for var, value in required_vars.items():
        if not value or value.startswith('https://your-'):
            print_check(f"  {var}", False, "Not configured")
            all_set = False
        else:
            # Mask secrets
            if 'SECRET' in var:
                display_value = value[:10] + "..." if len(value) > 10 else "***"
            else:
                display_value = value
            print_check(f"  {var}", True, display_value)

    return all_set


def test_codex_cli():
    """Check if Codex CLI is installed."""
    import shutil

    codex_path = shutil.which('codex') or shutil.which('codex-cli')

    if codex_path:
        print_check("Codex CLI", True, f"Found at {codex_path}")
        return True
    else:
        print_check("Codex CLI", False, "Not found in PATH")
        print(f"  {YELLOW}Install with: npm install -g @openai/codex-cli{RESET}")
        return False


def test_oauth_manager():
    """Test OAuth manager in mock mode."""
    try:
        from oauth_manager import OAuthManager

        manager = OAuthManager(
            endpoint="https://test.com/token",
            client_id="test",
            client_secret="test",
            mock_mode=True
        )

        token = manager.get_token()
        if token and token.startswith("mock_token"):
            print_check("OAuth manager (mock mode)", True, "Working")
            return True
        else:
            print_check("OAuth manager (mock mode)", False, "Unexpected token")
            return False

    except Exception as e:
        print_check("OAuth manager (mock mode)", False, str(e))
        return False


def test_config_generator():
    """Test config generator."""
    try:
        from config_generator import _generate_toml

        toml = _generate_toml(
            base_url="https://test.com/v1",
            model_name="test-model",
            env_key="TEST_KEY",
            wire_api="chat"
        )

        if "model = " in toml and "base_url = " in toml:
            print_check("Config generator", True, "Working")
            return True
        else:
            print_check("Config generator", False, "Invalid output")
            return False

    except Exception as e:
        print_check("Config generator", False, str(e))
        return False


def main():
    """Run all tests."""
    print("=" * 50)
    print("Enterprise Codex Wrapper - Setup Test")
    print("=" * 50)
    print()

    results = []

    print("Checking Python environment...")
    results.append(test_python_version())
    print()

    print("Checking Python dependencies...")
    results.append(test_dependencies())
    print()

    print("Checking rbc_security (work computer only)...")
    has_rbc = test_rbc_security()
    print()

    print("Checking .env configuration...")
    results.append(test_env_file())
    print()

    print("Checking Codex CLI installation...")
    results.append(test_codex_cli())
    print()

    print("Testing wrapper modules...")
    results.append(test_oauth_manager())
    results.append(test_config_generator())
    print()

    # Summary
    print("=" * 50)
    if all(results):
        print(f"{GREEN}✓ All tests passed!{RESET}")
        print()
        print("You're ready to use the wrapper:")
        print("  cd /path/to/your/project")
        print("  python codex_wrapper.py 'your prompt here'")
    else:
        print(f"{RED}✗ Some tests failed{RESET}")
        print()
        print("Please fix the issues above before using the wrapper.")

        if not has_rbc:
            load_dotenv()
            if os.getenv('MOCK_MODE', '').lower() != 'true':
                print()
                print(f"{YELLOW}Note:{RESET} rbc_security not found but MOCK_MODE is false.")
                print("Either install rbc_security or set MOCK_MODE=true in .env")

    print("=" * 50)


if __name__ == '__main__':
    main()
