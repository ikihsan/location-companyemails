"""
Unit tests for the email extraction module.
"""

import pytest
from extractors.email_extractor import (
    EmailExtractor,
    extract_emails_from_text,
    get_domain_from_url,
)
from models import ExtractionMethod, ConfidenceLevel


class TestEmailExtractor:
    """Tests for EmailExtractor class."""
    
    def setup_method(self):
        """Setup for each test."""
        self.extractor = EmailExtractor(company_domain='example.com')
    
    def test_extract_plain_email(self):
        """Test extraction of plain email addresses."""
        content = "Contact us at hello@example.com for more information."
        emails = self.extractor.extract_all(content, "https://example.com")
        
        assert len(emails) >= 1
        assert any(e.email == 'hello@example.com' for e in emails)
    
    def test_extract_mailto_link(self):
        """Test extraction from mailto: links."""
        content = '<a href="mailto:jobs@company.com">Email us</a>'
        emails = self.extractor.extract_all(content, "https://company.com")
        
        assert len(emails) >= 1
        email = next((e for e in emails if e.email == 'jobs@company.com'), None)
        assert email is not None
        assert email.extraction_method == ExtractionMethod.MAILTO_LINK
        assert email.confidence == ConfidenceLevel.HIGH
    
    def test_extract_obfuscated_at_dot(self):
        """Test extraction of 'at' and 'dot' obfuscated emails."""
        content = "Email: contact [at] company [dot] com"
        emails = self.extractor.extract_all(content, "https://company.com")
        
        assert len(emails) >= 1
        assert any(e.email == 'contact@company.com' for e in emails)
    
    def test_extract_obfuscated_parentheses(self):
        """Test extraction of parentheses obfuscated emails."""
        content = "Reach us at info(at)startup(dot)io"
        emails = self.extractor.extract_all(content, "https://startup.io")
        
        assert len(emails) >= 1
        assert any(e.email == 'info@startup.io' for e in emails)
    
    def test_extract_from_json(self):
        """Test extraction from JSON payloads."""
        content = '{"contact": {"email": "support@tech.com", "phone": "123"}}'
        emails = self.extractor.extract_all(content, "https://tech.com")
        
        assert len(emails) >= 1
        email = next((e for e in emails if e.email == 'support@tech.com'), None)
        assert email is not None
        assert email.extraction_method == ExtractionMethod.JSON_PAYLOAD
    
    def test_filter_invalid_emails(self):
        """Test that invalid emails are filtered."""
        content = """
        Valid: real@company.com
        Invalid: test@example.com
        Invalid: fake@localhost
        Invalid: image@2x.png
        """
        emails = self.extractor.extract_all(content, "https://company.com")
        
        # Should not include example.com, localhost, or image patterns
        email_addresses = [e.email for e in emails]
        assert 'test@example.com' not in email_addresses
        assert 'fake@localhost' not in email_addresses
        assert 'image@2x.png' not in email_addresses
    
    def test_domain_matching(self):
        """Test domain matching for confidence scoring."""
        extractor = EmailExtractor(company_domain='mycompany.com')
        content = "Contact: hr@mycompany.com or external@gmail.com"
        emails = extractor.extract_all(content, "https://mycompany.com")
        
        company_email = next((e for e in emails if e.email == 'hr@mycompany.com'), None)
        external_email = next((e for e in emails if e.email == 'external@gmail.com'), None)
        
        assert company_email is not None
        assert company_email.domain_matches_company is True
        
        if external_email:
            assert external_email.domain_matches_company is False
    
    def test_hr_detection(self):
        """Test HR contact detection."""
        content = """
        General: info@company.com
        HR: hr@company.com
        Jobs: careers@company.com
        """
        emails = self.extractor.extract_all(content, "https://company.com")
        
        hr_email = next((e for e in emails if e.email == 'hr@company.com'), None)
        careers_email = next((e for e in emails if e.email == 'careers@company.com'), None)
        info_email = next((e for e in emails if e.email == 'info@company.com'), None)
        
        assert hr_email is not None and hr_email.is_hr_contact is True
        assert careers_email is not None and careers_email.is_hr_contact is True
        if info_email:
            assert info_email.is_hr_contact is False
    
    def test_deduplication(self):
        """Test that duplicate emails are removed."""
        content = """
        Email: test@company.com
        Contact: test@company.com
        <a href="mailto:test@company.com">Mail</a>
        """
        emails = self.extractor.extract_all(content, "https://company.com")
        
        test_emails = [e for e in emails if e.email == 'test@company.com']
        assert len(test_emails) == 1
    
    def test_multiple_emails(self):
        """Test extraction of multiple different emails."""
        content = """
        Support: support@company.com
        Sales: sales@company.com
        HR: recruiting@company.com
        """
        emails = self.extractor.extract_all(content, "https://company.com")
        
        email_addresses = [e.email for e in emails]
        assert 'support@company.com' in email_addresses
        assert 'sales@company.com' in email_addresses
        assert 'recruiting@company.com' in email_addresses
    
    def test_context_extraction(self):
        """Test that context is extracted around emails."""
        content = "For job applications, please contact hr@startup.com or visit our careers page."
        emails = self.extractor.extract_all(content, "https://startup.com")
        
        email = next((e for e in emails if e.email == 'hr@startup.com'), None)
        assert email is not None
        assert 'job applications' in email.context.lower() or 'careers' in email.context.lower()


class TestDomainExtraction:
    """Tests for domain extraction utility."""
    
    def test_simple_domain(self):
        """Test simple domain extraction."""
        assert get_domain_from_url('https://example.com/path') == 'example.com'
    
    def test_www_prefix(self):
        """Test www prefix is removed."""
        assert get_domain_from_url('https://www.example.com') == 'example.com'
    
    def test_subdomain(self):
        """Test subdomain is preserved."""
        assert get_domain_from_url('https://jobs.example.com') == 'jobs.example.com'
    
    def test_port_handling(self):
        """Test URLs with ports."""
        result = get_domain_from_url('https://example.com:8080/path')
        assert 'example.com' in result
    
    def test_invalid_url(self):
        """Test invalid URL handling."""
        assert get_domain_from_url('not-a-url') is None or get_domain_from_url('not-a-url') == ''


class TestConvenienceFunction:
    """Tests for the convenience function."""
    
    def test_extract_emails_from_text(self):
        """Test the convenience function works."""
        text = "Contact support@test.com for help"
        emails = extract_emails_from_text(text, "https://test.com", "test.com")
        
        assert len(emails) >= 1
        assert any(e.email == 'support@test.com' for e in emails)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
