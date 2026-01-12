<#
.SYNOPSIS
    Sets up a Windows Scheduled Task for orgplan-todo sync.

.DESCRIPTION
    Creates a scheduled task that runs the sync.py script at a specified interval.
    The task runs as the current logged-in user.

.PARAMETER TodoList
    The name of the Microsoft To Do or Google Task list to sync. Default: "Orgplan 2025"

.PARAMETER ScheduleMinutes
    How often to run the sync in minutes. Default: 30

.PARAMETER LogFile
    Path to the log file. Defaults to sync.log in the project directory.

.PARAMETER TaskName
    Name of the scheduled task. Default: "OrgplanTodoSync"

.PARAMETER DryRun
    If specified, prints what would happen without actually creating the task.

.PARAMETER PythonPath
    Path to the python executable. Defaults to 'python' (PATH).

.EXAMPLE
    .\setup_tasksched.ps1 -TodoList "My Tasks" -ScheduleMinutes 15
#>

param(
    [string]$TodoList = "Orgplan 2025",
    [int]$ScheduleMinutes = 30,
    [string]$LogFile,
    [string]$TaskName = "OrgplanTodoSync",
    [switch]$DryRun,
    [string]$PythonPath = "python"
)

$ErrorActionPreference = "Stop"

# Get script directory and project root
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectDir = Split-Path -Parent $ScriptDir

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Orgplan-Todo Task Scheduler Setup" -ForegroundColor Cyan
Write-Host "=================================="
Write-Host ""

# Default log file path
if (-not $LogFile) {
    $LogFile = Join-Path $ProjectDir "sync.log"
}

Write-Host "Configuration:"
Write-Host "  Project directory: $ProjectDir"
Write-Host "  To Do list name:   $TodoList"
Write-Host "  Schedule:          Every $ScheduleMinutes minutes"
Write-Host "  Log file:          $LogFile"
Write-Host "  Task Name:         $TaskName"
Write-Host ""

# Check for .env file
$EnvFile = Join-Path $ProjectDir ".env"
if (-not (Test-Path $EnvFile)) {
    Write-Host "Error: .env file not found at $EnvFile" -ForegroundColor Red
    Write-Host "Please create it with your credentials before setting up the schedule."
    exit 1
}

# Construct arguments
# We use --no-prompt to prevent blocking in background
# We also want to redirect stderr to stdout for the log, but Task Scheduler handles output poorly unless wrapped.
# For simplicity, we'll let python write to the log file via --log-file and handling stdio locally if needed.
# However, the python script's --log-file argument already handles file logging.
# We just need to make sure the task wrapper doesn't pop up a window.
# We will use pythonw.exe (if available/implied) or just python.exe with proper window settings in the task.

# Check if auth-mode delegated might need persistent session, assuming tokens are already there.
# If using Google or Delegated MS, ensure the user has run it once manually.

$ScriptPath = Join-Path $ScriptDir "sync.py"
$Arguments = "`"$ScriptPath`" --todo-list `"$TodoList`" --log-file `"$LogFile`" --no-prompt"

Write-Host "Command to run:"
Write-Host "  $PythonPath $Arguments"
Write-Host ""

if ($DryRun) {
    Write-Host "Dry run completed. No task created." -ForegroundColor Yellow
    exit 0
}

$UserConfirmation = Read-Host "Create this scheduled task? (y/n)"
if ($UserConfirmation -notmatch "^[Yy]") {
    Write-Host "Aborted."
    exit 0
}

# Create Task Action
$Action = New-ScheduledTaskAction -Execute $PythonPath -Argument $Arguments -WorkingDirectory $ProjectDir

# Create Task Trigger
# Start 'AtStartup' or 'AtLogon' is good, but for a sync loop, a repetition trigger is usually done via a daily trigger that repeats.
# We'll use a standard approach: Start at a specific time (now) and repeat indefinitely.
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes $ScheduleMinutes)
# Note: By default RepetitionDuration is 1 day for Daily, but for -Once it's confusing.
# To repeat indefinitely, we often set RepetitionDuration to [TimeSpan]::MaxValue or effectively "indefinitely".
# PowerShell's New-ScheduledTaskTrigger doesn't expose "Indefinitely" easily for -Once.
# A better pattern for "Run every X minutes all day" is often:
# Trigger: Daily, Start 00:00, Repeat every X minutes, Duration 1 day.
$Trigger = New-ScheduledTaskTrigger -Daily -At "12:00 AM" -RepetitionInterval (New-TimeSpan -Minutes $ScheduleMinutes)

# Settings
# AllowStartIfOnBatteries, StopIfGoingOnBatteries -> False for reliability? Or True to save battery?
# Assuming desktop/dev usage:
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1)

# Register Task
try {
    # Unregister if exists to replace
    $Existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($Existing) {
        Write-Host "Task '$TaskName' already exists. Updating..." -ForegroundColor Yellow
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }
    
    Register-ScheduledTask -Action $Action -Trigger $Trigger -Settings $Settings -TaskName $TaskName -Description "Runs orgplan-todo sync" | Out-Null
    Write-Host "✓ Task '$TaskName' created successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "You can view/manage it in Task Scheduler (taskschd.msc)."
    Write-Host "To test run now:"
    Write-Host "  Start-ScheduledTask -TaskName `"$TaskName`""
}
catch {
    Write-Host "Failed to create task: $_" -ForegroundColor Red
    exit 1
}
