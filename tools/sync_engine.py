"""Sync engine for orgplan and task backends."""

import logging
import re
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

        # Patterns used to strip backend ID markers from detail sections
        self._id_marker_patterns = [
            OrgplanParser.MS_TODO_ID_PATTERN,
            OrgplanParser.GOOGLE_TASKS_ID_PATTERN,
        ]

    def _extract_notes_from_detail_section(self, detail_section: str) -> Optional[str]:
        """Extract plain notes text from a detail section, stripping backend ID markers.

        Args:
            detail_section: Raw detail section content (may contain ID markers)

        Returns:
            Clean notes text, or None if no meaningful content exists
        """
        if not detail_section or not detail_section.strip():
            return None

        lines = detail_section.split("\n")
        notes_lines = []
        for line in lines:
            if any(p.search(line) for p in self._id_marker_patterns):
                continue
            notes_lines.append(line)

        notes = "\n".join(notes_lines).strip()
        return notes if notes else None

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
                # Find matching To Do task
                todo_task = self._find_matching_todo_task(orgplan_task, todo_by_id, todo_by_title)

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
        """Find matching backend task for an orgplan task.

        Args:
            orgplan_task: Orgplan task to match
            todo_by_id: Dictionary of backend tasks by ID
            todo_by_title: Dictionary of backend tasks by title

        Returns:
            Matching TaskItem or None
        """
        # Try matching by backend-specific ID first
        backend_id_attr = self.backend.id_marker_prefix.replace("-", "_")
        backend_id = getattr(orgplan_task, backend_id_attr, None)

        if backend_id and backend_id in todo_by_id:
            return todo_by_id[backend_id]

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
            notes = self._extract_notes_from_detail_section(orgplan_task.detail_section)
            task_item = TaskItem(
                id="",  # Will be assigned by backend
                title=title,
                status="active",
                importance=importance,
                body=notes,
                due_date=orgplan_task.due_date,
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

    def _update_todo_task(self, orgplan_task: OrgplanTask, todo_task: TaskItem) -> bool:
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

        # Check importance (only if backend supports priority)
        if self.backend.supports_priority:
            desired_importance = self._map_priority_to_importance(orgplan_task.priority)
            if desired_importance != todo_task.importance:
                updates["importance"] = desired_importance
                changes.append(f"importance: {todo_task.importance} -> {desired_importance}")

        # Check due date (only if orgplan has one set)
        if orgplan_task.due_date and orgplan_task.due_date != todo_task.due_date:
            updates["due_date"] = orgplan_task.due_date
            changes.append(f"due_date: {todo_task.due_date} -> {orgplan_task.due_date}")

        # Check notes/body
        orgplan_notes = self._extract_notes_from_detail_section(orgplan_task.detail_section)
        remote_body = todo_task.body.strip() if todo_task.body else None
        if (orgplan_notes or remote_body) and orgplan_notes != remote_body:
            updates["body"] = orgplan_notes
            changes.append(f"body: '{remote_body or ''}' -> '{orgplan_notes or ''}'")

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
                body=updates.get("body", todo_task.body),
                due_date=updates.get("due_date", todo_task.due_date),
            )

            self.backend.update_task(self.task_list_id, updated_task)

            # Ensure backend ID is in orgplan
            backend_id_attr = self.backend.id_marker_prefix.replace("-", "_")
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
        if status in ["DONE", "DELEGATED", "CANCELED"]:
            return "completed"
        else:
            return "active"

    def sync_todo_to_orgplan(
        self, orgplan_tasks: list[OrgplanTask], todo_tasks: list[TaskItem]
    ) -> dict:
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
        backend_id_attr = self.backend.id_marker_prefix.replace("-", "_")

        for task in orgplan_tasks:
            backend_id = getattr(task, backend_id_attr, None)
            if backend_id:
                orgplan_by_id[backend_id] = task
            orgplan_by_title[task.description] = task

        # Process each To Do task
        for todo_task in todo_tasks:
            try:
                # Skip completed tasks that don't exist in orgplan
                # (they were likely completed in a previous month)
                if todo_task.is_completed and todo_task.id not in orgplan_by_id:
                    self.logger.debug(
                        f"Skipping completed To Do task not in orgplan: {todo_task.title}"
                    )
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
        # Only map priority if backend supports it
        priority = (
            self._map_importance_to_priority(todo_task.importance)
            if self.backend.supports_priority
            else None
        )

        self.logger.info(f"Creating orgplan task: {todo_task.title}")

        if self.dry_run:
            self.logger.info(
                f"  [DRY RUN] Would create task with status={status}, priority={priority}"
            )
            return True

        try:
            # Add task to orgplan
            orgplan_task = self.orgplan_parser.add_task(
                description=todo_task.title,
                status=status,
                priority=priority,
                due_date=todo_task.due_date,
                due_marker_style="plain" if todo_task.due_date else None,
            )

            # Add detail section with backend-specific ID
            backend_id_attr = self.backend.id_marker_prefix.replace("-", "_")
            id_kwargs = {backend_id_attr: todo_task.id}
            self.orgplan_parser.add_detail_section(orgplan_task, **id_kwargs)

            # Add body to detail section if present and not empty
            if todo_task.body and todo_task.body.strip():
                self.orgplan_parser.update_detail_section_body(
                    orgplan_task, todo_task.body.strip()
                )

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

        # Check priority (only if backend supports it)
        if self.backend.supports_priority:
            desired_priority = self._map_importance_to_priority(todo_task.importance)
            if desired_priority != orgplan_task.priority:
                changes.append(f"priority: {orgplan_task.priority} -> {desired_priority}")
                if not self.dry_run:
                    self.orgplan_parser.update_task_priority(orgplan_task, desired_priority)
                modified = True

        # Check due date (prefer title marker unless detail already has a deadline marker)
        if todo_task.due_date and todo_task.due_date != orgplan_task.due_date:
            if not orgplan_task.detail_has_deadline_marker:
                changes.append(f"due_date: {orgplan_task.due_date} -> {todo_task.due_date}")
                if not self.dry_run:
                    self.orgplan_parser.update_task_due_date(
                        orgplan_task, todo_task.due_date, "plain"
                    )
                modified = True

        # Sync detail section body (only if orgplan detail section has no notes content)
        backend_id_attr = self.backend.id_marker_prefix.replace("-", "_")
        orgplan_notes = self._extract_notes_from_detail_section(orgplan_task.detail_section)

        if todo_task.body and todo_task.body.strip() and not orgplan_notes:
            changes.append("adding backend notes to detail section")
            if not self.dry_run:
                if not getattr(orgplan_task, backend_id_attr, None):
                    id_kwargs = {backend_id_attr: todo_task.id}
                    self.orgplan_parser.add_detail_section(orgplan_task, **id_kwargs)
                self.orgplan_parser.update_detail_section_body(
                    orgplan_task, todo_task.body.strip()
                )
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

        # Ensure backend ID is present
        if not getattr(orgplan_task, backend_id_attr, None):
            id_kwargs = {backend_id_attr: todo_task.id}
            self.orgplan_parser.add_detail_section(orgplan_task, **id_kwargs)

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
