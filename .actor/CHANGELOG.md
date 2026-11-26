# Website Contact & Business Information Extractor — v0.2

**Release date:** 26 November 2026  
**Release type:** Feature release

## What's New

### AI-powered contact role enrichment

Introduced optional LLM-based enrichment to make extracted contact information more useful.

- Classifies discovered email addresses into meaningful business roles:
  - Sales
  - Support
  - Careers
  - General
  - Partnerships
  - Other
- Supports configurable LLM API endpoint, API key, model and timeout.
- Runs enrichment once per starting website after the crawling process completes.
- Enrichment can be enabled or disabled through Actor input settings.

### Reliable and controlled AI processing

- The deterministic crawler remains the source of truth for extracted email addresses.
- AI enrichment does not invent, modify, add or remove extracted email addresses.
- When enrichment fails, the crawler continues to operate using fallback contact-role classifications.
- Disabling enrichment avoids unnecessary LLM API calls.
- Existing extraction functionality remains available without requiring an LLM API key.

## Security and Reliability Improvements

- Added public-IP validation for URLs discovered during crawling.
- Strengthened protection against requests to private and internal subdomains.
- Added validation of redirect destinations before following redirects.
- Enforced destination-specific `robots.txt` rules for redirects.
- Improved handling of unsafe URLs and DNS re-resolution failures.

## Compatibility

- Existing crawling input parameters are retained.
- AI enrichment is optional and disabled by default.
- Existing deterministic email, phone and social-link extraction is preserved.
- Existing dataset output structure remains backward-compatible.

## Important Notes

- AI-generated classifications are intended to organize discovered contacts, not independently verify their accuracy.
- Business descriptions, industry classification and service enrichment are not included in this release.
- Websites must remain publicly accessible and subject to the Actor's crawling restrictions.