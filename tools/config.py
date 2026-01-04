"""Configuration management for orgplan-todo sync."""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


class Config:
    """Configuration holder for sync operations."""

    def __init__(
        self,
        client_id: str,
        tenant_id: str,
        todo_list_name: str,
        auth_mode: str = "application",
        client_secret: Optional[str] = None,
        token_storage_path: Optional[str] = None,
        allow_prompt: bool = True,
        orgplan_dir: str = ".",
        month: Optional[str] = None,
        dry_run: bool = False,
        log_file: Optional[str] = None,
    ):
        """Initialize configuration.

        Args:
            client_id: Microsoft Graph API client ID
            tenant_id: Microsoft Graph API tenant ID
            todo_list_name: Name of the Microsoft To Do list to sync
            auth_mode: Authentication mode ("application" or "delegated")
            client_secret: Microsoft Graph API client secret (required for application mode)
            token_storage_path: Path to store tokens (for delegated mode, default: .tokens/)
            allow_prompt: Allow interactive authentication prompts (False for cron)
            orgplan_dir: Root directory for orgplan files (default: current directory)
            month: Month to sync in YYYY-MM format (default: current month)
            dry_run: If True, preview changes without applying
            log_file: Optional log file path
        """
        self.client_id = client_id
        self.tenant_id = tenant_id
        self.auth_mode = auth_mode.lower()
        self.client_secret = client_secret
        self.token_storage_path = Path(token_storage_path) if token_storage_path else None
        self.allow_prompt = allow_prompt
        self.todo_list_name = todo_list_name
        self.orgplan_dir = Path(orgplan_dir).resolve()
        self.month = month or datetime.now().strftime("%Y-%m")
        self.dry_run = dry_run
        self.log_file = log_file

        # Derive orgplan file path
        year, month_num = self.month.split("-")
        self.orgplan_file = self.orgplan_dir / year / f"{month_num}-notes.md"

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors.

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        if not self.client_id:
            errors.append("Microsoft Client ID is required")
        if not self.tenant_id:
            errors.append("Microsoft Tenant ID is required")

        # Validate auth mode
        if self.auth_mode not in ["application", "delegated"]:
            errors.append(f"Invalid auth mode: {self.auth_mode} (must be 'application' or 'delegated')")

        # Client secret only required for application mode
        if self.auth_mode == "application" and not self.client_secret:
            errors.append("Microsoft Client Secret is required for application mode")

        if not self.todo_list_name:
            errors.append("To Do list name is required")

        if not self.orgplan_dir.exists():
            errors.append(f"Orgplan directory does not exist: {self.orgplan_dir}")
        elif not self.orgplan_dir.is_dir():
            errors.append(f"Orgplan directory is not a directory: {self.orgplan_dir}")

        if not self.orgplan_file.exists():
            errors.append(
                f"Orgplan file for {self.month} does not exist: {self.orgplan_file}"
            )

        # Validate month format
        try:
            datetime.strptime(self.month, "%Y-%m")
        except ValueError:
            errors.append(f"Invalid month format: {self.month} (expected YYYY-MM)")

        return errors


def load_config_from_env() -> dict:
    """Load configuration from environment variables and .env file.

    Returns:
        Dictionary of configuration values
    """
    # Load .env file if it exists
    load_dotenv()

    return {
        "client_id": os.getenv("MS_CLIENT_ID"),
        "tenant_id": os.getenv("MS_TENANT_ID"),
        "auth_mode": os.getenv("AUTH_MODE", "application"),
        "client_secret": os.getenv("MS_CLIENT_SECRET"),
        "token_storage_path": os.getenv("TOKEN_STORAGE_PATH"),
        "orgplan_dir": os.getenv("ORGPLAN_DIR", "."),
        "todo_list_name": os.getenv("TODO_LIST_NAME"),
        "month": os.getenv("SYNC_MONTH"),
        "log_file": os.getenv("LOG_FILE"),
    }


def create_config_from_args(args) -> Config:
    """Create Config object from parsed CLI arguments.

    Args:
        args: Parsed arguments from argparse

    Returns:
        Config object

    Raises:
        SystemExit: If configuration is invalid
    """
    # Load environment defaults
    env_config = load_config_from_env()

    # Determine allow_prompt (inverted from no_prompt flag)
    allow_prompt = not getattr(args, 'no_prompt', False)

    # CLI args override environment variables
    config = Config(
        client_id=args.client_id or env_config.get("client_id"),
        tenant_id=args.tenant_id or env_config.get("tenant_id"),
        auth_mode=getattr(args, 'auth_mode', None) or env_config.get("auth_mode", "application"),
        client_secret=args.client_secret or env_config.get("client_secret"),
        token_storage_path=getattr(args, 'token_storage_path', None) or env_config.get("token_storage_path"),
        allow_prompt=allow_prompt,
        todo_list_name=args.todo_list or env_config.get("todo_list_name"),
        orgplan_dir=args.orgplan_dir or env_config.get("orgplan_dir", "."),
        month=args.month or env_config.get("month"),
        dry_run=args.dry_run,
        log_file=args.log_file or env_config.get("log_file"),
    )

    # Validate configuration
    errors = config.validate()
    if errors:
        print("Configuration errors:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        sys.exit(1)

    return config
