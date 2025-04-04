#!/usr/bin/env python3
"""
Website scraper for AI Model Release Tracker.

This module handles scraping company blogs and news websites
to extract information about potential model releases.
"""

import logging
import time
from datetime import datetime
from typing import Dict, List, Optional
import hashlib
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Configure logging
logger = logging.getLogger(__name__)

class WebsiteScraper:
    """Scraper for company blogs and websites."""
    
    def __init__(self, config: Dict):
        """
        Initialize the website scraper.
        
        Args:
            config: Scraper configuration
        """
        self.config = config
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
        ]
        logger.info(f"Website scraper initialized for {self.config.get('name', 'unnamed site')}")
    
    def _get_headers(self) -> Dict:
        """Generate request headers with rotating user agent."""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    def fetch_page(self, url: str) -> Optional[str]:
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
    
    def parse_page(self, html: str, selector: str) -> List[Dict]:
        """
        Parse HTML content to extract article elements.
        
        Args:
            html: HTML content to parse
            selector: CSS selector for article elements
            
        Returns:
            List of extracted article data
        """
        if not html:
            return []
            
        try:
            soup = BeautifulSoup(html, 'html.parser')
            articles = soup.select(selector)
            
            logger.info(f"Found {len(articles)} articles with selector '{selector}'")
            
            results = []
            for article in articles:
                article_data = self._extract_article_data(article)
                if article_data:
                    results.append(article_data)
                    
            return results
            
        except Exception as e:
            logger.error(f"Error parsing HTML: {str(e)}")
            return []
    
    def _extract_article_data(self, element) -> Optional[Dict]:
        """
        Extract structured data from a article element.
        
        Args:
            element: BeautifulSoup element representing an article
            
        Returns:
            Dictionary with article data, or None if extraction failed
        """
        try:
            # Extract title
            title_elem = element.select_one('h2, h3, .title, .headline')
            if not title_elem:
                return None
                
            title = title_elem.get_text().strip()
            
            # Extract link
            link_elem = element.select_one('a')
            link = link_elem.get('href') if link_elem else None
            
            # Make sure link is absolute
            if link and not link.startswith(('http://', 'https://')):
                base_url = self.config.get('url', '')
                link = urljoin(base_url, link)
            
            # Extract date (if available)
            date_elem = element.select_one('.date, .time, time')
            date_str = date_elem.get_text().strip() if date_elem else None
            # Note: Date parsing would need more sophisticated handling in a real implementation
            
            # Extract description
            desc_elem = element.select_one('p, .description, .summary')
            description = desc_elem.get_text().strip() if desc_elem else ""
            
            # Generate a unique identifier for this article
            content_hash = hashlib.md5(f"{title}:{link}".encode()).hexdigest()
            
            return {
                'title': title,
                'url': link,
                'description': description,
                'date': date_str,
                'source_type': 'website',
                'source_name': self.config.get('name', 'Unknown'),
                'source_url': self.config.get('url', ''),
                'content_hash': content_hash,
                'raw_html': str(element),
                'extracted_at': datetime.now().isoformat()
            }
                
        except Exception as e:
            logger.error(f"Error extracting article data: {str(e)}")
            return None
    
    def scrape(self) -> List[Dict]:
        """
        Perform complete scrape of the configured website.
        
        Returns:
            List of extracted articles
        """
        url = self.config.get('url')
        selector = self.config.get('selector')
        
        if not url or not selector:
            logger.error("Missing required configuration (url or selector)")
            return []
        
        html = self.fetch_page(url)
        if not html:
            return []
            
        articles = self.parse_page(html, selector)
        logger.info(f"Scraped {len(articles)} articles from {url}")
        
        return articles


# Example usage
if __name__ == "__main__":
    # Configure logging for standalone execution
    logging.basicConfig(level=logging.INFO)
    
    # Test configuration
    test_config = {
        'name': 'OpenAI Blog',
        'url': 'https://openai.com/blog',
        'selector': '.post-card'
    }
    
    scraper = WebsiteScraper(test_config)
    results = scraper.scrape()
    
    print(f"Found {len(results)} articles")
    for article in results:
        print(f"Title: {article['title']}")
        print(f"URL: {article['url']}")
        print(f"Description: {article['description'][:100]}...")
        print("-" * 50)