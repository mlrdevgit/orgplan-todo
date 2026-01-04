# Troubleshooting Guide

This guide helps you diagnose and fix common issues with orgplan-todo sync.

## Table of Contents

- [Configuration Issues](#configuration-issues)
- [Authentication Issues](#authentication-issues)
- [Sync Issues](#sync-issues)
- [File Format Issues](#file-format-issues)
- [Lock File Issues](#lock-file-issues)
- [Network Issues](#network-issues)
- [Performance Issues](#performance-issues)

## Configuration Issues

### "Configuration errors: Microsoft Client ID is required"

**Symptoms:**
```
Configuration errors:
  - Microsoft Client ID is required
  - Microsoft Tenant ID is required
  - Microsoft Client Secret is required
```

**Cause:** Missing or incomplete `.env` file

**Solution:**
```bash
# Copy example file
cp .env.example .env

# Edit with your credentials
nano .env  # or your preferred editor
```

See [Graph API Setup Guide](GRAPH_API_SETUP.md) for obtaining credentials.

### "Orgplan file does not exist"

**Symptoms:**
```
Configuration errors:
  - Orgplan file for 2025-12 does not exist: /path/to/2025/12-notes.md
```

**Cause:** Monthly notes file hasn't been created yet

**Solution:**
```bash
# Create the directory structure
mkdir -p 2025

# Create the notes file with TODO List section
cat > 2025/12-notes.md << 'EOF'
# TODO List

- Example task

# Example task

This is a detail section for the task.
EOF
```

### "Invalid month format"

**Symptoms:**
```
Configuration errors:
  - Invalid month format: 2025-13 (expected YYYY-MM)
```

**Cause:** Month specified with `--month` is invalid

**Solution:**
```bash
# Use correct format: YYYY-MM
python tools/sync.py --todo-list "Orgplan 2025" --month 2025-12
```

## Authentication Issues

### Delegated Authentication Issues

#### "Authentication required but interactive prompt is disabled (--no-prompt)"

**Symptoms:**
```
Exception: Authentication required but interactive prompt is disabled (--no-prompt).
Run sync manually without --no-prompt to authenticate.
```

**Cause:** Using `--no-prompt` flag (for cron) but tokens have expired or don't exist

**Solution:**
```bash
# First, authenticate interactively without --no-prompt
python tools/sync.py --todo-list "Orgplan 2025" --auth-mode delegated --dry-run

# After successful login, cron jobs with --no-prompt will work
```

#### "Device code expired"

**Symptoms:**
```
Authentication failed: AADSTS50126: Error validating credentials
```

**Cause:** Took too long to enter device code (timeout is typically 15 minutes)

**Solution:**
- Run the sync command again
- Complete the authentication within 15 minutes
- Browser should open automatically - if not, manually open the URL shown

#### "Cached token expired, refresh failed"

**Symptoms:**
```
WARNING: Failed to refresh token, interactive login required
```

**Cause:** Refresh token has expired (typically after 90 days of inactivity)

**Solution:**
```bash
# Delete old tokens and re-authenticate
rm -rf .tokens/
python tools/sync.py --todo-list "Orgplan 2025" --auth-mode delegated
```

#### Token permission denied

**Symptoms:**
```
PermissionError: [Errno 13] Permission denied: '.tokens/tokens.json'
```

**Cause:** Incorrect file permissions on token storage

**Solution:**
```bash
# Fix permissions
chmod 700 .tokens/
chmod 600 .tokens/tokens.json

# Or remove and re-authenticate
rm -rf .tokens/
python tools/sync.py --todo-list "Orgplan 2025" --auth-mode delegated
```

### Application Authentication Issues (Microsoft)

### "Authentication failed: AADSTS700016"

**Symptoms:**
```
Authentication failed: AADSTS700016: Application with identifier 'xxx' was not found
```

**Cause:** Incorrect Client ID or Tenant ID

**Solution:**
1. Go to Azure Portal > App registrations
2. Find your application
3. Copy the correct Application (client) ID and Directory (tenant) ID
4. Update `.env` file
5. Verify no extra spaces or quotes

### "Authentication failed: AADSTS7000215"

**Symptoms:**
```
Authentication failed: AADSTS7000215: Invalid client secret provided
```

**Cause:** Incorrect or expired client secret

**Solution:**
1. Go to Azure Portal > App registrations > Your app
2. Click "Certificates & secrets"
3. Create a new client secret
4. Copy the Value immediately
5. Update `MS_CLIENT_SECRET` in `.env`

### "API request failed: 403 - Forbidden"

**Symptoms:**
```
API request failed: 403 - {"error": {"code": "Forbidden", "message": "Insufficient privileges"}}
```

**Cause:** Missing or not consented API permissions

**Solution:**
1. Go to Azure Portal > App registrations > Your app
2. Click "API permissions"
3. Ensure "Tasks.ReadWrite" is present
4. Click "Grant admin consent"
5. Wait a few minutes for changes to propagate

### Google Tasks Authentication Issues

#### "Authentication required but interactive prompt is disabled" (Google)

**Symptoms:**
```
Exception: Authentication required but interactive prompt is disabled (--no-prompt).
Run sync manually without --no-prompt to authenticate.
```

**Cause:** Using `--no-prompt` flag but Google OAuth tokens don't exist or have expired

**Solution:**
```bash
# First, authenticate interactively without --no-prompt
python tools/sync.py --backend google --todo-list "My Tasks"

# Follow the OAuth flow in your browser
# After successful login, cron jobs with --no-prompt will work
```

#### "Failed to refresh token" (Google)

**Symptoms:**
```
WARNING: Failed to refresh token: invalid_grant
```

**Cause:** Refresh token has expired or been revoked

**Solution:**
```bash
# Delete old tokens and re-authenticate
rm -rf .tokens/google_tokens.json
python tools/sync.py --backend google --todo-list "My Tasks"
```

#### "Invalid client_id or client_secret" (Google)

**Symptoms:**
```
Authentication failed: invalid_client
```

**Cause:** Incorrect Google OAuth credentials

**Solution:**
1. Go to Google Cloud Console > APIs & Services > Credentials
2. Find your OAuth 2.0 Client ID
3. Verify the Client ID and Client Secret
4. Update `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in `.env`
5. Ensure no extra spaces or quotes

#### "Access blocked: Authorization Error" (Google)

**Symptoms:**
```
This app is blocked
This app tried to access sensitive info in your Google Account
```

**Cause:** OAuth consent screen not configured or app not verified

**Solution:**
1. Go to Google Cloud Console > APIs & Services > OAuth consent screen
2. Ensure consent screen is configured
3. For personal use, set "User type" to "External"
4. Add your email as a test user
5. No verification required for personal use with test users

#### "insufficient_scope" (Google)

**Symptoms:**
```
API request failed: 403 - insufficient authentication scopes
```

**Cause:** Missing required OAuth scopes

**Solution:**
1. Delete cached tokens: `rm -rf .tokens/google_tokens.json`
2. Re-authenticate to request proper scopes
3. Ensure `https://www.googleapis.com/auth/tasks` scope is included

#### Browser doesn't open for OAuth (Google)

**Symptoms:** No browser window opens during authentication

**Solution:**
1. The script will print a URL - copy and paste it into your browser
2. Or manually open: `http://localhost:XXXXX` (shown in console)
3. Complete the OAuth flow
4. Grant permissions when prompted

#### "redirect_uri_mismatch" (Google)

**Symptoms:**
```
Error 400: redirect_uri_mismatch
```

**Cause:** OAuth client not configured for local redirect

**Solution:**
1. Go to Google Cloud Console > Credentials > Your OAuth Client
2. Under "Authorized redirect URIs", add:
   - `http://localhost`
   - `urn:ietf:wg:oauth:2.0:oob`
3. Save and wait a few minutes for changes to propagate

## Sync Issues

### "Task list not found"

**Symptoms:**
```
Task list 'Orgplan 2025' not found
Available lists:
  - Tasks
  - Work Tasks
```

**Cause:** List name doesn't match or doesn't exist

**Solution:**

**Microsoft To Do:**

**Option 1:** Use existing list
```bash
python tools/sync.py --todo-list "Tasks"
```

**Option 2:** Create the list
1. Open Microsoft To Do app (web, desktop, or mobile)
2. Click "+ New list"
3. Name it exactly "Orgplan 2025"
4. Run sync again

**Google Tasks:**

**Option 1:** Use existing list
```bash
python tools/sync.py --backend google --todo-list "My Tasks"
```

**Option 2:** Use primary list (default)
```bash
# If no list name specified, uses primary list
python tools/sync.py --backend google
```

**Option 3:** Create a new list
1. Open Google Tasks (web, mobile, or Gmail sidebar)
2. Click the current list name dropdown
3. Click "Create new list"
4. Name it and sync with that name

**Note:** List names are case-sensitive for both backends!

### "Another sync is already running"

**Symptoms:**
```
ERROR: Another sync is already running. Lock file: /path/to/sync.lock
ERROR: If no other sync is running, remove: /path/to/sync.lock
```

**Cause:** Lock file exists from previous run

**Solutions:**

**If sync IS running:**
- Wait for it to complete
- Check with: `ps aux | grep sync.py`

**If sync is NOT running:**
```bash
# Remove stale lock file
rm sync.lock

# Or let the script auto-clean (locks >1 hour old are auto-removed)
```

### "Sync completed with errors"

**Symptoms:**
```
Sync completed!
Total:
  Created:  3
  Updated:  5
  Errors:   2
```

**Cause:** Some tasks failed to sync

**Solution:**
1. Run with verbose logging:
   ```bash
   python tools/sync.py --todo-list "Orgplan 2025" -v
   ```
2. Check log file for specific errors:
   ```bash
   tail -n 50 sync.log
   ```
3. Common error causes:
   - Malformed task descriptions
   - Very long task titles (>255 chars)
   - Special characters causing issues
   - Network timeouts

## File Format Issues

### "Orgplan file format warnings: File is missing '# TODO List' section"

**Symptoms:**
```
WARNING: Orgplan file format warnings:
WARNING:   - File is missing '# TODO List' section
```

**Cause:** Monthly notes file doesn't have required header

**Solution:**
```bash
# Add TODO List section to your file
cat >> 2025/12-notes.md << 'EOF'

# TODO List

- First task
- Second task
EOF
```

### "Malformed task line"

**Symptoms:**
```
WARNING:   - Line 15: TODO List section should only contain task items (starting with '- ')
```

**Cause:** Non-task content in TODO List section

**Solution:**

**Before (incorrect):**
```markdown
# TODO List

- Task 1
Some random text here  ← Problem
- Task 2
```

**After (correct):**
```markdown
# TODO List

- Task 1
- Task 2

# Notes Section

Some random text can go in other sections
```

## Lock File Issues

### Lock File Won't Release

**Symptoms:** Lock file persists even though no sync is running

**Diagnostic:**
```bash
# Check if sync is actually running
ps aux | grep sync.py

# Check lock file age
ls -lh sync.lock

# View lock file contents
cat sync.lock
```

**Solution:**

**Manual removal:**
```bash
rm sync.lock
```

**Auto-cleanup:** Locks older than 1 hour are automatically removed

### Concurrent Syncs Interfering

**Symptoms:** Multiple cron jobs trying to run simultaneously

**Cause:** Cron schedule too frequent or sync taking too long

**Solution:**

**Option 1:** Increase cron interval
```bash
# Change from every 15 minutes to every 30
*/30 * * * * cd ~/orgplan && python tools/sync.py --todo-list "Orgplan 2025" --log-file sync.log
```

**Option 2:** Check sync duration
```bash
# Add timing to your cron job
*/15 * * * * cd ~/orgplan && time python tools/sync.py --todo-list "Orgplan 2025" --log-file sync.log 2>&1
```

## Network Issues

### "Request timed out"

**Symptoms:**
```
NetworkError: Request timed out: HTTPSConnectionPool...
```

**Cause:** Network connectivity issues or slow API response

**Solution:**
- Check internet connection
- The script automatically retries with backoff
- If persistent, check service status:
  - Microsoft: [Microsoft Service Health](https://portal.office.com/servicestatus)
  - Google: [Google Workspace Status](https://www.google.com/appsstatus)
- Network timeouts are handled automatically with retry logic

### "Connection failed"

**Symptoms:**
```
NetworkError: Connection failed: [Errno 11001] getaddrinfo failed
```

**Cause:** DNS or network connectivity issue

**Solution:**
1. Check internet connection:
   ```bash
   # For Microsoft To Do
   ping graph.microsoft.com

   # For Google Tasks
   ping www.googleapis.com
   ```
2. Check firewall settings
3. Verify proxy configuration if behind corporate firewall
4. Wait and retry - may be transient

### Retry Logic Exhausted

**Symptoms:**
```
WARNING: Attempt 1/4 failed: Server error 503. Retrying in 1.0s...
WARNING: Attempt 2/4 failed: Server error 503. Retrying in 2.0s...
WARNING: Attempt 3/4 failed: Server error 503. Retrying in 4.0s...
ERROR: All 4 attempts failed
```

**Cause:** Microsoft API temporarily unavailable

**Solution:**
- This is normal for transient issues
- Wait a few minutes and retry
- Check [Microsoft Service Health](https://portal.office.com/servicestatus)
- If persistent, may be rate limiting

## Performance Issues

### Sync Takes Very Long

**Symptoms:** Sync takes several minutes to complete

**Diagnostic:**
```bash
# Run with verbose logging to see what's slow
python tools/sync.py --todo-list "Orgplan 2025" -v --log-file debug.log

# Check task counts
grep "Found.*tasks" debug.log
```

**Common Causes:**
- Many tasks (>100) in orgplan or To Do
- Network latency
- API rate limiting

**Solutions:**
1. **Archive old tasks:**
   - Move completed tasks to archive section
   - Keep only active tasks in TODO List

2. **Optimize network:**
   - Run from server with good connectivity
   - Avoid running over VPN if possible

3. **Check for rate limiting:**
   - Reduce cron frequency if hitting limits
   - Space out multiple orgplan syncs

### High API Call Volume

**Symptoms:** Getting rate limited frequently

**Solutions:**
1. Reduce sync frequency:
   ```bash
   # Change from every 15 min to hourly
   0 * * * * cd ~/orgplan && python tools/sync.py --todo-list "Orgplan 2025" --log-file sync.log
   ```

2. Use dry-run for testing:
   ```bash
   python tools/sync.py --todo-list "Orgplan 2025" --dry-run
   ```

## Debugging Tips

### Enable Verbose Logging

```bash
python tools/sync.py --todo-list "Orgplan 2025" -v --log-file debug.log
```

### Check Configuration

```bash
# Verify .env file loads correctly
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print('Client ID:', os.getenv('MS_CLIENT_ID')[:10]  + '...')"
```

### Test Authentication Only

```bash
# Quick test to verify credentials
python tools/sync.py --todo-list "Orgplan 2025" --dry-run
```

### Inspect Lock File

```bash
cat sync.lock
# Shows: PID and start time of locking process
```

### View Recent Logs

```bash
# Last 50 lines of log
tail -n 50 sync.log

# Follow log in real-time
tail -f sync.log

# Search for errors
grep ERROR sync.log
```

## Getting Help

If you've tried the above and still have issues:

1. **Gather information:**
   ```bash
   # Run sync with verbose logging
   python tools/sync.py --todo-list "YourList" -v --log-file debug.log 2>&1

   # Check Python version
   python --version

   # Check installed packages
   pip list | grep -E "msal|requests|dotenv"
   ```

2. **Create a GitHub issue** with:
   - Operating system and Python version
   - Complete error message (redact credentials!)
   - Steps to reproduce
   - Relevant log excerpts
   - What you've already tried

3. **Before posting:**
   - Redact all credentials and IDs
   - Check existing issues for similar problems
   - Include the output from step 1

## Quick Reference

Common commands for troubleshooting:

```bash
# Test with dry-run
python tools/sync.py --todo-list "Orgplan 2025" --dry-run

# Verbose logging
python tools/sync.py --todo-list "Orgplan 2025" -v

# Check if sync is running
ps aux | grep sync.py

# Remove lock file
rm sync.lock

# View recent logs
tail -f sync.log

# Check .env file (without showing secrets)
head -n 3 .env

# Test authentication
python -c "from tools.config import load_config_from_env; c=load_config_from_env(); print('Config OK' if c['client_id'] else 'Missing config')"
```
