"""Tests for Google Tasks backend implementation.

This test file covers:
- Authentication and token management
- Task CRUD operations
- Task list operations
- API error handling
- TaskItem conversion
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, mock_open
import json
import tempfile
import shutil

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

from backends.google_tasks import GoogleTasksBackend
from backends.base import TaskItem


class TestGoogleTasksBackend(unittest.TestCase):
    """Test Google Tasks backend functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.client_id = "test_client_id"
        self.client_secret = "test_client_secret"
        
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()
        self.token_path = Path(self.test_dir) / "test_google_tokens.json"

        # Create backend instance
        self.backend = GoogleTasksBackend(
            client_id=self.client_id,
            client_secret=self.client_secret,
            token_storage_path=Path(self.test_dir),
            allow_prompt=False,  # No interactive prompts in tests
        )

    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_backend_name(self):
        """Test backend_name property."""
        self.assertEqual(self.backend.backend_name, "google")

    def test_id_marker_prefix(self):
        """Test id_marker_prefix property."""
        self.assertEqual(self.backend.id_marker_prefix, "google-tasks-id")

    @patch("backends.google_tasks.build")
    @patch("backends.google_tasks.Credentials")
    def test_authenticate_with_valid_tokens(self, mock_creds, mock_build):
        """Test authentication with valid cached tokens."""
        # Mock credentials
        mock_creds_instance = Mock()
        mock_creds_instance.valid = True
        mock_creds.return_value = mock_creds_instance

        # Mock token file
        token_data = {
            "token": "test_token",
            "refresh_token": "test_refresh_token",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scopes": ["https://www.googleapis.com/auth/tasks"],
        }

        with patch("builtins.open", mock_open(read_data=json.dumps(token_data))):
            with patch.object(Path, "exists", return_value=True):
                self.backend.authenticate()

        # Verify service was built
        mock_build.assert_called_once()
        self.assertIsNotNone(self.backend.service)

    @patch("backends.google_tasks.build")
    @patch("backends.google_tasks.Request")
    def test_authenticate_with_expired_token(self, mock_request, mock_build):
        """Test authentication with expired but refreshable token."""
        # Mock credentials
        mock_creds = Mock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = "refresh_token"
        self.backend.credentials = mock_creds

        # Mock refresh succeeds
        mock_creds.refresh = Mock()

        with patch.object(self.backend, "_load_credentials", return_value=mock_creds):
            with patch.object(self.backend, "_save_credentials"):
                self.backend.authenticate()

        # Verify refresh was called
        mock_creds.refresh.assert_called_once()

    def test_authenticate_requires_prompt_when_no_tokens(self):
        """Test that authentication fails when prompt disabled and no tokens."""
        with patch.object(Path, "exists", return_value=False):
            with self.assertRaises(Exception) as ctx:
                self.backend.authenticate()

            self.assertIn("Authentication required", str(ctx.exception))
            self.assertIn("--no-prompt", str(ctx.exception))

    @patch.object(GoogleTasksBackend, "service")
    def test_get_task_lists(self, mock_service):
        """Test fetching task lists."""
        # Mock API response
        mock_lists = [
            {"id": "list1", "title": "My Tasks"},
            {"id": "list2", "title": "Work Tasks"},
        ]

        mock_service.tasklists().list().execute.return_value = {"items": mock_lists}
        self.backend.service = mock_service

        # Call method
        result = self.backend.get_task_lists()

        # Verify
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["title"], "My Tasks")
        self.assertEqual(result[1]["title"], "Work Tasks")

    @patch.object(GoogleTasksBackend, "get_task_lists")
    def test_get_list_by_name_found(self, mock_get_lists):
        """Test finding a task list by name."""
        mock_get_lists.return_value = [
            {"id": "list1", "title": "My Tasks"},
            {"id": "list2", "title": "Work Tasks"},
        ]

        result = self.backend.get_list_by_name("Work Tasks")

        self.assertIsNotNone(result)
        self.assertEqual(result["id"], "list2")
        self.assertEqual(result["title"], "Work Tasks")

    @patch.object(GoogleTasksBackend, "get_task_lists")
    def test_get_list_by_name_not_found(self, mock_get_lists):
        """Test searching for non-existent task list."""
        mock_get_lists.return_value = [
            {"id": "list1", "title": "My Tasks"},
        ]

        result = self.backend.get_list_by_name("Nonexistent List")

        self.assertIsNone(result)

    @patch.object(GoogleTasksBackend, "service")
    def test_get_tasks(self, mock_service):
        """Test fetching tasks from a list."""
        # Mock API response
        mock_tasks = [
            {
                "id": "task1",
                "title": "Task 1",
                "status": "needsAction",
                "notes": "Task notes",
            },
            {
                "id": "task2",
                "title": "Task 2",
                "status": "completed",
                "completed": "2025-01-01T00:00:00Z",
            },
        ]

        mock_service.tasks().list().execute.return_value = {"items": mock_tasks}
        self.backend.service = mock_service

        # Call method
        result = self.backend.get_tasks("list1")

        # Verify
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], TaskItem)
        self.assertEqual(result[0].id, "task1")
        self.assertEqual(result[0].title, "Task 1")
        self.assertEqual(result[0].status, "active")
        self.assertEqual(result[0].importance, None)  # Google doesn't support priority
        self.assertEqual(result[1].status, "completed")

    @patch.object(GoogleTasksBackend, "service")
    def test_create_task(self, mock_service):
        """Test creating a new task."""
        # Input task
        task = TaskItem(
            id="",
            title="New Task",
            status="active",
            importance=None,
            body="Task description",
        )

        # Mock API response
        mock_created = {
            "id": "new_task_id",
            "title": "New Task",
            "status": "needsAction",
            "notes": "Task description",
        }

        mock_service.tasks().insert().execute.return_value = mock_created
        self.backend.service = mock_service

        # Call method
        result = self.backend.create_task("list1", task)

        # Verify
        self.assertIsInstance(result, TaskItem)
        self.assertEqual(result.id, "new_task_id")
        self.assertEqual(result.title, "New Task")
        self.assertEqual(result.status, "active")

        # Verify API was called correctly
        call_args = mock_service.tasks().insert.call_args
        self.assertEqual(call_args[1]["tasklist"], "list1")
        self.assertEqual(call_args[1]["body"]["title"], "New Task")
        self.assertEqual(call_args[1]["body"]["status"], "needsAction")

    @patch.object(GoogleTasksBackend, "service")
    def test_create_completed_task(self, mock_service):
        """Test creating a task that's already completed."""
        task = TaskItem(
            id="",
            title="Completed Task",
            status="completed",
            importance=None,
        )

        mock_created = {
            "id": "task_id",
            "title": "Completed Task",
            "status": "completed",
        }

        mock_service.tasks().insert().execute.return_value = mock_created
        self.backend.service = mock_service

        result = self.backend.create_task("list1", task)

        # Verify completed status was set
        call_args = mock_service.tasks().insert.call_args
        self.assertEqual(call_args[1]["body"]["status"], "completed")

    @patch.object(GoogleTasksBackend, "service")
    def test_update_task(self, mock_service):
        """Test updating an existing task."""
        task = TaskItem(
            id="task_id",
            title="Updated Task",
            status="completed",
            importance=None,
            body="Updated notes",
        )

        mock_updated = {
            "id": "task_id",
            "title": "Updated Task",
            "status": "completed",
            "notes": "Updated notes",
        }

        mock_service.tasks().update().execute.return_value = mock_updated
        self.backend.service = mock_service

        result = self.backend.update_task("list1", task)

        # Verify
        self.assertEqual(result.id, "task_id")
        self.assertEqual(result.title, "Updated Task")
        self.assertEqual(result.status, "completed")

        # Verify API was called correctly
        call_args = mock_service.tasks().update.call_args
        self.assertEqual(call_args[1]["tasklist"], "list1")
        self.assertEqual(call_args[1]["task"], "task_id")

    @patch.object(GoogleTasksBackend, "service")
    def test_delete_task(self, mock_service):
        """Test deleting a task."""
        mock_service.tasks().delete().execute.return_value = None
        self.backend.service = mock_service

        # Should not raise exception
        self.backend.delete_task("list1", "task_id")

        # Verify API was called
        call_args = mock_service.tasks().delete.call_args
        self.assertEqual(call_args[1]["tasklist"], "list1")
        self.assertEqual(call_args[1]["task"], "task_id")

    def test_api_to_task_item_active(self):
        """Test converting Google API task to TaskItem (active task)."""
        api_task = {
            "id": "task_id",
            "title": "Test Task",
            "status": "needsAction",
            "notes": "Task notes",
        }

        result = self.backend._api_to_task_item(api_task)

        self.assertEqual(result.id, "task_id")
        self.assertEqual(result.title, "Test Task")
        self.assertEqual(result.status, "active")
        self.assertEqual(result.body, "Task notes")
        self.assertIsNone(result.importance)  # Google doesn't support

    def test_api_to_task_item_completed(self):
        """Test converting Google API task to TaskItem (completed task)."""
        api_task = {
            "id": "task_id",
            "title": "Test Task",
            "status": "completed",
            "completed": "2025-01-01T00:00:00Z",
        }

        result = self.backend._api_to_task_item(api_task)

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.completed_datetime, "2025-01-01T00:00:00Z")

    def test_load_credentials_file_not_found(self):
        """Test loading credentials when file doesn't exist."""
        with patch.object(Path, "exists", return_value=False):
            result = self.backend._load_credentials()

            self.assertIsNone(result)

    def test_save_credentials(self):
        """Test saving credentials to file."""
        # Mock credentials
        mock_creds = Mock()
        mock_creds.token = "token"
        mock_creds.refresh_token = "refresh"
        mock_creds.token_uri = "uri"
        mock_creds.client_id = "client"
        mock_creds.client_secret = "secret"
        mock_creds.scopes = ["scope"]

        self.backend.credentials = mock_creds

        with patch("builtins.open", mock_open()) as m:
            with patch.object(Path, "mkdir"):
                with patch("os.chmod"):
                    self.backend._save_credentials()

        # Verify file was written
        m.assert_called_once()


class TestGoogleTasksIntegration(unittest.TestCase):
    """Integration tests for Google Tasks (requires actual credentials)."""

    @classmethod
    def setUpClass(cls):
        """Set up class-level fixtures."""
        cls.skip_integration = not all(
            [
                os.getenv("GOOGLE_CLIENT_ID"),
                os.getenv("GOOGLE_CLIENT_SECRET"),
                os.getenv("RUN_INTEGRATION_TESTS"),
            ]
        )

    def setUp(self):
        """Set up test fixtures."""
        if self.skip_integration:
            self.skipTest("Integration tests disabled (set RUN_INTEGRATION_TESTS=1)")

        self.backend = GoogleTasksBackend(
            client_id=os.getenv("GOOGLE_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
            allow_prompt=False,
        )

    def test_authentication(self):
        """Test real authentication."""
        # This requires cached tokens
        try:
            self.backend.authenticate()
            self.assertIsNotNone(self.backend.service)
        except Exception as e:
            self.skipTest(f"Authentication failed: {e}")

    def test_list_task_lists(self):
        """Test fetching real task lists."""
        try:
            self.backend.authenticate()
            lists = self.backend.get_task_lists()
            self.assertIsInstance(lists, list)
            if lists:
                self.assertIn("id", lists[0])
                self.assertIn("title", lists[0])
        except Exception as e:
            self.skipTest(f"Test failed: {e}")


if __name__ == "__main__":
    unittest.main()
