"""Configuration management for orgplan-todo sync."""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Import orgplan config to leverage shared configuration
try:
    from orgplan.config import load_config as load_orgplan_config
except ImportError:
    load_orgplan_config = None


class Config:
    """Configuration holder for sync operations."""

    def __init__(
        self,
        backend: str = "microsoft",
        # Microsoft To Do parameters
        client_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        auth_mode: str = "application",
        client_secret: Optional[str] = None,
        # Google Tasks parameters
        google_client_id: Optional[str] = None,
        google_client_secret: Optional[str] = None,
        # Common parameters
        task_list_name: Optional[str] = None,
        token_storage_path: Optional[str] = None,
        allow_prompt: bool = True,
        orgplan_dir: str = ".",
        month: Optional[str] = None,
        dry_run: bool = False,
        log_file: Optional[str] = None,
    ):
        """Initialize configuration.

        Args:
            backend: Task backend ("microsoft" or "google")
            client_id: Microsoft Graph API client ID (for Microsoft backend)
            tenant_id: Microsoft Graph API tenant ID (for Microsoft backend)
            auth_mode: Authentication mode for Microsoft ("application" or "delegated")
            client_secret: Client secret (for Microsoft application mode)
            google_client_id: Google OAuth client ID (for Google backend)
            google_client_secret: Google OAuth client secret (for Google backend)
            task_list_name: Name of the task list to sync
            token_storage_path: Path to store tokens (default: .tokens/)
            allow_prompt: Allow interactive authentication prompts (False for cron)
            orgplan_dir: Root directory for orgplan files (default: current directory)
            month: Month to sync in YYYY-MM format (default: current month)
            dry_run: If True, preview changes without applying
            log_file: Optional log file path
        """
        self.backend = backend.lower()
        # Microsoft-specific
        self.client_id = client_id
        self.tenant_id = tenant_id
        self.auth_mode = auth_mode.lower()
        self.client_secret = client_secret
        # Google-specific
        self.google_client_id = google_client_id
        self.google_client_secret = google_client_secret
        # Common
        self.task_list_name = task_list_name
        self.token_storage_path = Path(token_storage_path) if token_storage_path else None
        self.allow_prompt = allow_prompt
        
        # Orgplan Directory logic with fallback to orgplan core config
        # Use provided arg as primary source if not default "."
        self.orgplan_dir = self._resolve_orgplan_dir(orgplan_dir)
        
        self.month = month or datetime.now().strftime("%Y-%m")
        self.dry_run = dry_run
        self.log_file = log_file

        # Backward compatibility aliases
        self.todo_list_name = task_list_name
        self.google_task_list_name = task_list_name

        # Derive orgplan file path
        year, month_num = self.month.split("-")
        self.orgplan_file = self.orgplan_dir / year / f"{month_num}-notes.md"

    def _resolve_orgplan_dir(self, arg_dir: str) -> Path:
        """Resolve the orgplan data directory."""
        # 1. CLI Argument / Constructor Argument (if not default ".")
        if arg_dir != ".":
            return Path(arg_dir).resolve()
            
        # 2. Environment variable override
        env_dir = os.getenv("ORGPLAN_DIR")
        if env_dir:
            return Path(env_dir).resolve()
            
        # 3. Try orgplan core config
        if load_orgplan_config:
            try:
                # Try loading without path (uses ORGPLAN_CONFIG env var)
                try:
                    orgplan_conf = load_orgplan_config()
                except ValueError:
                    # If ORGPLAN_CONFIG not set, try default locations or skip
                    pass
                else:
                    if orgplan_conf and orgplan_conf.data_root:
                        return Path(orgplan_conf.data_root)
            except Exception:
                pass

        # 4. Default fallback to current directory
        # (Original code defaulted to current dir, but previous change defaulted to ~/orgplan.
        # Sticking to current dir as default to matching signature default ".")
        return Path(".").resolve()

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors.

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        # Validate backend
        if self.backend not in ["microsoft", "google"]:
            errors.append(f"Invalid backend: {self.backend} (must be 'microsoft' or 'google')")
            return errors  # Return early if backend is invalid

        # Backend-specific validation
        if self.backend == "microsoft":
            if not self.client_id:
                errors.append("Microsoft Client ID is required (set MS_CLIENT_ID)")
            if not self.tenant_id:
                errors.append("Microsoft Tenant ID is required (set MS_TENANT_ID)")

            # Validate auth mode
            if self.auth_mode not in ["application", "delegated"]:
                errors.append(
                    f"Invalid auth mode: {self.auth_mode} (must be 'application' or 'delegated')"
                )

            # Client secret only required for application mode
            if self.auth_mode == "application" and not self.client_secret:
                errors.append(
                    "Microsoft Client Secret is required for application mode (set MS_CLIENT_SECRET)"
                )

        elif self.backend == "google":
            if not self.google_client_id:
                errors.append("Google Client ID is required (set GOOGLE_CLIENT_ID)")
            if not self.google_client_secret:
                errors.append("Google Client Secret is required (set GOOGLE_CLIENT_SECRET)")

        # Common validation
        # For Google Tasks, empty task_list_name is valid (uses primary list)
        # For Microsoft, task_list_name is required
        if not self.task_list_name and self.backend != "google":
            errors.append("Task list name is required for Microsoft (set TODO_LIST_NAME)")

        if not self.orgplan_dir.exists():
            errors.append(f"Orgplan directory does not exist: {self.orgplan_dir}")
        elif not self.orgplan_dir.is_dir():
            errors.append(f"Orgplan directory is not a directory: {self.orgplan_dir}")
        
        # Check orgplan file existence (only if we can't create it, but usually validation checks if input is valid)
        # OrgplanParser might create it? No, usually valid for reading.
        # But if we are creating new tasks, file might not need to exist yet?
        # The original code checked existence.
        
        # if not self.orgplan_file.exists():
        #     errors.append(f"Orgplan file for {self.month} does not exist: {self.orgplan_file}")

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

    backend = os.getenv("TASK_BACKEND", "microsoft")

    # Choose task list name based on backend
    if backend == "google":
        # For Google, prefer GOOGLE_TASK_LIST_NAME, fallback to TODO_LIST_NAME
        task_list_name = os.getenv("GOOGLE_TASK_LIST_NAME") or os.getenv("TODO_LIST_NAME")
    else:
        # For Microsoft, prefer TODO_LIST_NAME, fallback to GOOGLE_TASK_LIST_NAME
        task_list_name = os.getenv("TODO_LIST_NAME") or os.getenv("GOOGLE_TASK_LIST_NAME")

    return {
        "backend": backend,
        # Microsoft-specific
        "client_id": os.getenv("MS_CLIENT_ID"),
        "tenant_id": os.getenv("MS_TENANT_ID"),
        "auth_mode": os.getenv("AUTH_MODE", "application"),
        "client_secret": os.getenv("MS_CLIENT_SECRET"),
        # Google-specific
        "google_client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "google_client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        # Common
        "task_list_name": task_list_name,
        "token_storage_path": os.getenv("TOKEN_STORAGE_PATH"),
        "orgplan_dir": os.getenv("ORGPLAN_DIR", "."),
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
    allow_prompt = not getattr(args, "no_prompt", False)

    # Get task list name (support both --todo-list and --task-list)
    task_list = (
        getattr(args, "task_list", None)
        or getattr(args, "todo_list", None)
        or env_config.get("task_list_name")
    )

    # CLI args override environment variables
    config = Config(
        backend=getattr(args, "backend", None) or env_config.get("backend", "microsoft"),
        # Microsoft-specific
        client_id=getattr(args, "client_id", None) or env_config.get("client_id"),
        tenant_id=getattr(args, "tenant_id", None) or env_config.get("tenant_id"),
        auth_mode=getattr(args, "auth_mode", None) or env_config.get("auth_mode", "application"),
        client_secret=getattr(args, "client_secret", None) or env_config.get("client_secret"),
        # Google-specific
        google_client_id=env_config.get("google_client_id"),
        google_client_secret=env_config.get("google_client_secret"),
        # Common
        task_list_name=task_list,
        token_storage_path=getattr(args, "token_storage_path", None)
        or env_config.get("token_storage_path"),
        allow_prompt=allow_prompt,
        orgplan_dir=getattr(args, "orgplan_dir", None) or env_config.get("orgplan_dir", "."),
        month=getattr(args, "month", None) or env_config.get("month"),
        dry_run=getattr(args, "dry_run", False),
        log_file=getattr(args, "log_file", None) or env_config.get("log_file"),
    )

    # Validate configuration
    errors = config.validate()
    if errors:
        print("Configuration errors:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        sys.exit(1)

    return config
