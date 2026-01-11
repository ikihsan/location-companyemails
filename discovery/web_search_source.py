"""
Web search sources for discovering companies.
Uses DuckDuckGo HTML which is more scraper-friendly.
"""

import re
from typing import List, Generator, Optional, Set
from urllib.parse import quote_plus, urljoin, urlparse
from bs4 import BeautifulSoup

from models import Company
from fetcher import PageFetcher
from parsers import HTMLParser, extract_company_name_from_url
from extractors import extract_emails_from_text, get_domain_from_url
from utils import get_logger
from .base_source import BaseSource


class DuckDuckGoSource(BaseSource):
    """
    Discovers companies through DuckDuckGo HTML search.
    More scraper-friendly than Google.
    """
    
    def __init__(self):
        super().__init__(
            name="duckduckgo",
            base_url="https://html.duckduckgo.com",
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
        """Search DuckDuckGo for job listings."""
        
        seen_domains: Set[str] = set()
        companies_found = 0
        
        for role in roles:
            if companies_found >= max_results:
                break
            
            # Search for companies hiring
            queries = [
                f'"{role}" hiring {location}',
                f'"{role}" jobs {location} careers',
                f'{role} developer jobs {location}',
            ]
            
            for query in queries:
                if companies_found >= max_results:
                    break
                
                search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
                
                self.logger.debug(f"Searching DuckDuckGo: {query}")
                
                result = self.fetcher.fetch(search_url)
                
                if not result.success or not result.html_content:
                    self.logger.warning(f"Failed to fetch DuckDuckGo results: {result.error}")
                    continue
                
                # Parse search results
                soup = BeautifulSoup(result.html_content, 'lxml')
                
                # DuckDuckGo HTML uses .result__url for result links
                for result_div in soup.find_all('div', class_='result'):
                    if companies_found >= max_results:
                        break
                    
                    # Get the URL
                    url_elem = result_div.find('a', class_='result__url')
                    title_elem = result_div.find('a', class_='result__a')
                    snippet_elem = result_div.find('a', class_='result__snippet')
                    
                    if not url_elem and not title_elem:
                        continue
                    
                    # Get URL from href
                    link = None
                    if title_elem and title_elem.get('href'):
                        link = title_elem['href']
                    elif url_elem:
                        link = url_elem.get_text(strip=True)
                        if not link.startswith('http'):
                            link = f"https://{link}"
                    
                    if not link:
                        continue
                    
                    # Skip unwanted domains
                    skip_domains = [
                        'duckduckgo.com', 'google.com', 'bing.com', 
                        'indeed.com', 'linkedin.com', 'glassdoor.com',
                        'monster.com', 'ziprecruiter.com', 'facebook.com',
                        'twitter.com', 'youtube.com', 'wikipedia.org'
                    ]
                    
                    domain = get_domain_from_url(link)
                    if not domain:
                        continue
                    
                    if any(skip in domain for skip in skip_domains):
                        continue
                    
                    if domain in seen_domains:
                        continue
                    
                    seen_domains.add(domain)
                    
                    # Get company name from title or domain
                    title = title_elem.get_text(strip=True) if title_elem else ""
                    company_name = self._extract_company_from_title(title) or extract_company_name_from_url(link)
                    
                    snippet = snippet_elem.get_text(strip=True)[:300] if snippet_elem else ""
                    
                    company = Company(
                        name=company_name,
                        location=location,
                        source_url=link,
                        hiring_roles=[role],
                        website=f"https://{domain}",
                        job_description_snippet=snippet,
                    )
                    
                    companies_found += 1
                    self.logger.debug(f"Found company: {company_name} ({domain})")
                    yield company
    
    def _extract_company_from_title(self, title: str) -> Optional[str]:
        """Try to extract company name from search result title."""
        if not title:
            return None
        
        # Common patterns: "Job at Company", "Company - Careers", "Company is hiring"
        patterns = [
            r'(?:jobs?\s+at\s+)([^|–\-]+)',
            r'^([^|–\-]+?)(?:\s*[-–|]\s*careers)',
            r'^([^|–\-]+?)(?:\s+is\s+hiring)',
            r'^([^|–\-]+?)(?:\s*[-–|])',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, title, re.I)
            if match:
                name = match.group(1).strip()
                if len(name) > 2 and len(name) < 50:
                    return name
        
        return None
    
    def get_company_details(self, company: Company) -> Company:
        """Enrich company with details from its website."""
        if not company.website:
            return company
        
        result = self.fetcher.fetch(company.website)
        
        if result.success and result.html_content:
            parser = HTMLParser(company.website)
            parsed = parser.parse(result.html_content)
            
            # Update company name if we found a better one
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


class TechJobsSource(BaseSource):
    """
    Aggregates from various tech job listing sites.
    """
    
    # Tech job boards that list company info
    JOB_SITES = [
        {
            'name': 'RemoteOK',
            'url': 'https://remoteok.com/remote-{role}-jobs',
            'roles_map': {
                'software developer': 'dev',
                'backend developer': 'backend',
                'full stack developer': 'full-stack',
                'software engineer': 'engineer',
                'web developer': 'web-dev',
                'python developer': 'python',
                'devops engineer': 'devops',
            }
        },
        {
            'name': 'WeWorkRemotely',
            'url': 'https://weworkremotely.com/categories/remote-{role}-jobs',
            'roles_map': {
                'software developer': 'programming',
                'backend developer': 'back-end-programming',
                'full stack developer': 'full-stack-programming',
                'software engineer': 'programming',
                'web developer': 'front-end-programming',
            }
        },
    ]
    
    def __init__(self):
        super().__init__(
            name="tech_jobs",
            base_url="https://remoteok.com",
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
        """Search tech job boards."""
        
        seen_companies: Set[str] = set()
        companies_found = 0
        
        for site in self.JOB_SITES:
            if companies_found >= max_results:
                break
            
            for role in roles:
                if companies_found >= max_results:
                    break
                
                role_key = site['roles_map'].get(role.lower())
                if not role_key:
                    continue
                
                url = site['url'].format(role=role_key)
                self.logger.debug(f"Fetching {site['name']}: {url}")
                
                result = self.fetcher.fetch(url)
                
                if not result.success or not result.html_content:
                    continue
                
                soup = BeautifulSoup(result.html_content, 'lxml')
                
                # Look for job listings with company names
                for job_elem in soup.find_all(['tr', 'article', 'div'], class_=re.compile(r'job|posting', re.I)):
                    if companies_found >= max_results:
                        break
                    
                    # Try to find company name
                    company_elem = job_elem.find(class_=re.compile(r'company', re.I))
                    if not company_elem:
                        company_elem = job_elem.find('h3')
                    
                    if not company_elem:
                        continue
                    
                    company_name = company_elem.get_text(strip=True)
                    if not company_name or len(company_name) < 2:
                        continue
                    
                    # Normalize for dedup
                    company_key = company_name.lower().strip()
                    if company_key in seen_companies:
                        continue
                    
                    seen_companies.add(company_key)
                    
                    # Find job link
                    job_link = job_elem.find('a', href=True)
                    job_url = urljoin(url, job_link['href']) if job_link else url
                    
                    # Get job title
                    title_elem = job_elem.find(class_=re.compile(r'title|position', re.I))
                    job_title = title_elem.get_text(strip=True) if title_elem else role
                    
                    company = Company(
                        name=company_name,
                        location=location,  # May be remote
                        source_url=job_url,
                        hiring_roles=[job_title],
                    )
                    
                    companies_found += 1
                    yield company
    
    def get_company_details(self, company: Company) -> Company:
        """Enrich company - for remote jobs, try to find company website."""
        if company.source_url:
            result = self.fetcher.fetch(company.source_url)
            
            if result.success and result.html_content:
                soup = BeautifulSoup(result.html_content, 'lxml')
                
                # Look for company website link
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    text = link.get_text(strip=True).lower()
                    
                    if 'website' in text or 'company' in text or 'apply' in text:
                        if href.startswith('http') and 'remoteok' not in href and 'weworkremotely' not in href:
                            company.website = href
                            break
                
                # Extract emails
                emails = extract_emails_from_text(
                    result.html_content,
                    company.source_url,
                    get_domain_from_url(company.website) if company.website else None
                )
                for email in emails:
                    company.add_email(email)
        
        return company
