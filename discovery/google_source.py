"""
Google Jobs search source.
Scrapes job listings from Google search results.
"""

import re
from typing import List, Generator, Optional
from urllib.parse import urlencode, quote_plus

from models import Company
from fetcher import PageFetcher
from parsers import HTMLParser, extract_company_name_from_url
from extractors import extract_emails_from_text, get_domain_from_url
from utils import get_logger
from .base_source import BaseSource


class GoogleJobsSource(BaseSource):
    """
    Discovers companies through Google job search.
    """
    
    def __init__(self):
        super().__init__(
            name="google_jobs",
            base_url="https://www.google.com",
            requires_js=False,
        )
        self.logger = get_logger()
        self.fetcher = PageFetcher()
    
    def search(
        self,
        location: str,
        roles: List[str],
        max_results: int = 100,
    ) -> Generator[Company, None, None]:
        """Search Google for job listings."""
        
        for role in roles:
            query = f"{role} jobs {location}"
            search_url = f"https://www.google.com/search?q={quote_plus(query)}&num=50"
            
            self.logger.debug(f"Searching Google: {query}")
            
            result = self.fetcher.fetch(search_url)
            
            if not result.success or not result.html_content:
                self.logger.warning(f"Failed to fetch Google results: {result.error}")
                continue
            
            # Parse search results
            parser = HTMLParser(search_url)
            parsed = parser.parse(result.html_content)
            
            # Extract company URLs from search results
            seen_domains = set()
            for link in parsed.links:
                # Skip Google internal links
                if 'google.com' in link:
                    continue
                
                domain = get_domain_from_url(link)
                if domain and domain not in seen_domains:
                    seen_domains.add(domain)
                    
                    company = Company(
                        name=extract_company_name_from_url(link),
                        location=location,
                        source_url=link,
                        hiring_roles=[role],
                        website=f"https://{domain}",
                    )
                    
                    if len(seen_domains) >= max_results // len(roles):
                        break
                    
                    yield company
    
    def get_company_details(self, company: Company) -> Company:
        """Enrich company with details from its website."""
        if not company.website:
            return company
        
        result = self.fetcher.fetch(company.website)
        
        if result.success and result.html_content:
            parser = HTMLParser(company.website)
            parsed = parser.parse(result.html_content)
            
            # Update company info
            if parsed.company_info.get('name'):
                company.name = parsed.company_info['name']
            
            # Find careers page
            if parsed.careers_links:
                company.careers_url = parsed.careers_links[0]
            
            # Get LinkedIn
            if 'linkedin' in parsed.social_links:
                company.linkedin_url = parsed.social_links['linkedin']
            
            # Extract emails
            domain = get_domain_from_url(company.website)
            emails = extract_emails_from_text(
                result.html_content,
                company.website,
                domain,
            )
            for email in emails:
                company.add_email(email)
            
            company.http_status = result.status_code
        
        return company
