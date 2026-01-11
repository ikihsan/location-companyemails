"""
Unit tests for the data storage and deduplication modules.
"""

import pytest
import json
import csv
from pathlib import Path
from datetime import datetime
import tempfile
import shutil

from storage.data_storage import DataStorage, CompanyDeduplicator, ManifestEntry
from models import Company, ExtractedEmail, ExtractionMethod, ConfidenceLevel


class TestCompanyDeduplicator:
    """Tests for company deduplication."""
    
    def setup_method(self):
        """Setup for each test."""
        self.deduplicator = CompanyDeduplicator()
    
    def test_is_not_duplicate_new_company(self):
        """Test that new company is not marked as duplicate."""
        company = Company(
            name="Test Company",
            location="Berlin, Germany",
            source_url="https://test.com"
        )
        
        assert self.deduplicator.is_duplicate(company) is False
    
    def test_is_duplicate_same_company(self):
        """Test that same company is marked as duplicate after adding."""
        company = Company(
            name="Test Company",
            location="Berlin, Germany",
            source_url="https://test.com"
        )
        
        self.deduplicator.add(company)
        assert self.deduplicator.is_duplicate(company) is True
    
    def test_normalized_name_matching(self):
        """Test that companies with similar names are detected."""
        company1 = Company(
            name="Test Company GmbH",
            location="Berlin",
            source_url="https://test.com"
        )
        company2 = Company(
            name="Test Company",
            location="Berlin",
            source_url="https://test2.com"
        )
        
        self.deduplicator.add(company1)
        assert self.deduplicator.is_duplicate(company2) is True
    
    def test_different_companies_not_duplicate(self):
        """Test that different companies are not marked as duplicate."""
        company1 = Company(
            name="Alpha Corp",
            location="Berlin",
            source_url="https://alpha.com"
        )
        company2 = Company(
            name="Beta Inc",
            location="Berlin",
            source_url="https://beta.com"
        )
        
        self.deduplicator.add(company1)
        assert self.deduplicator.is_duplicate(company2) is False
    
    def test_suffix_normalization(self):
        """Test that company suffixes are normalized."""
        company1 = Company(
            name="Startup Inc.",
            location="NYC",
            source_url="https://startup.com"
        )
        company2 = Company(
            name="Startup LLC",
            location="NYC",
            source_url="https://startup.io"
        )
        
        self.deduplicator.add(company1)
        assert self.deduplicator.is_duplicate(company2) is True


class TestDataStorage:
    """Tests for data storage functionality."""
    
    def setup_method(self):
        """Setup temp directory for each test."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.storage = DataStorage(output_dir=self.temp_dir)
    
    def teardown_method(self):
        """Cleanup temp directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_add_company(self):
        """Test adding a single company."""
        company = Company(
            name="Test Co",
            location="Berlin",
            source_url="https://test.com"
        )
        
        result = self.storage.add_company(company)
        assert result is True
        assert self.storage.get_company_count() == 1
    
    def test_add_duplicate_company(self):
        """Test that duplicate companies are merged."""
        company1 = Company(
            name="Test Co",
            location="Berlin",
            source_url="https://test.com",
            hiring_roles=["Developer"]
        )
        company2 = Company(
            name="Test Co",
            location="Berlin",
            source_url="https://test.com/jobs",
            hiring_roles=["Designer"]
        )
        
        self.storage.add_company(company1)
        result = self.storage.add_company(company2)
        
        assert result is False  # Should merge, not add new
        assert self.storage.get_company_count() == 1
        
        # Check roles were merged
        companies = self.storage.get_companies()
        assert "Developer" in companies[0].hiring_roles
        assert "Designer" in companies[0].hiring_roles
    
    def test_add_multiple_companies(self):
        """Test adding multiple companies."""
        companies = [
            Company(name=f"Company {i}", location="Berlin", source_url=f"https://c{i}.com")
            for i in range(5)
        ]
        
        new_count = self.storage.add_companies(companies)
        assert new_count == 5
        assert self.storage.get_company_count() == 5
    
    def test_save_to_csv(self):
        """Test saving to CSV file."""
        company = Company(
            name="CSV Test Co",
            location="Munich",
            source_url="https://csvtest.com",
            website="https://csvtest.com",
            hiring_roles=["Engineer", "Designer"]
        )
        email = ExtractedEmail(
            email="hr@csvtest.com",
            source_url="https://csvtest.com",
            extraction_method=ExtractionMethod.MAILTO_LINK,
            confidence=ConfidenceLevel.HIGH,
            domain_matches_company=True,
            is_hr_contact=True,
        )
        company.add_email(email)
        
        self.storage.add_company(company)
        csv_path = self.storage.save_to_csv("Munich")
        
        assert csv_path.exists()
        assert csv_path.suffix == '.csv'
        
        # Verify content
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            assert len(rows) == 1
            assert rows[0]['company_name'] == "CSV Test Co"
            assert rows[0]['best_email'] == "hr@csvtest.com"
    
    def test_save_to_json(self):
        """Test saving to JSON file."""
        company = Company(
            name="JSON Test Co",
            location="Hamburg",
            source_url="https://jsontest.com",
        )
        
        self.storage.add_company(company)
        json_path = self.storage.save_to_json("Hamburg")
        
        assert json_path.exists()
        assert json_path.suffix == '.json'
        
        # Verify content
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            assert 'metadata' in data
            assert 'companies' in data
            assert len(data['companies']) == 1
            assert data['companies'][0]['name'] == "JSON Test Co"
    
    def test_manifest_created(self):
        """Test that manifest is created and updated."""
        company = Company(
            name="Manifest Test",
            location="Berlin",
            source_url="https://manifest.com"
        )
        
        self.storage.add_company(company)
        self.storage.save_to_csv()
        self.storage.save_to_json()
        
        manifest_path = self.temp_dir / 'manifest.json'
        assert manifest_path.exists()
        
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
            
            assert 'entries' in manifest
            assert len(manifest['entries']) == 2  # CSV and JSON
    
    def test_flush_partial(self):
        """Test flushing partial results."""
        company = Company(
            name="Partial Test",
            location="Berlin",
            source_url="https://partial.com"
        )
        
        self.storage.add_company(company)
        files = self.storage.flush_partial("Berlin")
        
        assert 'csv' in files
        assert 'json' in files
        assert files['csv'].exists()
        assert files['json'].exists()
        assert 'partial' in files['csv'].name
    
    def test_clear_storage(self):
        """Test clearing stored data."""
        company = Company(
            name="Clear Test",
            location="Berlin",
            source_url="https://clear.com"
        )
        
        self.storage.add_company(company)
        assert self.storage.get_company_count() == 1
        
        self.storage.clear()
        assert self.storage.get_company_count() == 0


class TestManifestEntry:
    """Tests for manifest entry creation."""
    
    def test_manifest_entry_creation(self):
        """Test creating a manifest entry."""
        entry = ManifestEntry(
            filename="test.csv",
            format="csv",
            record_count=10,
            created_at=datetime.now().isoformat(),
            location="Berlin",
            checksum="abc123"
        )
        
        assert entry.filename == "test.csv"
        assert entry.format == "csv"
        assert entry.record_count == 10


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
