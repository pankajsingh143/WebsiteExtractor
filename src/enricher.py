"""Provider-independent enrichment orchestrator."""

import logging

from src.providers.base import (
    EnrichmentProvider,
    EnrichmentRequest,
    EnrichmentResult,
)
from src.providers.api_provider import APIProvider
from src.enrichment_validator import validate_enrichment

logger = logging.getLogger(__name__)


class Enricher:
    """Orchestrates enrichment independently of the underlying AI provider."""

    def __init__(
        self,
        enabled: bool = False,
        provider: EnrichmentProvider | None = None,
        api_url: str = "",
        api_key: str | None = None,
        model: str = "",
        timeout: float = 60.0,
    ):
        self.enabled = enabled
        self.provider = None

        if self.enabled:
            self.provider = provider or self._create_provider(
                api_url=api_url,
                api_key=api_key,
                model=model,
                timeout=timeout,
            )

    @staticmethod
    def _create_provider(
        api_url: str,
        api_key: str | None,
        model: str,
        timeout: float,
    ) -> EnrichmentProvider:
        return APIProvider(
            api_url=api_url,
            api_key=api_key,
            model=model,
            timeout=timeout,
        )

    def enrich(self, request: EnrichmentRequest) -> EnrichmentResult:
        """Run enrichment with safe fallback if the provider fails."""

        if not self.enabled:
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

            # Preserve deterministic Python-extracted emails.
            return EnrichmentResult(
                contact_roles=[
                    {"email": email, "role": "general"}
                    for email in request.extracted_emails
                ]
            )