"""Base classes and interfaces for task backend implementations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


@dataclass
class TaskItem:
    """Backend-agnostic task representation.

    This class provides a common task model that works across different
    task management backends (Microsoft To Do, Google Tasks, etc.).
    """

    id: str
    title: str
    status: str  # "active" or "completed"
    body: Optional[str] = None
    importance: Optional[str] = None  # "low", "normal", "high" (None for backends without priority)
    completed_datetime: Optional[str] = None
    due_date: Optional[date] = None
    backend_specific: dict = field(default_factory=dict)  # For backend-specific fields

    @property
    def is_completed(self) -> bool:
        """Check if task is completed."""
        return self.status == "completed"


class TaskBackend(ABC):
    """Abstract base class for task backend implementations.

    All task backends (Microsoft To Do, Google Tasks, etc.) must implement
    this interface to work with the sync engine.
    """

    @abstractmethod
    def authenticate(self) -> None:
        """Authenticate with the task service.

        Raises:
            Exception: If authentication fails
        """
        pass

    @abstractmethod
    def get_task_lists(self) -> list[dict]:
        """Get all task lists from the backend.

        Returns:
            List of task list dictionaries with at least 'id' and 'displayName' keys
        """
        pass

    @abstractmethod
    def get_list_by_name(self, name: str) -> Optional[dict]:
        """Get task list by name.

        Args:
            name: The display name of the task list

        Returns:
            Task list dictionary if found, None otherwise
        """
        pass

    @abstractmethod
    def get_tasks(self, list_id: str) -> list[TaskItem]:
        """Get all tasks from a task list.

        Args:
            list_id: The ID of the task list

        Returns:
            List of TaskItem objects
        """
        pass

    @abstractmethod
    def create_task(self, list_id: str, task: TaskItem) -> TaskItem:
        """Create a new task.

        Args:
            list_id: The ID of the task list
            task: TaskItem to create (id may be None)

        Returns:
            Created TaskItem with backend-assigned ID
        """
        pass

    @abstractmethod
    def update_task(self, list_id: str, task: TaskItem) -> TaskItem:
        """Update an existing task.

        Args:
            list_id: The ID of the task list
            task: TaskItem with updated fields

        Returns:
            Updated TaskItem
        """
        pass

    @abstractmethod
    def delete_task(self, list_id: str, task_id: str) -> None:
        """Delete a task.

        Args:
            list_id: The ID of the task list
            task_id: The ID of the task to delete
        """
        pass

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Return the backend name (e.g., 'microsoft', 'google').

        Returns:
            Backend identifier string
        """
        pass

    @property
    @abstractmethod
    def id_marker_prefix(self) -> str:
        """Return the ID marker prefix for orgplan files.

        This is used to identify which backend a task belongs to in the
        orgplan markdown files.

        Returns:
            ID marker prefix (e.g., 'ms-todo-id', 'google-tasks-id')
        """
        pass

    @property
    @abstractmethod
    def supports_priority(self) -> bool:
        """Return whether this backend supports task priority/importance.

        Backends that don't support priority (like Google Tasks) should return False.
        This prevents unnecessary sync updates when priority is the only difference.

        Returns:
            True if backend supports priority, False otherwise
        """
        pass
