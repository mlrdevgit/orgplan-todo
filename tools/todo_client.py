"""Microsoft To Do client using Graph API."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from pathlib import Path
import logging
import webbrowser

import msal
import requests

from errors import retry_on_failure, APIError, NetworkError
from token_storage import TokenStorage


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
    """Client for Microsoft To Do via Graph API.

    Supports two authentication modes:
    - application: Client credentials flow (requires client secret, admin consent)
    - delegated: Authorization code flow (user login, no admin consent needed)
    """

    GRAPH_API_ENDPOINT = "https://graph.microsoft.com/v1.0"
    SCOPES_APPLICATION = ["https://graph.microsoft.com/.default"]
    # For delegated permissions, offline_access is implicit in device code flow
    # and shouldn't be explicitly requested (it's a reserved scope)
    SCOPES_DELEGATED = ["Tasks.ReadWrite"]

    def __init__(
        self,
        client_id: str,
        tenant_id: str,
        auth_mode: str = "application",
        client_secret: Optional[str] = None,
        token_storage_path: Optional[Path] = None,
        allow_prompt: bool = True,
        logger: Optional[logging.Logger] = None
    ):
        """Initialize To Do client.

        Args:
            client_id: Azure AD application client ID
            tenant_id: Azure AD tenant ID
            auth_mode: Authentication mode ("application" or "delegated")
            client_secret: Client secret (required for application mode)
            token_storage_path: Path to store tokens (for delegated mode)
            allow_prompt: Allow interactive authentication prompt (False for cron)
            logger: Optional logger for retry messages
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
            raise ValueError(f"Invalid auth_mode: {auth_mode}. Must be 'application' or 'delegated'")

    def authenticate(self):
        """Authenticate with Microsoft Graph API.

        Uses the configured authentication mode (application or delegated).

        Raises:
            Exception: If authentication fails
        """
        if self.auth_mode == "application":
            self._authenticate_application()
        else:
            self._authenticate_delegated()

    def _authenticate_application(self):
        """Authenticate using client credentials (application mode).

        Raises:
            Exception: If authentication fails
        """
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
        """Authenticate using authorization code flow (delegated mode).

        Tries to use cached tokens first, then refresh token, and finally
        interactive login if allowed.

        Raises:
            Exception: If authentication fails or interactive login not allowed
        """
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
            result = app.acquire_token_by_refresh_token(
                refresh_token,
                scopes=self.SCOPES_DELEGATED
            )

            if "access_token" in result:
                self.access_token = result["access_token"]
                # Save new tokens
                self.token_storage.save_tokens(
                    access_token=result["access_token"],
                    refresh_token=result.get("refresh_token", refresh_token),
                    expires_in=result.get("expires_in")
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
        """Perform interactive login with authorization code flow.

        Args:
            app: MSAL Public Client Application

        Raises:
            Exception: If authentication fails
        """
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
                expires_in=result.get("expires_in")
            )

            print("\n✓ Authentication successful!")
            print("Tokens have been saved for future use.\n")
            self.logger.info("Authenticated using delegated mode (device code flow)")
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
        self, method: str, endpoint: str, json_data: Optional[dict] = None, retry: bool = True
    ) -> dict:
        """Make HTTP request to Graph API with retry logic.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            endpoint: API endpoint (without base URL)
            json_data: Optional JSON data for request body
            retry: Whether to retry on transient failures

        Returns:
            Response JSON

        Raises:
            APIError: If request fails
            NetworkError: If network operation fails
        """
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
                # Server errors - retryable
                raise APIError(
                    f"Server error {response.status_code}: {response.text}"
                )
            elif response.status_code == 429:
                # Rate limiting - retryable
                raise APIError(f"Rate limited: {response.text}")
            elif response.status_code >= 400:
                # Client errors - not retryable
                raise APIError(
                    f"API request failed: {response.status_code} - {response.text}"
                )

            return response.json() if response.content else {}

        if retry:
            return retry_on_failure(_do_request, max_retries=3, logger=self.logger)
        else:
            return _do_request()

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
