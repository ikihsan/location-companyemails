"""
Data models for the company scraper.
Defines Company, Email, and related entities with deduplication support.
"""

import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


class ExtractionMethod(Enum):
    """How an email was extracted."""
    REGEX_PLAIN = "regex_plain"
    REGEX_OBFUSCATED = "regex_obfuscated"
    MAILTO_LINK = "mailto_link"
    JSON_PAYLOAD = "json_payload"
    CONTACT_FORM = "contact_form"
    LINKEDIN_CARD = "linkedin_card"
    API_RESPONSE = "api_response"
    META_TAG = "meta_tag"


class ConfidenceLevel(Enum):
    """Confidence score for extracted emails."""
    HIGH = "high"      # Direct mailto or verified format
    MEDIUM = "medium"  # Regex match, domain matches
    LOW = "low"        # Obfuscated or domain mismatch


@dataclass
class ExtractedEmail:
    """Represents an extracted email with metadata."""
    email: str
    source_url: str
    extraction_method: ExtractionMethod
    confidence: ConfidenceLevel
    domain_matches_company: bool
    is_hr_contact: bool = False
    context: str = ""  # Surrounding text for context
    discovered_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'email': self.email,
            'source_url': self.source_url,
            'extraction_method': self.extraction_method.value,
            'confidence': self.confidence.value,
            'domain_matches_company': self.domain_matches_company,
            'is_hr_contact': self.is_hr_contact,
            'context': self.context,
            'discovered_at': self.discovered_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExtractedEmail':
        return cls(
            email=data['email'],
            source_url=data['source_url'],
            extraction_method=ExtractionMethod(data['extraction_method']),
            confidence=ConfidenceLevel(data['confidence']),
            domain_matches_company=data['domain_matches_company'],
            is_hr_contact=data.get('is_hr_contact', False),
            context=data.get('context', ''),
            discovered_at=datetime.fromisoformat(data['discovered_at']),
        )
    
    def get_hash(self) -> str:
        """Generate stable hash for deduplication."""
        content = f"{self.email.lower()}:{self.source_url}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class Company:
    """Represents a discovered company with all metadata."""
    name: str
    location: str
    source_url: str
    hiring_roles: List[str] = field(default_factory=list)
    job_description_snippet: str = ""
    emails: List[ExtractedEmail] = field(default_factory=list)
    careers_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    website: Optional[str] = None
    crawl_depth: int = 0
    http_status: int = 200
    discovered_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'location': self.location,
            'source_url': self.source_url,
            'hiring_roles': self.hiring_roles,
            'job_description_snippet': self.job_description_snippet,
            'emails': [e.to_dict() for e in self.emails],
            'careers_url': self.careers_url,
            'linkedin_url': self.linkedin_url,
            'website': self.website,
            'crawl_depth': self.crawl_depth,
            'http_status': self.http_status,
            'discovered_at': self.discovered_at.isoformat(),
            'last_updated': self.last_updated.isoformat(),
            'metadata': self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Company':
        emails = [ExtractedEmail.from_dict(e) for e in data.get('emails', [])]
        return cls(
            name=data['name'],
            location=data['location'],
            source_url=data['source_url'],
            hiring_roles=data.get('hiring_roles', []),
            job_description_snippet=data.get('job_description_snippet', ''),
            emails=emails,
            careers_url=data.get('careers_url'),
            linkedin_url=data.get('linkedin_url'),
            website=data.get('website'),
            crawl_depth=data.get('crawl_depth', 0),
            http_status=data.get('http_status', 200),
            discovered_at=datetime.fromisoformat(data['discovered_at']),
            last_updated=datetime.fromisoformat(data['last_updated']),
            metadata=data.get('metadata', {}),
        )
    
    def get_hash(self) -> str:
        """Generate stable hash for deduplication based on name and location."""
        normalized_name = self.name.lower().strip()
        normalized_location = self.location.lower().strip()
        content = f"{normalized_name}:{normalized_location}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def get_best_hr_contact(self) -> Optional[ExtractedEmail]:
        """Return the best HR contact email if available."""
        # Priority: marked as HR > high confidence > medium confidence
        hr_emails = [e for e in self.emails if e.is_hr_contact]
        if hr_emails:
            return sorted(hr_emails, key=lambda e: e.confidence.value)[0]
        
        # Look for HR-related patterns
        hr_patterns = ['hr@', 'jobs@', 'careers@', 'recruiting@', 'talent@', 'hiring@', 'people@']
        for email in self.emails:
            if any(pattern in email.email.lower() for pattern in hr_patterns):
                return email
        
        # Return highest confidence email
        if self.emails:
            sorted_emails = sorted(
                self.emails, 
                key=lambda e: (e.confidence == ConfidenceLevel.HIGH, e.domain_matches_company),
                reverse=True
            )
            return sorted_emails[0]
        return None
    
    def add_email(self, email: ExtractedEmail) -> bool:
        """Add email if not duplicate, returns True if added."""
        email_hash = email.get_hash()
        for existing in self.emails:
            if existing.get_hash() == email_hash:
                return False
        self.emails.append(email)
        self.last_updated = datetime.utcnow()
        return True
    
    def merge_with(self, other: 'Company') -> None:
        """Merge another company's data into this one."""
        # Merge roles
        for role in other.hiring_roles:
            if role not in self.hiring_roles:
                self.hiring_roles.append(role)
        
        # Merge emails
        for email in other.emails:
            self.add_email(email)
        
        # Update URLs if missing
        if not self.careers_url and other.careers_url:
            self.careers_url = other.careers_url
        if not self.linkedin_url and other.linkedin_url:
            self.linkedin_url = other.linkedin_url
        if not self.website and other.website:
            self.website = other.website
        
        # Extend job description
        if other.job_description_snippet and other.job_description_snippet not in self.job_description_snippet:
            self.job_description_snippet = f"{self.job_description_snippet} | {other.job_description_snippet}"[:500]
        
        self.last_updated = datetime.utcnow()


@dataclass 
class CrawlResult:
    """Result from crawling a single URL."""
    url: str
    status_code: int
    content_type: str
    html_content: Optional[str] = None
    emails_found: List[ExtractedEmail] = field(default_factory=list)
    links_found: List[str] = field(default_factory=list)
    error: Optional[str] = None
    crawl_time_ms: float = 0.0
    
    @property
    def success(self) -> bool:
        return self.status_code == 200 and self.error is None


@dataclass
class DiscoverySource:
    """Represents a job board or company discovery source."""
    name: str
    base_url: str
    source_type: str  # 'job_board', 'directory', 'social'
    requires_js: bool = False
    rate_limit_per_minute: int = 30
    enabled: bool = True
