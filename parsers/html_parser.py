"""
HTML content parser module.
Extracts structured data from HTML pages.
"""

import re
from typing import List, Optional, Dict, Tuple, Set
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag


@dataclass
class ParsedPage:
    """Structured data extracted from a page."""
    title: str
    text_content: str
    links: List[str]
    emails_raw: List[str]
    job_postings: List[Dict]
    company_info: Dict
    contact_info: Dict
    careers_links: List[str]
    social_links: Dict[str, str]


class HTMLParser:
    """Parses HTML pages to extract relevant information."""
    
    # Patterns to identify careers/jobs pages
    CAREERS_PATTERNS = [
        r'/careers', r'/jobs', r'/job', r'/openings', r'/positions',
        r'/work-with-us', r'/join-us', r'/join', r'/hiring', r'/vacancies',
        r'/opportunities', r'/employment', r'/team',
    ]
    
    # Patterns for contact pages
    CONTACT_PATTERNS = [
        r'/contact', r'/kontakt', r'/about', r'/impressum', 
        r'/imprint', r'/legal', r'/info',
    ]
    
    # Social media patterns
    SOCIAL_PATTERNS = {
        'linkedin': r'linkedin\.com',
        'twitter': r'twitter\.com|x\.com',
        'facebook': r'facebook\.com',
        'github': r'github\.com',
        'instagram': r'instagram\.com',
    }
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.base_domain = urlparse(base_url).netloc
    
    def parse(self, html_content: str) -> ParsedPage:
        """Parse HTML content and extract all relevant data."""
        soup = BeautifulSoup(html_content, 'lxml')
        
        # Remove script and style elements
        for element in soup(['script', 'style', 'noscript', 'header', 'footer', 'nav']):
            element.decompose()
        
        title = self._extract_title(soup)
        text_content = self._extract_text(soup)
        links = self._extract_links(soup)
        emails_raw = self._extract_emails_from_html(soup)
        job_postings = self._extract_job_postings(soup)
        company_info = self._extract_company_info(soup)
        contact_info = self._extract_contact_info(soup)
        careers_links = self._filter_careers_links(links)
        social_links = self._extract_social_links(links)
        
        return ParsedPage(
            title=title,
            text_content=text_content,
            links=links,
            emails_raw=emails_raw,
            job_postings=job_postings,
            company_info=company_info,
            contact_info=contact_info,
            careers_links=careers_links,
            social_links=social_links,
        )
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title."""
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text(strip=True)
        
        h1_tag = soup.find('h1')
        if h1_tag:
            return h1_tag.get_text(strip=True)
        
        return ''
    
    def _extract_text(self, soup: BeautifulSoup) -> str:
        """Extract all text content."""
        text = soup.get_text(separator=' ', strip=True)
        # Normalize whitespace
        text = ' '.join(text.split())
        return text
    
    def _extract_links(self, soup: BeautifulSoup) -> List[str]:
        """Extract all links from the page."""
        links = []
        seen: Set[str] = set()
        
        for anchor in soup.find_all('a', href=True):
            href = anchor['href']
            
            # Skip javascript and anchor links
            if href.startswith(('javascript:', '#', 'mailto:', 'tel:')):
                continue
            
            # Resolve relative URLs
            full_url = urljoin(self.base_url, href)
            
            # Normalize
            full_url = full_url.split('#')[0].rstrip('/')
            
            if full_url not in seen:
                seen.add(full_url)
                links.append(full_url)
        
        return links
    
    def _extract_emails_from_html(self, soup: BeautifulSoup) -> List[str]:
        """Extract emails from mailto links and visible text."""
        emails = []
        
        # From mailto links
        for anchor in soup.find_all('a', href=True):
            href = anchor['href']
            if href.startswith('mailto:'):
                email = href.replace('mailto:', '').split('?')[0]
                if email and '@' in email:
                    emails.append(email.lower())
        
        return emails
    
    def _extract_job_postings(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract structured job posting data."""
        jobs = []
        
        # Look for JSON-LD structured data
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                import json
                data = json.loads(script.string)
                if isinstance(data, dict):
                    if data.get('@type') == 'JobPosting':
                        jobs.append(self._parse_job_posting(data))
                    elif data.get('@type') == 'ItemList':
                        for item in data.get('itemListElement', []):
                            if isinstance(item, dict) and item.get('@type') == 'JobPosting':
                                jobs.append(self._parse_job_posting(item))
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get('@type') == 'JobPosting':
                            jobs.append(self._parse_job_posting(item))
            except (json.JSONDecodeError, AttributeError):
                continue
        
        # Look for common job listing patterns
        job_containers = soup.find_all(['div', 'article', 'li'], class_=re.compile(
            r'job|position|opening|vacancy|career', re.I
        ))
        
        for container in job_containers[:10]:  # Limit to first 10
            title_elem = container.find(['h1', 'h2', 'h3', 'h4', 'a'], class_=re.compile(r'title|name', re.I))
            if not title_elem:
                title_elem = container.find(['h1', 'h2', 'h3', 'h4'])
            
            if title_elem:
                job = {
                    'title': title_elem.get_text(strip=True),
                    'description': container.get_text(strip=True)[:500],
                }
                
                link = container.find('a', href=True)
                if link:
                    job['url'] = urljoin(self.base_url, link['href'])
                
                if job['title'] and len(job['title']) > 3:
                    jobs.append(job)
        
        return jobs
    
    def _parse_job_posting(self, data: Dict) -> Dict:
        """Parse JSON-LD job posting."""
        return {
            'title': data.get('title', ''),
            'description': data.get('description', '')[:500],
            'url': data.get('url', ''),
            'company': data.get('hiringOrganization', {}).get('name', ''),
            'location': data.get('jobLocation', {}).get('address', {}).get('addressLocality', ''),
            'date_posted': data.get('datePosted', ''),
        }
    
    def _extract_company_info(self, soup: BeautifulSoup) -> Dict:
        """Extract company information."""
        info = {}
        
        # Look for Organization structured data
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                import json
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') in ['Organization', 'Corporation', 'LocalBusiness']:
                    info['name'] = data.get('name', '')
                    info['description'] = data.get('description', '')[:300]
                    info['url'] = data.get('url', '')
                    if 'address' in data:
                        addr = data['address']
                        if isinstance(addr, dict):
                            info['location'] = f"{addr.get('addressLocality', '')}, {addr.get('addressCountry', '')}"
                    break
            except (json.JSONDecodeError, AttributeError):
                continue
        
        # Meta tags
        og_title = soup.find('meta', property='og:site_name')
        if og_title and not info.get('name'):
            info['name'] = og_title.get('content', '')
        
        og_desc = soup.find('meta', property='og:description')
        if og_desc and not info.get('description'):
            info['description'] = og_desc.get('content', '')[:300]
        
        return info
    
    def _extract_contact_info(self, soup: BeautifulSoup) -> Dict:
        """Extract contact information."""
        contact = {}
        
        # Phone numbers
        phone_pattern = re.compile(r'[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,9}')
        for tel_link in soup.find_all('a', href=re.compile(r'^tel:')):
            phone = tel_link['href'].replace('tel:', '')
            contact['phone'] = phone
            break
        
        # Address
        address_elem = soup.find(['address', 'div'], class_=re.compile(r'address', re.I))
        if address_elem:
            contact['address'] = address_elem.get_text(strip=True)[:200]
        
        return contact
    
    def _filter_careers_links(self, links: List[str]) -> List[str]:
        """Filter links that likely lead to careers/jobs pages."""
        careers_links = []
        
        for link in links:
            parsed = urlparse(link)
            path = parsed.path.lower()
            
            # Check if internal link
            if self.base_domain not in parsed.netloc and parsed.netloc:
                continue
            
            # Check against patterns
            for pattern in self.CAREERS_PATTERNS:
                if re.search(pattern, path):
                    careers_links.append(link)
                    break
        
        return careers_links
    
    def _extract_social_links(self, links: List[str]) -> Dict[str, str]:
        """Extract social media links."""
        social = {}
        
        for link in links:
            for platform, pattern in self.SOCIAL_PATTERNS.items():
                if re.search(pattern, link, re.I):
                    if platform not in social:
                        social[platform] = link
                    break
        
        return social


def extract_company_name_from_url(url: str) -> str:
    """Try to extract company name from URL."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    
    # Remove common prefixes
    if domain.startswith('www.'):
        domain = domain[4:]
    
    # Remove TLD
    parts = domain.split('.')
    if len(parts) >= 2:
        name = parts[0]
    else:
        name = domain
    
    # Clean up
    name = name.replace('-', ' ').replace('_', ' ')
    name = name.title()
    
    return name


def find_careers_page(links: List[str], base_url: str) -> Optional[str]:
    """Find the most likely careers page from a list of links."""
    base_domain = urlparse(base_url).netloc
    
    # Priority patterns
    priority_patterns = [
        r'^/careers/?$',
        r'^/jobs/?$',
        r'^/careers/all',
        r'^/jobs/all',
        r'/careers$',
        r'/jobs$',
    ]
    
    for pattern in priority_patterns:
        for link in links:
            parsed = urlparse(link)
            if base_domain in parsed.netloc or not parsed.netloc:
                if re.search(pattern, parsed.path, re.I):
                    return link
    
    # Fallback to any careers link
    for link in links:
        parsed = urlparse(link)
        if base_domain in parsed.netloc or not parsed.netloc:
            if re.search(r'career|job|opening|position', parsed.path, re.I):
                return link
    
    return None
