"""Secure token storage for delegated authentication."""

import json
import os
from pathlib import Path
from typing import Optional
import logging


class TokenStorage:
    """Manages storage and retrieval of OAuth tokens."""

    def __init__(
        self, storage_path: Optional[Path] = None, logger: Optional[logging.Logger] = None
    ):
        """Initialize token storage.

        Args:
            storage_path: Path to token storage directory (default: .tokens/ in orgplan dir)
            logger: Optional logger
        """
        self.logger = logger or logging.getLogger(__name__)

        if storage_path is None:
            # Default to .tokens/ in current directory
            storage_path = Path.cwd() / ".tokens"

        self.storage_path = storage_path
        self.token_file = self.storage_path / "tokens.json"

        # Ensure storage directory exists with secure permissions
        self._ensure_storage_directory()

    def _ensure_storage_directory(self):
        """Create storage directory with secure permissions."""
        if not self.storage_path.exists():
            self.storage_path.mkdir(mode=0o700, parents=True)
            self.logger.debug(f"Created token storage directory: {self.storage_path}")

        # Ensure directory has secure permissions (owner only)
        try:
            os.chmod(self.storage_path, 0o700)
        except OSError as e:
            self.logger.warning(f"Could not set secure permissions on {self.storage_path}: {e}")

    def save_tokens(
        self,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_in: Optional[int] = None,
    ):
        """Save tokens to storage.

        Args:
            access_token: OAuth access token
            refresh_token: OAuth refresh token (optional)
            expires_in: Token expiry time in seconds (optional)
        """
        import time

        token_data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": time.time() + expires_in if expires_in else None,
        }

        try:
            # Write with secure permissions
            with open(self.token_file, "w") as f:
                json.dump(token_data, f, indent=2)

            # Ensure file has secure permissions (owner read/write only)
            os.chmod(self.token_file, 0o600)

            self.logger.debug(f"Saved tokens to {self.token_file}")
        except OSError as e:
            self.logger.error(f"Failed to save tokens: {e}")
            raise

    def load_tokens(self) -> Optional[dict]:
        """Load tokens from storage.

        Returns:
            Dictionary with token data or None if no tokens exist
        """
        if not self.token_file.exists():
            self.logger.debug("No token file found")
            return None

        try:
            with open(self.token_file, "r") as f:
                token_data = json.load(f)

            self.logger.debug("Loaded tokens from storage")
            return token_data
        except (OSError, json.JSONDecodeError) as e:
            self.logger.error(f"Failed to load tokens: {e}")
            return None

    def get_access_token(self) -> Optional[str]:
        """Get current access token if valid.

        Returns:
            Access token or None if expired/missing
        """
        import time

        token_data = self.load_tokens()
        if not token_data:
            return None

        # Check if token is expired
        expires_at = token_data.get("expires_at")
        if expires_at and time.time() >= expires_at:
            self.logger.debug("Access token expired")
            return None

        return token_data.get("access_token")

    def get_refresh_token(self) -> Optional[str]:
        """Get refresh token.

        Returns:
            Refresh token or None if not available
        """
        token_data = self.load_tokens()
        if not token_data:
            return None

        return token_data.get("refresh_token")

    def clear_tokens(self):
        """Remove all stored tokens."""
        if self.token_file.exists():
            try:
                self.token_file.unlink()
                self.logger.info("Cleared stored tokens")
            except OSError as e:
                self.logger.error(f"Failed to clear tokens: {e}")
                raise

    def has_tokens(self) -> bool:
        """Check if tokens exist.

        Returns:
            True if token file exists
        """
        return self.token_file.exists()
