from src.enrichment_validator import validate_enrichment
from src.providers.base import EnrichmentRequest, EnrichmentResult


def test_validator_preserves_schema_with_empty_business_enrichment():
    request = EnrichmentRequest(
        website_url="https://acmecloud.io",
        extracted_emails=["sales@acmecloud.io"],
    )

    result = EnrichmentResult(
        business_name="Invented Company",
        description="Invented description",
        industry="Healthcare",
        services=["Invented service"],
        contact_roles=[
            {"email": "sales@acmecloud.io", "role": "sales"},
        ],
    )

    validated = validate_enrichment(result, request)

    assert validated.business_name is None
    assert validated.description is None
    assert validated.industry is None
    assert validated.services == []
    assert validated.evidence == {}


def test_validator_accepts_valid_contact_roles():
    request = EnrichmentRequest(
        website_url="https://acmecloud.io",
        extracted_emails=[
            "sales@acmecloud.io",
            "support@acmecloud.io",
        ],
    )

    result = EnrichmentResult(
        contact_roles=[
            {"email": "sales@acmecloud.io", "role": "sales"},
            {"email": "support@acmecloud.io", "role": "support"},
        ],
    )

    validated = validate_enrichment(result, request)

    assert validated.contact_roles == [
        {"email": "sales@acmecloud.io", "role": "sales"},
        {"email": "support@acmecloud.io", "role": "support"},
    ]


def test_validator_defaults_invalid_roles_to_general():
    request = EnrichmentRequest(
        website_url="https://example.com",
        extracted_emails=["info@example.com"],
    )

    result = EnrichmentResult(
        contact_roles=[
            {"email": "info@example.com", "role": "ceo"},
        ],
    )

    validated = validate_enrichment(result, request)

    assert validated.contact_roles == [
        {"email": "info@example.com", "role": "general"},
    ]


def test_validator_never_adds_or_removes_extracted_emails():
    request = EnrichmentRequest(
        website_url="https://example.com",
        extracted_emails=[
            "info@example.com",
            "support@example.com",
        ],
    )

    result = EnrichmentResult(
        contact_roles=[
            {"email": "info@example.com", "role": "sales"},
            {"email": "fake@example.com", "role": "support"},
        ],
    )

    validated = validate_enrichment(result, request)

    assert validated.contact_roles == [
        {"email": "info@example.com", "role": "sales"},
        {"email": "support@example.com", "role": "general"},
    ]