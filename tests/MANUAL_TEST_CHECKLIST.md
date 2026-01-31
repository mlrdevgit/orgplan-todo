# Manual Testing Checklist

This checklist covers manual testing scenarios for both Microsoft To Do and Google Tasks backends.

## Prerequisites

### Microsoft To Do
- [ ] Azure app registration created
- [ ] Client ID, Tenant ID, Client Secret obtained
- [ ] API permissions configured (Tasks.ReadWrite)
- [ ] Admin consent granted (if using application mode)
- [ ] Test task list created in Microsoft To Do

### Google Tasks
- [ ] Google Cloud project created
- [ ] OAuth 2.0 credentials created
- [ ] OAuth consent screen configured
- [ ] Test user added (if using External user type)
- [ ] Test task list created in Google Tasks (or plan to use primary)

## Environment Setup

- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] `.env` file configured with appropriate credentials
- [ ] Orgplan directory created with test monthly file
- [ ] Test monthly file has valid TODO List section

## Microsoft To Do Tests

### Authentication - Application Mode

- [ ] Run with application mode: `python tools/sync.py --todo-list "Test List" --dry-run`
- [ ] Verify authentication succeeds
- [ ] Check token cache created: `.tokens/tokens.json`
- [ ] Verify no interactive prompts

### Authentication - Delegated Mode

- [ ] Run with delegated mode: `python tools/sync.py --todo-list "Test List" --auth-mode delegated --dry-run`
- [ ] Verify device code flow starts
- [ ] Open browser and complete authentication
- [ ] Verify tokens cached
- [ ] Run again, verify no re-authentication needed

### Task Sync - Orgplan to Microsoft

- [ ] Add new task in orgplan: `- #p1 Test task from orgplan`
- [ ] Run sync: `python tools/sync.py --todo-list "Test List"`
- [ ] Verify task appears in Microsoft To Do
- [ ] Verify priority is set to "high"
- [ ] Verify `ms-todo-id` marker added to orgplan detail section
- [ ] Update task title in orgplan
- [ ] Run sync again
- [ ] Verify title updated in Microsoft To Do

### Task Sync - Microsoft to Orgplan

- [ ] Add new task in Microsoft To Do app
- [ ] Set importance to "High"
- [ ] Add some notes
- [ ] Run sync: `python tools/sync.py --todo-list "Test List"`
- [ ] Verify task appears in orgplan TODO List
- [ ] Verify priority tag `#p1` added
- [ ] Verify detail section created with notes
- [ ] Verify `ms-todo-id` marker present

### Completion Status Sync

- [ ] Mark task as `[DONE]` in orgplan
- [ ] Run sync
- [ ] Verify task marked completed in Microsoft To Do
- [ ] Mark different task completed in Microsoft To Do
- [ ] Run sync
- [ ] Verify task marked `[DONE]` in orgplan

### Priority Changes

- [ ] Change priority in orgplan: `#p1` → `#p2`
- [ ] Run sync
- [ ] Verify importance changed in Microsoft To Do: High → Normal
- [ ] Change importance in Microsoft To Do: Normal → Low
- [ ] Run sync
- [ ] Verify priority changed in orgplan: `#p2` → `#p3`

## Google Tasks Tests

### Authentication - OAuth Flow

- [ ] Run with Google backend: `python tools/sync.py --backend google --todo-list "Test List" --dry-run`
- [ ] Verify browser opens for OAuth consent
- [ ] Complete OAuth flow and grant permissions
- [ ] Verify authentication succeeds
- [ ] Check tokens cached: `.tokens/google_tokens.json`
- [ ] Run again, verify no re-authentication needed

### Token Refresh

- [ ] Wait or manually expire access token
- [ ] Run sync
- [ ] Verify automatic token refresh works
- [ ] No re-authentication required

### Task Sync - Orgplan to Google

- [ ] Add new task in orgplan: `- Test task for Google`
- [ ] Run sync: `python tools/sync.py --backend google --todo-list "Test List"`
- [ ] Verify task appears in Google Tasks
- [ ] Verify `google-tasks-id` marker added to orgplan detail section
- [ ] Update task title in orgplan
- [ ] Run sync again
- [ ] Verify title updated in Google Tasks

### Task Sync - Google to Orgplan

- [ ] Add new task in Google Tasks app
- [ ] Add some notes to the task
- [ ] Run sync: `python tools/sync.py --backend google --todo-list "Test List"`
- [ ] Verify task appears in orgplan TODO List
- [ ] Verify detail section created with notes
- [ ] Verify `google-tasks-id` marker present
- [ ] Verify NO priority tag added (Google doesn't support)

### Completion Status Sync

- [ ] Mark task as `[DONE]` in orgplan
- [ ] Run sync
- [ ] Verify task marked completed in Google Tasks
- [ ] Mark different task completed in Google Tasks
- [ ] Run sync
- [ ] Verify task marked `[DONE]` in orgplan

### Priority Handling (Google)

- [ ] Add task with priority in orgplan: `- #p1 High priority task`
- [ ] Run sync with Google backend
- [ ] Verify task created in Google Tasks
- [ ] Verify priority tag IGNORED (Google doesn't support priority)
- [ ] Task should not have any importance/priority indicator

### Primary List Default

- [ ] Run sync without specifying list name: `python tools/sync.py --backend google`
- [ ] Verify sync uses primary task list automatically
- [ ] Verify tasks sync correctly

## Multi-Backend Tests

### Both Markers

- [ ] Sync task to Microsoft: `python tools/sync.py --todo-list "Test List"`
- [ ] Verify `ms-todo-id` marker added
- [ ] Sync same task to Google: `python tools/sync.py --backend google --todo-list "Test List"`
- [ ] Verify `google-tasks-id` marker added
- [ ] Verify both markers present in detail section
- [ ] Update task in orgplan
- [ ] Sync to both backends
- [ ] Verify updates appear in both Microsoft and Google

### Backend Isolation

- [ ] Create task with `ms-todo-id` marker only
- [ ] Run sync with Google backend
- [ ] Verify Google creates NEW task (doesn't recognize MS marker)
- [ ] Verify `google-tasks-id` marker added alongside `ms-todo-id`
- [ ] Delete task from Google Tasks
- [ ] Run sync with Microsoft backend
- [ ] Verify Microsoft still finds task by `ms-todo-id`

### Switching Backends

- [ ] Sync with Microsoft: `python tools/sync.py --todo-list "Test List"`
- [ ] Change .env: `TASK_BACKEND=google`
- [ ] Sync with Google: `python tools/sync.py`
- [ ] Verify no duplicate tasks created
- [ ] Verify both sets of markers present
- [ ] Switch back to Microsoft
- [ ] Verify sync still works

## Error Handling Tests

### Authentication Errors

- [ ] Use invalid credentials
- [ ] Verify clear error message
- [ ] Verify sync exits with error code 1

### Network Errors

- [ ] Disconnect network
- [ ] Run sync
- [ ] Verify retry logic triggers
- [ ] Verify exponential backoff
- [ ] Verify eventual failure with clear message

### Invalid Configuration

- [ ] Missing CLIENT_ID
- [ ] Run sync
- [ ] Verify validation error before attempting sync
- [ ] Missing task list name
- [ ] Verify error message lists available lists

### Orgplan Format Errors

- [ ] Create orgplan file without TODO List section
- [ ] Run sync
- [ ] Verify warning message
- [ ] Invalid markdown in TODO List section
- [ ] Verify warning but sync continues

## Automation Tests

### Dry Run Mode

- [ ] Run with `--dry-run` flag
- [ ] Verify no changes made to backend
- [ ] Verify no changes made to orgplan file
- [ ] Verify preview of what would change

### No Prompt Mode (Cron)

Microsoft Delegated:
- [ ] First authenticate interactively
- [ ] Run with `--no-prompt` flag
- [ ] Verify no interactive prompts
- [ ] Verify sync succeeds using cached tokens

Google:
- [ ] First authenticate interactively
- [ ] Run with `--no-prompt` flag
- [ ] Verify no interactive prompts
- [ ] Verify sync succeeds using cached tokens

Both:
- [ ] Delete cached tokens
- [ ] Run with `--no-prompt`
- [ ] Verify sync FAILS with clear error message
- [ ] Error should instruct to run without --no-prompt first

### Lock File

- [ ] Run sync
- [ ] While running, try to run another sync
- [ ] Verify second sync fails with lock error
- [ ] Wait for first sync to complete
- [ ] Verify lock file removed
- [ ] Run sync again successfully

### Logging

- [ ] Run with `--log-file sync.log`
- [ ] Verify log file created
- [ ] Verify log contains timestamps
- [ ] Run with `-v` (verbose)
- [ ] Verify debug-level logging

## Configuration Tests

### Validation Command

- [ ] Run: `python tools/sync.py --validate-config`
- [ ] Verify configuration validated
- [ ] Verify orgplan file validated
- [ ] Verify no sync performed

### Environment Variables

- [ ] Set backend via env: `TASK_BACKEND=google`
- [ ] Run sync without `--backend` flag
- [ ] Verify Google backend used

### Command Line Override

- [ ] Set `TASK_BACKEND=microsoft` in .env
- [ ] Run: `python tools/sync.py --backend google`
- [ ] Verify Google backend used (CLI override)

## Regression Tests (Microsoft)

These ensure Microsoft To Do functionality wasn't broken:

- [ ] All existing Microsoft To Do features work
- [ ] Application mode authentication
- [ ] Delegated mode authentication
- [ ] Task creation
- [ ] Task updates
- [ ] Priority sync (both directions)
- [ ] Completion status sync
- [ ] Detail section sync
- [ ] Task matching by ID
- [ ] Task matching by title (fallback)

## Performance Tests

### Many Tasks

- [ ] Create orgplan file with 50+ tasks
- [ ] Run sync
- [ ] Verify all tasks sync
- [ ] Measure time taken
- [ ] Verify no timeouts
- [ ] Verify statistics accurate

### Large Detail Sections

- [ ] Create task with large detail section (>1000 chars)
- [ ] Run sync
- [ ] Verify detail section syncs
- [ ] Verify no truncation

## Edge Cases

### Special Characters

- [ ] Task with emoji: `- 🚀 Launch project`
- [ ] Task with quotes: `- "Quoted" task`
- [ ] Task with markdown: `- Task with **bold** text`
- [ ] Verify all sync correctly

### Long Titles

- [ ] Create task with very long title (>200 chars)
- [ ] Run sync
- [ ] Verify handling (truncation or error)

### Concurrent Edits

- [ ] Edit task in orgplan
- [ ] Edit same task in backend
- [ ] Run sync
- [ ] Verify orgplan wins (as designed)

### Deleted Tasks

- [ ] Delete task from orgplan TODO List
- [ ] Run sync
- [ ] Verify task NOT deleted from backend (by design)
- [ ] Delete task from backend
- [ ] Run sync
- [ ] Verify task NOT deleted from orgplan (by design)

## Test Results

Document results:

- Date: ___________
- Tester: ___________
- Environment: ___________
- Passed: _____ / _____
- Failed: _____ / _____
- Issues Found: _____

### Issues Log

| Test | Backend | Issue Description | Severity | Status |
|------|---------|-------------------|----------|--------|
|      |         |                   |          |        |

## Sign-Off

- [ ] All critical tests passed
- [ ] All blocking issues resolved
- [ ] Documentation updated with known issues
- [ ] Ready for release

Signed: ___________ Date: ___________
