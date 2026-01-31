# Backend Migration Guide

This guide explains how to switch between Microsoft To Do and Google Tasks backends, or use both simultaneously.

## Table of Contents

- [Understanding Multiple Backends](#understanding-multiple-backends)
- [Migration Scenarios](#migration-scenarios)
- [ID Marker System](#id-marker-system)
- [Step-by-Step Migration](#step-by-step-migration)
- [Using Both Backends](#using-both-backends)
- [Troubleshooting](#troubleshooting)

## Understanding Multiple Backends

orgplan-todo supports two task backends:

- **Microsoft To Do**: Supports priority sync, application and delegated authentication modes
- **Google Tasks**: OAuth 2.0 authentication, no admin consent required, integrates with Google ecosystem

**Key Features:**
- Tasks can have **both** ID markers (Microsoft and Google)
- Each backend only reads its own marker
- No automatic migration - you control the process
- Switching backends doesn't create duplicates (if markers exist)

## Migration Scenarios

### Scenario 1: Microsoft To Do → Google Tasks

**Why migrate:**
- Prefer Google ecosystem
- Don't need priority support
- Want simpler OAuth setup

**Trade-offs:**
- ❌ Lose priority sync (Google doesn't support)
- ✅ Keep all tasks and completion status
- ✅ Can still use Microsoft To Do alongside

### Scenario 2: Google Tasks → Microsoft To Do

**Why migrate:**
- Need priority support
- Work in enterprise environment
- Want application authentication

**Trade-offs:**
- ✅ Gain priority support
- ✅ Keep all tasks and completion status
- ✅ Can still use Google Tasks alongside

### Scenario 3: Use Both Backends

**Why use both:**
- Different task lists for different purposes
- Work (Microsoft) and Personal (Google)
- Testing or comparison

**Trade-offs:**
- ✅ Full flexibility
- ❌ More complex configuration
- ❌ Two sets of credentials to manage

## ID Marker System

### How ID Markers Work

When a task is synced, an ID marker is added to the detail section:

```markdown
# Task Title

<!-- ms-todo-id: AAMkAGI2THAAA= -->
<!-- google-tasks-id: MTIzNDU2Nzg5... -->

Task details here...
```

**Important:**
- Each backend **only** looks for its own marker
- Multiple markers can coexist peacefully
- Markers ensure no duplicates are created

### Marker Behavior

| Scenario | Microsoft Marker | Google Marker | Result |
|----------|------------------|---------------|--------|
| First sync to MS | Added | None | Task linked to MS To Do |
| First sync to Google | None | Added | Task linked to Google Tasks |
| Sync to both | Added | Added | Task linked to both |
| Switch backends | Existing | New added | Task updates in both |

## Step-by-Step Migration

### From Microsoft To Do to Google Tasks

```bash
# Prerequisites
# 1. Setup Google OAuth credentials (see GOOGLE_TASKS_SETUP.md)
# 2. Add to .env: GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET

# Step 1: Verify current Microsoft sync works
python tools/sync.py --todo-list "Orgplan 2025" --dry-run

# Step 2: Test Google authentication
python tools/sync.py --backend google --dry-run
# Browser will open for OAuth consent

# Step 3: Create task list in Google Tasks
# Open Google Tasks and create a list (or use primary list)

# Step 4: First Google sync (dry run)
python tools/sync.py --backend google --todo-list "Orgplan 2025" --dry-run
# Review what will be created

# Step 5: Perform first Google sync
python tools/sync.py --backend google --todo-list "Orgplan 2025"
# All tasks from orgplan are created in Google Tasks
# Google ID markers added to orgplan

# Step 6: Verify both markers exist
grep -r "google-tasks-id" 2025/12-notes.md
grep -r "ms-todo-id" 2025/12-notes.md

# Step 7: Switch default backend in .env
nano .env
# Change: TASK_BACKEND=google

# Step 8: Update cron job (if using)
crontab -e
# Add: --backend google

# Done! You can now use Google Tasks as primary
# Microsoft To Do still works if you specify --backend microsoft
```

### From Google Tasks to Microsoft To Do

```bash
# Prerequisites
# 1. Setup Azure app registration (see GRAPH_API_SETUP.md)
# 2. Add to .env: MS_CLIENT_ID, MS_TENANT_ID, MS_CLIENT_SECRET (or AUTH_MODE=delegated)

# Step 1: Verify current Google sync works
python tools/sync.py --backend google --dry-run

# Step 2: Test Microsoft authentication
python tools/sync.py --todo-list "Orgplan 2025" --dry-run
# For delegated mode, device code flow will start

# Step 3: Create task list in Microsoft To Do
# Open Microsoft To Do and create list "Orgplan 2025"

# Step 4: First Microsoft sync (dry run)
python tools/sync.py --todo-list "Orgplan 2025" --dry-run
# Review what will be created

# Step 5: Perform first Microsoft sync
python tools/sync.py --todo-list "Orgplan 2025"
# All tasks from orgplan are created in Microsoft To Do
# Microsoft ID markers added to orgplan

# Step 6: Verify both markers exist
grep -r "ms-todo-id" 2025/12-notes.md
grep -r "google-tasks-id" 2025/12-notes.md

# Step 7: Add priorities to tasks (optional)
nano 2025/12-notes.md
# Add #p1, #p2, #p3 tags to tasks
python tools/sync.py --todo-list "Orgplan 2025"

# Step 8: Switch default backend in .env
nano .env
# Change or add: TASK_BACKEND=microsoft

# Step 9: Update cron job (if using)
crontab -e
# Remove or update --backend flag

# Done! You can now use Microsoft To Do as primary
# Google Tasks still works if you specify --backend google
```

## Using Both Backends

### Same Orgplan, Multiple Backends

```bash
# Configuration in .env
TASK_BACKEND=microsoft  # Default backend

# Microsoft To Do
MS_CLIENT_ID=...
MS_TENANT_ID=...
MS_CLIENT_SECRET=...
TODO_LIST_NAME=Orgplan 2025

# Google Tasks
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_TASK_LIST_NAME=Orgplan 2025

# Sync to Microsoft (uses default from .env)
python tools/sync.py --todo-list "Orgplan 2025"

# Sync to Google (override backend)
python tools/sync.py --backend google --todo-list "Orgplan 2025"

# Both services now have the same tasks
# Tasks have both ID markers
```

### Separate Orgplan Directories

```bash
# Work (Microsoft To Do)
python tools/sync.py \
  --orgplan-dir ~/work \
  --todo-list "Work Tasks" \
  --client-id "$MS_CLIENT_ID" \
  --tenant-id "$MS_TENANT_ID" \
  --client-secret "$MS_CLIENT_SECRET"

# Personal (Google Tasks)
python tools/sync.py \
  --backend google \
  --orgplan-dir ~/personal \
  --todo-list "Personal Tasks"

# Separate cron jobs
*/30 * * * * cd ~/work && python ~/orgplan-todo/tools/sync.py --todo-list "Work Tasks" --log-file work-sync.log
*/30 * * * * cd ~/personal && python ~/orgplan-todo/tools/sync.py --backend google --log-file personal-sync.log
```

## Troubleshooting

### Duplicate Tasks Created

**Problem:** Tasks appear twice after migration

**Cause:** ID markers not recognized

**Solution:**
```bash
# 1. Check ID markers in orgplan
grep "ms-todo-id\|google-tasks-id" 2025/12-notes.md

# 2. If markers are missing, delete duplicates in backend
# (manually in To Do or Google Tasks app)

# 3. Sync again - should match by title
python tools/sync.py --backend google --dry-run
```

### Priority Tags Not Syncing

**Problem:** Priority tags (#p1, #p2, #p3) not appearing in Google Tasks

**Explanation:** This is expected - Google Tasks doesn't support priority

**Options:**
1. Accept that priorities only work with Microsoft To Do
2. Use Microsoft To Do if you need priorities
3. Encode priorities in task title (e.g., "[P1] Task name")

### Tasks Out of Sync

**Problem:** Changes in one backend don't appear in the other

**Cause:** Each backend operates independently

**Solution:**
```bash
# Sync to both backends
python tools/sync.py --todo-list "Orgplan 2025"  # Microsoft
python tools/sync.py --backend google --todo-list "Orgplan 2025"  # Google

# Orgplan is the source of truth
# Both backends receive updates from orgplan
```

### Authentication Conflicts

**Problem:** Switching backends causes auth errors

**Cause:** Cached credentials for wrong backend

**Solution:**
```bash
# Microsoft: Clear token cache
rm -rf .tokens/tokens.json

# Google: Clear OAuth tokens
rm -rf .tokens/google_tokens.json

# Re-authenticate
python tools/sync.py --backend microsoft --todo-list "Orgplan 2025"
python tools/sync.py --backend google --todo-list "My Tasks"
```

### Markers Not Appearing

**Problem:** ID markers not added to detail sections

**Cause:** Detail section doesn't exist or has wrong format

**Solution:**
```markdown
# Ensure each task has a detail section:

# TODO List

- Task title

# Task title

<!-- ID marker will be added here by sync -->

Task details...
```

## Best Practices

### Migration Checklist

- [ ] Backup orgplan files before migration
- [ ] Test with --dry-run first
- [ ] Verify authentication works for new backend
- [ ] Create target task list in new backend
- [ ] Perform migration during low-activity period
- [ ] Verify ID markers are added
- [ ] Test round-trip sync (orgplan → backend → orgplan)
- [ ] Update cron jobs if using automation

### When to Use Multiple Backends

**Good use cases:**
- Work and personal separation
- Testing new backend
- Gradual migration
- Team uses Microsoft, personal uses Google

**Avoid if:**
- Increases complexity without benefit
- Only need one task management system
- Priority support is critical everywhere

### Maintaining Both Backends

If using both:

1. **Pick a primary:** One backend as source of truth
2. **Sync order:** Sync to orgplan first, then to both backends
3. **Monitoring:** Check both backends occasionally for sync errors
4. **Credentials:** Keep both sets of credentials updated

## Advanced Scenarios

### Gradual Migration

```bash
# Week 1: Add Google Tasks alongside Microsoft
python tools/sync.py --backend google --todo-list "Orgplan 2025"
# Use both, verify Google works

# Week 2: Use Google as primary for new tasks
# Add new tasks in Google Tasks
python tools/sync.py --backend google

# Week 3: Transition cron jobs
# Update automation to use Google
crontab -e
# Change to: --backend google

# Week 4: Keep Microsoft as backup
# Still sync occasionally
python tools/sync.py --todo-list "Orgplan 2025"
```

### Emergency Rollback

```bash
# If migration to Google has issues:

# 1. Stop syncing to Google
# (Remove from cron, stop manual syncs)

# 2. Revert to Microsoft To Do
python tools/sync.py --todo-list "Orgplan 2025"

# 3. Clean up Google Tasks if needed
# (Delete tasks manually in Google Tasks)

# 4. Remove Google markers if desired
# (Manual edit or script to remove <!-- google-tasks-id: ... --> lines)
```

## Getting Help

For backend-specific issues:
- Microsoft To Do: See [GRAPH_API_SETUP.md](GRAPH_API_SETUP.md)
- Google Tasks: See [GOOGLE_TASKS_SETUP.md](GOOGLE_TASKS_SETUP.md)
- General issues: See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
