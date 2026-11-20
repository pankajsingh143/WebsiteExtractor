"""Provider-independent enrichment orchestrator."""

import logging
import os
from unittest import result
from urllib import request

from src.providers.base import EnrichmentProvider, EnrichmentRequest, EnrichmentResult
from src.providers.ollama import OllamaProvider
from src.enrichment_validator import validate_enrichment

logger = logging.getLogger(__name__)


class Enricher:
    """Orchestrates enrichment independently of the underlying AI provider."""

    def __init__(self, provider: EnrichmentProvider | None = None):
        self.provider = provider or self._create_provider()

    @staticmethod
    def _create_provider() -> EnrichmentProvider:
        provider_name = os.getenv("ENRICHMENT_PROVIDER", "ollama").lower()

        if provider_name == "ollama":
            return OllamaProvider(
                model=os.getenv("OLLAMA_MODEL", "qwen3.5:4b"),
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            )

        raise ValueError(f"Unsupported enrichment provider: {provider_name}")
    
    @staticmethod
    def is_enabled() -> bool:
        """Return whether LLM enrichment is explicitly enabled."""
        return os.getenv("ENRICHMENT_ENABLED", "false").lower() in {
            "true",
            "1",
            "yes",
        }

    def enrich(self, request: EnrichmentRequest) -> EnrichmentResult:
        """Run enrichment with safe fallback if the provider fails."""
        if not self.is_enabled():
            return EnrichmentResult()
        try:
            result = self.provider.enrich(request)
            return validate_enrichment(result, request)

        except Exception as exc:
            logger.warning(
                "Enrichment failed using provider '%s': %s",
                self.provider.provider_name,
                exc,
            )

            # Preserve Python-extracted emails; never lose deterministic data.
            return EnrichmentResult(
                contact_roles=[
                    {"email": email, "role": "general"}
                    for email in request.extracted_emails
                ]
            )