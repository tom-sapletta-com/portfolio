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


def capture_thumbnail(current_url, domain_name):
    """
    Capture a thumbnail of the website.
    - Handles www and non-www versions of the domain
    - Only captures screenshot when page exists
    - Tries multiple approaches to get a representative image
    """
    try:
        # Try both www and non-www versions if needed


        headers = {
            'User-Agent': USER_AGENT
        }

        # Try each URL variation
        try:
            # First check if the page exists
            response = requests.head(current_url, headers=headers, timeout=HTTP_TIMEOUT / 2)

            # Skip to next URL if this one doesn't respond properly
            if response.status_code >= 400:
                logger.warning(f"URL {current_url} returned status code {response.status_code}")
                return false
            # Get the full page content
            response = requests.get(current_url, headers=headers, timeout=HTTP_TIMEOUT)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # Create thumbnails directory if it doesn't exist
            os.makedirs(THUMBNAILS_DIR, exist_ok=True)
            thumbnail_path = os.path.join(THUMBNAILS_DIR, f"{domain_name}.jpg")

            # Strategy 1: Try to find Open Graph image first (usually high quality and representative)
            og_image = soup.find('meta', property='og:image') or soup.find('meta', attrs={'name': 'og:image'})
            if og_image and og_image.get('content'):
                img_url = og_image.get('content')
                # Handle relative URLs
                if not img_url.startswith(('http://', 'https://')):
                    base_url = urlparse(current_url)
                    img_url = f"{base_url.scheme}://{base_url.netloc}{img_url if img_url.startswith('/') else '/' + img_url}"

                try:
                    img_response = requests.get(img_url, headers=headers, timeout=HTTP_TIMEOUT)
                    img_response.raise_for_status()
                    img = Image.open(BytesIO(img_response.content))

                    # Save thumbnail
                    img = img.convert('RGB')  # Convert to RGB for JPG
                    img.thumbnail((300, 200))  # Resize to thumbnail
                    img.save(thumbnail_path, 'JPEG', quality=85)
                    logger.info(f"Saved OG image thumbnail for {domain_name}")
                    return thumbnail_path
                except Exception as e:
                    logger.warning(f"Could not use og:image for {current_url}: {e}")

            # Strategy 2: Try to find Twitter Card image
            twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
            if twitter_image and twitter_image.get('content'):
                img_url = twitter_image.get('content')
                if not img_url.startswith(('http://', 'https://')):
                    base_url = urlparse(current_url)
                    img_url = f"{base_url.scheme}://{base_url.netloc}{img_url if img_url.startswith('/') else '/' + img_url}"

                try:
                    img_response = requests.get(img_url, headers=headers, timeout=HTTP_TIMEOUT)
                    img_response.raise_for_status()
                    img = Image.open(BytesIO(img_response.content))

                    # Save thumbnail
                    img = img.convert('RGB')
                    img.thumbnail((300, 200))
                    img.save(thumbnail_path, 'JPEG', quality=85)
                    logger.info(f"Saved Twitter Card image thumbnail for {domain_name}")
                    return thumbnail_path
                except Exception as e:
                    logger.warning(f"Could not use twitter:image for {current_url}: {e}")

            # Strategy 3: Find the largest image on the page
            largest_image = None
            max_size = 0
            min_acceptable_size = 5000  # Minimum pixel count (e.g., 50x100)

            for img in soup.find_all('img'):
                src = img.get('src')
                if not src:
                    continue

                # Skip tiny icons, spacers, etc.
                if any(skip in src.lower() for skip in ['icon', 'logo', 'spacer', 'blank', 'pixel']):
                    continue

                # Convert relative URLs to absolute
                if not src.startswith(('http://', 'https://')):
                    base_url = urlparse(current_url)
                    src = f"{base_url.scheme}://{base_url.netloc}{src if src.startswith('/') else '/' + src}"

                try:
                    img_response = requests.get(src, headers=headers, timeout=HTTP_TIMEOUT / 2)
                    img_response.raise_for_status()
                    img = Image.open(BytesIO(img_response.content))

                    # Calculate image size
                    size = img.width * img.height

                    # Update largest image if this one is bigger
                    if size > max_size and size > min_acceptable_size:
                        max_size = size
                        largest_image = img
                except Exception:
                    continue

            # Save the largest image as thumbnail
            if largest_image:
                largest_image = largest_image.convert('RGB')  # Convert to RGB for JPG
                largest_image.thumbnail((300, 200))  # Resize to thumbnail
                largest_image.save(thumbnail_path, 'JPEG', quality=85)
                logger.info(f"Saved largest image thumbnail for {domain_name}")
                return thumbnail_path

            # Strategy 4: Create a placeholder with domain initials
            logger.warning(f"No suitable images found for {domain_name}, creating placeholder")
            initials = get_initials(domain_name)
            color = get_color_for_domain(domain_name)

            # Create a placeholder image with the domain's initials
            img = Image.new('RGB', (300, 200), f"#{color}")
            # Would need PIL's ImageDraw to add text, but we'll skip that for simplicity
            img.save(thumbnail_path, 'JPEG', quality=85)
            logger.info(f"Created placeholder thumbnail for {domain_name}")
            return thumbnail_path

        except requests.exceptions.RequestException as e:
            logger.warning(f"Error accessing {current_url}: {e}")
            return False

        # If we get here, all URL variations failed
        logger.error(f"All URL variations failed for {domain_name}")
        return None

    except Exception as e:
        logger.error(f"Error capturing thumbnail for {url}: {e}")
        return None


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

def main():
    """Main function to generate the portfolio."""
    try:
        # Create output directories
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        os.makedirs(THUMBNAILS_DIR, exist_ok=True)

        # Load existing data if available
        existing_data = []
        existing_domains = {}

        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)

                # Create a lookup dictionary for faster access
                for site in existing_data:
                    existing_domains[site.get("domain", "")] = site

                logger.info(f"Loaded {len(existing_data)} existing sites from {DATA_FILE}")
            except Exception as e:
                logger.error(f"Error loading existing data: {e}")

        # Load domains from file
        try:
            from domain2url.load_urls_from_csv import load_urls_from_csv

            urls = load_urls_from_csv('portfolio_http.txt', only_available=True)
            logger.info(f"Loaded {len(urls)} domains from {DOMAINS_FILE}")
        except Exception as e:
            logger.error(f"Error loading domains: {e}")
            urls = []

        # Process each domain
        new_domains = 0
        updated_domains = 0

        for url_info in urls:
            try:
                # Extract URL and domain
                url = url_info['url']
                domain_name = url_info['domain']

                logger.info(f"Processing {domain_name}")

                # Check if we already have data for this domain
                if domain_name in existing_domains:
                    # Skip if processed recently (less than 7 days ago)
                    last_updated = existing_domains[domain_name].get("last_updated", "")
                    if last_updated:
                        try:
                            last_date = datetime.strptime(last_updated, "%Y-%m-%d")
                            days_since_update = (datetime.now() - last_date).days
                            if days_since_update < 7:
                                logger.info(f"Skipping {domain_name} - updated {days_since_update} days ago")
                                continue
                        except Exception:
                            # If date parsing fails, process anyway
                            pass

                # Fetch website content
                html_content = get_domain_content(url)
                if not html_content:
                    logger.warning(f"Could not fetch content for {domain_name}")
                    continue

                # Analyze content
                analysis = analyze_content(html_content)

                # Capture thumbnail
                thumbnail_path = capture_thumbnail(url, domain_name)

                # Create or update site data
                site_data = {
                    "domain": domain_name,
                    "url": url,
                    "theme": analysis["theme"],
                    "keywords": analysis["keywords"],
                    "technologies": analysis["technologies"],
                    "last_updated": datetime.now().strftime("%Y-%m-%d"),
                    "description": ""
                }

                # Generate description
                site_data["description"] = generate_description(site_data)

                # Update existing data or add new entry
                if domain_name in existing_domains:
                    # Update existing entry
                    for i, site in enumerate(existing_data):
                        if site.get("domain") == domain_name:
                            existing_data[i] = site_data
                            break
                    updated_domains += 1
                    logger.info(f"Updated data for {domain_name}")
                else:
                    # Add new entry
                    existing_data.append(site_data)
                    new_domains += 1
                    logger.info(f"Added new data for {domain_name}")

                # Sleep to avoid rate limiting
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error processing {url_info}: {e}")

        # Save updated data
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, indent=2)

        logger.info(f"Saved data for {len(existing_data)} sites to {DATA_FILE}")
        logger.info(f"Added {new_domains} new domains, updated {updated_domains} existing domains")

        return True
    except Exception as e:
        logger.error(f"Error in main function: {e}")
        return False

if __name__ == "__main__":
    # Run once
    success = main()

    if success:
        logger.info("Portfolio generation completed successfully")
    else:
        logger.error("Portfolio generation failed")


