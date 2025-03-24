#!/bin/bash

# Script to set up a virtual environment and run the portfolio generator

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Portfolio Generator - Setup and Run${NC}"
echo "This script will create a virtual environment, install requirements, and start the portfolio generator."
echo

# Get the current directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Check if python3 and venv are available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed or not in PATH.${NC}"
    exit 1
fi

if ! python3 -c "import venv" &> /dev/null; then
    echo -e "${RED}Error: Python venv module is not available.${NC}"
    echo "Please install it with your package manager."
    echo "Example: sudo apt-get install python3-venv  # For Debian/Ubuntu"
    exit 1
fi

# Check for requirements.txt
if [ ! -f "$SCRIPT_DIR/requirements.txt" ]; then
    echo -e "${RED}Error: requirements.txt not found in the current directory.${NC}"
    echo "Creating a minimal requirements.txt file..."
    cat > "$SCRIPT_DIR/requirements.txt" << EOF
requests>=2.25.0
beautifulsoup4>=4.9.3
scikit-learn>=0.24.0
numpy>=1.19.0
pillow>=8.0.0
schedule>=1.0.0
gitpython>=3.1.14
EOF
    echo -e "${GREEN}Created requirements.txt${NC}"
fi

# Check for portfolio_generator.py
if [ ! -f "$SCRIPT_DIR/portfolio_generator.py" ]; then
    echo -e "${RED}Error: portfolio_generator.py not found in the current directory.${NC}"
    exit 1
fi

# Ask for venv name
read -p "Enter virtual environment name [portfolio-env]: " VENV_NAME
VENV_NAME=${VENV_NAME:-"portfolio-env"}
VENV_PATH="$SCRIPT_DIR/$VENV_NAME"

# Create virtual environment
echo -e "${YELLOW}Creating virtual environment at $VENV_PATH...${NC}"
python3 -m venv "$VENV_PATH"

if [ ! -d "$VENV_PATH" ]; then
    echo -e "${RED}Failed to create virtual environment.${NC}"
    exit 1
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source "$VENV_PATH/bin/activate"

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to activate virtual environment.${NC}"
    exit 1
fi

# Install requirements
echo -e "${YELLOW}Installing requirements...${NC}"
pip install --upgrade pip
pip install -r "$SCRIPT_DIR/requirements.txt"

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to install requirements.${NC}"
    deactivate
    exit 1
fi

echo -e "${GREEN}Requirements installed successfully!${NC}"

# Check for domains.txt
if [ ! -f "$SCRIPT_DIR/domains.txt" ]; then
    echo -e "${YELLOW}domains.txt not found. Creating an example file...${NC}"
    cat > "$SCRIPT_DIR/domains.txt" << EOF
example.com
github.com
stackoverflow.com
dev.to
python.org
wordpress.org
EOF
    echo -e "${GREEN}Created example domains.txt${NC}"
    echo "Please edit this file to add your own domains."
    read -p "Press Enter to continue or Ctrl+C to exit and edit the file"
fi

# Create output directory
mkdir -p "$SCRIPT_DIR/portfolio"

# Ask if user wants to add a cron job
read -p "Do you want to add a cron job to run daily at 16:00? (y/n): " ADD_CRON

if [ "$ADD_CRON" = "y" ] || [ "$ADD_CRON" = "Y" ]; then
    # Create a wrapper script that activates the venv and runs the python script
    WRAPPER_SCRIPT="$SCRIPT_DIR/run_portfolio_generator.sh"
    cat > "$WRAPPER_SCRIPT" << EOF
#!/bin/bash
cd "$SCRIPT_DIR"
source "$VENV_PATH/bin/activate"
python portfolio_generator.py
deactivate
EOF
    chmod +x "$WRAPPER_SCRIPT"

    # Add cron job
    TMPFILE=$(mktemp)
    crontab -l > "$TMPFILE" 2>/dev/null || true

    # Check if the cron job already exists
    if grep -q "$WRAPPER_SCRIPT" "$TMPFILE"; then
        echo -e "${YELLOW}A cron job for this script already exists.${NC}"
    else
        echo "0 16 * * * $WRAPPER_SCRIPT > $SCRIPT_DIR/cron_log.txt 2>&1" >> "$TMPFILE"
        if crontab "$TMPFILE"; then
            echo -e "${GREEN}Cron job added successfully!${NC}"
        else
            echo -e "${RED}Failed to add cron job.${NC}"
        fi
    fi

    rm "$TMPFILE"
fi

# Run the script
echo -e "${YELLOW}Running portfolio generator...${NC}"
python "$SCRIPT_DIR/portfolio_generator.py"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Portfolio generator completed successfully!${NC}"
    echo "Generated portfolio is available at: $SCRIPT_DIR/portfolio/index.html"
else
    echo -e "${RED}Portfolio generator encountered errors. Please check the output above.${NC}"
fi

# Create a script to easily run the portfolio generator in the future
ACTIVATE_SCRIPT="$SCRIPT_DIR/start_portfolio_generator.sh"
cat > "$ACTIVATE_SCRIPT" << EOF
#!/bin/bash
cd "$SCRIPT_DIR"
source "$VENV_PATH/bin/activate"
python portfolio_generator.py
deactivate
EOF
chmod +x "$ACTIVATE_SCRIPT"

echo -e "${GREEN}Setup complete!${NC}"
echo "To run the portfolio generator in the future, use: $ACTIVATE_SCRIPT"

# Deactivate the virtual environment
deactivate