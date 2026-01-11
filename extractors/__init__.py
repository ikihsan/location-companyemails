"""
Email extraction package.
"""

from .email_extractor import (
    EmailExtractor,
    extract_emails_from_text,
    get_domain_from_url,
)

from .smart_hr_extractor import (
    SmartHREmailExtractor,
    get_smart_extractor,
)

__all__ = [
    'EmailExtractor',
    'extract_emails_from_text',
    'get_domain_from_url',
    'SmartHREmailExtractor',
    'get_smart_extractor',
]
