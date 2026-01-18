"""Tests for due date parsing and formatting in OrgplanParser."""

import datetime
from pathlib import Path

from tools.orgplan_parser import OrgplanParser


def _write_tmp(tmp_path, content: str) -> Path:
    path = tmp_path / "notes.md"
    path.write_text(content, encoding="utf-8")
    return path


def test_parses_plain_date_due(tmp_path):
    content = "# TODO List\n- Ship it <2025-06-15>\n"
    path = _write_tmp(tmp_path, content)
    parser = OrgplanParser(path)

    tasks = parser.parse_tasks()

    assert len(tasks) == 1
    assert tasks[0].description == "Ship it"
    assert tasks[0].due_date == datetime.date(2025, 6, 15)
    assert tasks[0].due_marker_style == "plain"


def test_parses_deadline_marker_due(tmp_path):
    content = "# TODO List\n- Ship it DEADLINE: <2025-06-15>\n"
    path = _write_tmp(tmp_path, content)
    parser = OrgplanParser(path)

    tasks = parser.parse_tasks()

    assert len(tasks) == 1
    assert tasks[0].description == "Ship it"
    assert tasks[0].due_date == datetime.date(2025, 6, 15)
    assert tasks[0].due_marker_style == "deadline"


def test_parses_detail_deadline_due(tmp_path):
    content = "# TODO List\n- Ship it\n\n# Ship it\nDEADLINE: <2025-06-20>\n"
    path = _write_tmp(tmp_path, content)
    parser = OrgplanParser(path)

    tasks = parser.parse_tasks()

    assert len(tasks) == 1
    assert tasks[0].due_date == datetime.date(2025, 6, 20)
    assert tasks[0].detail_has_deadline_marker is True
    assert tasks[0].due_marker_style is None


def test_update_task_due_date_adds_marker(tmp_path):
    content = "# TODO List\n- Ship it\n"
    path = _write_tmp(tmp_path, content)
    parser = OrgplanParser(path)

    tasks = parser.parse_tasks()
    parser.update_task_due_date(tasks[0], datetime.date(2025, 6, 30), "plain")

    assert parser.lines[1].endswith("<2025-06-30>")
