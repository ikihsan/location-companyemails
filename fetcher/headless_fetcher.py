"""
Headless browser fetcher using Playwright.
For JavaScript-heavy sites that require browser rendering.
"""

import asyncio
from typing import Optional, List
from urllib.parse import urlparse

from config import get_config, Config
from models import CrawlResult
from utils import get_logger

# Playwright is optional
try:
    from playwright.async_api import async_playwright, Browser, Page
    from playwright.async_api import TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class HeadlessFetcher:
    """Fetches pages using headless browser for JS-heavy sites."""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self.logger = get_logger()
        self._browser: Optional['Browser'] = None
        self._playwright = None
        
        if not PLAYWRIGHT_AVAILABLE:
            self.logger.warning("Playwright not available. Install with: pip install playwright && playwright install")
    
    async def _ensure_browser(self):
        """Ensure browser is started."""
        if self._browser is None and PLAYWRIGHT_AVAILABLE:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.config.browser.use_headless,
            )
    
    async def fetch_async(self, url: str, wait_for_selector: Optional[str] = None) -> CrawlResult:
        """Fetch a URL using headless browser."""
        if not PLAYWRIGHT_AVAILABLE:
            return CrawlResult(
                url=url,
                status_code=0,
                content_type='',
                error='Playwright not available',
            )
        
        await self._ensure_browser()
        
        page: Optional['Page'] = None
        try:
            page = await self._browser.new_page()
            
            # Set user agent
            await page.set_extra_http_headers({
                'Accept-Language': 'en-US,en;q=0.9',
            })
            
            response = await page.goto(
                url,
                timeout=self.config.browser.timeout,
                wait_until='networkidle',
            )
            
            if wait_for_selector:
                try:
                    await page.wait_for_selector(wait_for_selector, timeout=10000)
                except PlaywrightTimeout:
                    self.logger.debug(f"Selector {wait_for_selector} not found on {url}")
            
            # Wait a bit for dynamic content
            await asyncio.sleep(1)
            
            html_content = await page.content()
            status_code = response.status if response else 200
            
            return CrawlResult(
                url=url,
                status_code=status_code,
                content_type='text/html',
                html_content=html_content,
            )
            
        except PlaywrightTimeout:
            self.logger.warning(f"Timeout loading {url}")
            return CrawlResult(
                url=url,
                status_code=408,
                content_type='',
                error='Timeout',
            )
        except Exception as e:
            self.logger.warning(f"Error loading {url}: {e}")
            return CrawlResult(
                url=url,
                status_code=0,
                content_type='',
                error=str(e),
            )
        finally:
            if page:
                await page.close()
    
    def fetch(self, url: str, wait_for_selector: Optional[str] = None) -> CrawlResult:
        """Synchronous wrapper for fetch_async."""
        return asyncio.get_event_loop().run_until_complete(
            self.fetch_async(url, wait_for_selector)
        )
    
    async def close_async(self):
        """Close browser and playwright."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
    
    def close(self):
        """Synchronous close."""
        if self._browser or self._playwright:
            asyncio.get_event_loop().run_until_complete(self.close_async())
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class HybridFetcher:
    """Fetcher that uses regular requests by default, falls back to headless for JS sites."""
    
    # Domains known to require JavaScript
    JS_HEAVY_DOMAINS = [
        'linkedin.com',
        'wellfound.com',
        'angel.co',
        'glassdoor.com',
        'indeed.com',
    ]
    
    def __init__(self, config: Optional[Config] = None, use_headless: bool = False):
        self.config = config or get_config()
        self.use_headless = use_headless
        
        from .page_fetcher import PageFetcher
        self.regular_fetcher = PageFetcher(config)
        self.headless_fetcher: Optional[HeadlessFetcher] = None
        
        if use_headless and PLAYWRIGHT_AVAILABLE:
            self.headless_fetcher = HeadlessFetcher(config)
    
    def _needs_headless(self, url: str) -> bool:
        """Check if URL needs headless browser."""
        if not self.use_headless:
            return False
        
        domain = urlparse(url).netloc.lower()
        return any(js_domain in domain for js_domain in self.JS_HEAVY_DOMAINS)
    
    def fetch(self, url: str) -> CrawlResult:
        """Fetch URL using appropriate method."""
        if self._needs_headless(url) and self.headless_fetcher:
            return self.headless_fetcher.fetch(url)
        return self.regular_fetcher.fetch(url)
    
    def fetch_multiple(self, urls: List[str]) -> List[CrawlResult]:
        """Fetch multiple URLs."""
        results = []
        for url in urls:
            results.append(self.fetch(url))
        return results
    
    def close(self):
        """Close all fetchers."""
        self.regular_fetcher.close()
        if self.headless_fetcher:
            self.headless_fetcher.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
