"""Microsoft To Do client using Graph API.

This module maintains backward compatibility by re-exporting
the Microsoft To Do backend implementation.

For new code, prefer importing from backends.microsoft_todo directly.
"""

from backends.microsoft_todo import MicrosoftTodoBackend
from backends.base import TaskItem

# Maintain backward compatibility with old TodoClient name
TodoClient = MicrosoftTodoBackend

# Maintain backward compatibility with old TodoTask name
TodoTask = TaskItem

__all__ = ["TodoClient", "TodoTask", "MicrosoftTodoBackend", "TaskItem"]
