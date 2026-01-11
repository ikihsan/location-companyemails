"""
Storage module for persisting scraped data.
Handles CSV, JSON output with timestamped filenames and manifest.
"""

import csv
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any, Set
from dataclasses import dataclass, asdict

from models import Company, ExtractedEmail
from config import get_config
from utils import get_logger


@dataclass
class ManifestEntry:
    """Entry in the output manifest."""
    filename: str
    format: str
    record_count: int
    created_at: str
    location: str
    checksum: str


class DataStorage:
    """Handles data persistence to CSV and JSON files."""
    
    def __init__(self, output_dir: Optional[Path] = None):
        self.config = get_config()
        self.output_dir = output_dir or self.config.storage.output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger()
        
        self._companies: Dict[str, Company] = {}  # hash -> company
        self._manifest_path = self.output_dir / 'manifest.json'
        self._load_existing_manifest()
    
    def _load_existing_manifest(self):
        """Load existing manifest if present."""
        self.manifest: List[ManifestEntry] = []
        if self._manifest_path.exists():
            try:
                with open(self._manifest_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.manifest = [
                        ManifestEntry(**entry) for entry in data.get('entries', [])
                    ]
            except (json.JSONDecodeError, KeyError):
                self.manifest = []
    
    def add_company(self, company: Company) -> bool:
        """
        Add or merge a company. Returns True if new company added.
        """
        company_hash = company.get_hash()
        
        if company_hash in self._companies:
            # Merge with existing
            self._companies[company_hash].merge_with(company)
            return False
        else:
            self._companies[company_hash] = company
            return True
    
    def add_companies(self, companies: List[Company]) -> int:
        """Add multiple companies. Returns count of new companies."""
        new_count = 0
        for company in companies:
            if self.add_company(company):
                new_count += 1
        return new_count
    
    def get_companies(self) -> List[Company]:
        """Get all stored companies."""
        return list(self._companies.values())
    
    def get_company_count(self) -> int:
        """Get total company count."""
        return len(self._companies)
    
    def save_to_csv(self, location: str = "") -> Path:
        """Save companies to CSV file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        location_slug = self._slugify(location) if location else "all"
        filename = f"companies_{location_slug}_{timestamp}.csv"
        filepath = self.output_dir / filename
        
        companies = self.get_companies()
        
        if not companies:
            self.logger.warning("No companies to save")
            return filepath
        
        # Flatten company data for CSV
        rows = []
        for company in companies:
            best_email = company.get_best_hr_contact()
            all_emails = '; '.join([e.email for e in company.emails])
            
            row = {
                'company_name': company.name,
                'location': company.location,
                'website': company.website or '',
                'careers_url': company.careers_url or '',
                'linkedin_url': company.linkedin_url or '',
                'hiring_roles': '; '.join(company.hiring_roles),
                'best_email': best_email.email if best_email else '',
                'best_email_confidence': best_email.confidence.value if best_email else '',
                'all_emails': all_emails,
                'email_count': len(company.emails),
                'job_description': company.job_description_snippet[:200],
                'source_url': company.source_url,
                'crawl_depth': company.crawl_depth,
                'discovered_at': company.discovered_at.isoformat(),
            }
            rows.append(row)
        
        # Write CSV
        fieldnames = list(rows[0].keys()) if rows else []
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        
        # Update manifest
        checksum = self._compute_checksum(filepath)
        self.manifest.append(ManifestEntry(
            filename=filename,
            format='csv',
            record_count=len(rows),
            created_at=datetime.now().isoformat(),
            location=location,
            checksum=checksum,
        ))
        self._save_manifest()
        
        self.logger.info(f"Saved {len(rows)} companies to {filepath}")
        return filepath
    
    def save_to_json(self, location: str = "") -> Path:
        """Save companies to JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        location_slug = self._slugify(location) if location else "all"
        filename = f"companies_{location_slug}_{timestamp}.json"
        filepath = self.output_dir / filename
        
        companies = self.get_companies()
        
        data = {
            'metadata': {
                'created_at': datetime.now().isoformat(),
                'location': location,
                'total_companies': len(companies),
                'total_emails': sum(len(c.emails) for c in companies),
            },
            'companies': [c.to_dict() for c in companies],
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Update manifest
        checksum = self._compute_checksum(filepath)
        self.manifest.append(ManifestEntry(
            filename=filename,
            format='json',
            record_count=len(companies),
            created_at=datetime.now().isoformat(),
            location=location,
            checksum=checksum,
        ))
        self._save_manifest()
        
        self.logger.info(f"Saved {len(companies)} companies to {filepath}")
        return filepath
    
    def save_to_text(self, location: str = "") -> Path:
        """Save companies with emails to a clean, aligned text file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        location_slug = self._slugify(location) if location else "all"
        filename = f"company_emails_{location_slug}_{timestamp}.txt"
        filepath = self.output_dir / filename
        
        companies = self.get_companies()
        
        # Filter only companies with emails
        companies_with_emails = [c for c in companies if c.emails]
        
        if not companies_with_emails:
            self.logger.warning("No companies with emails to save")
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("No companies with emails found.\n")
            return filepath
        
        # Calculate max company name length for alignment
        max_name_len = max(len(c.name) for c in companies_with_emails)
        max_name_len = min(max_name_len, 50)  # Cap at 50 chars
        
        lines = []
        lines.append("=" * 80)
        lines.append(f"COMPANY EMAIL LIST - {location.upper() if location else 'ALL LOCATIONS'}")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Total Companies with Emails: {len(companies_with_emails)}")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"{'COMPANY NAME':<{max_name_len}}  |  EMAIL")
        lines.append("-" * 80)
        
        for company in sorted(companies_with_emails, key=lambda c: c.name.lower()):
            company_name = company.name[:max_name_len]  # Truncate if too long
            
            # Get unique emails for this company
            unique_emails = list(set(e.email for e in company.emails))
            
            # First email on same line as company
            if unique_emails:
                lines.append(f"{company_name:<{max_name_len}}  |  {unique_emails[0]}")
                
                # Additional emails on subsequent lines (indented)
                for email in unique_emails[1:]:
                    lines.append(f"{'':<{max_name_len}}  |  {email}")
        
        lines.append("")
        lines.append("-" * 80)
        lines.append(f"END OF LIST - {len(companies_with_emails)} companies")
        lines.append("=" * 80)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        self.logger.info(f"Saved {len(companies_with_emails)} companies with emails to {filepath}")
        return filepath
    
    def save_all(self, location: str = "") -> Dict[str, Path]:
        """Save to CSV, JSON, and text file."""
        return {
            'csv': self.save_to_csv(location),
            'json': self.save_to_json(location),
            'txt': self.save_to_text(location),
        }
    
    def flush_partial(self, location: str = "") -> Dict[str, Path]:
        """Flush current data to disk (for graceful shutdown)."""
        if not self._companies:
            return {}
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        location_slug = self._slugify(location) if location else "all"
        
        # Save partial results
        csv_path = self.output_dir / f"companies_{location_slug}_{timestamp}_partial.csv"
        json_path = self.output_dir / f"companies_{location_slug}_{timestamp}_partial.json"
        
        companies = self.get_companies()
        
        # Save JSON
        data = {
            'metadata': {
                'created_at': datetime.now().isoformat(),
                'location': location,
                'is_partial': True,
                'total_companies': len(companies),
            },
            'companies': [c.to_dict() for c in companies],
        }
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Save CSV
        rows = []
        for company in companies:
            best_email = company.get_best_hr_contact()
            row = {
                'company_name': company.name,
                'location': company.location,
                'website': company.website or '',
                'best_email': best_email.email if best_email else '',
                'all_emails': '; '.join([e.email for e in company.emails]),
                'source_url': company.source_url,
            }
            rows.append(row)
        
        if rows:
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)
        
        self.logger.info(f"Flushed {len(companies)} partial results to disk")
        
        return {'csv': csv_path, 'json': json_path}
    
    def _save_manifest(self):
        """Save the manifest file."""
        data = {
            'last_updated': datetime.now().isoformat(),
            'total_files': len(self.manifest),
            'entries': [asdict(entry) for entry in self.manifest],
        }
        
        with open(self._manifest_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    def _compute_checksum(self, filepath: Path) -> str:
        """Compute SHA256 checksum of a file."""
        sha256 = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()[:16]
    
    def _slugify(self, text: str) -> str:
        """Convert text to URL-friendly slug."""
        import re
        text = text.lower().strip()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[-\s]+', '_', text)
        return text[:50]
    
    def clear(self):
        """Clear all stored data."""
        self._companies.clear()


class CompanyDeduplicator:
    """Handles company deduplication across multiple sources."""
    
    def __init__(self):
        self._seen_hashes: Set[str] = set()
        self._company_names: Dict[str, str] = {}  # normalized name -> hash
    
    def is_duplicate(self, company: Company) -> bool:
        """Check if company is a duplicate."""
        company_hash = company.get_hash()
        
        if company_hash in self._seen_hashes:
            return True
        
        # Check by normalized name
        normalized = self._normalize_name(company.name)
        if normalized in self._company_names:
            return True
        
        return False
    
    def add(self, company: Company):
        """Add company to seen set."""
        company_hash = company.get_hash()
        self._seen_hashes.add(company_hash)
        
        normalized = self._normalize_name(company.name)
        self._company_names[normalized] = company_hash
    
    def _normalize_name(self, name: str) -> str:
        """Normalize company name for comparison."""
        import re
        name = name.lower().strip()
        # Remove common suffixes
        suffixes = ['gmbh', 'inc', 'ltd', 'llc', 'ag', 'se', 'ug', 'co', 'corp', 'corporation']
        for suffix in suffixes:
            name = re.sub(rf'\b{suffix}\b\.?', '', name)
        # Remove special characters
        name = re.sub(r'[^\w\s]', '', name)
        # Normalize whitespace
        name = ' '.join(name.split())
        return name
