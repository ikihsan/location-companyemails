"""
Base source interface for pluggable discovery sources.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Generator
from dataclasses import dataclass

from models import Company, DiscoverySource


@dataclass
class DiscoveryResult:
    """Result from a discovery source."""
    companies: List[Company]
    source_name: str
    total_found: int
    has_more: bool
    next_page_token: Optional[str] = None
    error: Optional[str] = None


class BaseSource(ABC):
    """
    Abstract base class for company discovery sources.
    Extend this class to add new sources.
    """
    
    def __init__(self, name: str, base_url: str, requires_js: bool = False):
        self.name = name
        self.base_url = base_url
        self.requires_js = requires_js
        self._enabled = True
    
    @abstractmethod
    def search(
        self,
        location: str,
        roles: List[str],
        max_results: int = 100,
    ) -> Generator[Company, None, None]:
        """
        Search for companies hiring for given roles in location.
        Yields Company objects as they are discovered.
        """
        pass
    
    @abstractmethod
    def get_company_details(self, company: Company) -> Company:
        """
        Enrich company with additional details by crawling its pages.
        Returns the enriched Company object.
        """
        pass
    
    def is_enabled(self) -> bool:
        """Check if this source is enabled."""
        return self._enabled
    
    def enable(self):
        """Enable this source."""
        self._enabled = True
    
    def disable(self):
        """Disable this source."""
        self._enabled = False
    
    def get_source_info(self) -> DiscoverySource:
        """Get source metadata."""
        return DiscoverySource(
            name=self.name,
            base_url=self.base_url,
            source_type='discovery',
            requires_js=self.requires_js,
            enabled=self._enabled,
        )


class SourceRegistry:
    """Registry for managing discovery sources."""
    
    def __init__(self):
        self._sources: dict = {}
    
    def register(self, source: BaseSource):
        """Register a new source."""
        self._sources[source.name] = source
    
    def unregister(self, name: str):
        """Unregister a source."""
        if name in self._sources:
            del self._sources[name]
    
    def get(self, name: str) -> Optional[BaseSource]:
        """Get a source by name."""
        return self._sources.get(name)
    
    def get_all(self) -> List[BaseSource]:
        """Get all registered sources."""
        return list(self._sources.values())
    
    def get_enabled(self) -> List[BaseSource]:
        """Get all enabled sources."""
        return [s for s in self._sources.values() if s.is_enabled()]
    
    def list_names(self) -> List[str]:
        """List all registered source names."""
        return list(self._sources.keys())


# Global registry
_registry = SourceRegistry()


def get_registry() -> SourceRegistry:
    """Get the global source registry."""
    return _registry


def register_source(source: BaseSource):
    """Register a source in the global registry."""
    _registry.register(source)
