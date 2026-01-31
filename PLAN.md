# Orgplan-Todo Synchronization Project Plan

> **Note:** This document was the original project plan written before multi-backend
> support was added. The project now supports both **Microsoft To Do** and
> **Google Tasks** as backends. See [PLAN_GOOGLE_TASKS.md](PLAN_GOOGLE_TASKS.md)
> for the Google Tasks implementation plan and [README.md](README.md) for
> current documentation.

## Project Overview

This project provides Python scripts to synchronize tasks between an orgplan productivity system (plain text markdown files) and cloud task management services (Microsoft To Do and Google Tasks).

**Key Principles:**
- Bidirectional synchronization
- Orgplan detail sections take precedence over backend notes
- Graceful conflict resolution via dedicated task
- Configuration-driven execution
- Suitable for manual or automated (cron) execution

---

## Orgplan System Format

### Directory Structure

```
2024/01-notes.md
2025/10-notes.md
2025/11-notes.md
2025/12-notes.md
tools/
  sync.py
.env
```

### Monthly Notes File Format

Each monthly file (e.g., `2025/12-notes.md`) follows this structure:

1. **TODO List Section** (always first):
```markdown
# TODO List

- [STATUS] #priority #time Task description
- #p1 #4h Learn how to refine an LLM
- [DONE] #p2 Review project documentation
- [PENDING] #p1 #blocked Setup development environment
- Write quarterly report
```

2. **Detail Sections** (one per task):
```markdown
# Learn how to refine an LLM

<!-- ms-todo-id: AAMkAGI2T... -->

## Steps

- [ ] Pick a scenario to implement
- [ ] Research the general approach
- [ ] Create a practice plan
- [ ] Refine an LLM and put it to work

[Additional notes, links, commands, observations...]
```

### Task Format Specification

**TODO List Item Format:**
```
- [STATUS] #tags Task description
```

**Components:**
- `[STATUS]`: Optional - `[DONE]`, `[PENDING]`, `[DELEGATED]`, or `[CANCELED]`
- Priority tags: `#p1`, `#p2`, `#p3`, etc.
- Time estimates: `#1h`, `#2h`, `#1d`, etc. (ignored by sync)
- `#blocked`: Indicates blocked task (ignored by sync)
- Task description: Free text

**Detail Section Marker:**
```markdown
# Task Description

<!-- ms-todo-id: UNIQUE_ID -->
```

---

## Microsoft To Do Integration

### To Do List Structure

- **One list per year**: e.g., "Orgplan 2025", "Work Tasks 2025"
- List name is configurable via CLI option
- Script syncs with current month's orgplan file
- List must exist (script exits with error if missing)

### To Do Task Fields

**Field Mappings:**

| Orgplan | Microsoft To Do |
|---------|-----------------|
| Task description (no tags/status) | Title |
| `[DONE]` | Status: Completed |
| `[DELEGATED]` | Status: Completed |
| `[PENDING]` or unmarked | Status: Not Completed |
| `#p1` | Importance: High |
| `#p2` | Importance: Normal |
| `#p3` or higher | Importance: Low |
| Detail section content | Body/Notes (only if orgplan detail is empty) |
| `<!-- ms-todo-id: X -->` | Task ID for matching |

**Fields Ignored:**
- Time estimates (`#1h`, `#2h`, `#1d`)
- `#blocked` tag
- Checklist items in detail sections (no special sync behavior)

---

## Synchronization Logic

### Sync Scope

**Included:**
- All tasks in current month's `# TODO List` section

**Excluded:**
- Tasks marked `[DONE]` in prior monthly files
- Tasks with completed date in To Do (if already synced)

### Sync Direction: Bidirectional

**Orgplan → To Do:**
1. New task in orgplan → Create in To Do
2. Status change to `[DONE]` → Mark completed in To Do
3. Status change to `[DELEGATED]` → Mark completed in To Do
4. Task title change → Update title in To Do
5. Priority change → Update importance in To Do
6. Detail section added/updated → Update To Do notes (only if To Do notes empty)

**To Do → Orgplan:**
1. New task in To Do → Add to `# TODO List`
2. Task marked completed → Add `[DONE]` status
3. Task title change → Update description in TODO list
4. Importance change → Update priority tag
5. Notes added/updated → Add to detail section (only if orgplan detail section empty)

### Task Matching Strategy

**Primary Method:** To Do ID marker
```markdown
# Task Name

<!-- ms-todo-id: AAMkAGI2T... -->
```

**Fallback Method:** Title matching
- Strip status blocks (`[DONE]`, `[PENDING]`, `[DELEGATED]`)
- Strip all tags (`#p1`, `#2h`, `#blocked`, etc.)
- Compare remaining text (case-sensitive)

**When creating new tasks:**
- Add `<!-- ms-todo-id: X -->` to detail section
- Create detail section if it doesn't exist

### Monthly File Transition

When a new monthly file is created:
- Active tasks are typically rolled over manually to new file
- Sync script operates only on current month's file
- No special action needed in To Do (tasks already exist)
- Completed tasks remain in old monthly files

### Deletion Behavior

**Ignored:** Deletions in either system do not trigger deletion in the other system.

---

## Conflict Resolution

### Conflict Detection

A conflict occurs when:
1. A task is modified in both orgplan and To Do between syncs
2. Modifications are incompatible (e.g., different title changes)

### Conflict Handling

**Create/Update Conflict Task:**
```markdown
# TODO List

- [PENDING] #p1 Resolve sync conflicts

# Resolve sync conflicts

## Conflicts detected on YYYY-MM-DD HH:MM:SS

### Task: "Original Task Title"

**Orgplan version:**
- Title: "Updated title A"
- Status: [PENDING]
- Priority: #p1

**To Do version:**
- Title: "Updated title B"
- Status: Completed
- Importance: Normal

**Action required:** Manually resolve and re-run sync.
```

**Rules:**
- Add conflict details to existing "Resolve sync conflicts" task if present
- Create new task if not present
- Abort sync on conflict (do not apply partial changes)
- User must manually resolve and re-run

---

## Configuration

### Authentication (Microsoft Graph API)

**Required Configuration:**
- Client ID
- Tenant ID
- Client Secret or Certificate
- Scopes: `Tasks.ReadWrite`

**Future Enhancement:** Add detailed setup instructions for app registration

### Configuration Sources (Priority Order)

1. Command-line options
2. Environment variables
3. `.env` file
4. Default values (where applicable)

### Configuration Parameters

| Parameter | CLI Option | Env Var | Required | Default | Description |
|-----------|------------|---------|----------|---------|-------------|
| Client ID | `--client-id` | `MS_CLIENT_ID` | Yes | - | Azure AD app client ID |
| Tenant ID | `--tenant-id` | `MS_TENANT_ID` | Yes | - | Azure AD tenant ID |
| Client Secret | `--client-secret` | `MS_CLIENT_SECRET` | Yes | - | Azure AD app secret |
| Orgplan Root | `--orgplan-dir` | `ORGPLAN_DIR` | No | `.` | Root directory for orgplan files |
| To Do List Name | `--todo-list` | `TODO_LIST_NAME` | Yes | - | Name of To Do list to sync |
| Month | `--month` | `SYNC_MONTH` | No | Current (YYYY-MM) | Month to sync (format: YYYY-MM) |
| Dry Run | `--dry-run` | - | No | False | Preview changes without applying |
| Log File | `--log-file` | `LOG_FILE` | No | None | Log file path (console always logs) |

### Example Usage

```bash
# Manual sync with dry-run
python tools/sync.py \
  --orgplan-dir /path/to/notes \
  --todo-list "Orgplan 2025" \
  --dry-run

# Full sync with logging
python tools/sync.py \
  --orgplan-dir ~/orgplan \
  --todo-list "Work Tasks 2025" \
  --log-file sync.log

# Override month
python tools/sync.py \
  --todo-list "Orgplan 2025" \
  --month 2025-11

# Using .env file
# (credentials in .env, other options via CLI)
python tools/sync.py --todo-list "Orgplan 2025"
```

### Cron Setup

```bash
# Run every hour
0 * * * * cd ~/orgplan && python tools/sync.py --todo-list "Orgplan 2025" >> cron.log 2>&1

# Run every 30 minutes with logging
*/30 * * * * cd ~/orgplan && python tools/sync.py --todo-list "Orgplan 2025" --log-file sync.log
```

---

## Error Handling

### Error Categories

**1. Configuration Errors:**
- Missing required parameters
- Invalid authentication credentials
- Invalid orgplan directory path
- Action: Exit with clear error message and exit code 1

**2. Missing Resources:**
- To Do list not found
- Current month's orgplan file not found
- Action: Exit with error message and exit code 1

**3. API Errors:**
- Network failures
- Graph API errors (auth, rate limiting, etc.)
- Action: Abort, log detailed error, exit code 1

**4. Sync Conflicts:**
- Incompatible changes in both systems
- Action: Create/update conflict task, log details, exit code 2

**5. File I/O Errors:**
- Cannot read orgplan file
- Cannot write to orgplan file
- Action: Log error with details, exit code 1

### Logging

**Console Output (always enabled):**
- INFO: Summary of changes
- WARNING: Non-fatal issues
- ERROR: Fatal errors with details

**File Logging (optional):**
- Same as console output
- Timestamped entries
- Append mode
- Include full stack traces for debugging

**Log Format:**
```
[2025-12-30 14:30:22] INFO: Starting sync for 2025-12
[2025-12-30 14:30:23] INFO: Found 15 tasks in orgplan
[2025-12-30 14:30:24] INFO: Found 12 tasks in To Do list "Orgplan 2025"
[2025-12-30 14:30:25] INFO: Creating 3 new tasks in To Do
[2025-12-30 14:30:26] INFO: Updating 2 tasks in orgplan
[2025-12-30 14:30:27] INFO: Sync completed successfully
```

---

## Implementation Phases

### Phase 1: Foundation (MVP)

**Deliverables:**
1. `tools/sync.py` - Main sync script
2. `.env.example` - Example configuration file
3. `requirements.txt` - Python dependencies
4. Basic README with usage instructions

**Features:**
- Microsoft Graph API authentication
- Parse orgplan TODO list section
- Parse orgplan detail sections
- Read To Do tasks from specified list
- Basic task matching (title-based)
- Unidirectional sync: Orgplan → To Do only
- Console logging
- Basic error handling

**Testing:**
- Create sample orgplan file
- Manual testing with real To Do account
- Verify task creation and updates

### Phase 2: Bidirectional Sync

**Features:**
- To Do → Orgplan sync
- Task ID marker in detail sections (`<!-- ms-todo-id: X -->`)
- Improved task matching with ID fallback
- Status sync both directions
- Priority/importance sync both directions
- Detail section sync (orgplan takes precedence)

**Testing:**
- Test task creation from To Do
- Test status updates both ways
- Test title changes both ways
- Test priority changes

### Phase 3: Robustness

**Features:**
- Conflict detection and resolution
- Create/update "Resolve sync conflicts" task
- File logging option
- Comprehensive error handling
- Retry logic for transient failures
- Validation of orgplan file format
- Better logging with dry-run mode summary

**Testing:**
- Intentionally create conflicts
- Test with malformed orgplan files
- Test with network failures
- Test with missing To Do list

### Phase 4: Automation

**Deliverables:**
- Cron setup script or instructions
- `--dry-run` mode
- Enhanced logging for automation
- Lock file to prevent concurrent runs

**Features:**
- Prevent concurrent sync execution
- Better error messages for automation context
- Success/failure exit codes
- Email notification on errors (optional)

**Testing:**
- Run via cron
- Test concurrent execution prevention
- Verify logging in automated context

### Phase 5: Polish & Documentation

**Deliverables:**
- Comprehensive README
- Setup guide for Microsoft Graph API
- Troubleshooting guide
- Example workflows

**Features:**
- Input validation and helpful error messages
- Progress indicators for long operations
- Statistics summary (X created, Y updated, Z conflicts)
- Configuration validation command

---

## Future Enhancements

### Implemented Since Original Plan

- ✅ **Microsoft Graph API Setup Guide** - See docs/GRAPH_API_SETUP.md
- ✅ **Due Date Support** - DEADLINE, SCHEDULED, and plain timestamp markers
- ✅ **Google Tasks Integration** - Full backend with OAuth 2.0 (see PLAN_GOOGLE_TASKS.md)
- ✅ **One-way Sync** - `--sync-direction` flag for orgplan-to-remote or remote-to-orgplan
- ✅ **CANCELED Status** - Tasks marked `[CANCELED]` are synced as completed

### Planned for Future Iterations

1. **Multiple To Do Lists**
   - Support syncing to different lists based on tags or priorities
   - Map projects to separate lists

2. **Recurring Tasks**
   - Handle recurring tasks in backend
   - Smart handling in orgplan

3. **Attachments/Links**
   - Sync links from detail sections to backend
   - Handle backend attachments

4. **Archive Handling**
   - Option to archive completed backend tasks
   - Keep orgplan as source of truth for history

5. **Multi-file Sync**
   - Option to sync multiple months
   - Aggregate view across time periods

6. **Web Dashboard**
   - Visual conflict resolution UI
   - Sync history and statistics
   - Manual sync trigger

7. **Additional Backends**
   - Todoist integration
   - Trello integration
   - Calendar integration for due dates

---

## Technical Stack

**Core Dependencies:**
- Python 3.8+
- `msal` - Microsoft Authentication Library
- `requests` - HTTP client for Graph API
- `python-dotenv` - Environment variable management
- `argparse` - CLI argument parsing (stdlib)
- `google-auth-oauthlib` - Google OAuth 2.0 flow
- `google-auth-httplib2` - HTTP library for Google APIs
- `google-api-python-client` - Google Tasks API client

**Optional Dependencies:**
- `pytest` - Testing framework
- `black` - Code formatting
- `pylint` - Code linting

---

## Project Structure

```
orgplan-todo/
├── .env                          # Configuration (not in git)
├── .env.example                  # Example configuration
├── .gitignore
├── README.md                     # User documentation
├── PLAN.md                       # This file
├── requirements.txt              # Python dependencies
├── tools/
│   ├── sync.py                   # Main sync script
│   ├── orgplan_parser.py         # Orgplan file parser
│   ├── todo_client.py            # Microsoft To Do API client
│   ├── sync_engine.py            # Sync logic
│   └── config.py                 # Configuration management
├── tests/
│   ├── test_orgplan_parser.py
│   ├── test_todo_client.py
│   ├── test_sync_engine.py
│   └── fixtures/
│       └── sample_notes.md
└── 2025/
    └── 12-notes.md               # Sample orgplan file
```

---

## Success Criteria

### Phase 1 (MVP)
- ✓ Can authenticate with Microsoft Graph API
- ✓ Can parse orgplan TODO list
- ✓ Can create tasks in To Do
- ✓ Can update existing To Do tasks
- ✓ Console logging works
- ✓ Basic error handling

### Phase 2 (Bidirectional)
- ✓ Tasks created in To Do appear in orgplan
- ✓ Completions sync both directions
- ✓ Title changes sync both directions
- ✓ Task ID markers work for matching
- ✓ Priority/importance syncs correctly

### Phase 3 (Robustness)
- ✓ Conflicts are detected and reported
- ✓ Conflict task is created/updated
- ✓ File logging works
- ✓ All error cases handled gracefully
- ✓ Dry-run mode works correctly

### Phase 4 (Automation)
- ✓ Can run via cron successfully
- ✓ Concurrent execution prevented
- ✓ Exit codes are correct
- ✓ Logging suitable for automation

### Phase 5 (Polish)
- ✓ Documentation is complete
- ✓ Setup instructions are clear
- ✓ Error messages are helpful
- ✓ Ready for production use

---

## Risk Assessment

### High Priority Risks

**1. API Rate Limiting**
- Risk: Graph API rate limits could cause sync failures
- Mitigation: Implement retry with exponential backoff, batch operations where possible

**2. Concurrent Modifications**
- Risk: User modifying files during sync could cause corruption
- Mitigation: File locking, atomic writes, backup before modification

**3. Data Loss**
- Risk: Bugs could delete or corrupt tasks
- Mitigation: Dry-run mode, extensive testing, backup recommendations

**4. Authentication Issues**
- Risk: Token expiration, permission changes
- Mitigation: Proper token refresh, clear error messages, setup validation

### Medium Priority Risks

**5. Format Variations**
- Risk: Users may have slightly different orgplan formats
- Mitigation: Flexible parsing, validation with helpful errors

**6. Network Failures**
- Risk: Transient failures could cause incomplete syncs
- Mitigation: Transaction-like approach, rollback on partial failure

### Low Priority Risks

**7. Performance**
- Risk: Large task lists could be slow
- Mitigation: Pagination, incremental sync, progress indicators

---

## Notes

- This plan assumes the user follows the orgplan format consistently
- Monthly file rollover is manual and out of scope
- The system is designed for personal productivity (single user)
- No multi-user or collaboration features planned
- Graph API permissions should be scoped to minimum required (Tasks.ReadWrite)
