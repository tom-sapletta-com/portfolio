#!/usr/bin/env python3
import os
import argparse
import logging
import requests
from PIL import Image
from io import BytesIO
from urllib.parse import urlparse
from bs4 import BeautifulSoup

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

# Constants
HTTP_TIMEOUT = 10
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"


def get_color_for_domain(domain):
    """Generate a consistent color hex code for a domain."""
    hash_value = 0
    for char in domain:
        hash_value = ((hash_value << 5) - hash_value) + ord(char)
        hash_value = hash_value & 0xFFFFFF

    # Convert to hex and ensure it's 6 characters
    hex_color = format(hash_value & 0xFFFFFF, '06x')
    return hex_color


def get_initials(domain):
    """Get initials from domain name."""
    domain_name = domain.split('.')[0]
    if len(domain_name) >= 2:
        return domain_name[:2].upper()
    return domain_name.upper()


def capture_thumbnail(url, output_path=None, size=(300, 200), quality=85):
    """
    Capture a thumbnail of the website.

    Parameters:
    -----------
    url : str
        The URL of the website to capture
    output_path : str, optional
        Path where to save the thumbnail. If None, returns the image object
    size : tuple, optional
        Size of the thumbnail (width, height)
    quality : int, optional
        JPEG quality (1-100)

    Returns:
    --------
    str or PIL.Image
        Path to the saved thumbnail or Image object if output_path is None
    """
    try:
        # Extract domain name for placeholder generation if needed
        parsed_url = urlparse(url)
        domain_name = parsed_url.netloc
        if domain_name.startswith('www.'):
            domain_name = domain_name[4:]

        headers = {
            'User-Agent': USER_AGENT
        }

        # First check if the page exists
        response = requests.head(url, headers=headers, timeout=HTTP_TIMEOUT / 2)

        # Skip if URL doesn't respond properly
        if response.status_code >= 400:
            logger.warning(f"URL {url} returned status code {response.status_code}")
            return False

        # Get the full page content
        response = requests.get(url, headers=headers, timeout=HTTP_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Create output directory if needed and output_path is provided
        if output_path:
            os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

        # Strategy 1: Try to find Open Graph image first (usually high quality and representative)
        og_image = soup.find('meta', property='og:image') or soup.find('meta', attrs={'name': 'og:image'})
        if og_image and og_image.get('content'):
            img_url = og_image.get('content')
            # Handle relative URLs
            if not img_url.startswith(('http://', 'https://')):
                base_url = urlparse(url)
                img_url = f"{base_url.scheme}://{base_url.netloc}{img_url if img_url.startswith('/') else '/' + img_url}"

            try:
                img_response = requests.get(img_url, headers=headers, timeout=HTTP_TIMEOUT)
                img_response.raise_for_status()
                img = Image.open(BytesIO(img_response.content))

                # Convert to RGB for JPG
                img = img.convert('RGB')
                # Resize to thumbnail
                img.thumbnail(size)

                if output_path:
                    img.save(output_path, 'JPEG', quality=quality)
                    logger.info(f"Saved OG image thumbnail for {domain_name}")
                    return output_path
                return img
            except Exception as e:
                logger.warning(f"Could not use og:image for {url}: {e}")

        # Strategy 2: Try to find Twitter Card image
        twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
        if twitter_image and twitter_image.get('content'):
            img_url = twitter_image.get('content')
            if not img_url.startswith(('http://', 'https://')):
                base_url = urlparse(url)
                img_url = f"{base_url.scheme}://{base_url.netloc}{img_url if img_url.startswith('/') else '/' + img_url}"

            try:
                img_response = requests.get(img_url, headers=headers, timeout=HTTP_TIMEOUT)
                img_response.raise_for_status()
                img = Image.open(BytesIO(img_response.content))

                # Convert to RGB for JPG
                img = img.convert('RGB')
                # Resize to thumbnail
                img.thumbnail(size)

                if output_path:
                    img.save(output_path, 'JPEG', quality=quality)
                    logger.info(f"Saved Twitter Card image thumbnail for {domain_name}")
                    return output_path
                return img
            except Exception as e:
                logger.warning(f"Could not use twitter:image for {url}: {e}")

        # Strategy 3: Find the largest image on the page
        largest_image = None
        max_size = 0
        min_acceptable_size = 5000  # Minimum pixel count (e.g., 50x100)

        for img_tag in soup.find_all('img'):
            src = img_tag.get('src')
            if not src:
                continue

            # Skip tiny icons, spacers, etc.
            if any(skip in src.lower() for skip in ['icon', 'logo', 'spacer', 'blank', 'pixel']):
                continue

            # Convert relative URLs to absolute
            if not src.startswith(('http://', 'https://')):
                base_url = urlparse(url)
                src = f"{base_url.scheme}://{base_url.netloc}{src if src.startswith('/') else '/' + src}"

            try:
                img_response = requests.get(src, headers=headers, timeout=HTTP_TIMEOUT / 2)
                img_response.raise_for_status()
                img = Image.open(BytesIO(img_response.content))

                # Calculate image size
                size_pixels = img.width * img.height

                # Update largest image if this one is bigger
                if size_pixels > max_size and size_pixels > min_acceptable_size:
                    max_size = size_pixels
                    largest_image = img
            except Exception:
                continue

        # Save the largest image as thumbnail
        if largest_image:
            largest_image = largest_image.convert('RGB')  # Convert to RGB for JPG
            largest_image.thumbnail(size)  # Resize to thumbnail

            if output_path:
                largest_image.save(output_path, 'JPEG', quality=quality)
                logger.info(f"Saved largest image thumbnail for {domain_name}")
                return output_path
            return largest_image

        # Strategy 4: Create a placeholder with domain initials
        logger.warning(f"No suitable images found for {domain_name}, creating placeholder")
        initials = get_initials(domain_name)
        color = get_color_for_domain(domain_name)

        # Create a placeholder image with the domain's initials
        img = Image.new('RGB', size, f"#{color}")
        # Would need PIL's ImageDraw to add text, but we'll skip that for simplicity

        if output_path:
            img.save(output_path, 'JPEG', quality=quality)
            logger.info(f"Created placeholder thumbnail for {domain_name}")
            return output_path
        return img

    except Exception as e:
        logger.error(f"Error capturing thumbnail for {url}: {e}")
        return None


def main():
    """Command-line interface for the screenshot tool."""
    parser = argparse.ArgumentParser(description='Capture website thumbnails')
    parser.add_argument('url', help='URL of the website to capture')
    parser.add_argument('-o', '--output', help='Output file path', default='thumbnail.jpg')
    parser.add_argument('-w', '--width', type=int, default=300, help='Thumbnail width')
    parser.add_argument('--height', type=int, default=200, help='Thumbnail height')  # Removed -h
    parser.add_argument('-q', '--quality', type=int, default=85, help='JPEG quality (1-100)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')

    args = parser.parse_args()

    # Set logging level based on verbose flag
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Capture thumbnail
    result = capture_thumbnail(
        args.url,
        args.output,
        (args.width, args.height),
        args.quality
    )

    if result:
        print(f"Thumbnail saved to {args.output}")
        return 0
    else:
        print(f"Failed to capture thumbnail for {args.url}")
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
