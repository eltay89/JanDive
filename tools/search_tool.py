from tools.base_tool import BaseTool
try:
    from ddgs import DDGS
except ImportError:
    DDGS = None
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import re
import time
import random
import urllib.robotparser as robotparser

# Setup logger for this module
logger = logging.getLogger(__name__)

# User-agents list
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1'
]

class SearchTool(BaseTool):
    def __init__(self, config=None):
        super().__init__(config)
        self.name = "search_web"
        self.description = "Search the web for comprehensive information"
        # Load configuration parameters
        self.max_content_length = config.getint('search', 'max_content_length', fallback=2000) if config else 2000
        self.request_timeout = config.getint('search', 'request_timeout', fallback=5) if config else 5
        self.retry_attempts = config.getint('search', 'retry_attempts', fallback=2) if config else 2
        self.min_content_quality = config.getint('search', 'min_content_quality', fallback=100) if config else 100

    def _is_safe_url(self, url):
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            return False
        # Block private and reserved IP ranges
        if re.match(r"^(10\.|172\.(1[6-9]|2[0-9]|3[0-1])\.|192\.168\.|127\.|0\.|169\.254)", parsed.netloc):
            return False
        return True

    def _is_allowed_by_robots(self, url):
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = robotparser.RobotFileParser()
        rp.set_url(robots_url)
        try:
            rp.read()
            user_agent = random.choice(USER_AGENTS) # nosec B311
            logger.info(f"Checking robots.txt for {url} with user-agent {user_agent}")
            return rp.can_fetch(user_agent, url)
        except Exception as e:
            logger.warning(f"Could not fetch or parse robots.txt for {robots_url}: {e}. Assuming allowed.")
            return True

    

    def _is_boilerplate(self, text):
        """Check if content is likely boilerplate/navigation"""
        boilerplate_phrases = [
            'cookie policy', 'terms of service', 'privacy policy',
            'all rights reserved', 'sign up', 'log in', 'subscribe'
        ]
        text_lower = text.lower()
        return any(phrase in text_lower for phrase in boilerplate_phrases)

    def _fetch_full_content(self, url, max_chars=None, max_retries=None):
        # Use configured values if not explicitly provided
        max_chars = max_chars or self.max_content_length
        max_retries = max_retries or self.retry_attempts
        
        for attempt in range(max_retries):
            if not self._is_safe_url(url):
                logger.warning(f"Skipping unsafe URL: {url}")
                return "Skipped (unsafe URL)"
            if not self._is_allowed_by_robots(url):
                logger.warning(f"Skipping URL disallowed by robots.txt: {url}")
                return "Skipped (disallowed by robots.txt)"
            
            time.sleep(random.uniform(1, 3))  # Respectful delay # nosec B311
            headers = {'User-Agent': random.choice(USER_AGENTS)} # nosec B311
            
            try:
                logger.info(f"Fetching content from: {url}")
                r = requests.get(url, timeout=self.request_timeout, headers=headers)
                r.raise_for_status()
                
                # Try lxml first, fallback to html.parser
                try:
                    from lxml import etree
                    soup = BeautifulSoup(r.text, 'lxml')
                except ImportError:
                    soup = BeautifulSoup(r.text, 'html.parser')
                    logger.info("Using html.parser fallback (install lxml for better performance)")
                
                # Remove script, style, nav, footer elements
                for element in soup(['script', 'style', 'nav', 'footer', 'aside', 'header']):
                    element.decompose()
                
                # More robust content extraction
                content_selectors = [
                    'article', 'main', '.post-content', '.entry-content', 
                    '.td-post-content', '.single-post-content', '.article-body',
                    '[role="main"]', '#main', '#content'
                ]
                
                content_element = None
                for selector in content_selectors:
                    content_element = soup.select_one(selector)
                    if content_element:
                        break
                
                if not content_element:
                    content_element = soup.body

                # Get text and clean it
                if content_element:
                    content = content_element.get_text(separator=' ', strip=True)
                else:
                    content = ""
                
                # Clean up content
                content = re.sub(r'\s+', ' ', content).strip()
                
                # Quality check - skip if too short or too much boilerplate
                if len(content) < self.min_content_quality or self._is_boilerplate(content):
                    return None
                    
                return content[:max_chars] + ('...' if len(content) > max_chars else '')
            except requests.exceptions.Timeout:
                if attempt == max_retries - 1:
                    logger.warning(f"Timeout fetching {url} after {max_retries} attempts")
                    return None
                time.sleep(0.5 * (attempt + 1))  # Exponential backoff
            except requests.exceptions.RequestException as e:
                logger.warning(f"Failed to fetch {url}: {e}")
                return None

    def execute(self, query=None, max_results=5):
        if DDGS is None:
            return [{"error": "DDGS library not installed. Please run 'pip install duckduckgo_search'."}]
        if not query:
            return [{"error": "The 'query' parameter is required for a web search."}]
        
        try:
            logger.info(f"Executing search for: '{query}'")
            
            all_results = []
            
            with DDGS() as ddgs:
                search_results = list(ddgs.text(query, max_results=max_results))
                for res in search_results:
                    if res.get('href') and self._is_safe_url(res['href']):
                        content = self._fetch_full_content(res['href'])
                        all_results.append({
                            'title': res.get('title'),
                            'url': res.get('href'),
                            'snippet': res.get('body'),
                            'content': content if content else res.get('body') # Fallback to snippet
                        })
            
            # Deduplicate results by URL, prioritizing those with fetched content
            unique_results_map = {}
            for r in all_results:
                url = r.get('url')
                if url and (url not in unique_results_map or (r.get('content') and not unique_results_map[url].get('content'))):
                    unique_results_map[url] = r
            
            unique_results = list(unique_results_map.values())
            logger.info(f"Found {len(unique_results)} unique results after deduplication.")
            
            return unique_results[:max_results] if unique_results else [{"info": "No relevant web pages found."}]
        except Exception as e:
            logger.error(f"An unexpected error occurred in the search tool: {e}", exc_info=True)
            return [{"error": f"An unexpected search failure occurred: {str(e)}"}]
