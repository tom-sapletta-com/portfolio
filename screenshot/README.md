This implementation:

Extracts the thumbnail generation functionality from the original code
Provides a clean API for use as a library
Adds command-line interface with various options
Maintains the same thumbnail generation strategies:
Open Graph image
Twitter Card image
Largest image on the page
Placeholder with domain color
You can use it in two ways:

As a command-line tool:
```
python screenshot.py https://example.com -o example.jpg -w 400 -h 300 -q 90
```

As a library in your code:
```        
from screenshot import capture_thumbnail

# Save to file
capture_thumbnail("https://example.com", "thumbnails/example.jpg")

# Or get PIL Image object
image = capture_thumbnail("https://example.com")
# Do something with the image...
```

source "portfolio-env/bin/activate"

pip install selenium webdriver-manager pillow requests beautifulsoup4



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

3. Start the server:
   ```bash
   python3 screenshot.py
   ```
   

# For Debian/Ubuntu
sudo apt-get update
sudo apt-get install google-chrome-stable

sudo apt-get update
sudo apt-get install python3-dev python3-setuptools libtiff5-dev libjpeg8-dev libopenjp2-7-dev zlib1g-dev libfreetype6-dev liblcms2-dev libwebp-dev tcl8.6-dev tk8.6-dev python3-tk libharfbuzz-dev libfribidi-dev libxcb1-dev


## fedora
# For Fedora/RHEL

sudo dnf install python3-devel redhat-rpm-config zlib-devel libjpeg-devel openjpeg2-devel freetype-devel lcms2-devel libwebp-devel tcl-devel tk-devel harfbuzz-devel fribidi-devel


sudo dnf install google-chrome-stable
To find the Chrome binary on Fedora, you can use several methods:

Use the which command to locate the Chrome executable:

which google-chrome
which google-chrome-stable
which chromium-browser
which chromium



Check common installation locations on Fedora:

ls -l /usr/bin/google-chrome*
ls -l /usr/bin/chromium*



Use the whereis command which shows binary, source, and manual page locations:

whereis google-chrome
whereis chromium



Use the find command to search the entire filesystem (this might take some time):

sudo find / -name "google-chrome" -type f 2>/dev/null
sudo find / -name "chromium-browser" -type f 2>/dev/null


If Chrome is not installed, you can install it with:

# For Google Chrome
sudo dnf install fedora-workstation-repositories
sudo dnf config-manager --set-enabled google-chrome
sudo dnf install google-chrome-stable

# For Chromium
sudo dnf install chromium