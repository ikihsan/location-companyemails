"""
Dynamic job portal scrapers - scrapes real job boards for companies.
No static data - everything is discovered in real-time.
"""

import re
import time
import random
import json
from typing import List, Generator, Optional, Set, Dict
from urllib.parse import urljoin, quote_plus, urlparse
from dataclasses import dataclass

from models import Company
from fetcher import PageFetcher
from utils import get_logger
from .base_source import BaseSource


@dataclass
class JobListing:
    """Represents a job listing from a portal."""
    company_name: str
    job_title: str
    location: str
    company_url: Optional[str] = None
    job_url: Optional[str] = None


class MultiJobPortalSource(BaseSource):
    """
    Scrapes multiple job portals simultaneously for company discovery.
    Supports: Indeed, Glassdoor, SimplyHired, ZipRecruiter, and more.
    """
    
    # Job portal configurations
    PORTALS = {
        'indeed': {
            'search_url': 'https://www.indeed.com/jobs?q={query}&l={location}&start={offset}',
            'india_url': 'https://www.indeed.co.in/jobs?q={query}&l={location}&start={offset}',
            'company_patterns': [
                r'data-testid="company-name"[^>]*>([^<]+)<',
                r'"companyName"\s*:\s*"([^"]+)"',
                r'class="[^"]*companyName[^"]*"[^>]*>([^<]+)<',
                r'<span[^>]*class="[^"]*company[^"]*"[^>]*>([^<]+)</span>',
                r'data-tn-element="companyName"[^>]*>([^<]+)<',
            ],
            'job_patterns': [
                r'<h2[^>]*class="[^"]*jobTitle[^"]*"[^>]*>.*?<span[^>]*>([^<]+)</span>',
                r'"title"\s*:\s*"([^"]+)"',
            ],
            'link_patterns': [
                r'href="(/company/[^"]+)"',
                r'"companyOverviewLink"\s*:\s*"([^"]+)"',
            ],
            'results_per_page': 15,
        },
        'glassdoor': {
            'search_url': 'https://www.glassdoor.com/Job/jobs.htm?sc.keyword={query}&locT=C&locKeyword={location}',
            'company_patterns': [
                r'data-test="employer-short-name"[^>]*>([^<]+)<',
                r'"employerName"\s*:\s*"([^"]+)"',
                r'class="[^"]*employer-name[^"]*"[^>]*>([^<]+)<',
            ],
            'job_patterns': [
                r'data-test="job-title"[^>]*>([^<]+)<',
                r'"jobTitle"\s*:\s*"([^"]+)"',
            ],
            'results_per_page': 30,
        },
        'simplyhired': {
            'search_url': 'https://www.simplyhired.com/search?q={query}&l={location}&pn={page}',
            'company_patterns': [
                r'data-testid="companyName"[^>]*>([^<]+)<',
                r'class="[^"]*company[^"]*"[^>]*>([^<]+)<',
                r'<span[^>]*class="[^"]*jobposting-company[^"]*"[^>]*>([^<]+)</span>',
            ],
            'results_per_page': 20,
        },
        'linkedin_jobs': {
            'search_url': 'https://www.linkedin.com/jobs/search/?keywords={query}&location={location}&start={offset}',
            'company_patterns': [
                r'<h4[^>]*class="[^"]*company[^"]*"[^>]*>([^<]+)</h4>',
                r'"companyName"\s*:\s*"([^"]+)"',
                r'data-tracking-control-name="[^"]*company[^"]*"[^>]*>([^<]+)<',
            ],
            'results_per_page': 25,
        },
        'naukri': {
            'search_url': 'https://www.naukri.com/{query}-jobs-in-{location}?pg={page}',
            'company_patterns': [
                r'class="[^"]*comp-name[^"]*"[^>]*>([^<]+)<',
                r'"companyName"\s*:\s*"([^"]+)"',
                r'<a[^>]*class="[^"]*subTitle[^"]*"[^>]*>([^<]+)</a>',
            ],
            'results_per_page': 20,
        },
        'monster': {
            'search_url': 'https://www.monster.com/jobs/search/?q={query}&where={location}&page={page}',
            'company_patterns': [
                r'<span[^>]*class="[^"]*company[^"]*"[^>]*>([^<]+)</span>',
                r'"companyName"\s*:\s*"([^"]+)"',
                r'data-testid="company"[^>]*>([^<]+)<',
            ],
            'results_per_page': 25,
        },
        'ziprecruiter': {
            'search_url': 'https://www.ziprecruiter.com/candidate/search?search={query}&location={location}&page={page}',
            'company_patterns': [
                r'<p[^>]*class="[^"]*company[^"]*"[^>]*>([^<]+)</p>',
                r'"hiringOrganization"\s*:\s*\{[^}]*"name"\s*:\s*"([^"]+)"',
            ],
            'results_per_page': 20,
        },
        'careerbuilder': {
            'search_url': 'https://www.careerbuilder.com/jobs?keywords={query}&location={location}&page_number={page}',
            'company_patterns': [
                r'data-cb-employer="([^"]+)"',
                r'class="[^"]*employer[^"]*"[^>]*>([^<]+)<',
            ],
            'results_per_page': 25,
        },
    }
    
    # India-specific portals
    INDIA_PORTALS = {
        'indeed_india': {
            'search_url': 'https://www.indeed.co.in/jobs?q={query}&l={location}&start={offset}',
            'company_patterns': [
                r'data-testid="company-name"[^>]*>([^<]+)<',
                r'"companyName"\s*:\s*"([^"]+)"',
                r'<span[^>]*data-testid="company-name"[^>]*>([^<]+)</span>',
                r'class="[^"]*companyName[^"]*"[^>]*>([^<]+)<',
            ],
            'results_per_page': 10,
        },
        'naukri': {
            'search_url': 'https://www.naukri.com/{query}-jobs-in-{location}',
            'company_patterns': [
                r'"companyName"\s*:\s*"([^"]+)"',
                r'class="[^"]*comp-name[^"]*"[^>]*>([^<]+)<',
                r'<a[^>]*class="[^"]*subTitle[^"]*"[^>]*title="([^"]+)"',
                r'class="[^"]*companyInfo[^"]*"[^>]*>.*?<a[^>]*>([^<]+)</a>',
            ],
            'results_per_page': 20,
        },
        'shine': {
            'search_url': 'https://www.shine.com/job-search/{query}-jobs-in-{location}',
            'company_patterns': [
                r'class="[^"]*company_name[^"]*"[^>]*>([^<]+)<',
                r'"hiringOrganization"[^}]*"name"\s*:\s*"([^"]+)"',
            ],
            'results_per_page': 20,
        },
        'timesjobs': {
            'search_url': 'https://www.timesjobs.com/candidate/job-search.html?searchType=personalizedSearch&from=submit&txtKeywords={query}&txtLocation={location}',
            'company_patterns': [
                r'<h3[^>]*class="[^"]*joblist-comp-name[^"]*"[^>]*>([^<]+)</h3>',
                r'"hiringOrganization"[^}]*"name"\s*:\s*"([^"]+)"',
                r'class="[^"]*comp-name[^"]*"[^>]*>([^<]+)<',
            ],
            'results_per_page': 25,
        },
        'freshersworld': {
            'search_url': 'https://www.freshersworld.com/jobs/jobsearch/{query}-jobs-in-{location}',
            'company_patterns': [
                r'class="[^"]*company-name[^"]*"[^>]*>([^<]+)<',
                r'"hiringOrganization"[^}]*"name"\s*:\s*"([^"]+)"',
            ],
            'results_per_page': 20,
        },
    }
    
    def __init__(self):
        super().__init__(
            name="job_portals",
            base_url="https://www.indeed.com",
            requires_js=False,
        )
        self.logger = get_logger()
        self.fetcher = PageFetcher()
        self.seen_companies: Set[str] = set()
    
    def search(
        self,
        location: str,
        roles: List[str],
        max_results: int = 100,
    ) -> Generator[Company, None, None]:
        """Search multiple job portals for companies."""
        
        self.seen_companies.clear()
        count = 0
        
        # Determine which portals to use based on location
        is_india = self._is_indian_location(location)
        portals = self.INDIA_PORTALS if is_india else self.PORTALS
        
        # Also add global portals for Indian locations
        if is_india:
            portals = {**portals, **{'indeed': self.PORTALS['indeed']}}
        
        for role in roles:
            if count >= max_results:
                break
            
            # Scrape each portal
            for portal_name, portal_config in portals.items():
                if count >= max_results:
                    break
                
                self.logger.info(f"Scraping {portal_name} for '{role}' in {location}...")
                
                try:
                    for company in self._scrape_portal(portal_name, portal_config, role, location, max_results - count):
                        if company.name.lower() not in self.seen_companies:
                            self.seen_companies.add(company.name.lower())
                            count += 1
                            yield company
                            
                            if count >= max_results:
                                break
                except Exception as e:
                    self.logger.warning(f"Error scraping {portal_name}: {e}")
                    continue
    
    def _is_indian_location(self, location: str) -> bool:
        """Check if location is in India."""
        indian_keywords = [
            'india', 'kerala', 'bangalore', 'bengaluru', 'mumbai', 'delhi',
            'hyderabad', 'chennai', 'pune', 'kolkata', 'kochi', 'trivandrum',
            'ahmedabad', 'jaipur', 'lucknow', 'noida', 'gurgaon', 'gurugram',
            'chandigarh', 'indore', 'bhopal', 'nagpur', 'coimbatore', 'mysore',
        ]
        return any(kw in location.lower() for kw in indian_keywords)
    
    def _scrape_portal(
        self,
        portal_name: str,
        config: Dict,
        role: str,
        location: str,
        max_results: int
    ) -> Generator[Company, None, None]:
        """Scrape a single job portal with timeout protection."""
        
        count = 0
        max_pages = min(5, (max_results // 15) + 1)  # Limit pages to avoid rate limiting
        
        for page in range(max_pages):
            if count >= max_results:
                break
            
            # Build URL
            url = self._build_portal_url(config, role, location, page)
            if not url:
                self.logger.debug(f"Could not build URL for {portal_name}")
                break
            
            self.logger.debug(f"Fetching {portal_name} page {page}: {url[:80]}...")
            
            # Add delay between requests
            if page > 0:
                time.sleep(random.uniform(1.0, 2.0))
            
            # Fetch page with timeout
            try:
                result = self.fetcher.fetch(url)
                if not result.success:
                    self.logger.debug(f"Failed to fetch {portal_name} page {page}: {result.error}")
                    break  # Move to next portal instead of continuing
                
                if not result.html_content or len(result.html_content) < 500:
                    self.logger.debug(f"Empty or small response from {portal_name}")
                    break
            except Exception as e:
                self.logger.debug(f"Exception fetching {portal_name}: {e}")
                break
            
            # Extract companies
            companies = self._extract_companies_from_html(
                result.html_content,
                config.get('company_patterns', []),
                config.get('link_patterns', []),
                role,
                location,
                url
            )
            
            self.logger.debug(f"Found {len(companies)} companies on {portal_name} page {page}")
            
            if not companies:
                # No more results, try next portal
                break
            
            for company in companies:
                count += 1
                yield company
                
                if count >= max_results:
                    break
    
    def _build_portal_url(self, config: Dict, role: str, location: str, page: int) -> Optional[str]:
        """Build the search URL for a portal."""
        
        # Try different URL formats
        url_template = config.get('search_url') or config.get('india_url')
        if not url_template:
            return None
        
        # Clean and encode parameters - handle Naukri's hyphenated format
        query = role.lower().replace(' ', '-')
        query_encoded = quote_plus(role)
        loc = location.lower().replace(' ', '-')
        loc_encoded = quote_plus(location)
        
        # Handle different pagination styles
        offset = page * config.get('results_per_page', 20)
        
        try:
            # Try with hyphenated format first (for Naukri-style URLs)
            url = url_template.format(
                query=query,
                location=loc,
                page=page + 1,
                offset=offset,
            )
            return url
        except KeyError:
            try:
                # Try with encoded format
                return url_template.format(
                    query=query_encoded,
                    location=loc_encoded,
                    page=page + 1,
                    offset=offset,
                )
            except KeyError:
                # Minimal format
                try:
                    return url_template.format(query=query, location=loc)
                except:
                    return None
    
    def _extract_companies_from_html(
        self,
        content: str,
        company_patterns: List[str],
        link_patterns: List[str],
        role: str,
        location: str,
        source_url: str
    ) -> List[Company]:
        """Extract company information from HTML content."""
        
        companies = []
        seen_in_page = set()
        
        # First, try to extract from JSON-LD structured data
        json_ld_companies = self._extract_from_json_ld(content, role, location, source_url)
        for company in json_ld_companies:
            if company.name.lower() not in seen_in_page:
                seen_in_page.add(company.name.lower())
                companies.append(company)
        
        # Try to extract from inline JSON (many SPA sites embed data)
        json_companies = self._extract_from_inline_json(content, role, location, source_url)
        for company in json_companies:
            if company.name.lower() not in seen_in_page:
                seen_in_page.add(company.name.lower())
                companies.append(company)
        
        # Extract company names using patterns
        for pattern in company_patterns:
            try:
                matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    name = match.strip() if isinstance(match, str) else match[0].strip()
                    name = self._clean_company_name(name)
                    
                    if name and self._is_valid_company_name(name) and name.lower() not in seen_in_page:
                        seen_in_page.add(name.lower())
                        
                        # Try to find company website
                        website = self._find_company_website(name, content, link_patterns)
                        
                        companies.append(Company(
                            name=name,
                            location=location,
                            source_url=source_url,
                            website=website,
                            hiring_roles=[role],
                        ))
            except Exception as e:
                self.logger.debug(f"Error with pattern {pattern}: {e}")
                continue
        
        return companies
    
    def _extract_from_json_ld(self, content: str, role: str, location: str, source_url: str) -> List[Company]:
        """Extract companies from JSON-LD structured data."""
        companies = []
        
        # Find all JSON-LD blocks
        json_ld_pattern = r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>'
        matches = re.findall(json_ld_pattern, content, re.IGNORECASE | re.DOTALL)
        
        for json_str in matches:
            try:
                data = json.loads(json_str)
                
                # Handle single object or array
                items = data if isinstance(data, list) else [data]
                
                for item in items:
                    # Look for JobPosting schema
                    if item.get('@type') == 'JobPosting':
                        org = item.get('hiringOrganization', {})
                        name = org.get('name', '')
                        if name and self._is_valid_company_name(name):
                            website = org.get('url', org.get('sameAs', ''))
                            companies.append(Company(
                                name=name,
                                location=location,
                                source_url=source_url,
                                website=website if website else None,
                                hiring_roles=[role],
                            ))
                    
                    # Check for ItemList with JobPosting items
                    if item.get('@type') == 'ItemList':
                        for list_item in item.get('itemListElement', []):
                            if list_item.get('@type') == 'JobPosting':
                                org = list_item.get('hiringOrganization', {})
                                name = org.get('name', '')
                                if name and self._is_valid_company_name(name):
                                    companies.append(Company(
                                        name=name,
                                        location=location,
                                        source_url=source_url,
                                        hiring_roles=[role],
                                    ))
            except (json.JSONDecodeError, TypeError, KeyError):
                continue
        
        return companies
    
    def _extract_from_inline_json(self, content: str, role: str, location: str, source_url: str) -> List[Company]:
        """Extract companies from inline JSON data embedded in page."""
        companies = []
        seen = set()
        
        # Look for common patterns of embedded JSON data
        patterns = [
            # Naukri style
            r'"companyName"\s*:\s*"([^"]+)"',
            # Indeed style  
            r'"company"\s*:\s*"([^"]+)"',
            r'"employerName"\s*:\s*"([^"]+)"',
            # LinkedIn style
            r'"companyName"\s*:\s*\{[^}]*"text"\s*:\s*"([^"]+)"',
            # Generic
            r'"name"\s*:\s*"([^"]+)"[^}]*"@type"\s*:\s*"Organization"',
            r'"@type"\s*:\s*"Organization"[^}]*"name"\s*:\s*"([^"]+)"',
        ]
        
        for pattern in patterns:
            try:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    name = match.strip()
                    name = self._clean_company_name(name)
                    if name and self._is_valid_company_name(name) and name.lower() not in seen:
                        seen.add(name.lower())
                        companies.append(Company(
                            name=name,
                            location=location,
                            source_url=source_url,
                            hiring_roles=[role],
                        ))
            except Exception:
                continue
        
        return companies
    
    def _clean_company_name(self, name: str) -> str:
        """Clean up extracted company name."""
        if not name:
            return ""
        
        # Remove HTML entities
        name = re.sub(r'&[a-zA-Z]+;', '', name)
        name = re.sub(r'&#\d+;', '', name)
        
        # Remove extra whitespace
        name = re.sub(r'\s+', ' ', name).strip()
        
        # Remove common suffixes that aren't part of the name
        suffixes_to_remove = [
            ' - Remote', ' (Remote)', ' | Remote',
            ' - Hiring', ' is hiring', ' hiring',
        ]
        for suffix in suffixes_to_remove:
            if name.lower().endswith(suffix.lower()):
                name = name[:-len(suffix)].strip()
        
        return name
    
    def _is_valid_company_name(self, name: str) -> bool:
        """Check if a string looks like a valid company name."""
        if not name or len(name) < 2 or len(name) > 100:
            return False
        
        # Filter out common false positives
        invalid_patterns = [
            r'^(javascript|python|java|react|angular|node|vue|php|ruby|golang|rust)$',
            r'^(remote|full.?time|part.?time|contract|freelance|hybrid|onsite)$',
            r'^(posted|days?\s+ago|just\s+posted|today|yesterday)$',
            r'^(apply|save|share|report|hide)$',
            r'^(salary|location|job\s+type|experience|skills?)$',
            r'^(description|requirements|qualifications|benefits)$',
            r'^(senior|junior|lead|principal|staff|intern)$',
            r'^\d+$',  # Just numbers
            r'^[^a-zA-Z]+$',  # No letters
            r'^.{1,2}$',  # Too short
        ]
        
        name_lower = name.lower()
        for pattern in invalid_patterns:
            if re.match(pattern, name_lower, re.IGNORECASE):
                return False
        
        return True
    
    def _find_company_website(self, company_name: str, content: str, link_patterns: List[str]) -> Optional[str]:
        """Try to find company website from the page content."""
        
        # Look for company links in content
        for pattern in link_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if company_name.lower().split()[0] in match.lower():
                    return match
        
        # DO NOT construct fake URLs - they waste time and never work
        # If we couldn't find a real URL from the page, return None
        # The pipeline will use search engines to find real company websites later
        return None
    
    def get_company_details(self, company: Company) -> Company:
        """Enrich company with additional details."""
        return company


class SearchEngineSource(BaseSource):
    """
    Uses multiple search engines to find companies hiring.
    Supports: DuckDuckGo, Bing, Mojeek (most reliable without rate limiting)
    """
    
    SEARCH_ENGINES = {
        'duckduckgo': {
            'url': 'https://html.duckduckgo.com/html/?q={query}',
            'result_pattern': r'<a[^>]*class="[^"]*result__a[^"]*"[^>]*href="([^"]+)"[^>]*>([^<]+)</a>',
            'snippet_pattern': r'<a[^>]*class="[^"]*result__snippet[^"]*"[^>]*>([^<]+)</a>',
        },
        'bing': {
            'url': 'https://www.bing.com/search?q={query}&first={offset}',
            'result_pattern': r'<a[^>]*href="(https?://[^"]+)"[^>]*><h2>([^<]+)</h2></a>',
        },
        'mojeek': {
            'url': 'https://www.mojeek.com/search?q={query}&s={offset}',
            'result_pattern': r'<a[^>]*class="[^"]*ob[^"]*"[^>]*href="([^"]+)"[^>]*>([^<]+)</a>',
        },
    }
    
    # Search query templates for finding companies
    QUERY_TEMPLATES = [
        '"{role}" jobs in {location} hiring',
        '{role} careers {location} company',
        'software companies hiring {role} {location}',
        'tech companies {location} {role} jobs',
        'IT companies in {location} hiring {role}',
        '{role} openings {location} apply',
        'startups hiring {role} {location}',
        '{location} {role} job openings 2024',
        'web development companies {location}',
        'software development companies {location}',
        # More specific queries
        'IT companies {location} contact email',
        'software firms {location} careers page',
        '{location} based tech startups hiring',
        'best software companies in {location}',
        'top IT companies {location} list',
        '{role} jobs {location} company website',
        'technology companies in {location} India',
        '{location} software park companies',
        'technopark {location} companies hiring',
        'infopark {location} IT companies',
    ]
    
    def __init__(self):
        super().__init__(
            name="search_engines",
            base_url="https://duckduckgo.com",
            requires_js=False,
        )
        self.logger = get_logger()
        self.fetcher = PageFetcher()
        self.seen_companies: Set[str] = set()
    
    def search(
        self,
        location: str,
        roles: List[str],
        max_results: int = 100,
    ) -> Generator[Company, None, None]:
        """Search multiple engines for companies hiring."""
        
        self.seen_companies.clear()
        count = 0
        
        for role in roles:
            if count >= max_results:
                break
            
            # Generate various search queries
            queries = self._generate_queries(role, location)
            
            for query in queries:
                if count >= max_results:
                    break
                
                # Try each search engine
                for engine_name, engine_config in self.SEARCH_ENGINES.items():
                    if count >= max_results:
                        break
                    
                    try:
                        for company in self._search_engine(engine_name, engine_config, query, role, location):
                            if company.name.lower() not in self.seen_companies:
                                self.seen_companies.add(company.name.lower())
                                count += 1
                                yield company
                                
                                if count >= max_results:
                                    break
                    except Exception as e:
                        self.logger.debug(f"Error with {engine_name}: {e}")
                        continue
                    
                    # Rate limiting between engines
                    time.sleep(random.uniform(1.0, 2.0))
    
    def _generate_queries(self, role: str, location: str) -> List[str]:
        """Generate search queries for finding companies."""
        queries = []
        for template in self.QUERY_TEMPLATES[:10]:  # Use first 10 templates
            query = template.format(role=role, location=location)
            queries.append(query)
        return queries
    
    def _search_engine(
        self,
        engine_name: str,
        config: Dict,
        query: str,
        role: str,
        location: str
    ) -> Generator[Company, None, None]:
        """Search a single engine and extract companies."""
        
        url = config['url'].format(
            query=quote_plus(query),
            page=1,
            offset=0
        )
        
        result = self.fetcher.fetch(url)
        if not result.success or not result.html_content:
            return
        
        html_content = result.html_content
        
        # First try to extract from search result titles (often contain company names)
        title_companies = self._extract_from_search_titles(html_content, role, location)
        for company in title_companies:
            yield company
        
        # Extract URLs from search results
        pattern = config.get('result_pattern', r'href="(https?://[^"]+)"')
        matches = re.findall(pattern, html_content, re.IGNORECASE)
        
        # Also look for generic href links to company sites
        generic_pattern = r'href="(https?://(?:www\.)?[a-zA-Z0-9-]+\.(?:com|in|io|co|org|net)/[^"]*(?:about|careers?|jobs?|hiring)[^"]*)"'
        generic_matches = re.findall(generic_pattern, html_content, re.IGNORECASE)
        
        all_urls = set()
        for match in matches[:30]:
            url_str = match[0] if isinstance(match, tuple) else match
            all_urls.add(url_str)
        for url_str in generic_matches[:20]:
            all_urls.add(url_str)
        
        for url_str in all_urls:
            company = self._extract_company_from_url(url_str, role, location)
            if company:
                yield company
    
    def _extract_from_search_titles(self, content: str, role: str, location: str) -> List[Company]:
        """Extract company names from search result titles."""
        companies = []
        seen = set()
        
        # Patterns for extracting titles that mention hiring/jobs
        patterns = [
            # "Company Name is hiring" or "Company Name jobs"
            r'>([A-Z][a-zA-Z0-9\s&\.]+?)\s+(?:is\s+hiring|jobs?|careers?|openings?)<',
            # "Jobs at Company Name"
            r'>Jobs?\s+(?:at|@)\s+([A-Z][a-zA-Z0-9\s&\.]+?)(?:\s*[-|]\s*|\s*<)',
            # "Company Name - Jobs" or "Company Name | Careers"
            r'>([A-Z][a-zA-Z0-9\s&\.]+?)\s*[-|]\s*(?:Jobs?|Careers?|Hiring)',
            # DuckDuckGo result titles
            r'class="[^"]*result__a[^"]*"[^>]*>([A-Z][a-zA-Z0-9\s&\.]+?)\s*[-|:]',
        ]
        
        for pattern in patterns:
            try:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    name = match.strip()
                    name = re.sub(r'\s+', ' ', name)
                    
                    # Skip if too short or too long
                    if len(name) < 3 or len(name) > 50:
                        continue
                    
                    # Skip generic terms
                    skip_terms = ['jobs', 'careers', 'hiring', 'apply', 'indeed', 'glassdoor', 
                                  'linkedin', 'naukri', 'best', 'top', 'latest', 'new']
                    if any(term in name.lower() for term in skip_terms):
                        continue
                    
                    if name.lower() not in seen:
                        seen.add(name.lower())
                        companies.append(Company(
                            name=name,
                            location=location,
                            source_url="search_engine",
                            hiring_roles=[role],
                        ))
            except Exception:
                continue
        
        return companies
    
    def _extract_company_from_url(self, url: str, role: str, location: str) -> Optional[Company]:
        """Extract company information from a URL."""
        
        # Skip common non-company domains
        skip_domains = [
            'google.com', 'bing.com', 'duckduckgo.com', 'facebook.com',
            'twitter.com', 'linkedin.com', 'youtube.com', 'wikipedia.org',
            'indeed.com', 'glassdoor.com', 'naukri.com', 'monster.com',
            'reddit.com', 'quora.com', 'medium.com', 'github.com',
            'instagram.com', 'pinterest.com', 'tumblr.com', 'blogspot.com',
            'wordpress.com', 'amazon.com', 'flipkart.com', 'apple.com',
            'microsoft.com', 'gov.in', 'nic.in', 'edu', 'ac.in',
            'timesofindia.', 'thehindu.', 'ndtv.', 'moneycontrol.',
            'shine.com', 'timesjobs.com', 'freshersworld.com', 'simplyhired.com',
        ]
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Skip if it's a job board, social media, or news site
            if any(skip in domain for skip in skip_domains):
                return None
            
            # Must be a real domain with proper TLD
            if '.' not in domain:
                return None
            
            # Extract company name from domain
            domain_clean = domain.replace('www.', '')
            parts = domain_clean.split('.')
            
            if len(parts) < 2:
                return None
            
            # Get the main part of the domain
            name = parts[0]
            
            # Clean up the name
            name = name.replace('-', ' ').replace('_', ' ')
            name = re.sub(r'\d+', '', name)  # Remove numbers
            name = name.strip()
            
            # Title case and validate
            if len(name) < 2:
                return None
            
            name = name.title()
            
            # Skip if it's just common words
            skip_words = ['www', 'web', 'site', 'online', 'app', 'blog', 'news', 'info']
            if name.lower() in skip_words:
                return None
            
            return Company(
                name=name,
                location=location,
                source_url=url,
                website=f"https://{domain_clean}",
                hiring_roles=[role],
            )
        except Exception:
            return None
    
    def get_company_details(self, company: Company) -> Company:
        """Enrich company with additional details."""
        return company


class StartupListSource(BaseSource):
    """
    Scrapes startup directories and lists for companies.
    Sources: AngelList, Crunchbase, StartupList, ProductHunt, etc.
    """
    
    DIRECTORIES = {
        'ycombinator': {
            'url': 'https://www.ycombinator.com/companies?batch=&industry=&isHiring=true&demographic=&query={location}',
            'company_pattern': r'"name"\s*:\s*"([^"]+)"',
            'website_pattern': r'"website"\s*:\s*"([^"]+)"',
        },
        'angellist': {
            'url': 'https://angel.co/location/{location}',
            'company_pattern': r'data-type="company"[^>]*>([^<]+)<',
        },
        'wellfound': {
            'url': 'https://wellfound.com/location/{location}',
            'company_pattern': r'"name"\s*:\s*"([^"]+)"[^}]*"__typename"\s*:\s*"StartupResult"',
        },
        'f6s': {
            'url': 'https://www.f6s.com/companies/{location}/co',
            'company_pattern': r'<h3[^>]*class="[^"]*company[^"]*"[^>]*>([^<]+)</h3>',
        },
    }
    
    def __init__(self):
        super().__init__(
            name="startup_directories",
            base_url="https://www.ycombinator.com",
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
        """Search startup directories for companies."""
        
        count = 0
        seen = set()
        
        for dir_name, config in self.DIRECTORIES.items():
            if count >= max_results:
                break
            
            try:
                url = config['url'].format(location=quote_plus(location))
                result = self.fetcher.fetch(url)
                
                if not result.success:
                    continue
                
                # Extract companies
                pattern = config.get('company_pattern', r'"name"\s*:\s*"([^"]+)"')
                matches = re.findall(pattern, result.html_content or '', re.IGNORECASE)
                
                for match in matches:
                    name = match.strip()
                    if name and name.lower() not in seen and len(name) > 2:
                        seen.add(name.lower())
                        
                        company = Company(
                            name=name,
                            location=location,
                            source_url=url,
                            hiring_roles=roles.copy(),
                        )
                        
                        count += 1
                        yield company
                        
                        if count >= max_results:
                            break
                            
            except Exception as e:
                self.logger.debug(f"Error with {dir_name}: {e}")
                continue
            
            time.sleep(random.uniform(1.0, 2.0))
    
    def get_company_details(self, company: Company) -> Company:
        return company


class ITParksSource(BaseSource):
    """
    Searches IT park directories and tech hub company lists.
    Targets specific tech parks in India like Technopark, Infopark, etc.
    """
    
    IT_PARKS = {
        'technopark_trivandrum': {
            'search_url': 'https://www.technopark.org/companies',
            'alt_urls': [
                'https://duckduckgo.com/html/?q=technopark+trivandrum+companies+list',
                'https://www.bing.com/search?q=technopark+trivandrum+IT+companies',
            ],
        },
        'infopark_kochi': {
            'search_url': 'https://www.infopark.in/companies',
            'alt_urls': [
                'https://duckduckgo.com/html/?q=infopark+kochi+companies+list',
                'https://www.bing.com/search?q=infopark+kochi+IT+companies',
            ],
        },
        'cyberpark_kozhikode': {
            'alt_urls': [
                'https://duckduckgo.com/html/?q=cyberpark+kozhikode+companies',
                'https://www.bing.com/search?q=cyberpark+calicut+IT+companies',
            ],
        },
    }
    
    # More search query templates specific to finding company directories
    DIRECTORY_QUERIES = [
        'IT companies in {location} list with contact',
        'software companies {location} directory',
        'tech startups {location} website email',
        'IT park companies {location}',
        '{location} IT companies address contact',
        'top 50 software companies in {location}',
        '{location} based IT companies hiring',
        'software services companies in {location} India',
    ]
    
    def __init__(self):
        super().__init__(
            name="it_parks",
            base_url="https://www.technopark.org",
            requires_js=False,
        )
        self.logger = get_logger()
        self.fetcher = PageFetcher()
        self.seen_companies: Set[str] = set()
    
    def search(
        self,
        location: str,
        roles: List[str],
        max_results: int = 100,
    ) -> Generator[Company, None, None]:
        """Search IT park directories for companies."""
        
        self.seen_companies.clear()
        count = 0
        
        # Search using directory queries
        for query_template in self.DIRECTORY_QUERIES:
            if count >= max_results:
                break
            
            query = query_template.format(location=location)
            
            # Use DuckDuckGo and Bing for searches
            urls = [
                f'https://html.duckduckgo.com/html/?q={quote_plus(query)}',
                f'https://www.bing.com/search?q={quote_plus(query)}',
            ]
            
            for url in urls:
                if count >= max_results:
                    break
                
                try:
                    result = self.fetcher.fetch(url)
                    if not result.success or not result.html_content:
                        continue
                    
                    # Extract company names and URLs from search results
                    companies = self._extract_from_search_results(
                        result.html_content, roles, location, url
                    )
                    
                    for company in companies:
                        if company.name.lower() not in self.seen_companies:
                            self.seen_companies.add(company.name.lower())
                            count += 1
                            yield company
                            
                            if count >= max_results:
                                break
                except Exception as e:
                    self.logger.debug(f"Error searching directory: {e}")
                    continue
                
                time.sleep(random.uniform(0.5, 1.5))
    
    def _extract_from_search_results(
        self, content: str, roles: List[str], location: str, source_url: str
    ) -> List[Company]:
        """Extract company information from search results."""
        companies = []
        
        # Extract URLs that look like company websites
        url_patterns = [
            r'href="(https?://(?:www\.)?[a-zA-Z0-9-]+\.(?:com|in|io|co\.in|net|org)/[^"]*)"',
            r'href="(https?://[a-zA-Z0-9-]+\.[a-zA-Z]{2,})"',
        ]
        
        seen_domains = set()
        for pattern in url_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for url in matches:
                try:
                    parsed = urlparse(url)
                    domain = parsed.netloc.lower().replace('www.', '')
                    
                    if domain in seen_domains:
                        continue
                    
                    # Skip non-company domains
                    skip = ['google', 'bing', 'duckduckgo', 'facebook', 'twitter',
                            'linkedin', 'youtube', 'wikipedia', 'indeed', 'glassdoor',
                            'naukri', 'monster', 'reddit', 'quora', 'medium', 'github']
                    if any(s in domain for s in skip):
                        continue
                    
                    seen_domains.add(domain)
                    
                    # Extract company name from domain
                    name_part = domain.split('.')[0]
                    name = name_part.replace('-', ' ').replace('_', ' ').title()
                    
                    if len(name) >= 3:
                        companies.append(Company(
                            name=name,
                            location=location,
                            source_url=source_url,
                            website=f"https://{domain}",
                            hiring_roles=roles.copy(),
                        ))
                except Exception:
                    continue
        
        # Also extract company names from text patterns
        name_patterns = [
            r'([A-Z][a-zA-Z0-9]+\s+(?:Technologies?|Software|Solutions?|IT\s+Services?|Infotech|Tech|Systems?))\b',
            r'([A-Z][a-zA-Z0-9]+\s+(?:Pvt\.?\s*Ltd\.?|Private\s+Limited|LLP))',
            r'([A-Z][a-zA-Z0-9]+(?:soft|tech|sys|info|data))\b',
        ]
        
        for pattern in name_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for name in matches:
                name = name.strip()
                if len(name) >= 4 and len(name) <= 60:
                    companies.append(Company(
                        name=name,
                        location=location,
                        source_url=source_url,
                        hiring_roles=roles.copy(),
                    ))
        
        return companies
    
    def get_company_details(self, company: Company) -> Company:
        return company
