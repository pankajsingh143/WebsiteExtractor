"""Provider-independent contract for website data enrichment."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class EnrichmentRequest:
    """Evidence collected by the Python scraper."""

    scraped_text: str
    extracted_emails: list[str] = field(default_factory=list)


@dataclass
class EnrichmentResult:
    """Normalized enrichment output."""

    business_name: str | None = None
    description: str | None = None
    industry: str | None = None
    services: list[str] = field(default_factory=list)
    contact_roles: list[dict[str, str]] = field(default_factory=list)


class EnrichmentProvider(ABC):
    """Interface all enrichment providers must implement."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider identifier."""
        pass

    @abstractmethod
    def enrich(self, request: EnrichmentRequest) -> EnrichmentResult:
        """Enrich using only supplied scraped evidence."""
        pass