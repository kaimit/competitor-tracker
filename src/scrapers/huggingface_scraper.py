#!/usr/bin/env python3
"""
HuggingFace scraper for AI Model Release Tracker.

This module handles monitoring HuggingFace repositories and model releases
for major AI companies.
"""

import logging
import time
import hashlib
import random
import re
from datetime import datetime
from typing import Dict, List, Optional
import requests
from bs4 import BeautifulSoup

# Configure logging
logger = logging.getLogger(__name__)

class HuggingFaceScraper:
    """Scraper for HuggingFace model repositories."""
    
    def __init__(self, config: Dict):
        """
        Initialize the HuggingFace scraper.
        
        Args:
            config: Scraper configuration
        """
        self.config = config
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
        ]
        self.base_url = "https://huggingface.co/"
        self.model_keywords = self.config.get("model_keywords", ["language model", "billion parameters"])
        logger.info(f"HuggingFace scraper initialized")
    
    def _get_headers(self) -> Dict:
        """Generate request headers with rotating user agent."""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    def _fetch_page(self, url: str) -> Optional[str]:
        """
        Fetch HTML content from a URL.
        
        Args:
            url: The URL to fetch
            
        Returns:
            HTML content as string, or None if fetch failed
        """
        try:
            logger.info(f"Fetching {url}")
            response = requests.get(url, headers=self._get_headers(), timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            return None
    
    def scrape_organization(self, org_name: str) -> List[Dict]:
        """
        Scrape models for a specific organization on HuggingFace.
        
        Args:
            org_name: The organization name to scrape
            
        Returns:
            List of model data dictionaries
        """
        url = f"{self.base_url}{org_name}"
        logger.info(f"Scraping organization: {org_name} from {url}")
        
        html = self._fetch_page(url)
        if not html:
            return []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            model_cards = soup.select(".model-card")
            
            logger.info(f"Found {len(model_cards)} model cards for {org_name}")
            
            results = []
            for card in model_cards:
                model_data = self._extract_model_data(card, org_name)
                if model_data:
                    results.append(model_data)
            
            return results
            
        except Exception as e:
            logger.error(f"Error parsing organization page for {org_name}: {str(e)}")
            return []
    
    def scrape_trending_models(self, url: str) -> List[Dict]:
        """
        Scrape trending or recently updated models from HuggingFace.
        
        Args:
            url: The URL to scrape (trending or recently modified)
            
        Returns:
            List of model data dictionaries
        """
        logger.info(f"Scraping trending/updated models from {url}")
        
        html = self._fetch_page(url)
        if not html:
            return []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            model_cards = soup.select(".model-card")
            
            logger.info(f"Found {len(model_cards)} model cards")
            
            results = []
            for card in model_cards:
                model_data = self._extract_model_data(card)
                if model_data:
                    results.append(model_data)
            
            return results
            
        except Exception as e:
            logger.error(f"Error parsing trending models: {str(e)}")
            return []
    
    def _extract_model_data(self, card_elem, org_name: str = None) -> Optional[Dict]:
        """
        Extract model data from a model card element.
        
        Args:
            card_elem: BeautifulSoup element for the model card
            org_name: Optional organization name
            
        Returns:
            Dictionary of model data or None if extraction failed
        """
        try:
            # Extract model name and link
            title_elem = card_elem.select_one(".model-name")
            if not title_elem:
                return None
                
            model_name = title_elem.get_text().strip()
            
            # Extract model link
            link_elem = card_elem.select_one("a")
            link = link_elem.get('href') if link_elem else None
            
            if link and not link.startswith(('http://', 'https://')):
                link = f"{self.base_url.rstrip('/')}{link}"
            
            # Extract model author/organization
            author_elem = card_elem.select_one(".author")
            author = author_elem.get_text().strip() if author_elem else (org_name or "Unknown")
            
            # Extract description (if available)
            desc_elem = card_elem.select_one(".description")
            description = desc_elem.get_text().strip() if desc_elem else ""
            
            # Extract tags
            tags = []
            tag_elems = card_elem.select(".tag")
            for tag_elem in tag_elems:
                tags.append(tag_elem.get_text().strip())
            
            # Extract downloads count (if available)
            downloads_elem = card_elem.select_one(".downloads")
            downloads = downloads_elem.get_text().strip() if downloads_elem else "Unknown"
            
            # Extract last updated date (if available)
            updated_elem = card_elem.select_one(".metadata .date")
            updated = updated_elem.get_text().strip() if updated_elem else None
            
            # Generate a unique identifier for this model
            content_hash = hashlib.md5(f"{model_name}:{link}".encode()).hexdigest()
            
            # Check if the model description or name contains relevant keywords
            is_model_release = False
            combined_text = f"{model_name} {description} {' '.join(tags)}".lower()
            
            for keyword in self.model_keywords:
                if keyword.lower() in combined_text:
                    is_model_release = True
                    break
            
            # Try to extract model size from name or description
            model_size = None
            size_patterns = [
                r'(\d+[,\.\s]?\d*)\s*[bB]',  # Match patterns like "7B", "13B", "70.3B"
                r'(\d+[,\.\s]?\d*)\s*billion',  # Match patterns like "7 billion"
                r'(\d+[,\.\s]?\d*)\s*parameters'  # Match patterns like "7 billion parameters"
            ]
            
            for pattern in size_patterns:
                match = re.search(pattern, combined_text)
                if match:
                    model_size = match.group(1).replace(',', '').replace(' ', '')
                    break
                    
            return {
                'model_name': model_name,
                'url': link,
                'author': author,
                'description': description,
                'tags': tags,
                'downloads': downloads,
                'updated': updated,
                'model_size': model_size,
                'is_model_release': is_model_release,
                'source_type': 'huggingface',
                'source_name': f"HuggingFace - {author}",
                'content_hash': content_hash,
                'extracted_at': datetime.now().isoformat()
            }
                
        except Exception as e:
            logger.error(f"Error extracting model data: {str(e)}")
            return None
    
    def scrape_model_details(self, model_url: str) -> Dict:
        """
        Scrape detailed information from a specific model page.
        
        Args:
            model_url: URL of the model detail page
            
        Returns:
            Dictionary with model details or empty dict if scraping failed
        """
        logger.info(f"Scraping model details from {model_url}")
        
        html = self._fetch_page(model_url)
        if not html:
            return {}
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract README content
            readme = soup.select_one(".markdown-body")
            readme_text = readme.get_text() if readme else ""
            
            # Extract model metadata
            metadata = {}
            metadata_table = soup.select_one(".metadata-table")
            if metadata_table:
                rows = metadata_table.select("tr")
                for row in rows:
                    cols = row.select("td")
                    if len(cols) >= 2:
                        key = cols[0].get_text().strip()
                        value = cols[1].get_text().strip()
                        metadata[key] = value
            
            # Check for files section
            files_section = soup.select_one(".files-section")
            has_model_files = bool(files_section)
            
            return {
                'readme': readme_text,
                'metadata': metadata,
                'has_model_files': has_model_files
            }
                
        except Exception as e:
            logger.error(f"Error scraping model details for {model_url}: {str(e)}")
            return {}
    
    def scrape(self) -> List[Dict]:
        """
        Perform complete scrape of HuggingFace based on configuration.
        
        Returns:
            List of model information dictionaries
        """
        results = []
        
        # Scrape organizations
        if "orgs" in self.config:
            for org in self.config.get("orgs", []):
                org_results = self.scrape_organization(org)
                results.extend(org_results)
                # Be nice to the server
                time.sleep(2)
        
        # Scrape global trending/updated models
        if self.config.get("global_monitoring", {}).get("enabled", False):
            for url in self.config.get("global_monitoring", {}).get("urls", []):
                global_results = self.scrape_trending_models(url)
                results.extend(global_results)
                # Be nice to the server
                time.sleep(2)
        
        logger.info(f"Scraped {len(results)} total models from HuggingFace")
        return results


# Example usage
if __name__ == "__main__":
    # Configure logging for standalone execution
    logging.basicConfig(level=logging.INFO)
    
    # Test configuration
    test_config = {
        "orgs": ["meta-llama", "deepseek-ai"],
        "model_keywords": [
            "new release",
            "introducing",
            "announcing",
            "version",
            "billion parameters",
            "language model",
            "multimodal"
        ],
        "global_monitoring": {
            "enabled": True,
            "urls": ["https://huggingface.co/models?sort=trending"]
        }
    }
    
    scraper = HuggingFaceScraper(test_config)
    results = scraper.scrape()
    
    print(f"Found {len(results)} models")
    for model in results[:5]:  # Just print first 5 for testing
        print(f"Model: {model['model_name']}")
        print(f"Author: {model['author']}")
        print(f"URL: {model['url']}")
        print(f"Is model release: {model['is_model_release']}")
        if model['model_size']:
            print(f"Model size: {model['model_size']}")
        print("-" * 50)