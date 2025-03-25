import os
import re
import git
import json
import time
import hashlib
import logging
import requests
import schedule
from PIL import Image
from io import BytesIO
from datetime import datetime, timedelta
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from sklearn.feature_extraction.text import TfidfVectorizer
# Detect technologies
from tech_patterns import tech_patterns
from common_themes import common_themes

from AdvancedContentAnalyzer import AdvancedContentAnalyzer, analyze_content


# Configuration
DOMAINS_FILE = "portfolio_http.txt"
OUTPUT_DIR = "media"
THUMBNAILS_DIR = os.path.join(OUTPUT_DIR, "thumbnails")
DATA_FILE = os.path.join(OUTPUT_DIR, "data.json")
GIT_REPO_PATH = OUTPUT_DIR
GIT_REMOTE = "origin"
GIT_BRANCH = "main"
HTTP_TIMEOUT = 10
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("portfolio_generator.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("portfolio_generator")


def normalize_url(url):
    """Normalize URL to standard format."""
    url = url.strip().lower()

    # Add http:// if no protocol specified
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url

    # Parse URL and reconstruct it
    parsed = urlparse(url)
    hostname = parsed.netloc

    # Remove www. if present
    if hostname.startswith('www.'):
        hostname = hostname[4:]

    # Return normalized URL
    return f"{parsed.scheme}://{hostname}"


def get_domain_content(url):
    """Fetch website content."""
    try:
        headers = {
            'User-Agent': USER_AGENT
        }
        response = requests.get(url, headers=headers, timeout=HTTP_TIMEOUT)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching {url}: {e}")
        return None


def generate_filename(self, url: str) -> str:
    """
    Generowanie nazwy pliku na podstawie URL.

    Args:
        url (str): Adres URL

    Returns:
        str: Znormalizowana nazwa pliku
    """
    parsed_url = urlparse(url)
    return f"{parsed_url.netloc.replace('.', '_').replace(':', '_')}.png"



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


def generate_description(site):
    """
    Generate a comprehensive description from the site data using NLP techniques.

    Args:
        site (dict): Dictionary containing site analysis data

    Returns:
        str: A natural language description of the website
    """
    # Extract site data
    theme = site.get('theme', 'general').lower()
    keywords = site.get('keywords', [])
    technologies = site.get('technologies', [])

    # If no keywords available, return basic description
    if not keywords:
        return f"This appears to be a {theme} website utilizing {', '.join(technologies[:2]) if technologies else 'standard web technologies'}."

    # Create more nuanced descriptions based on theme and keywords
    if theme == "e-commerce":
        primary_focus = keywords[0] if keywords else "products"
        secondary_items = ", ".join(keywords[1:3]) if len(keywords) > 1 else ""
        tech_stack = f" Built with {', '.join(technologies[:2])}" if technologies else ""

        if secondary_items:
            return f"An online store specializing in {primary_focus} with additional offerings including {secondary_items}.{tech_stack}"
        return f"An e-commerce platform focused on {primary_focus}.{tech_stack}"

    elif theme == "blog" or theme == "news":
        topics = ", ".join(keywords[:3])
        return f"A {theme} site covering topics such as {topics}, providing readers with informative content and insights."

    elif theme == "portfolio" or theme == "personal":
        focus = keywords[0] if keywords else "personal projects"
        return f"A {theme} website showcasing work in {focus}" + (
            f" and {', '.join(keywords[1:3])}" if len(keywords) > 1 else "") + "."

    elif theme == "corporate" or theme == "business":
        industry = keywords[0] if keywords else "business services"
        features = ", ".join(keywords[1:3]) if len(keywords) > 1 else "professional services"
        return f"A professional {theme} site for a company in the {industry} industry, highlighting their {features}."

    elif theme == "educational":
        subjects = ", ".join(keywords[:3]) if keywords else "various subjects"
        return f"An educational platform providing resources and information on {subjects}."

    # Default description with more natural language
    keyword_text = ", ".join(keywords[:3])
    tech_mention = f" Developed using {', '.join(technologies[:2])}" if technologies else ""

    descriptions = [
        f"A {theme} website that primarily focuses on {keyword_text}.{tech_mention}",
        f"This {theme} site specializes in {keyword_text}, offering visitors comprehensive information and resources.{tech_mention}",
        f"A platform dedicated to {keyword_text} with a {theme} approach.{tech_mention}"
    ]

    # Use a hash of the domain to consistently select the same description style
    domain_hash = hash(site.get('domain', '')) % len(descriptions)
    return descriptions[domain_hash]

def find_most_common_theme(portfolio_data):
    """Find the most common theme in the portfolio data."""
    themes = {}
    for site in portfolio_data:
        theme = site.get("theme", "Unknown")
        themes[theme] = themes.get(theme, 0) + 1

    if not themes:
        return "None"

    # Return the theme with the highest count
    return max(themes.items(), key=lambda x: x[1])[0]


def prepare_output_environment():
    """
    Prepare output directories and remove existing data file.

    Returns:
        bool: True if preparation was successful, False otherwise
    """
    try:
        # Remove existing data.json file
        if os.path.exists(DATA_FILE):
            os.remove(DATA_FILE)
            logger.info(f"Usunięto poprzedni plik {DATA_FILE}")

        # Create output directories
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        os.makedirs(THUMBNAILS_DIR, exist_ok=True)

        return True
    except Exception as e:
        logger.error(f"Error preparing output environment: {e}")
        return False


def load_domain_urls():
    """
    Load URLs from the domains file.

    Returns:
        list: List of domain URLs, or empty list if loading fails
    """
    try:
        from domain2url.load_urls_from_csv import load_urls_from_csv

        urls = load_urls_from_csv('portfolio_http.txt', only_available=True)
        logger.info(f"Loaded {len(urls)} domains from {DOMAINS_FILE}")
        return urls
    except Exception as e:
        logger.error(f"Error loading domains: {e}")
        return []


def process_single_domain(url_info, screenshotter=None):
    """
    Process a single domain for portfolio generation.

    Args:
        url_info (dict): Dictionary containing domain information
        screenshotter (ScreenshotCapture, optional): Screenshot capture instance

    Returns:
        dict or None: Site data dictionary if successful, None otherwise
    """
    try:
        # Extract URL and domain
        url = url_info['url']
        domain_name = url_info['domain']

        logger.info(f"Processing {domain_name}")

        # Fetch website content
        html_content = get_domain_content(url)
        if not html_content:
            logger.warning(f"Could not fetch content for {domain_name}")
            return None

        # Analyze content
        # print(html_content)
        analysis = analyze_content(html_content)

        # Capture thumbnail
        if screenshotter:
            thumbnail_path = screenshotter.capture(url)
        else:
            from screenshot.ScreenshotCapture import ScreenshotCapture
            screenshotter = ScreenshotCapture(output_dir="media/thumbnails")
            thumbnail_path = screenshotter.capture(url)

        # Create site data
        site_data = {
            "domain": domain_name,
            "url": url,
            "thumbnail": thumbnail_path,
            "theme": analysis["theme"],
            "keywords": analysis["keywords"],
            "technologies": analysis["technologies"],
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
            "description": ""
        }

        # Generate description
        site_data["description"] = generate_description(site_data)

        return site_data
    except Exception as e:
        logger.error(f"Error processing {url_info}: {e}")
        return None


def save_portfolio_data(existing_data):
    """
    Save portfolio data to JSON file.

    Args:
        existing_data (list): List of site data dictionaries

    Returns:
        bool: True if save was successful, False otherwise
    """
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, indent=2)

        logger.info(f"Saved data for {len(existing_data)} sites to {DATA_FILE}")
        logger.info(f"Added {len(existing_data)} new domains")

        return True
    except Exception as e:
        logger.error(f"Error saving portfolio data: {e}")
        return False


def one():
    """
    Main function to generate the portfolio using sequential screenshot capture.

    Returns:
        bool: True if portfolio generation was successful, False otherwise
    """
    try:
        # Prepare environment
        if not prepare_output_environment():
            return False

        # Load domain URLs
        urls = load_domain_urls()
        if not urls:
            return False

        # Process domains sequentially
        existing_data = []

        for url_info in urls:
            # Process single domain
            site_data = process_single_domain(url_info)

            if site_data:
                existing_data.append(site_data)

                # Minimal sleep to prevent potential rate limiting
                time.sleep(1)

        # Save portfolio data
        return save_portfolio_data(existing_data)

    except Exception as e:
        logger.error(f"Error in main_one function: {e}")
        return False


def multi():
    """
    Main function to generate the portfolio using parallel screenshot capture.

    Returns:
        bool: True if portfolio generation was successful, False otherwise
    """
    try:
        # Prepare environment
        if not prepare_output_environment():
            return False

        # Load domain URLs
        urls = load_domain_urls()
        if not urls:
            return False

        # Prepare URLs for parallel capture
        urls_to_capture = [url_info['url'] for url_info in urls]

        # Capture screenshots in parallel
        from screenshot.ScreenshotCapture import ScreenshotCapture
        screenshotter = ScreenshotCapture(output_dir="thumbnails")
        #screenshotter = ScreenshotCapture(output_dir="media/thumbnails")

        # Use multicapture to get screenshots
        try:
            thumbnail_paths = screenshotter.multicapture(urls_to_capture, max_workers=5, timeout=300)
            logger.info(f"Successfully captured {len(thumbnail_paths)} screenshots")
        except Exception as e:
            logger.error(f"Error in multicapture: {e}")
            thumbnail_paths = []

        # Create a mapping of URL to thumbnail path
        thumbnail_map = dict(zip(urls_to_capture, thumbnail_paths))

        # Process domains
        existing_data = []

        for url_info in urls:
            url = url_info['url']

            # Use multicapture result
            screenshotter.output_dir = "media/thumbnails"
            screenshotter.thumbnail_path = thumbnail_map.get(url)

            # Process single domain
            site_data = process_single_domain(url_info, screenshotter)

            if site_data:
                existing_data.append(site_data)

                # Minimal sleep to prevent potential rate limiting
                time.sleep(0.5)

        # Save portfolio data
        return save_portfolio_data(existing_data)

    except Exception as e:
        logger.error(f"Error in main function: {e}")
        return False

if __name__ == "__main__":
    # Run once
    success = one()
    # success = multi()

    if success:
        logger.info("Portfolio generation completed successfully")
    else:
        logger.error("Portfolio generation failed")


