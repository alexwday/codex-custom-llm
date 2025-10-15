#!/usr/bin/env python3
"""
Test your LLM endpoint directly

This bypasses Codex entirely and tests your endpoint to see if the issue
is with the API itself or with Codex CLI.
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv

# Load environment
load_dotenv()

def test_endpoint():
    """Test the LLM endpoint directly."""

    # Check if mock mode
    mock_mode = os.getenv('MOCK_MODE', 'false').lower() == 'true'
    if mock_mode:
        print("⚠️  MOCK_MODE is enabled. This test requires a real endpoint.")
        print("   Set MOCK_MODE=false in .env and provide real credentials.\n")
        return False

    # Get config
    base_url = os.getenv('LLM_API_BASE_URL')
    model_name = os.getenv('LLM_MODEL_NAME', 'gpt-4-internal')
    max_tokens = int(os.getenv('MAX_TOKENS', '4096'))

    # Get OAuth token
    print("=" * 70)
    print("ENDPOINT TEST")
    print("=" * 70)
    print(f"Base URL: {base_url}")
    print(f"Model: {model_name}")
    print(f"Max Tokens: {max_tokens}")
    print()

    # Check for SSL setup
    try:
        import rbc_security
        print("Setting up SSL certificates...")
        rbc_security.enable_certs()
        print("✓ SSL certificates configured\n")
    except ImportError:
        print("⚠️  rbc_security not available (running without SSL certs)\n")

    # Get OAuth token
    print("Fetching OAuth token...")
    try:
        from oauth_manager import OAuthManager
        oauth = OAuthManager(
            endpoint=os.getenv('OAUTH_ENDPOINT'),
            client_id=os.getenv('OAUTH_CLIENT_ID'),
            client_secret=os.getenv('OAUTH_CLIENT_SECRET'),
            mock_mode=False
        )
        token = oauth.get_token()
        if not token:
            print("✗ Failed to get OAuth token\n")
            return False
        print(f"✓ OAuth token obtained: {token[:20]}...\n")
    except Exception as e:
        print(f"✗ OAuth error: {e}\n")
        return False

    # Test the endpoint
    print("=" * 70)
    print("TEST 1: Simple short request")
    print("=" * 70)

    success = send_request(
        base_url=base_url,
        model=model_name,
        token=token,
        messages=[{"role": "user", "content": "Say 'hello' and nothing else."}],
        max_tokens=max_tokens
    )

    if not success:
        return False

    print("\n" + "=" * 70)
    print("TEST 2: Longer request (code analysis)")
    print("=" * 70)

    success = send_request(
        base_url=base_url,
        model=model_name,
        token=token,
        messages=[{"role": "user", "content": "Write a Python function that calculates fibonacci numbers. Include docstrings and type hints."}],
        max_tokens=max_tokens
    )

    if not success:
        return False

    print("\n" + "=" * 70)
    print("TEST 3: Multi-step reasoning")
    print("=" * 70)

    success = send_request(
        base_url=base_url,
        model=model_name,
        token=token,
        messages=[{"role": "user", "content": "List the first 5 prime numbers and explain why each one is prime."}],
        max_tokens=max_tokens
    )

    return success


def send_request(base_url, model, token, messages, max_tokens):
    """Send a request to the LLM endpoint."""

    # Construct URL
    if not base_url.endswith('/'):
        base_url += '/'
    url = base_url + 'chat/completions'

    # Prepare request
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    payload = {
        'model': model,
        'messages': messages,
        'max_tokens': max_tokens,
        'stream': False  # Non-streaming for testing
    }

    print(f"Request: {messages[0]['content'][:60]}...")
    print(f"Endpoint: {url}")
    print(f"Sending request...\n")

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=60  # 60 second timeout
        )

        # Check response
        if response.status_code != 200:
            print(f"✗ HTTP {response.status_code}")
            print(f"  Response: {response.text[:200]}\n")
            return False

        # Parse response
        try:
            data = response.json()
        except json.JSONDecodeError:
            print(f"✗ Invalid JSON response")
            print(f"  Response: {response.text[:200]}\n")
            return False

        # Extract content
        if 'choices' not in data or len(data['choices']) == 0:
            print(f"✗ No choices in response")
            print(f"  Response: {json.dumps(data, indent=2)[:500]}\n")
            return False

        content = data['choices'][0].get('message', {}).get('content', '')
        finish_reason = data['choices'][0].get('finish_reason', 'unknown')

        # Check usage
        usage = data.get('usage', {})
        prompt_tokens = usage.get('prompt_tokens', 0)
        completion_tokens = usage.get('completion_tokens', 0)
        total_tokens = usage.get('total_tokens', 0)

        print(f"✓ Success!")
        print(f"  Finish reason: {finish_reason}")
        print(f"  Tokens - Prompt: {prompt_tokens}, Completion: {completion_tokens}, Total: {total_tokens}")
        print(f"  Response length: {len(content)} characters")
        print(f"\n  Content preview:")
        print("  " + "-" * 66)
        for line in content.split('\n')[:10]:  # First 10 lines
            print(f"  {line[:66]}")
        if len(content.split('\n')) > 10:
            print(f"  ... ({len(content.split('\n')) - 10} more lines)")
        print("  " + "-" * 66)

        # Check for issues
        if finish_reason == 'length':
            print("\n  ⚠️  WARNING: Response was cut off due to length limit!")
            print(f"     Consider increasing MAX_TOKENS (current: {max_tokens})")

        if completion_tokens >= max_tokens * 0.9:
            print("\n  ⚠️  WARNING: Response used 90%+ of max_tokens!")
            print(f"     Increase MAX_TOKENS to avoid cut-offs")

        return True

    except requests.exceptions.Timeout:
        print("✗ Request timed out after 60 seconds")
        print("  Your endpoint may be slow or unresponsive\n")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"✗ Connection error: {e}")
        print("  Check your network connection and endpoint URL\n")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}\n")
        return False


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("  LLM ENDPOINT DIAGNOSTIC TEST")
    print("=" * 70)
    print()
    print("This script tests your endpoint directly, bypassing Codex CLI.")
    print("Use this to determine if issues are with the endpoint or Codex.\n")

    success = test_endpoint()

    print("\n" + "=" * 70)
    if success:
        print("  ✓ ALL TESTS PASSED")
        print("=" * 70)
        print()
        print("Your endpoint is working correctly. If Codex still has issues,")
        print("the problem is likely with Codex CLI itself, not your setup.")
        print()
        print("Next steps:")
        print("  1. Try using Codex with shorter prompts")
        print("  2. Check Codex CLI version: codex --version")
        print("  3. Try updating Codex: npm update -g @openai/codex-cli")
        print("  4. Check Codex logs for errors")
    else:
        print("  ✗ TESTS FAILED")
        print("=" * 70)
        print()
        print("Your endpoint has issues. Fix these before using Codex.")
        print()
        print("Common issues:")
        print("  - OAuth credentials incorrect")
        print("  - Endpoint URL wrong")
        print("  - Network connectivity issues")
        print("  - SSL certificate problems")
        print("  - API rate limiting")
    print()
