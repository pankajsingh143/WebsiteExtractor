"""Provider-independent enrichment orchestrator."""

import logging
import os

from src.providers.base import (
    EnrichmentProvider,
    EnrichmentRequest,
    EnrichmentResult,
)
from src.providers.ollama import APIProvider
from src.enrichment_validator import validate_enrichment

logger = logging.getLogger(__name__)


class Enricher:
    """Orchestrates enrichment independently of the underlying AI provider."""

    def __init__(self, provider: EnrichmentProvider | None = None):
        self.provider = provider or self._create_provider()

    @staticmethod
    def _create_provider() -> EnrichmentProvider:
        return APIProvider(
            api_url=os.getenv("ENRICHMENT_API_URL", ""),
            model=os.getenv("ENRICHMENT_MODEL", ""),
            api_key=os.getenv("ENRICHMENT_API_KEY") or None,
            timeout=float(os.getenv("ENRICHMENT_TIMEOUT", "60")),
        )

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