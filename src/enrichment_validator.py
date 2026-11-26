"""Validate LLM contact-role enrichment against deterministic extraction."""

from src.providers.base import EnrichmentRequest, EnrichmentResult


ALLOWED_ROLES = {
    "sales",
    "support",
    "careers",
    "general",
    "partnerships",
    "other",
}


def validate_enrichment(
    result: EnrichmentResult,
    request: EnrichmentRequest,
) -> EnrichmentResult:
    """Validate AI roles while preserving deterministic extracted emails."""

    roles_by_email = {}

    if isinstance(result.contact_roles, list):
        for contact in result.contact_roles:
            if not isinstance(contact, dict):
                continue

            email = contact.get("email")
            role = contact.get("role", "general")

            if email not in request.extracted_emails:
                continue

            if role not in ALLOWED_ROLES:
                role = "general"

            roles_by_email[email] = role

    # Python extraction is authoritative; AI cannot add or remove emails.
    contact_roles = [
        {
            "email": email,
            "role": roles_by_email.get(email, "general"),
        }
        for email in request.extracted_emails
    ]

    # Business enrichment is intentionally disabled in Phase 1.
    return EnrichmentResult(
        business_name=None,
        description=None,
        industry=None,
        services=[],
        contact_roles=contact_roles,
        evidence={},
    )