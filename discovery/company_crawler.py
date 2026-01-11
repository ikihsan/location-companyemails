"""
Company crawler for deep crawling company websites.
Follows links to careers, contact, about pages to extract emails.
Uses SmartHREmailExtractor for intelligent email filtering.
"""

import re
from typing import List, Set, Optional
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass

from models import Company, CrawlResult
from fetcher import PageFetcher, HybridFetcher
from parsers import HTMLParser, find_careers_page
from extractors import extract_emails_from_text, get_domain_from_url, get_smart_extractor
from utils import get_logger


@dataclass
class CrawlConfig:
    """Configuration for company crawling."""
    max_depth: int = 2
    max_pages_per_company: int = 10
    follow_careers: bool = True
    follow_contact: bool = True
    follow_about: bool = True
    extract_from_pdfs: bool = False


class CompanyCrawler:
    """
    Deep crawler for company websites.
    Follows relevant links to find contact information.
    """
    
    # Patterns for relevant pages (EXPANDED)
    RELEVANT_PATHS = {
        'careers': [r'/careers', r'/jobs', r'/openings', r'/positions', r'/join', r'/work-with-us', 
                    r'/hiring', r'/vacancy', r'/vacancies', r'/recruitment', r'/apply', r'/opportunities',
                    r'/job-listing', r'/current-openings', r'/life-at', r'/work-at', r'/join-us',
                    r'/career', r'/job', r'/open-positions', r'/talent', r'/people'],
        'contact': [r'/contact', r'/kontakt', r'/reach-us', r'/get-in-touch', r'/connect', 
                    r'/contact-us', r'/reach-out', r'/enquiry', r'/inquiry', r'/talk-to-us',
                    r'/write-to-us', r'/get-started', r'/demo', r'/request'],
        'about': [r'/about', r'/team', r'/company', r'/who-we-are', r'/our-team', r'/leadership',
                  r'/about-us', r'/our-story', r'/our-company', r'/overview', r'/management'],
        'legal': [r'/impressum', r'/imprint', r'/legal', r'/datenschutz', r'/privacy', r'/terms'],
        'hr': [r'/hr', r'/human-resources', r'/people-team', r'/talent-acquisition', r'/recruiting'],
    }
    
    def __init__(
        self,
        config: Optional[CrawlConfig] = None,
        use_headless: bool = False,
    ):
        self.config = config or CrawlConfig()
        self.logger = get_logger()
        self.fetcher = HybridFetcher(use_headless=use_headless)
        self.smart_extractor = get_smart_extractor()  # Smart HR email extraction
    
    def crawl_company(self, company: Company) -> Company:
        """
        Deep crawl a company's website to extract all available information.
        If no website is available, tries to find it using search engines.
        """
        # If no website, try to find it via search engine
        if not company.website:
            self.logger.debug(f"No website for {company.name}, searching...")
            found_url = self._find_company_website_via_search(company.name)
            if found_url:
                company.website = found_url
                self.logger.info(f"Found website for {company.name}: {found_url}")
            else:
                self.logger.debug(f"Could not find website for {company.name}")
                return company
        
        base_domain = get_domain_from_url(company.website)
        visited: Set[str] = set()
        to_visit: List[tuple] = [(company.website, 0)]  # (url, depth)
        
        pages_crawled = 0
        
        while to_visit and pages_crawled < self.config.max_pages_per_company:
            url, depth = to_visit.pop(0)
            
            if url in visited:
                continue
            
            if depth > self.config.max_depth:
                continue
            
            visited.add(url)
            pages_crawled += 1
            
            self.logger.debug(f"Crawling {url} (depth={depth})")
            
            result = self.fetcher.fetch(url)
            
            if not result.success or not result.html_content:
                continue
            
            # Parse page
            parser = HTMLParser(url)
            parsed = parser.parse(result.html_content)
            
            # Extract emails using SMART HR extractor (filters out support/info emails)
            emails = self.smart_extractor.extract_hr_emails(
                result.html_content,
                url,
                company_name=company.name,
                company_domain=base_domain,
            )
            for email in emails:
                company.add_email(email)
            
            # Update company info
            if not company.name or company.name == "Unknown":
                if parsed.company_info.get('name'):
                    company.name = parsed.company_info['name']
            
            if parsed.social_links.get('linkedin') and not company.linkedin_url:
                company.linkedin_url = parsed.social_links['linkedin']
            
            # Find careers URL
            if not company.careers_url and parsed.careers_links:
                company.careers_url = parsed.careers_links[0]
            
            # Extract job postings
            for job in parsed.job_postings:
                title = job.get('title', '')
                if title and title not in company.hiring_roles:
                    company.hiring_roles.append(title)
            
            # Queue relevant pages for crawling
            if depth < self.config.max_depth:
                for link in parsed.links:
                    if self._is_relevant_link(link, base_domain, visited):
                        to_visit.append((link, depth + 1))
        
        company.crawl_depth = pages_crawled
        
        self.logger.info(f"Crawled {pages_crawled} pages for {company.name}, found {len(company.emails)} emails")
        
        return company
    
    def _is_relevant_link(self, url: str, base_domain: str, visited: Set[str]) -> bool:
        """Check if a link is relevant for crawling."""
        if url in visited:
            return False
        
        # Must be same domain
        link_domain = get_domain_from_url(url)
        if link_domain and base_domain not in link_domain:
            return False
        
        parsed = urlparse(url)
        path = parsed.path.lower()
        
        # Skip common non-content paths
        skip_patterns = [
            r'\.pdf$', r'\.jpg$', r'\.png$', r'\.gif$', r'\.css$', r'\.js$',
            r'\.svg$', r'\.ico$', r'\.woff', r'\.ttf$', r'\.eot$',
            r'/cdn-cgi/', r'/wp-content/', r'/wp-includes/',
            r'/tag/', r'/category/', r'/author/',
            r'/blog/', r'/news/', r'/press/',  # Skip blog/news sections
            r'/login', r'/signin', r'/signup', r'/register',
            r'/cart', r'/checkout', r'/account',
            r'/search', r'/sitemap',
            r'\?', r'#',
        ]
        
        for pattern in skip_patterns:
            if re.search(pattern, url, re.I):
                return False
        
        # Check if path matches relevant patterns (PRIORITY - always follow these)
        for category, patterns in self.RELEVANT_PATHS.items():
            for pattern in patterns:
                if re.search(pattern, path):
                    return True
        
        # Also allow top-level pages (short paths) which often have contact info
        if path.count('/') <= 2 and len(path) < 30:
            return True
        
        return False
    
    def _find_company_website_via_search(self, company_name: str) -> Optional[str]:
        """
        Use search engines to find the real company website.
        Returns the most likely official company website URL.
        """
        import time
        
        # Skip generic/placeholder company names
        invalid_names = {
            'for a client', 'client of', 'confidential', 'various', 'multiple',
            'to be disclosed', 'tbd', 'n/a', 'na', 'undisclosed'
        }
        name_lower = company_name.lower()
        if any(inv in name_lower for inv in invalid_names):
            return None
        
        # Search query
        query = f"{company_name} official website careers contact"
        encoded_query = query.replace(' ', '+')
        
        # Use Bing (most reliable for this purpose)
        search_url = f"https://www.bing.com/search?q={encoded_query}"
        
        result = self.fetcher.fetch(search_url)
        if not result.success or not result.html_content:
            return None
        
        # Extract URLs from search results
        # Look for company-related URLs in the results
        url_pattern = r'href="(https?://(?:www\.)?[^/"]+[^"]*)"'
        matches = re.findall(url_pattern, result.html_content, re.IGNORECASE)
        
        # Common domains to skip (job boards, search engines, social media)
        skip_domains = {
            'bing.com', 'google.com', 'yahoo.com', 'facebook.com', 'twitter.com',
            'linkedin.com', 'instagram.com', 'youtube.com', 'wikipedia.org',
            'indeed.com', 'glassdoor.com', 'naukri.com', 'monster.com',
            'freshersworld.com', 'shine.com', 'timesjobs.com', 'simplyhired.com',
            'ziprecruiter.com', 'careerbuilder.com', 'microsoft.com', 'msn.com',
            'yelp.com', 'yellowpages.com', 'crunchbase.com', 'zoominfo.com',
            'ambitionbox.com', 'fundoodata.com', 'justdial.com', 'sulekha.com',
        }
        
        # Find the first likely company website
        for url in matches:
            try:
                parsed = urlparse(url)
                domain = parsed.netloc.lower().replace('www.', '')
                
                # Skip known non-company domains
                if any(skip in domain for skip in skip_domains):
                    continue
                
                # Skip very long domains (likely not real)
                if len(domain) > 40:
                    continue
                
                # Check if company name words appear in domain
                name_words = [w.lower() for w in re.findall(r'[a-zA-Z]+', company_name) if len(w) > 2]
                domain_clean = domain.replace('.com', '').replace('.in', '').replace('.co', '').replace('.io', '')
                
                # If any significant word from company name is in domain, it's likely the right site
                for word in name_words:
                    if len(word) > 3 and word in domain_clean:
                        # Construct clean base URL
                        base_url = f"https://{parsed.netloc}"
                        return base_url
                
            except Exception:
                continue
        
        return None
    
    def crawl_careers_page(self, company: Company) -> Company:
        """Specifically crawl the careers page if available."""
        careers_url = company.careers_url
        
        if not careers_url and company.website:
            # Try to find careers page
            result = self.fetcher.fetch(company.website)
            if result.success and result.html_content:
                parser = HTMLParser(company.website)
                parsed = parser.parse(result.html_content)
                careers_url = find_careers_page(parsed.links, company.website)
        
        if not careers_url:
            return company
        
        company.careers_url = careers_url
        
        result = self.fetcher.fetch(careers_url)
        if not result.success or not result.html_content:
            return company
        
        parser = HTMLParser(careers_url)
        parsed = parser.parse(result.html_content)
        
        # Extract all job postings
        for job in parsed.job_postings:
            title = job.get('title', '')
            if title and title not in company.hiring_roles:
                company.hiring_roles.append(title)
        
        # Extract emails using SMART HR extractor
        domain = get_domain_from_url(company.website) if company.website else None
        emails = self.smart_extractor.extract_hr_emails(
            result.html_content, 
            careers_url,
            company_name=company.name,
            company_domain=domain,
        )
        for email in emails:
            company.add_email(email)
        
        return company
    
    def close(self):
        """Close the fetcher."""
        self.fetcher.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
