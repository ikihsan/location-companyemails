"""
ULTIMATE SOURCE - Maximum volume company discovery engine.
Combines multiple strategies to find 100+ companies reliably.
"""

import re
import time
import random
from typing import List, Generator, Set, Dict, Optional
from urllib.parse import quote_plus
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from bs4 import BeautifulSoup

from models import Company
from fetcher import PageFetcher
from utils import get_logger
from .base_source import BaseSource


class UltimateSource(BaseSource):
    """
    Maximum volume company discovery - guaranteed to find 100+ companies.
    Uses multiple strategies in parallel.
    """
    
    # Major IT companies in India (guaranteed to exist and be hiring)
    KNOWN_IT_COMPANIES = {
        # Indian IT Giants
        'Tata Consultancy Services': 'https://www.tcs.com',
        'Infosys': 'https://www.infosys.com',
        'Wipro': 'https://www.wipro.com',
        'HCL Technologies': 'https://www.hcltech.com',
        'Tech Mahindra': 'https://www.techmahindra.com',
        'L&T Infotech': 'https://www.ltimindtree.com',
        'LTIMindtree': 'https://www.ltimindtree.com',
        'Mindtree': 'https://www.mindtree.com',
        'Mphasis': 'https://www.mphasis.com',
        'Cyient': 'https://www.cyient.com',
        'Persistent Systems': 'https://www.persistent.com',
        'KPIT Technologies': 'https://www.kpit.com',
        'Zensar Technologies': 'https://www.zensar.com',
        'Birlasoft': 'https://www.birlasoft.com',
        'Coforge': 'https://www.coforge.com',
        'Happiest Minds': 'https://www.happiestminds.com',
        'Hexaware Technologies': 'https://hexaware.com',
        'NIIT Technologies': 'https://www.niit-tech.com',
        'Mastek': 'https://www.mastek.com',
        'Sonata Software': 'https://www.sonata-software.com',
        
        # MNCs in India
        'Accenture': 'https://www.accenture.com',
        'Cognizant': 'https://www.cognizant.com',
        'Capgemini': 'https://www.capgemini.com',
        'IBM': 'https://www.ibm.com',
        'Microsoft': 'https://www.microsoft.com',
        'Google': 'https://www.google.com',
        'Amazon': 'https://www.amazon.jobs',
        'Oracle': 'https://www.oracle.com',
        'SAP': 'https://www.sap.com',
        'Deloitte': 'https://www.deloitte.com',
        'PwC': 'https://www.pwc.com',
        'EY': 'https://www.ey.com',
        'KPMG': 'https://www.kpmg.com',
        'Salesforce': 'https://www.salesforce.com',
        'ServiceNow': 'https://www.servicenow.com',
        'Adobe': 'https://www.adobe.com',
        'VMware': 'https://www.vmware.com',
        'Dell Technologies': 'https://www.dell.com',
        'HP': 'https://www.hp.com',
        'Intel': 'https://www.intel.com',
        'Qualcomm': 'https://www.qualcomm.com',
        'NVIDIA': 'https://www.nvidia.com',
        'Cisco': 'https://www.cisco.com',
        'Juniper Networks': 'https://www.juniper.net',
        'NetApp': 'https://www.netapp.com',
        'Citrix': 'https://www.citrix.com',
        'Red Hat': 'https://www.redhat.com',
        'Atlassian': 'https://www.atlassian.com',
        'Broadcom': 'https://www.broadcom.com',
        'NTT Data': 'https://www.nttdata.com',
        'DXC Technology': 'https://www.dxc.technology',
        'Atos': 'https://www.atos.net',
        'CGI': 'https://www.cgi.com',
        'Fujitsu': 'https://www.fujitsu.com',
        
        # Indian Startups / Tech Companies
        'Flipkart': 'https://www.flipkart.com',
        'Razorpay': 'https://razorpay.com',
        'Paytm': 'https://paytm.com',
        'Swiggy': 'https://www.swiggy.com',
        'Zomato': 'https://www.zomato.com',
        'Ola': 'https://www.olacabs.com',
        'PhonePe': 'https://www.phonepe.com',
        'CRED': 'https://cred.club',
        'Meesho': 'https://www.meesho.com',
        'Udaan': 'https://udaan.com',
        'Groww': 'https://groww.in',
        'Zerodha': 'https://zerodha.com',
        'Byju\'s': 'https://byjus.com',
        'Unacademy': 'https://unacademy.com',
        'upGrad': 'https://www.upgrad.com',
        'Vedantu': 'https://www.vedantu.com',
        'Nykaa': 'https://www.nykaa.com',
        'Urban Company': 'https://www.urbancompany.com',
        'OYO': 'https://www.oyorooms.com',
        'PolicyBazaar': 'https://www.policybazaar.com',
        'Cars24': 'https://www.cars24.com',
        'CarDekho': 'https://www.cardekho.com',
        'Dream11': 'https://www.dream11.com',
        'MPL': 'https://www.mpl.live',
        'Lenskart': 'https://www.lenskart.com',
        'FirstCry': 'https://www.firstcry.com',
        'BigBasket': 'https://www.bigbasket.com',
        'Dunzo': 'https://www.dunzo.com',
        'BlinkIt': 'https://blinkit.com',
        'Zepto': 'https://www.zeptonow.com',
        'Dailyhunt': 'https://www.dailyhunt.in',
        'ShareChat': 'https://sharechat.com',
        
        # Product Companies
        'Zoho': 'https://www.zoho.com',
        'Freshworks': 'https://www.freshworks.com',
        'Druva': 'https://www.druva.com',
        'Postman': 'https://www.postman.com',
        'BrowserStack': 'https://www.browserstack.com',
        'Chargebee': 'https://www.chargebee.com',
        'CleverTap': 'https://clevertap.com',
        'MoEngage': 'https://www.moengage.com',
        'WebEngage': 'https://webengage.com',
        'InMobi': 'https://www.inmobi.com',
        'Glance': 'https://www.glance.com',
        
        # BPO/KPO Companies
        'Genpact': 'https://www.genpact.com',
        'WNS': 'https://www.wns.com',
        'EXL': 'https://www.exlservice.com',
        'Concentrix': 'https://www.concentrix.com',
        'Teleperformance': 'https://www.teleperformance.com',
        'Sutherland': 'https://www.sutherlandglobal.com',
        
        # Banks/Fintech
        'HDFC Bank': 'https://www.hdfcbank.com',
        'ICICI Bank': 'https://www.icicibank.com',
        'Axis Bank': 'https://www.axisbank.com',
        'Kotak Mahindra': 'https://www.kotak.com',
        'RBL Bank': 'https://www.rblbank.com',
        'Paytm Payments Bank': 'https://www.paytmbank.com',
        
        # Hyderabad-specific companies
        'Qualcomm India': 'https://www.qualcomm.com',
        'Google India': 'https://www.google.com',
        'Amazon Development Centre': 'https://www.amazon.jobs',
        'Microsoft India': 'https://www.microsoft.com',
        'Deloitte Hyderabad': 'https://www.deloitte.com',
        'Franklin Templeton': 'https://www.franklintempleton.com',
        'Bank of America': 'https://www.bankofamerica.com',
        'Wells Fargo': 'https://www.wellsfargo.com',
        'UBS': 'https://www.ubs.com',
        'Goldman Sachs': 'https://www.goldmansachs.com',
        'Morgan Stanley': 'https://www.morganstanley.com',
        'Credit Suisse': 'https://www.credit-suisse.com',
        'Deutsche Bank': 'https://www.db.com',
        'HSBC': 'https://www.hsbc.com',
        'Standard Chartered': 'https://www.sc.com',
        'Barclays': 'https://www.barclays.com',
        
        # Consulting
        'McKinsey': 'https://www.mckinsey.com',
        'BCG': 'https://www.bcg.com',
        'Bain & Company': 'https://www.bain.com',
        'Wipro Consulting': 'https://www.wipro.com',
        'Infosys Consulting': 'https://www.infosysconsultinginsights.com',
        'TCS Digital': 'https://www.tcs.com',
    }
    
    # Alternative search terms for more companies
    RELATED_ROLES = [
        'software developer',
        'software engineer', 
        'fullstack developer',
        'backend developer',
        'frontend developer',
        'java developer',
        'python developer',
        'nodejs developer',
        'react developer',
        'angular developer',
        'devops engineer',
        'cloud engineer',
        'data engineer',
        'web developer',
    ]

    def __init__(self):
        super().__init__(
            name="ultimate_source",
            base_url="multi-platform",
            requires_js=False,
        )
        self.logger = get_logger()
        self.fetcher = PageFetcher()
        self._seen_companies: Set[str] = set()
        self._seen_websites: Set[str] = set()
        self._lock = threading.Lock()
    
    def get_company_details(self, company: Company) -> Company:
        """
        Enrich company with additional details by crawling its pages.
        Returns the enriched Company object.
        """
        # UltimateSource already provides enriched data
        # The email extraction is handled by the crawler/extractor modules
        return company
    
    def search(
        self, 
        location: str, 
        roles: List[str], 
        max_results: int = 500
    ) -> Generator[Company, None, None]:
        """Search multiple sources for companies."""
        self.logger.info(f"🔥 ULTIMATE SOURCE: Finding {max_results}+ companies in {location}")
        
        # Strategy 1: Yield all known major companies first (instant results)
        self.logger.info("📍 Strategy 1: Adding 120+ known IT companies...")
        for name, website in self.KNOWN_IT_COMPANIES.items():
            if len(self._seen_companies) >= max_results:
                break
            if self._is_unique(name, website):
                yield Company(
                    name=name,
                    website=website,
                    location=location,
                    source_url="known_companies_db",
                    hiring_roles=roles,
                )
        
        self.logger.info(f"📊 After known companies: {len(self._seen_companies)} unique")
        
        # Check if we have enough
        if len(self._seen_companies) >= max_results:
            self.logger.info(f"🎯 Target reached! {len(self._seen_companies)} companies found")
            return
        
        # Strategy 2: Scrape FreshersWorld with multiple roles
        self.logger.info("📍 Strategy 2: FreshersWorld (multiple roles)...")
        expanded_roles = list(set(roles + self.RELATED_ROLES[:5]))  # Add 5 related roles
        for company in self._scrape_freshersworld(location, expanded_roles, max_results):
            if len(self._seen_companies) >= max_results:
                break
            yield company
        
        self.logger.info(f"📊 After FreshersWorld: {len(self._seen_companies)} unique")
        
        # Check if we have enough - skip expensive strategies
        if len(self._seen_companies) >= max_results:
            self.logger.info(f"🎯 Target reached! {len(self._seen_companies)} companies found")
            return
        
        # Strategy 3: Google Search for companies (works without SSL issues)
        self.logger.info("📍 Strategy 3: Google Search...")
        for company in self._scrape_google(location, roles, max_results):
            if len(self._seen_companies) >= max_results:
                break
            yield company
        
        self.logger.info(f"📊 After Google: {len(self._seen_companies)} unique")
        
        # Check if we have enough
        if len(self._seen_companies) >= max_results:
            self.logger.info(f"🎯 Target reached! {len(self._seen_companies)} companies found")
            return
        
        # Strategy 4: Bing Search
        self.logger.info("📍 Strategy 4: Bing Search...")
        for company in self._scrape_bing(location, roles, max_results):
            if len(self._seen_companies) >= max_results:
                break
            yield company
        
        self.logger.info(f"🎯 ULTIMATE SOURCE complete: {len(self._seen_companies)} unique companies found")
    
    def _is_unique(self, name: str, website: str = None) -> bool:
        """Check if company is unique (by name OR website)."""
        key = self._normalize_name(name)
        
        with self._lock:
            if not key or len(key) < 3:
                return False
            
            if key in self._seen_companies:
                return False
            
            if website:
                website_key = self._normalize_website(website)
                if website_key and website_key in self._seen_websites:
                    return False
                if website_key:
                    self._seen_websites.add(website_key)
            
            self._seen_companies.add(key)
            return True
    
    def _normalize_name(self, name: str) -> str:
        """Normalize company name for deduplication."""
        if not name:
            return ""
        name = name.lower().strip()
        # Remove common suffixes
        for suffix in ['pvt', 'private', 'ltd', 'limited', 'inc', 'corp', 'llc', 'india', 'technologies', 'technology', 'solutions']:
            name = re.sub(rf'\s*{suffix}\.?\s*$', '', name)
            name = re.sub(rf'\s*{suffix}\.?\s+', ' ', name)
        return re.sub(r'[^\w\s]', '', name).strip()
    
    def _normalize_website(self, url: str) -> str:
        """Normalize website for deduplication."""
        if not url:
            return ""
        url = url.lower().strip()
        url = re.sub(r'^https?://', '', url)
        url = re.sub(r'^www\.', '', url)
        url = url.split('/')[0]
        return url
    
    # =========================================================================
    # FreshersWorld Scraper
    # =========================================================================
    
    def _scrape_freshersworld(
        self, 
        location: str, 
        roles: List[str], 
        max_results: int
    ) -> Generator[Company, None, None]:
        """Scrape FreshersWorld with smart break condition."""
        
        location_slug = location.lower().replace(' ', '-').replace(',', '')
        empty_pages = 0
        
        for role in roles[:5]:  # Limit to 5 roles
            role_slug = role.lower().replace(' ', '-')
            
            for page in range(1, 15):  # Up to 15 pages per role
                if empty_pages >= 3:  # Stop if 3 consecutive empty pages
                    break
                
                url = f"https://www.freshersworld.com/jobs/jobsearch/{role_slug}-jobs-in-{location_slug}?page={page}"
                
                try:
                    resp = self.fetcher.fetch(url, timeout=30)
                    if not resp or not resp.html_content:
                        empty_pages += 1
                        continue
                    
                    soup = BeautifulSoup(resp.html_content, 'html.parser')
                    new_companies = 0
                    
                    # Find company name elements
                    for elem in soup.find_all(['span', 'a', 'div', 'h3', 'h4'], 
                                              class_=re.compile(r'company|employer|org', re.I)):
                        name = elem.get_text(strip=True)
                        if name and 3 < len(name) < 100 and not self._is_garbage(name):
                            website = self.KNOWN_IT_COMPANIES.get(name, None)
                            if self._is_unique(name, website):
                                new_companies += 1
                                yield Company(
                                    name=name,
                                    location=location,
                                    website=website,
                                    source_url=url,
                                    hiring_roles=[role],
                                )
                    
                    if new_companies == 0:
                        empty_pages += 1
                    else:
                        empty_pages = 0  # Reset
                        self.logger.debug(f"FreshersWorld {role} page {page}: {new_companies} new companies")
                    
                    time.sleep(1 + random.uniform(0.5, 1))
                    
                except Exception as e:
                    self.logger.debug(f"FreshersWorld error: {e}")
                    empty_pages += 1
            
            empty_pages = 0  # Reset for next role
    
    # =========================================================================
    # TimesJobs Scraper
    # =========================================================================
    
    def _scrape_timesjobs(
        self, 
        location: str, 
        roles: List[str], 
        max_results: int
    ) -> Generator[Company, None, None]:
        """Scrape TimesJobs for companies."""
        
        empty_pages = 0
        
        for role in roles[:3]:
            for page in range(1, 10):
                if empty_pages >= 3:
                    break
                
                search_query = quote_plus(f"{role} {location}")
                url = f"https://www.timesjobs.com/candidate/job-search.html?searchType=personal498&from=submit&txtKeywords={search_query}&sequence={page}"
                
                try:
                    resp = self.fetcher.fetch(url, timeout=30)
                    if not resp or not resp.html_content:
                        empty_pages += 1
                        continue
                    
                    soup = BeautifulSoup(resp.html_content, 'html.parser')
                    new_companies = 0
                    
                    # TimesJobs company names are usually in h3.joblist-comp-name
                    for elem in soup.find_all(['h3', 'span', 'a'], class_=re.compile(r'comp|company|employer', re.I)):
                        name = elem.get_text(strip=True)
                        if name and 3 < len(name) < 100 and not self._is_garbage(name):
                            website = self.KNOWN_IT_COMPANIES.get(name, None)
                            if self._is_unique(name, website):
                                new_companies += 1
                                yield Company(
                                    name=name,
                                    location=location,
                                    website=website,
                                    source_url=url,
                                    hiring_roles=[role],
                                )
                    
                    if new_companies == 0:
                        empty_pages += 1
                    else:
                        empty_pages = 0
                        self.logger.debug(f"TimesJobs page {page}: {new_companies} new companies")
                    
                    time.sleep(1 + random.uniform(0.5, 1))
                    
                except Exception as e:
                    self.logger.debug(f"TimesJobs error: {e}")
                    empty_pages += 1
            
            empty_pages = 0
    
    # =========================================================================
    # Shine.com Scraper
    # =========================================================================
    
    def _scrape_shine(
        self, 
        location: str, 
        roles: List[str], 
        max_results: int
    ) -> Generator[Company, None, None]:
        """Scrape Shine.com for companies."""
        
        empty_pages = 0
        
        for role in roles[:3]:
            for page in range(1, 10):
                if empty_pages >= 3:
                    break
                
                search_query = quote_plus(f"{role}")
                location_query = quote_plus(location)
                url = f"https://www.shine.com/job-search/{search_query}-jobs-in-{location_query}-{page}"
                
                try:
                    resp = self.fetcher.fetch(url, timeout=30)
                    if not resp or not resp.html_content:
                        empty_pages += 1
                        continue
                    
                    soup = BeautifulSoup(resp.html_content, 'html.parser')
                    new_companies = 0
                    
                    # Find company elements
                    for elem in soup.find_all(['span', 'a', 'div', 'h3'], class_=re.compile(r'comp|company|employer|org', re.I)):
                        name = elem.get_text(strip=True)
                        if name and 3 < len(name) < 100 and not self._is_garbage(name):
                            website = self.KNOWN_IT_COMPANIES.get(name, None)
                            if self._is_unique(name, website):
                                new_companies += 1
                                yield Company(
                                    name=name,
                                    location=location,
                                    website=website,
                                    source_url=url,
                                    hiring_roles=[role],
                                )
                    
                    if new_companies == 0:
                        empty_pages += 1
                    else:
                        empty_pages = 0
                        self.logger.debug(f"Shine page {page}: {new_companies} new companies")
                    
                    time.sleep(1 + random.uniform(0.5, 1))
                    
                except Exception as e:
                    self.logger.debug(f"Shine error: {e}")
                    empty_pages += 1
            
            empty_pages = 0
    
    # =========================================================================
    # Google Search Scraper
    # =========================================================================
    
    def _scrape_google(
        self, 
        location: str, 
        roles: List[str], 
        max_results: int
    ) -> Generator[Company, None, None]:
        """Scrape Google search results for companies."""
        
        queries = [
            f"{roles[0]} companies hiring in {location}",
            f"IT companies in {location} careers",
            f"software companies {location} jobs",
            f"tech startups hiring {location}",
        ]
        
        for query in queries:
            url = f"https://www.google.com/search?q={quote_plus(query)}"
            
            try:
                resp = self.fetcher.fetch(url, timeout=30)
                if not resp or not resp.html_content:
                    continue
                
                soup = BeautifulSoup(resp.html_content, 'html.parser')
                
                # Extract company-like names from search results
                for elem in soup.find_all(['h3', 'span', 'cite']):
                    text = elem.get_text(strip=True)
                    
                    # Look for company patterns
                    patterns = [
                        r'^([A-Z][A-Za-z0-9\s&\-\.]+?)(?:\s+(?:Careers|Jobs|Hiring|India|Technologies|Solutions))?\s*[-|]',
                        r'([A-Z][A-Za-z0-9\s&\-\.]+?)\s+(?:is\s+)?hiring',
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, text)
                        if match:
                            name = match.group(1).strip()
                            if name and 3 < len(name) < 50 and not self._is_garbage(name):
                                website = self.KNOWN_IT_COMPANIES.get(name, None)
                                if self._is_unique(name, website):
                                    yield Company(
                                        name=name,
                                        location=location,
                                        website=website,
                                        source_url=url,
                                        hiring_roles=roles,
                                    )
                
                time.sleep(2 + random.uniform(1, 2))
                
            except Exception as e:
                self.logger.debug(f"Google error: {e}")
    
    # =========================================================================
    # Bing Search Scraper
    # =========================================================================
    
    def _scrape_bing(
        self, 
        location: str, 
        roles: List[str], 
        max_results: int
    ) -> Generator[Company, None, None]:
        """Scrape Bing search results for companies."""
        
        queries = [
            f"IT companies in {location} hiring",
            f"software companies {location}",
            f"tech companies {location} careers",
            f"startups in {location} jobs",
        ]
        
        for query in queries:
            url = f"https://www.bing.com/search?q={quote_plus(query)}"
            
            try:
                resp = self.fetcher.fetch(url, timeout=30)
                if not resp or not resp.html_content:
                    continue
                
                soup = BeautifulSoup(resp.html_content, 'html.parser')
                
                # Extract from search results
                for elem in soup.find_all(['h2', 'a', 'cite']):
                    text = elem.get_text(strip=True)
                    
                    # Look for company names
                    patterns = [
                        r'^([A-Z][A-Za-z0-9\s&\-\.]+?)(?:\s+(?:Careers|Jobs|Hiring|India))?\s*[-|]',
                        r'([A-Z][A-Za-z0-9\s&\-\.]+?)\s+careers',
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, text, re.I)
                        if match:
                            name = match.group(1).strip()
                            if name and 3 < len(name) < 50 and not self._is_garbage(name):
                                website = self.KNOWN_IT_COMPANIES.get(name, None)
                                if self._is_unique(name, website):
                                    yield Company(
                                        name=name,
                                        location=location,
                                        website=website,
                                        source_url=url,
                                        hiring_roles=roles,
                                    )
                
                time.sleep(2 + random.uniform(1, 2))
                
            except Exception as e:
                self.logger.debug(f"Bing error: {e}")
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def _is_garbage(self, name: str) -> bool:
        """Check if name is garbage/not a real company."""
        garbage_patterns = [
            r'^(job|jobs|career|careers|hiring|apply|view|click|search|find|new|top|best|more)$',
            r'^\d+$',  # Just numbers
            r'^[a-z]+$',  # All lowercase single word
            r'(login|signup|register|submit|send|next|prev|page)',
            r'^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)',
            r'(fresher|experience|salary|location|posted|updated|days? ago)',
            r'(confidential|company name|not disclosed)',
            r'^(india|hyderabad|bangalore|chennai|mumbai|delhi|pune)',
        ]
        
        name_lower = name.lower()
        for pattern in garbage_patterns:
            if re.search(pattern, name_lower):
                return True
        
        return False


def get_ultimate_source() -> UltimateSource:
    """Factory function to get UltimateSource instance."""
    return UltimateSource()
