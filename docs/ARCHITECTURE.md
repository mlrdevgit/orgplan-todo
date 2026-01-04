# Architecture Documentation

This document describes the technical architecture of orgplan-todo, focusing on the multi-backend design.

## Table of Contents

- [System Overview](#system-overview)
- [Architecture Diagram](#architecture-diagram)
- [Core Components](#core-components)
- [Backend Abstraction](#backend-abstraction)
- [Data Flow](#data-flow)
- [Error Handling](#error-handling)
- [Extension Points](#extension-points)

## System Overview

orgplan-todo is a bidirectional task synchronization tool that connects orgplan markdown files with cloud task management services.

### Design Principles

1. **Backend Agnostic**: Core sync engine doesn't know about specific backends
2. **Pluggable Architecture**: Easy to add new backends
3. **Data Integrity**: Orgplan is the source of truth
4. **Idempotent Operations**: Safe to run multiple times
5. **Error Resilience**: Retry logic and graceful degradation

### Technology Stack

- **Language**: Python 3.8+
- **Microsoft Backend**: MSAL (Microsoft Authentication Library)
- **Google Backend**: google-api-python-client, google-auth-oauthlib
- **Configuration**: python-dotenv
- **File Format**: Markdown with custom markers

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         User Layer                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Command Line │  │  Cron Jobs   │  │ Custom Scripts│     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
└─────────┼──────────────────┼──────────────────┼─────────────┘
          │                  │                  │
          └──────────────────┴──────────────────┘
                             │
┌────────────────────────────┼─────────────────────────────────┐
│                      Core Layer                               │
│                            │                                  │
│  ┌─────────────────────────▼──────────────────────────────┐  │
│  │                    sync.py (Main)                       │  │
│  │  - Argument parsing                                     │  │
│  │  - Configuration loading                                │  │
│  │  - Orchestration                                        │  │
│  └─────────────────────────┬──────────────────────────────┘  │
│                            │                                  │
│  ┌─────────────────────────▼──────────────────────────────┐  │
│  │                  SyncEngine                             │  │
│  │  - Bidirectional sync logic                            │  │
│  │  - Task matching (ID + title fallback)                 │  │
│  │  - Conflict detection                                   │  │
│  │  - Statistics tracking                                  │  │
│  └───────┬────────────────────────────────────┬────────────┘  │
│          │                                    │               │
│  ┌───────▼────────┐                  ┌────────▼───────────┐  │
│  │ OrgplanParser  │                  │ Backend Factory    │  │
│  │ - Parse markdown│                  │ - create_backend() │  │
│  │ - Extract tasks │                  └────────┬───────────┘  │
│  │ - Update files  │                           │              │
│  │ - ID markers    │                           │              │
│  └────────────────┘                            │              │
└────────────────────────────────────────────────┼──────────────┘
                                                 │
┌────────────────────────────────────────────────┼──────────────┐
│                   Backend Abstraction Layer                    │
│                                                │               │
│  ┌─────────────────────────────────────────────▼────────────┐ │
│  │              TaskBackend (Abstract Base)                 │ │
│  │  Properties:                                             │ │
│  │    - backend_name: str                                   │ │
│  │    - id_marker_prefix: str                               │ │
│  │  Methods:                                                │ │
│  │    - authenticate()                                      │ │
│  │    - get_task_lists() -> list[dict]                      │ │
│  │    - get_list_by_name(name) -> dict                      │ │
│  │    - get_tasks(list_id) -> list[TaskItem]                │ │
│  │    - create_task(list_id, task) -> TaskItem              │ │
│  │    - update_task(list_id, task) -> TaskItem              │ │
│  │    - delete_task(list_id, task_id)                       │ │
│  └──────────────────┬────────────────────┬──────────────────┘ │
│                     │                    │                    │
│  ┌──────────────────▼─────┐   ┌──────────▼──────────────┐    │
│  │  MicrosoftTodoBackend  │   │  GoogleTasksBackend     │    │
│  │  - MSAL authentication │   │  - OAuth 2.0 auth       │    │
│  │  - Graph API calls     │   │  - Tasks API calls      │    │
│  │  - Priority mapping    │   │  - No priority support  │    │
│  │  - ms-todo-id marker   │   │  - google-tasks-id      │    │
│  └────────────────────────┘   └─────────────────────────┘    │
└────────────────────────────────────────────────────────────────┘
                     │                    │
┌────────────────────┼────────────────────┼────────────────────┐
│                External Services Layer                        │
│  ┌─────────────────▼─────────┐   ┌──────▼──────────────────┐ │
│  │  Microsoft Graph API      │   │  Google Tasks API       │ │
│  │  - Task lists             │   │  - Task lists           │ │
│  │  - Tasks                  │   │  - Tasks                │ │
│  │  - Authentication         │   │  - Authentication       │ │
│  └───────────────────────────┘   └─────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Configuration (config.py)

**Purpose**: Centralized configuration management

**Key Classes**:
```python
class Config:
    backend: str              # "microsoft" or "google"
    # Microsoft-specific
    client_id: str
    tenant_id: str
    auth_mode: str
    client_secret: Optional[str]
    # Google-specific
    google_client_id: str
    google_client_secret: str
    # Common
    task_list_name: str
    orgplan_dir: Path
    month: str
```

**Configuration Sources** (priority order):
1. Command-line arguments
2. Environment variables
3. `.env` file
4. Defaults

### 2. OrgplanParser (orgplan_parser.py)

**Purpose**: Parse and update orgplan markdown files

**Key Classes**:
```python
@dataclass
class OrgplanTask:
    title: str
    status: Optional[str]        # "DONE", "PENDING", "DELEGATED"
    priority: Optional[str]      # "p1", "p2", "p3"
    time_estimate: Optional[str] # "1h", "2h", "1d"
    blocked: bool
    detail_section: Optional[str]
    # Backend ID markers
    ms_todo_id: Optional[str]
    google_tasks_id: Optional[str]
```

**Key Methods**:
- `load()`: Read and parse markdown file
- `extract_tasks()`: Parse TODO List section
- `validate()`: Check file format
- `add_detail_section()`: Add task details with ID markers
- `save()`: Write changes back to file

**ID Marker Patterns**:
```python
MS_TODO_ID_PATTERN = r"<!--\s*ms-todo-id:\s*([^\s]+)\s*-->"
GOOGLE_TASKS_ID_PATTERN = r"<!--\s*google-tasks-id:\s*([^\s]+)\s*-->"
```

### 3. SyncEngine (sync_engine.py)

**Purpose**: Bidirectional synchronization logic

**Key Methods**:
```python
def sync_bidirectional() -> dict:
    """Perform two-way sync."""
    # Phase 1: Orgplan → Backend
    # Phase 2: Backend → Orgplan
    # Return statistics

def _find_matching_todo_task(orgplan_task, ...):
    """Match task using ID marker or title."""
    # 1. Try backend-specific ID marker
    # 2. Fall back to exact title match
```

**Backend Agnostic Design**:
- Uses `backend.id_marker_prefix` dynamically
- Converts prefix to Python attribute name: `ms-todo-id` → `ms_todo_id`
- No hardcoded backend logic

### 4. Locking (locking.py)

**Purpose**: Prevent concurrent sync operations

**Features**:
- File-based locking
- Stale lock detection (>1 hour)
- Automatic cleanup
- Process ID tracking

## Backend Abstraction

### Base Classes

#### TaskBackend (Abstract)

```python
class TaskBackend(ABC):
    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Return backend identifier (e.g., 'microsoft', 'google')."""
        pass

    @property
    @abstractmethod
    def id_marker_prefix(self) -> str:
        """Return ID marker prefix (e.g., 'ms-todo-id', 'google-tasks-id')."""
        pass

    @abstractmethod
    def authenticate(self) -> None:
        """Authenticate with the backend service."""
        pass
```

#### TaskItem (Data Class)

```python
@dataclass
class TaskItem:
    id: str                              # Backend-assigned ID
    title: str                           # Task title
    status: str                          # "active" or "completed"
    body: Optional[str] = None           # Task notes/details
    importance: Optional[str] = None     # "high", "normal", "low", or None
    completed_datetime: Optional[str] = None
    backend_specific: dict = field(default_factory=dict)
```

**Design Notes**:
- Generic `status` field: "active" or "completed" (not backend-specific)
- `importance` can be None (for Google Tasks)
- `backend_specific` for future extensions

### Backend Implementations

#### MicrosoftTodoBackend

**Authentication**:
- **Application Mode**: Client credentials flow (MSAL)
- **Delegated Mode**: Device code flow (MSAL)

**Features**:
- Full priority support
- Task body/notes
- Token caching in `msal_cache.bin`

**API Mapping**:
```python
MS Status → TaskItem Status:
  "notStarted" → "active"
  "completed" → "completed"

MS Importance → TaskItem Importance:
  "high" → "high"
  "normal" → "normal"
  "low" → "low"
```

#### GoogleTasksBackend

**Authentication**:
- OAuth 2.0 with local server flow
- Interactive browser consent
- Token caching in `google_tokens.json`

**Features**:
- No priority support (importance = None)
- Task body/notes
- Automatic token refresh

**API Mapping**:
```python
Google Status → TaskItem Status:
  "needsAction" → "active"
  "completed" → "completed"

Google doesn't have importance/priority → None
```

## Data Flow

### Sync Flow Diagram

```
┌─────────────┐
│   Start     │
└──────┬──────┘
       │
       ▼
┌─────────────────────────┐
│ Load Configuration      │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│ Acquire Lock            │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│ Authenticate Backend    │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│ Load Orgplan Tasks      │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│ Fetch Backend Tasks     │
└──────┬──────────────────┘
       │
       ├─────────────────────────────┐
       │                             │
       ▼                             ▼
┌──────────────────┐      ┌──────────────────┐
│ Orgplan → Backend│      │ Backend → Orgplan│
│                  │      │                  │
│ For each task:   │      │ For each task:   │
│ 1. Find match    │      │ 1. Find match    │
│ 2. Compare       │      │ 2. Compare       │
│ 3. Update/Create │      │ 3. Update/Create │
└──────┬───────────┘      └──────┬───────────┘
       │                         │
       └─────────┬───────────────┘
                 │
                 ▼
       ┌─────────────────────────┐
       │ Save Orgplan Changes    │
       └──────┬──────────────────┘
              │
              ▼
       ┌─────────────────────────┐
       │ Generate Statistics     │
       └──────┬──────────────────┘
              │
              ▼
       ┌─────────────────────────┐
       │ Release Lock            │
       └──────┬──────────────────┘
              │
              ▼
       ┌─────────────┐
       │   Done      │
       └─────────────┘
```

### Task Matching Logic

```python
def _find_matching_todo_task(orgplan_task, todo_by_id, todo_by_title):
    # Step 1: Get backend-specific ID attribute name
    backend_id_attr = backend.id_marker_prefix.replace('-', '_')
    # e.g., "ms-todo-id" → "ms_todo_id"

    # Step 2: Try to get backend ID from orgplan task
    backend_id = getattr(orgplan_task, backend_id_attr, None)

    # Step 3: Match by ID if available
    if backend_id and backend_id in todo_by_id:
        return todo_by_id[backend_id]

    # Step 4: Fall back to title matching
    if orgplan_task.title in todo_by_title:
        return todo_by_title[orgplan_task.title]

    # Step 5: No match found
    return None
```

### Priority Handling

```python
# Orgplan → Backend
if backend.backend_name == "microsoft":
    importance = map_priority_to_importance(task.priority)
    # "p1" → "high", "p2" → "normal", "p3" → "low"
else:  # Google Tasks
    importance = None  # Not supported

# Backend → Orgplan
if task_item.importance and backend.backend_name == "microsoft":
    priority = map_importance_to_priority(task_item.importance)
    # "high" → "p1", "normal" → "p2", "low" → "p3"
else:
    priority = None  # Keep existing or None
```

## Error Handling

### Error Hierarchy

```python
class OrgplanSyncError(Exception):
    """Base exception for all sync errors."""

class ConfigurationError(OrgplanSyncError):
    """Configuration or validation errors."""

class APIError(OrgplanSyncError):
    """API request failures."""

class NetworkError(OrgplanSyncError):
    """Network connectivity issues."""

class AuthenticationError(OrgplanSyncError):
    """Authentication failures."""

class OrgplanFormatError(OrgplanSyncError):
    """Invalid orgplan file format."""
```

### Retry Logic

```python
@retry_on_failure
def api_call():
    # Wrapped function
    pass

# Retry behavior:
# - Max retries: 3
# - Exponential backoff: 1s, 2s, 4s
# - Retry on: NetworkError, APIError (5xx)
# - No retry: AuthenticationError, ConfigurationError
```

### Graceful Degradation

- Individual task sync failures don't stop entire sync
- Errors are logged and counted
- Statistics show success/failure counts
- Exit code indicates overall result

## Extension Points

### Adding a New Backend

1. **Create backend class**:
```python
# tools/backends/new_backend.py
from .base import TaskBackend, TaskItem

class NewBackend(TaskBackend):
    @property
    def backend_name(self) -> str:
        return "newbackend"

    @property
    def id_marker_prefix(self) -> str:
        return "new-backend-id"

    # Implement all abstract methods
```

2. **Update backend factory**:
```python
# tools/backends/__init__.py
def create_backend(backend_type, config, logger):
    if backend_type == "newbackend":
        from .new_backend import NewBackend
        return NewBackend(...)
```

3. **Add configuration**:
```python
# tools/config.py
class Config:
    def __init__(self, ..., new_backend_param=None):
        self.new_backend_param = new_backend_param
```

4. **Add ID marker pattern**:
```python
# tools/orgplan_parser.py
class OrgplanParser:
    NEW_BACKEND_ID_PATTERN = re.compile(r"<!--\s*new-backend-id:\s*([^\s]+)\s*-->")

    @dataclass
    class OrgplanTask:
        new_backend_id: Optional[str] = None
```

### Custom Sync Logic

Extend `SyncEngine`:
```python
class CustomSyncEngine(SyncEngine):
    def sync_bidirectional(self):
        # Add custom pre-sync logic
        super().sync_bidirectional()
        # Add custom post-sync logic
```

### Custom Task Matching

Override matching logic:
```python
def custom_task_matcher(orgplan_task, backend_tasks):
    # Custom matching algorithm
    # E.g., fuzzy title matching, tags, etc.
    pass
```

## Performance Considerations

### Optimization Strategies

1. **Bulk Operations**: Fetch all tasks at once, not individually
2. **Change Detection**: Only update if fields actually changed
3. **Dry-run Mode**: Preview changes without API calls
4. **Caching**: Token caching to avoid re-authentication
5. **Locking**: Prevent concurrent syncs

### Scalability

Current design handles:
- **Tasks**: Hundreds of tasks per monthly file
- **Files**: Multiple monthly files (one active at a time)
- **Sync Frequency**: Every 15-30 minutes typical

Limitations:
- Single-threaded (no parallel API calls)
- One monthly file processed at a time
- No pagination for very large task lists (>1000 tasks)

## Security Considerations

### Credential Storage

- **Microsoft**: Client secret in `.env` (0o600 permissions)
- **Google**: OAuth tokens in `.tokens/` (0o700 directory, 0o600 files)
- **Cache**: MSAL cache encrypted by library

### Best Practices

1. **Never commit credentials**: `.env` in `.gitignore`
2. **Secure permissions**: Restrictive file permissions on tokens
3. **Token rotation**: Regular credential rotation recommended
4. **Audit logs**: Use log files for debugging only, redact in issues

## Testing Strategy

### Unit Tests

- Test each backend independently
- Mock API calls
- Test task matching logic
- Test priority mapping

### Integration Tests

- Test with real API endpoints (staging)
- Test authentication flows
- Test full sync cycle

### Manual Testing Checklist

- [ ] New task creation (both directions)
- [ ] Task updates (title, status, priority)
- [ ] Task matching (ID and title)
- [ ] Multiple ID markers
- [ ] Priority sync (Microsoft only)
- [ ] Authentication flows
- [ ] Error handling and retry
- [ ] Dry-run mode
- [ ] Lock file behavior

## Future Enhancements

### Potential Features

1. **Additional Backends**:
   - Todoist
   - Trello
   - Notion
   - Linear

2. **Advanced Sync**:
   - Conflict resolution UI
   - Bi-directional priority (custom mapping for Google)
   - Subtasks/checklist items
   - Due dates
   - Attachments

3. **Performance**:
   - Parallel API calls
   - Incremental sync (delta changes only)
   - Pagination for large lists

4. **Developer Experience**:
   - Plugin system for custom backends
   - Webhook support for real-time sync
   - REST API for programmatic access

## Contributing

To contribute to the architecture:

1. **Understand the abstraction**: Backend-agnostic core
2. **Follow patterns**: Use existing backend implementations as templates
3. **Test thoroughly**: Unit tests + manual verification
4. **Document**: Update this file with architectural changes
5. **Maintain compatibility**: Don't break existing backends

## References

- [Microsoft Graph API Documentation](https://docs.microsoft.com/en-us/graph/api/resources/todo-overview)
- [Google Tasks API Documentation](https://developers.google.com/tasks)
- [MSAL Python Documentation](https://msal-python.readthedocs.io/)
- [Google OAuth Documentation](https://developers.google.com/identity/protocols/oauth2)
