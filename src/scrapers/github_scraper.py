#!/usr/bin/env python3
"""
GitHub scraper for AI Model Release Tracker.

This module handles monitoring GitHub repositories for commit activity,
releases, and README changes related to model releases.
"""

import logging
import time
import hashlib
import random
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests
from bs4 import BeautifulSoup

# Configure logging
logger = logging.getLogger(__name__)

class GitHubScraper:
    """Scraper for GitHub repositories."""
    
    def __init__(self, config: Dict):
        """
        Initialize the GitHub scraper.
        
        Args:
            config: Scraper configuration
        """
        self.config = config
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
        ]
        self.base_url = "https://github.com/"
        self.model_keywords = [
            "model",
            "release",
            "version",
            "launch",
            "introduce",
            "announce",
            "billion parameters",
            "language model",
            "llm",
            "gpt",
            "transformer"
        ]
        logger.info(f"GitHub scraper initialized")
    
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
    
    def scrape_repository(self, repo_name: str) -> Dict:
        """
        Scrape information from a GitHub repository.
        
        Args:
            repo_name: Repository name in format "owner/repo"
            
        Returns:
            Dictionary with repository data
        """
        url = f"{self.base_url}{repo_name}"
        logger.info(f"Scraping repository: {repo_name} from {url}")
        
        html = self._fetch_page(url)
        if not html:
            return {}
        
        try:
            repo_data = {
                'name': repo_name,
                'url': url,
                'source_type': 'github',
                'source_name': f"GitHub - {repo_name}",
                'extracted_at': datetime.now().isoformat(),
                'readme': {},
                'releases': [],
                'recent_commits': []
            }
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract repository details
            description_elem = soup.select_one(".f4.my-3")
            repo_data['description'] = description_elem.get_text().strip() if description_elem else ""
            
            # Get README content
            readme_elem = soup.select_one("#readme")
            if readme_elem:
                readme_content = readme_elem.select_one(".markdown-body")
                readme_text = readme_content.get_text() if readme_content else ""
                
                # Generate content hash
                readme_hash = hashlib.md5(readme_text.encode()).hexdigest()
                
                repo_data['readme'] = {
                    'content': readme_text,
                    'hash': readme_hash
                }
            
            # Check for recent activity
            self._scrape_recent_commits(repo_name, repo_data)
            self._scrape_releases(repo_name, repo_data)
            
            return repo_data
            
        except Exception as e:
            logger.error(f"Error parsing repository for {repo_name}: {str(e)}")
            return {}
    
    def _scrape_recent_commits(self, repo_name: str, repo_data: Dict) -> None:
        """
        Scrape recent commits from a repository.
        
        Args:
            repo_name: Repository name in format "owner/repo"
            repo_data: Dictionary to update with commit data
        """
        commits_url = f"{self.base_url}{repo_name}/commits"
        html = self._fetch_page(commits_url)
        if not html:
            return
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            commit_items = soup.select(".js-commits-list-item")
            
            recent_commits = []
            for item in commit_items[:10]:  # Get latest 10 commits
                title_elem = item.select_one(".js-navigation-open")
                if not title_elem:
                    continue
                    
                commit_title = title_elem.get_text().strip()
                commit_url = title_elem.get('href')
                if commit_url and not commit_url.startswith(('http://', 'https://')):
                    commit_url = f"https://github.com{commit_url}"
                
                date_elem = item.select_one("relative-time")
                commit_date = date_elem.get('datetime') if date_elem else None
                
                author_elem = item.select_one(".commit-author")
                author = author_elem.get_text().strip() if author_elem else "Unknown"
                
                # Check if commit might be related to model release
                is_model_related = any(keyword.lower() in commit_title.lower() for keyword in self.model_keywords)
                
                commit_data = {
                    'title': commit_title,
                    'url': commit_url,
                    'date': commit_date,
                    'author': author,
                    'is_model_related': is_model_related
                }
                
                recent_commits.append(commit_data)
            
            repo_data['recent_commits'] = recent_commits
            logger.info(f"Scraped {len(recent_commits)} recent commits for {repo_name}")
            
        except Exception as e:
            logger.error(f"Error scraping commits for {repo_name}: {str(e)}")
    
    def _scrape_releases(self, repo_name: str, repo_data: Dict) -> None:
        """
        Scrape releases from a repository.
        
        Args:
            repo_name: Repository name in format "owner/repo"
            repo_data: Dictionary to update with release data
        """
        releases_url = f"{self.base_url}{repo_name}/releases"
        html = self._fetch_page(releases_url)
        if not html:
            return
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            release_items = soup.select(".release")
            
            releases = []
            for item in release_items[:5]:  # Get latest 5 releases
                title_elem = item.select_one(".release-title")
                if not title_elem:
                    continue
                    
                title = title_elem.get_text().strip()
                
                # Get release URL
                link_elem = title_elem.select_one("a")
                link = link_elem.get('href') if link_elem else None
                if link and not link.startswith(('http://', 'https://')):
                    link = f"https://github.com{link}"
                
                # Get release date
                date_elem = item.select_one("relative-time")
                release_date = date_elem.get('datetime') if date_elem else None
                
                # Get release description
                desc_elem = item.select_one(".markdown-body")
                description = desc_elem.get_text().strip() if desc_elem else ""
                
                # Check if release might be related to a model
                is_model_release = any(keyword.lower() in (title.lower() + " " + description.lower()) 
                                      for keyword in self.model_keywords)
                
                release_data = {
                    'title': title,
                    'url': link,
                    'date': release_date,
                    'description': description,
                    'is_model_release': is_model_release,
                    'content_hash': hashlib.md5(f"{title}:{description}".encode()).hexdigest()
                }
                
                releases.append(release_data)
            
            repo_data['releases'] = releases
            logger.info(f"Scraped {len(releases)} recent releases for {repo_name}")
            
        except Exception as e:
            logger.error(f"Error scraping releases for {repo_name}: {str(e)}")
    
    def scrape(self) -> List[Dict]:
        """
        Perform complete scrape of GitHub repositories based on configuration.
        
        Returns:
            List of repository data dictionaries
        """
        results = []
        
        repos = self.config.get("repos", [])
        for repo in repos:
            repo_data = self.scrape_repository(repo)
            if repo_data:
                results.append(repo_data)
                
                # Extract model releases
                model_releases = self._extract_model_releases(repo_data)
                if model_releases:
                    for release in model_releases:
                        results.append(release)
                
            # Be nice to GitHub
            time.sleep(2)
        
        logger.info(f"Scraped {len(results)} repositories from GitHub")
        return results
    
    def _extract_model_releases(self, repo_data: Dict) -> List[Dict]:
        """
        Extract model release information from repository data.
        
        Args:
            repo_data: Repository data dictionary
            
        Returns:
            List of model release dictionaries
        """
        model_releases = []
        
        # Check releases
        for release in repo_data.get('releases', []):
            if release.get('is_model_release', False):
                model_release = {
                    'title': release['title'],
                    'description': release['description'],
                    'url': release['url'],
                    'date': release['date'],
                    'source_type': 'github_release',
                    'source_name': f"GitHub Release - {repo_data['name']}",
                    'content_hash': release['content_hash'],
                    'extracted_at': datetime.now().isoformat(),
                    'is_model_release': True
                }
                
                # Try to extract model size from title or description
                model_size = None
                size_patterns = [
                    r'(\d+[,\.\s]?\d*)\s*[bB]',  # Match patterns like "7B", "13B", "70.3B"
                    r'(\d+[,\.\s]?\d*)\s*billion',  # Match patterns like "7 billion"
                    r'(\d+[,\.\s]?\d*)\s*parameters'  # Match patterns like "7 billion parameters"
                ]
                
                combined_text = f"{release['title']} {release['description']}".lower()
                for pattern in size_patterns:
                    match = re.search(pattern, combined_text)
                    if match:
                        model_size = match.group(1).replace(',', '').replace(' ', '')
                        break
                        
                if model_size:
                    model_release['model_size'] = model_size
                
                model_releases.append(model_release)
        
        # Check model-related commits (only if no releases were found)
        if not model_releases:
            for commit in repo_data.get('recent_commits', []):
                if commit.get('is_model_related', False):
                    model_release = {
                        'title': commit['title'],
                        'url': commit['url'],
                        'date': commit['date'],
                        'author': commit['author'],
                        'source_type': 'github_commit',
                        'source_name': f"GitHub Commit - {repo_data['name']}",
                        'content_hash': hashlib.md5(commit['title'].encode()).hexdigest(),
                        'extracted_at': datetime.now().isoformat(),
                        'is_model_release': True
                    }
                    model_releases.append(model_release)
        
        return model_releases


# Example usage
if __name__ == "__main__":
    # Configure logging for standalone execution
    logging.basicConfig(level=logging.INFO)
    
    # Test configuration
    test_config = {
        "repos": ["openai/openai-python", "deepseek-ai/deepseek-coder", "meta-llama/llama"]
    }
    
    scraper = GitHubScraper(test_config)
    results = scraper.scrape()
    
    print(f"Scraped {len(results)} repositories")
    
    model_releases_found = 0
    for repo in results:
        # Print repository name
        print(f"Repository: {repo.get('name', 'Unknown')}")
        
        # Check for releases
        releases = repo.get('releases', [])
        model_releases = [r for r in releases if r.get('is_model_release', False)]
        if model_releases:
            print(f"Found {len(model_releases)} potential model releases:")
            for release in model_releases:
                print(f"  - {release['title']}")
                model_releases_found += 1
        
        # Check for model-related commits
        commits = repo.get('recent_commits', [])
        model_commits = [c for c in commits if c.get('is_model_related', False)]
        if model_commits:
            print(f"Found {len(model_commits)} potential model-related commits:")
            for commit in model_commits:
                print(f"  - {commit['title']}")
        
        print("-" * 50)
    
    print(f"Total potential model releases found: {model_releases_found}")