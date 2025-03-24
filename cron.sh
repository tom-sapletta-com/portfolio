#!/bin/bash

# Script to automatically add a cron job for the portfolio generator

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Portfolio Generator - Cron Job Setup${NC}"
echo "This script will add a cron job to run the portfolio generator daily at 16:00."
echo

# Get the current directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Check if portfolio_generator.py exists
if [ ! -f "$SCRIPT_DIR/portfolio_generator.py" ]; then
    echo -e "${RED}Error: portfolio_generator.py not found in the current directory.${NC}"
    read -p "Enter the full path to the portfolio_generator.py script: " SCRIPT_PATH
    
    if [ ! -f "$SCRIPT_PATH" ]; then
        echo -e "${RED}Error: File not found at $SCRIPT_PATH${NC}"
        exit 1
    fi
    
    SCRIPT_DIR=$(dirname "$SCRIPT_PATH")
    SCRIPT_NAME=$(basename "$SCRIPT_PATH")
else
    SCRIPT_PATH="$SCRIPT_DIR/portfolio_generator.py"
    SCRIPT_NAME="portfolio_generator.py"
fi

echo -e "${GREEN}Found script at: $SCRIPT_PATH${NC}"

# Check Python path
PYTHON_PATH=$(which python3)
if [ -z "$PYTHON_PATH" ]; then
    echo -e "${RED}Error: Python 3 not found in PATH.${NC}"
    read -p "Enter the full path to the Python 3 executable: " PYTHON_PATH
    
    if [ ! -f "$PYTHON_PATH" ]; then
        echo -e "${RED}Error: Python not found at $PYTHON_PATH${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}Using Python: $PYTHON_PATH${NC}"

# Get current crontab
TMPFILE=$(mktemp)
crontab -l > "$TMPFILE" 2>/dev/null || true

# Check if the cron job already exists
if grep -q "$SCRIPT_PATH" "$TMPFILE"; then
    echo -e "${YELLOW}A cron job for this script already exists:${NC}"
    grep "$SCRIPT_PATH" "$TMPFILE"
    read -p "Do you want to replace it? (y/n): " REPLACE
    
    if [ "$REPLACE" = "y" ] || [ "$REPLACE" = "Y" ]; then
        # Remove existing lines with this script
        grep -v "$SCRIPT_PATH" "$TMPFILE" > "${TMPFILE}.new"
        mv "${TMPFILE}.new" "$TMPFILE"
    else
        echo -e "${GREEN}Keeping existing cron job.${NC}"
        rm "$TMPFILE"
        exit 0
    fi
fi

# Ask for customization
echo "Default cron job will run daily at 16:00."
read -p "Do you want to customize the schedule? (y/n): " CUSTOMIZE

if [ "$CUSTOMIZE" = "y" ] || [ "$CUSTOMIZE" = "Y" ]; then
    echo "Enter values for each field (or press Enter for default):"
    read -p "Minute (0-59) [0]: " MINUTE
    MINUTE=${MINUTE:-0}
    
    read -p "Hour (0-23) [16]: " HOUR
    HOUR=${HOUR:-16}
    
    read -p "Day of month (1-31 or *) [*]: " DOM
    DOM=${DOM:-*}
    
    read -p "Month (1-12 or *) [*]: " MONTH
    MONTH=${MONTH:-*}
    
    read -p "Day of week (0-6 or *) [*]: " DOW
    DOW=${DOW:-*}
    
    CRON_SCHEDULE="$MINUTE $HOUR $DOM $MONTH $DOW"
else
    CRON_SCHEDULE="0 16 * * *"
fi

# Ask for logging
read -p "Do you want to save output logs? (y/n): " SAVE_LOGS

if [ "$SAVE_LOGS" = "y" ] || [ "$SAVE_LOGS" = "Y" ]; then
    read -p "Enter log file path [$SCRIPT_DIR/cron_log.txt]: " LOG_PATH
    LOG_PATH=${LOG_PATH:-"$SCRIPT_DIR/cron_log.txt"}
    CRON_COMMAND="$CRON_SCHEDULE cd $SCRIPT_DIR && $PYTHON_PATH $SCRIPT_NAME >> $LOG_PATH 2>&1"
else
    CRON_COMMAND="$CRON_SCHEDULE cd $SCRIPT_DIR && $PYTHON_PATH $SCRIPT_NAME > /dev/null 2>&1"
fi

# Add new cron job
echo "$CRON_COMMAND" >> "$TMPFILE"

# Install new crontab
if crontab "$TMPFILE"; then
    echo -e "${GREEN}Cron job successfully added:${NC}"
    echo -e "${YELLOW}$CRON_COMMAND${NC}"
    echo
    echo "To verify, run: crontab -l"
else
    echo -e "${RED}Failed to install crontab.${NC}"
    exit 1
fi

# Clean up
rm "$TMPFILE"

echo -e "${GREEN}Setup complete!${NC}"
echo "The portfolio generator will run automatically according to the schedule."