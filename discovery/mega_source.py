"""
MEGA SOURCE - High-volume, multi-platform company discovery engine.
This is the ultimate scraper that combines 15+ job platforms and directories.
Designed for maximum company discovery and HR email extraction.
"""

import re
import time
import random
import json
import asyncio
from typing import List, Generator, Optional, Set, Dict, Tuple
from urllib.parse import urljoin, quote_plus, urlparse, parse_qs
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

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


class MegaSource(BaseSource):
    """
    Ultimate multi-source company discovery engine.
    Combines 15+ job platforms, search engines, and directories.
    Uses parallel scraping with intelligent rate limiting.
    """
    
    # =========================================================================
    # SOURCE CONFIGURATIONS - All the job platforms we scrape
    # =========================================================================
    
    SOURCES = {
        # Indian Job Portals
        'naukri': {
            'enabled': True,
            'base_url': 'https://www.naukri.com',
            'search_urls': [
                'https://www.naukri.com/{role}-jobs-in-{location}',
                'https://www.naukri.com/jobapi/v3/search?noOfResults=50&urlType=search_by_keyword&searchType=adv&keyword={role}&location={location}&pageNo={page}',
            ],
            'api_url': 'https://www.naukri.com/jobapi/v3/search?noOfResults=50&urlType=search_by_keyword&searchType=adv&keyword={role}&location={location}&pageNo={page}',
            'needs_js': False,  # API works without JS
            'rate_limit': 2.0,
            'max_pages': 20,
        },
        'indeed_india': {
            'enabled': True,
            'base_url': 'https://in.indeed.com',
            'search_urls': [
                'https://in.indeed.com/jobs?q={role}&l={location}&start={offset}',
            ],
            'needs_js': False,
            'rate_limit': 3.0,
            'max_pages': 20,
            'results_per_page': 15,
        },
        'foundit': {  # Monster India rebranded
            'enabled': True,
            'base_url': 'https://www.foundit.in',
            'search_urls': [
                'https://www.foundit.in/srp/results?query={role}&locations={location}&start={offset}',
            ],
            'api_url': 'https://apigw.foundit.in/seeker/search?query={role}&locations={location}&start={offset}&limit=50',
            'needs_js': False,
            'rate_limit': 2.0,
            'max_pages': 20,
        },
        'shine': {
            'enabled': True,
            'base_url': 'https://www.shine.com',
            'search_urls': [
                'https://www.shine.com/job-search/{role}-jobs-in-{location}-{page}',
            ],
            'needs_js': True,
            'rate_limit': 2.0,
            'max_pages': 15,
        },
        'timesjobs': {
            'enabled': True,
            'base_url': 'https://www.timesjobs.com',
            'search_urls': [
                'https://www.timesjobs.com/candidate/job-search.html?searchType=personal498&from=submit&lucession=N&txtKeywords={role}&txtLocation={location}&sequence={page}',
            ],
            'needs_js': False,
            'rate_limit': 2.0,
            'max_pages': 20,
        },
        'hirist': {
            'enabled': True,
            'base_url': 'https://www.hirist.tech',
            'search_urls': [
                'https://www.hirist.tech/j/{role}-jobs-in-{location}-{page}.html',
                'https://www.hirist.tech/jobs/{role}?location={location}&page={page}',
            ],
            'needs_js': False,
            'rate_limit': 2.0,
            'max_pages': 15,
        },
        'cutshort': {
            'enabled': True,
            'base_url': 'https://cutshort.io',
            'search_urls': [
                'https://cutshort.io/jobs/{role}-jobs-{location}',
                'https://cutshort.io/api/jobs/search?role={role}&location={location}&page={page}',
            ],
            'api_url': 'https://cutshort.io/api/jobs/search',
            'needs_js': True,
            'rate_limit': 2.0,
            'max_pages': 10,
        },
        'instahyre': {
            'enabled': True,
            'base_url': 'https://www.instahyre.com',
            'search_urls': [
                'https://www.instahyre.com/search-jobs/?job_type=&location={location}&experience=0&keywords={role}&page={page}',
            ],
            'needs_js': True,
            'rate_limit': 3.0,
            'max_pages': 10,
        },
        'freshersworld': {
            'enabled': True,
            'base_url': 'https://www.freshersworld.com',
            'search_urls': [
                'https://www.freshersworld.com/jobs/jobsearch/{role}-jobs-in-{location}?page={page}',
            ],
            'needs_js': False,
            'rate_limit': 2.0,
            'max_pages': 30,
        },
        'internshala': {
            'enabled': True,
            'base_url': 'https://internshala.com',
            'search_urls': [
                'https://internshala.com/jobs/{role}-jobs-in-{location}/page-{page}',
                'https://internshala.com/fresher-jobs/{role}-fresher-jobs-in-{location}',
            ],
            'needs_js': False,
            'rate_limit': 2.0,
            'max_pages': 15,
        },
        
        # Global Job Platforms
        'linkedin_public': {
            'enabled': True,
            'base_url': 'https://www.linkedin.com',
            'search_urls': [
                'https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={role}&location={location}&start={offset}',
                'https://www.linkedin.com/jobs/search/?keywords={role}&location={location}&start={offset}',
            ],
            'needs_js': False,  # Guest API works without auth
            'rate_limit': 5.0,  # Be careful with LinkedIn
            'max_pages': 10,
            'results_per_page': 25,
        },
        'glassdoor': {
            'enabled': True,
            'base_url': 'https://www.glassdoor.co.in',
            'search_urls': [
                'https://www.glassdoor.co.in/Job/jobs.htm?sc.keyword={role}&locT=C&locKeyword={location}&jobType=',
            ],
            'needs_js': True,
            'rate_limit': 3.0,
            'max_pages': 10,
        },
        'wellfound': {  # AngelList Jobs
            'enabled': True,
            'base_url': 'https://wellfound.com',
            'search_urls': [
                'https://wellfound.com/role/l/{role}/{location}',
                'https://wellfound.com/jobs?location={location}&role={role}',
            ],
            'needs_js': True,
            'rate_limit': 3.0,
            'max_pages': 10,
        },
        
        # Search Engines
        'google_jobs': {
            'enabled': True,
            'base_url': 'https://www.google.com',
            'search_urls': [
                'https://www.google.com/search?q={role}+jobs+{location}+hiring+careers&ibp=htl;jobs&start={offset}',
            ],
            'needs_js': True,
            'rate_limit': 5.0,
            'max_pages': 10,
        },
        'bing': {
            'enabled': True,
            'base_url': 'https://www.bing.com',
            'search_urls': [
                'https://www.bing.com/search?q={role}+jobs+{location}+company+hiring+email&first={offset}',
                'https://www.bing.com/search?q=companies+hiring+{role}+{location}+careers+contact&first={offset}',
            ],
            'needs_js': False,
            'rate_limit': 2.0,
            'max_pages': 10,
            'results_per_page': 10,
        },
        'duckduckgo': {
            'enabled': True,
            'base_url': 'https://html.duckduckgo.com',
            'search_urls': [
                'https://html.duckduckgo.com/html/?q={role}+jobs+{location}+hiring+company',
                'https://html.duckduckgo.com/html/?q=companies+hiring+{role}+{location}+careers+email',
            ],
            'needs_js': False,
            'rate_limit': 2.0,
            'max_pages': 5,
        },
        
        # Startup Directories
        'startupindia': {
            'enabled': True,
            'base_url': 'https://www.startupindia.gov.in',
            'search_urls': [
                'https://www.startupindia.gov.in/content/sih/en/search.html?industries=IT&states={location}',
            ],
            'needs_js': True,
            'rate_limit': 3.0,
            'max_pages': 5,
        },
        'yourstory': {
            'enabled': True,
            'base_url': 'https://yourstory.com',
            'search_urls': [
                'https://yourstory.com/companies?location={location}&industry=technology',
            ],
            'needs_js': True,
            'rate_limit': 3.0,
            'max_pages': 5,
        },
        'tracxn': {
            'enabled': True,
            'base_url': 'https://tracxn.com',
            'search_urls': [
                'https://tracxn.com/explore/Software-Development-Startups-in-{location}',
            ],
            'needs_js': True,
            'rate_limit': 3.0,
            'max_pages': 5,
        },
    }
    
    # Company extraction patterns for different platforms
    EXTRACTION_PATTERNS = {
        'company_name': [
            # Common HTML patterns
            r'data-company="([^"]+)"',
            r'data-company-name="([^"]+)"',
            r'class="[^"]*company[^"]*name[^"]*"[^>]*>([^<]+)<',
            r'class="[^"]*companyName[^"]*"[^>]*>([^<]+)<',
            r'class="[^"]*comp-name[^"]*"[^>]*>([^<]+)<',
            r'class="[^"]*employer[^"]*"[^>]*>([^<]+)<',
            r'<h4[^>]*class="[^"]*company[^"]*"[^>]*>([^<]+)</h4>',
            r'<span[^>]*class="[^"]*company[^"]*"[^>]*>([^<]+)</span>',
            r'<a[^>]*class="[^"]*company[^"]*"[^>]*>([^<]+)</a>',
            r'<div[^>]*class="[^"]*company[^"]*"[^>]*>([^<]+)</div>',
            
            # JSON patterns
            r'"companyName"\s*:\s*"([^"]+)"',
            r'"company_name"\s*:\s*"([^"]+)"',
            r'"employer"\s*:\s*"([^"]+)"',
            r'"employerName"\s*:\s*"([^"]+)"',
            r'"organization"\s*:\s*"([^"]+)"',
            r'"hiringOrganization"\s*:\s*\{[^}]*"name"\s*:\s*"([^"]+)"',
            
            # Specific platforms
            r'data-tn-element="companyName"[^>]*>([^<]+)<',  # Indeed
            r'data-test="employer-short-name"[^>]*>([^<]+)<',  # Glassdoor
            r'data-testid="company-name"[^>]*>([^<]+)<',  # Various
        ],
        'company_website': [
            r'"website"\s*:\s*"(https?://[^"]+)"',
            r'"companyUrl"\s*:\s*"(https?://[^"]+)"',
            r'"company_url"\s*:\s*"(https?://[^"]+)"',
            r'"url"\s*:\s*"(https?://[^"]+)"',
            r'href="(https?://(?:www\.)?[a-zA-Z0-9-]+\.[a-z]{2,}/?)"[^>]*>(?:Visit|Website|Company)',
            r'class="[^"]*website[^"]*"[^>]*href="(https?://[^"]+)"',
        ],
        'linkedin': [
            r'href="(https?://(?:www\.)?linkedin\.com/company/[^"]+)"',
            r'"linkedinUrl"\s*:\s*"(https?://[^"]+)"',
            r'"linkedin"\s*:\s*"(https?://[^"]+)"',
        ],
    }
    
    # Known company websites mapping (for major companies)
    KNOWN_WEBSITES = {
        'tcs': 'https://www.tcs.com',
        'tata consultancy services': 'https://www.tcs.com',
        'infosys': 'https://www.infosys.com',
        'wipro': 'https://www.wipro.com',
        'cognizant': 'https://www.cognizant.com',
        'accenture': 'https://www.accenture.com',
        'hcl': 'https://www.hcltech.com',
        'tech mahindra': 'https://www.techmahindra.com',
        'capgemini': 'https://www.capgemini.com',
        'deloitte': 'https://www.deloitte.com',
        'google': 'https://www.google.com/about/careers/',
        'microsoft': 'https://careers.microsoft.com',
        'amazon': 'https://www.amazon.jobs',
        'meta': 'https://www.metacareers.com',
        'facebook': 'https://www.metacareers.com',
        'apple': 'https://www.apple.com/careers/',
        'netflix': 'https://jobs.netflix.com',
        'uber': 'https://www.uber.com/careers/',
        'airbnb': 'https://careers.airbnb.com',
        'salesforce': 'https://www.salesforce.com/company/careers/',
        'oracle': 'https://www.oracle.com/careers/',
        'ibm': 'https://www.ibm.com/employment/',
        'sap': 'https://www.sap.com/about/careers.html',
        'adobe': 'https://www.adobe.com/careers.html',
        'nvidia': 'https://www.nvidia.com/en-us/about-nvidia/careers/',
        'intel': 'https://www.intel.com/content/www/us/en/jobs/jobs-at-intel.html',
        'cisco': 'https://www.cisco.com/c/en/us/about/careers.html',
        'vmware': 'https://careers.vmware.com',
        'dell': 'https://jobs.dell.com',
        'hp': 'https://jobs.hp.com',
        'servicenow': 'https://www.servicenow.com/careers.html',
        'workday': 'https://www.workday.com/en-us/company/careers.html',
        'splunk': 'https://www.splunk.com/en_us/careers.html',
        'atlassian': 'https://www.atlassian.com/company/careers',
        'zoom': 'https://careers.zoom.us',
        'slack': 'https://slack.com/careers',
        'stripe': 'https://stripe.com/jobs',
        'shopify': 'https://www.shopify.com/careers',
        'paypal': 'https://www.paypal.com/us/webapps/mpp/jobs',
        'paytm': 'https://paytm.com/careers/',
        'razorpay': 'https://razorpay.com/jobs/',
        'flipkart': 'https://www.flipkartcareers.com',
        'swiggy': 'https://careers.swiggy.com',
        'zomato': 'https://www.zomato.com/careers',
        'ola': 'https://www.olacabs.com/careers',
        'byju': 'https://byjus.com/careers/',
        'freshworks': 'https://www.freshworks.com/company/careers/',
        'zoho': 'https://www.zoho.com/careers.html',
        'mphasis': 'https://www.mphasis.com/home/careers.html',
        'mindtree': 'https://www.mindtree.com/careers',
        'l&t infotech': 'https://www.ltimindtree.com/careers/',
        'persistent': 'https://www.persistent.com/careers/',
        'cyient': 'https://www.cyient.com/careers',
        'hexaware': 'https://hexaware.com/careers/',
        'muthoot': 'https://www.muthootfinance.com/careers',
        'hdfc': 'https://www.hdfcbank.com/personal/about-us/careers',
        'icici': 'https://www.icicicareers.com',
        'axis bank': 'https://www.axisbank.com/careers',
        'kotak': 'https://www.kotak.com/en/careers.html',
        'wells fargo': 'https://www.wellsfargojobs.com',
        'jpmorgan': 'https://careers.jpmorgan.com',
        'goldman sachs': 'https://www.goldmansachs.com/careers/',
        'morgan stanley': 'https://www.morganstanley.com/people-opportunities/students-graduates',
        'barclays': 'https://home.barclays/careers/',
        'hsbc': 'https://www.hsbc.com/careers',
        'citi': 'https://jobs.citi.com',
    }

    def __init__(self):
        super().__init__(
            name="mega_source",
            base_url="multi-platform",
            requires_js=False,
        )
        self.logger = get_logger()
        self.fetcher = PageFetcher()
        self._seen_companies: Set[str] = set()
        self._lock = threading.Lock()
        self._results: List[Company] = []
    
    def search(
        self, 
        location: str, 
        roles: List[str], 
        max_results: int = 500
    ) -> Generator[Company, None, None]:
        """
        Search all sources in parallel for maximum company discovery.
        """
        self.logger.info(f"🚀 MegaSource: Searching {len(self.SOURCES)} platforms for {roles} in {location}")
        
        # Process all roles
        for role in roles:
            role_clean = role.lower().replace(' ', '-')
            location_clean = location.lower().replace(' ', '-').replace(',', '')
            
            # Parallel scrape all sources
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {}
                for source_name, source_config in self.SOURCES.items():
                    if not source_config.get('enabled', True):
                        continue
                    
                    future = executor.submit(
                        self._scrape_source,
                        source_name,
                        source_config,
                        role_clean,
                        location_clean,
                        max_results // len(self.SOURCES)
                    )
                    futures[future] = source_name
                
                # Collect results as they complete
                for future in as_completed(futures):
                    source_name = futures[future]
                    try:
                        result = future.result(timeout=120)
                        self.logger.info(f"  ✓ {source_name}: Found {len(result.companies)} companies")
                        
                        for company in result.companies:
                            if len(self._results) >= max_results:
                                break
                            
                            # Deduplicate
                            company_key = self._normalize_company_name(company.name)
                            with self._lock:
                                if company_key not in self._seen_companies:
                                    self._seen_companies.add(company_key)
                                    self._results.append(company)
                                    yield company
                    
                    except Exception as e:
                        self.logger.warning(f"  ✗ {source_name}: {str(e)[:100]}")
        
        self.logger.info(f"📊 MegaSource complete: {len(self._results)} unique companies found")
    
    def _scrape_source(
        self,
        source_name: str,
        config: Dict,
        role: str,
        location: str,
        max_results: int
    ) -> SourceResult:
        """Scrape a single source with pagination."""
        result = SourceResult(source_name=source_name, companies=[], pages_scraped=0)
        
        try:
            max_pages = min(config.get('max_pages', 10), 30)
            rate_limit = config.get('rate_limit', 2.0)
            results_per_page = config.get('results_per_page', 20)
            
            for page in range(1, max_pages + 1):
                if len(result.companies) >= max_results:
                    break
                
                # Build URL with pagination
                offset = (page - 1) * results_per_page
                search_urls = config.get('search_urls', [])
                
                for url_template in search_urls:
                    url = url_template.format(
                        role=quote_plus(role.replace('-', ' ')),
                        location=quote_plus(location.replace('-', ' ')),
                        page=page,
                        offset=offset
                    )
                    
                    try:
                        # Fetch the page
                        resp = self.fetcher.fetch(url, timeout=30)
                        if resp and resp.content:
                            companies = self._extract_companies_from_page(
                                resp.content,
                                location.replace('-', ', ').title(),
                                role.replace('-', ' '),
                                url,
                                source_name
                            )
                            result.companies.extend(companies)
                            result.pages_scraped += 1
                            
                            # Break if no results (end of pagination)
                            if not companies and page > 1:
                                break
                        
                        # Rate limit
                        time.sleep(rate_limit + random.uniform(0.5, 1.5))
                    
                    except Exception as e:
                        result.errors.append(f"Page {page}: {str(e)[:50]}")
                        continue
        
        except Exception as e:
            result.errors.append(str(e))
        
        return result
    
    def _extract_companies_from_page(
        self,
        html: str,
        location: str,
        role: str,
        source_url: str,
        source_name: str
    ) -> List[Company]:
        """Extract companies from a page using multiple patterns."""
        companies = []
        seen_on_page: Set[str] = set()
        
        # Try JSON extraction first (for API responses)
        try:
            json_companies = self._extract_from_json(html, location, role, source_url)
            companies.extend(json_companies)
            for c in json_companies:
                seen_on_page.add(self._normalize_company_name(c.name))
        except:
            pass
        
        # Try HTML patterns
        for pattern in self.EXTRACTION_PATTERNS['company_name']:
            try:
                matches = re.findall(pattern, html, re.IGNORECASE)
                for match in matches:
                    name = self._clean_company_name(match)
                    if not name or len(name) < 2 or len(name) > 100:
                        continue
                    
                    name_key = self._normalize_company_name(name)
                    if name_key in seen_on_page:
                        continue
                    seen_on_page.add(name_key)
                    
                    # Get website if possible
                    website = self._find_company_website(name, html)
                    linkedin = self._find_company_linkedin(name, html)
                    
                    company = Company(
                        name=name,
                        location=location,
                        website=website,
                        linkedin_url=linkedin,
                        source_url=source_url,
                        hiring_roles=[role],
                    )
                    companies.append(company)
            except:
                continue
        
        return companies
    
    def _extract_from_json(
        self,
        content: str,
        location: str,
        role: str,
        source_url: str
    ) -> List[Company]:
        """Extract companies from JSON responses."""
        companies = []
        
        # Try to find JSON in the content
        json_patterns = [
            r'\{[^{}]*"companyName"[^{}]*\}',
            r'\{[^{}]*"company_name"[^{}]*\}',
            r'\{[^{}]*"employer"[^{}]*\}',
            r'"jobs"\s*:\s*\[(.*?)\]',
            r'"results"\s*:\s*\[(.*?)\]',
        ]
        
        for pattern in json_patterns:
            try:
                matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
                for match in matches:
                    try:
                        data = json.loads('{' + match + '}') if not match.startswith('{') else json.loads(match)
                        name = data.get('companyName') or data.get('company_name') or data.get('employer')
                        if name:
                            companies.append(Company(
                                name=self._clean_company_name(name),
                                location=location,
                                website=data.get('website') or data.get('companyUrl'),
                                linkedin_url=data.get('linkedin'),
                                source_url=source_url,
                                hiring_roles=[role],
                            ))
                    except:
                        continue
            except:
                continue
        
        return companies
    
    def _find_company_website(self, company_name: str, html: str) -> Optional[str]:
        """Find company website from HTML or known websites."""
        # Check known websites first
        name_lower = company_name.lower().strip()
        for known_name, website in self.KNOWN_WEBSITES.items():
            if known_name in name_lower or name_lower in known_name:
                return website
        
        # Try to extract from HTML
        for pattern in self.EXTRACTION_PATTERNS['company_website']:
            try:
                # Look near company name
                name_escaped = re.escape(company_name)
                context_pattern = rf'{name_escaped}[^<]*<[^>]*{pattern}'
                matches = re.findall(context_pattern, html, re.IGNORECASE)
                for match in matches:
                    if self._is_valid_company_url(match):
                        return match
            except:
                continue
        
        return None
    
    def _find_company_linkedin(self, company_name: str, html: str) -> Optional[str]:
        """Find company LinkedIn URL from HTML."""
        for pattern in self.EXTRACTION_PATTERNS['linkedin']:
            try:
                matches = re.findall(pattern, html, re.IGNORECASE)
                for match in matches:
                    if 'linkedin.com/company/' in match.lower():
                        return match
            except:
                continue
        return None
    
    def _clean_company_name(self, name: str) -> str:
        """Clean and normalize company name."""
        if not name:
            return ""
        
        # Remove HTML entities
        name = re.sub(r'&[a-z]+;', ' ', name)
        name = re.sub(r'&#\d+;', ' ', name)
        
        # Remove common suffixes/noise
        noise_patterns = [
            r'\s*-\s*.*$',  # Everything after dash
            r'\s*\|.*$',  # Everything after pipe
            r'\s*\(.*\)$',  # Parenthetical
            r'\s+(?:pvt|private|ltd|limited|inc|corp|llc|llp)\.?\s*$',
        ]
        
        for pattern in noise_patterns:
            name = re.sub(pattern, '', name, flags=re.IGNORECASE)
        
        # Clean whitespace
        name = ' '.join(name.split())
        
        return name.strip()
    
    def _normalize_company_name(self, name: str) -> str:
        """Normalize company name for deduplication."""
        if not name:
            return ""
        
        name = name.lower().strip()
        
        # Remove common suffixes
        suffixes = ['pvt', 'private', 'ltd', 'limited', 'inc', 'incorporated',
                    'corp', 'corporation', 'llc', 'llp', 'co', 'company',
                    'technologies', 'technology', 'tech', 'solutions',
                    'services', 'software', 'systems', 'india', 'global']
        
        for suffix in suffixes:
            name = re.sub(rf'\s*{suffix}\.?\s*$', '', name)
            name = re.sub(rf'\s*{suffix}\s+', ' ', name)
        
        # Remove special chars
        name = re.sub(r'[^\w\s]', '', name)
        name = ' '.join(name.split())
        
        return name
    
    def _is_valid_company_url(self, url: str) -> bool:
        """Check if URL is a valid company website."""
        if not url:
            return False
        
        # Exclude job boards and social media
        excluded = [
            'indeed.com', 'linkedin.com', 'glassdoor.com', 'naukri.com',
            'monster.com', 'facebook.com', 'twitter.com', 'instagram.com',
            'youtube.com', 'google.com', 'github.com', 'stackoverflow.com',
        ]
        
        url_lower = url.lower()
        for exc in excluded:
            if exc in url_lower:
                return False
        
        return url.startswith('http')
    
    def get_company_details(self, company: Company) -> Company:
        """Enrich company with additional details."""
        return company


class WebsiteDiscovery:
    """
    Multi-engine website discovery for companies.
    Uses multiple search engines to find real company websites.
    """
    
    SEARCH_ENGINES = [
        {
            'name': 'bing',
            'url': 'https://www.bing.com/search?q={query}',
            'pattern': r'<a[^>]*href="(https?://[^"]+)"[^>]*>',
            'rate_limit': 1.0,
        },
        {
            'name': 'duckduckgo',
            'url': 'https://html.duckduckgo.com/html/?q={query}',
            'pattern': r'href="(https?://[^"]+)"[^>]*class="result__url"',
            'rate_limit': 1.5,
        },
        {
            'name': 'ecosia',
            'url': 'https://www.ecosia.org/search?q={query}',
            'pattern': r'<a[^>]*class="result-url"[^>]*href="(https?://[^"]+)"',
            'rate_limit': 2.0,
        },
    ]
    
    # Job boards and social media to exclude from results
    EXCLUDED_DOMAINS = {
        'linkedin.com', 'indeed.com', 'glassdoor.com', 'naukri.com',
        'monster.com', 'shine.com', 'timesjobs.com', 'facebook.com',
        'twitter.com', 'instagram.com', 'youtube.com', 'pinterest.com',
        'wikipedia.org', 'crunchbase.com', 'zoominfo.com', 'google.com',
        'bing.com', 'yahoo.com', 'github.com', 'stackoverflow.com',
        'ambitionbox.com', 'comparably.com', 'kununu.com', 'owler.com',
    }
    
    def __init__(self):
        self.fetcher = PageFetcher()
        self.logger = get_logger()
    
    def find_website(self, company_name: str) -> Optional[str]:
        """
        Find a company's real website using multiple search engines.
        """
        # Clean company name for search
        search_query = f"{company_name} official website careers"
        
        for engine in self.SEARCH_ENGINES:
            try:
                url = engine['url'].format(query=quote_plus(search_query))
                resp = self.fetcher.fetch(url, timeout=15)
                
                if resp and resp.content:
                    # Extract all URLs from results
                    urls = re.findall(engine['pattern'], resp.content, re.IGNORECASE)
                    
                    for result_url in urls[:10]:  # Check first 10 results
                        if self._is_likely_company_website(result_url, company_name):
                            return result_url
                
                time.sleep(engine['rate_limit'])
            
            except Exception as e:
                continue
        
        return None
    
    def _is_likely_company_website(self, url: str, company_name: str) -> bool:
        """Check if URL is likely the company's real website."""
        if not url or not url.startswith('http'):
            return False
        
        # Parse domain
        try:
            domain = urlparse(url).netloc.lower()
        except:
            return False
        
        # Exclude known non-company domains
        for excluded in self.EXCLUDED_DOMAINS:
            if excluded in domain:
                return False
        
        # Check if domain contains any word from company name
        name_words = set(re.findall(r'\w+', company_name.lower()))
        domain_clean = domain.replace('www.', '').split('.')[0]
        
        # Accept if domain matches company name somewhat
        for word in name_words:
            if len(word) >= 3 and word in domain_clean:
                return True
        
        # Accept .com/.in/.co domains for India
        if any(domain.endswith(ext) for ext in ['.com', '.in', '.co.in', '.io', '.tech', '.co']):
            # More relaxed matching for first result
            return True
        
        return False


# Register the mega source globally
_mega_source_instance = None

def get_mega_source() -> MegaSource:
    """Get singleton instance of MegaSource."""
    global _mega_source_instance
    if _mega_source_instance is None:
        _mega_source_instance = MegaSource()
    return _mega_source_instance
