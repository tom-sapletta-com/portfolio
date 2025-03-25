import os
import re
import json
import logging
import numpy as np
import spacy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import Dict, List, Optional
from AdvancedContentAnalyzer import AdvancedContentAnalyzer

# Ensure the necessary models are downloaded
# python -m spacy download en_core_web_md

class AdvancedContentAnalyzer:
    def __init__(self,
                 tech_patterns_file='tech_patterns.json',
                 themes_file='common_themes.json',
                 spacy_model='en_core_web_md'):
        """
        Advanced content analyzer using NLP techniques.

        Args:
            tech_patterns_file (str): Path to technology patterns JSON
            themes_file (str): Path to themes JSON
            spacy_model (str): SpaCy language model to use
        """
        # Load SpaCy model
        try:
            self.nlp = spacy.load(spacy_model)
        except OSError:
            logging.warning(f"SpaCy model {spacy_model} not found. Using default.")
            self.nlp = spacy.load('en_core_web_sm')

        # Load technology and theme patterns
        self.tech_patterns = self._load_json(tech_patterns_file)
        self.themes = self._load_json(themes_file)

        # Predefined theme embeddings
        self.theme_embeddings = self._create_theme_embeddings()

    def _load_json(self, filename: str) -> Dict:
        """
        Load JSON file safely.

        Args:
            filename (str): Path to JSON file

        Returns:
            Dict: Loaded JSON data or empty dict
        """
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.error(f"Error loading {filename}: {e}")
            return {}

    def _create_theme_embeddings(self) -> Dict[str, np.ndarray]:
        """
        Create embeddings for predefined themes.

        Returns:
            Dict of theme names to their embeddings
        """
        theme_embeddings = {}
        for theme, keywords in self.themes.items():
            # Combine theme keywords into a single text
            theme_text = ' '.join(keywords)
            theme_embeddings[theme] = self.nlp(theme_text).vector
        return theme_embeddings

    def extract_keywords(self, text: str, top_k: int = 10) -> List[str]:
        """
        Extract top keywords using TF-IDF and Named Entity Recognition.

        Args:
            text (str): Input text
            top_k (int): Number of top keywords to return

        Returns:
            List of top keywords
        """
        # Preprocess text
        text = re.sub(r'\s+', ' ', text).lower().strip()

        # SpaCy named entity extraction
        doc = self.nlp(text)

        # Extract named entities
        entities = [ent.text.lower() for ent in doc.ents
                    if ent.label_ in ['ORG', 'PRODUCT', 'GPE', 'PERSON']]

        # TF-IDF for additional keywords
        try:
            vectorizer = TfidfVectorizer(
                max_features=100,
                stop_words='english',
                ngram_range=(1, 2)
            )

            # Combine text processing
            tfidf_matrix = vectorizer.fit_transform([text])
            feature_names = vectorizer.get_feature_names_out()

            # Combine TF-IDF keywords with named entities
            tfidf_scores = tfidf_matrix.toarray()[0]
            keyword_scores = list(zip(feature_names, tfidf_scores))

            # Sort and filter keywords
            sorted_keywords = sorted(keyword_scores, key=lambda x: x[1], reverse=True)

            # Combine and deduplicate keywords
            keywords = []
            seen = set()
            for word, score in sorted_keywords + [(e, 1.0) for e in entities]:
                if word not in seen and score > 0:
                    keywords.append(word)
                    seen.add(word)
                    if len(keywords) == top_k:
                        break

            return keywords

        except Exception as e:
            logging.error(f"Keyword extraction error: {e}")
            return entities[:top_k]

    def detect_theme(self, text: str) -> str:
        """
        Detect website theme using semantic similarity.

        Args:
            text (str): Input text

        Returns:
            str: Detected theme
        """
        # Preprocess text
        text = re.sub(r'\s+', ' ', text).lower().strip()

        try:
            # Create text embedding
            text_embedding = self.nlp(text).vector

            # Compute cosine similarities with theme embeddings
            theme_similarities = {}
            for theme, theme_embedding in self.theme_embeddings.items():
                similarity = cosine_similarity(
                    text_embedding.reshape(1, -1),
                    theme_embedding.reshape(1, -1)
                )[0][0]
                theme_similarities[theme] = similarity

            # Return theme with highest similarity
            if theme_similarities:
                return max(theme_similarities, key=theme_similarities.get)
        except Exception as e:
            logging.error(f"Theme detection error: {e}")

        return "General"

    def detect_technologies(self, html_content: str) -> List[str]:
        """
        Detect technologies used in the website.

        Args:
            html_content (str): Website HTML content

        Returns:
            List of detected technologies
        """
        html_str = html_content.lower()
        detected_techs = []

        for tech, patterns in self.tech_patterns.items():
            for pattern in patterns:
                if pattern.lower() in html_str:
                    detected_techs.append(tech)
                    break

        return list(set(detected_techs))


def analyze_content(html_content: Optional[str]) -> Dict[str, List[str]]:
    """
    Analyze website content using advanced NLP techniques.

    Args:
        html_content (str): HTML content of the website

    Returns:
        Dict containing theme, keywords, and technologies
    """
    # Default return if no content
    if not html_content:
        return {
            "theme": "Unknown",
            "keywords": [],
            "technologies": []
        }

    try:
        # Extract text from HTML
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        text_content = soup.get_text(separator=' ', strip=True)

        # Initialize analyzer
        analyzer = AdvancedContentAnalyzer()

        # Analyze content
        theme = analyzer.detect_theme(text_content)
        keywords = analyzer.extract_keywords(text_content)
        technologies = analyzer.detect_technologies(html_content)

        return {
            "theme": theme,
            "keywords": keywords,
            "technologies": technologies
        }

    except Exception as e:
        logging.error(f"Comprehensive content analysis error: {e}")
        return {
            "theme": "Unknown",
            "keywords": [],
            "technologies": []
        }