"""Tests for sync direction CLI options."""

import argparse
from pathlib import Path
from unittest.mock import Mock, patch

import tools.sync as sync


def _base_args(**overrides):
    args = {
        "backend": "microsoft",
        "todo_list": "Test List",
        "auth_mode": "application",
        "client_id": "client-id",
        "tenant_id": "tenant-id",
        "client_secret": "secret",
        "token_storage_path": None,
        "no_prompt": True,
        "orgplan_dir": ".",
        "month": "2025-01",
        "dry_run": False,
        "validate_config": False,
        "sync_direction": "both",
        "log_file": None,
        "verbose": False,
    }
    args.update(overrides)
    return argparse.Namespace(**args)


def _mock_config():
    config = Mock()
    config.backend = "microsoft"
    config.auth_mode = "application"
    config.client_id = "client-id"
    config.client_secret = "secret"
    config.tenant_id = "tenant-id"
    config.token_storage_path = None
    config.allow_prompt = False
    config.orgplan_dir = Path(".")
    config.orgplan_file = Path("notes.md")
    config.todo_list_name = "Test List"
    config.task_list_name = "Test List"
    config.month = "2025-01"
    config.dry_run = False
    return config


@patch("tools.sync.SyncLock")
@patch("tools.sync.OrgplanParser")
@patch("tools.sync.create_backend")
@patch("tools.sync.create_config_from_args")
@patch("tools.sync.parse_arguments")
@patch("tools.sync.setup_logging")
def test_orgplan_to_remote_only(
    mock_setup_logging,
    mock_parse_arguments,
    mock_create_config,
    mock_create_backend,
    mock_parser_cls,
    mock_lock_cls,
):
    args = _base_args(sync_direction="orgplan-to-remote")
    mock_parse_arguments.return_value = args
    mock_create_config.return_value = _mock_config()

    backend = Mock()
    backend.get_list_by_name.return_value = {"id": "list-id", "displayName": "Test List"}
    mock_create_backend.return_value = backend

    parser = Mock()
    parser.validate.return_value = []
    mock_parser_cls.return_value = parser

    lock = Mock()
    lock.acquire.return_value = True
    mock_lock_cls.return_value = lock

    engine = Mock()
    engine.sync_orgplan_to_todo.return_value = {
        "created": 1,
        "updated": 0,
        "skipped": 0,
        "errors": 0,
    }

    with patch("tools.sync.SyncEngine", return_value=engine):
        sync.main()

    engine.sync_orgplan_to_todo.assert_called_once()
    engine.sync_todo_to_orgplan.assert_not_called()
    backend.get_tasks.assert_not_called()


@patch("tools.sync.SyncLock")
@patch("tools.sync.OrgplanParser")
@patch("tools.sync.create_backend")
@patch("tools.sync.create_config_from_args")
@patch("tools.sync.parse_arguments")
@patch("tools.sync.setup_logging")
def test_remote_to_orgplan_only(
    mock_setup_logging,
    mock_parse_arguments,
    mock_create_config,
    mock_create_backend,
    mock_parser_cls,
    mock_lock_cls,
):
    args = _base_args(sync_direction="remote-to-orgplan")
    mock_parse_arguments.return_value = args
    mock_create_config.return_value = _mock_config()

    backend = Mock()
    backend.get_list_by_name.return_value = {"id": "list-id", "displayName": "Test List"}
    backend.get_tasks.return_value = []
    mock_create_backend.return_value = backend

    parser = Mock()
    parser.validate.return_value = []
    parser.parse_tasks.return_value = []
    mock_parser_cls.return_value = parser

    lock = Mock()
    lock.acquire.return_value = True
    mock_lock_cls.return_value = lock

    engine = Mock()
    engine.sync_todo_to_orgplan.return_value = {
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "errors": 0,
    }

    with patch("tools.sync.SyncEngine", return_value=engine):
        sync.main()

    engine.sync_todo_to_orgplan.assert_called_once()
    engine.sync_orgplan_to_todo.assert_not_called()
    parser.save.assert_called_once()
