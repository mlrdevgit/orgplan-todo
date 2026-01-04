# orgplan-todo

Synchronize tasks between your orgplan productivity system and Microsoft To Do using the Graph API.

## Features

- **Bidirectional sync** between orgplan markdown files and Microsoft To Do
- **Two authentication modes**: Application (client credentials) or Delegated (user login)
- **Intelligent task matching** using unique IDs and title fallback
- **Status synchronization** in both directions (DONE ↔ Completed, PENDING/Active)
- **Priority mapping** (#p1 ↔ High, #p2 ↔ Normal, #p3+ ↔ Low)
- **New task creation** from either system
- **Detail section sync** with orgplan taking precedence
- **Automated sync** with file locking and cron support
- **Dry-run mode** to preview changes before applying
- **Flexible configuration** via CLI, environment variables, or .env file

## Installation

1. Clone this repository:
```bash
git clone https://github.com/mlrdevgit/orgplan-todo.git
cd orgplan-todo
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up configuration:
```bash
cp .env.example .env
# Edit .env with your Microsoft Graph API credentials
```

## Configuration

### Microsoft Graph API Setup

This tool supports two authentication modes:

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

📖 **[Complete Setup Guide](docs/GRAPH_API_SETUP.md)** - Step-by-step instructions for both modes

### Configuration Options

Configuration can be provided via (in order of precedence):
1. Command-line arguments
2. Environment variables
3. `.env` file

| Parameter | CLI Option | Env Var | Required | Default |
|-----------|------------|---------|----------|---------|
| Auth Mode | `--auth-mode` | `AUTH_MODE` | No | `application` |
| Client ID | `--client-id` | `MS_CLIENT_ID` | Yes | - |
| Tenant ID | `--tenant-id` | `MS_TENANT_ID` | Yes | - |
| Client Secret | `--client-secret` | `MS_CLIENT_SECRET` | Application mode only | - |
| Token Storage | `--token-storage-path` | `TOKEN_STORAGE_PATH` | No | `.tokens/` |
| Allow Prompt | `--no-prompt` | - | No | `true` |
| To Do List Name | `--todo-list` | `TODO_LIST_NAME` | Yes | - |
| Orgplan Directory | `--orgplan-dir` | `ORGPLAN_DIR` | No | `.` (current) |
| Month | `--month` | `SYNC_MONTH` | No | Current month |
| Log File | `--log-file` | `LOG_FILE` | No | None |

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

### Automated Sync (Cron Job)

```bash
# For delegated mode, use --no-prompt to prevent blocking
python tools/sync.py --todo-list "Orgplan 2025" --auth-mode delegated --no-prompt --log-file sync.log
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

## Steps

- [ ] Pick a scenario to implement
- [ ] Research the general approach
...
```

### Task Format

```
- [STATUS] #priority Task description
```

- **Status**: `[DONE]`, `[PENDING]`, `[DELEGATED]` (optional)
- **Priority**: `#p1`, `#p2`, `#p3`, etc. (optional)
- **Time estimates**: `#1h`, `#2h`, `#1d` (ignored by sync)
- **#blocked**: Indicates blocked task (ignored by sync)

## Sync Behavior (Bidirectional - Phase 2)

### Orgplan → To Do

- New tasks in orgplan → Created in To Do
- Status changes → Update completion status
- Priority changes → Update importance
- Title changes → Update task title
- `[DONE]` or `[DELEGATED]` → Mark completed in To Do
- Tasks with existing `<!-- ms-todo-id: X -->` are matched by ID
- Tasks without ID are matched by title

### To Do → Orgplan

- New tasks in To Do → Created in orgplan TODO list
- Task completed in To Do → Mark `[DONE]` in orgplan
- Title changes → Update task description
- Importance changes → Update priority tags
  - `high` → `#p1`
  - `normal` → `#p2`
  - `low` → `#p3`
- To Do notes → Added to detail section (only if orgplan detail section is empty)

### Task Matching

Tasks are matched between systems using:
1. **Primary:** `ms-todo-id` marker in orgplan detail section
2. **Fallback:** Exact title matching (case-sensitive)

### Detail Section Sync

- **Orgplan takes precedence:** If orgplan has content in the detail section, it is NOT overwritten by To Do notes
- **Empty orgplan detail:** To Do notes can be synced to empty orgplan detail sections
- The `<!-- ms-todo-id: X -->` marker is always maintained for task matching

### Excluded from Sync

- Tasks already marked `[DONE]` in prior monthly files
- Completed To Do tasks not present in current orgplan (likely from previous months)
- Time estimates (`#1h`, `#2h`, `#1d`)
- `#blocked` tag
- Task deletions (ignored in both directions)

## Automated Sync with Cron

### Quick Setup (Recommended)

Use the automated setup script:
```bash
cd orgplan-todo
TODO_LIST_NAME="Orgplan 2025" SCHEDULE="*/30 * * * *" tools/setup_cron.sh
```

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

### "To Do list not found" Error

The script will list all available To Do lists. Make sure the name matches exactly:
```bash
python tools/sync.py --todo-list "Orgplan 2025"
```

### "Orgplan file does not exist" Error

Ensure the monthly file exists for the month you're syncing:
```
2025/12-notes.md  # For December 2025
```

### Authentication Errors

Verify your Microsoft Graph API credentials are correct:
- Client ID
- Tenant ID
- Client Secret
- App has `Tasks.ReadWrite` permission

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

# Setup automated sync
TODO_LIST_NAME="Orgplan 2025" tools/setup_cron.sh
```

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
