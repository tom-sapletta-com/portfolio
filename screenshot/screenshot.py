from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image
import os
import time
import concurrent.futures
import logging
import threading
import platform
import subprocess
from queue import Queue
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get configuration from environment
IMAGE_DIR = os.getenv('IMAGE_DIR', 'img')
TARGET_FILE = os.getenv('TARGET_FILE', 'target.txt')
SCREENSHOT_WIDTH = int(os.getenv('SCREENSHOT_WIDTH', 1920))
SCREENSHOT_HEIGHT = int(os.getenv('SCREENSHOT_HEIGHT', 1080))
SCREENSHOT_RESIZE_WIDTH = int(os.getenv('SCREENSHOT_RESIZE_WIDTH', 500))
PAGE_LOAD_WAIT = int(os.getenv('PAGE_LOAD_WAIT', 3))
MAX_WORKERS = int(os.getenv('MAX_WORKERS', 4))
MAX_RETRIES = int(os.getenv('MAX_RETRIES', 3))
RETRY_DELAY = int(os.getenv('RETRY_DELAY', 2))
HEADLESS = os.getenv('HEADLESS', 'true').lower() == 'true'
# New environment variable for Chrome binary path
CHROME_BINARY = os.getenv('CHROME_BINARY', '/usr/bin/google-chrome')
# which google-chrome

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [Thread-%(thread)d] - %(levelname)s - %(message)s'
)

# Thread-local storage for WebDriver instances
thread_local = threading.local()

# Shared queue for progress tracking
progress_queue = Queue()


def find_chrome_binary():
    """Find Chrome binary path based on the operating system"""
    if CHROME_BINARY and os.path.exists(CHROME_BINARY):
        return CHROME_BINARY

    system = platform.system()

    # Common Chrome binary locations by OS
    if system == "Linux":
        chrome_paths = [
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
            "/snap/bin/chromium",
        ]

        # Try to find Chrome using 'which' command
        try:
            chrome_path = subprocess.check_output(["which", "google-chrome"],
                                                  stderr=subprocess.STDOUT,
                                                  universal_newlines=True).strip()
            if chrome_path:
                return chrome_path
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        # Check common locations
        for path in chrome_paths:
            if os.path.exists(path):
                return path

    elif system == "Darwin":  # macOS
        chrome_paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ]
        for path in chrome_paths:
            if os.path.exists(path):
                return path

    elif system == "Windows":
        chrome_paths = [
            os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'),
                         'Google\\Chrome\\Application\\chrome.exe'),
            os.path.join(os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)'),
                         'Google\\Chrome\\Application\\chrome.exe'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''),
                         'Google\\Chrome\\Application\\chrome.exe'),
        ]
        for path in chrome_paths:
            if os.path.exists(path):
                return path

    return None


def create_placeholder_image(domain, output_path):
    """Create a placeholder image when screenshot fails"""
    try:
        width = SCREENSHOT_RESIZE_WIDTH
        height = int(width * 0.75)  # 4:3 aspect ratio

        # Create a colored background based on domain name
        color = sum(ord(c) for c in domain) % 255
        img = Image.new('RGB', (width, height), (color, 255 - color, 150))

        # Save the placeholder
        img.save(output_path)
        logging.info(f"Created placeholder image for {domain}")
        return True
    except Exception as e:
        logging.error(f"Failed to create placeholder for {domain}: {str(e)}")
        return False


def get_thread_driver():
    """Get or create thread-local WebDriver instance"""
    if not hasattr(thread_local, "driver"):
        chrome_options = Options()
        if HEADLESS:
            chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument(f'--window-size={SCREENSHOT_WIDTH},{SCREENSHOT_HEIGHT}')
        chrome_options.add_argument('--disable-gpu')

        # Find and set Chrome binary path
        chrome_binary = find_chrome_binary()
        if chrome_binary:
            logging.info(f"Using Chrome binary at: {chrome_binary}")
            chrome_options.binary_location = chrome_binary
        else:
            logging.warning("Chrome binary not found. WebDriver might fail.")

        try:
            # Use webdriver-manager to get the correct chromedriver version
            service = Service(ChromeDriverManager().install())
            thread_local.driver = webdriver.Chrome(service=service, options=chrome_options)
            logging.info("Successfully created Chrome WebDriver instance")
        except Exception as e:
            logging.error(f"Error setting up Chrome WebDriver: {str(e)}")
            thread_local.driver = None
            raise
    return thread_local.driver


def cleanup_thread_driver():
    """Cleanup thread-local WebDriver instance"""
    if hasattr(thread_local, "driver") and thread_local.driver:
        try:
            thread_local.driver.quit()
            logging.debug("WebDriver instance cleaned up")
        except Exception as e:
            logging.debug(f"Error cleaning up WebDriver: {str(e)}")
        finally:
            thread_local.driver = None


def process_single_domain(domain):
    """Process a single domain with retries"""
    retry_count = 0
    output_path = os.path.join(IMAGE_DIR, f"{domain.replace('.', '_').replace('/', '_')}.png")

    while retry_count < MAX_RETRIES:
        try:
            driver = get_thread_driver()
            if not driver:
                raise WebDriverException("Failed to create WebDriver instance")

            url = f"http://{domain}" if not domain.startswith(('http://', 'https://')) else domain
            logging.info(f"Processing: {url}")

            driver.get(url)
            time.sleep(PAGE_LOAD_WAIT)

            driver.set_window_size(SCREENSHOT_WIDTH, SCREENSHOT_HEIGHT)
            driver.save_screenshot(output_path)

            with Image.open(output_path) as img:
                width_percent = (SCREENSHOT_RESIZE_WIDTH / float(img.size[0]))
                new_height = int((float(img.size[1]) * float(width_percent)))
                resized_img = img.resize((SCREENSHOT_RESIZE_WIDTH, new_height), Image.Resampling.LANCZOS)
                resized_img.save(output_path)

            logging.info(f"Screenshot saved: {output_path}")
            progress_queue.put(('success', domain))
            return True

        except Exception as e:
            retry_count += 1
            logging.error(f"Error processing {domain} (attempt {retry_count}/{MAX_RETRIES}): {str(e)}")

            # Clean up the driver on error
            cleanup_thread_driver()

            if retry_count < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
            else:
                # Create a placeholder image after all retries fail
                if create_placeholder_image(domain, output_path):
                    progress_queue.put(('success', domain))
                    return True
                else:
                    progress_queue.put(('error', domain))
                    return False





def progress_monitor():
    """Monitor and display progress information"""
    success_count = 0
    error_count = 0
    total_count = 0

    while True:
        try:
            status, domain = progress_queue.get()
            if status == 'success':
                success_count += 1
            elif status == 'error':
                error_count += 1
            elif status == 'total':
                total_count = domain
                logging.info(f"Starting processing of {total_count} domains")
                continue

            processed = success_count + error_count
            if total_count > 0:
                percentage = (processed / total_count) * 100
                logging.info(f"Progress: {processed}/{total_count} ({percentage:.1f}%) - "
                             f"Success: {success_count}, Errors: {error_count}")

            if processed == total_count:
                logging.info(f"Processing completed! Success: {success_count}, Errors: {error_count}")
                break

        except Exception as e:
            logging.error(f"Error in progress monitor: {str(e)}")
            break


def process_domains_parallel(domains):
    """Process domains in parallel using ThreadPoolExecutor"""
    # Start the progress monitor thread
    monitor_thread = threading.Thread(target=progress_monitor)
    monitor_thread.daemon = True  # Make thread exit when main thread exits
    monitor_thread.start()

    # Send total count to progress monitor
    progress_queue.put(('total', len(domains)))

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(process_single_domain, domain) for domain in domains]
            concurrent.futures.wait(futures)

    except KeyboardInterrupt:
        logging.info("Process interrupted by user. Cleaning up...")

    finally:
        # Make sure all threads clean up their drivers
        cleanup_thread_driver()

    # Wait for progress monitor to finish
    monitor_thread.join(timeout=5.0)


def main():
    try:
        # Create output directory if it doesn't exist
        if not os.path.exists(IMAGE_DIR):
            os.makedirs(IMAGE_DIR)
            logging.info(f"Created output directory: {IMAGE_DIR}")

        # Check if Chrome is available
        chrome_binary = find_chrome_binary()
        if chrome_binary:
            logging.info(f"Found Chrome binary at: {chrome_binary}")
        else:
            logging.warning("Chrome binary not found. Please install Chrome or set CHROME_BINARY environment variable.")

        # Read domains from file
        if not os.path.exists(TARGET_FILE):
            logging.error(f"Target file not found: {TARGET_FILE}")
            return

        with open(TARGET_FILE, 'r') as file:
            domains = [line.strip() for line in file if line.strip()]

        if not domains:
            logging.error(f"No domains found in {TARGET_FILE}")
            return

        logging.info(f"Starting screenshot generation with {len(domains)} domains")
        process_domains_parallel(domains)
        logging.info("All processing completed!")

    except Exception as e:
        logging.error(f"Error in main process: {str(e)}")

    finally:
        cleanup_thread_driver()


if __name__ == "__main__":
    main()
