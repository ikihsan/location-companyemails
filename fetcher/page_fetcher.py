"""
Page fetcher module.
Handles HTTP requests with retries, rate limiting, and user-agent rotation.
"""

import time
import random
import asyncio
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
from dataclasses import dataclass

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

try:
    from fake_useragent import UserAgent
    FAKE_UA_AVAILABLE = True
except ImportError:
    FAKE_UA_AVAILABLE = False

from config import get_config, Config
from models import CrawlResult
from utils import get_logger


# Default user agents if fake_useragent not available
DEFAULT_USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]


class UserAgentRotator:
    """Rotates user agents to avoid detection."""
    
    def __init__(self):
        self._ua = None
        if FAKE_UA_AVAILABLE:
            try:
                self._ua = UserAgent()
            except Exception:
                pass
    
    def get_random(self) -> str:
        """Get a random user agent string."""
        if self._ua:
            try:
                return self._ua.random
            except Exception:
                pass
        return random.choice(DEFAULT_USER_AGENTS)
    
    def get_chrome(self) -> str:
        """Get a Chrome user agent."""
        if self._ua:
            try:
                return self._ua.chrome
            except Exception:
                pass
        return DEFAULT_USER_AGENTS[0]


class RobotsChecker:
    """Checks robots.txt compliance."""
    
    # Domains to skip robots.txt check (job portals and search engines - we use rate limiting instead)
    SKIP_ROBOTS_DOMAINS = [
        # Search engines
        'google.com', 'bing.com', 'duckduckgo.com', 'yahoo.com',
        'brave.com', 'ecosia.org', 'startpage.com', 'mojeek.com',
        # Job portals - India
        'indeed.co.in', 'naukri.com', 'shine.com', 'timesjobs.com',
        'freshersworld.com', 'monster.co.in', 'instahyre.com',
        # Job portals - Global  
        'indeed.com', 'glassdoor.com', 'linkedin.com', 'monster.com',
        'simplyhired.com', 'ziprecruiter.com', 'careerbuilder.com',
        # Startup directories
        'ycombinator.com', 'wellfound.com', 'angellist.com', 'f6s.com',
    ]
    
    def __init__(self, respect_robots: bool = True):
        self.respect_robots = respect_robots
        self._cache: Dict[str, RobotFileParser] = {}
        self._user_agent = 'Mozilla/5.0 (compatible; Googlebot/2.1)'
    
    def can_fetch(self, url: str) -> bool:
        """Check if URL can be fetched according to robots.txt."""
        if not self.respect_robots:
            return True
        
        # Skip robots.txt for certain domains (we'll be respectful with rate limiting instead)
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if any(skip_domain in domain for skip_domain in self.SKIP_ROBOTS_DOMAINS):
            return True
        
        try:
            parsed = urlparse(url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            
            if base_url not in self._cache:
                rp = RobotFileParser()
                robots_url = f"{base_url}/robots.txt"
                rp.set_url(robots_url)
                try:
                    rp.read()
                except Exception:
                    # If robots.txt not found, assume allowed
                    return True
                self._cache[base_url] = rp
            
            return self._cache[base_url].can_fetch(self._user_agent, url)
        except Exception:
            return True


class RateLimiter:
    """Rate limiter with configurable delays."""
    
    def __init__(
        self,
        min_delay: float = 1.0,
        max_delay: float = 3.0,
        requests_per_minute: int = 30,
    ):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.requests_per_minute = requests_per_minute
        self._last_request_time: Dict[str, float] = {}
        self._request_count = 0
        self._minute_start = time.time()
    
    def wait(self, domain: Optional[str] = None):
        """Wait appropriate time before next request."""
        # Check per-minute limit
        current_time = time.time()
        if current_time - self._minute_start >= 60:
            self._request_count = 0
            self._minute_start = current_time
        
        if self._request_count >= self.requests_per_minute:
            wait_time = 60 - (current_time - self._minute_start)
            if wait_time > 0:
                time.sleep(wait_time)
            self._request_count = 0
            self._minute_start = time.time()
        
        # Random delay
        delay = random.uniform(self.min_delay, self.max_delay)
        
        # Per-domain delay
        if domain and domain in self._last_request_time:
            elapsed = time.time() - self._last_request_time[domain]
            if elapsed < delay:
                time.sleep(delay - elapsed)
        
        self._last_request_time[domain or 'default'] = time.time()
        self._request_count += 1


class PageFetcher:
    """Fetches web pages with retry logic and rate limiting."""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self.logger = get_logger()
        
        self.ua_rotator = UserAgentRotator()
        self.robots_checker = RobotsChecker(self.config.scraping.respect_robots_txt)
        self.rate_limiter = RateLimiter(
            min_delay=self.config.rate_limit.min_delay_seconds,
            max_delay=self.config.rate_limit.max_delay_seconds,
            requests_per_minute=self.config.rate_limit.max_requests_per_minute,
        )
        
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry logic."""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=self.config.scraping.max_retries,
            backoff_factor=self.config.scraping.retry_backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set proxies if configured
        proxies = self.config.proxy.get_proxies()
        if proxies:
            session.proxies.update(proxies)
        
        return session
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with rotated user agent."""
        return {
            'User-Agent': self.ua_rotator.get_random(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    def fetch(self, url: str, timeout: int = 30) -> CrawlResult:
        """Fetch a single URL."""
        start_time = time.time()
        
        # Check robots.txt
        if not self.robots_checker.can_fetch(url):
            self.logger.debug(f"Blocked by robots.txt: {url}")
            return CrawlResult(
                url=url,
                status_code=403,
                content_type='',
                error='Blocked by robots.txt',
            )
        
        # Rate limiting
        domain = urlparse(url).netloc
        self.rate_limiter.wait(domain)
        
        try:
            response = self.session.get(
                url,
                headers=self._get_headers(),
                timeout=timeout,
                allow_redirects=True,
            )
            
            elapsed = (time.time() - start_time) * 1000
            content_type = response.headers.get('Content-Type', '')
            
            # Only get text for HTML content
            html_content = None
            if 'text/html' in content_type or 'application/xhtml' in content_type:
                html_content = response.text
            
            self.logger.debug(f"Fetched {url} - {response.status_code} ({elapsed:.0f}ms)")
            
            return CrawlResult(
                url=url,
                status_code=response.status_code,
                content_type=content_type,
                html_content=html_content,
                crawl_time_ms=elapsed,
            )
            
        except requests.exceptions.Timeout:
            self.logger.warning(f"Timeout fetching {url}")
            return CrawlResult(
                url=url,
                status_code=408,
                content_type='',
                error='Timeout',
                crawl_time_ms=(time.time() - start_time) * 1000,
            )
            
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Error fetching {url}: {e}")
            return CrawlResult(
                url=url,
                status_code=0,
                content_type='',
                error=str(e),
                crawl_time_ms=(time.time() - start_time) * 1000,
            )
    
    def fetch_multiple(self, urls: List[str], timeout: int = 30) -> List[CrawlResult]:
        """Fetch multiple URLs sequentially."""
        results = []
        for url in urls:
            results.append(self.fetch(url, timeout))
        return results
    
    def close(self):
        """Close the session."""
        self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
