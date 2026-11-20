
from src.enrichment_validator import validate_enrichment
from src.providers.base import EnrichmentRequest, EnrichmentResult


def test_validator_rejects_unsupported_information():
    source = (
        "Acme Cloud Solutions provides AWS cloud migration "
        "and DevOps consulting. Contact sales@acmecloud.io."
    )

    request = EnrichmentRequest(
        scraped_text=source,
        extracted_emails=["sales@acmecloud.io"],
    )

    result = EnrichmentResult(
        business_name="Acme Cloud Solutions",
        description="Acme Cloud Solutions provides AWS cloud migration and DevOps consulting.",
        industry="Healthcare",
        services=[
            "AWS cloud migration",
            "DevOps consulting",
            "Blockchain development",
        ],
        contact_roles=[
            {"email": "sales@acmecloud.io", "role": "sales"},
            {"email": "fake@acmecloud.io", "role": "support"},
        ],
        evidence={
            "businessName": "Acme Cloud Solutions",
            "description": source,
            "industry": "Healthcare",
            "services": [
                "AWS cloud migration",
                "DevOps consulting",
                "Blockchain development",
            ],
            "contactRoles": {
                "sales@acmecloud.io": "Contact sales@acmecloud.io",
                "fake@acmecloud.io": "Contact our support team",
            },
        },
    )

    validated = validate_enrichment(result, request)

    assert validated.business_name == "Acme Cloud Solutions"
    assert validated.industry is None
    assert "AWS cloud migration" in validated.services
    assert "DevOps consulting" in validated.services
    assert "Blockchain development" not in validated.services
    assert validated.contact_roles == [
        {"email": "sales@acmecloud.io", "role": "sales"}
    ]
    


def test_validator_preserves_emails_and_defaults_unknown_roles():
    source = "Contact us at info@example.com for more information."

    request = EnrichmentRequest(
        scraped_text=source,
        extracted_emails=["info@example.com", "support@example.com"],
    )

    result = EnrichmentResult(
        business_name="Invented Company",
        description="We manufacture aerospace engines and medical equipment.",
        industry="Aerospace",
        services=["Medical equipment manufacturing"],
        contact_roles=[
            {"email": "info@example.com", "role": "unknown_role"},
        ],
        evidence={
            "businessName": "Invented Company",
            "description": "We manufacture aerospace engines and medical equipment.",
            "industry": "Aerospace",
            "services": ["Medical equipment manufacturing"],
            "contactRoles": {
                "info@example.com": "Contact us at info@example.com for more information.",
            },
        },
    )

    validated = validate_enrichment(result, request)

    assert validated.business_name is None
    assert validated.description is None
    assert validated.industry is None
    assert validated.services == []
    assert validated.contact_roles == [
        {"email": "info@example.com", "role": "general"},
        {"email": "support@example.com", "role": "general"},
    ]
