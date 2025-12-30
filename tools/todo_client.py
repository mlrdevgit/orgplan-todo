"""Microsoft To Do client using Graph API."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import msal
import requests


@dataclass
class TodoTask:
    """Represents a Microsoft To Do task."""

    id: str
    title: str
    status: str  # "notStarted" or "completed"
    importance: str  # "low", "normal", "high"
    body: Optional[str] = None
    completed_datetime: Optional[str] = None

    @property
    def is_completed(self) -> bool:
        """Check if task is completed."""
        return self.status == "completed"


class TodoClient:
    """Client for Microsoft To Do via Graph API."""

    GRAPH_API_ENDPOINT = "https://graph.microsoft.com/v1.0"
    SCOPES = ["https://graph.microsoft.com/.default"]

    def __init__(self, client_id: str, tenant_id: str, client_secret: str):
        """Initialize To Do client.

        Args:
            client_id: Azure AD application client ID
            tenant_id: Azure AD tenant ID
            client_secret: Azure AD application client secret
        """
        self.client_id = client_id
        self.tenant_id = tenant_id
        self.client_secret = client_secret
        self.access_token = None

    def authenticate(self):
        """Authenticate with Microsoft Graph API using client credentials.

        Raises:
            Exception: If authentication fails
        """
        authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        app = msal.ConfidentialClientApplication(
            self.client_id,
            authority=authority,
            client_credential=self.client_secret,
        )

        result = app.acquire_token_for_client(scopes=self.SCOPES)

        if "access_token" in result:
            self.access_token = result["access_token"]
        else:
            error = result.get("error_description", result.get("error", "Unknown error"))
            raise Exception(f"Authentication failed: {error}")

    def _get_headers(self) -> dict:
        """Get HTTP headers for API requests.

        Returns:
            Dictionary of headers
        """
        if not self.access_token:
            raise Exception("Not authenticated. Call authenticate() first.")

        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def _make_request(
        self, method: str, endpoint: str, json_data: Optional[dict] = None
    ) -> dict:
        """Make HTTP request to Graph API.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            endpoint: API endpoint (without base URL)
            json_data: Optional JSON data for request body

        Returns:
            Response JSON

        Raises:
            Exception: If request fails
        """
        url = f"{self.GRAPH_API_ENDPOINT}{endpoint}"
        response = requests.request(
            method=method,
            url=url,
            headers=self._get_headers(),
            json=json_data,
            timeout=30,
        )

        if response.status_code >= 400:
            raise Exception(
                f"API request failed: {response.status_code} - {response.text}"
            )

        return response.json() if response.content else {}

    def get_task_lists(self) -> list[dict]:
        """Get all To Do lists for the authenticated user.

        Returns:
            List of task list dictionaries

        Raises:
            Exception: If request fails
        """
        result = self._make_request("GET", "/me/todo/lists")
        return result.get("value", [])

    def get_list_by_name(self, list_name: str) -> Optional[dict]:
        """Get a To Do list by name.

        Args:
            list_name: Name of the list to find

        Returns:
            List dictionary or None if not found

        Raises:
            Exception: If request fails
        """
        lists = self.get_task_lists()
        for task_list in lists:
            if task_list.get("displayName") == list_name:
                return task_list
        return None

    def get_tasks(self, list_id: str) -> list[TodoTask]:
        """Get all tasks from a To Do list.

        Args:
            list_id: ID of the To Do list

        Returns:
            List of TodoTask objects

        Raises:
            Exception: If request fails
        """
        result = self._make_request("GET", f"/me/todo/lists/{list_id}/tasks")
        tasks = result.get("value", [])

        return [
            TodoTask(
                id=task["id"],
                title=task.get("title", ""),
                status=task.get("status", "notStarted"),
                importance=task.get("importance", "normal"),
                body=task.get("body", {}).get("content"),
                completed_datetime=task.get("completedDateTime", {}).get("dateTime"),
            )
            for task in tasks
        ]

    def create_task(
        self,
        list_id: str,
        title: str,
        importance: str = "normal",
        body: Optional[str] = None,
    ) -> TodoTask:
        """Create a new task in a To Do list.

        Args:
            list_id: ID of the To Do list
            title: Task title
            importance: Task importance (low, normal, high)
            body: Optional task body/notes

        Returns:
            Created TodoTask object

        Raises:
            Exception: If request fails
        """
        task_data = {
            "title": title,
            "importance": importance,
            "status": "notStarted",
        }

        if body:
            task_data["body"] = {"contentType": "text", "content": body}

        result = self._make_request("POST", f"/me/todo/lists/{list_id}/tasks", task_data)

        return TodoTask(
            id=result["id"],
            title=result.get("title", ""),
            status=result.get("status", "notStarted"),
            importance=result.get("importance", "normal"),
            body=result.get("body", {}).get("content"),
        )

    def update_task(
        self,
        list_id: str,
        task_id: str,
        title: Optional[str] = None,
        importance: Optional[str] = None,
        status: Optional[str] = None,
        body: Optional[str] = None,
    ) -> TodoTask:
        """Update an existing task.

        Args:
            list_id: ID of the To Do list
            task_id: ID of the task to update
            title: Optional new title
            importance: Optional new importance
            status: Optional new status (notStarted, completed)
            body: Optional new body/notes

        Returns:
            Updated TodoTask object

        Raises:
            Exception: If request fails
        """
        task_data = {}

        if title is not None:
            task_data["title"] = title
        if importance is not None:
            task_data["importance"] = importance
        if status is not None:
            task_data["status"] = status
        if body is not None:
            task_data["body"] = {"contentType": "text", "content": body}

        result = self._make_request(
            "PATCH", f"/me/todo/lists/{list_id}/tasks/{task_id}", task_data
        )

        return TodoTask(
            id=result["id"],
            title=result.get("title", ""),
            status=result.get("status", "notStarted"),
            importance=result.get("importance", "normal"),
            body=result.get("body", {}).get("content"),
            completed_datetime=result.get("completedDateTime", {}).get("dateTime"),
        )

    def complete_task(self, list_id: str, task_id: str) -> TodoTask:
        """Mark a task as completed.

        Args:
            list_id: ID of the To Do list
            task_id: ID of the task

        Returns:
            Updated TodoTask object

        Raises:
            Exception: If request fails
        """
        return self.update_task(list_id, task_id, status="completed")

    def reopen_task(self, list_id: str, task_id: str) -> TodoTask:
        """Reopen a completed task.

        Args:
            list_id: ID of the To Do list
            task_id: ID of the task

        Returns:
            Updated TodoTask object

        Raises:
            Exception: If request fails
        """
        return self.update_task(list_id, task_id, status="notStarted")
