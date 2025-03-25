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

def analyze_content(html_content):
    """Analyze website content to identify theme and technologies."""
    if not html_content:
        return {
            "theme": "Unknown",
            "keywords": [],
            "technologies": []
        }

    soup = BeautifulSoup(html_content, 'html.parser')

    # Extract text for theme/keywords analysis
    text_content = soup.get_text(separator=' ', strip=True)

    # Very simple NLP with TF-IDF to extract keywords
    try:
        # Simple preprocessing
        text_content = re.sub(r'\s+', ' ', text_content).lower()

        # Extract keywords with TF-IDF
        vectorizer = TfidfVectorizer(
            max_features=100,
            stop_words='english',
            ngram_range=(1, 2)
        )

        # Ensure we have enough text to analyze
        if len(text_content.split()) < 10:
            keywords = []
        else:
            tfidf_matrix = vectorizer.fit_transform([text_content])
            feature_names = vectorizer.get_feature_names_out()

            # Get top keywords
            scores = zip(feature_names, tfidf_matrix.toarray()[0])
            sorted_scores = sorted(scores, key=lambda x: x[1], reverse=True)
            keywords = [word for word, score in sorted_scores[:10] if score > 0]

        # Cluster text to identify theme
        if len(text_content.split()) < 20:
            theme = "Unknown"
        else:
            # Simple theme identification based on keyword frequency

            # Count theme keywords in content
            theme_scores = {}
            for theme_name, theme_keywords in common_themes.items():
                score = sum(1 for keyword in theme_keywords if keyword in text_content)
                if score > 0:
                    theme_scores[theme_name] = score

            # Select theme with highest score
            if theme_scores:
                theme = max(theme_scores.items(), key=lambda x: x[1])[0]
            else:
                theme = "General"

        # Detect technologies
        technologies = []
        html_str = str(soup).lower()

        for tech, patterns in tech_patterns.items():
            for pattern in patterns:
                if pattern.lower() in html_str:
                    technologies.append(tech)
                    break

        # Remove duplicates
        technologies = list(set(technologies))

        return {
            "theme": theme,
            "keywords": keywords,
            "technologies": technologies
        }
    except Exception as e:
        logger.error(f"Error analyzing content: {e}")
        return {
            "theme": "Unknown",
            "keywords": [],
            "technologies": []
        }



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
    """Generate a brief description from the site data."""
    keywords = site.get("keywords", [])
    if not keywords:
        return f"This appears to be a {site.get('theme', 'general').lower()} website."

    keyword_text = ", ".join(keywords[:3])
    return f"This {site.get('theme', 'website').lower()} focuses on {keyword_text}."

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
        screenshotter = ScreenshotCapture(output_dir="media/thumbnails")

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


