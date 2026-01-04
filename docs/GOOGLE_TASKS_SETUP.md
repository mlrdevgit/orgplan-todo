# Google Tasks API Setup Guide

This guide walks you through setting up Google Tasks API access for orgplan-todo synchronization.

## Prerequisites

- A Google account (personal or workspace)
- Access to Google Cloud Console

## Step 1: Create Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" at the top
3. Click "New Project"
4. Enter project name (e.g., "Orgplan Todo Sync")
5. Click "Create"
6. Wait for the project to be created and switch to it

## Step 2: Enable Google Tasks API

1. In the left sidebar, go to **APIs & Services > Library**
2. Search for "Google Tasks API"
3. Click on "Google Tasks API"
4. Click **Enable**
5. Wait for the API to be enabled

## Step 3: Configure OAuth Consent Screen

1. In the left sidebar, go to **APIs & Services > OAuth consent screen**
2. Select **External** as the user type (unless using Google Workspace)
3. Click **Create**

### Fill in Required Information:

**App Information:**
- App name: `Orgplan Todo Sync` (or your preferred name)
- User support email: Your email address
- Developer contact email: Your email address

**App Domain** (optional):
- Leave blank for personal use

Click **Save and Continue**

### Scopes:

1. Click **Add or Remove Scopes**
2. Filter for "Google Tasks API"
3. Select: `https://www.googleapis.com/auth/tasks`
4. Click **Update**
5. Click **Save and Continue**

### Test Users (for External apps in testing):

1. Click **Add Users**
2. Add your Google account email
3. Click **Save**
4. Click **Save and Continue**

### Summary:

- Review and click **Back to Dashboard**

## Step 4: Create OAuth 2.0 Credentials

1. In the left sidebar, go to **APIs & Services > Credentials**
2. Click **+ Create Credentials** at the top
3. Select **OAuth client ID**

**Configure:**
- Application type: **Desktop app**
- Name: `Orgplan Sync Client` (or your preferred name)
- Click **Create**

**Important:** A dialog will appear with your credentials. Copy these values:
- **Client ID**: Something like `123456789-abcdefg.apps.googleusercontent.com`
  - This is your `GOOGLE_CLIENT_ID`
- **Client secret**: Something like `GOCSPX-abc123xyz`
  - This is your `GOOGLE_CLIENT_SECRET`

Click **OK** to close the dialog.

**Note:** You can always view these credentials later from the Credentials page.

## Step 5: Create .env File

In your `orgplan-todo` directory, create or update your `.env` file:

```bash
cd orgplan-todo
cp .env.example .env
```

Edit `.env` with your Google credentials:

```env
# Task Backend Selection
TASK_BACKEND=google

# Google Tasks Configuration
GOOGLE_CLIENT_ID=your-actual-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-actual-client-secret

# Google task list name (leave empty for primary list)
GOOGLE_TASK_LIST_NAME=

# Orgplan Configuration
ORGPLAN_DIR=.
TODO_LIST_NAME=
```

## Step 6: Test Authentication

Run a test sync to authenticate:

```bash
python tools/sync.py --backend google --dry-run
```

**What happens:**

1. A browser window will open automatically
2. You'll be prompted to sign in to Google (if not already signed in)
3. Review the permissions requested:
   - **See, edit, create and delete all your Google Tasks**
4. Click **Allow**
5. You may see a warning "Google hasn't verified this app"
   - Click **Advanced**
   - Click **Go to Orgplan Todo Sync (unsafe)**
   - This is safe - it's your own app!
6. After approval, return to the terminal

You should see:
```
✓ Authentication successful!
Tokens have been saved for future use.
```

**Tokens are cached** in `.tokens/google_tokens.json` for future runs.

## Step 7: Specify Task List (Optional)

If you want to sync with a specific Google Tasks list instead of the primary list:

1. Find your task list name in Google Tasks
2. Update `.env`:
   ```env
   GOOGLE_TASK_LIST_NAME=Work Tasks
   ```

Or use CLI:
```bash
python tools/sync.py --backend google --todo-list "Work Tasks"
```

## Troubleshooting

### "Google hasn't verified this app"

**Why this happens:** Google shows this warning for apps in "Testing" mode that haven't gone through their verification process.

**Solution:** This is expected and safe for personal use. Click **Advanced > Go to [App Name] (unsafe)** to continue.

**To remove the warning:** Publish your app (requires verification process), or keep it in Testing mode and add all users as test users.

### "Access blocked: Orgplan Todo Sync has not completed verification"

**Solution:** Make sure you added your email as a test user in Step 3.

### "Invalid client: no application name"

**Solution:** Complete the OAuth consent screen configuration in Step 3.

### "Error 400: redirect_uri_mismatch"

**Solution:** Make sure you selected "Desktop app" as the application type, not "Web application".

### Tokens not refreshing

**Solution:** Delete the tokens and re-authenticate:
```bash
rm -rf .tokens/google_tokens.json
python tools/sync.py --backend google
```

### Cannot find task list

**Solution:** Check available task lists:
```bash
python tools/sync.py --backend google --validate-config
```

This will show all available task lists.

## Security Notes

### Token Storage

- Tokens are stored in `.tokens/google_tokens.json`
- File permissions are set to `0o600` (owner read/write only)
- **Never** commit this file to git (it's in `.gitignore`)

### Credential Security

- Keep your `GOOGLE_CLIENT_SECRET` private
- Don't share or commit your `.env` file
- Rotate credentials if exposed

### Permissions Scope

The app only requests:
- `https://www.googleapis.com/auth/tasks` - Read and write access to Google Tasks

**No access to:**
- Gmail
- Google Calendar
- Google Drive
- Any other Google services

## Automation with Cron

For automated syncs, use the `--no-prompt` flag:

```bash
# Crontab example: sync every hour
0 * * * * cd /path/to/orgplan-todo && python tools/sync.py --backend google --no-prompt --log-file sync.log
```

**Important:** Run an interactive sync at least once before setting up cron to cache the tokens.

If tokens expire while using `--no-prompt`, the script will exit with an error. Run manually without `--no-prompt` to re-authenticate.

## Switching from Microsoft To Do

To switch from Microsoft To Do to Google Tasks:

1. Update `.env`: `TASK_BACKEND=google`
2. Run sync: `python tools/sync.py --backend google`
3. Tasks will be created in Google Tasks with `google-tasks-id` markers
4. Old `ms-todo-id` markers remain in orgplan files but are ignored

**Note:** This creates duplicate tasks. The systems don't automatically migrate. See `docs/BACKEND_MIGRATION.md` for details.

## Additional Resources

- [Google Tasks API Documentation](https://developers.google.com/tasks)
- [OAuth 2.0 for Desktop Apps](https://developers.google.com/identity/protocols/oauth2/native-app)
- [Google Cloud Console](https://console.cloud.google.com/)

## Next Steps

- See `README.md` for usage examples
- See `docs/TROUBLESHOOTING.md` for common issues
- See `docs/WORKFLOWS.md` for automation examples
