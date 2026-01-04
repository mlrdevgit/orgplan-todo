# Implementation Plan: Google Tasks Backend Support

## Overview

Refactor the orgplan-todo sync tool to support multiple task backends (Microsoft To Do and Google Tasks) with a pluggable architecture. Users can choose their backend via environment variable, with only one backend active per sync operation.

## Goals

1. Support Google Tasks API as an alternative to Microsoft To Do
2. Refactor codebase to use a common backend abstraction layer
3. Maintain backward compatibility with existing Microsoft To Do users
4. Support both backends with the same orgplan file format (with separate ID markers)
5. Use OAuth 2.0 for Google Tasks authentication (personal accounts)

## Architecture Design

### Backend Abstraction Layer

Create a plugin architecture with a common interface for all task backends:

```
tools/
├── backends/
│   ├── __init__.py           # Backend factory and exports
│   ├── base.py               # Abstract base class
│   ├── microsoft_todo.py     # Microsoft To Do implementation
│   └── google_tasks.py       # Google Tasks implementation (NEW)
├── config.py                 # Updated with backend selection
├── sync_engine.py            # Updated to use backend abstraction
├── sync.py                   # Updated to instantiate backends
└── token_storage.py          # Reusable for both backends
```

### Base Backend Interface

**File**: `tools/backends/base.py`

Abstract base class defining the interface all backends must implement:

```python
class TaskBackend(ABC):
    """Abstract base class for task backend implementations."""

    @abstractmethod
    def authenticate(self) -> None:
        """Authenticate with the task service."""
        pass

    @abstractmethod
    def get_task_lists(self) -> list[dict]:
        """Get all task lists."""
        pass

    @abstractmethod
    def get_list_by_name(self, name: str) -> Optional[dict]:
        """Get task list by name."""
        pass

    @abstractmethod
    def get_tasks(self, list_id: str) -> list[TaskItem]:
        """Get all tasks from a list."""
        pass

    @abstractmethod
    def create_task(self, list_id: str, task: TaskItem) -> TaskItem:
        """Create a new task."""
        pass

    @abstractmethod
    def update_task(self, list_id: str, task: TaskItem) -> TaskItem:
        """Update an existing task."""
        pass

    @abstractmethod
    def delete_task(self, list_id: str, task_id: str) -> None:
        """Delete a task."""
        pass

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Return the backend name (e.g., 'microsoft', 'google')."""
        pass

    @property
    @abstractmethod
    def id_marker_prefix(self) -> str:
        """Return the ID marker prefix for orgplan files (e.g., 'ms-todo-id', 'google-tasks-id')."""
        pass
```

### Common Task Data Model

**File**: `tools/backends/base.py`

Unified task representation that works across backends:

```python
@dataclass
class TaskItem:
    """Backend-agnostic task representation."""

    id: str
    title: str
    status: str  # "active" or "completed"
    body: Optional[str] = None
    importance: Optional[str] = None  # "low", "normal", "high" (None for Google Tasks)
    completed_datetime: Optional[str] = None
    backend_specific: dict = None  # For backend-specific fields

    @property
    def is_completed(self) -> bool:
        return self.status == "completed"
```

## Implementation Phases

### Phase 1: Refactor Existing Code for Backend Abstraction

**Objective**: Extract Microsoft To Do implementation into the new architecture without breaking existing functionality.

#### Step 1.1: Create Backend Infrastructure

1. Create `tools/backends/` directory
2. Create `tools/backends/__init__.py` with backend factory
3. Create `tools/backends/base.py` with:
   - `TaskBackend` abstract base class
   - `TaskItem` dataclass
   - Helper utilities

#### Step 1.2: Refactor Microsoft To Do Client

1. Create `tools/backends/microsoft_todo.py`
2. Move code from `tools/todo_client.py` to new file
3. Implement `MicrosoftTodoBackend(TaskBackend)`:
   - Convert `TodoTask` to use `TaskItem`
   - Implement all abstract methods
   - Set `backend_name = "microsoft"`
   - Set `id_marker_prefix = "ms-todo-id"`
   - Keep existing authentication logic (application + delegated modes)
4. Update imports in `tools/todo_client.py` to re-export for backward compatibility

#### Step 1.3: Update Sync Engine

1. Modify `tools/sync_engine.py`:
   - Change `TodoClient` parameter to `TaskBackend`
   - Use `backend.id_marker_prefix` instead of hardcoded "ms-todo-id"
   - Ensure all task operations use backend abstraction
   - Update task matching logic to be backend-agnostic

#### Step 1.4: Update Configuration

1. Modify `tools/config.py`:
   - Add `backend` parameter (default: "microsoft")
   - Add `TASK_BACKEND` environment variable
   - Validate backend is one of ["microsoft", "google"]
   - Keep all Microsoft-specific config for backward compatibility

2. Update `.env.example`:
   ```env
   # Task Backend Selection
   TASK_BACKEND=microsoft  # Options: microsoft, google

   # Microsoft To Do Configuration (if TASK_BACKEND=microsoft)
   AUTH_MODE=application
   MS_CLIENT_ID=...
   # ... rest of MS config

   # Google Tasks Configuration (if TASK_BACKEND=google)
   GOOGLE_CLIENT_ID=...
   GOOGLE_CLIENT_SECRET=...
   ```

#### Step 1.5: Update Main Script

1. Modify `tools/sync.py`:
   - Add `--backend` CLI argument (optional, defaults to env var)
   - Instantiate correct backend based on configuration
   - Pass backend instance to sync engine
   - Update help text to mention backend selection

#### Step 1.6: Testing

1. Test that Microsoft To Do still works with refactored code
2. Verify backward compatibility (existing .env files work)
3. Run existing test files: `test_bidirectional.py`, `test_phase3.py`, `test_phase4.py`

### Phase 2: Implement Google Tasks Backend

**Objective**: Add Google Tasks support using the new backend architecture.

#### Step 2.1: Google Tasks API Setup Documentation

Create `docs/GOOGLE_TASKS_SETUP.md`:

1. **Prerequisites**
   - Google account
   - Access to Google Cloud Console
   - Enable Google Tasks API

2. **Create Google Cloud Project**
   - Go to https://console.cloud.google.com
   - Create new project
   - Enable Google Tasks API

3. **Configure OAuth Consent Screen**
   - User type: External (for personal accounts)
   - Add app name, support email
   - Scopes: https://www.googleapis.com/auth/tasks

4. **Create OAuth 2.0 Credentials**
   - Application type: Desktop app
   - Download credentials JSON
   - Extract client_id and client_secret

5. **Configure Application**
   - Add credentials to .env file
   - Set TASK_BACKEND=google

#### Step 2.2: Install Dependencies

Update `requirements.txt`:
```
google-auth-oauthlib>=1.0.0
google-auth-httplib2>=0.1.0
google-api-python-client>=2.0.0
```

#### Step 2.3: Implement Google Tasks Client

Create `tools/backends/google_tasks.py`:

1. **GoogleTasksBackend class**
   - Inherit from `TaskBackend`
   - OAuth 2.0 authentication using `google-auth-oauthlib`
   - Token storage in `.tokens/google_tokens.json`
   - Auto browser opening for auth flow

2. **Authentication Flow**
   ```python
   def authenticate(self):
       # Check for cached tokens
       # If expired, use refresh token
       # If no tokens, start OAuth flow
       # Save tokens to .tokens/google_tokens.json
   ```

3. **API Methods Implementation**:
   - `get_task_lists()` - Uses `tasklists().list()`
   - `get_list_by_name()` - Find list by title
   - `get_tasks()` - Uses `tasks().list()`
   - `create_task()` - Uses `tasks().insert()`
   - `update_task()` - Uses `tasks().update()`
   - `delete_task()` - Uses `tasks().delete()`

4. **Field Mapping**:
   - Google Tasks → TaskItem:
     ```python
     TaskItem(
         id=gtask['id'],
         title=gtask['title'],
         status='completed' if gtask['status'] == 'completed' else 'active',
         body=gtask.get('notes'),
         importance=None,  # Google Tasks doesn't support priority
         completed_datetime=gtask.get('completed'),
     )
     ```

   - TaskItem → Google Tasks:
     ```python
     {
         'title': task.title,
         'status': 'completed' if task.is_completed else 'needsAction',
         'notes': task.body or '',
     }
     ```
     Note: Ignore `task.importance` - not supported by Google Tasks

5. **Properties**:
   - `backend_name = "google"`
   - `id_marker_prefix = "google-tasks-id"`

6. **Error Handling**:
   - Wrap API calls with retry logic (reuse `@retry_on_failure` decorator)
   - Handle rate limits (exponential backoff)
   - Handle authentication errors

#### Step 2.4: Backend Factory

Update `tools/backends/__init__.py`:

```python
def create_backend(backend_type: str, config: Config, logger) -> TaskBackend:
    """Factory function to create appropriate backend."""
    if backend_type == "microsoft":
        from .microsoft_todo import MicrosoftTodoBackend
        return MicrosoftTodoBackend(
            client_id=config.client_id,
            tenant_id=config.tenant_id,
            auth_mode=config.auth_mode,
            client_secret=config.client_secret,
            token_storage_path=config.token_storage_path,
            allow_prompt=config.allow_prompt,
            logger=logger,
        )
    elif backend_type == "google":
        from .google_tasks import GoogleTasksBackend
        return GoogleTasksBackend(
            client_id=config.google_client_id,
            client_secret=config.google_client_secret,
            token_storage_path=config.token_storage_path,
            allow_prompt=config.allow_prompt,
            logger=logger,
        )
    else:
        raise ValueError(f"Unknown backend type: {backend_type}")
```

#### Step 2.5: Update Configuration for Google Tasks

Update `tools/config.py`:

1. Add Google Tasks specific parameters:
   - `google_client_id`
   - `google_client_secret`
   - `google_task_list_name` (optional, defaults to primary)

2. Update `load_config_from_env()`:
   ```python
   return {
       # ... existing fields
       "backend": os.getenv("TASK_BACKEND", "microsoft"),
       "google_client_id": os.getenv("GOOGLE_CLIENT_ID"),
       "google_client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
       "google_task_list_name": os.getenv("GOOGLE_TASK_LIST_NAME"),
   }
   ```

3. Update validation:
   - If backend == "microsoft": validate MS_CLIENT_ID, MS_TENANT_ID, etc.
   - If backend == "google": validate GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
   - Make task_list_name backend-aware (todo_list_name for MS, google_task_list_name for Google)

#### Step 2.6: Update Main Script for Backend Selection

Update `tools/sync.py`:

1. Add `--backend` CLI argument:
   ```python
   parser.add_argument(
       "--backend",
       type=str,
       choices=["microsoft", "google"],
       help="Task backend to use (default: from TASK_BACKEND env var or 'microsoft')",
   )
   ```

2. Update task list argument to be backend-aware:
   ```python
   parser.add_argument(
       "--task-list",
       type=str,
       help="Name of the task list to sync with (for Microsoft: To Do list, for Google: task list)",
   )
   ```

3. Instantiate backend using factory:
   ```python
   from backends import create_backend

   backend = create_backend(
       backend_type=config.backend,
       config=config,
       logger=logger,
   )
   backend.authenticate()
   ```

4. Get task list (backend-agnostic):
   ```python
   logger.info(f"Finding task list '{config.task_list_name}'...")
   task_list = backend.get_list_by_name(config.task_list_name)
   if not task_list:
       # For Google Tasks, use primary list if name not found
       if config.backend == "google" and not config.task_list_name:
           task_lists = backend.get_task_lists()
           task_list = next((lst for lst in task_lists if lst.get('title') == '@default'), task_lists[0])
       else:
           logger.error(f"Task list '{config.task_list_name}' not found")
           # ... show available lists
   ```

### Phase 3: Update Orgplan Parser for Multiple ID Markers

**Objective**: Support both `ms-todo-id` and `google-tasks-id` markers in orgplan files.

#### Step 3.1: Update Parser

Modify `tools/orgplan_parser.py`:

1. Update ID extraction to support multiple marker types:
   ```python
   def extract_backend_id(self, detail_text: str, backend_prefix: str) -> Optional[str]:
       """Extract backend-specific ID from detail section.

       Args:
           detail_text: The detail section text
           backend_prefix: e.g., 'ms-todo-id' or 'google-tasks-id'
       """
       pattern = rf'{backend_prefix}:\s*([a-zA-Z0-9\-_]+)'
       match = re.search(pattern, detail_text)
       return match.group(1) if match else None
   ```

2. Update task matching in sync engine to use backend-specific prefix:
   ```python
   # In sync_engine.py
   backend_id = orgplan_parser.extract_backend_id(
       task.detail,
       self.backend.id_marker_prefix
   )
   ```

3. When creating/updating tasks, use correct marker:
   ```python
   # Add ID marker to detail section
   detail += f"\n{self.backend.id_marker_prefix}: {task_id}"
   ```

#### Step 3.2: Handle Mixed Markers

Decide on behavior when orgplan file has markers for different backends:

1. **Ignore markers from other backends** - Treat tasks without current backend's marker as new tasks
2. **Warning message** - Log when tasks have markers for different backend
3. **No automatic migration** - Users switching backends will get duplicate tasks (expected behavior per requirements)

### Phase 4: Documentation

**Objective**: Provide comprehensive documentation for Google Tasks setup and multi-backend usage.

#### Step 4.1: Google Tasks Setup Guide

Create `docs/GOOGLE_TASKS_SETUP.md`:
- Google Cloud Console setup
- OAuth 2.0 configuration
- Enabling Google Tasks API
- Creating credentials
- Configuration examples
- Testing authentication

#### Step 4.2: Update Main README

Update `README.md`:

1. **Features section**:
   - Add "Multiple backend support (Microsoft To Do, Google Tasks)"
   - Clarify backend selection

2. **Configuration section**:
   - Add backend selection documentation
   - Show examples for both backends
   - Update configuration table with backend-specific fields

3. **Usage examples**:
   ```bash
   # Microsoft To Do (default)
   python tools/sync.py --todo-list "Orgplan 2025"

   # Google Tasks
   python tools/sync.py --backend google --task-list "My Tasks"

   # Google Tasks with primary list (default)
   TASK_BACKEND=google python tools/sync.py
   ```

#### Step 4.3: Update Troubleshooting Guide

Update `docs/TROUBLESHOOTING.md`:

1. Add "Backend Selection Issues" section
2. Add "Google Tasks Authentication Issues" section:
   - OAuth consent screen errors
   - Invalid client errors
   - Token refresh failures
   - API not enabled errors

3. Add "Switching Backends" section:
   - Expected behavior (duplicate tasks)
   - ID marker differences
   - No automatic migration

#### Step 4.4: Architecture Documentation

Create `docs/ARCHITECTURE.md`:
- Backend abstraction design
- Adding new backends (for future contributors)
- Task data model
- Authentication flows
- Sync engine workflow

### Phase 5: Testing and Validation

**Objective**: Ensure both backends work correctly and independently.

#### Step 5.1: Unit Tests

Create `test_google_tasks.py`:
- Test Google Tasks authentication
- Test task list operations
- Test CRUD operations
- Test field mapping
- Test error handling

#### Step 5.2: Integration Tests

Create `test_multi_backend.py`:
- Test backend factory
- Test configuration with different backends
- Test sync engine with both backends
- Test ID marker handling

#### Step 5.3: Manual Testing Checklist

1. **Microsoft To Do** (ensure no regression):
   - [ ] Application mode authentication works
   - [ ] Delegated mode authentication works
   - [ ] Bidirectional sync works
   - [ ] Priority mapping works
   - [ ] Detail section sync works

2. **Google Tasks** (new functionality):
   - [ ] OAuth 2.0 authentication works
   - [ ] Token refresh works
   - [ ] Task list discovery works
   - [ ] Primary list default works
   - [ ] Bidirectional sync works
   - [ ] Priority ignored correctly
   - [ ] Detail section sync works

3. **Backend Selection**:
   - [ ] TASK_BACKEND env var works
   - [ ] --backend CLI flag works
   - [ ] Configuration validation works
   - [ ] Error messages are clear

4. **Orgplan File Handling**:
   - [ ] ms-todo-id markers work
   - [ ] google-tasks-id markers work
   - [ ] Mixed markers handled correctly
   - [ ] Switching backends creates duplicates (expected)

### Phase 6: Polish and Release

**Objective**: Final cleanup and preparation for use.

#### Step 6.1: Code Cleanup

1. Remove deprecated code
2. Add type hints throughout
3. Add docstrings for all public methods
4. Run linters (pylint, black, mypy)

#### Step 6.2: Update .env.example

Create comprehensive `.env.example` with both backends:

```env
################################################################################
# Task Backend Selection
################################################################################
# Choose which task management service to sync with
# Options: microsoft, google
TASK_BACKEND=microsoft

################################################################################
# Microsoft To Do Configuration (if TASK_BACKEND=microsoft)
################################################################################
# Authentication mode: application (client credentials) or delegated (user login)
AUTH_MODE=application

# Required for Microsoft To Do
MS_CLIENT_ID=your-application-client-id
MS_TENANT_ID=your-directory-tenant-id

# Required only for application mode
MS_CLIENT_SECRET=your-client-secret

# Microsoft To Do list name
TODO_LIST_NAME=Orgplan 2025

################################################################################
# Google Tasks Configuration (if TASK_BACKEND=google)
################################################################################
# OAuth 2.0 credentials from Google Cloud Console
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Google task list name (leave empty for primary list)
GOOGLE_TASK_LIST_NAME=

################################################################################
# Common Configuration
################################################################################
# Orgplan directory (default: current directory)
ORGPLAN_DIR=.

# Optional: Override current month (format: YYYY-MM)
# SYNC_MONTH=2025-12

# Optional: Token storage path
# TOKEN_STORAGE_PATH=.tokens/

# Optional: Log file path
# LOG_FILE=sync.log
```

#### Step 6.3: Update README with Feature Comparison

Add comparison table to README.md:

| Feature | Microsoft To Do | Google Tasks |
|---------|----------------|--------------|
| Authentication | Application + Delegated | OAuth 2.0 |
| Priority/Importance | ✅ Supported (#p1-#p3) | ❌ Not supported |
| Task Status | ✅ Supported | ✅ Supported |
| Task Body/Notes | ✅ Supported | ✅ Supported |
| Detail Section Sync | ✅ Supported | ✅ Supported |
| Admin Consent Required | Application mode only | ❌ No |
| Personal Accounts | ✅ Supported | ✅ Supported |

#### Step 6.4: Migration Guide

Create `docs/BACKEND_MIGRATION.md`:
- How to switch from Microsoft To Do to Google Tasks
- What happens to existing tasks
- How to clean up duplicate tasks
- ID marker explanation

## Success Criteria

1. ✅ Users can choose between Microsoft To Do and Google Tasks via `TASK_BACKEND` env var
2. ✅ Google Tasks authentication works with personal Google accounts (OAuth 2.0)
3. ✅ Both backends support full bidirectional sync
4. ✅ Priority is ignored for Google Tasks (no errors, clean handling)
5. ✅ Orgplan files support both `ms-todo-id` and `google-tasks-id` markers
6. ✅ Existing Microsoft To Do users experience no breaking changes
7. ✅ Code is well-organized with clear separation between backends
8. ✅ Comprehensive documentation for both backends
9. ✅ All existing tests pass with refactored code
10. ✅ New tests cover Google Tasks functionality

## Non-Goals

- ❌ Simultaneous sync to multiple backends
- ❌ Automatic migration between backends
- ❌ Support for service accounts (G Suite/Workspace)
- ❌ Priority emulation in Google Tasks (e.g., in notes field)
- ❌ Backward compatibility with old ID markers when switching backends

## File Structure Summary

```
orgplan-todo/
├── tools/
│   ├── backends/
│   │   ├── __init__.py              # Backend factory
│   │   ├── base.py                  # TaskBackend abstract class, TaskItem dataclass
│   │   ├── microsoft_todo.py        # Microsoft To Do implementation (refactored)
│   │   └── google_tasks.py          # Google Tasks implementation (NEW)
│   ├── config.py                    # Updated with backend selection
│   ├── sync_engine.py               # Updated to use TaskBackend abstraction
│   ├── sync.py                      # Updated with --backend flag
│   ├── orgplan_parser.py            # Updated for multiple ID markers
│   ├── token_storage.py             # Shared by both backends
│   ├── errors.py                    # Existing error handling
│   └── locking.py                   # Existing file locking
├── docs/
│   ├── GRAPH_API_SETUP.md          # Existing MS To Do setup
│   ├── GOOGLE_TASKS_SETUP.md       # NEW: Google Tasks setup guide
│   ├── ARCHITECTURE.md              # NEW: Multi-backend architecture
│   ├── BACKEND_MIGRATION.md         # NEW: Switching backends guide
│   ├── TROUBLESHOOTING.md           # Updated with Google Tasks issues
│   └── WORKFLOWS.md                 # Updated with backend examples
├── tests/
│   ├── test_bidirectional.py       # Existing (update for backends)
│   ├── test_phase3.py              # Existing
│   ├── test_phase4.py              # Existing
│   ├── test_google_tasks.py        # NEW: Google Tasks tests
│   └── test_multi_backend.py       # NEW: Backend abstraction tests
├── .env.example                     # Updated with both backends
├── requirements.txt                 # Updated with google-* packages
└── README.md                        # Updated with backend info
```

## Timeline Estimate

- **Phase 1** (Refactoring): 3-4 hours
- **Phase 2** (Google Tasks): 4-5 hours
- **Phase 3** (Parser updates): 1-2 hours
- **Phase 4** (Documentation): 2-3 hours
- **Phase 5** (Testing): 2-3 hours
- **Phase 6** (Polish): 1-2 hours

**Total**: ~13-19 hours of implementation work

## Dependencies

New Python packages required:
- `google-auth-oauthlib>=1.0.0` - OAuth 2.0 flow
- `google-auth-httplib2>=0.1.0` - HTTP library for Google APIs
- `google-api-python-client>=2.0.0` - Google Tasks API client

External dependencies:
- Google Cloud Console account (free)
- Google Tasks API enabled
- OAuth 2.0 credentials configured

## Risk Assessment

**Low Risk**:
- Backend abstraction (well-defined interface)
- Google Tasks API (mature, stable)
- Token storage (reuse existing pattern)

**Medium Risk**:
- OAuth 2.0 flow complexity (first-time setup friction)
- Field mapping differences (priority handling)
- Testing coverage (need comprehensive tests)

**Mitigation**:
- Detailed Google Tasks setup documentation
- Clear error messages for missing priority
- Extensive integration testing
- Gradual rollout (test with small orgplan files first)
