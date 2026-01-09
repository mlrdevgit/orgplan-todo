"""Parser for orgplan markdown files."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class OrgplanTask:
    """Represents a task from orgplan."""

    description: str  # Task description without status/tags
    status: Optional[str] = None  # DONE, PENDING, DELEGATED, or None
    priority: Optional[int] = None  # 1, 2, 3, etc. from #p1, #p2, #p3
    raw_line: str = ""  # Original line from TODO list
    detail_section: str = ""  # Content of the detail section
    # Backend-specific task IDs
    ms_todo_id: Optional[str] = None  # Microsoft To Do task ID if synced
    google_tasks_id: Optional[str] = None  # Google Tasks task ID if synced
    line_number: int = 0  # Line number in the file


class OrgplanParser:
    """Parser for orgplan markdown files."""

    # Regex patterns
    STATUS_PATTERN = re.compile(r"\[(DONE|PENDING|DELEGATED)\]")
    PRIORITY_PATTERN = re.compile(r"#p(\d+)")
    TIME_ESTIMATE_PATTERN = re.compile(r"#\d+[hd]")
    BLOCKED_PATTERN = re.compile(r"#blocked")
    # Custom tags pattern - matches any remaining hashtags (e.g., #uma, #tag, #custom)
    CUSTOM_TAG_PATTERN = re.compile(r"#\w+")
    # Backend ID patterns
    MS_TODO_ID_PATTERN = re.compile(r"<!--\s*ms-todo-id:\s*([^\s]+)\s*-->")
    GOOGLE_TASKS_ID_PATTERN = re.compile(r"<!--\s*google-tasks-id:\s*([^\s]+)\s*-->")

    def __init__(self, file_path: Path):
        """Initialize parser with orgplan file path.

        Args:
            file_path: Path to the orgplan markdown file
        """
        self.file_path = file_path
        self.content = ""
        self.lines = []

    def load(self):
        """Load the orgplan file."""
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                self.content = f.read()
        except UnicodeDecodeError:
            # Fallback to CP1252 (Windows default) if UTF-8 fails
            with open(self.file_path, "r", encoding="cp1252") as f:
                self.content = f.read()
        
        self.lines = self.content.splitlines()

    def validate(self) -> list[str]:
        """Validate orgplan file format.

        Returns:
            List of validation warnings (empty if valid)
        """
        warnings = []

        if not self.lines:
            self.load()

        # Check for TODO List section
        has_todo_section = False
        for line in self.lines:
            if line.strip() == "# TODO List":
                has_todo_section = True
                break

        if not has_todo_section:
            warnings.append("File is missing '# TODO List' section")

        # Check for malformed task lines
        in_todo_section = False
        for i, line in enumerate(self.lines, 1):
            if line.strip() == "# TODO List":
                in_todo_section = True
                continue
            elif in_todo_section and line.startswith("# "):
                in_todo_section = False

            if in_todo_section and line.strip() and not line.startswith("- "):
                if not line.startswith("#"):  # Allow headers
                    warnings.append(
                        f"Line {i}: TODO List section should only contain task items (starting with '- ')"
                    )

        return warnings

    def parse_tasks(self) -> list[OrgplanTask]:
        """Parse all tasks from the TODO List section.

        Returns:
            List of OrgplanTask objects
        """
        if not self.lines:
            self.load()

        tasks = []
        in_todo_section = False
        todo_start_line = 0

        # Find TODO List section
        for i, line in enumerate(self.lines):
            if line.strip() == "# TODO List":
                in_todo_section = True
                todo_start_line = i + 1
            elif in_todo_section and line.startswith("# "):
                # End of TODO section (next top-level header)
                break
            elif in_todo_section and line.strip().startswith("- "):
                # Parse task line
                task = self._parse_task_line(line, i + 1)
                if task:
                    tasks.append(task)

        # Parse detail sections for each task
        for task in tasks:
            self._parse_detail_section(task)

        return tasks

    def _parse_task_line(self, line: str, line_number: int) -> Optional[OrgplanTask]:
        """Parse a single task line from TODO list.

        Args:
            line: Task line from markdown
            line_number: Line number in file (1-indexed)

        Returns:
            OrgplanTask object or None if invalid
        """
        # Remove leading "- "
        content = line.strip()[2:]

        # Extract status
        status_match = self.STATUS_PATTERN.search(content)
        status = status_match.group(1) if status_match else None

        # Extract priority
        priority_match = self.PRIORITY_PATTERN.search(content)
        priority = int(priority_match.group(1)) if priority_match else None

        # Remove status blocks, tags, and other metadata to get description
        description = content
        description = self.STATUS_PATTERN.sub("", description)
        description = self.PRIORITY_PATTERN.sub("", description)
        description = self.TIME_ESTIMATE_PATTERN.sub("", description)
        description = self.BLOCKED_PATTERN.sub("", description)
        # Remove any remaining custom tags (e.g., #uma, #tag, #custom)
        description = self.CUSTOM_TAG_PATTERN.sub("", description)
        description = description.strip()

        if not description:
            return None

        return OrgplanTask(
            description=description,
            status=status,
            priority=priority,
            raw_line=line,
            line_number=line_number,
        )

    def _parse_detail_section(self, task: OrgplanTask):
        """Parse detail section for a task.

        Args:
            task: OrgplanTask to update with detail section info
        """
        # Find the detail section header matching the task description
        section_header = f"# {task.description}"
        in_section = False
        section_lines = []

        for line in self.lines:
            if line.strip() == section_header:
                in_section = True
                continue
            elif in_section:
                if line.startswith("# "):
                    # Next top-level section
                    break
                section_lines.append(line)

        if section_lines:
            task.detail_section = "\n".join(section_lines).strip()

            # Extract backend IDs if present
            ms_id_match = self.MS_TODO_ID_PATTERN.search(task.detail_section)
            if ms_id_match:
                task.ms_todo_id = ms_id_match.group(1)

            google_id_match = self.GOOGLE_TASKS_ID_PATTERN.search(task.detail_section)
            if google_id_match:
                task.google_tasks_id = google_id_match.group(1)

    def update_task_status(self, task: OrgplanTask, new_status: Optional[str]):
        """Update task status in the orgplan file.

        Args:
            task: Task to update
            new_status: New status (DONE, PENDING, DELEGATED, or None)
        """
        if not self.lines:
            self.load()

        # Find and update the task line
        line_idx = task.line_number - 1
        if line_idx >= len(self.lines):
            return

        old_line = self.lines[line_idx]

        # Remove existing status
        new_line = self.STATUS_PATTERN.sub("", old_line).strip()

        # Add new status if provided
        if new_status:
            # Insert status after "- "
            new_line = f"- [{new_status}] {new_line[2:]}"
        else:
            # Ensure it still starts with "- "
            if not new_line.startswith("- "):
                new_line = "- " + new_line

        self.lines[line_idx] = new_line
        task.raw_line = new_line

    def update_task_description(self, task: OrgplanTask, new_description: str):
        """Update task description in the orgplan file.

        Args:
            task: Task to update
            new_description: New description
        """
        if not self.lines:
            self.load()

        line_idx = task.line_number - 1
        if line_idx >= len(self.lines):
            return

        # Preserve status and tags, update description
        parts = ["- "]

        if task.status:
            parts.append(f"[{task.status}] ")

        if task.priority:
            parts.append(f"#p{task.priority} ")

        parts.append(new_description)

        new_line = "".join(parts)
        self.lines[line_idx] = new_line
        task.raw_line = new_line
        task.description = new_description

    def update_task_priority(self, task: OrgplanTask, new_priority: Optional[int]):
        """Update task priority in the orgplan file.

        Args:
            task: Task to update
            new_priority: New priority (1, 2, 3, etc.) or None
        """
        if not self.lines:
            self.load()

        line_idx = task.line_number - 1
        if line_idx >= len(self.lines):
            return

        old_line = self.lines[line_idx]

        # Remove existing priority
        new_line = self.PRIORITY_PATTERN.sub("", old_line).strip()

        # Add new priority if provided
        if new_priority:
            # Insert after status if present, otherwise after "- "
            status_match = self.STATUS_PATTERN.search(new_line)
            if status_match:
                insert_pos = status_match.end()
                new_line = new_line[:insert_pos] + f" #p{new_priority}" + new_line[insert_pos:]
            else:
                new_line = f"- #p{new_priority} {new_line[2:]}"

        self.lines[line_idx] = new_line.strip()
        task.raw_line = self.lines[line_idx]
        task.priority = new_priority

    def add_task(
        self, description: str, status: Optional[str] = None, priority: Optional[int] = None
    ) -> OrgplanTask:
        """Add a new task to the TODO list section.

        Args:
            description: Task description
            status: Optional status (DONE, PENDING, DELEGATED)
            priority: Optional priority level

        Returns:
            Created OrgplanTask object
        """
        if not self.lines:
            self.load()

        # Build task line
        parts = ["- "]

        if status:
            parts.append(f"[{status}] ")

        if priority:
            parts.append(f"#p{priority} ")

        parts.append(description)
        task_line = "".join(parts)

        # Find TODO List section and insert
        todo_section_end = 0
        for i, line in enumerate(self.lines):
            if line.strip() == "# TODO List":
                todo_section_end = i + 1
            elif todo_section_end > 0 and line.startswith("# "):
                # Found next section, insert before it
                break
            elif todo_section_end > 0 and line.strip().startswith("- "):
                todo_section_end = i + 1

        # Insert the new task
        self.lines.insert(todo_section_end, task_line)

        task = OrgplanTask(
            description=description,
            status=status,
            priority=priority,
            raw_line=task_line,
            line_number=todo_section_end + 1,
        )

        return task

    def add_detail_section(self, task: OrgplanTask, **backend_ids):
        """Add or update detail section for a task with backend IDs.

        Args:
            task: Task to add detail section for
            **backend_ids: Backend IDs to add (e.g., ms_todo_id="xyz", google_tasks_id="abc")
        """
        if not self.lines:
            self.load()

        # Check if detail section already exists
        section_header = f"# {task.description}"
        section_exists = False
        section_start = -1

        for i, line in enumerate(self.lines):
            if line.strip() == section_header:
                section_exists = True
                section_start = i
                break

        if not section_exists:
            # Add new section at the end
            self.lines.append("")
            self.lines.append(section_header)
            self.lines.append("")
            section_start = len(self.lines) - 2

        # Mapping of backend ID names to their patterns and marker formats
        id_mappings = {
            "ms_todo_id": (self.MS_TODO_ID_PATTERN, "ms-todo-id"),
            "google_tasks_id": (self.GOOGLE_TASKS_ID_PATTERN, "google-tasks-id"),
        }

        # Add or update backend ID markers
        for id_name, id_value in backend_ids.items():
            if not id_value or id_name not in id_mappings:
                continue

            pattern, marker_name = id_mappings[id_name]
            id_marker = f"<!-- {marker_name}: {id_value} -->"

            # Check if ID already exists in section
            id_found = False
            for i in range(section_start + 1, len(self.lines)):
                if self.lines[i].startswith("# "):
                    break
                if pattern.search(self.lines[i]):
                    # Update existing ID
                    self.lines[i] = id_marker
                    setattr(task, id_name, id_value)
                    id_found = True
                    break

            if not id_found:
                # Insert new ID marker after section header
                # Find where to insert (after other ID markers if any)
                insert_pos = section_start + 1
                for i in range(section_start + 1, len(self.lines)):
                    if self.lines[i].startswith("# "):
                        break
                    if any(pattern.search(self.lines[i]) for pattern, _ in id_mappings.values()):
                        insert_pos = i + 1
                    elif self.lines[i].strip() == "":
                        continue
                    else:
                        break

                self.lines.insert(insert_pos, id_marker)
                setattr(task, id_name, id_value)

    def save(self):
        """Save changes back to the orgplan file."""
        with open(self.file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(self.lines))
            if self.lines and not self.lines[-1].endswith("\n"):
                f.write("\n")
