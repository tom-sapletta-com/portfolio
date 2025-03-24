#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Portfolio Generator - Analyzes websites and creates a portfolio page
"""

import os
import re
import sys
import time
import logging
import requests
import schedule
import datetime
import subprocess
import threading
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import MiniBatchKMeans
import numpy as np
import git
from PIL import Image
from io import BytesIO
import json
import hashlib

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("portfolio_generator.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("portfolio_generator")

# Configuration
DOMAINS_FILE = "portfolio.txt"
OUTPUT_DIR = "portfolio"
HTML_OUTPUT = os.path.join(OUTPUT_DIR, "index.html")
THUMBNAILS_DIR = os.path.join(OUTPUT_DIR, "thumbnails")
DATA_FILE = os.path.join(OUTPUT_DIR, "data.json")
GIT_REPO_PATH = OUTPUT_DIR
GIT_REMOTE = "origin"
GIT_BRANCH = "main"
HTTP_TIMEOUT = 15  # seconds
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"


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


def capture_thumbnail(url, domain_name):
    """Capture a thumbnail of the website."""
    try:
        # Since we can't use Selenium or similar tools with the resource constraints,
        # we'll try to find and use the largest image on the page as a thumbnail
        headers = {
            'User-Agent': USER_AGENT
        }
        response = requests.get(url, headers=headers, timeout=HTTP_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Try to find the largest image
        largest_image = None
        max_size = 0
        
        # Check for open graph image first
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            img_url = og_image.get('content')
            if not img_url.startswith(('http://', 'https://')):
                base_url = urlparse(url)
                img_url = f"{base_url.scheme}://{base_url.netloc}{img_url}"
            
            try:
                img_response = requests.get(img_url, headers=headers, timeout=HTTP_TIMEOUT)
                img_response.raise_for_status()
                img = Image.open(BytesIO(img_response.content))
                
                # Save thumbnail
                os.makedirs(THUMBNAILS_DIR, exist_ok=True)
                thumbnail_path = os.path.join(THUMBNAILS_DIR, f"{domain_name}.jpg")
                img = img.convert('RGB')  # Convert to RGB for JPG
                img.thumbnail((300, 200))  # Resize to thumbnail
                img.save(thumbnail_path, 'JPEG')
                return thumbnail_path
            except Exception as e:
                logger.warning(f"Could not use og:image for {url}: {e}")
        
        # If og:image fails, try to find the largest image
        for img in soup.find_all('img'):
            src = img.get('src')
            if not src:
                continue
                
            # Convert relative URLs to absolute
            if not src.startswith(('http://', 'https://')):
                base_url = urlparse(url)
                src = f"{base_url.scheme}://{base_url.netloc}{src}"
            
            # Get image dimensions from attributes or download and check
            width = img.get('width')
            height = img.get('height')
            
            try:
                if width and height:
                    size = int(width) * int(height)
                else:
                    img_response = requests.get(src, headers=headers, timeout=HTTP_TIMEOUT)
                    img_response.raise_for_status()
                    img_obj = Image.open(BytesIO(img_response.content))
                    size = img_obj.width * img_obj.height
                
                if size > max_size:
                    max_size = size
                    largest_image = src
            except Exception as e:
                continue
        
        # Use the largest image as thumbnail
        if largest_image:
            try:
                img_response = requests.get(largest_image, headers=headers, timeout=HTTP_TIMEOUT)
                img_response.raise_for_status()
                img = Image.open(BytesIO(img_response.content))
                
                # Save thumbnail
                os.makedirs(THUMBNAILS_DIR, exist_ok=True)
                thumbnail_path = os.path.join(THUMBNAILS_DIR, f"{domain_name}.jpg")
                img = img.convert('RGB')  # Convert to RGB for JPG
                img.thumbnail((300, 200))  # Resize to thumbnail
                img.save(thumbnail_path, 'JPEG')
                return thumbnail_path
            except Exception as e:
                logger.error(f"Error creating thumbnail for {url}: {e}")
        
        # If all fails, create a placeholder thumbnail with domain name
        os.makedirs(THUMBNAILS_DIR, exist_ok=True)
        thumbnail_path = os.path.join(THUMBNAILS_DIR, f"{domain_name}.jpg")
        img = Image.new('RGB', (300, 200), color=(73, 109, 137))
        return thumbnail_path
    
    except Exception as e:
        logger.error(f"Error capturing thumbnail for {url}: {e}")
        # Create a placeholder thumbnail
        os.makedirs(THUMBNAILS_DIR, exist_ok=True)
        thumbnail_path = os.path.join(THUMBNAILS_DIR, f"{domain_name}.jpg")
        img = Image.new('RGB', (300, 200), color=(200, 200, 200))
        return thumbnail_path


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
            common_themes = {
                "ecommerce": ["shop", "cart", "product", "buy", "price", "store", "shipping"],
                "blog": ["blog", "post", "article", "author", "comment", "read"],
                "portfolio": ["portfolio", "work", "project", "gallery", "showcase"],
                "corporate": ["company", "business", "service", "solution", "client", "partner"],
                "news": ["news", "article", "latest", "update", "publish", "press"],
                "education": ["course", "class", "learn", "student", "education", "training"],
                "technology": ["tech", "software", "application", "digital", "innovation"]
            }
            
            theme_scores = {}
            for theme_name, theme_keywords in common_themes.items():
                score = sum(1 for keyword in theme_keywords if keyword in text_content.lower())
                theme_scores[theme_name] = score
            
            theme = max(theme_scores.items(), key=lambda x: x[1])[0] if any(theme_scores.values()) else "Unknown"
        
        # Identify technologies - check for common frameworks and libraries
        technologies = []
        
        # JavaScript frameworks
        if "react" in html_content.lower() or "reactjs" in html_content.lower():
            technologies.append("React")
        if "vue" in html_content.lower() or "vuejs" in html_content.lower():
            technologies.append("Vue.js")
        if "angular" in html_content.lower():
            technologies.append("Angular")
        if "jquery" in html_content.lower():
            technologies.append("jQuery")
        
        # CSS frameworks
        if "bootstrap" in html_content.lower():
            technologies.append("Bootstrap")
        if "tailwind" in html_content.lower():
            technologies.append("Tailwind CSS")
        if "bulma" in html_content.lower():
            technologies.append("Bulma")
        
        # CMS
        if "wordpress" in html_content.lower():
            technologies.append("WordPress")
        if "drupal" in html_content.lower():
            technologies.append("Drupal")
        if "joomla" in html_content.lower():
            technologies.append("Joomla")
        if "shopify" in html_content.lower():
            technologies.append("Shopify")
        
        # Analytics
        if "google analytics" in html_content.lower() or "ga.js" in html_content.lower() or "analytics.js" in html_content.lower():
            technologies.append("Google Analytics")
        
        # Generate hashtags from keywords and theme
        hashtags = [f"#{keyword.replace(' ', '')}" for keyword in keywords[:5]]
        hashtags.append(f"#{theme}")
        
        return {
            "theme": theme.capitalize(),
            "keywords": keywords,
            "technologies": technologies,
            "hashtags": hashtags
        }
    
    except Exception as e:
        logger.error(f"Error analyzing content: {e}")
        return {
            "theme": "Unknown",
            "keywords": [],
            "technologies": [],
            "hashtags": []
        }


def generate_html(portfolio_data):
    """Generate HTML for the portfolio page."""
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Website Portfolio Analysis</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
                color: #333;
            }}
            h1 {{
                text-align: center;
                margin-bottom: 30px;
                color: #2c3e50;
            }}
            .portfolio-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                gap: 25px;
                margin: 0 auto;
                max-width: 1200px;
            }}
            .portfolio-item {{
                background-color: white;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                transition: transform 0.3s ease, box-shadow 0.3s ease;
            }}
            .portfolio-item:hover {{
                transform: translateY(-5px);
                box-shadow: 0 10px 20px rgba(0,0,0,0.15);
            }}
            .thumbnail {{
                width: 100%;
                height: 200px;
                object-fit: cover;
                border-bottom: 1px solid #eee;
            }}
            .content {{
                padding: 15px;
            }}
            .domain {{
                font-size: 18px;
                font-weight: 600;
                margin-bottom: 10px;
                color: #2c3e50;
            }}
            .theme {{
                font-weight: 500;
                margin-bottom: 8px;
                color: #3498db;
            }}
            .description, .technologies {{
                margin-bottom: 8px;
                font-size: 14px;
                color: #666;
            }}
            .hashtags {{
                display: flex;
                flex-wrap: wrap;
                gap: 5px;
                margin-top: 10px;
            }}
            .hashtag {{
                background-color: #e1f5fe;
                color: #0288d1;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
            }}
            .date-info {{
                text-align: center;
                margin-top: 30px;
                color: #7f8c8d;
                font-size: 14px;
            }}
            a {{
                color: #2c3e50;
                text-decoration: none;
            }}
            a:hover {{
                text-decoration: underline;
            }}
            .header {{
                text-align: center;
                margin-bottom: 40px;
            }}
            .stats {{
                margin: 20px auto;
                max-width: 800px;
                background-color: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .search-container {{
                margin: 0 auto 30px;
                max-width: 600px;
                text-align: center;
            }}
            #searchInput {{
                width: 100%;
                padding: 12px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 16px;
                box-sizing: border-box;
            }}
            .tech-tag {{
                display: inline-block;
                background-color: #f1f1f1;
                padding: 4px 8px;
                margin-right: 5px;
                margin-bottom: 5px;
                border-radius: 4px;
                font-size: 12px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Website Portfolio Analysis</h1>
            <p>Automated analysis of websites to identify themes, technologies, and content patterns</p>
        </div>

        <div class="search-container">
            <input type="text" id="searchInput" placeholder="Search by domain, technology, theme, or keywords...">
        </div>

        <div class="stats">
            <h2>Portfolio Stats</h2>
            <p>Total websites analyzed: <strong>{total_websites}</strong></p>
            <p>Most common theme: <strong>{most_common_theme}</strong></p>
            <p>Most used technologies:</p>
            <div>
                {tech_tags}
            </div>
        </div>

        <div class="portfolio-grid">
    """

    # Add each portfolio item
    for site in portfolio_data:
        html += """
            <div class="portfolio-item" data-domain="{domain}" data-theme="{theme}" data-keywords="{keywords}" data-tech="{technologies}">
                <img src="{thumbnail}" alt="{domain}" class="thumbnail" onerror="this.onerror=null; this.src='data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"300\" height=\"200\" viewBox=\"0 0 300 200\"><rect fill=\"%23{color}\" width=\"300\" height=\"200\"/><text fill=\"%23fff\" font-family=\"Arial\" font-size=\"30\" font-weight=\"bold\" text-anchor=\"middle\" x=\"150\" y=\"110\">{initials}</text></svg>';">
                <div class="content">
                    <div class="domain"><a href="{url}" target="_blank">{domain}</a></div>
                    <div class="theme">{theme}</div>
                    <div class="technologies">Technologies: {technologies_list}</div>
                    <div class="description">
                        {description}
                    </div>
                    <div class="hashtags">
                        {hashtags}
                    </div>
                </div>
            </div>
        """.format(
            domain=site.get("domain", "Unknown"),
            url=site.get("url", "#"),
            thumbnail=os.path.join("thumbnails", f"{site.get('domain_hash')}.jpg"),
            color=get_color_for_domain(site.get("domain", "Unknown")),
            initials=get_initials(site.get("domain", "Unknown")),
            theme=site.get("theme", "Unknown"),
            keywords=" ".join(site.get("keywords", [])),
            technologies=" ".join(site.get("technologies", [])),
            technologies_list=", ".join(site.get("technologies", ["Not detected"])),
            description=generate_description(site),
            hashtags="".join([f'<span class="hashtag">{tag}</span>' for tag in site.get("hashtags", [])])
        )

    # Add footer and JavaScript for search functionality
    html += """
        </div>

        <div class="date-info">
            <p>Last updated: {date}</p>
        </div>

        <script>
            document.addEventListener('DOMContentLoaded', function() {
                const searchInput = document.getElementById('searchInput');
                const portfolioItems = document.querySelectorAll('.portfolio-item');

                searchInput.addEventListener('keyup', function() {
                    const searchTerm = this.value.toLowerCase();

                    portfolioItems.forEach(item => {
                        const domain = item.getAttribute('data-domain').toLowerCase();
                        const theme = item.getAttribute('data-theme').toLowerCase();
                        const keywords = item.getAttribute('data-keywords').toLowerCase();
                        const tech = item.getAttribute('data-tech').toLowerCase();

                        if (domain.includes(searchTerm) || 
                            theme.includes(searchTerm) || 
                            keywords.includes(searchTerm) || 
                            tech.includes(searchTerm)) {
                            item.style.display = 'block';
                        } else {
                            item.style.display = 'none';
                        }
                    });
                });
            });
        </script>
    </body>
    </html>
    """.format(date=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))

    return html


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


def find_most_common_theme(portfolio_data):
    """Find the most common theme in the portfolio data."""
    themes = {}
    for site in portfolio_data:
        theme = site.get("theme", "Unknown")
        themes[theme] = themes.get(theme, 0) + 1
    
    if not themes:
        return "None"
    
    return max(themes.items(), key=lambda x: x[1])[0]


def generate_tech_tags(portfolio_data):
    """Generate HTML for most used technology tags."""
    tech_counts = {}
    for site in portfolio_data:
        for tech in site.get("technologies", []):
            tech_counts[tech] = tech_counts.get(tech, 0) + 1
    
    # Sort by count
    sorted_techs = sorted(tech_counts.items(), key=lambda x: x[1], reverse=True)
    
    # Generate HTML tags for top 10 technologies
    tags = ""
    for tech, count in sorted_techs[:10]:
        tags += f'<span class="tech-tag">{tech} ({count})</span>'
    
    return tags or "<span>No technologies detected</span>"


def generate_description(site):
    """Generate a brief description from the site data."""
    keywords = site.get("keywords", [])
    if not keywords:
        return f"This appears to be a {site.get('theme', 'general').lower()} website."
    
    keyword_text = ", ".join(keywords[:3])
    return f"This {site.get('theme', 'website').lower()} focuses on {keyword_text}."


def init_git_repo():
    """Initialize or update git repository."""
    try:
        # Ensure output directory exists
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # Check if it's already a git repo
        try:
            repo = git.Repo(GIT_REPO_PATH)
            logger.info("Git repository already initialized")
        except git.exc.InvalidGitRepositoryError:
            # Initialize new repo
            repo = git.Repo.init(GIT_REPO_PATH)
            logger.info("Initialized new git repository")
            
            # Add .gitignore
            with open(os.path.join(GIT_REPO_PATH, ".gitignore"), "w") as f:
                f.write("*.log\n__pycache__/\n*.py[cod]\n*$py.class\n")
            
            # Initial commit
            repo.git.add(".")
            repo.git.commit("-m", "Initial commit")
            logger.info("Created initial commit")
        
        # Check if remote exists
        try:
            remote_exists = GIT_REMOTE in [remote.name for remote in repo.remotes]
            if not remote_exists:
                logger.warning(f"Remote '{GIT_REMOTE}' does not exist. Please add it manually.")
        except Exception as e:
            logger.warning(f"Error checking git remote: {e}")
        
        return repo
    except Exception as e:
        logger.error(f"Error initializing git repository: {e}")
        return None


def push_to_git():
    """Commit changes and push to git repository."""
    try:
        repo = git.Repo(GIT_REPO_PATH)
        
        # Check if there are changes
        if not repo.is_dirty() and not repo.untracked_files:
            logger.info("No changes to commit")
            return
        
        # Add all changes
        repo.git.add(".")
        
        # Commit
        commit_message = f"Update portfolio on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
        repo.git.commit("-m", commit_message)
        logger.info(f"Committed changes: {commit_message}")
        
        # Push to remote if it exists
        try:
            if GIT_REMOTE in [remote.name for remote in repo.remotes]:
                repo.git.push(GIT_REMOTE, GIT_BRANCH)
                logger.info(f"Pushed to {GIT_REMOTE}/{GIT_BRANCH}")
            else:
                logger.warning(f"Remote '{GIT_REMOTE}' not found. Could not push changes.")
        except Exception as e:
            logger.warning(f"Error pushing to remote: {e}")
    
    except Exception as e:
        logger.error(f"Error in git operations: {e}")


def run_portfolio_generation():
    """Main function to run the portfolio generation process."""
    logger.info("Starting portfolio generation process")
    
    # Ensure output directories exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(THUMBNAILS_DIR, exist_ok=True)
    
    # Initialize git repository
    repo = init_git_repo()
    
    # Load existing data if available
    portfolio_data = []
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                portfolio_data = json.load(f)
            logger.info(f"Loaded {len(portfolio_data)} existing entries from data file")
        except Exception as e:
            logger.error(f"Error loading existing data: {e}")
    
    # Create a dictionary for quick lookup of existing domains
    existing_domains = {site["domain"]: site for site in portfolio_data}
    
    # Read domains from file
    try:
        with open(DOMAINS_FILE, 'r', encoding='utf-8') as f:
            domains = [line.strip() for line in f if line.strip()]
        logger.info(f"Loaded {len(domains)} domains from {DOMAINS_FILE}")
    except Exception as e:
        logger.error(f"Error loading domains file: {e}")
        domains = []
    
    # Process each domain
    new_domains = 0
    updated_domains = 0
    
    for domain in domains:
        try:
            # Normalize URL
            url = normalize_url(domain)
            domain_name = urlparse(url).netloc
            
            # Create a hash of the domain name for filenames
            domain_hash = hashlib.md5(domain_name.encode()).hexdigest()
            
            logger.info(f"Processing {domain_name}")
            
            # Check if we already have data for this domain
            if domain_name in existing_domains:
                # Skip if processed recently (less than 7 days ago)
                last_updated = existing_domains[domain_name].get("last_updated", "")
                if last_updated:
                    try:
                        last_date = datetime.datetime.strptime(last_updated, "%Y-%m-%d %H:%M:%S")
                        days_since_update = (datetime.datetime.now() - last_date).days
                        if days_since_update < 7:
                            logger.info(f"Skipping {domain_name} - updated {days_since_update} days ago")
                            continue
                    except Exception:
                        pass  # If date parsing fails, we'll just update anyway
            
            # Fetch content from the website
            html_content = get_domain_content(url)
            
            if not html_content:
                logger.warning(f"Could not fetch content for {domain_name}")
                continue
            
            # Analyze the content
            analysis = analyze_content(html_content)
            
            # Capture thumbnail
            thumbnail_path = capture_thumbnail(url, domain_hash)
            
            # Create or update the site data
            site_data = {
                "domain": domain_name,
                "domain_hash": domain_hash,
                "url": url,
                "theme": analysis.get("theme", "Unknown"),
                "keywords": analysis.get("keywords", []),
                "technologies": analysis.get("technologies", []),
                "hashtags": analysis.get("hashtags", []),
                "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Update existing entry or add new one
            if domain_name in existing_domains:
                for i, site in enumerate(portfolio_data):
                    if site["domain"] == domain_name:
                        portfolio_data[i] = site_data
                        break
                updated_domains += 1
            else:
                portfolio_data.append(site_data)
                new_domains += 1
            
            # Save after each domain in case of interruptions
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(portfolio_data, f, indent=2, ensure_ascii=False)
            
            # Don't hammer servers
            time.sleep(2)
        
        except Exception as e:
            logger.error(f"Error processing domain {domain}: {e}")
    
    # Sort portfolio by last updated date
    portfolio_data.sort(key=lambda x: x.get("last_updated", ""), reverse=True)
    
    # Generate HTML
    html_content = generate_html(portfolio_data)
    
    # Write HTML file
    with open(HTML_OUTPUT, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    logger.info(f"Generated portfolio with {len(portfolio_data)} sites ({new_domains} new, {updated_domains} updated)")
    
    # Push changes to git
    push_to_git()
    
    logger.info("Portfolio generation completed")


def run_scheduled_task():
    """Run the task at the scheduled time."""
    thread = threading.Thread(target=run_portfolio_generation)
    thread.daemon = True
    thread.start()


def main():
    """Main entry point for the script."""
    # Ensure the output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Schedule the task to run daily at 16:00
    schedule.every().day.at("16:00").do(run_scheduled_task)
    
    # Also run it immediately when the script starts
    logger.info("Running initial portfolio generation")
    run_portfolio_generation()
    
    # Keep the script running to execute scheduled tasks
    logger.info("Waiting for scheduled tasks. Press Ctrl+C to exit.")
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        logger.info("Script stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()