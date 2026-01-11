"""
Configuration management for the company scraper.
Loads settings from environment variables and .env file.
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()


@dataclass
class ProxyConfig:
    """Proxy configuration settings."""
    http_proxy: Optional[str] = None
    https_proxy: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> 'ProxyConfig':
        return cls(
            http_proxy=os.getenv('HTTP_PROXY') or None,
            https_proxy=os.getenv('HTTPS_PROXY') or None,
            username=os.getenv('PROXY_USERNAME') or None,
            password=os.getenv('PROXY_PASSWORD') or None,
        )
    
    def get_proxies(self) -> Optional[dict]:
        """Return proxies dict for requests library."""
        if not self.http_proxy and not self.https_proxy:
            return None
        proxies = {}
        if self.http_proxy:
            proxies['http'] = self.http_proxy
        if self.https_proxy:
            proxies['https'] = self.https_proxy
        return proxies


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    max_requests_per_minute: int = 30
    max_concurrent_requests: int = 5
    min_delay_seconds: float = 1.0
    max_delay_seconds: float = 3.0
    
    @classmethod
    def from_env(cls) -> 'RateLimitConfig':
        return cls(
            max_requests_per_minute=int(os.getenv('MAX_REQUESTS_PER_MINUTE', 30)),
            max_concurrent_requests=int(os.getenv('MAX_CONCURRENT_REQUESTS', 5)),
            min_delay_seconds=float(os.getenv('MIN_DELAY_SECONDS', 1.0)),
            max_delay_seconds=float(os.getenv('MAX_DELAY_SECONDS', 3.0)),
        )


@dataclass
class BrowserConfig:
    """Headless browser configuration."""
    use_headless: bool = True
    timeout: int = 30000
    
    @classmethod
    def from_env(cls) -> 'BrowserConfig':
        return cls(
            use_headless=os.getenv('USE_HEADLESS', 'true').lower() == 'true',
            timeout=int(os.getenv('BROWSER_TIMEOUT', 30000)),
        )


@dataclass
class StorageConfig:
    """Storage configuration."""
    output_dir: Path = field(default_factory=lambda: Path('data/company_contacts'))
    log_dir: Path = field(default_factory=lambda: Path('logs'))
    
    @classmethod
    def from_env(cls) -> 'StorageConfig':
        return cls(
            output_dir=Path(os.getenv('OUTPUT_DIR', 'data/company_contacts')),
            log_dir=Path(os.getenv('LOG_DIR', 'logs')),
        )
    
    def ensure_dirs(self):
        """Create output directories if they don't exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)


@dataclass
class ScrapingConfig:
    """Main scraping behavior configuration."""
    respect_robots_txt: bool = True
    max_retries: int = 3
    retry_backoff_factor: float = 2.0
    debug: bool = False
    verbose: bool = False
    
    @classmethod
    def from_env(cls) -> 'ScrapingConfig':
        return cls(
            respect_robots_txt=os.getenv('RESPECT_ROBOTS_TXT', 'true').lower() == 'true',
            max_retries=int(os.getenv('MAX_RETRIES', 3)),
            retry_backoff_factor=float(os.getenv('RETRY_BACKOFF_FACTOR', 2.0)),
            debug=os.getenv('DEBUG', 'false').lower() == 'true',
            verbose=os.getenv('VERBOSE', 'false').lower() == 'true',
        )


@dataclass
class APIKeysConfig:
    """API keys for various services."""
    linkedin_api_key: Optional[str] = None
    crunchbase_api_key: Optional[str] = None
    wellfound_api_key: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> 'APIKeysConfig':
        return cls(
            linkedin_api_key=os.getenv('LINKEDIN_API_KEY') or None,
            crunchbase_api_key=os.getenv('CRUNCHBASE_API_KEY') or None,
            wellfound_api_key=os.getenv('WELLFOUND_API_KEY') or None,
        )


@dataclass
class Config:
    """Main configuration container."""
    proxy: ProxyConfig = field(default_factory=ProxyConfig)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    scraping: ScrapingConfig = field(default_factory=ScrapingConfig)
    api_keys: APIKeysConfig = field(default_factory=APIKeysConfig)
    
    # Target roles for job searching
    target_roles: List[str] = field(default_factory=lambda: [
        'software developer',
        'backend developer',
        'full stack developer',
        'software engineer',
        'web developer',
        'frontend developer',
        'python developer',
        'java developer',
    ])
    
    @classmethod
    def from_env(cls) -> 'Config':
        """Load all configuration from environment."""
        config = cls(
            proxy=ProxyConfig.from_env(),
            rate_limit=RateLimitConfig.from_env(),
            browser=BrowserConfig.from_env(),
            storage=StorageConfig.from_env(),
            scraping=ScrapingConfig.from_env(),
            api_keys=APIKeysConfig.from_env(),
        )
        config.storage.ensure_dirs()
        return config


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get or create global config instance."""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config


def reload_config() -> Config:
    """Force reload configuration from environment."""
    global _config
    load_dotenv(override=True)
    _config = Config.from_env()
    return _config
