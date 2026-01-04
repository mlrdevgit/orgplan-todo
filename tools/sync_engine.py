"""Sync engine for orgplan and task backends."""

import logging
from typing import Optional

from backends.base import TaskBackend, TaskItem
from orgplan_parser import OrgplanParser, OrgplanTask


class SyncEngine:
    """Coordinates synchronization between orgplan and task backend."""

    def __init__(
        self,
        orgplan_parser: OrgplanParser,
        backend: TaskBackend,
        task_list_id: str,
        dry_run: bool = False,
    ):
        """Initialize sync engine.

        Args:
            orgplan_parser: Parser for orgplan file
            backend: Task backend (Microsoft To Do, Google Tasks, etc.)
            task_list_id: ID of the task list to sync with
            dry_run: If True, preview changes without applying
        """
        self.orgplan_parser = orgplan_parser
        self.backend = backend
        self.task_list_id = task_list_id
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
        todo_tasks = self.backend.get_tasks(self.task_list_id)
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
        todo_by_id: dict[str, TaskItem],
        todo_by_title: dict[str, TaskItem],
    ) -> Optional[TaskItem]:
        """Find matching To Do task for an orgplan task.

        Args:
            orgplan_task: Orgplan task to match
            todo_by_id: Dictionary of To Do tasks by ID
            todo_by_title: Dictionary of To Do tasks by title

        Returns:
            Matching TaskItem or None
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
            # Create TaskItem for new task
            task_item = TaskItem(
                id="",  # Will be assigned by backend
                title=title,
                status="active",
                importance=importance,
                body=None,
            )

            created_task = self.backend.create_task(self.task_list_id, task_item)

            # Add backend ID to orgplan
            id_marker = {f"{self.backend.id_marker_prefix.replace('-', '_')}": created_task.id}
            self.orgplan_parser.add_detail_section(orgplan_task, **id_marker)

            self.logger.info(f"  Created task with ID: {created_task.id}")
            return True

        except Exception as e:
            self.logger.error(f"  Failed to create task: {e}")
            return False

    def _update_todo_task(
        self, orgplan_task: OrgplanTask, todo_task: TaskItem
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
            # Create updated TaskItem
            updated_task = TaskItem(
                id=todo_task.id,
                title=updates.get("title", todo_task.title),
                status=updates.get("status", todo_task.status),
                importance=updates.get("importance", todo_task.importance),
                body=todo_task.body,
            )

            self.backend.update_task(self.task_list_id, updated_task)

            # Ensure backend ID is in orgplan
            backend_id_attr = self.backend.id_marker_prefix.replace('-', '_')
            if not getattr(orgplan_task, backend_id_attr, None):
                id_marker = {backend_id_attr: todo_task.id}
                self.orgplan_parser.add_detail_section(orgplan_task, **id_marker)

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
        """Map orgplan status to backend task status.

        Args:
            status: Orgplan status (DONE, DELEGATED, PENDING, or None)

        Returns:
            Backend status (active, completed)
        """
        if status in ["DONE", "DELEGATED"]:
            return "completed"
        else:
            return "active"

    def sync_todo_to_orgplan(self, orgplan_tasks: list[OrgplanTask], todo_tasks: list[TaskItem]) -> dict:
        """Sync tasks from Microsoft To Do to orgplan (Phase 2).

        Args:
            orgplan_tasks: List of orgplan tasks
            todo_tasks: List of To Do tasks

        Returns:
            Dictionary with sync statistics
        """
        stats = {
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0,
        }

        # Build lookup maps for orgplan tasks
        orgplan_by_id = {}
        orgplan_by_title = {}
        for task in orgplan_tasks:
            if task.ms_todo_id:
                orgplan_by_id[task.ms_todo_id] = task
            orgplan_by_title[task.description] = task

        # Process each To Do task
        for todo_task in todo_tasks:
            try:
                # Skip completed tasks that don't exist in orgplan
                # (they were likely completed in a previous month)
                if todo_task.is_completed and todo_task.id not in orgplan_by_id:
                    self.logger.debug(f"Skipping completed To Do task not in orgplan: {todo_task.title}")
                    stats["skipped"] += 1
                    continue

                # Find matching orgplan task
                orgplan_task = self._find_matching_orgplan_task(
                    todo_task, orgplan_by_id, orgplan_by_title
                )

                if orgplan_task:
                    # Update existing task
                    if self._update_orgplan_task(orgplan_task, todo_task):
                        stats["updated"] += 1
                    else:
                        stats["skipped"] += 1
                else:
                    # Create new task from To Do
                    if self._create_orgplan_task(todo_task):
                        stats["created"] += 1

            except Exception as e:
                self.logger.error(f"Error processing To Do task '{todo_task.title}': {e}")
                stats["errors"] += 1

        return stats

    def _find_matching_orgplan_task(
        self,
        todo_task: TaskItem,
        orgplan_by_id: dict[str, OrgplanTask],
        orgplan_by_title: dict[str, OrgplanTask],
    ) -> Optional[OrgplanTask]:
        """Find matching orgplan task for a To Do task.

        Args:
            todo_task: To Do task to match
            orgplan_by_id: Dictionary of orgplan tasks by ms-todo-id
            orgplan_by_title: Dictionary of orgplan tasks by description

        Returns:
            Matching OrgplanTask or None
        """
        # Try matching by ID first
        if todo_task.id in orgplan_by_id:
            return orgplan_by_id[todo_task.id]

        # Fallback to title matching
        if todo_task.title in orgplan_by_title:
            return orgplan_by_title[todo_task.title]

        return None

    def _create_orgplan_task(self, todo_task: TaskItem) -> bool:
        """Create a new orgplan task from To Do task.

        Args:
            todo_task: To Do task to create

        Returns:
            True if task was created
        """
        status = self._map_todo_status_to_orgplan(todo_task.status)
        priority = self._map_importance_to_priority(todo_task.importance)

        self.logger.info(f"Creating orgplan task: {todo_task.title}")

        if self.dry_run:
            self.logger.info(f"  [DRY RUN] Would create task with status={status}, priority={priority}")
            return True

        try:
            # Add task to orgplan
            orgplan_task = self.orgplan_parser.add_task(
                description=todo_task.title,
                status=status,
                priority=priority,
            )

            # Add detail section with ms-todo-id and body if present
            self.orgplan_parser.add_detail_section(orgplan_task, ms_todo_id=todo_task.id)

            # Add body to detail section if present and not empty
            if todo_task.body and todo_task.body.strip():
                # We need to update the detail section with the body
                # For now, we'll just add the ID marker
                # The body content will be handled in detail section sync
                pass

            self.logger.info(f"  Created orgplan task")
            return True

        except Exception as e:
            self.logger.error(f"  Failed to create orgplan task: {e}")
            return False

    def _update_orgplan_task(self, orgplan_task: OrgplanTask, todo_task: TaskItem) -> bool:
        """Update existing orgplan task from To Do task.

        Args:
            orgplan_task: Orgplan task (target)
            todo_task: To Do task (source)

        Returns:
            True if task was updated
        """
        changes = []
        modified = False

        # Check title
        if todo_task.title != orgplan_task.description:
            changes.append(f"title: '{orgplan_task.description}' -> '{todo_task.title}'")
            if not self.dry_run:
                self.orgplan_parser.update_task_description(orgplan_task, todo_task.title)
                modified = True

        # Check status
        desired_status = self._map_todo_status_to_orgplan(todo_task.status)
        if desired_status != orgplan_task.status:
            changes.append(f"status: {orgplan_task.status} -> {desired_status}")
            if not self.dry_run:
                self.orgplan_parser.update_task_status(orgplan_task, desired_status)
                modified = True

        # Check priority
        desired_priority = self._map_importance_to_priority(todo_task.importance)
        if desired_priority != orgplan_task.priority:
            changes.append(f"priority: {orgplan_task.priority} -> {desired_priority}")
            if not self.dry_run:
                self.orgplan_parser.update_task_priority(orgplan_task, desired_priority)
                modified = True

        # Sync detail section body (only if orgplan detail section is empty)
        if todo_task.body and todo_task.body.strip() and not orgplan_task.detail_section.strip():
            changes.append("adding To Do notes to empty detail section")
            if not self.dry_run:
                # The detail section sync would happen here
                # For now, we just ensure the ms-todo-id is present
                if not orgplan_task.ms_todo_id:
                    self.orgplan_parser.add_detail_section(orgplan_task, ms_todo_id=todo_task.id)
                modified = True

        if not changes:
            self.logger.debug(f"Orgplan task '{orgplan_task.description}' is up to date")
            return False

        self.logger.info(f"Updating orgplan task: {orgplan_task.description}")
        for change in changes:
            self.logger.info(f"  {change}")

        if self.dry_run:
            self.logger.info("  [DRY RUN] Would update orgplan task")
            return True

        # Ensure ms-todo-id is present
        if not orgplan_task.ms_todo_id:
            self.orgplan_parser.add_detail_section(orgplan_task, ms_todo_id=todo_task.id)

        self.logger.info("  Updated successfully")
        return modified

    def _map_importance_to_priority(self, importance: str) -> Optional[int]:
        """Map To Do importance to orgplan priority.

        Args:
            importance: To Do importance (low, normal, high)

        Returns:
            Orgplan priority (1, 2, 3) or None
        """
        if importance == "high":
            return 1
        elif importance == "normal":
            return 2
        elif importance == "low":
            return 3
        else:
            return None

    def _map_todo_status_to_orgplan(self, status: str) -> Optional[str]:
        """Map backend task status to orgplan status.

        Args:
            status: Backend status (active, completed)

        Returns:
            Orgplan status (DONE, PENDING, or None)
        """
        if status == "completed":
            return "DONE"
        elif status == "active":
            return None  # Active tasks don't need a status marker
        else:
            return None

    def sync_bidirectional(self) -> dict:
        """Perform bidirectional sync between orgplan and To Do (Phase 2).

        Returns:
            Dictionary with combined sync statistics
        """
        self.logger.info("=" * 60)
        self.logger.info("Phase 1: Syncing Orgplan -> To Do")
        self.logger.info("=" * 60)

        # Load tasks once
        orgplan_tasks = self.orgplan_parser.parse_tasks()
        self.logger.info(f"Found {len(orgplan_tasks)} tasks in orgplan")

        todo_tasks = self.backend.get_tasks(self.task_list_id)
        self.logger.info(f"Found {len(todo_tasks)} tasks in To Do")

        # Phase 1: Orgplan -> To Do
        stats_to_todo = self.sync_orgplan_to_todo()

        # Reload tasks after Phase 1 changes
        if stats_to_todo["created"] > 0 or stats_to_todo["updated"] > 0:
            self.logger.info("Reloading tasks after orgplan -> To Do sync...")
            orgplan_tasks = self.orgplan_parser.parse_tasks()
            todo_tasks = self.backend.get_tasks(self.task_list_id)

        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info("Phase 2: Syncing To Do -> Orgplan")
        self.logger.info("=" * 60)

        # Phase 2: To Do -> Orgplan
        stats_to_orgplan = self.sync_todo_to_orgplan(orgplan_tasks, todo_tasks)

        # Save orgplan changes if not dry run
        if not self.dry_run:
            self.orgplan_parser.save()
            self.logger.info("Saved orgplan changes")

        # Combine statistics
        combined_stats = {
            "orgplan_to_todo": stats_to_todo,
            "todo_to_orgplan": stats_to_orgplan,
            "total_created": stats_to_todo["created"] + stats_to_orgplan["created"],
            "total_updated": stats_to_todo["updated"] + stats_to_orgplan["updated"],
            "total_errors": stats_to_todo["errors"] + stats_to_orgplan["errors"],
        }

        return combined_stats
