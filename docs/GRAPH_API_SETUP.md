# Microsoft Graph API Setup Guide

This guide walks you through setting up a Microsoft Azure AD application for accessing Microsoft To Do via the Graph API.

## Prerequisites

- A Microsoft account (personal or work/school)
- Access to Azure Portal
- Administrator privileges (for some steps)

## Step 1: Create Azure AD Application

1. Go to the [Azure Portal](https://portal.azure.com/)
2. Sign in with your Microsoft account
3. Navigate to **Azure Active Directory**
   - Use the search bar at the top or find it in the left sidebar
4. Click on **App registrations** in the left menu
5. Click **+ New registration**

### Application Registration Details

- **Name**: Choose a descriptive name (e.g., "Orgplan To Do Sync")
- **Supported account types**: Select one of:
  - **Accounts in this organizational directory only** (single tenant) - Work/school accounts only
  - **Accounts in any organizational directory** (multi-tenant) - Any work/school account
  - **Accounts in any organizational directory and personal Microsoft accounts** - Recommended for personal use
- **Redirect URI**: Leave blank (not needed for this application)

6. Click **Register**

## Step 2: Note Your Application IDs

After registration, you'll see the application overview page.

**Copy these values** (you'll need them for `.env` file):

1. **Application (client) ID**
   - This is your `MS_CLIENT_ID`
   - Example format: `12345678-1234-1234-1234-123456789abc`

2. **Directory (tenant) ID**
   - This is your `MS_TENANT_ID`
   - Example format: `87654321-4321-4321-4321-cba987654321`

## Step 3: Create Client Secret

1. In the left menu, click **Certificates & secrets**
2. Click **+ New client secret**
3. Add a description (e.g., "Orgplan sync secret")
4. Choose an expiration period:
   - **Recommended**: 24 months
   - You'll need to create a new secret before it expires
5. Click **Add**

**IMPORTANT**: Copy the secret **Value** immediately!
- This is your `MS_CLIENT_SECRET`
- You cannot view it again after leaving this page
- Example format: `abc123~XyZ789.qwerty_ASDFGH-123456`

## Step 4: Configure API Permissions

1. In the left menu, click **API permissions**
2. Click **+ Add a permission**
3. Select **Microsoft Graph**
4. Select **Application permissions** (not Delegated permissions)
5. Search for and select these permissions:
   - **Tasks.ReadWrite** - Read and write tasks and task lists
6. Click **Add permissions**

### Grant Admin Consent

**Important**: Application permissions require admin consent.

1. Click **Grant admin consent for [your organization]**
2. Click **Yes** to confirm

You should see green checkmarks indicating consent has been granted.

## Step 5: Create .env File

In your `orgplan-todo` directory, create a `.env` file:

```bash
cd orgplan-todo
cp .env.example .env
```

Edit `.env` and add your credentials:

```env
# Microsoft Graph API Authentication
MS_CLIENT_ID=your-application-client-id-here
MS_TENANT_ID=your-directory-tenant-id-here
MS_CLIENT_SECRET=your-client-secret-value-here

# Orgplan Configuration
ORGPLAN_DIR=.
TODO_LIST_NAME=Orgplan 2025

# Optional: Override current month (format: YYYY-MM)
# SYNC_MONTH=2025-12

# Optional: Log file path
# LOG_FILE=sync.log
```

## Step 6: Test Authentication

Test that your credentials work:

```bash
python tools/sync.py --todo-list "Orgplan 2025" --dry-run
```

If authentication succeeds, you should see:
```
[YYYY-MM-DD HH:MM:SS] INFO: Authenticating with Microsoft Graph API...
[YYYY-MM-DD HH:MM:SS] INFO: Authentication successful
```

## Troubleshooting

### "Authentication failed" Error

**Symptoms:**
```
Authentication failed: AADSTS700016: Application with identifier 'xxx' was not found...
```

**Solutions:**
- Verify `MS_CLIENT_ID` is correct (from app registration overview)
- Ensure no extra spaces or quotes in `.env` file

### "Unauthorized" or "Insufficient privileges"

**Symptoms:**
```
API request failed: 403 - Forbidden
```

**Solutions:**
- Verify `Tasks.ReadWrite` permission is added
- Ensure admin consent was granted (look for green checkmarks)
- Wait a few minutes for permissions to propagate

### "Invalid client secret"

**Symptoms:**
```
Authentication failed: AADSTS7000215: Invalid client secret provided
```

**Solutions:**
- Verify `MS_CLIENT_SECRET` is correct and not expired
- Check for extra spaces or line breaks in `.env`
- Create a new client secret if the old one expired

### "To Do list not found"

**Symptoms:**
```
To Do list 'Orgplan 2025' not found
Available lists:
  - Tasks
```

**Solutions:**
- Create the list in Microsoft To Do app first
- Use the exact name shown in "Available lists"
- List names are case-sensitive

## Security Best Practices

### Protect Your Credentials

**DO:**
- Keep `.env` file secure (it's in `.gitignore`)
- Use environment variables in production
- Rotate client secrets regularly
- Use least-privilege permissions

**DON'T:**
- Commit `.env` to version control
- Share credentials in chat/email
- Use the same credentials across environments
- Leave expired secrets in Azure

### Client Secret Expiration

Set a calendar reminder before your secret expires:
1. Go to Azure Portal > App registrations > Your app
2. Click **Certificates & secrets**
3. Create new client secret before old one expires
4. Update `.env` with new secret
5. Delete old secret after confirming new one works

## Permission Details

### Tasks.ReadWrite (Application)

**Allows:**
- Read all task lists
- Create, update, delete tasks
- Mark tasks as complete/incomplete
- Read and write task details

**Does NOT allow:**
- Access to other users' data (single user scope)
- Access to email or calendar
- Access to files or documents

## Alternative: Delegated Permissions (Future)

Currently, this project uses **Application permissions** with client credentials flow.

For **user-specific** access, you could use:
- **Delegated permissions**: Tasks.ReadWrite
- **Authentication flow**: OAuth 2.0 with user consent
- **Benefit**: User-specific access without admin consent

This would require interactive login but wouldn't need admin consent. Consider this for multi-user scenarios.

## Additional Resources

- [Microsoft Graph API Documentation](https://docs.microsoft.com/en-us/graph/)
- [Microsoft To Do API Reference](https://docs.microsoft.com/en-us/graph/api/resources/todo-overview)
- [Azure AD App Registration](https://docs.microsoft.com/en-us/azure/active-directory/develop/quickstart-register-app)
- [Application vs Delegated Permissions](https://docs.microsoft.com/en-us/azure/active-directory/develop/v2-permissions-and-consent)

## Getting Help

If you encounter issues:

1. Check the troubleshooting section above
2. Review the [main README](../README.md) troubleshooting section
3. Verify all steps were completed in order
4. Check Azure AD application logs for detailed errors
5. Create an issue on GitHub with:
   - Error message (redact your IDs)
   - Steps you've completed
   - Output of `python tools/sync.py --todo-list "YourList" --dry-run -v`
