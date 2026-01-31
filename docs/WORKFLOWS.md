# Example Workflows

This guide shows common workflows and usage patterns for orgplan-todo sync.

## Table of Contents

- [Backend Selection](#backend-selection)
- [First-Time Setup](#first-time-setup)
- [Daily Workflows](#daily-workflows)
- [Monthly Workflows](#monthly-workflows)
- [Troubleshooting Workflows](#troubleshooting-workflows)
- [Advanced Workflows](#advanced-workflows)

## Backend Selection

This tool supports two backends: **Microsoft To Do** and **Google Tasks**.

### Choosing a Backend

**Microsoft To Do:**
- ✅ Supports priority (High/Normal/Low)
- ✅ Two authentication modes (Application/Delegated)
- ✅ Good for enterprise environments
- ❌ Requires Azure app registration

**Google Tasks:**
- ✅ Simple OAuth setup
- ✅ Personal Google account friendly
- ✅ No admin consent required
- ❌ No priority support

### Configuration

**Microsoft To Do:**
```bash
# In .env file
TASK_BACKEND=microsoft
MS_CLIENT_ID=your_client_id
MS_TENANT_ID=your_tenant_id
MS_CLIENT_SECRET=your_secret  # For application mode
TODO_LIST_NAME=Orgplan 2025
```

**Google Tasks:**
```bash
# In .env file
TASK_BACKEND=google
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_TASK_LIST_NAME=My Tasks
```

## First-Time Setup

### Complete Setup from Scratch

```bash
# 1. Clone the repository
git clone https://github.com/mlrdevgit/orgplan-todo.git
cd orgplan-todo

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create orgplan directory structure
mkdir -p 2025

# 4. Create first monthly file
cat > 2025/12-notes.md << 'EOF'
# TODO List

- Setup orgplan-todo sync
- Review project documentation
- Plan weekly goals

# Setup orgplan-todo sync

Steps to get started with syncing.

# Review project documentation

Read through README and understand the system.

# Plan weekly goals

Define goals for the upcoming week.
EOF

# 5. Setup your backend credentials:
#    - Microsoft To Do: see GRAPH_API_SETUP.md
#    - Google Tasks: see GOOGLE_TASKS_SETUP.md

# 6. Configure .env file
cp .env.example .env
nano .env  # Add your credentials

# 7. Validate configuration
python tools/sync.py --validate-config

# 8. First sync (dry-run)
python tools/sync.py --todo-list "Orgplan 2025" --dry-run

# 9. First real sync
python tools/sync.py --todo-list "Orgplan 2025"

# 10. Setup automated sync
TODO_LIST_NAME="Orgplan 2025" SCHEDULE="*/30 * * * *" tools/setup_cron.sh
```

### Complete Setup with Google Tasks

```bash
# 1. Clone the repository
git clone https://github.com/mlrdevgit/orgplan-todo.git
cd orgplan-todo

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create orgplan directory structure
mkdir -p 2025

# 4. Create first monthly file
cat > 2025/12-notes.md << 'EOF'
# TODO List

- Setup orgplan-todo sync
- Review project documentation
- Plan weekly goals
EOF

# 5. Setup Google OAuth (see GOOGLE_TASKS_SETUP.md)
# Follow the guide to get OAuth credentials from Google Cloud Console

# 6. Configure .env file
cp .env.example .env
nano .env  # Add: TASK_BACKEND=google, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET

# 7. Validate configuration
python tools/sync.py --validate-config

# 8. First sync (interactive authentication)
python tools/sync.py --backend google --todo-list "My Tasks"
# Browser will open for OAuth consent

# 9. Subsequent syncs (uses cached tokens)
python tools/sync.py --backend google

# 10. Setup automated sync
# Create a cron job with --backend google --no-prompt
```

## Daily Workflows

### Morning Routine

```bash
# 1. Update tasks in orgplan
nano 2025/12-notes.md

# Add new tasks:
- [ ] Review emails
- [ ] Team standup meeting
- [ ] Complete project proposal

# 2. Sync to your task backend
python tools/sync.py --todo-list "Orgplan 2025"
# Or for Google Tasks:
# python tools/sync.py --backend google --todo-list "My Tasks"

# 3. Check your task app on mobile/desktop
# Tasks are now available on all devices
```

### Evening Routine

```bash
# 1. Mark tasks complete in your task app
# (Throughout the day on any device)

# 2. Sync back to orgplan
python tools/sync.py --todo-list "Orgplan 2025"

# 3. Review progress
cat 2025/12-notes.md | grep "\[DONE\]"

# 4. Plan tomorrow
nano 2025/12-notes.md
# Add tasks for tomorrow
```

### Quick Task Addition

**From Command Line:**
```bash
# Add task to orgplan
echo "- #p1 Call dentist for appointment" >> 2025/12-notes.md

# Sync immediately
python tools/sync.py --todo-list "Orgplan 2025"

# Task appears in To Do within seconds
```

**From Microsoft To Do App:**
```
1. Open Microsoft To Do
2. Add task: "Buy groceries"
3. Set importance: High
4. Wait for next sync (or run manually)
5. Task appears in orgplan with #p1 priority
```

**From Google Tasks App:**
```
1. Open Google Tasks (web, Gmail sidebar, or mobile app)
2. Add task: "Buy groceries"
3. (No priority - Google Tasks doesn't support it)
4. Wait for next sync (or run manually)
5. Task appears in orgplan without priority tag
```

## Monthly Workflows

### Month-End Transition

```bash
# Current: December 2025 (2025/12-notes.md)
# Starting: January 2026

# 1. Create new month file
cat > 2026/01-notes.md << 'EOF'
# TODO List

EOF

# 2. Review last month's incomplete tasks
grep -v "\[DONE\]" 2025/12-notes.md | grep "^- "

# 3. Copy active tasks to new month (manually or script)
# Only copy tasks you want to continue

# 4. Update sync to use new month
python tools/sync.py --todo-list "Orgplan 2026" --month 2026-01

# 5. Verify sync
python tools/sync.py --todo-list "Orgplan 2026" --dry-run

# 6. Update cron job for new year (if needed)
TODO_LIST_NAME="Orgplan 2026" tools/setup_cron.sh
```

### Archive Old Tasks

```bash
# Archive completed tasks from current month
cat 2025/12-notes.md | grep "\[DONE\]" >> 2025/archive.md

# Remove from active file (manual edit)
# Keep only active tasks in TODO List section
```

### Monthly Review

```bash
# Generate monthly stats
echo "Tasks completed in December:"
grep "\[DONE\]" 2025/12-notes.md | wc -l

# By priority
echo "P1 tasks completed:"
grep "\[DONE\].*#p1" 2025/12-notes.md | wc -l

# Export for analysis
grep "^- " 2025/12-notes.md > december-tasks.txt
```

## Troubleshooting Workflows

### Verify Everything is Working

```bash
# 1. Validate configuration
python tools/sync.py --validate-config

# 2. Test authentication
python tools/sync.py --todo-list "Orgplan 2025" --dry-run -v

# 3. Check To Do list exists
# Should show "Found list: Orgplan 2025"

# 4. Verify orgplan file
python -c "from pathlib import Path; print('File exists:', Path('2025/12-notes.md').exists())"

# 5. Check for lock file issues
ls -la sync.lock 2>/dev/null || echo "No lock file (good)"
```

### Recover from Sync Issues

```bash
# 1. Check recent logs
tail -n 100 sync.log | less

# 2. Run with verbose logging
python tools/sync.py --todo-list "Orgplan 2025" -v --log-file debug.log

# 3. Review errors
grep ERROR debug.log

# 4. If lock file stuck
rm sync.lock
python tools/sync.py --todo-list "Orgplan 2025"

# 5. Validate and retry
python tools/sync.py --validate-config
python tools/sync.py --todo-list "Orgplan 2025"
```

### Fix Mismatched Tasks

```bash
# Scenario: Task title changed in both systems

# 1. Check current state
python tools/sync.py --todo-list "Orgplan 2025" --dry-run -v

# 2. Manually align
# Option A: Update in orgplan, sync to To Do
# Option B: Update in To Do, sync to orgplan

# 3. Force title to match
# Edit orgplan to match To Do exactly
# Or edit To Do to match orgplan

# 4. Sync
python tools/sync.py --todo-list "Orgplan 2025"
```

## Advanced Workflows

### Switching Between Backends

```bash
# Current setup: Microsoft To Do
# Want to try: Google Tasks

# 1. Add Google credentials to .env
nano .env
# Add: GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET

# 2. Test Google Tasks (dry run)
python tools/sync.py --backend google --dry-run

# 3. First sync with Google (interactive auth)
python tools/sync.py --backend google --todo-list "My Tasks"

# 4. Tasks will get both ID markers:
# <!-- ms-todo-id: AAMkAGI2T... -->
# <!-- google-tasks-id: MTIzNDU2... -->

# 5. Switch backends anytime
python tools/sync.py --backend microsoft  # Use Microsoft
python tools/sync.py --backend google     # Use Google

# Note: Priority tags only sync with Microsoft To Do
```

### Multiple Orgplan Setups

```bash
# Personal and Work separation

# Personal
python tools/sync.py \
  --orgplan-dir ~/personal \
  --todo-list "Personal 2025" \
  --log-file personal-sync.log

# Work
python tools/sync.py \
  --orgplan-dir ~/work \
  --todo-list "Work 2025" \
  --log-file work-sync.log

# Setup separate cron jobs
TODO_LIST_NAME="Personal 2025" ORGPLAN_DIR=~/personal tools/setup_cron.sh
TODO_LIST_NAME="Work 2025" ORGPLAN_DIR=~/work tools/setup_cron.sh
```

### Batch Operations

```bash
# Add multiple tasks at once
cat >> 2025/12-notes.md << 'EOF'
- #p1 #2h Review Q4 metrics
- #p2 Schedule team 1-on-1s
- #p2 Update project roadmap
- #p3 Clean up email inbox
EOF

# Sync all at once
python tools/sync.py --todo-list "Orgplan 2025"
```

### Custom Integration Scripts

**Example: Add task from command line**
```bash
#!/bin/bash
# add-task.sh - Quick task addition

TASK="$*"
MONTH=$(date +%Y-%m)
FILE="$(date +%Y)/${MONTH:5}-notes.md"

echo "- $TASK" >> "$FILE"
python tools/sync.py --todo-list "Orgplan 2025"
echo "✓ Task added and synced: $TASK"
```

Usage:
```bash
chmod +x add-task.sh
./add-task.sh "#p1 Call client about proposal"
```

**Example: Daily summary**
```bash
#!/bin/bash
# daily-summary.sh - Show today's completions

MONTH=$(date +%Y-%m)
FILE="$(date +%Y)/${MONTH:5}-notes.md"

echo "Tasks completed today:"
grep "\[DONE\]" "$FILE"

echo ""
echo "Remaining tasks:"
grep "^- " "$FILE" | grep -v "\[DONE\]"
```

### Selective Sync

```bash
# Only sync high-priority tasks (requires modification)
# Feature for future: filter by priority

# Workaround: temporary orgplan files
# 1. Create filtered view
grep "#p1" 2025/12-notes.md > 2025/12-priority.md

# 2. Sync filtered view
python tools/sync.py --orgplan-dir ./filtered --todo-list "Priority Tasks"
```

### Backup Strategy

```bash
#!/bin/bash
# backup-orgplan.sh - Daily backup

BACKUP_DIR=~/backups/orgplan
DATE=$(date +%Y-%m-%d)

mkdir -p "$BACKUP_DIR"
tar -czf "$BACKUP_DIR/orgplan-$DATE.tar.gz" 2025/ 2026/

# Keep last 30 days
find "$BACKUP_DIR" -name "orgplan-*.tar.gz" -mtime +30 -delete

echo "✓ Backup created: orgplan-$DATE.tar.gz"
```

Add to cron:
```bash
0 2 * * * ~/orgplan-todo/backup-orgplan.sh
```

### Migration to New System

```bash
# Export all tasks to CSV
cat 2025/*.md | grep "^- " | sed 's/^- //' > all-tasks.csv

# Import to new system (manual process)
# Or create custom import script

# Verify nothing lost
wc -l all-tasks.csv
```

## Best Practices

### Task Organization

**Good:**
```markdown
# TODO List

- #p1 #2h Complete project proposal
- #p1 Review Q4 budget
- #p2 Update team documentation
- #p3 Clean desk

# Complete project proposal

## Sections needed
- Executive summary
- Technical approach
- Timeline and milestones
```

**Avoid:**
```markdown
# TODO List

- do stuff
- things!
- remember to...
```

### Sync Frequency

**Recommendations:**
- **High activity**: Every 15-30 minutes
- **Normal usage**: Every 30-60 minutes
- **Low activity**: Every 2-4 hours

**Balance:**
- More frequent = better sync
- Less frequent = fewer API calls

### Error Recovery

Always have these ready:
```bash
# Quick validation
python tools/sync.py --validate-config

# Safe sync
python tools/sync.py --todo-list "Orgplan 2025" --dry-run

# Full sync with logging
python tools/sync.py --todo-list "Orgplan 2025" -v --log-file recovery.log
```

## Getting Help

See also:
- [Troubleshooting Guide](TROUBLESHOOTING.md)
- [Microsoft To Do Setup](GRAPH_API_SETUP.md)
- [Google Tasks Setup](GOOGLE_TASKS_SETUP.md)
- [Backend Migration Guide](BACKEND_MIGRATION.md)
- [Main README](../README.md)
