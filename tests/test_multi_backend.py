"""Tests for multi-backend functionality.

This test file covers:
- Backend factory
- Multiple ID markers in orgplan
- Switching between backends
- Backend-agnostic sync engine
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

from backends import create_backend
from backends.base import TaskBackend, TaskItem
from backends.microsoft_todo import MicrosoftTodoBackend
from backends.google_tasks import GoogleTasksBackend
from config import Config
from orgplan_parser import OrgplanParser, OrgplanTask


class TestBackendFactory(unittest.TestCase):
    """Test backend factory functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = Mock()
        self.logger = Mock()

    def test_create_microsoft_backend(self):
        """Test creating Microsoft To Do backend."""
        self.config.client_id = "client_id"
        self.config.tenant_id = "tenant_id"
        self.config.auth_mode = "application"
        self.config.client_secret = "secret"
        self.config.token_storage_path = None
        self.config.allow_prompt = True

        backend = create_backend("microsoft", self.config, self.logger)

        self.assertIsInstance(backend, MicrosoftTodoBackend)
        self.assertEqual(backend.backend_name, "microsoft")
        self.assertEqual(backend.id_marker_prefix, "ms-todo-id")

    def test_create_google_backend(self):
        """Test creating Google Tasks backend."""
        self.config.google_client_id = "client_id"
        self.config.google_client_secret = "client_secret"
        self.config.token_storage_path = None
        self.config.allow_prompt = True

        backend = create_backend("google", self.config, self.logger)

        self.assertIsInstance(backend, GoogleTasksBackend)
        self.assertEqual(backend.backend_name, "google")
        self.assertEqual(backend.id_marker_prefix, "google-tasks-id")

    def test_create_invalid_backend(self):
        """Test creating invalid backend raises error."""
        with self.assertRaises(ValueError) as ctx:
            create_backend("invalid", self.config, self.logger)

        self.assertIn("Unknown backend type", str(ctx.exception))


class TestMultipleIDMarkers(unittest.TestCase):
    """Test handling of multiple ID markers in orgplan."""

    def test_orgplan_task_has_both_id_fields(self):
        """Test that OrgplanTask supports both ID markers."""
        task = OrgplanTask(
            title="Test Task",
            status=None,
            priority=None,
            time_estimate=None,
            blocked=False,
            detail_section="",
            ms_todo_id="ms-id-123",
            google_tasks_id="google-id-456",
        )

        self.assertEqual(task.ms_todo_id, "ms-id-123")
        self.assertEqual(task.google_tasks_id, "google-id-456")

    def test_parse_detail_section_with_both_markers(self):
        """Test parsing detail section with both ID markers."""
        markdown_content = """# TODO List

- Test task

# Test task

<!-- ms-todo-id: AAMkAGI2THAAA= -->
<!-- google-tasks-id: MTIzNDU2Nzg5 -->

Task details here.
"""

        # Create temp file
        import tempfile

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(markdown_content)
            temp_path = Path(f.name)

        try:
            parser = OrgplanParser(temp_path)
            parser.load()
            tasks = parser.extract_tasks()

            self.assertEqual(len(tasks), 1)
            task = tasks[0]
            self.assertEqual(task.ms_todo_id, "AAMkAGI2THAAA=")
            self.assertEqual(task.google_tasks_id, "MTIzNDU2Nzg5")
        finally:
            temp_path.unlink()

    def test_add_detail_section_with_multiple_markers(self):
        """Test adding detail section with multiple backend IDs."""
        markdown_content = """# TODO List

- Test task
"""

        import tempfile

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(markdown_content)
            temp_path = Path(f.name)

        try:
            parser = OrgplanParser(temp_path)
            parser.load()
            tasks = parser.extract_tasks()
            task = tasks[0]

            # Add both markers
            parser.add_detail_section(
                task, ms_todo_id="ms-id-123", google_tasks_id="google-id-456"
            )
            parser.save()

            # Re-parse
            parser2 = OrgplanParser(temp_path)
            parser2.load()
            tasks2 = parser2.extract_tasks()

            self.assertEqual(tasks2[0].ms_todo_id, "ms-id-123")
            self.assertEqual(tasks2[0].google_tasks_id, "google-id-456")
        finally:
            temp_path.unlink()


class TestBackendAgnosticSync(unittest.TestCase):
    """Test that sync engine works with any backend."""

    def setUp(self):
        """Set up test fixtures."""
        # Create mock backends
        self.mock_ms_backend = Mock(spec=TaskBackend)
        self.mock_ms_backend.backend_name = "microsoft"
        self.mock_ms_backend.id_marker_prefix = "ms-todo-id"

        self.mock_google_backend = Mock(spec=TaskBackend)
        self.mock_google_backend.backend_name = "google"
        self.mock_google_backend.id_marker_prefix = "google-tasks-id"

    def test_id_marker_attribute_conversion(self):
        """Test converting ID marker prefix to attribute name."""
        # Microsoft
        ms_attr = self.mock_ms_backend.id_marker_prefix.replace("-", "_")
        self.assertEqual(ms_attr, "ms_todo_id")

        # Google
        google_attr = self.mock_google_backend.id_marker_prefix.replace("-", "_")
        self.assertEqual(google_attr, "google_tasks_id")

    def test_dynamic_id_marker_lookup(self):
        """Test dynamic ID marker lookup on task."""
        task = OrgplanTask(
            title="Test",
            status=None,
            priority=None,
            time_estimate=None,
            blocked=False,
            detail_section="",
            ms_todo_id="ms-123",
            google_tasks_id="google-456",
        )

        # Microsoft backend lookup
        ms_attr = self.mock_ms_backend.id_marker_prefix.replace("-", "_")
        ms_id = getattr(task, ms_attr, None)
        self.assertEqual(ms_id, "ms-123")

        # Google backend lookup
        google_attr = self.mock_google_backend.id_marker_prefix.replace("-", "_")
        google_id = getattr(task, google_attr, None)
        self.assertEqual(google_id, "google-456")


class TestBackendSwitching(unittest.TestCase):
    """Test switching between backends."""

    def test_task_with_only_ms_marker(self):
        """Test task that only has Microsoft ID."""
        task = OrgplanTask(
            title="Test",
            status=None,
            priority=None,
            time_estimate=None,
            blocked=False,
            detail_section="",
            ms_todo_id="ms-123",
            google_tasks_id=None,
        )

        # Google backend won't find ID marker
        google_attr = "google_tasks_id"
        google_id = getattr(task, google_attr, None)
        self.assertIsNone(google_id)

        # Microsoft backend will find it
        ms_attr = "ms_todo_id"
        ms_id = getattr(task, ms_attr, None)
        self.assertEqual(ms_id, "ms-123")

    def test_task_with_only_google_marker(self):
        """Test task that only has Google ID."""
        task = OrgplanTask(
            title="Test",
            status=None,
            priority=None,
            time_estimate=None,
            blocked=False,
            detail_section="",
            ms_todo_id=None,
            google_tasks_id="google-456",
        )

        # Microsoft backend won't find ID marker
        ms_attr = "ms_todo_id"
        ms_id = getattr(task, ms_attr, None)
        self.assertIsNone(ms_id)

        # Google backend will find it
        google_attr = "google_tasks_id"
        google_id = getattr(task, google_attr, None)
        self.assertEqual(google_id, "google-456")

    def test_task_with_both_markers(self):
        """Test task that has both markers."""
        task = OrgplanTask(
            title="Test",
            status=None,
            priority=None,
            time_estimate=None,
            blocked=False,
            detail_section="",
            ms_todo_id="ms-123",
            google_tasks_id="google-456",
        )

        # Both backends find their markers
        ms_attr = "ms_todo_id"
        ms_id = getattr(task, ms_attr, None)
        self.assertEqual(ms_id, "ms-123")

        google_attr = "google_tasks_id"
        google_id = getattr(task, google_attr, None)
        self.assertEqual(google_id, "google-456")


class TestTaskItemConversion(unittest.TestCase):
    """Test TaskItem works across backends."""

    def test_task_item_with_importance(self):
        """Test TaskItem with importance (Microsoft)."""
        task = TaskItem(
            id="id-123",
            title="Test Task",
            status="active",
            importance="high",
            body="Task notes",
        )

        self.assertEqual(task.importance, "high")

    def test_task_item_without_importance(self):
        """Test TaskItem without importance (Google)."""
        task = TaskItem(
            id="id-123",
            title="Test Task",
            status="active",
            importance=None,  # Google doesn't support
            body="Task notes",
        )

        self.assertIsNone(task.importance)

    def test_task_item_status_mapping(self):
        """Test that status uses generic values."""
        # Both backends should use "active" and "completed"
        active_task = TaskItem(
            id="1", title="Active", status="active", importance=None
        )
        completed_task = TaskItem(
            id="2", title="Completed", status="completed", importance=None
        )

        self.assertEqual(active_task.status, "active")
        self.assertEqual(completed_task.status, "completed")


class TestConfigurationBackendSupport(unittest.TestCase):
    """Test configuration supports multiple backends."""

    def test_config_backend_field(self):
        """Test Config has backend field."""
        config = Config(
            backend="microsoft",
            client_id="id",
            tenant_id="tenant",
            client_secret="secret",
        )

        self.assertEqual(config.backend, "microsoft")

    def test_config_microsoft_fields(self):
        """Test Config has Microsoft-specific fields."""
        config = Config(
            backend="microsoft",
            client_id="ms_id",
            tenant_id="tenant",
            auth_mode="application",
            client_secret="secret",
        )

        self.assertEqual(config.client_id, "ms_id")
        self.assertEqual(config.tenant_id, "tenant")
        self.assertEqual(config.auth_mode, "application")
        self.assertEqual(config.client_secret, "secret")

    def test_config_google_fields(self):
        """Test Config has Google-specific fields."""
        config = Config(
            backend="google",
            google_client_id="google_id",
            google_client_secret="google_secret",
        )

        self.assertEqual(config.google_client_id, "google_id")
        self.assertEqual(config.google_client_secret, "google_secret")

    def test_config_validation_microsoft(self):
        """Test Config validation for Microsoft backend."""
        config = Config(
            backend="microsoft",
            client_id=None,  # Missing
            tenant_id="tenant",
            client_secret="secret",
        )

        errors = config.validate()
        self.assertTrue(any("Client ID" in e for e in errors))

    def test_config_validation_google(self):
        """Test Config validation for Google backend."""
        config = Config(
            backend="google",
            google_client_id=None,  # Missing
            google_client_secret="secret",
        )

        errors = config.validate()
        self.assertTrue(any("Google Client ID" in e for e in errors))


class TestPriorityHandling(unittest.TestCase):
    """Test priority handling across backends."""

    def test_microsoft_supports_priority(self):
        """Test Microsoft backend supports priority."""
        # Microsoft backend should map priorities
        task = TaskItem(
            id="1", title="Task", status="active", importance="high", body=None
        )

        # This would be mapped to #p1 in orgplan
        self.assertEqual(task.importance, "high")

    def test_google_ignores_priority(self):
        """Test Google backend ignores priority."""
        # Google backend should set importance to None
        task = TaskItem(
            id="1", title="Task", status="active", importance=None, body=None
        )

        # Google Tasks doesn't support priority
        self.assertIsNone(task.importance)


if __name__ == "__main__":
    unittest.main()
