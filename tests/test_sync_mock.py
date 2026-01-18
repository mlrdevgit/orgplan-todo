
"""Tests for Sync Engine using Mocks."""

import datetime
import unittest
from unittest.mock import Mock, MagicMock
from tools.sync_engine import SyncEngine
from tools.orgplan_parser import OrgplanTask
from tools.backends.base import TaskItem

class TestSyncEngineMock(unittest.TestCase):
    """Test SyncEngine logic without external calls."""

    def setUp(self):
        self.parser = Mock()
        self.backend = Mock()
        # Mock backend properties
        type(self.backend).id_marker_prefix = unittest.mock.PropertyMock(return_value="ms-todo-id")
        type(self.backend).supports_priority = unittest.mock.PropertyMock(return_value=True)
        type(self.backend).backend_name = unittest.mock.PropertyMock(return_value="microsoft")
        
        self.engine = SyncEngine(
            orgplan_parser=self.parser,
            backend=self.backend,
            task_list_id="list_id",
            dry_run=False
        )

    def test_sync_orgplan_to_todo_create(self):
        """Test creating a new task in backend from orgplan."""
        # Setup orgplan task
        task = OrgplanTask(
            description="New Task",
            status=None,
            priority=1,
            due_date=datetime.date(2025, 1, 15),
            line_number=1
        )
        self.parser.parse_tasks.return_value = [task]
        
        # Setup backend state (empty)
        self.backend.get_tasks.return_value = []
        
        # Setup creation return
        created_item = TaskItem(
            id="new_id",
            title="New Task",
            status="active",
            importance="high",
            due_date=datetime.date(2025, 1, 15),
        )
        self.backend.create_task.return_value = created_item
        
        # Run sync
        stats = self.engine.sync_orgplan_to_todo()
        
        # Verify
        self.assertEqual(stats["created"], 1)
        self.backend.create_task.assert_called_once()
        self.parser.add_detail_section.assert_called_once()
        
        # Check that add_detail_section was called with the new ID
        args, kwargs = self.parser.add_detail_section.call_args
        self.assertEqual(args[0], task)
        self.assertEqual(kwargs["ms_todo_id"], "new_id")

    def test_sync_orgplan_to_todo_updates_due_date(self):
        """Test updating due date in backend from orgplan."""
        task = OrgplanTask(
            description="Due Task",
            status=None,
            priority=None,
            due_date=datetime.date(2025, 2, 1),
            line_number=1,
        )
        setattr(task, "ms_todo_id", "task-123")

        self.parser.parse_tasks.return_value = [task]

        backend_task = TaskItem(
            id="task-123",
            title="Due Task",
            status="active",
            importance="normal",
            due_date=None,
        )
        self.backend.get_tasks.return_value = [backend_task]

        self.engine.sync_orgplan_to_todo()

        self.backend.update_task.assert_called_once()
        args, _ = self.backend.update_task.call_args
        updated_task = args[1]
        self.assertEqual(updated_task.due_date, datetime.date(2025, 2, 1))

    def test_sync_todo_to_orgplan_create(self):
        """Test creating a new task in orgplan from backend."""
        # Setup backend task
        todo_task = TaskItem(id="remote_id", title="Remote Task", status="active", importance="normal")
        
        # Run sync
        # Note: sync_todo_to_orgplan takes lists, so we don't mock parse_tasks/get_tasks here usually,
        # but the engine assumes we pass them in.
        stats = self.engine.sync_todo_to_orgplan([], [todo_task])
        
        # Verify
        self.assertEqual(stats["created"], 1)
        self.parser.add_task.assert_called_once()
        self.parser.add_detail_section.assert_called_once()

    def test_sync_canceled_task(self):
        """Test that [CANCELED] task treats backend as completed (regression test)."""
        # Setup orgplan task CANCELED
        task = OrgplanTask(
            description="Canceled Task",
            status="CANCELED",
            priority=None,
            line_number=1
        )
        setattr(task, "ms_todo_id", "task-123")  # Explicitly set ID
        
        self.parser.parse_tasks.return_value = [task]

        # Setup backend task COMPLETED
        backend_task = TaskItem(
            id="task-123", 
            title="Canceled Task", 
            status="completed", 
            importance="normal"
        )
        self.backend.get_tasks.return_value = [backend_task]

        # Run sync
        self.engine.sync_orgplan_to_todo()

        # Verify NO update
        self.backend.update_task.assert_not_called()

if __name__ == "__main__":
    unittest.main()
