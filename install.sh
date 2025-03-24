#!/bin/bash

# Portfolio Generator Installation Script

# Exit on error
set -e

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Portfolio Generator Installation${NC}"
echo "This script will install the Portfolio Generator and set it up to run automatically."
echo

# Check Python version
echo -e "${YELLOW}Checking Python version...${NC}"
if command -v python3 &>/dev/null; then
    python_version=$(python3 --version)
    echo -e "${GREEN}Found $python_version${NC}"
else
    echo -e "${RED}Python 3 is not installed. Please install Python 3.6 or newer.${NC}"
    exit 1
fi

# Create directory
echo -e "${YELLOW}Creating project directory...${NC}"
read -p "Enter directory path for installation [./portfolio-generator]: " install_dir
install_dir=${install_dir:-./portfolio-generator}

mkdir -p "$install_dir"
cd "$install_dir"
echo -e "${GREEN}Created directory: $install_dir${NC}"

# Download script
echo -e "${YELLOW}Downloading portfolio generator script...${NC}"
wget -O portfolio_generator.py https://raw.githubusercontent.com/yourusername/portfolio-generator/main/portfolio_generator.py || {
    echo -e "${RED}Failed to download script. Creating a new one from your clipboard...${NC}"
    echo "Please paste the script content and press Ctrl+D when finished:"
    cat > portfolio_generator.py
}
chmod +x portfolio_generator.py
echo -e "${GREEN}Script saved to portfolio_generator.py${NC}"

# Create domains.txt
echo -e "${YELLOW}Creating domains.txt file...${NC}"
if [ ! -f domains.txt ]; then
    echo "Please enter domain names (one per line). Press Ctrl+D when finished:"
    cat > domains.txt
    echo -e "${GREEN}Created domains.txt with your domains${NC}"
else
    echo -e "${GREEN}domains.txt already exists${NC}"
fi

# Install dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
pip3 install --user requests beautifulsoup4 scikit-learn numpy pillow schedule gitpython
echo -e "${GREEN}Dependencies installed${NC}"

# Create output directory
mkdir -p portfolio

# Create systemd service file
echo -e "${YELLOW}Setting up automatic execution...${NC}"
read -p "Do you want to set up a systemd service to run the script automatically? (y/n) " setup_systemd

if [ "$setup_systemd" = "y" ] || [ "$setup_systemd" = "Y" ]; then
    username=$(whoami)
    current_dir=$(pwd)
    
    cat > portfolio-generator.service << EOF
[Unit]
Description=Portfolio Generator Service
After=network.target

[Service]
Type=simple
User=$username
WorkingDirectory=$current_dir
ExecStart=/usr/bin/python3 $current_dir/portfolio_generator.py
Restart=on-failure
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=portfolio-generator

[Install]
WantedBy=multi-user.target
EOF
    
    echo -e "${GREEN}Created systemd service file: portfolio-generator.service${NC}"
    echo "To install the service, run the following commands:"
    echo "  sudo cp portfolio-generator.service /etc/systemd/system/"
    echo "  sudo systemctl daemon-reload"
    echo "  sudo systemctl enable portfolio-generator.service"
    echo "  sudo systemctl start portfolio-generator.service"
else
    echo "To set up automatic execution, you can add a cron job:"
    echo "  crontab -e"
    echo "Then add this line to run daily at 16:00:"
    echo "  0 16 * * * cd $(pwd) && /usr/bin/python3 portfolio_generator.py"
fi

# Set up Git
echo -e "${YELLOW}Setting up Git repository...${NC}"
read -p "Do you want to set up a Git repository? (y/n) " setup_git

if [ "$setup_git" = "y" ] || [ "$setup_git" = "Y" ]; then
    cd portfolio
    git init
    echo "*.log" > .gitignore
    echo "__pycache__/" >> .gitignore
    echo "*.py[cod]" >> .gitignore
    echo "*$py.class" >> .gitignore
    git add .
    git commit -m "Initial commit"
    
    read -p "Enter remote repository URL (leave empty to skip): " remote_url
    if [ ! -z "$remote_url" ]; then
        git remote add origin "$remote_url"
        echo -e "${GREEN}Remote repository added: $remote_url${NC}"
        echo "To push to remote repository, run:"
        echo "  cd $(pwd) && git push -u origin main"
    fi
    cd ..
    echo -e "${GREEN}Git repository initialized${NC}"
fi

# Run the script
echo -e "${YELLOW}Running the portfolio generator for the first time...${NC}"
read -p "Do you want to run the script now? (y/n) " run_now

if [ "$run_now" = "y" ] || [ "$run_now" = "Y" ]; then
    python3 portfolio_generator.py
    echo -e "${GREEN}Script executed! Check the portfolio/index.html file.${NC}"
else
    echo -e "${GREEN}You can run the script manually with:${NC}"
    echo "  cd $(pwd) && python3 portfolio_generator.py"
fi

echo
echo -e "${GREEN}Installation complete!${NC}"
echo "Your portfolio generator is set up in: $install_dir"
echo "Generated portfolio will be in: $install_dir/portfolio/index.html"
echo
echo "Thank you for using Portfolio Generator!"