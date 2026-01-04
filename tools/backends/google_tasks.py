"""Google Tasks backend implementation."""

import json
import logging
from pathlib import Path
from typing import Optional
import os

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .base import TaskBackend, TaskItem
from errors import retry_on_failure, APIError, NetworkError


class GoogleTasksBackend(TaskBackend):
    """Google Tasks backend implementation.

    Uses OAuth 2.0 for authentication with user consent.
    """

    # OAuth 2.0 scopes
    SCOPES = ["https://www.googleapis.com/auth/tasks"]

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        token_storage_path: Optional[Path] = None,
        allow_prompt: bool = True,
        logger: Optional[logging.Logger] = None,
    ):
        """Initialize Google Tasks backend.

        Args:
            client_id: Google OAuth client ID
            client_secret: Google OAuth client secret
            token_storage_path: Path to store tokens (default: .tokens/)
            allow_prompt: Allow interactive authentication prompt (False for cron)
            logger: Optional logger for messages
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.allow_prompt = allow_prompt
        self.logger = logger or logging.getLogger(__name__)

        # Token storage
        if token_storage_path:
            self.token_path = Path(token_storage_path) / "google_tokens.json"
        else:
            self.token_path = Path.home() / ".tokens" / "google_tokens.json"

        self.credentials = None
        self.service = None

    @property
    def backend_name(self) -> str:
        """Return backend name."""
        return "google"

    @property
    def id_marker_prefix(self) -> str:
        """Return ID marker prefix for orgplan files."""
        return "google-tasks-id"

    def authenticate(self):
        """Authenticate with Google Tasks API using OAuth 2.0."""
        self.credentials = self._load_credentials()

        if not self.credentials or not self.credentials.valid:
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                # Try to refresh the token
                try:
                    self.logger.info("Attempting to refresh access token...")
                    self.credentials.refresh(Request())
                    self._save_credentials()
                    self.logger.info("Successfully refreshed access token")
                except Exception as e:
                    self.logger.warning(f"Failed to refresh token: {e}")
                    self.credentials = None

            if not self.credentials:
                # Interactive login required
                if not self.allow_prompt:
                    raise Exception(
                        "Authentication required but interactive prompt is disabled (--no-prompt). "
                        "Run sync manually without --no-prompt to authenticate."
                    )

                self.logger.info("Starting interactive authentication...")
                self._interactive_login()

        # Build the service
        self.service = build("tasks", "v1", credentials=self.credentials)
        self.logger.info("Authenticated with Google Tasks API")

    def _load_credentials(self) -> Optional[Credentials]:
        """Load credentials from token file.

        Returns:
            Credentials object or None if file doesn't exist
        """
        if not self.token_path.exists():
            return None

        try:
            with open(self.token_path, "r") as f:
                token_data = json.load(f)

            return Credentials(
                token=token_data.get("token"),
                refresh_token=token_data.get("refresh_token"),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=self.SCOPES,
            )
        except Exception as e:
            self.logger.warning(f"Failed to load credentials: {e}")
            return None

    def _save_credentials(self):
        """Save credentials to token file."""
        # Ensure directory exists
        self.token_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

        token_data = {
            "token": self.credentials.token,
            "refresh_token": self.credentials.refresh_token,
            "token_uri": self.credentials.token_uri,
            "client_id": self.credentials.client_id,
            "client_secret": self.credentials.client_secret,
            "scopes": self.credentials.scopes,
        }

        with open(self.token_path, "w") as f:
            json.dump(token_data, f, indent=2)

        # Set secure permissions
        os.chmod(self.token_path, 0o600)
        self.logger.info(f"Saved credentials to {self.token_path}")

    def _interactive_login(self):
        """Perform interactive OAuth 2.0 login."""
        # Create OAuth flow
        client_config = {
            "installed": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uris": ["http://localhost", "urn:ietf:wg:oauth:2.0:oob"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }

        flow = InstalledAppFlow.from_client_config(client_config, scopes=self.SCOPES)

        # Display authentication instructions
        print("\n" + "=" * 70)
        print("GOOGLE AUTHENTICATION REQUIRED")
        print("=" * 70)
        print("A browser window will open for you to sign in with Google.")
        print("Grant access to Google Tasks when prompted.")
        print("=" * 70)
        print("\nWaiting for authentication...")

        # Run the local server flow
        try:
            self.credentials = flow.run_local_server(port=0)
            self._save_credentials()

            print("\n✓ Authentication successful!")
            print("Tokens have been saved for future use.\n")
            self.logger.info("Authenticated using OAuth 2.0 flow")
        except Exception as e:
            raise Exception(f"Authentication failed: {e}")

    def _handle_api_error(self, error: HttpError) -> Exception:
        """Convert Google API error to our error types.

        Args:
            error: HttpError from Google API

        Returns:
            APIError or NetworkError
        """
        if error.resp.status >= 500:
            return APIError(f"Server error {error.resp.status}: {error.content}")
        elif error.resp.status == 429:
            return APIError(f"Rate limited: {error.content}")
        else:
            return APIError(f"API request failed: {error.resp.status} - {error.content}")

    def get_task_lists(self) -> list[dict]:
        """Get all task lists."""

        def _get_lists():
            try:
                results = self.service.tasklists().list().execute()
                return results.get("items", [])
            except HttpError as e:
                raise self._handle_api_error(e)

        return retry_on_failure(_get_lists, max_retries=3, logger=self.logger)

    def get_list_by_name(self, name: str) -> Optional[dict]:
        """Get a task list by name (title).

        Args:
            name: The title of the task list

        Returns:
            Task list dictionary if found, None otherwise
        """
        lists = self.get_task_lists()
        for task_list in lists:
            if task_list.get("title") == name:
                return task_list
        return None

    def get_tasks(self, list_id: str) -> list[TaskItem]:
        """Get all tasks from a task list.

        Args:
            list_id: The ID of the task list

        Returns:
            List of TaskItem objects
        """

        def _get_tasks():
            try:
                results = (
                    self.service.tasks()
                    .list(tasklist=list_id, showCompleted=True, showHidden=True)
                    .execute()
                )
                tasks = results.get("items", [])
                return [self._api_to_task_item(task) for task in tasks]
            except HttpError as e:
                raise self._handle_api_error(e)

        return retry_on_failure(_get_tasks, max_retries=3, logger=self.logger)

    def create_task(self, list_id: str, task: TaskItem) -> TaskItem:
        """Create a new task.

        Args:
            list_id: The ID of the task list
            task: TaskItem to create

        Returns:
            Created TaskItem with backend-assigned ID
        """

        def _create_task():
            try:
                # Build Google Tasks task object
                task_body = {
                    "title": task.title,
                    "status": "completed" if task.status == "completed" else "needsAction",
                }

                if task.body:
                    task_body["notes"] = task.body

                result = self.service.tasks().insert(tasklist=list_id, body=task_body).execute()

                return self._api_to_task_item(result)
            except HttpError as e:
                raise self._handle_api_error(e)

        return retry_on_failure(_create_task, max_retries=3, logger=self.logger)

    def update_task(self, list_id: str, task: TaskItem) -> TaskItem:
        """Update an existing task.

        Args:
            list_id: The ID of the task list
            task: TaskItem with updated fields

        Returns:
            Updated TaskItem
        """

        def _update_task():
            try:
                # Build Google Tasks task object
                task_body = {
                    "id": task.id,
                    "title": task.title,
                    "status": "completed" if task.status == "completed" else "needsAction",
                }

                if task.body is not None:
                    task_body["notes"] = task.body

                result = (
                    self.service.tasks()
                    .update(tasklist=list_id, task=task.id, body=task_body)
                    .execute()
                )

                return self._api_to_task_item(result)
            except HttpError as e:
                raise self._handle_api_error(e)

        return retry_on_failure(_update_task, max_retries=3, logger=self.logger)

    def delete_task(self, list_id: str, task_id: str) -> None:
        """Delete a task.

        Args:
            list_id: The ID of the task list
            task_id: The ID of the task to delete
        """

        def _delete_task():
            try:
                self.service.tasks().delete(tasklist=list_id, task=task_id).execute()
            except HttpError as e:
                raise self._handle_api_error(e)

        retry_on_failure(_delete_task, max_retries=3, logger=self.logger)

    def _api_to_task_item(self, api_task: dict) -> TaskItem:
        """Convert Google Tasks API task to TaskItem.

        Args:
            api_task: Task dictionary from Google Tasks API

        Returns:
            TaskItem object
        """
        # Map Google status to generic status
        google_status = api_task.get("status", "needsAction")
        status = "completed" if google_status == "completed" else "active"

        # Google Tasks doesn't have importance/priority
        return TaskItem(
            id=api_task["id"],
            title=api_task.get("title", ""),
            status=status,
            importance=None,  # Google Tasks doesn't support priority
            body=api_task.get("notes"),
            completed_datetime=api_task.get("completed"),
        )
