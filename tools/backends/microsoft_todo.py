"""Microsoft To Do backend implementation using Graph API."""

from datetime import datetime
from typing import Optional
from pathlib import Path
import logging
import webbrowser

import msal
import requests

from .base import TaskBackend, TaskItem
from errors import retry_on_failure, APIError, NetworkError
from token_storage import TokenStorage


class MicrosoftTodoBackend(TaskBackend):
    """Microsoft To Do backend implementation.

    Supports two authentication modes:
    - application: Client credentials flow (requires client secret, admin consent)
    - delegated: Device code flow (user login, no admin consent needed)
    """

    GRAPH_API_ENDPOINT = "https://graph.microsoft.com/v1.0"
    SCOPES_APPLICATION = ["https://graph.microsoft.com/.default"]
    # Device code flow automatically includes refresh token support
    SCOPES_DELEGATED = ["Tasks.ReadWrite"]

    def __init__(
        self,
        client_id: str,
        tenant_id: str,
        auth_mode: str = "application",
        client_secret: Optional[str] = None,
        token_storage_path: Optional[Path] = None,
        allow_prompt: bool = True,
        logger: Optional[logging.Logger] = None,
    ):
        """Initialize Microsoft To Do backend.

        Args:
            client_id: Azure AD application client ID
            tenant_id: Azure AD tenant ID
            auth_mode: Authentication mode ("application" or "delegated")
            client_secret: Client secret (required for application mode)
            token_storage_path: Path to store tokens (for delegated mode)
            allow_prompt: Allow interactive authentication prompt (False for cron)
            logger: Optional logger for messages
        """
        self.client_id = client_id
        self.tenant_id = tenant_id
        self.auth_mode = auth_mode.lower()
        self.client_secret = client_secret
        self.allow_prompt = allow_prompt
        self.access_token = None
        self.logger = logger or logging.getLogger(__name__)

        # Token storage for delegated mode
        if self.auth_mode == "delegated":
            self.token_storage = TokenStorage(token_storage_path, logger=self.logger)
        else:
            self.token_storage = None

        # Validate configuration
        if self.auth_mode == "application" and not client_secret:
            raise ValueError("client_secret is required for application mode")

        if self.auth_mode not in ["application", "delegated"]:
            raise ValueError(
                f"Invalid auth_mode: {auth_mode}. Must be 'application' or 'delegated'"
            )

    @property
    def backend_name(self) -> str:
        """Return backend name."""
        return "microsoft"

    @property
    def id_marker_prefix(self) -> str:
        """Return ID marker prefix for orgplan files."""
        return "ms-todo-id"

    @property
    def supports_priority(self) -> bool:
        """Microsoft To Do supports task priority/importance."""
        return True

    def authenticate(self):
        """Authenticate with Microsoft Graph API."""
        if self.auth_mode == "application":
            self._authenticate_application()
        else:
            self._authenticate_delegated()

    def _authenticate_application(self):
        """Authenticate using client credentials (application mode)."""
        authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        app = msal.ConfidentialClientApplication(
            self.client_id,
            authority=authority,
            client_credential=self.client_secret,
        )

        result = app.acquire_token_for_client(scopes=self.SCOPES_APPLICATION)

        if "access_token" in result:
            self.access_token = result["access_token"]
            self.logger.info("Authenticated using application mode (client credentials)")
        else:
            error = result.get("error_description", result.get("error", "Unknown error"))
            raise Exception(f"Authentication failed: {error}")

    def _authenticate_delegated(self):
        """Authenticate using device code flow (delegated mode)."""
        authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        app = msal.PublicClientApplication(
            self.client_id,
            authority=authority,
        )

        # Try to get cached access token
        cached_token = self.token_storage.get_access_token()
        if cached_token:
            self.access_token = cached_token
            self.logger.info("Using cached access token")
            return

        # Try to use refresh token
        refresh_token = self.token_storage.get_refresh_token()
        if refresh_token:
            self.logger.info("Attempting to refresh access token...")
            result = app.acquire_token_by_refresh_token(refresh_token, scopes=self.SCOPES_DELEGATED)

            if "access_token" in result:
                self.access_token = result["access_token"]
                # Save new tokens
                self.token_storage.save_tokens(
                    access_token=result["access_token"],
                    refresh_token=result.get("refresh_token", refresh_token),
                    expires_in=result.get("expires_in"),
                )
                self.logger.info("Successfully refreshed access token")
                return
            else:
                self.logger.warning("Failed to refresh token, interactive login required")

        # Interactive login required
        if not self.allow_prompt:
            raise Exception(
                "Authentication required but interactive prompt is disabled (--no-prompt). "
                "Run sync manually without --no-prompt to authenticate."
            )

        self.logger.info("Starting interactive authentication...")
        self._interactive_login(app)

    def _interactive_login(self, app: msal.PublicClientApplication):
        """Perform interactive login with device code flow."""
        # Initiate device code flow
        flow = app.initiate_device_flow(scopes=self.SCOPES_DELEGATED)

        if "user_code" not in flow:
            raise Exception("Failed to create device flow")

        # Display instructions to user
        print("\n" + "=" * 70)
        print("AUTHENTICATION REQUIRED")
        print("=" * 70)
        print(flow["message"])
        print("=" * 70)
        print("\nWaiting for authentication...")

        # Open browser automatically
        try:
            webbrowser.open(flow["verification_uri"])
            self.logger.info(f"Opened browser to {flow['verification_uri']}")
        except Exception as e:
            self.logger.warning(f"Could not open browser automatically: {e}")

        # Wait for user to authenticate
        result = app.acquire_token_by_device_flow(flow)

        if "access_token" in result:
            self.access_token = result["access_token"]

            # Save tokens for future use
            self.token_storage.save_tokens(
                access_token=result["access_token"],
                refresh_token=result.get("refresh_token"),
                expires_in=result.get("expires_in"),
            )

            print("\n✓ Authentication successful!")
            print("Tokens have been saved for future use.\n")
            self.logger.info("Authenticated using delegated mode (device code flow)")
        else:
            error = result.get("error_description", result.get("error", "Unknown error"))
            raise Exception(f"Authentication failed: {error}")

    def _get_headers(self) -> dict:
        """Get HTTP headers for API requests."""
        if not self.access_token:
            raise Exception("Not authenticated. Call authenticate() first.")

        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def _make_request(
        self, method: str, endpoint: str, json_data: Optional[dict] = None, retry: bool = True
    ) -> dict:
        """Make HTTP request to Graph API with retry logic."""

        def _do_request():
            url = f"{self.GRAPH_API_ENDPOINT}{endpoint}"
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=self._get_headers(),
                    json=json_data,
                    timeout=30,
                )
            except requests.exceptions.Timeout as e:
                raise NetworkError(f"Request timed out: {e}")
            except requests.exceptions.ConnectionError as e:
                raise NetworkError(f"Connection failed: {e}")
            except requests.exceptions.RequestException as e:
                raise NetworkError(f"Network error: {e}")

            if response.status_code >= 500:
                raise APIError(f"Server error {response.status_code}: {response.text}")
            elif response.status_code == 429:
                raise APIError(f"Rate limited: {response.text}")
            elif response.status_code >= 400:
                raise APIError(f"API request failed: {response.status_code} - {response.text}")

            return response.json() if response.content else {}

        if retry:
            return retry_on_failure(_do_request, max_retries=3, logger=self.logger)
        else:
            return _do_request()

    def get_task_lists(self) -> list[dict]:
        """Get all To Do lists."""
        result = self._make_request("GET", "/me/todo/lists")
        return result.get("value", [])

    def get_list_by_name(self, name: str) -> Optional[dict]:
        """Get a To Do list by name."""
        lists = self.get_task_lists()
        for task_list in lists:
            if task_list.get("displayName") == name:
                return task_list
        return None

    def get_tasks(self, list_id: str) -> list[TaskItem]:
        """Get all tasks from a To Do list."""
        result = self._make_request("GET", f"/me/todo/lists/{list_id}/tasks")
        tasks = result.get("value", [])

        return [self._api_to_task_item(task) for task in tasks]

    def create_task(self, list_id: str, task: TaskItem) -> TaskItem:
        """Create a new task in a To Do list."""
        task_data = {
            "title": task.title,
            "importance": task.importance or "normal",
            "status": "completed" if task.is_completed else "notStarted",
        }

        if task.body:
            task_data["body"] = {"contentType": "text", "content": task.body}

        result = self._make_request("POST", f"/me/todo/lists/{list_id}/tasks", task_data)
        return self._api_to_task_item(result)

    def update_task(self, list_id: str, task: TaskItem) -> TaskItem:
        """Update an existing task."""
        task_data = {}

        if task.title is not None:
            task_data["title"] = task.title
        if task.importance is not None:
            task_data["importance"] = task.importance

        # Map TaskItem status to Microsoft To Do status
        if task.status == "completed":
            task_data["status"] = "completed"
        elif task.status == "active":
            task_data["status"] = "notStarted"

        if task.body is not None:
            task_data["body"] = {"contentType": "text", "content": task.body}

        result = self._make_request("PATCH", f"/me/todo/lists/{list_id}/tasks/{task.id}", task_data)
        return self._api_to_task_item(result)

    def delete_task(self, list_id: str, task_id: str) -> None:
        """Delete a task (not currently used, but required by interface)."""
        self._make_request("DELETE", f"/me/todo/lists/{list_id}/tasks/{task_id}")

    def _api_to_task_item(self, api_task: dict) -> TaskItem:
        """Convert Microsoft To Do API task to TaskItem.

        Args:
            api_task: Task dictionary from Graph API

        Returns:
            TaskItem object
        """
        # Map Microsoft status to generic status
        ms_status = api_task.get("status", "notStarted")
        status = "completed" if ms_status == "completed" else "active"

        return TaskItem(
            id=api_task["id"],
            title=api_task.get("title", ""),
            status=status,
            importance=api_task.get("importance", "normal"),
            body=api_task.get("body", {}).get("content"),
            completed_datetime=api_task.get("completedDateTime", {}).get("dateTime"),
        )
