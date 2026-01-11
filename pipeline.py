"""
Main pipeline orchestrator.
Coordinates discovery, crawling, extraction, and storage.
"""

import signal
import sys
from typing import List, Optional, Set
from datetime import datetime

from config import Config, get_config
from models import Company
from discovery import (
    BaseSource,
    GoogleJobsSource,
    JobBoardSource,
    StartupDirectorySource,
    CompanyCrawler,
    CrawlConfig,
    get_registry,
    register_source,
)
from storage import DataStorage, CompanyDeduplicator
from utils import get_logger, setup_logger, ProgressTracker


class ScrapingPipeline:
    """
    Main orchestrator for the company scraping pipeline.
    Coordinates all modules to discover, crawl, and store company data.
    """
    
    def __init__(
        self,
        locations: List[str],
        roles: Optional[List[str]] = None,
        max_companies: int = 100,
        use_headless: bool = False,
        verbose: bool = False,
        config: Optional[Config] = None,
    ):
        self.locations = locations
        self.config = config or get_config()
        self.roles = roles or self.config.target_roles
        self.max_companies = max_companies
        self.use_headless = use_headless
        
        # Setup logging
        self.logger = setup_logger(
            verbose=verbose,
            log_dir=self.config.storage.log_dir,
        )
        
        # Initialize components
        self.storage = DataStorage(self.config.storage.output_dir)
        self.deduplicator = CompanyDeduplicator()
        self.crawler = CompanyCrawler(
            config=CrawlConfig(max_depth=4, max_pages_per_company=20),  # Deep crawl
            use_headless=use_headless,
        )
        
        # Setup sources
        self._setup_sources()
        
        # Graceful shutdown handling
        self._shutdown_requested = False
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
    
    def _setup_sources(self):
        """Register all discovery sources - ULTIMATE SOURCE for max volume."""
        from discovery.ultimate_source import UltimateSource, get_ultimate_source
        
        registry = get_registry()
        
        # Use the ULTIMATE SOURCE - guaranteed 100+ companies
        # Starts with 120+ known IT companies, then scrapes multiple job portals
        # FreshersWorld, TimesJobs, Shine, Google, Bing - all with smart dedup
        register_source(get_ultimate_source())
        
        # Add fallback sources
        try:
            from discovery.job_portals_source import MultiJobPortalSource, SearchEngineSource
            register_source(MultiJobPortalSource())
            register_source(SearchEngineSource())
        except ImportError:
            pass
        
        self.logger.info(f"🚀 Registered {len(registry.get_enabled())} discovery sources")
    
    def _handle_shutdown(self, signum, frame):
        """Handle graceful shutdown."""
        self.logger.warning("Shutdown requested, flushing partial results...")
        self._shutdown_requested = True
        
        # Flush partial results
        location_str = ', '.join(self.locations)
        self.storage.flush_partial(location_str)
        
        self.logger.info("Partial results saved. Exiting.")
        sys.exit(0)
    
    def run(self) -> dict:
        """
        Run the complete scraping pipeline.
        Returns summary statistics.
        """
        start_time = datetime.now()
        
        self.logger.info(f"Starting pipeline for locations: {self.locations}")
        self.logger.info(f"Target roles: {self.roles}")
        self.logger.info(f"Max companies: {self.max_companies}")
        
        companies_discovered = 0
        companies_with_emails = 0
        total_emails = 0
        
        registry = get_registry()
        sources = registry.get_enabled()
        
        if not sources:
            self.logger.error("No discovery sources enabled!")
            return {'error': 'No sources enabled'}
        
        # Phase 1: Discovery
        self.logger.info("Phase 1: Discovering companies...")
        
        for location in self.locations:
            if self._shutdown_requested:
                break
            
            self.logger.info(f"Searching in: {location}")
            
            for source in sources:
                if self._shutdown_requested:
                    break
                
                if companies_discovered >= self.max_companies:
                    break
                
                self.logger.info(f"Using source: {source.name}")
                
                try:
                    remaining = self.max_companies - companies_discovered
                    
                    for company in source.search(location, self.roles, remaining):
                        if self._shutdown_requested:
                            break
                        
                        if self.deduplicator.is_duplicate(company):
                            continue
                        
                        self.deduplicator.add(company)
                        self.storage.add_company(company)
                        companies_discovered += 1
                        
                        if companies_discovered % 10 == 0:
                            self.logger.info(f"Discovered {companies_discovered} companies...")
                        
                        if companies_discovered >= self.max_companies:
                            break
                
                except Exception as e:
                    self.logger.exception(f"Error with source {source.name}: {e}")
        
        self.logger.info(f"Phase 1 complete: {companies_discovered} companies discovered")
        
        # Phase 2: Deep crawling and email extraction
        self.logger.info("Phase 2: Crawling company websites...")
        
        companies = self.storage.get_companies()
        
        with ProgressTracker(len(companies), "Crawling") as progress:
            for i, company in enumerate(companies):
                if self._shutdown_requested:
                    break
                
                try:
                    # Deep crawl company website
                    enriched = self.crawler.crawl_company(company)
                    
                    # Also crawl careers page specifically
                    enriched = self.crawler.crawl_careers_page(enriched)
                    
                    if enriched.emails:
                        companies_with_emails += 1
                        total_emails += len(enriched.emails)
                    
                    progress.update(1, f"Crawling {company.name[:30]}...")
                    
                except Exception as e:
                    self.logger.warning(f"Error crawling {company.name}: {e}")
                    progress.update(1)
        
        self.logger.info(f"Phase 2 complete: {companies_with_emails} companies with emails")
        
        # Phase 3: Save results
        self.logger.info("Phase 3: Saving results...")
        
        location_str = ', '.join(self.locations)
        output_files = self.storage.save_all(location_str)
        
        # Cleanup
        self.crawler.close()
        
        # Summary
        elapsed = (datetime.now() - start_time).total_seconds()
        
        summary = {
            'locations': self.locations,
            'roles': self.roles,
            'companies_discovered': companies_discovered,
            'companies_with_emails': companies_with_emails,
            'total_emails': total_emails,
            'output_files': {k: str(v) for k, v in output_files.items()},
            'elapsed_seconds': elapsed,
        }
        
        self.logger.info("=" * 50)
        self.logger.info("PIPELINE COMPLETE")
        self.logger.info(f"Companies discovered: {companies_discovered}")
        self.logger.info(f"Companies with emails: {companies_with_emails}")
        self.logger.info(f"Total emails found: {total_emails}")
        self.logger.info(f"Output files: {output_files}")
        self.logger.info(f"Elapsed time: {elapsed:.1f}s")
        self.logger.info("=" * 50)
        
        return summary


def run_pipeline(
    locations: List[str],
    roles: Optional[List[str]] = None,
    max_companies: int = 100,
    use_headless: bool = False,
    verbose: bool = False,
) -> dict:
    """
    Convenience function to run the pipeline.
    """
    pipeline = ScrapingPipeline(
        locations=locations,
        roles=roles,
        max_companies=max_companies,
        use_headless=use_headless,
        verbose=verbose,
    )
    
    return pipeline.run()
