# Edit crontab:
# crontab -e

# Add this line to run daily at 16:00:
0 16 * * * cd /path/to/script/directory && /usr/bin/python3 portfolio_generator.py

# For logging output:
0 16 * * * cd /path/to/script/directory && /usr/bin/python3 portfolio_generator.py >> /path/to/script/directory/cron_log.txt 2>&1