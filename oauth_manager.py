"""
OAuth Token Manager

Handles OAuth2 client credentials flow for enterprise authentication.
Supports mock mode for local development without real OAuth endpoints.
"""

import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)


class OAuthManager:
    """Manages OAuth token fetching and caching."""

    def __init__(self, endpoint: str, client_id: str, client_secret: str, mock_mode: bool = False):
        """
        Initialize OAuth manager.

        Args:
            endpoint: OAuth token endpoint URL
            client_id: OAuth client ID
            client_secret: OAuth client secret
            mock_mode: If True, return mock tokens instead of real ones
        """
        self.endpoint = endpoint
        self.client_id = client_id
        self.client_secret = client_secret
        self.mock_mode = mock_mode
        self._cached_token: Optional[str] = None

    def get_token(self) -> Optional[str]:
        """
        Fetch a new OAuth token.

        Returns:
            Access token string, or None if fetch failed
        """
        if self.mock_mode:
            return self._get_mock_token()

        try:
            logger.debug(f"Requesting OAuth token from {self.endpoint}")

            # OAuth2 client credentials flow
            response = requests.post(
                self.endpoint,
                data={
                    'grant_type': 'client_credentials',
                    'client_id': self.client_id,
                    'client_secret': self.client_secret
                },
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                timeout=30
            )

            response.raise_for_status()
            token_data = response.json()

            # Extract access token (standard OAuth2 response format)
            access_token = token_data.get('access_token')

            if not access_token:
                logger.error("No access_token in OAuth response")
                return None

            self._cached_token = access_token
            logger.debug("Successfully obtained OAuth token")

            # Log token info (but not the token itself)
            token_type = token_data.get('token_type', 'Bearer')
            expires_in = token_data.get('expires_in', 'unknown')
            logger.info(f"Token obtained: type={token_type}, expires_in={expires_in}s")

            return access_token

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch OAuth token: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching OAuth token: {e}")
            return None

    def _get_mock_token(self) -> str:
        """
        Return a mock token for local development.

        Returns:
            A fake but valid-looking token string
        """
        logger.info("Mock mode: Using mock OAuth token")
        return "mock_token_for_local_development_" + "x" * 50

    def refresh_token(self) -> Optional[str]:
        """
        Refresh the OAuth token (same as get_token for client credentials flow).

        In client credentials flow, there's no refresh token - you just request
        a new access token each time.

        Returns:
            New access token string, or None if fetch failed
        """
        logger.debug("Refreshing OAuth token")
        return self.get_token()

    @property
    def has_valid_token(self) -> bool:
        """
        Check if we have a cached token.

        Note: This doesn't validate the token, just checks if one exists.
        In production, the token refresh mechanism handles expiry.

        Returns:
            True if a token is cached, False otherwise
        """
        return self._cached_token is not None


# Example usage and testing
if __name__ == '__main__':
    # Test in mock mode
    print("Testing OAuthManager in mock mode...")
    manager = OAuthManager(
        endpoint="https://fake-endpoint.com/token",
        client_id="test-client",
        client_secret="test-secret",
        mock_mode=True
    )

    token = manager.get_token()
    print(f"Obtained token: {token[:50]}...")

    # Test refresh
    new_token = manager.refresh_token()
    print(f"Refreshed token: {new_token[:50]}...")
    print(f"Has valid token: {manager.has_valid_token}")
