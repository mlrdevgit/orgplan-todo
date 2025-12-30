#!/bin/bash
# Setup cron job for orgplan-todo sync

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=================================="
echo "Orgplan-Todo Cron Setup"
echo "=================================="
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Default values
TODO_LIST_NAME="${TODO_LIST_NAME:-Orgplan 2025}"
SCHEDULE="${SCHEDULE:-*/30 * * * *}"  # Every 30 minutes by default
LOG_FILE="${LOG_FILE:-${PROJECT_DIR}/sync.log}"

echo "Configuration:"
echo "  Project directory: $PROJECT_DIR"
echo "  To Do list name: $TODO_LIST_NAME"
echo "  Schedule: $SCHEDULE"
echo "  Log file: $LOG_FILE"
echo ""

# Check if .env file exists
if [ ! -f "${PROJECT_DIR}/.env" ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo "Please create ${PROJECT_DIR}/.env with your Microsoft Graph API credentials."
    echo "See .env.example for template."
    exit 1
fi

# Create cron command
CRON_COMMAND="cd ${PROJECT_DIR} && python ${SCRIPT_DIR}/sync.py --todo-list \"${TODO_LIST_NAME}\" --log-file \"${LOG_FILE}\" 2>&1"

# Full cron entry
CRON_ENTRY="${SCHEDULE} ${CRON_COMMAND}"

echo "Cron entry to be added:"
echo "  ${CRON_ENTRY}"
echo ""

# Ask for confirmation
read -p "Add this cron job? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

# Add to crontab
(crontab -l 2>/dev/null | grep -v "orgplan-todo sync"; echo "$CRON_ENTRY  # orgplan-todo sync") | crontab -

echo -e "${GREEN}✓ Cron job added successfully!${NC}"
echo ""
echo "Cron job details:"
crontab -l | grep "orgplan-todo sync"
echo ""
echo "To view logs:"
echo "  tail -f $LOG_FILE"
echo ""
echo "To remove the cron job:"
echo "  crontab -e"
echo "  # Then delete the line with 'orgplan-todo sync'"
echo ""
echo -e "${YELLOW}Note: First sync will run according to schedule.${NC}"
echo "You can test manually with:"
echo "  python ${SCRIPT_DIR}/sync.py --todo-list \"${TODO_LIST_NAME}\" --dry-run"
