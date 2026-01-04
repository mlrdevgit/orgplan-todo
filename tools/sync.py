#!/usr/bin/env python3
"""Main script for syncing orgplan with Microsoft To Do."""

import argparse
import logging
import sys
from datetime import datetime

from config import create_config_from_args
from orgplan_parser import OrgplanParser
from sync_engine import SyncEngine
from todo_client import TodoClient
from locking import SyncLock


def setup_logging(log_file: str = None, verbose: bool = False):
    """Setup logging configuration.

    Args:
        log_file: Optional file path for logging
        verbose: If True, enable debug logging
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    log_format = "[%(asctime)s] %(levelname)s: %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))

    handlers = [console_handler]

    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))
        handlers.append(file_handler)

    # Configure root logger
    logging.basicConfig(level=log_level, handlers=handlers)


def parse_arguments():
    """Parse command line arguments.

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Sync orgplan tasks with Microsoft To Do",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Sync with default configuration from .env (application mode)
  python sync.py --todo-list "Orgplan 2025"

  # Sync using delegated authentication (user login)
  python sync.py --todo-list "Orgplan 2025" --auth-mode delegated

  # Dry run to preview changes
  python sync.py --todo-list "Orgplan 2025" --dry-run

  # Sync specific month with logging
  python sync.py --todo-list "Work Tasks 2025" --month 2025-11 --log-file sync.log

  # Cron job (delegated auth, no interactive prompts)
  python sync.py --todo-list "Orgplan 2025" --auth-mode delegated --no-prompt --log-file sync.log

  # Override configuration
  python sync.py \\
    --client-id YOUR_CLIENT_ID \\
    --tenant-id YOUR_TENANT_ID \\
    --client-secret YOUR_SECRET \\
    --todo-list "Orgplan 2025" \\
    --orgplan-dir ~/notes
        """,
    )

    # Required arguments
    parser.add_argument(
        "--todo-list",
        type=str,
        help="Name of the Microsoft To Do list to sync with (required)",
    )

    # Authentication
    auth_group = parser.add_argument_group("authentication")
    auth_group.add_argument(
        "--auth-mode",
        type=str,
        choices=["application", "delegated"],
        help="Authentication mode: 'application' (client credentials) or 'delegated' (user login). Default: application",
    )
    auth_group.add_argument(
        "--client-id",
        type=str,
        help="Microsoft Graph API client ID (or set MS_CLIENT_ID env var)",
    )
    auth_group.add_argument(
        "--tenant-id",
        type=str,
        help="Microsoft Graph API tenant ID (or set MS_TENANT_ID env var)",
    )
    auth_group.add_argument(
        "--client-secret",
        type=str,
        help="Microsoft Graph API client secret (required for application mode, or set MS_CLIENT_SECRET env var)",
    )
    auth_group.add_argument(
        "--token-storage-path",
        type=str,
        help="Path to store authentication tokens (for delegated mode, default: .tokens/)",
    )
    auth_group.add_argument(
        "--no-prompt",
        action="store_true",
        help="Disable interactive authentication prompts (for cron jobs). Exit with error if re-authentication needed.",
    )

    # Orgplan configuration
    orgplan_group = parser.add_argument_group("orgplan")
    orgplan_group.add_argument(
        "--orgplan-dir",
        type=str,
        help="Root directory for orgplan files (default: current directory)",
    )
    orgplan_group.add_argument(
        "--month",
        type=str,
        help="Month to sync in YYYY-MM format (default: current month)",
    )

    # Sync options
    sync_group = parser.add_argument_group("sync options")
    sync_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying them",
    )
    sync_group.add_argument(
        "--validate-config",
        action="store_true",
        help="Validate configuration and exit (no sync)",
    )

    # Logging
    log_group = parser.add_argument_group("logging")
    log_group.add_argument(
        "--log-file",
        type=str,
        help="Path to log file (console always logs)",
    )
    log_group.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose (debug) logging",
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    # Parse arguments
    args = parse_arguments()

    # Setup logging
    setup_logging(log_file=args.log_file, verbose=args.verbose)
    logger = logging.getLogger(__name__)

    # Create configuration
    logger.info("Loading configuration...")
    config = create_config_from_args(args)

    # If validating config only, exit after validation
    if args.validate_config:
        logger.info("=" * 60)
        logger.info("Configuration Validation")
        logger.info("=" * 60)
        logger.info(f"✓ Authentication mode: {config.auth_mode}")
        logger.info(f"✓ Client ID: {config.client_id[:10]}...")
        logger.info(f"✓ Tenant ID: {config.tenant_id[:10]}...")
        if config.auth_mode == "application":
            logger.info(f"✓ Client Secret: ***{config.client_secret[-4:]}")
        else:
            logger.info(f"✓ Token storage: {config.token_storage_path or '.tokens/'}")
            logger.info(f"✓ Allow prompt: {config.allow_prompt}")
        logger.info(f"✓ Orgplan directory: {config.orgplan_dir}")
        logger.info(f"✓ Orgplan file: {config.orgplan_file}")
        logger.info(f"✓ To Do list name: {config.todo_list_name}")
        logger.info(f"✓ Month: {config.month}")

        # Validate orgplan file
        from orgplan_parser import OrgplanParser
        parser = OrgplanParser(config.orgplan_file)
        parser.load()
        warnings = parser.validate()

        if warnings:
            logger.warning("Orgplan file format warnings:")
            for warning in warnings:
                logger.warning(f"  - {warning}")
        else:
            logger.info("✓ Orgplan file format is valid")

        logger.info("=" * 60)
        logger.info("Configuration is valid!")
        logger.info("=" * 60)
        return

    if config.dry_run:
        logger.info("DRY RUN MODE: No changes will be applied")

    logger.info(f"Syncing orgplan month: {config.month}")
    logger.info(f"Orgplan file: {config.orgplan_file}")
    logger.info(f"To Do list: {config.todo_list_name}")

    # Acquire lock to prevent concurrent runs
    lock_file = config.orgplan_dir / "sync.lock"
    lock = SyncLock(lock_file, logger)

    if not lock.acquire(timeout=0, stale_threshold=3600):
        logger.error("Failed to acquire lock. Another sync may be running.")
        logger.error(f"If no other sync is running, remove: {lock_file}")
        sys.exit(1)

    try:
        # Initialize components
        logger.info(f"Authenticating with Microsoft Graph API ({config.auth_mode} mode)...")
        todo_client = TodoClient(
            client_id=config.client_id,
            tenant_id=config.tenant_id,
            auth_mode=config.auth_mode,
            client_secret=config.client_secret,
            token_storage_path=config.token_storage_path,
            allow_prompt=config.allow_prompt,
            logger=logger,
        )
        todo_client.authenticate()
        logger.info("Authentication successful")

        # Get To Do list
        logger.info(f"Finding To Do list '{config.todo_list_name}'...")
        todo_list = todo_client.get_list_by_name(config.todo_list_name)
        if not todo_list:
            logger.error(f"To Do list '{config.todo_list_name}' not found")
            logger.error("Available lists:")
            for lst in todo_client.get_task_lists():
                logger.error(f"  - {lst.get('displayName')}")
            sys.exit(1)

        logger.info(f"Found list: {todo_list['displayName']} (ID: {todo_list['id']})")

        # Initialize orgplan parser
        logger.info("Initializing orgplan parser...")
        orgplan_parser = OrgplanParser(config.orgplan_file)
        orgplan_parser.load()

        # Validate orgplan file format
        logger.info("Validating orgplan file format...")
        warnings = orgplan_parser.validate()
        if warnings:
            logger.warning("Orgplan file format warnings:")
            for warning in warnings:
                logger.warning(f"  - {warning}")
        else:
            logger.info("Orgplan file format is valid")

        # Initialize sync engine
        logger.info("Initializing sync engine...")
        sync_engine = SyncEngine(
            orgplan_parser=orgplan_parser,
            todo_client=todo_client,
            todo_list_id=todo_list["id"],
            dry_run=config.dry_run,
        )

        # Perform bidirectional sync
        logger.info("=" * 60)
        logger.info("Starting bidirectional sync")
        logger.info("=" * 60)

        stats = sync_engine.sync_bidirectional()

        # Print summary
        logger.info("")
        logger.info("=" * 60)
        logger.info("Sync completed!")
        logger.info("=" * 60)
        logger.info("")
        logger.info("Orgplan -> To Do:")
        logger.info(f"  Created:  {stats['orgplan_to_todo']['created']}")
        logger.info(f"  Updated:  {stats['orgplan_to_todo']['updated']}")
        logger.info(f"  Skipped:  {stats['orgplan_to_todo']['skipped']}")
        logger.info(f"  Errors:   {stats['orgplan_to_todo']['errors']}")
        logger.info("")
        logger.info("To Do -> Orgplan:")
        logger.info(f"  Created:  {stats['todo_to_orgplan']['created']}")
        logger.info(f"  Updated:  {stats['todo_to_orgplan']['updated']}")
        logger.info(f"  Skipped:  {stats['todo_to_orgplan']['skipped']}")
        logger.info(f"  Errors:   {stats['todo_to_orgplan']['errors']}")
        logger.info("")
        logger.info("Total:")
        logger.info(f"  Created:  {stats['total_created']}")
        logger.info(f"  Updated:  {stats['total_updated']}")
        logger.info(f"  Errors:   {stats['total_errors']}")

        if config.dry_run:
            logger.info("")
            logger.info("DRY RUN MODE: No changes were applied")
            logger.info("Run without --dry-run to apply changes")

        # Exit with error code if there were errors
        if stats["total_errors"] > 0:
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\nSync interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Sync failed: {e}", exc_info=args.verbose)
        sys.exit(1)
    finally:
        # Always release the lock
        lock.release()


if __name__ == "__main__":
    main()
