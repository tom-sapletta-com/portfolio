# portfolio
portfolio generator

# Portfolio Generator

This script analyzes websites from a list of domains, extracts information about their content, themes, and technologies, and generates a portfolio page with thumbnails. The script runs automatically every day at 16:00 and pushes changes to a Git repository.

## Features

- Automatically analyzes websites from a list of domains
- Normalizes URLs (http/https, with/without www)
- Extracts website themes, keywords, and technologies using simple NLP techniques
- Generates thumbnails for each website
- Creates a searchable HTML portfolio page
- Runs automatically on a daily schedule
- Commits and pushes changes to a Git repository

## Requirements

- Python 3.6+
- Required Python packages:
  - requests
  - beautifulsoup4
  - scikit-learn
  - numpy
  - pillow
  - schedule
  - gitpython

## Installation

1. Clone this repository or download the script
2. Install required packages:

```bash
pip install requests beautifulsoup4 scikit-learn numpy pillow schedule gitpython
```

3. Create a `domains.txt` file with one domain per line (see example below)
4. Run the script:

```bash
python portfolio_generator.py
```

## Configuration

The script has several configuration variables at the top:

- `DOMAINS_FILE`: Path to the file containing domain names (default: "domains.txt")
- `OUTPUT_DIR`: Directory where the portfolio will be generated (default: "portfolio")
- `HTML_OUTPUT`: Path to the generated HTML file (default: "portfolio/index.html")
- `THUMBNAILS_DIR`: Directory where thumbnails will be stored (default: "portfolio/thumbnails")
- `DATA_FILE`: Path to the JSON file with portfolio data (default: "portfolio/data.json")
- `GIT_REPO_PATH`: Path to the Git repository (default: same as OUTPUT_DIR)
- `GIT_REMOTE`: Name of the remote repository (default: "origin")
- `GIT_BRANCH`: Name of the branch to push to (default: "main")

## Git Setup

The script automatically initializes a Git repository in the output directory. To push to a remote repository:

1. Create a remote repository (e.g., on GitHub, GitLab, etc.)
2. Add the remote to your local repository:

```bash
cd portfolio
git remote add origin YOUR_REMOTE_REPOSITORY_URL
```

## Automatic Scheduling

The script uses the `schedule` library to run automatically every day at 16:00. To make it run properly:

1. Keep the script running in the background (e.g., using a service, screen, tmux, etc.)
2. Alternatively, set up a cron job to run the script at 16:00 every day

Example cron job (run `crontab -e` to edit):

```
0 16 * * * cd /path/to/script/directory && /usr/bin/python3 portfolio_generator.py
```

## How It Works

1. The script reads a list of domains from a file
2. For each domain:
   - It normalizes the URL
   - Fetches the website content
   - Analyzes the content to identify theme, keywords, and technologies
   - Captures a thumbnail of the website
   - Stores the data in a JSON file
3. Generates an HTML portfolio page with all the analyzed websites
4. Commits and pushes changes to a Git repository

## Limitations

- The NLP analysis is very simple and may not always accurately identify the theme
- Thumbnail generation is basic and might not always capture the best visual representation
- The script has limited memory usage (suitable for running on an i5 CPU with 16MB RAM)
- Technology detection is based on simple text matching and may miss some technologies

## Example domains.txt

```
example.com
github.com
wordpress.org
stackoverflow.com
developer.mozilla.org
```

## Output

The script generates:

1. A `portfolio` directory with:
   - `index.html`: The main portfolio page
   - `thumbnails/`: Directory with website thumbnails
   - `data.json`: JSON file with all the portfolio data
2. A Git repository in the `portfolio` directory, ready to be pushed to a remote repository

## Troubleshooting

- If the script fails to push to the Git repository, make sure you've set up the remote correctly
- If website analysis fails, check the log file for more details
- The script creates a log file (`portfolio_generator.log`) with detailed information about its execution

## License

This script is provided as-is with no warranty. Use at your own risk.