"""
Generic job board scraper source.
Works with common job board patterns.
"""

import re
from typing import List, Generator, Optional
from urllib.parse import urljoin, quote_plus

from models import Company
from fetcher import PageFetcher, HybridFetcher
from parsers import HTMLParser, extract_company_name_from_url, find_careers_page
from extractors import extract_emails_from_text, get_domain_from_url
from utils import get_logger
from .base_source import BaseSource


class JobBoardSource(BaseSource):
    """
    Generic job board source that can be configured for different boards.
    """
    
    # Common job board configurations
    BOARDS = {
        'indeed': {
            'base_url': 'https://www.indeed.com',
            'search_path': '/jobs',
            'search_params': {'q': '{role}', 'l': '{location}'},
            'requires_js': True,
        },
        'glassdoor': {
            'base_url': 'https://www.glassdoor.com',
            'search_path': '/Job/jobs.htm',
            'search_params': {'sc.keyword': '{role}', 'locT': 'C', 'locId': '{location}'},
            'requires_js': True,
        },
        'stepstone': {
            'base_url': 'https://www.stepstone.de',
            'search_path': '/jobs/{role}/in-{location}',
            'requires_js': False,
        },
    }
    
    def __init__(self, board_name: str = 'indeed', use_headless: bool = False):
        board_config = self.BOARDS.get(board_name, self.BOARDS['indeed'])
        
        super().__init__(
            name=f"jobboard_{board_name}",
            base_url=board_config['base_url'],
            requires_js=board_config.get('requires_js', False),
        )
        
        self.board_name = board_name
        self.board_config = board_config
        self.logger = get_logger()
        self.fetcher = HybridFetcher(use_headless=use_headless)
    
    def _build_search_url(self, role: str, location: str) -> str:
        """Build search URL for the job board."""
        base = self.board_config['base_url']
        path = self.board_config.get('search_path', '')
        
        # Replace placeholders in path
        path = path.replace('{role}', quote_plus(role))
        path = path.replace('{location}', quote_plus(location))
        
        url = urljoin(base, path)
        
        # Add query params if configured
        params = self.board_config.get('search_params', {})
        if params:
            param_str = '&'.join([
                f"{k}={quote_plus(v.format(role=role, location=location))}"
                for k, v in params.items()
            ])
            url = f"{url}?{param_str}"
        
        return url
    
    def search(
        self,
        location: str,
        roles: List[str],
        max_results: int = 100,
    ) -> Generator[Company, None, None]:
        """Search job board for listings."""
        
        companies_found = 0
        
        for role in roles:
            if companies_found >= max_results:
                break
            
            search_url = self._build_search_url(role, location)
            self.logger.debug(f"Searching {self.board_name}: {search_url}")
            
            result = self.fetcher.fetch(search_url)
            
            if not result.success or not result.html_content:
                self.logger.warning(f"Failed to fetch {self.board_name}: {result.error}")
                continue
            
            # Parse job listings
            parser = HTMLParser(search_url)
            parsed = parser.parse(result.html_content)
            
            # Extract from structured job postings
            for job in parsed.job_postings:
                if companies_found >= max_results:
                    break
                
                company_name = job.get('company', '') or extract_company_name_from_url(job.get('url', ''))
                if not company_name:
                    continue
                
                company = Company(
                    name=company_name,
                    location=job.get('location', location),
                    source_url=job.get('url', search_url),
                    hiring_roles=[job.get('title', role)],
                    job_description_snippet=job.get('description', '')[:300],
                )
                
                companies_found += 1
                yield company
    
    def get_company_details(self, company: Company) -> Company:
        """Enrich company with additional details."""
        # Similar to GoogleJobsSource implementation
        if company.website:
            result = self.fetcher.fetch(company.website)
            
            if result.success and result.html_content:
                parser = HTMLParser(company.website)
                parsed = parser.parse(result.html_content)
                
                if parsed.careers_links:
                    company.careers_url = parsed.careers_links[0]
                
                if 'linkedin' in parsed.social_links:
                    company.linkedin_url = parsed.social_links['linkedin']
                
                domain = get_domain_from_url(company.website)
                emails = extract_emails_from_text(
                    result.html_content,
                    company.website,
                    domain,
                )
                for email in emails:
                    company.add_email(email)
        
        return company


class StartupDirectorySource(BaseSource):
    """
    Source for startup directories like Wellfound, Crunchbase, etc.
    """
    
    DIRECTORIES = {
        'wellfound': {
            'base_url': 'https://wellfound.com',
            'search_path': '/role/{role}',
            'location_filter': 'location={location}',
            'requires_js': True,
        },
        'ycombinator': {
            'base_url': 'https://www.workatastartup.com',
            'search_path': '/jobs',
            'requires_js': True,
        },
    }
    
    def __init__(self, directory_name: str = 'wellfound', use_headless: bool = False):
        dir_config = self.DIRECTORIES.get(directory_name, self.DIRECTORIES['wellfound'])
        
        super().__init__(
            name=f"startup_{directory_name}",
            base_url=dir_config['base_url'],
            requires_js=dir_config.get('requires_js', True),
        )
        
        self.directory_name = directory_name
        self.dir_config = dir_config
        self.logger = get_logger()
        self.use_headless = use_headless
        self.fetcher = HybridFetcher(use_headless=use_headless)
    
    def search(
        self,
        location: str,
        roles: List[str],
        max_results: int = 100,
    ) -> Generator[Company, None, None]:
        """Search startup directory."""
        
        # Map generic roles to directory-specific terms
        role_mapping = {
            'software developer': 'software-engineer',
            'backend developer': 'backend-engineer',
            'full stack developer': 'full-stack-engineer',
            'software engineer': 'software-engineer',
            'web developer': 'frontend-engineer',
        }
        
        companies_found = 0
        
        for role in roles:
            if companies_found >= max_results:
                break
            
            mapped_role = role_mapping.get(role.lower(), 'software-engineer')
            
            search_url = urljoin(
                self.dir_config['base_url'],
                self.dir_config.get('search_path', '').replace('{role}', mapped_role)
            )
            
            if 'location_filter' in self.dir_config:
                search_url += '?' + self.dir_config['location_filter'].replace(
                    '{location}', quote_plus(location)
                )
            
            self.logger.debug(f"Searching {self.directory_name}: {search_url}")
            
            result = self.fetcher.fetch(search_url)
            
            if not result.success or not result.html_content:
                self.logger.warning(f"Failed to fetch {self.directory_name}: {result.error}")
                continue
            
            parser = HTMLParser(search_url)
            parsed = parser.parse(result.html_content)
            
            # Parse startup listings
            for job in parsed.job_postings:
                if companies_found >= max_results:
                    break
                
                company_name = job.get('company', '')
                if not company_name:
                    continue
                
                company = Company(
                    name=company_name,
                    location=job.get('location', location),
                    source_url=job.get('url', search_url),
                    hiring_roles=[job.get('title', role)],
                    job_description_snippet=job.get('description', '')[:300],
                )
                
                companies_found += 1
                yield company
    
    def get_company_details(self, company: Company) -> Company:
        """Enrich startup with details."""
        if not company.source_url:
            return company
        
        result = self.fetcher.fetch(company.source_url)
        
        if result.success and result.html_content:
            parser = HTMLParser(company.source_url)
            parsed = parser.parse(result.html_content)
            
            # Extract website from startup page
            for link in parsed.links:
                if 'linkedin.com' not in link and 'wellfound' not in link:
                    domain = get_domain_from_url(link)
                    if domain and '.' in domain:
                        company.website = link
                        break
            
            if 'linkedin' in parsed.social_links:
                company.linkedin_url = parsed.social_links['linkedin']
            
            # Extract emails
            emails = extract_emails_from_text(
                result.html_content,
                company.source_url,
                get_domain_from_url(company.website) if company.website else None,
            )
            for email in emails:
                company.add_email(email)
        
        return company
