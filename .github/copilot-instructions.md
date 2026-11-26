
# WebsiteExtractor — Code Review Instructions

## Project overview
WebsiteExtractor is a Python-based Apify Actor that extracts
business contact information from websites.

## Architecture principles
- Deterministic extraction is authoritative.
- LLM enrichment is optional.
- LLM output must never invent, modify, or remove extracted emails.
- Preserve the existing Apify dataset output schema.
- Network failures must not crash the entire Actor unnecessarily.

## Security requirements
- Prevent Server-Side Request Forgery (SSRF).
- Reject private, loopback, link-local and non-public IP addresses.
- Validate redirect destinations before following them.
- Never follow redirects outside the allowed registrable domain.
- Respect robots.txt when enabled.
- Do not expose API keys or secrets in logs or output.

## Crawling requirements
- Respect configured page and timeout limits.
- Avoid duplicate page processing.
- Handle HTTP errors and redirects safely.
- Maintain reasonable request rates.

## LLM requirements
- Only classify emails supplied by deterministic extraction.
- Restrict contact roles to the supported schema.
- Invalid LLM output must fall back safely.
- LLM failures must not break deterministic extraction.

## Testing requirements
- Add regression tests for new functionality.
- Test security-sensitive URL and redirect handling.
- Preserve backward compatibility.
- Do not weaken existing tests to make implementation pass.

## Review priorities
1. Critical security vulnerabilities
2. Data integrity and incorrect extraction
3. Functional bugs and regressions
4. Reliability and error handling
5. Maintainability and performance

Flag findings with severity:
CRITICAL, HIGH, MEDIUM, LOW.

Do not approve changes merely because tests pass.
