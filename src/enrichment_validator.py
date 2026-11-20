
"""Validate LLM enrichment against deterministic scraped evidence."""

import re

from src.providers.base import EnrichmentRequest, EnrichmentResult


def _normalize_text(text: str) -> str:
    """Normalize text for case-insensitive evidence matching."""
    return re.sub(r"\s+", " ", text.lower()).strip()


def _supported_quote(quote: object, source: str) -> bool:
    """Check whether an evidence quote appears in the scraped source."""
    return (
        isinstance(quote, str)
        and bool(quote.strip())
        and _normalize_text(quote) in _normalize_text(source)
    )


def _value_supported_by_quote(value: str, quote: str) -> bool:
    """Check whether a value is directly supported by its evidence quote."""
    return _normalize_text(value) in _normalize_text(quote)


def validate_enrichment(
    result: EnrichmentResult,
    request: EnrichmentRequest,
) -> EnrichmentResult:
    """Reject enriched values without verifiable source evidence."""

    source = request.scraped_text
    evidence = result.evidence if isinstance(result.evidence, dict) else {}

    # Business name: must be supported by a source quote.
    business_name = result.business_name
    name_quote = evidence.get("businessName")

    if not (
        isinstance(business_name, str)
        and _supported_quote(name_quote, source)
        and _value_supported_by_quote(business_name, name_quote)
    ):
        business_name = None

    # Industry: must appear in the supporting evidence quote.
    industry = result.industry
    industry_quote = evidence.get("industry")

    if not (
        isinstance(industry, str)
        and _supported_quote(industry_quote, source)
        and _value_supported_by_quote(industry, industry_quote)
    ):
        industry = None

    # Description: require a source quote and meaningful word overlap.
    description = result.description
    description_quote = evidence.get("description")

    if not (
        isinstance(description, str)
        and _supported_quote(description_quote, source)
    ):
        description = None
    elif description:
        description_words = {
            word
            for word in re.findall(r"\b[a-zA-Z]{4,}\b", description.lower())
        }
        quote_words = {
            word
            for word in re.findall(
                r"\b[a-zA-Z]{4,}\b", description_quote.lower()
            )
        }

        overlap = description_words & quote_words

        if not description_words or len(overlap) / len(description_words) < 0.5:
            description = None

    # Services: each service must have a matching source quote.
    services = []
    service_quotes = evidence.get("services", [])

    if isinstance(result.services, list) and isinstance(service_quotes, list):
        for index, service in enumerate(result.services):
            if index >= len(service_quotes):
                break

            quote = service_quotes[index]

            if (
                isinstance(service, str)
                and service.strip()
                and _supported_quote(quote, source)
                and _value_supported_by_quote(service, quote)
            ):
                services.append(service)

    # Contact roles: only Python-extracted emails may be retained.
    allowed_emails = set(request.extracted_emails)
    role_evidence = evidence.get("contactRoles", {})
    roles_by_email = {}

    if isinstance(result.contact_roles, list):
        for contact in result.contact_roles:
            if not isinstance(contact, dict):
                continue

            email = contact.get("email")
            role = contact.get("role", "general")

            if email not in allowed_emails:
                continue

            if role not in {
                "sales",
                "support",
                "careers",
                "general",
                "partnerships",
                "other",
            }:
                role = "general"

            quote = (
                role_evidence.get(email)
                if isinstance(role_evidence, dict)
                else None
            )

            # Require a verifiable quote for non-general classifications.
            if role != "general" and not _supported_quote(quote, source):
                role = "general"

            roles_by_email[email] = role

    # Never lose emails extracted by Python.
    contact_roles = [
        {
            "email": email,
            "role": roles_by_email.get(email, "general"),
        }
        for email in request.extracted_emails
    ]

    return EnrichmentResult(
        business_name=business_name,
        description=description,
        industry=industry,
        services=services,
        contact_roles=contact_roles,
        evidence=evidence,
    )
