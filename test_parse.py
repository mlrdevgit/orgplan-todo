#!/usr/bin/env python3
"""Quick test to verify orgplan parser works correctly."""

import sys
from pathlib import Path

# Add tools directory to path
sys.path.insert(0, str(Path(__file__).parent / "tools"))

from orgplan_parser import OrgplanParser

def test_parser():
    """Test the orgplan parser."""
    parser = OrgplanParser(Path("2025/12-notes.md"))
    parser.load()

    tasks = parser.parse_tasks()

    print(f"Found {len(tasks)} tasks:")
    print()

    for i, task in enumerate(tasks, 1):
        print(f"{i}. {task.description}")
        print(f"   Status: {task.status}")
        print(f"   Priority: {task.priority}")
        print(f"   MS Todo ID: {task.ms_todo_id}")
        print(f"   Has detail section: {bool(task.detail_section)}")
        print()

    return tasks

if __name__ == "__main__":
    tasks = test_parser()
    print(f"\nTotal: {len(tasks)} tasks parsed successfully!")
