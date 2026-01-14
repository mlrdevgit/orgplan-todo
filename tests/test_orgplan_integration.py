
"""Tests for OrgplanParser using orgplan library integration."""

import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from tools.orgplan_parser import OrgplanParser

# Helper to mock orgplan.markup.parse_title_parts
def mock_parse(content):
    # Mimic simple parsing logic for testing
    state = "open"
    tags = []
    
    if content.startswith("[DONE]"):
        state = "done"
        content = content[6:].strip()
    
    words = content.split()
    clean_words = []
    for word in words:
        if word.startswith("#"):
            tags.append(word[1:])
        else:
            clean_words.append(word)
            
    return state, tags, " ".join(clean_words)


class TestOrgplanIntegration(unittest.TestCase):
    """Test OrgplanParser with orgplan library integration."""

    @patch("tools.orgplan_parser.parse_title_parts")
    def test_parse_task_line_integration(self, mock_parser):
        """Test parsing a task line using the integration."""
        
        # Setup mock to return specific values
        # Case 1: Simple task
        mock_parser.return_value = ("open", [], "Task Title")
        
        parser = OrgplanParser(Path("dummy.md"))
        task = parser._parse_task_line("- Task Title", 1)
        
        self.assertEqual(task.description, "Task Title")
        self.assertIsNone(task.status)
        self.assertIsNone(task.priority)
        
        # Case 2: Task with status and priority tag
        mock_parser.return_value = ("done", ["p1"], "Important Task")
        task = parser._parse_task_line("- [DONE] Important Task #p1", 2)
        
        self.assertEqual(task.description, "Important Task")
        self.assertEqual(task.status, "DONE")
        self.assertEqual(task.priority, 1)
        
        # Case 3: Task with other tags
        mock_parser.return_value = ("pending", ["weekly", "2h"], "Weekly Task")
        task = parser._parse_task_line("- [PENDING] Weekly Task #weekly", 3)
        
        self.assertEqual(task.description, "Weekly Task")
        self.assertEqual(task.status, "PENDING")
        self.assertIsNone(task.priority)

    def test_fallback_parsing(self):
        """Test fallback to regex parsing if orgplan is not available."""
        # Force parse_title_parts to be None
        with patch("tools.orgplan_parser.parse_title_parts", None):
            parser = OrgplanParser(Path("dummy.md"))
            
            # Test simple task
            task = parser._parse_task_line("- Task Title", 1)
            self.assertEqual(task.description, "Task Title")
            
            # Test priority
            task = parser._parse_task_line("- Task #p1", 2)
            self.assertEqual(task.description, "Task")
            self.assertEqual(task.priority, 1)

if __name__ == "__main__":
    unittest.main()
