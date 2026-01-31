
import unittest
from unittest.mock import Mock, MagicMock
from tools.sync_engine import SyncEngine
from tools.orgplan_parser import OrgplanTask
from tools.backends.base import TaskItem

class TestSyncCancellationConflict(unittest.TestCase):
    """Test conflict resolution between Local CANCELED and Remote DONE."""

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

    def test_remote_complete_overwrites_local_canceled(self):
        """Test that currently [CANCELED] task is overwritten by remote completed."""
        # Setup orgplan task CANCELED
        local_task = OrgplanTask(
            description="Canceled Task",
            status="CANCELED",
            priority=2,
            line_number=1
        )
        setattr(local_task, "ms_todo_id", "task-123")  # Explicitly set ID
        
        # Setup backend task COMPLETED (DONE)
        remote_task = TaskItem(
            id="task-123", 
            title="Canceled Task", 
            status="completed", 
            importance="normal"
        )
        
        # We need to simulate the finding logic or just call _update_orgplan_task directly
        # calling _update_orgplan_task directly is easier for unit testing the logic
        
        # Act
        modified = self.engine._update_orgplan_task(local_task, remote_task)
        
        # Assert
        # We EXPECT it to NOT be modified, preserving CANCELED state
        self.assertFalse(modified, "Local CANCELED task should NOT be overwritten by remote DONE")
        self.parser.update_task_status.assert_not_called()
        


if __name__ == "__main__":
    unittest.main()
