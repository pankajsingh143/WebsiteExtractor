"""Validate LLM enrichment against deterministic scraped evidence."""

import re

from src.providers.base import EnrichmentRequest, EnrichmentResult


def _normalize_text(text: str) -> str:
    """Normalize text for conservative evidence matching."""
    return re.sub(r"\s+", " ", text.lower()).strip()


def validate_enrichment(
    result: EnrichmentResult,
    request: EnrichmentRequest,
) -> EnrichmentResult:
    """Remove enrichment values that cannot be supported by scraped evidence."""

    evidence = _normalize_text(request.scraped_text)

    # Business name must appear explicitly in scraped text.
    business_name = result.business_name
    if business_name and _normalize_text(business_name) not in evidence:
        business_name = None

    # Industry must be explicitly supported.
    industry = result.industry
    if industry and _normalize_text(industry) not in evidence:
        industry = None

    # Description must contain meaningful evidence from the source.
    description = result.description
    if description:
        description_words = {
            word
            for word in re.findall(r"\b[a-zA-Z]{4,}\b", description.lower())
        }
        evidence_words = {
            word
            for word in re.findall(r"\b[a-zA-Z]{4,}\b", evidence)
        }

        overlap = description_words & evidence_words

        # Reject descriptions with insufficient source-word overlap.
        if not description_words or len(overlap) / len(description_words) < 0.5:
            description = None

    # Services must have textual evidence in scraped content.
    services = [
        service
        for service in result.services
        if isinstance(service, str)
        and service.strip()
        and _normalize_text(service) in evidence
    ]

    # Only Python-extracted emails are allowed.
    allowed_emails = set(request.extracted_emails)
    roles_by_email = {}

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
    )