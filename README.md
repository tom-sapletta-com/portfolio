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



I'll create a script that will automatically add the cron job to run the portfolio generator at 16:00 daily:

I've created a script that will automatically add a cron job for running your portfolio generator. Here's what this script does:

1. **Detects the location** of your portfolio generator script automatically
2. **Finds the Python executable** path on your system
3. **Checks for existing cron jobs** for the same script to avoid duplicates
4. **Allows customization** of the cron schedule if you don't want the default 16:00 time
5. **Configures logging options** so you can keep track of script execution
6. **Updates your crontab** with the new settings


### How to use the script:

1. Save it as `add-cron-job.sh` in the same directory as your portfolio generator
2. Make it executable:
   ```bash
   chmod +x add-cron-job.sh
   ```
3. Run it:
   ```bash
   ./add-cron-job.sh
   ```

The script is interactive and will guide you through the process with prompts. By default, it will set up the cron job to run the portfolio generator daily at 16:00, but you can customize this schedule if needed.

After running the script, you can verify that the cron job was added successfully by running:
```bash
crontab -l
```

This script is designed to be user-friendly even for those who aren't familiar with cron syntax.



## License

This script is provided as-is with no warranty. Use at your own risk.


I see you're still having issues with installing spaCy on your Fedora system. Let's try a few alternative approaches.

The error now shows that there's no binary (wheel) package available for spaCy for your specific Python version, which seems to be Python 3.13 according to the error logs.

Here are some options to resolve this:

1. First, let's install the general development tools and gcc:
```bash
sudo dnf groupinstall "Development Tools"
sudo dnf install gcc-c++
```

2. Since the build is specifically looking for g++-11, let's create a symbolic link to make the existing g++ available as g++-11:
```bash
which g++  # Find where g++ is located
sudo ln -s $(which g++) /usr/local/bin/g++-11
```

3. Try installing spaCy with minimal dependencies or alternate versions:
```bash
pip install spacy==3.7.2  # Try an older version
```

4. If none of the above works, you could consider using a different Python version. SpaCy might not yet be fully compatible with Python 3.13 (which is quite new). You could create a new virtual environment with Python 3.10 or 3.11:
```bash
sudo dnf install python3.11
python3.11 -m venv venv311
source venv311/bin/activate
pip install spacy scikit-learn beautifulsoup4
```

5. Alternatively, you could use Conda which manages its own binaries:
```bash
# Install Miniconda if you don't have it
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh

# Create and activate conda environment
conda create -n nlp python=3.10
conda activate nlp
conda install -c conda-forge spacy scikit-learn beautifulsoup4
```

The key issue seems to be Python 3.13 compatibility with spaCy's build system. Using a slightly older Python version (3.10-3.11) might be the quickest path to success.

```        
pip install spacy scikit-learn beautifulsoup4
python -m spacy download en_core_web_md
```

1. Create and activate virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install requirements:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

# Install spaCy's small English model directly
```bash
pip install spacy
pip install selenium
pip install webdriver_manager
python -m spacy download en_core_web_sm
```

3. Start the server:
   ```bash
   python portfolio_generator.py
   ```
   

I see you're still having issues with installing spaCy on your Fedora system. Let's try a few alternative approaches.

The error now shows that there's no binary (wheel) package available for spaCy for your specific Python version, which seems to be Python 3.13 according to the error logs.

Here are some options to resolve this:

1. First, let's install the general development tools and gcc:
```bash
sudo dnf groupinstall "Development Tools"
sudo dnf install gcc-c++
```

2. Since the build is specifically looking for g++-11, let's create a symbolic link to make the existing g++ available as g++-11:
```bash
which g++  # Find where g++ is located
sudo ln -s $(which g++) /usr/local/bin/g++-11
```

3. Try installing spaCy with minimal dependencies or alternate versions:
```bash
pip install spacy==3.7.2  # Try an older version
```

4. If none of the above works, you could consider using a different Python version. SpaCy might not yet be fully compatible with Python 3.13 (which is quite new). You could create a new virtual environment with Python 3.10 or 3.11:
```bash
sudo dnf install python3.11
python3.11 -m venv venv311
source venv311/bin/activate
pip install spacy scikit-learn beautifulsoup4
```

5. Alternatively, you could use Conda which manages its own binaries:
```bash
# Install Miniconda if you don't have it
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh

# Create and activate conda environment
conda create -n nlp python=3.10
conda activate nlp
conda install -c conda-forge spacy scikit-learn beautifulsoup4
```

The key issue seems to be Python 3.13 compatibility with spaCy's build system. Using a slightly older Python version (3.10-3.11) might be the quickest path to success.