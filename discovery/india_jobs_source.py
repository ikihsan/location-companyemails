"""
India-focused job sources - scrapes Indian job boards and company directories.
"""

import re
import time
from typing import List, Generator, Optional
from urllib.parse import urljoin, quote_plus

from models import Company
from fetcher import PageFetcher
from utils import get_logger
from .base_source import BaseSource


class IndiaJobsSource(BaseSource):
    """
    Scrapes Indian job portals and company directories.
    Sources: Naukri, Indeed India, LinkedIn India, Glassdoor India, etc.
    """
    
    # Job board search URLs
    JOB_BOARDS = {
        'indeed_india': 'https://www.indeed.co.in/jobs?q={query}&l={location}',
        'glassdoor_india': 'https://www.glassdoor.co.in/Job/jobs.htm?sc.keyword={query}&locT=C&locId={location_id}',
        'instahyre': 'https://www.instahyre.com/search-jobs/?job_type=&location={location}&search_query={query}',
        'cutshort': 'https://cutshort.io/jobs?search={query}&location={location}',
        'angellist': 'https://angel.co/location/{location}',
    }
    
    # Common company patterns in job listings
    COMPANY_PATTERNS = [
        r'<a[^>]*class="[^"]*company[^"]*"[^>]*>([^<]+)</a>',
        r'data-company[^>]*>([^<]+)<',
        r'"companyName"\s*:\s*"([^"]+)"',
        r'"company"\s*:\s*"([^"]+)"',
        r'class="[^"]*employer[^"]*"[^>]*>([^<]+)<',
        r'"employer"\s*:\s*\{[^}]*"name"\s*:\s*"([^"]+)"',
        r'<span[^>]*class="[^"]*company-name[^"]*"[^>]*>([^<]+)</span>',
    ]
    
    # Company website patterns
    WEBSITE_PATTERNS = [
        r'href="(https?://(?:www\.)?[a-zA-Z0-9-]+\.[a-z]{2,})"[^>]*>(?:Visit|Website|Company)',
        r'"companyWebsite"\s*:\s*"([^"]+)"',
        r'"website"\s*:\s*"([^"]+)"',
        r'"url"\s*:\s*"(https?://[^"]+)"',
    ]
    
    def __init__(self):
        super().__init__(
            name="india_jobs",
            base_url="https://www.indeed.co.in",
            requires_js=False,
        )
        self.rate_limit = 2.0  # Be gentle with job boards
        self.fetcher = PageFetcher()  # Uses default config
    
    def search(
        self,
        location: str,
        roles: List[str],
        max_results: int = 100,
    ) -> Generator[Company, None, None]:
        """Search Indian job boards for companies hiring."""
        
        companies_found = set()
        count = 0
        
        for role in roles:
            if count >= max_results:
                break
            
            # Try Indeed India
            for company in self._search_indeed(role, location, max_results - count):
                if company.name.lower() not in companies_found:
                    companies_found.add(company.name.lower())
                    count += 1
                    yield company
                    if count >= max_results:
                        break
            
            # Try to find companies from directory sites
            for company in self._search_directories(role, location, max_results - count):
                if company.name.lower() not in companies_found:
                    companies_found.add(company.name.lower())
                    count += 1
                    yield company
                    if count >= max_results:
                        break
    
    def _search_indeed(
        self,
        role: str,
        location: str,
        max_results: int
    ) -> Generator[Company, None, None]:
        """Search Indeed India for job listings and extract companies."""
        
        query = quote_plus(role)
        loc = quote_plus(location)
        
        # Try multiple pages
        for page in range(0, min(5, (max_results // 15) + 1)):
            url = f"https://www.indeed.co.in/jobs?q={query}&l={loc}&start={page * 10}"
            
            result = self.fetcher.fetch(url)
            if not result.success:
                self.logger.warning(f"Failed to fetch Indeed page {page}: {result.error}")
                continue
            
            # Extract company names and details
            companies = self._extract_companies_from_html(result.html_content or '', url, role, location)
            
            for company in companies:
                yield company
            
            time.sleep(self.rate_limit)
    
    def _search_directories(
        self,
        role: str,
        location: str,
        max_results: int
    ) -> Generator[Company, None, None]:
        """Search company directories and startup lists."""
        
        # Try searching Google for company lists
        search_queries = [
            f"top IT companies in {location}",
            f"software companies hiring in {location}",
            f"tech startups in {location}",
            f"{role} jobs {location} company list",
        ]
        
        count = 0
        for query in search_queries:
            if count >= max_results:
                break
            
            # Use DuckDuckGo HTML search
            url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            
            result = self.fetcher.fetch(url)
            if not result.success:
                continue
            
            # Extract any company names mentioned
            companies = self._extract_companies_from_search(result.html_content or '', role, location)
            
            for company in companies:
                count += 1
                yield company
                if count >= max_results:
                    break
            
            time.sleep(self.rate_limit)
    
    def _extract_companies_from_html(
        self,
        content: str,
        source_url: str,
        role: str,
        location: str
    ) -> List[Company]:
        """Extract company information from job board HTML."""
        
        companies = []
        seen_names = set()
        
        for pattern in self.COMPANY_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for name in matches:
                name = name.strip()
                if len(name) > 2 and len(name) < 100 and name.lower() not in seen_names:
                    # Clean up the name
                    name = re.sub(r'\s+', ' ', name)
                    name = name.strip()
                    
                    if self._is_valid_company_name(name):
                        seen_names.add(name.lower())
                        companies.append(Company(
                            name=name,
                            location=location,
                            source_url=source_url,
                            hiring_roles=[role],
                        ))
        
        return companies
    
    def _extract_companies_from_search(
        self,
        content: str,
        role: str,
        location: str
    ) -> List[Company]:
        """Extract companies from search result snippets."""
        
        companies = []
        seen = set()
        
        # Common tech company name patterns
        patterns = [
            r'([A-Z][a-zA-Z0-9]+ (?:Technologies|Tech|Software|Systems|Solutions|Labs|Digital|IT|Infotech|Consulting))',
            r'([A-Z][a-zA-Z0-9]+ (?:Pvt\.? Ltd\.?|Private Limited|LLP|Inc\.?))',
            r'([A-Z][a-zA-Z]+(?:soft|tech|sys|ware|cloud|data|net))',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content)
            for name in matches:
                name = name.strip()
                if name.lower() not in seen and self._is_valid_company_name(name):
                    seen.add(name.lower())
                    companies.append(Company(
                        name=name,
                        location=location,
                        source_url="search_result",
                        hiring_roles=[role],
                    ))
        
        return companies
    
    def _is_valid_company_name(self, name: str) -> bool:
        """Check if a string looks like a valid company name."""
        if not name or len(name) < 3:
            return False
        
        # Filter out common false positives
        invalid = [
            'javascript', 'python', 'java', 'react', 'angular', 'node',
            'remote', 'full time', 'part time', 'contract', 'freelance',
            'posted', 'days ago', 'apply', 'save job', 'company', 'employer',
            'salary', 'location', 'job type', 'experience', 'skills',
            'description', 'requirements', 'qualifications', 'benefits',
            'cookie', 'privacy', 'terms', 'sign in', 'login', 'register',
        ]
        
        name_lower = name.lower()
        return not any(inv in name_lower for inv in invalid)
    
    def get_company_details(self, company: Company) -> Company:
        """Try to find more details about a company."""
        # Search for company website if not present
        if not company.website:
            company.website = self._find_company_website(company.name)
        
        return company
    
    def _find_company_website(self, company_name: str) -> Optional[str]:
        """Try to find a company's website via search."""
        query = quote_plus(f"{company_name} official website")
        url = f"https://html.duckduckgo.com/html/?q={query}"
        
        result = self.fetcher.fetch(url)
        if not result.success:
            return None
        
        # Look for likely website URLs
        pattern = r'href="(https?://(?:www\.)?[a-zA-Z0-9-]+\.(?:com|in|io|co|org|net))"'
        matches = re.findall(pattern, result.html_content or '')
        
        for url in matches:
            # Skip common non-company domains
            skip_domains = ['google', 'facebook', 'linkedin', 'twitter', 'youtube', 
                          'wikipedia', 'indeed', 'glassdoor', 'naukri', 'duckduckgo']
            if not any(d in url.lower() for d in skip_domains):
                return url
        
        return None
