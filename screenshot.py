#!/usr/bin/env python3
import os
import sys
import argparse
import logging
import hashlib
import tempfile
from urllib.parse import urlparse

import requests
from PIL import Image, ImageDraw, ImageFont
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("screenshot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("screenshot")

# Predefined colors for placeholders
COLORS = [
    "#4285F4", "#EA4335", "#FBBC05", "#34A853",
    "#FF9900", "#146EB4", "#0077B5", "#1DA1F2",
    "#FF6900", "#8B4513", "#FF7F50", "#6A5ACD",
    "#32CD32", "#FF4500", "#9370DB", "#3CB371",
    "#20B2AA", "#B8860B", "#D2691E", "#CD5C5C"
]


def get_color_for_domain(domain):
    """Generate a consistent color for a domain from predefined colors."""
    hash_obj = hashlib.md5(domain.encode())
    hash_int = int(hash_obj.hexdigest(), 16)
    color_index = hash_int % len(COLORS)
    return COLORS[color_index]


def create_placeholder_image(domain_name, size=(800, 200)):
    """Create a visually appealing placeholder image with domain name."""
    color = get_color_for_domain(domain_name)
    img = Image.new('RGB', size, color)
    draw = ImageDraw.Draw(img)

    try:
        display_name = domain_name.split('.')[0].upper()
        font_size = min(size) // (3 + min(len(display_name) // 5, 3))

        # Try multiple font options
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
        ]

        font = None
        for font_path in font_paths:
            try:
                font = ImageFont.truetype(font_path, font_size)
                break
            except IOError:
                continue

        if not font:
            font = ImageFont.load_default()

        # Calculate text positioning
        bbox = font.getbbox(display_name)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        x = (size[0] - text_width) // 2
        y = (size[1] - text_height) // 2

        # Draw text with shadow
        shadow_offset = max(1, font_size // 15)
        draw.text((x + shadow_offset, y + shadow_offset), display_name, fill="rgba(0,0,0,128)", font=font)
        draw.text((x, y), display_name, fill="white", font=font)

    except Exception as e:
        logger.warning(f"Could not add text to placeholder: {e}")

    return img


def capture_webpage_screenshot(url, output_path, size=(800, 200)):
    """
    Capture a full webpage screenshot using Selenium WebDriver.

    Args:
        url (str): URL of the webpage to screenshot
        output_path (str): Path to save the screenshot
        size (tuple): Desired thumbnail size (width, height)

    Returns:
        bool: True if screenshot successful, False otherwise
    """
    try:
        # Setup Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in background
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument(f"--window-size={size[0]},{size[1]}")

        # Use WebDriver Manager to handle driver installation
        service = Service(ChromeDriverManager().install())

        # Initialize the WebDriver
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # Navigate to the URL
        driver.get(url)

        # Wait for page to load (up to 10 seconds)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Take screenshot
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_screenshot:
            driver.save_screenshot(temp_screenshot.name)

        # Close the browser
        driver.quit()

        # Open the screenshot and resize
        with Image.open(temp_screenshot.name) as img:
            # Crop to desired aspect ratio
            width, height = img.size
            crop_height = int(width / 4)
            cropped_img = img.crop((0, 0, width, min(crop_height, height)))

            # Resize to exact desired size
            cropped_img = cropped_img.resize(size, Image.LANCZOS)

            # Save the final image
            cropped_img.save(output_path, 'JPEG', quality=85)

        # Remove temporary file
        os.unlink(temp_screenshot.name)

        return True

    except Exception as e:
        logger.error(f"Error capturing screenshot for {url}: {e}")
        return False


def capture_thumbnail(url, output_path=None, size=(800, 200), force_placeholder=False):
    """
    Capture a thumbnail of the website.

    Args:
        url (str): URL of the website
        output_path (str, optional): Path to save the thumbnail
        size (tuple, optional): Desired thumbnail size
        force_placeholder (bool, optional): Force placeholder image

    Returns:
        str or Image: Path to saved thumbnail or Image object
    """
    # Extract domain name
    parsed_url = urlparse(url)
    domain_name = parsed_url.netloc
    if domain_name.startswith('www.'):
        domain_name = domain_name[4:]

    # Create output directory if needed
    if output_path:
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

    # Determine output path
    output_path = output_path or f"{domain_name}_thumbnail.jpg"

    # If forcing placeholder or screenshot fails, create placeholder
    if force_placeholder or not capture_webpage_screenshot(url, output_path, size):
        logger.warning(f"Creating placeholder for {domain_name}")
        img = create_placeholder_image(domain_name, size)
        img.save(output_path, 'JPEG', quality=85)

    return output_path


def main():
    """Command-line interface for the screenshot tool."""
    parser = argparse.ArgumentParser(description='Capture website thumbnails in 1:4 ratio')
    parser.add_argument('url', help='URL of the website to capture')
    parser.add_argument('-o', '--output', help='Output file path')
    parser.add_argument('-w', '--width', type=int, default=800, help='Thumbnail width')
    parser.add_argument('--height', type=int, default=200, help='Thumbnail height')
    parser.add_argument('-p', '--placeholder', action='store_true', help='Force placeholder image')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')

    args = parser.parse_args()

    # Validate aspect ratio
    if args.width / args.height != 4:
        print("Warning: Dimensions do not maintain 1:4 aspect ratio. Recommended sizes: 800x200, 1200x300, etc.")

    # Set logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    try:
        # Capture thumbnail
        result = capture_thumbnail(
            args.url,
            args.output,
            (args.width, args.height),
            args.placeholder
        )
        print(f"Thumbnail saved to {result}")
        return 0
    except Exception as e:
        print(f"Failed to capture thumbnail: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

# Wymagane zależności:
# pip install selenium webdriver-manager pillow requests