"""Sync engine for orgplan and Microsoft To Do."""

import logging
from typing import Optional

from orgplan_parser import OrgplanParser, OrgplanTask
from todo_client import TodoClient, TodoTask


class SyncEngine:
    """Coordinates synchronization between orgplan and To Do."""

    def __init__(
        self,
        orgplan_parser: OrgplanParser,
        todo_client: TodoClient,
        todo_list_id: str,
        dry_run: bool = False,
    ):
        """Initialize sync engine.

        Args:
            orgplan_parser: Parser for orgplan file
            todo_client: Client for Microsoft To Do
            todo_list_id: ID of the To Do list to sync with
            dry_run: If True, preview changes without applying
        """
        self.orgplan_parser = orgplan_parser
        self.todo_client = todo_client
        self.todo_list_id = todo_list_id
        self.dry_run = dry_run
        self.logger = logging.getLogger(__name__)

    def sync_orgplan_to_todo(self) -> dict:
        """Sync tasks from orgplan to Microsoft To Do (Phase 1 MVP).

        Returns:
            Dictionary with sync statistics
        """
        stats = {
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0,
        }

        # Load orgplan tasks
        self.logger.info("Loading orgplan tasks...")
        orgplan_tasks = self.orgplan_parser.parse_tasks()
        self.logger.info(f"Found {len(orgplan_tasks)} tasks in orgplan")

        # Load To Do tasks
        self.logger.info("Loading To Do tasks...")
        todo_tasks = self.todo_client.get_tasks(self.todo_list_id)
        self.logger.info(f"Found {len(todo_tasks)} tasks in To Do")

        # Build lookup maps
        todo_by_id = {task.id: task for task in todo_tasks}
        todo_by_title = {task.title: task for task in todo_tasks}

        # Process each orgplan task
        for orgplan_task in orgplan_tasks:
            try:
                # Skip tasks that are already done
                if orgplan_task.status == "DONE":
                    self.logger.debug(f"Skipping completed task: {orgplan_task.description}")
                    stats["skipped"] += 1
                    continue

                # Find matching To Do task
                todo_task = self._find_matching_todo_task(
                    orgplan_task, todo_by_id, todo_by_title
                )

                if todo_task:
                    # Update existing task
                    if self._update_todo_task(orgplan_task, todo_task):
                        stats["updated"] += 1
                    else:
                        stats["skipped"] += 1
                else:
                    # Create new task
                    if self._create_todo_task(orgplan_task):
                        stats["created"] += 1

            except Exception as e:
                self.logger.error(f"Error processing task '{orgplan_task.description}': {e}")
                stats["errors"] += 1

        # Save orgplan changes if not dry run
        if not self.dry_run:
            self.orgplan_parser.save()
            self.logger.info("Saved orgplan changes")

        return stats

    def _find_matching_todo_task(
        self,
        orgplan_task: OrgplanTask,
        todo_by_id: dict[str, TodoTask],
        todo_by_title: dict[str, TodoTask],
    ) -> Optional[TodoTask]:
        """Find matching To Do task for an orgplan task.

        Args:
            orgplan_task: Orgplan task to match
            todo_by_id: Dictionary of To Do tasks by ID
            todo_by_title: Dictionary of To Do tasks by title

        Returns:
            Matching TodoTask or None
        """
        # Try matching by ms-todo-id first
        if orgplan_task.ms_todo_id and orgplan_task.ms_todo_id in todo_by_id:
            return todo_by_id[orgplan_task.ms_todo_id]

        # Fallback to title matching
        if orgplan_task.description in todo_by_title:
            return todo_by_title[orgplan_task.description]

        return None

    def _create_todo_task(self, orgplan_task: OrgplanTask) -> bool:
        """Create a new To Do task from orgplan task.

        Args:
            orgplan_task: Orgplan task to create

        Returns:
            True if task was created
        """
        importance = self._map_priority_to_importance(orgplan_task.priority)
        title = orgplan_task.description

        self.logger.info(f"Creating task: {title}")

        if self.dry_run:
            self.logger.info(f"  [DRY RUN] Would create task with importance={importance}")
            return True

        try:
            todo_task = self.todo_client.create_task(
                self.todo_list_id,
                title=title,
                importance=importance,
            )

            # Add ms-todo-id to orgplan
            self.orgplan_parser.add_detail_section(orgplan_task, ms_todo_id=todo_task.id)

            self.logger.info(f"  Created task with ID: {todo_task.id}")
            return True

        except Exception as e:
            self.logger.error(f"  Failed to create task: {e}")
            return False

    def _update_todo_task(
        self, orgplan_task: OrgplanTask, todo_task: TodoTask
    ) -> bool:
        """Update existing To Do task from orgplan task.

        Args:
            orgplan_task: Orgplan task (source)
            todo_task: To Do task (target)

        Returns:
            True if task was updated
        """
        updates = {}
        changes = []

        # Check title
        if orgplan_task.description != todo_task.title:
            updates["title"] = orgplan_task.description
            changes.append(f"title: '{todo_task.title}' -> '{orgplan_task.description}'")

        # Check status
        desired_status = self._map_orgplan_status_to_todo(orgplan_task.status)
        if desired_status != todo_task.status:
            updates["status"] = desired_status
            changes.append(f"status: {todo_task.status} -> {desired_status}")

        # Check importance
        desired_importance = self._map_priority_to_importance(orgplan_task.priority)
        if desired_importance != todo_task.importance:
            updates["importance"] = desired_importance
            changes.append(f"importance: {todo_task.importance} -> {desired_importance}")

        if not updates:
            self.logger.debug(f"Task '{orgplan_task.description}' is up to date")
            return False

        self.logger.info(f"Updating task: {orgplan_task.description}")
        for change in changes:
            self.logger.info(f"  {change}")

        if self.dry_run:
            self.logger.info("  [DRY RUN] Would update task")
            return True

        try:
            self.todo_client.update_task(
                self.todo_list_id,
                todo_task.id,
                **updates,
            )

            # Ensure ms-todo-id is in orgplan
            if not orgplan_task.ms_todo_id:
                self.orgplan_parser.add_detail_section(orgplan_task, ms_todo_id=todo_task.id)

            self.logger.info("  Updated successfully")
            return True

        except Exception as e:
            self.logger.error(f"  Failed to update task: {e}")
            return False

    def _map_priority_to_importance(self, priority: Optional[int]) -> str:
        """Map orgplan priority to To Do importance.

        Args:
            priority: Orgplan priority (1, 2, 3, etc.)

        Returns:
            To Do importance (low, normal, high)
        """
        if priority is None:
            return "normal"
        elif priority == 1:
            return "high"
        elif priority == 2:
            return "normal"
        else:  # 3+
            return "low"

    def _map_orgplan_status_to_todo(self, status: Optional[str]) -> str:
        """Map orgplan status to To Do status.

        Args:
            status: Orgplan status (DONE, DELEGATED, PENDING, or None)

        Returns:
            To Do status (notStarted, completed)
        """
        if status in ["DONE", "DELEGATED"]:
            return "completed"
        else:
            return "notStarted"
