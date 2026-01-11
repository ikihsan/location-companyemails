"""
Smart HR Email Extractor - Only extracts actionable recruiting emails.
Filters out support@, info@, privacy@, noreply@ and other non-recruiter emails.
Prioritizes hr@, careers@, jobs@, recruiting@, talent@ emails.
"""

import re
from typing import List, Optional, Set, Tuple, Dict
from dataclasses import dataclass, field
from models import ExtractedEmail, ConfidenceLevel, ExtractionMethod


@dataclass
class EmailScore:
    """Scoring for email relevance."""
    email: str
    score: int = 0
    reasons: List[str] = field(default_factory=list)
    is_hr: bool = False
    is_recruiter: bool = False
    is_rejected: bool = False


class SmartHREmailExtractor:
    """
    Intelligent email extractor that only keeps emails useful for job applications.
    Prioritizes HR/recruiting emails and filters out generic/support emails.
    """
    
    # =========================================================================
    # EMAIL PATTERNS TO ACCEPT (High Priority)
    # =========================================================================
    
    # HR/Recruiting prefixes (local part before @)
    HR_PREFIXES = {
        # Highest priority - direct HR
        'hr': 100,
        'jobs': 95,
        'careers': 95,
        'recruiting': 90,
        'recruitment': 90,
        'talent': 85,
        'hiring': 85,
        'apply': 80,
        'joinus': 80,
        'join': 75,
        'work': 70,
        'opportunities': 70,
        'employment': 70,
        'people': 65,
        'team': 60,
        'staffing': 60,
        
        # Named recruiters (first names common for HR)
        'recruiter': 90,
        'hr-team': 90,
        'hr_team': 90,
        'hrteam': 90,
        'career': 85,
        'campus': 75,
        'internship': 70,
        'interns': 70,
        
        # Regional HR
        'hr.india': 95,
        'hr-india': 95,
        'india.hr': 95,
        'india-hr': 95,
        'hr.hyderabad': 95,
        'hr.bangalore': 95,
        'hr.mumbai': 95,
        'hr.delhi': 95,
    }
    
    # Person name patterns (likely a real person, not support)
    PERSON_NAME_PATTERNS = [
        r'^[a-z]{2,12}\.[a-z]{2,15}@',  # firstname.lastname@
        r'^[a-z]{2,12}_[a-z]{2,15}@',   # firstname_lastname@
        r'^[a-z]{2,15}[0-9]{0,3}@',     # firstnameNNN@ (might be real person)
    ]
    
    # Context patterns that indicate HR page
    HR_PAGE_INDICATORS = [
        r'career', r'job', r'hiring', r'recruit', r'join\s+us', r'work\s+with',
        r'apply\s+now', r'open\s+position', r'vacancy', r'opportunities',
        r'talent', r'human\s+resource', r'we.re\s+hiring', r'team',
    ]
    
    # =========================================================================
    # EMAIL PATTERNS TO REJECT (Low Priority / Useless)
    # =========================================================================
    
    # Support/Generic prefixes that won't help job seekers
    REJECTED_PREFIXES = {
        # Generic support (useless for jobs)
        'support', 'help', 'helpdesk', 'service', 'customerservice',
        'customersupport', 'techsupport', 'tech-support', 'tech_support',
        'contact', 'feedback', 'enquiry', 'enquiries', 'inquiry',
        'queries', 'query', 'ask', 'hello', 'hi',
        
        # System/automated (never respond)
        'noreply', 'no-reply', 'no_reply', 'donotreply', 'do-not-reply',
        'mailer', 'mailer-daemon', 'postmaster', 'webmaster', 'hostmaster',
        'admin', 'administrator', 'root', 'system', 'automated', 'auto',
        'notification', 'notifications', 'alert', 'alerts', 'bot',
        'newsletter', 'news', 'updates', 'marketing', 'promo', 'promotions',
        'unsubscribe', 'bounce', 'spam', 'abuse',
        
        # Privacy/Legal (won't help)
        'privacy', 'privacysupport', 'legal', 'compliance', 'gdpr', 'dpo',
        'dataprotection', 'data-protection', 'security', 'infosec',
        
        # Sales (not HR)
        'sales', 'billing', 'accounts', 'invoice', 'payment', 'payments',
        'orders', 'order', 'shop', 'store', 'buy', 'purchase',
        
        # General info (rarely responds personally)
        'info', 'information', 'general', 'office', 'reception',
        'media', 'press', 'pr', 'communications', 'comm',
        
        # Technical (not HR)
        'dev', 'developer', 'devops', 'engineering', 'api', 'sdk',
        'bugs', 'issues', 'github', 'git', 'code',
        'partners', 'partnership', 'partner', 'vendor', 'vendors',
        'demo', 'trial', 'signup', 'register', 'subscribe',
    }
    
    # Domains that never have useful HR contacts
    REJECTED_DOMAINS = {
        # Job boards (scraped from, but their emails are useless)
        'indeed.com', 'glassdoor.com', 'linkedin.com', 'naukri.com',
        'monster.com', 'shine.com', 'timesjobs.com', 'careerbuilder.com',
        'ziprecruiter.com', 'simplyhired.com', 'dice.com', 'wellfound.com',
        'instahyre.com', 'cutshort.io', 'hirist.tech', 'angel.co',
        
        # Generic email providers (personal emails, not company HR)
        'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
        'live.com', 'aol.com', 'mail.com', 'protonmail.com',
        'icloud.com', 'msn.com', 'ymail.com', 'rediffmail.com',
        
        # Test/placeholder
        'example.com', 'example.org', 'test.com', 'localhost',
        'mailinator.com', 'tempmail.com', 'throwaway.email',
        'guerrillamail.com', 'fakeinbox.com',
        
        # Service providers
        'sentry.io', 'github.com', 'atlassian.com', 'slack.com',
        'zendesk.com', 'freshdesk.com', 'intercom.com', 'hubspot.com',
        'salesforce.com', 'mailchimp.com', 'sendgrid.com',
        
        # Protection services
        'shl.com',  # Talent assessment, not real HR
        'taleo.com', 'workday.com',  # HR systems, not company HR
        'icims.com', 'lever.co', 'greenhouse.io', 'bamboohr.com',
    }
    
    # Image/file patterns in emails (false positives)
    FILE_PATTERNS = [
        r'\.png$', r'\.jpg$', r'\.jpeg$', r'\.gif$', r'\.svg$',
        r'\.webp$', r'\.ico$', r'\.pdf$', r'\.doc$', r'\.docx$',
        r'@\d+x\.', r'@2x', r'@3x',  # Image scaling
    ]
    
    # =========================================================================
    # MAIN EXTRACTION METHODS
    # =========================================================================
    
    EMAIL_REGEX = re.compile(
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        re.IGNORECASE
    )
    
    MAILTO_REGEX = re.compile(
        r'mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        re.IGNORECASE
    )
    
    def __init__(self, company_domain: Optional[str] = None):
        self.company_domain = company_domain
        self._file_patterns = [re.compile(p, re.IGNORECASE) for p in self.FILE_PATTERNS]
    
    def extract_hr_emails(
        self,
        content: str,
        source_url: str,
        company_name: Optional[str] = None,
        company_domain: Optional[str] = None
    ) -> List[ExtractedEmail]:
        """
        Extract only HR/recruiting emails from content.
        Returns sorted list with best emails first.
        """
        if company_domain:
            self.company_domain = company_domain
        
        # Check if page is HR-related
        is_hr_page = self._is_hr_related_page(content)
        
        # Extract all potential emails
        all_emails = self._extract_all_emails(content)
        
        # Score and filter
        scored_emails: List[EmailScore] = []
        seen: Set[str] = set()
        
        for email in all_emails:
            email_lower = email.lower()
            
            # Skip duplicates
            if email_lower in seen:
                continue
            seen.add(email_lower)
            
            # Score the email
            score = self._score_email(email_lower, is_hr_page)
            
            # Only keep non-rejected emails with positive scores
            if not score.is_rejected and score.score > 0:
                scored_emails.append(score)
        
        # Sort by score (highest first)
        scored_emails.sort(key=lambda x: x.score, reverse=True)
        
        # Convert to ExtractedEmail objects
        results = []
        for scored in scored_emails[:20]:  # Max 20 emails per page
            confidence = self._score_to_confidence(scored.score)
            extracted = ExtractedEmail(
                email=scored.email,
                source_url=source_url,
                confidence=confidence,
                is_hr_contact=scored.is_hr,
                extraction_method=ExtractionMethod.MAILTO if 'mailto' in str(scored.reasons) else ExtractionMethod.REGEX,
            )
            results.append(extracted)
        
        return results
    
    def _extract_all_emails(self, content: str) -> List[str]:
        """Extract all email-like strings from content."""
        emails = []
        
        # Mailto links (higher quality)
        for match in self.MAILTO_REGEX.finditer(content):
            emails.append(match.group(1))
        
        # Plain regex
        for match in self.EMAIL_REGEX.finditer(content):
            emails.append(match.group())
        
        return emails
    
    def _score_email(self, email: str, is_hr_page: bool) -> EmailScore:
        """Score an email based on how useful it is for job applications."""
        score = EmailScore(email=email)
        
        try:
            local_part, domain = email.rsplit('@', 1)
        except ValueError:
            score.is_rejected = True
            score.reasons.append("Invalid format")
            return score
        
        local_lower = local_part.lower()
        domain_lower = domain.lower()
        
        # =====================================================================
        # REJECTION CHECKS (Email is useless)
        # =====================================================================
        
        # Check rejected domains
        for rejected_domain in self.REJECTED_DOMAINS:
            if rejected_domain in domain_lower:
                score.is_rejected = True
                score.reasons.append(f"Rejected domain: {rejected_domain}")
                return score
        
        # Check rejected prefixes
        for prefix in self.REJECTED_PREFIXES:
            if local_lower == prefix or local_lower.startswith(f"{prefix}.") or local_lower.startswith(f"{prefix}_"):
                score.is_rejected = True
                score.reasons.append(f"Rejected prefix: {prefix}")
                return score
        
        # Check file patterns
        for pattern in self._file_patterns:
            if pattern.search(email):
                score.is_rejected = True
                score.reasons.append("File pattern")
                return score
        
        # Too short or too long local parts
        if len(local_part) < 2 or len(local_part) > 50:
            score.is_rejected = True
            score.reasons.append("Invalid length")
            return score
        
        # =====================================================================
        # POSITIVE SCORING (Email is useful)
        # =====================================================================
        
        # HR prefixes (highest priority)
        for prefix, prefix_score in self.HR_PREFIXES.items():
            if local_lower == prefix or local_lower.startswith(f"{prefix}.") or local_lower.startswith(f"{prefix}@"):
                score.score += prefix_score
                score.is_hr = True
                score.reasons.append(f"HR prefix: {prefix}")
                break
            if prefix in local_lower:
                score.score += prefix_score // 2
                score.is_hr = True
                score.reasons.append(f"Contains HR keyword: {prefix}")
        
        # Page context boost
        if is_hr_page:
            score.score += 30
            score.reasons.append("On HR page")
        
        # Company domain match boost
        if self.company_domain:
            if domain_lower == self.company_domain or domain_lower.endswith(f".{self.company_domain}"):
                score.score += 50
                score.reasons.append("Matches company domain")
        
        # Person name patterns (likely real person)
        for pattern in self.PERSON_NAME_PATTERNS:
            if re.match(pattern, email, re.IGNORECASE):
                score.score += 40
                score.is_recruiter = True
                score.reasons.append("Person name pattern")
                break
        
        # .in domain (Indian companies)
        if domain_lower.endswith('.in') or domain_lower.endswith('.co.in'):
            score.score += 10
            score.reasons.append("Indian domain")
        
        # Corporate domain (not free email)
        if not any(free in domain_lower for free in ['gmail', 'yahoo', 'hotmail', 'outlook']):
            score.score += 20
            score.reasons.append("Corporate domain")
        
        # If nothing else, give base score for being a valid email
        if score.score == 0 and not score.is_rejected:
            score.score = 10
            score.reasons.append("Valid corporate email")
        
        return score
    
    def _is_hr_related_page(self, content: str) -> bool:
        """Check if the page content is related to HR/careers."""
        content_lower = content.lower()
        
        hr_count = 0
        for pattern in self.HR_PAGE_INDICATORS:
            if re.search(pattern, content_lower):
                hr_count += 1
        
        return hr_count >= 2  # At least 2 HR indicators
    
    def _score_to_confidence(self, score: int) -> ConfidenceLevel:
        """Convert numeric score to confidence level."""
        if score >= 100:
            return ConfidenceLevel.HIGH
        elif score >= 50:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW
    
    def get_best_email(self, emails: List[ExtractedEmail]) -> Optional[ExtractedEmail]:
        """Get the single best email from a list."""
        if not emails:
            return None
        
        # Sort by confidence and HR status
        def sort_key(e: ExtractedEmail) -> Tuple[int, int]:
            conf_score = {ConfidenceLevel.HIGH: 3, ConfidenceLevel.MEDIUM: 2, ConfidenceLevel.LOW: 1}.get(e.confidence, 0)
            hr_score = 1 if e.is_hr_contact else 0
            return (conf_score, hr_score)
        
        sorted_emails = sorted(emails, key=sort_key, reverse=True)
        return sorted_emails[0]


# Global instance
_smart_extractor: Optional[SmartHREmailExtractor] = None

def get_smart_extractor() -> SmartHREmailExtractor:
    """Get singleton instance of SmartHREmailExtractor."""
    global _smart_extractor
    if _smart_extractor is None:
        _smart_extractor = SmartHREmailExtractor()
    return _smart_extractor
