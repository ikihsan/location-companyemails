"""
Discovery package for finding companies.
All sources are DYNAMIC - scraping real job portals and search engines.
PowerSource uses BeautifulSoup for reliable extraction.
"""

from .base_source import (
    BaseSource,
    SourceRegistry,
    DiscoveryResult,
    get_registry,
    register_source,
)
from .google_source import GoogleJobsSource
from .job_board_source import JobBoardSource, StartupDirectorySource
from .company_crawler import CompanyCrawler, CrawlConfig
from .web_search_source import DuckDuckGoSource, TechJobsSource
from .job_portals_source import MultiJobPortalSource, SearchEngineSource, StartupListSource, ITParksSource
from .mega_source import MegaSource, get_mega_source, WebsiteDiscovery
from .power_source import PowerSource, get_power_source
from .ultimate_source import UltimateSource, get_ultimate_source

__all__ = [
    'BaseSource',
    'SourceRegistry',
    'DiscoveryResult',
    'get_registry',
    'register_source',
    'GoogleJobsSource',
    'JobBoardSource',
    'StartupDirectorySource',
    'CompanyCrawler',
    'CrawlConfig',
    'DuckDuckGoSource',
    'TechJobsSource',
    'MultiJobPortalSource',
    'SearchEngineSource',
    'StartupListSource',
    'ITParksSource',
    'MegaSource',
    'get_mega_source',
    'WebsiteDiscovery',
    'PowerSource',
    'get_power_source',
    'UltimateSource',
    'get_ultimate_source',
]
