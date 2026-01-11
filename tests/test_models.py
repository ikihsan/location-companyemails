"""
Unit tests for the Company model.
"""

import pytest
from datetime import datetime

from models import (
    Company, 
    ExtractedEmail, 
    ExtractionMethod, 
    ConfidenceLevel,
    CrawlResult,
)


class TestExtractedEmail:
    """Tests for ExtractedEmail model."""
    
    def test_email_creation(self):
        """Test creating an email object."""
        email = ExtractedEmail(
            email="test@company.com",
            source_url="https://company.com",
            extraction_method=ExtractionMethod.MAILTO_LINK,
            confidence=ConfidenceLevel.HIGH,
            domain_matches_company=True,
        )
        
        assert email.email == "test@company.com"
        assert email.confidence == ConfidenceLevel.HIGH
        assert email.domain_matches_company is True
    
    def test_email_hash(self):
        """Test email hash generation."""
        email = ExtractedEmail(
            email="test@company.com",
            source_url="https://company.com",
            extraction_method=ExtractionMethod.REGEX_PLAIN,
            confidence=ConfidenceLevel.MEDIUM,
            domain_matches_company=True,
        )
        
        hash1 = email.get_hash()
        assert len(hash1) == 16
        
        # Same email, same URL should produce same hash
        email2 = ExtractedEmail(
            email="TEST@COMPANY.COM",  # Different case
            source_url="https://company.com",
            extraction_method=ExtractionMethod.MAILTO_LINK,
            confidence=ConfidenceLevel.HIGH,
            domain_matches_company=True,
        )
        
        # Hash should be case-insensitive for email
        assert email.get_hash() == email2.get_hash()
    
    def test_email_to_dict(self):
        """Test serialization to dict."""
        email = ExtractedEmail(
            email="hr@startup.io",
            source_url="https://startup.io/contact",
            extraction_method=ExtractionMethod.JSON_PAYLOAD,
            confidence=ConfidenceLevel.HIGH,
            domain_matches_company=True,
            is_hr_contact=True,
            context="Apply for jobs"
        )
        
        data = email.to_dict()
        
        assert data['email'] == "hr@startup.io"
        assert data['extraction_method'] == "json_payload"
        assert data['confidence'] == "high"
        assert data['is_hr_contact'] is True
    
    def test_email_from_dict(self):
        """Test deserialization from dict."""
        data = {
            'email': 'jobs@tech.com',
            'source_url': 'https://tech.com',
            'extraction_method': 'mailto_link',
            'confidence': 'high',
            'domain_matches_company': True,
            'is_hr_contact': True,
            'context': '',
            'discovered_at': '2025-01-10T12:00:00',
        }
        
        email = ExtractedEmail.from_dict(data)
        
        assert email.email == 'jobs@tech.com'
        assert email.extraction_method == ExtractionMethod.MAILTO_LINK
        assert email.confidence == ConfidenceLevel.HIGH


class TestCompany:
    """Tests for Company model."""
    
    def test_company_creation(self):
        """Test creating a company object."""
        company = Company(
            name="Tech Startup GmbH",
            location="Berlin, Germany",
            source_url="https://techstartup.com",
            hiring_roles=["Backend Developer", "Frontend Developer"]
        )
        
        assert company.name == "Tech Startup GmbH"
        assert company.location == "Berlin, Germany"
        assert len(company.hiring_roles) == 2
    
    def test_company_hash(self):
        """Test company hash for deduplication."""
        company1 = Company(
            name="Test Company",
            location="Berlin",
            source_url="https://test.com"
        )
        company2 = Company(
            name="Test Company",
            location="Berlin",
            source_url="https://different.com"
        )
        
        # Same name and location should produce same hash
        assert company1.get_hash() == company2.get_hash()
    
    def test_add_email(self):
        """Test adding emails to company."""
        company = Company(
            name="Email Test",
            location="Munich",
            source_url="https://emailtest.com"
        )
        
        email = ExtractedEmail(
            email="contact@emailtest.com",
            source_url="https://emailtest.com",
            extraction_method=ExtractionMethod.MAILTO_LINK,
            confidence=ConfidenceLevel.HIGH,
            domain_matches_company=True,
        )
        
        result = company.add_email(email)
        assert result is True
        assert len(company.emails) == 1
        
        # Adding same email should not duplicate
        result2 = company.add_email(email)
        assert result2 is False
        assert len(company.emails) == 1
    
    def test_get_best_hr_contact(self):
        """Test finding best HR contact."""
        company = Company(
            name="HR Test",
            location="Hamburg",
            source_url="https://hrtest.com"
        )
        
        # Add general email
        company.add_email(ExtractedEmail(
            email="info@hrtest.com",
            source_url="https://hrtest.com",
            extraction_method=ExtractionMethod.REGEX_PLAIN,
            confidence=ConfidenceLevel.MEDIUM,
            domain_matches_company=True,
        ))
        
        # Add HR email
        company.add_email(ExtractedEmail(
            email="careers@hrtest.com",
            source_url="https://hrtest.com/jobs",
            extraction_method=ExtractionMethod.MAILTO_LINK,
            confidence=ConfidenceLevel.HIGH,
            domain_matches_company=True,
            is_hr_contact=True,
        ))
        
        best = company.get_best_hr_contact()
        assert best is not None
        assert best.email == "careers@hrtest.com"
    
    def test_get_best_hr_contact_by_prefix(self):
        """Test HR detection by email prefix."""
        company = Company(
            name="Prefix Test",
            location="Berlin",
            source_url="https://prefix.com"
        )
        
        company.add_email(ExtractedEmail(
            email="info@prefix.com",
            source_url="https://prefix.com",
            extraction_method=ExtractionMethod.REGEX_PLAIN,
            confidence=ConfidenceLevel.MEDIUM,
            domain_matches_company=True,
        ))
        
        company.add_email(ExtractedEmail(
            email="hr@prefix.com",
            source_url="https://prefix.com/contact",
            extraction_method=ExtractionMethod.REGEX_PLAIN,
            confidence=ConfidenceLevel.MEDIUM,
            domain_matches_company=True,
        ))
        
        best = company.get_best_hr_contact()
        assert best is not None
        assert best.email == "hr@prefix.com"
    
    def test_merge_companies(self):
        """Test merging two company records."""
        company1 = Company(
            name="Merge Test",
            location="Berlin",
            source_url="https://merge.com",
            hiring_roles=["Developer"],
            website="https://merge.com",
        )
        
        company2 = Company(
            name="Merge Test",
            location="Berlin",
            source_url="https://merge.com/jobs",
            hiring_roles=["Designer"],
            linkedin_url="https://linkedin.com/company/merge",
        )
        
        company2.add_email(ExtractedEmail(
            email="jobs@merge.com",
            source_url="https://merge.com/jobs",
            extraction_method=ExtractionMethod.MAILTO_LINK,
            confidence=ConfidenceLevel.HIGH,
            domain_matches_company=True,
        ))
        
        company1.merge_with(company2)
        
        assert "Developer" in company1.hiring_roles
        assert "Designer" in company1.hiring_roles
        assert company1.linkedin_url == "https://linkedin.com/company/merge"
        assert len(company1.emails) == 1
    
    def test_company_to_dict(self):
        """Test serialization to dict."""
        company = Company(
            name="Serial Test",
            location="Munich",
            source_url="https://serial.com",
            hiring_roles=["Engineer"],
        )
        
        data = company.to_dict()
        
        assert data['name'] == "Serial Test"
        assert data['location'] == "Munich"
        assert 'discovered_at' in data
    
    def test_company_from_dict(self):
        """Test deserialization from dict."""
        data = {
            'name': 'Deserial Test',
            'location': 'Hamburg',
            'source_url': 'https://deserial.com',
            'hiring_roles': ['Dev'],
            'job_description_snippet': 'Great job',
            'emails': [],
            'careers_url': None,
            'linkedin_url': None,
            'website': 'https://deserial.com',
            'crawl_depth': 2,
            'http_status': 200,
            'discovered_at': '2025-01-10T10:00:00',
            'last_updated': '2025-01-10T11:00:00',
            'metadata': {},
        }
        
        company = Company.from_dict(data)
        
        assert company.name == 'Deserial Test'
        assert company.crawl_depth == 2


class TestCrawlResult:
    """Tests for CrawlResult model."""
    
    def test_successful_result(self):
        """Test successful crawl result."""
        result = CrawlResult(
            url="https://example.com",
            status_code=200,
            content_type="text/html",
            html_content="<html></html>",
        )
        
        assert result.success is True
    
    def test_failed_result(self):
        """Test failed crawl result."""
        result = CrawlResult(
            url="https://example.com",
            status_code=404,
            content_type="",
            error="Not found",
        )
        
        assert result.success is False
    
    def test_error_result(self):
        """Test error crawl result."""
        result = CrawlResult(
            url="https://example.com",
            status_code=200,
            content_type="text/html",
            error="Timeout",
        )
        
        assert result.success is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
