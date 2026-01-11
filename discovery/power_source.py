"""
POWER SOURCE - High-volume, reliable company discovery engine.
Uses BeautifulSoup for proper HTML parsing, not just regex.
Focuses on sources that actually work.
"""

import re
import time
import random
from typing import List, Generator, Optional, Set, Dict
from urllib.parse import quote_plus, urlparse
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from bs4 import BeautifulSoup

from models import Company
from fetcher import PageFetcher
from utils import get_logger
from .base_source import BaseSource


@dataclass
class SourceResult:
    """Result from a single source."""
    source_name: str
    companies: List[Company]
    pages_scraped: int
    errors: List[str] = field(default_factory=list)


class PowerSource(BaseSource):
    """
    Reliable multi-source company discovery using BeautifulSoup parsing.
    Focuses on sources that actually work and extract real companies.
    """
    
    # Known major company websites (guaranteed correct)
    KNOWN_COMPANIES = {
        'tcs': ('Tata Consultancy Services', 'https://www.tcs.com'),
        'infosys': ('Infosys', 'https://www.infosys.com'),
        'wipro': ('Wipro', 'https://www.wipro.com'),
        'cognizant': ('Cognizant', 'https://www.cognizant.com'),
        'accenture': ('Accenture', 'https://www.accenture.com'),
        'hcl': ('HCL Technologies', 'https://www.hcltech.com'),
        'tech mahindra': ('Tech Mahindra', 'https://www.techmahindra.com'),
        'capgemini': ('Capgemini', 'https://www.capgemini.com'),
        'deloitte': ('Deloitte', 'https://www.deloitte.com'),
        'mphasis': ('Mphasis', 'https://www.mphasis.com'),
        'mindtree': ('Mindtree', 'https://www.mindtree.com'),
        'persistent': ('Persistent Systems', 'https://www.persistent.com'),
        'cyient': ('Cyient', 'https://www.cyient.com'),
        'hexaware': ('Hexaware', 'https://hexaware.com'),
        'zoho': ('Zoho', 'https://www.zoho.com'),
        'freshworks': ('Freshworks', 'https://www.freshworks.com'),
        'razorpay': ('Razorpay', 'https://razorpay.com'),
        'paytm': ('Paytm', 'https://paytm.com'),
        'flipkart': ('Flipkart', 'https://www.flipkart.com'),
        'swiggy': ('Swiggy', 'https://www.swiggy.com'),
        'zomato': ('Zomato', 'https://www.zomato.com'),
        'ola': ('Ola', 'https://www.olacabs.com'),
        'byju': ('Byju\'s', 'https://byjus.com'),
        'oracle': ('Oracle', 'https://www.oracle.com'),
        'microsoft': ('Microsoft', 'https://www.microsoft.com'),
        'google': ('Google', 'https://www.google.com'),
        'amazon': ('Amazon', 'https://www.amazon.com'),
        'salesforce': ('Salesforce', 'https://www.salesforce.com'),
        'servicenow': ('ServiceNow', 'https://www.servicenow.com'),
        'adobe': ('Adobe', 'https://www.adobe.com'),
        'nvidia': ('NVIDIA', 'https://www.nvidia.com'),
        'intel': ('Intel', 'https://www.intel.com'),
        'qualcomm': ('Qualcomm', 'https://www.qualcomm.com'),
        'vmware': ('VMware', 'https://www.vmware.com'),
        'ibm': ('IBM', 'https://www.ibm.com'),
        'sap': ('SAP', 'https://www.sap.com'),
    }

    def __init__(self):
        super().__init__(
            name="power_source",
            base_url="multi-platform",
            requires_js=False,
        )
        self.logger = get_logger()
        self.fetcher = PageFetcher()
        self._seen_companies: Set[str] = set()
        self._lock = threading.Lock()
    
    def search(
        self, 
        location: str, 
        roles: List[str], 
        max_results: int = 500
    ) -> Generator[Company, None, None]:
        """Search multiple sources for companies."""
        self.logger.info(f"🚀 PowerSource: Searching for {roles} in {location}")
        
        found_count = 0
        
        # Source 1: FreshersWorld (proven to work)
        self.logger.info("📍 Scraping FreshersWorld...")
        for company in self._scrape_freshersworld(location, roles, max_results):
            if found_count >= max_results:
                break
            if self._add_unique(company):
                found_count += 1
                yield company
        
        # Source 2: Search Engines (Bing + DuckDuckGo)
        self.logger.info("📍 Scraping Search Engines...")
        for company in self._scrape_search_engines(location, roles, max_results - found_count):
            if found_count >= max_results:
                break
            if self._add_unique(company):
                found_count += 1
                yield company
        
        # Source 3: Job aggregators (Cutshort, Instahyre pages)
        self.logger.info("📍 Scraping Job Aggregators...")
        for company in self._scrape_aggregators(location, roles, max_results - found_count):
            if found_count >= max_results:
                break
            if self._add_unique(company):
                found_count += 1
                yield company
        
        # Source 4: Startup directories
        self.logger.info("📍 Scraping Startup Directories...")
        for company in self._scrape_startup_lists(location, roles, max_results - found_count):
            if found_count >= max_results:
                break
            if self._add_unique(company):
                found_count += 1
                yield company
        
        self.logger.info(f"📊 PowerSource complete: {found_count} unique companies found")
    
    def _add_unique(self, company: Company) -> bool:
        """Add company if unique, return True if added."""
        key = self._normalize_name(company.name)
        with self._lock:
            if key and key not in self._seen_companies and len(key) > 2:
                self._seen_companies.add(key)
                return True
        return False
    
    def _normalize_name(self, name: str) -> str:
        """Normalize company name for deduplication."""
        if not name:
            return ""
        name = name.lower().strip()
        # Remove common suffixes
        for suffix in ['pvt', 'private', 'ltd', 'limited', 'inc', 'corp', 'llc', 'india']:
            name = re.sub(rf'\s*{suffix}\.?\s*$', '', name)
        return re.sub(r'[^\w\s]', '', name).strip()
    
    # =========================================================================
    # SOURCE 1: FreshersWorld (Proven to work)
    # =========================================================================
    
    def _scrape_freshersworld(
        self, 
        location: str, 
        roles: List[str], 
        max_results: int
    ) -> Generator[Company, None, None]:
        """Scrape FreshersWorld - proven to work well."""
        
        for role in roles:
            role_slug = role.lower().replace(' ', '-')
            location_slug = location.lower().replace(' ', '-').replace(',', '')
            
            for page in range(1, 31):  # Up to 30 pages
                url = f"https://www.freshersworld.com/jobs/jobsearch/{role_slug}-jobs-in-{location_slug}?page={page}"
                
                try:
                    resp = self.fetcher.fetch(url, timeout=30)
                    if not resp or not resp.html_content:
                        continue
                    
                    soup = BeautifulSoup(resp.html_content, 'html.parser')
                    
                    # Find job cards
                    job_cards = soup.find_all('div', class_=re.compile(r'job-?container|job-?card|job-?listing', re.I))
                    if not job_cards:
                        job_cards = soup.find_all('div', class_=re.compile(r'job', re.I))
                    
                    # Also try to find company names directly
                    companies_found = 0
                    
                    # Pattern 1: Look for company name elements
                    for elem in soup.find_all(['span', 'a', 'div', 'h3', 'h4'], 
                                              class_=re.compile(r'company|employer|org', re.I)):
                        name = elem.get_text(strip=True)
                        if name and 3 < len(name) < 100:
                            company = Company(
                                name=name,
                                location=location,
                                website=self._get_known_website(name),
                                source_url=url,
                                hiring_roles=[role],
                            )
                            companies_found += 1
                            yield company
                    
                    # Pattern 2: Job listing links often have company names
                    for link in soup.find_all('a', href=re.compile(r'job|career|position', re.I)):
                        # Check link text or title
                        text = link.get_text(strip=True)
                        # Often format is "Job Title at Company Name"
                        if ' at ' in text:
                            parts = text.split(' at ')
                            if len(parts) >= 2:
                                company_name = parts[-1].strip()
                                if company_name and 3 < len(company_name) < 100:
                                    company = Company(
                                        name=company_name,
                                        location=location,
                                        website=self._get_known_website(company_name),
                                        source_url=url,
                                        hiring_roles=[role],
                                    )
                                    yield company
                    
                    # Pattern 3: Text content analysis
                    text_content = soup.get_text()
                    # Look for patterns like "Company: XYZ" or "Hiring Company: XYZ"
                    for pattern in [
                        r'(?:company|employer|organization)\s*:\s*([A-Z][A-Za-z0-9\s&\-\.]+?)(?:\s*\||$|\n)',
                        r'(?:hiring\s+)?company\s*:\s*([A-Z][A-Za-z0-9\s&\-\.]+)',
                    ]:
                        for match in re.finditer(pattern, text_content, re.I):
                            name = match.group(1).strip()
                            if name and 3 < len(name) < 80:
                                company = Company(
                                    name=name,
                                    location=location,
                                    website=self._get_known_website(name),
                                    source_url=url,
                                    hiring_roles=[role],
                                )
                                yield company
                    
                    self.logger.debug(f"FreshersWorld page {page}: Found {companies_found} companies")
                    
                    if companies_found == 0 and page > 2:
                        break  # No more results
                    
                    time.sleep(2 + random.uniform(0.5, 1.5))
                    
                except Exception as e:
                    self.logger.debug(f"FreshersWorld error on page {page}: {str(e)[:50]}")
                    continue
    
    # =========================================================================
    # SOURCE 2: Search Engines
    # =========================================================================
    
    def _scrape_search_engines(
        self, 
        location: str, 
        roles: List[str], 
        max_results: int
    ) -> Generator[Company, None, None]:
        """Scrape Bing and DuckDuckGo for company job listings."""
        
        queries = []
        for role in roles:
            queries.extend([
                f"{role} jobs {location} hiring company careers",
                f"companies hiring {role} {location}",
                f"{location} {role} job openings company",
                f"top IT companies {location} hiring {role}",
                f"startups {location} {role} jobs",
            ])
        
        for query in queries[:10]:  # Limit queries
            # Bing
            for company in self._search_bing(query, location, roles):
                yield company
            
            # DuckDuckGo
            for company in self._search_duckduckgo(query, location, roles):
                yield company
            
            time.sleep(2)
    
    def _search_bing(
        self, 
        query: str, 
        location: str, 
        roles: List[str]
    ) -> Generator[Company, None, None]:
        """Search Bing for companies."""
        url = f"https://www.bing.com/search?q={quote_plus(query)}"
        
        try:
            resp = self.fetcher.fetch(url, timeout=20)
            if not resp or not resp.html_content:
                return
            
            soup = BeautifulSoup(resp.html_content, 'html.parser')
            
            # Extract from search result titles and snippets
            for result in soup.find_all(['li', 'div'], class_=re.compile(r'b_algo|result', re.I)):
                # Get link
                link = result.find('a')
                if not link:
                    continue
                
                href = link.get('href', '')
                text = result.get_text()
                
                # Skip job boards
                if any(jb in href.lower() for jb in ['indeed', 'linkedin', 'naukri', 'glassdoor', 'monster']):
                    continue
                
                # Extract company name from result
                company_name = self._extract_company_from_text(text)
                if company_name:
                    website = href if href.startswith('http') and 'bing.com' not in href else None
                    company = Company(
                        name=company_name,
                        location=location,
                        website=website or self._get_known_website(company_name),
                        source_url=url,
                        hiring_roles=list(roles),
                    )
                    yield company
        
        except Exception as e:
            self.logger.debug(f"Bing search error: {str(e)[:50]}")
    
    def _search_duckduckgo(
        self, 
        query: str, 
        location: str, 
        roles: List[str]
    ) -> Generator[Company, None, None]:
        """Search DuckDuckGo for companies."""
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        
        try:
            resp = self.fetcher.fetch(url, timeout=20)
            if not resp or not resp.html_content:
                return
            
            soup = BeautifulSoup(resp.html_content, 'html.parser')
            
            for result in soup.find_all('div', class_='result'):
                title = result.find('a', class_='result__a')
                snippet = result.find('a', class_='result__snippet')
                
                if not title:
                    continue
                
                href = title.get('href', '')
                text = title.get_text() + ' ' + (snippet.get_text() if snippet else '')
                
                # Skip job boards
                if any(jb in href.lower() for jb in ['indeed', 'linkedin', 'naukri', 'glassdoor']):
                    continue
                
                company_name = self._extract_company_from_text(text)
                if company_name:
                    company = Company(
                        name=company_name,
                        location=location,
                        website=self._get_known_website(company_name),
                        source_url=url,
                        hiring_roles=list(roles),
                    )
                    yield company
        
        except Exception as e:
            self.logger.debug(f"DuckDuckGo error: {str(e)[:50]}")
    
    def _extract_company_from_text(self, text: str) -> Optional[str]:
        """Extract company name from search result text."""
        # Patterns for company names
        patterns = [
            r'(?:at|@)\s+([A-Z][A-Za-z0-9\s&\-\.]+?)(?:\s*[-–|]|$)',
            r'([A-Z][A-Za-z0-9\s&]+?)\s+(?:is\s+)?hiring',
            r'([A-Z][A-Za-z0-9\s&]+?)\s+careers',
            r'([A-Z][A-Za-z0-9\s&]+?)\s+jobs',
            r'join\s+([A-Z][A-Za-z0-9\s&]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                name = match.group(1).strip()
                if 3 < len(name) < 50 and not self._is_generic_word(name):
                    return name
        
        return None
    
    def _is_generic_word(self, text: str) -> bool:
        """Check if text is a generic word, not a company name."""
        generic = {
            'jobs', 'careers', 'hiring', 'apply', 'join', 'work', 'position',
            'openings', 'vacancy', 'developer', 'engineer', 'software', 'tech',
            'fullstack', 'backend', 'frontend', 'remote', 'hybrid', 'india',
        }
        return text.lower() in generic
    
    # =========================================================================
    # SOURCE 3: Job Aggregators
    # =========================================================================
    
    def _scrape_aggregators(
        self, 
        location: str, 
        roles: List[str], 
        max_results: int
    ) -> Generator[Company, None, None]:
        """Scrape job aggregator sites."""
        
        # Cutshort
        for role in roles:
            url = f"https://cutshort.io/jobs/{role.replace(' ', '-')}-jobs-{location.lower()}"
            for company in self._scrape_page_for_companies(url, location, role):
                yield company
        
        # Internshala (fresher jobs)
        for role in roles:
            url = f"https://internshala.com/jobs/{role.replace(' ', '-')}-jobs-in-{location.lower()}"
            for company in self._scrape_page_for_companies(url, location, role):
                yield company
    
    def _scrape_page_for_companies(
        self, 
        url: str, 
        location: str, 
        role: str
    ) -> Generator[Company, None, None]:
        """Generic company scraper for any job page."""
        try:
            resp = self.fetcher.fetch(url, timeout=30)
            if not resp or not resp.html_content:
                return
            
            soup = BeautifulSoup(resp.html_content, 'html.parser')
            
            # Look for company-like elements
            for elem in soup.find_all(['span', 'a', 'div', 'h3', 'h4', 'p'],
                                      class_=re.compile(r'company|employer|org|brand', re.I)):
                name = elem.get_text(strip=True)
                if name and 3 < len(name) < 80 and not self._is_generic_word(name):
                    company = Company(
                        name=name,
                        location=location,
                        website=self._get_known_website(name),
                        source_url=url,
                        hiring_roles=[role],
                    )
                    yield company
            
            time.sleep(2)
        
        except Exception as e:
            self.logger.debug(f"Aggregator scrape error: {str(e)[:50]}")
    
    # =========================================================================
    # SOURCE 4: Startup Directories
    # =========================================================================
    
    def _scrape_startup_lists(
        self, 
        location: str, 
        roles: List[str], 
        max_results: int
    ) -> Generator[Company, None, None]:
        """Scrape startup directory pages."""
        
        # Search for startup lists
        queries = [
            f"top startups {location} 2024",
            f"IT companies {location} list",
            f"tech companies hiring {location}",
            f"software companies {location}",
        ]
        
        for query in queries[:5]:
            url = f"https://www.bing.com/search?q={quote_plus(query)}"
            
            try:
                resp = self.fetcher.fetch(url, timeout=20)
                if not resp or not resp.html_content:
                    continue
                
                soup = BeautifulSoup(resp.html_content, 'html.parser')
                
                # Look for company names in numbered/bulleted lists
                for li in soup.find_all('li'):
                    text = li.get_text(strip=True)
                    # Often lists like "1. Company Name - description"
                    match = re.match(r'^\d+\.?\s*([A-Z][A-Za-z0-9\s&\-\.]+?)(?:\s*[-–:]|\s*$)', text)
                    if match:
                        name = match.group(1).strip()
                        if 3 < len(name) < 50:
                            company = Company(
                                name=name,
                                location=location,
                                website=self._get_known_website(name),
                                source_url=url,
                                hiring_roles=list(roles),
                            )
                            yield company
                
                time.sleep(2)
            
            except Exception as e:
                continue
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _get_known_website(self, company_name: str) -> Optional[str]:
        """Get website for known companies."""
        name_lower = company_name.lower().strip()
        
        # Direct match
        for key, (_, website) in self.KNOWN_COMPANIES.items():
            if key in name_lower or name_lower in key:
                return website
        
        return None
    
    def get_company_details(self, company: Company) -> Company:
        """Enrich company with additional details."""
        return company


# Singleton instance
_power_source: Optional[PowerSource] = None


def get_power_source() -> PowerSource:
    """Get singleton instance of PowerSource."""
    global _power_source
    if _power_source is None:
        _power_source = PowerSource()
    return _power_source
