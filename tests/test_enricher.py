from src.enricher import Enricher
from src.providers.base import EnrichmentRequest, EnrichmentResult, EnrichmentProvider


class MockProvider(EnrichmentProvider):
    @property
    def provider_name(self) -> str:
        return "mock"

    def enrich(self, request: EnrichmentRequest) -> EnrichmentResult:
        return EnrichmentResult(
            business_name="Example Company",
            description="Example business description",
            industry="Technology",
            services=["Consulting"],
            contact_roles=[
                {"email": email, "role": "general"}
                for email in request.extracted_emails
            ],
        )


class FailingProvider(EnrichmentProvider):
    @property
    def provider_name(self) -> str:
        return "failing-mock"

    def enrich(self, request: EnrichmentRequest) -> EnrichmentResult:
        raise RuntimeError("Simulated provider failure")


def test_enricher_uses_injected_provider(monkeypatch):
    monkeypatch.setenv("ENRICHMENT_ENABLED", "true")
    provider = MockProvider()
    enricher = Enricher(provider=provider)

    request = EnrichmentRequest(
        scraped_text="Example Company provides consulting.",
        extracted_emails=["info@example.com"],
    )

    result = enricher.enrich(request)

    assert result.business_name == "Example Company"
    assert result.services == ["Consulting"]
    assert result.contact_roles == [
        {"email": "info@example.com", "role": "general"}
    ]


def test_enricher_fallback_preserves_extracted_emails(monkeypatch):
    monkeypatch.setenv("ENRICHMENT_ENABLED", "true")
    provider = FailingProvider()
    enricher = Enricher(provider=provider)

    request = EnrichmentRequest(
        scraped_text="Some scraped content",
        extracted_emails=["sales@example.com", "support@example.com"],
    )

    result = enricher.enrich(request)

    assert result.business_name is None
    assert result.description is None
    assert result.industry is None
    assert result.services == []
    assert result.contact_roles == [
        {"email": "sales@example.com", "role": "general"},
        {"email": "support@example.com", "role": "general"},
    ]

def test_enrichment_disabled_does_not_call_provider(monkeypatch):
    monkeypatch.setenv("ENRICHMENT_ENABLED", "false")

    provider = MockProvider()
    enricher = Enricher(provider=provider)

    request = EnrichmentRequest(
        scraped_text="Example Company provides consulting.",
        extracted_emails=["info@example.com"],
    )

    result = enricher.enrich(request)

    assert result.business_name is None
    assert result.description is None
    assert result.industry is None
    assert result.services == []
    assert result.contact_roles == []