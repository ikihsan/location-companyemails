"""
Email extraction module.
Extracts emails using regex, heuristics, and pattern matching.
"""

import re
from typing import List, Tuple, Optional, Set
from urllib.parse import urlparse
from models import ExtractedEmail, ExtractionMethod, ConfidenceLevel


class EmailExtractor:
    """Extracts and validates email addresses from various sources."""
    
    # Standard email regex
    EMAIL_REGEX = re.compile(
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        re.IGNORECASE
    )
    
    # Obfuscated patterns
    OBFUSCATED_PATTERNS = [
        # info [at] company [dot] com
        re.compile(
            r'([a-zA-Z0-9._%+-]+)\s*[\[\(]?\s*at\s*[\]\)]?\s*([a-zA-Z0-9.-]+)\s*[\[\(]?\s*dot\s*[\]\)]?\s*([a-zA-Z]{2,})',
            re.IGNORECASE
        ),
        # info(at)company(dot)com
        re.compile(
            r'([a-zA-Z0-9._%+-]+)\s*\(\s*at\s*\)\s*([a-zA-Z0-9.-]+)\s*\(\s*dot\s*\)\s*([a-zA-Z]{2,})',
            re.IGNORECASE
        ),
        # info AT company DOT com
        re.compile(
            r'([a-zA-Z0-9._%+-]+)\s+AT\s+([a-zA-Z0-9.-]+)\s+DOT\s+([a-zA-Z]{2,})',
            re.IGNORECASE
        ),
        # info @ company . com (with spaces)
        re.compile(
            r'([a-zA-Z0-9._%+-]+)\s*@\s*([a-zA-Z0-9.-]+)\s*\.\s*([a-zA-Z]{2,})',
            re.IGNORECASE
        ),
    ]
    
    # Mailto link pattern
    MAILTO_REGEX = re.compile(
        r'mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        re.IGNORECASE
    )
    
    # JSON email pattern (in JSON strings)
    JSON_EMAIL_REGEX = re.compile(
        r'"(?:email|mail|contact)":\s*"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"',
        re.IGNORECASE
    )
    
    # HR-related prefixes
    HR_PREFIXES = [
        'hr', 'jobs', 'careers', 'recruiting', 'talent', 'hiring', 
        'people', 'recruitment', 'apply', 'join', 'opportunities'
    ]
    
    # Common invalid patterns to filter (placeholder/fake emails)
    INVALID_PATTERNS = [
        # Image file patterns
        r'.*\.png$', r'.*\.jpg$', r'.*\.gif$', r'.*\.svg$',
        r'.*@2x\..*', r'.*@\d+x\..*',  # Image scaling patterns
        
        # Test/example domains
        r'.*@example\.com$', r'.*@example\.org$', r'.*@example\.net$',
        r'.*@test\.com$', r'.*@testing\.com$', r'.*@localhost$',
        r'.*@.*\.local$', r'.*@mailinator\.com$', r'.*@tempmail\..*$',
        r'.*@fakeemail\..*$', r'.*@dummy\..*$',
        
        # Common placeholder local parts (before @)
        r'^example@.*$', r'^test@.*$', r'^user@.*$', r'^your@.*$',
        r'^email@.*$', r'^name@.*$', r'^placeholder@.*$', r'^sample@.*$',
        r'^demo@.*$', r'^fake@.*$', r'^dummy@.*$', r'^noreply@.*$',
        r'^no-reply@.*$', r'^donotreply@.*$', r'^yourname@.*$',
        r'^youremail@.*$', r'^someone@.*$', r'^anyone@.*$',
        r'^john\.?doe@.*$', r'^jane\.?doe@.*$', r'^abc@.*$', r'^xyz@.*$',
        r'^xxx@.*$', r'^aaa@.*$', r'^asdf@.*$', r'^qwerty@.*$',
        r'^firstname\.?lastname@.*$', r'^first\.?last@.*$',
        
        # Technical/system patterns
        r'.*sentry.*', r'.*webpack.*', r'.*@github\.com$',
        r'.*@users\.noreply\.github\.com$', r'.*wixpress.*',
        r'.*@.*\.wix\.com$', r'.*@w3\.org$', r'.*schema.*@.*$',
        
        # Form validation patterns
        r'^[a-z]@[a-z]\.[a-z]{2,3}$',  # Single letter patterns like a@b.co
    ]
    
    # Context patterns that indicate email is a placeholder/example
    PLACEHOLDER_CONTEXT_PATTERNS = [
        r'placeholder\s*[=:]\s*["\']?[^"\']*?{email}',
        r'value\s*[=:]\s*["\']?[^"\']*?{email}.*(?:placeholder|example|sample)',
        r'data-placeholder\s*[=:]\s*["\']?[^"\']*?{email}',
        r'aria-label\s*[=:]\s*["\']?(?:enter|your|email|example)',
        r'<input[^>]*type=["\']?email["\']?[^>]*placeholder=["\']?[^"\']*{email}',
        r'e\.?g\.?\s*[:\-]?\s*{email}',  # "e.g.: email@example.com"
        r'for\s+example\s*[:\-]?\s*{email}',
        r'such\s+as\s*[:\-]?\s*{email}',
    ]
    
    def __init__(self, company_domain: Optional[str] = None):
        self.company_domain = company_domain
        self._invalid_patterns = [re.compile(p, re.IGNORECASE) for p in self.INVALID_PATTERNS]
        self._placeholder_patterns = [re.compile(p.replace('{email}', r'[\w\.\-]+@[\w\.\-]+'), re.IGNORECASE) 
                                       for p in self.PLACEHOLDER_CONTEXT_PATTERNS]
        self._seen_emails: Set[str] = set()
    
    def extract_all(
        self, 
        content: str, 
        source_url: str,
        company_domain: Optional[str] = None
    ) -> List[ExtractedEmail]:
        """Extract all emails from content using multiple methods."""
        if company_domain:
            self.company_domain = company_domain
        
        all_emails: List[ExtractedEmail] = []
        
        # Extract from mailto links (highest confidence)
        all_emails.extend(self._extract_mailto(content, source_url))
        
        # Extract from JSON payloads
        all_emails.extend(self._extract_from_json(content, source_url))
        
        # Extract plain emails
        all_emails.extend(self._extract_plain_regex(content, source_url))
        
        # Extract obfuscated emails
        all_emails.extend(self._extract_obfuscated(content, source_url))
        
        # Deduplicate
        unique_emails = self._deduplicate(all_emails)
        
        # Mark HR contacts
        for email in unique_emails:
            email.is_hr_contact = self._is_hr_email(email.email)
        
        return unique_emails
    
    def _extract_mailto(self, content: str, source_url: str) -> List[ExtractedEmail]:
        """Extract emails from mailto: links."""
        emails = []
        for match in self.MAILTO_REGEX.finditer(content):
            email = match.group(1).lower()
            context = self._get_context(content, match.start(), match.end())
            if self._is_valid_email(email, context):
                emails.append(ExtractedEmail(
                    email=email,
                    source_url=source_url,
                    extraction_method=ExtractionMethod.MAILTO_LINK,
                    confidence=ConfidenceLevel.HIGH,
                    domain_matches_company=self._domain_matches(email),
                    context=context,
                ))
        return emails
    
    def _extract_from_json(self, content: str, source_url: str) -> List[ExtractedEmail]:
        """Extract emails from JSON structures."""
        emails = []
        for match in self.JSON_EMAIL_REGEX.finditer(content):
            email = match.group(1).lower()
            context = self._get_context(content, match.start(), match.end())
            if self._is_valid_email(email, context):
                emails.append(ExtractedEmail(
                    email=email,
                    source_url=source_url,
                    extraction_method=ExtractionMethod.JSON_PAYLOAD,
                    confidence=ConfidenceLevel.HIGH,
                    domain_matches_company=self._domain_matches(email),
                    context=context,
                ))
        return emails
    
    def _extract_plain_regex(self, content: str, source_url: str) -> List[ExtractedEmail]:
        """Extract emails using standard regex."""
        emails = []
        for match in self.EMAIL_REGEX.finditer(content):
            email = match.group(0).lower()
            context = self._get_context(content, match.start(), match.end())
            if self._is_valid_email(email, context):
                confidence = ConfidenceLevel.MEDIUM if self._domain_matches(email) else ConfidenceLevel.LOW
                emails.append(ExtractedEmail(
                    email=email,
                    source_url=source_url,
                    extraction_method=ExtractionMethod.REGEX_PLAIN,
                    confidence=confidence,
                    domain_matches_company=self._domain_matches(email),
                    context=context,
                ))
        return emails
    
    def _extract_obfuscated(self, content: str, source_url: str) -> List[ExtractedEmail]:
        """Extract obfuscated emails."""
        emails = []
        for pattern in self.OBFUSCATED_PATTERNS:
            for match in pattern.finditer(content):
                try:
                    local_part = match.group(1)
                    domain = match.group(2)
                    tld = match.group(3)
                    email = f"{local_part}@{domain}.{tld}".lower()
                    context = self._get_context(content, match.start(), match.end())
                    
                    if self._is_valid_email(email, context):
                        emails.append(ExtractedEmail(
                            email=email,
                            source_url=source_url,
                            extraction_method=ExtractionMethod.REGEX_OBFUSCATED,
                            confidence=ConfidenceLevel.MEDIUM,
                            domain_matches_company=self._domain_matches(email),
                            context=context,
                        ))
                except (IndexError, AttributeError):
                    continue
        return emails
    
    def _is_valid_email(self, email: str, context: str = "") -> bool:
        """Check if email is valid and not a false positive."""
        if not email or len(email) < 5:
            return False
        
        if '@' not in email:
            return False
        
        # Check against invalid patterns
        for pattern in self._invalid_patterns:
            if pattern.match(email):
                return False
        
        # Check if email appears in placeholder context
        if context and self._is_placeholder_context(email, context):
            return False
        
        # Basic structure validation
        parts = email.split('@')
        if len(parts) != 2:
            return False
        
        local, domain = parts
        if not local or not domain:
            return False
        
        if '.' not in domain:
            return False
        
        # Check for common false positives
        if domain.endswith('.js') or domain.endswith('.css'):
            return False
        
        return True
    
    def _is_placeholder_context(self, email: str, context: str) -> bool:
        """Check if email appears in a placeholder/example context."""
        context_lower = context.lower()
        email_lower = email.lower()
        
        # Check for placeholder indicators near the email
        placeholder_indicators = [
            'placeholder', 'example', 'sample', 'e.g.', 'e.g:', 'eg:',
            'for instance', 'such as', 'demo', 'test', 'fake', 'dummy',
            'enter your email', 'your email here', 'email address here',
            'type your', 'input type="email"', 'data-placeholder',
            'aria-placeholder', 'enter email', 'email format'
        ]
        
        for indicator in placeholder_indicators:
            if indicator in context_lower:
                return True
        
        # Check compiled placeholder patterns
        for pattern in self._placeholder_patterns:
            if pattern.search(context):
                return True
        
        return False

    def _domain_matches(self, email: str) -> bool:
        """Check if email domain matches company domain."""
        if not self.company_domain:
            return False
        
        try:
            email_domain = email.split('@')[1].lower()
            company = self.company_domain.lower()
            
            # Direct match
            if email_domain == company:
                return True
            
            # Subdomain match
            if email_domain.endswith(f'.{company}'):
                return True
            
            # Company name in domain
            company_name = company.split('.')[0]
            if company_name in email_domain:
                return True
            
            return False
        except (IndexError, AttributeError):
            return False
    
    def _is_hr_email(self, email: str) -> bool:
        """Check if email is likely an HR/recruiting contact."""
        try:
            local_part = email.split('@')[0].lower()
            return any(prefix in local_part for prefix in self.HR_PREFIXES)
        except (IndexError, AttributeError):
            return False
    
    def _get_context(self, content: str, start: int, end: int, window: int = 100) -> str:
        """Get surrounding context for an email match."""
        ctx_start = max(0, start - window)
        ctx_end = min(len(content), end + window)
        context = content[ctx_start:ctx_end]
        # Clean up whitespace
        context = ' '.join(context.split())
        return context[:200]  # Limit context length
    
    def _deduplicate(self, emails: List[ExtractedEmail]) -> List[ExtractedEmail]:
        """Remove duplicate emails, keeping highest confidence."""
        seen: dict = {}
        for email in emails:
            key = email.email.lower()
            if key not in seen:
                seen[key] = email
            else:
                # Keep higher confidence
                existing = seen[key]
                if self._confidence_rank(email.confidence) > self._confidence_rank(existing.confidence):
                    seen[key] = email
        return list(seen.values())
    
    def _confidence_rank(self, confidence: ConfidenceLevel) -> int:
        """Convert confidence to numeric rank."""
        ranks = {
            ConfidenceLevel.HIGH: 3,
            ConfidenceLevel.MEDIUM: 2,
            ConfidenceLevel.LOW: 1,
        }
        return ranks.get(confidence, 0)


def extract_emails_from_text(
    text: str,
    source_url: str,
    company_domain: Optional[str] = None
) -> List[ExtractedEmail]:
    """Convenience function to extract emails from text."""
    extractor = EmailExtractor(company_domain)
    return extractor.extract_all(text, source_url, company_domain)


def get_domain_from_url(url: str) -> Optional[str]:
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # Remove www prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except Exception:
        return None
