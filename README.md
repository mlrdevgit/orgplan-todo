# orgplan-todo

Synchronize tasks between your orgplan productivity system and Microsoft To Do or Google Tasks.

## Features

- **Multiple backends**: Choose between Microsoft To Do or Google Tasks
- **Bidirectional sync** between orgplan markdown files and your task backend
- **Flexible authentication**:
  - Microsoft: Application (client credentials) or Delegated (user login)
  - Google: OAuth 2.0 with interactive login
- **Intelligent task matching** using unique IDs and title fallback
- **Status synchronization** in both directions (DONE ↔ Completed, PENDING/Active)
- **Priority mapping** for Microsoft To Do (#p1 ↔ High, #p2 ↔ Normal, #p3+ ↔ Low)
- **New task creation** from either system
- **Detail section sync** with orgplan taking precedence
- **Due date sync** using orgplan timestamp markers (e.g., `DEADLINE: <YYYY-MM-DD>`, `SCHEDULED: <YYYY-MM-DD>`, or `<YYYY-MM-DD>`)
- **Automated sync** with file locking and cron support
- **Dry-run mode** to preview changes before applying
- **Flexible configuration** via CLI, environment variables, or .env file

## Installation

1. Clone this repository:
```bash
git clone https://github.com/mlrdevgit/orgplan-todo.git
cd orgplan-todo
```

2. Clone `orgplan` core library (required dependency):
```bash
# Clone into a parallel directory or adjusting path as needed
git clone https://github.com/mlrdevgit/orgplan.git ../orgplan
```

3. Configure Environment:
You must ensure `orgplan` is in your Python path.

**Linux/macOS:**
```bash
export PYTHONPATH=$PYTHONPATH:../orgplan
```

**Windows (PowerShell):**
```powershell
$env:PYTHONPATH="$env:PYTHONPATH;..\orgplan"
```

4. Install dependencies:
```bash
pip install -r requirements.txt
```

5. Set up configuration:
```bash
cp .env.example .env
# Edit .env with your backend credentials (Microsoft or Google)
```

## Configuration

### Authentication Setup

#### Microsoft To Do

This tool supports two authentication modes for Microsoft To Do:

**1. Application Mode (Client Credentials)**
- Best for: Server automation, background sync
- Requires: Client ID, Tenant ID, Client Secret
- Requires: Admin consent for API permissions
- No user interaction after setup

**2. Delegated Mode (User Login)**
- Best for: Personal use, single-user scenarios
- Requires: Client ID, Tenant ID only (no secret)
- No admin consent required
- One-time interactive login, then tokens cached

#### Google Tasks

Google Tasks uses OAuth 2.0 for authentication:

- **Authentication Mode**: OAuth 2.0 (User consent)
- **Best for**: Personal use, individual Google accounts
- **Requires**: Client ID, Client Secret from Google Cloud Console
- **Setup**: One-time interactive login, tokens cached locally
- **No admin consent required** for personal accounts

📖 **Setup Guides:**
- **[Microsoft To Do Setup](docs/GRAPH_API_SETUP.md)** - Complete guide for both authentication modes
- **[Google Tasks Setup](docs/GOOGLE_TASKS_SETUP.md)** - OAuth 2.0 setup for Google Tasks

### Backend Selection

Choose your backend in `.env`:
```env
TASK_BACKEND=microsoft  # or "google"
```

Or via CLI:
```bash
python tools/sync.py --backend google --todo-list "My Tasks"
```

### Configuration Options

Configuration can be provided via (in order of precedence):
1. Command-line arguments
2. Environment variables
3. `.env` file
4. `orgplan` core configuration (via `ORGPLAN_CONFIG` or default locations)

#### Common Options

| Parameter | CLI Option | Env Var | Required | Default |
|-----------|------------|---------|----------|---------|
| Backend | `--backend` | `TASK_BACKEND` | No | `microsoft` |
| Task List Name | `--todo-list` | `TODO_LIST_NAME` or `GOOGLE_TASK_LIST_NAME` | Yes (optional for Google primary list) | - |
| Token Storage | `--token-storage-path` | `TOKEN_STORAGE_PATH` | No | `.tokens/` |
| Allow Prompt | `--no-prompt` | - | No | `true` |
| Orgplan Directory | `--orgplan-dir` | `ORGPLAN_DIR` | No | `.` (current) |
| Month | `--month` | `SYNC_MONTH` | No | Current month |
| Log File | `--log-file` | `LOG_FILE` | No | None |

#### Microsoft To Do Options

| Parameter | CLI Option | Env Var | Required | Default |
|-----------|------------|---------|----------|---------|
| Auth Mode | `--auth-mode` | `AUTH_MODE` | No | `application` |
| Client ID | `--client-id` | `MS_CLIENT_ID` | Yes | - |
| Tenant ID | `--tenant-id` | `MS_TENANT_ID` | Yes | - |
| Client Secret | `--client-secret` | `MS_CLIENT_SECRET` | Application mode only | - |

#### Google Tasks Options

| Parameter | CLI Option | Env Var | Required | Default |
|-----------|------------|---------|----------|---------|
| Client ID | - | `GOOGLE_CLIENT_ID` | Yes | - |
| Client Secret | - | `GOOGLE_CLIENT_SECRET` | Yes | - |

## Usage

### Basic Sync (Application Mode)

```bash
python tools/sync.py --todo-list "Orgplan 2025"
```

### Delegated Mode (User Login)

```bash
# First-time: Interactive login required
python tools/sync.py --todo-list "Orgplan 2025" --auth-mode delegated

# Subsequent runs: Uses cached tokens
python tools/sync.py --todo-list "Orgplan 2025" --auth-mode delegated
```

### Dry Run (Preview Changes)

```bash
python tools/sync.py --todo-list "Orgplan 2025" --dry-run
```

### Sync Specific Month

```bash
python tools/sync.py --todo-list "Orgplan 2025" --month 2025-11
```

### With Logging

```bash
python tools/sync.py --todo-list "Orgplan 2025" --log-file sync.log
```

### Google Tasks

```bash
# First-time: Interactive login required
python tools/sync.py --backend google --todo-list "My Tasks"

# Use primary task list (default)
python tools/sync.py --backend google

# Subsequent runs: Uses cached tokens
python tools/sync.py --backend google
```

### Automated Sync (Cron Job)

```bash
# For delegated mode (Microsoft) or Google Tasks, use --no-prompt to prevent blocking
python tools/sync.py --todo-list "Orgplan 2025" --auth-mode delegated --no-prompt --log-file sync.log

# Google Tasks cron example
python tools/sync.py --backend google --no-prompt --log-file sync.log
```

### Override Configuration

```bash
python tools/sync.py \
  --client-id YOUR_CLIENT_ID \
  --tenant-id YOUR_TENANT_ID \
  --client-secret YOUR_SECRET \
  --todo-list "Orgplan 2025" \
  --orgplan-dir ~/notes
```

## Orgplan File Format

### Directory Structure

```
2025/
  01-notes.md
  02-notes.md
  ...
  12-notes.md
```

### Monthly File Format

Each monthly file starts with a `# TODO List` section:

```markdown
# TODO List

- #p1 #4h Learn how to refine an LLM
- [DONE] #p2 Review project documentation
- [PENDING] Setup development environment
- Write quarterly report

# Learn how to refine an LLM

<!-- ms-todo-id: AAMkAGI2T... -->
<!-- google-tasks-id: MTIzNDU2Nzg5... -->

## Steps

- [ ] Pick a scenario to implement
- [ ] Research the general approach
...
```

### Task Format

```
- [STATUS] #priority Task description DEADLINE: <YYYY-MM-DD>
```

- **Status**: `[DONE]`, `[PENDING]`, `[DELEGATED]` (optional)
- **Priority**: `#p1`, `#p2`, `#p3`, etc. (optional)
- **Time estimates**: `#1h`, `#2h`, `#1d` (ignored by sync)
- **#blocked**: Indicates blocked task (ignored by sync)
- **Due dates**: Use `DEADLINE: <YYYY-MM-DD>`, `SCHEDULED: <YYYY-MM-DD>`, or a plain `<YYYY-MM-DD>` timestamp

## Sync Behavior (Bidirectional)

### Orgplan → Backend (Microsoft/Google)

- New tasks in orgplan → Created in task backend
- Status changes → Update completion status
- Priority changes → Update importance (Microsoft only)
- Title changes → Update task title
- `[DONE]` or `[DELEGATED]` → Mark completed in backend
- Due dates → Synced to backend due dates
- Tasks with existing backend ID markers are matched by ID
- Tasks without ID are matched by title

### Backend → Orgplan

- New tasks in backend → Created in orgplan TODO list
- Task completed in backend → Mark `[DONE]` in orgplan
- Title changes → Update task description
- Due dates → Appended as `<YYYY-MM-DD>` in the task title (unless the detail section already has `DEADLINE:`/`SCHEDULED:` markers)
- **Microsoft only**: Importance changes → Update priority tags
  - `high` → `#p1`
  - `normal` → `#p2`
  - `low` → `#p3`
- **Google**: Priority tags are ignored (Google Tasks doesn't support priority)
- Backend notes → Added to detail section (only if orgplan detail section is empty)

### Task Matching

Tasks are matched between systems using:
1. **Primary:** Backend-specific ID marker in orgplan detail section
   - Microsoft: `<!-- ms-todo-id: X -->`
   - Google: `<!-- google-tasks-id: X -->`
2. **Fallback:** Exact title matching (case-sensitive)

**Note:** Tasks can have both Microsoft and Google ID markers. This allows switching backends without creating duplicates (each backend only looks for its own marker).

### Detail Section Sync

- **Orgplan takes precedence:** If orgplan has content in the detail section, it is NOT overwritten by backend notes
- **Empty orgplan detail:** Backend notes can be synced to empty orgplan detail sections
- Backend ID markers are always maintained for task matching

### Excluded from Sync

- Tasks already marked `[DONE]` in prior monthly files
- Completed backend tasks not present in current orgplan (likely from previous months)
- Time estimates (`#1h`, `#2h`, `#1d`)
- `#blocked` tag
- Task deletions (ignored in both directions)
- Priority tags when using Google Tasks backend (not supported)

## Automated Sync


### Quick Setup (Linux/macOS - Cron)

Use the automated setup script:
```bash
cd orgplan-todo
TODO_LIST_NAME="Orgplan 2025" SCHEDULE="*/30 * * * *" tools/setup_cron.sh
```

### Quick Setup (Windows - Task Scheduler)

Use the automated PowerShell script:
```powershell
cd orgplan-todo
.\tools\setup_tasksched.ps1 -TodoList "Orgplan 2025" -ScheduleMinutes 30
```

This script will:
- Create a Windows Scheduled Task
- Set up logging to `sync.log`
- Handle execution parameters


This script will:
- Validate your `.env` file exists
- Create a cron job with your specified schedule
- Set up logging to `sync.log`
- Handle concurrent execution prevention

### Manual Setup

Run sync every hour:
```bash
0 * * * * cd ~/orgplan && python tools/sync.py --todo-list "Orgplan 2025" --log-file sync.log 2>&1
```

Run every 30 minutes:
```bash
*/30 * * * * cd ~/orgplan && python tools/sync.py --todo-list "Orgplan 2025" --log-file sync.log 2>&1
```

### Concurrent Execution Prevention

The sync automatically uses file-based locking to prevent concurrent runs:
- Lock file: `sync.lock` in orgplan directory
- Stale locks (>1 hour old) are automatically cleaned up
- Lock is always released, even on errors or interruption

## Error Handling

The script exits with different codes based on the outcome:
- `0`: Success
- `1`: Configuration error, API error, or sync error
- `2`: Sync conflicts detected (future feature)
- `130`: Interrupted by user (Ctrl+C)

## Troubleshooting

### "Task list not found" Error

The script will list all available task lists. Make sure the name matches exactly:
```bash
# Microsoft To Do
python tools/sync.py --todo-list "Orgplan 2025"

# Google Tasks
python tools/sync.py --backend google --todo-list "My Tasks"
```

For Google Tasks, if no list is specified, the primary list is used automatically.

### "Orgplan file does not exist" Error

Ensure the monthly file exists for the month you're syncing:
```
2025/12-notes.md  # For December 2025
```

### Authentication Errors

**Microsoft To Do:**
- Verify Client ID, Tenant ID, and Client Secret (for application mode)
- Ensure app has `Tasks.ReadWrite` permission
- For delegated mode, run without `--no-prompt` first to authenticate

**Google Tasks:**
- Verify Client ID and Client Secret from Google Cloud Console
- Ensure OAuth 2.0 consent screen is configured
- Run without `--no-prompt` first to complete interactive authentication
- Check that tokens are saved to `.tokens/google_tokens.json`

For detailed troubleshooting, see [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

## Documentation

- 📖 **[Microsoft Graph API Setup Guide](docs/GRAPH_API_SETUP.md)** - Complete setup instructions
- 🔧 **[Troubleshooting Guide](docs/TROUBLESHOOTING.md)** - Common issues and solutions
- 📋 **[Example Workflows](docs/WORKFLOWS.md)** - Daily, weekly, and advanced usage patterns
- 📝 **[Project Plan](PLAN.md)** - Complete technical specification

### Quick Commands

```bash
# Validate configuration
python tools/sync.py --validate-config

# Test sync (no changes)
python tools/sync.py --todo-list "Orgplan 2025" --dry-run

# Full sync with logging
python tools/sync.py --todo-list "Orgplan 2025" -v --log-file sync.log

# Setup automated sync (Linux/macOS)
TODO_LIST_NAME="Orgplan 2025" tools/setup_cron.sh

# Setup automated sync (Windows)
.\tools\setup_tasksched.ps1 -TodoList "Orgplan 2025"

```

## Backend Comparison

| Feature | Microsoft To Do | Google Tasks |
|---------|----------------|--------------|
| **Authentication** | Application or Delegated (MSAL) | OAuth 2.0 (User consent) |
| **Admin Consent** | Required for application mode | Not required |
| **Priority Support** | ✅ Yes (High/Normal/Low) | ❌ No |
| **Task Notes/Body** | ✅ Yes | ✅ Yes |
| **Completion Status** | ✅ Yes | ✅ Yes |
| **Multiple Lists** | ✅ Yes | ✅ Yes |
| **ID Marker** | `ms-todo-id` | `google-tasks-id` |
| **Token Storage** | `.tokens/msal_cache.bin` | `.tokens/google_tokens.json` |
| **Cron Support** | ✅ Yes | ✅ Yes |
| **Default List** | Must specify | Uses primary if not specified |

**Choosing a Backend:**
- **Microsoft To Do**: Best if you need priority support, work in enterprise environment, or prefer Microsoft ecosystem
- **Google Tasks**: Best if you use personal Google account, prefer simpler OAuth setup, don't need priority levels

## Development Roadmap

See [PLAN.md](PLAN.md) for the complete project plan.

### Phase 1: Foundation (MVP) ✓
- Orgplan → To Do sync
- Basic task matching
- Console logging

### Phase 2: Bidirectional Sync ✓
- To Do → Orgplan sync
- Task ID markers with fallback to title matching
- Detail section sync (orgplan takes precedence)
- Status, priority, and title sync both directions
- New task creation from both systems

### Phase 3: Robustness ✓
- Custom error class hierarchy
- Retry logic with exponential backoff
- Orgplan file format validation
- API error classification
- Enhanced error handling

### Phase 4: Automation ✓
- File-based locking for concurrent prevention
- Cron setup script (tools/setup_cron.sh)
- Windows Task Scheduler script (tools/setup_tasksched.ps1)
- Automated lock cleanup

- Stale lock detection
- Production-ready for scheduled execution

### Phase 5: Polish & Documentation ✓
- Microsoft Graph API setup guide (docs/GRAPH_API_SETUP.md)
- Troubleshooting guide (docs/TROUBLESHOOTING.md)
- Example workflows documentation (docs/WORKFLOWS.md)
- Configuration validation command (--validate-config)
- Comprehensive README with quick commands
- Production-ready with full documentation

## Contributing

This project is in active development. Contributions are welcome!

## License

[Add license information]
