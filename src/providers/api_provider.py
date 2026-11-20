
"""Generic OpenAI-compatible API implementation of the enrichment provider."""

import json
from urllib.request import Request, HTTPRedirectHandler, build_opener, urlopen
from urllib.parse import urlparse
from urllib.error import HTTPError

from .base import EnrichmentProvider, EnrichmentRequest, EnrichmentResult



class NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None
    
class APIProvider(EnrichmentProvider):
    """Enrich scraped website data using a configurable LLM API endpoint."""

    def __init__(
        self,
        api_url: str,
        model: str,
        api_key: str | None = None,
        timeout: float = 60.0,
    ):
        self.api_url = api_url.strip()
        self.api_key = api_key
        parsed_url = urlparse(self.api_url)

        if parsed_url.scheme not in {"http", "https"}:
            raise ValueError("API URL must use HTTP or HTTPS.")

        if not parsed_url.hostname:
            raise ValueError("API URL must contain a valid hostname.")

        if parsed_url.username or parsed_url.password:
            raise ValueError("API URL must not contain embedded credentials.")
            self.api_key = api_key
        self.model = model
        self.timeout = timeout

    @property
    def provider_name(self) -> str:
        return "api"

    def enrich(self, request: EnrichmentRequest) -> EnrichmentResult:
        prompt = self._build_prompt(request)

        headers = {
            "Content-Type": "application/json",
        }

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = json.dumps(
            {
                "model": self.model,
                "temperature": 0,
                "max_tokens": 512,
                "response_format": {"type": "json_object"},
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a strict website data extraction engine. "
                            "Use ONLY the supplied scraped evidence. Never browse, "
                            "use outside knowledge, or invent information. "
                            "Every enriched value must have a supporting evidence "
                            "quote taken verbatim from the supplied text. "
                            "Return null or empty arrays when evidence is "
                            "insufficient. Return valid JSON only."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            }
        ).encode("utf-8")

        http_request = Request(
            self.api_url,
            data=payload,
            headers=headers,
            method="POST",
        )

        opener = build_opener(NoRedirectHandler())

        try:
            with opener.open(http_request, timeout=self.timeout) as response:
                api_result = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code in {301, 302, 303, 307, 308}:
                raise ValueError("API endpoint redirects are not allowed.") from exc
            raise

        content = api_result["choices"][0]["message"]["content"]
        data = json.loads(content)

        return EnrichmentResult(
            business_name=data.get("businessName"),
            description=data.get("description"),
            industry=data.get("industry"),
            services=data.get("services", []),
            contact_roles=data.get("contactRoles", []),
            evidence=data.get("evidence", {}),
        )

    @staticmethod
    def _build_prompt(request: EnrichmentRequest) -> str:
        supplied_evidence = {
            "scraped_text": request.scraped_text,
            "extracted_emails": request.extracted_emails,
        }

        return f"""
Extract business information using ONLY the supplied evidence.

Rules:
- Do not use external knowledge or assumptions.
- Business name must be explicitly supported by the text.
- Description must be a factual summary of the supplied text.
- Industry must be explicitly supported; otherwise null.
- Services must be explicitly mentioned in the text.
- Classify only the supplied email addresses.
- Never create, alter, or omit email addresses.
- If an email role is unclear, use "general".
- Allowed email roles: sales, support, careers, general, partnerships, other.
- Every non-null businessName, description, and industry must have a
  supporting verbatim evidence quote.
- Every service must have its own supporting evidence quote.
- Every email role must have a supporting evidence quote.
- Evidence quotes must be copied exactly from scraped_text.
- If you cannot provide evidence for a field, return null or omit that field.
- Do not explain or elaborate beyond the evidence.

Return exactly this JSON structure:
{{
  "businessName": null,
  "description": null,
  "industry": null,
  "services": [],
  "contactRoles": [
    {{"email": "", "role": "general"}}
  ],
  "evidence": {{
    "businessName": null,
    "description": null,
    "industry": null,
    "services": [],
    "contactRoles": {{}}
  }}
}}

Evidence requirements:
- evidence.businessName: quote supporting businessName, or null.
- evidence.description: quote supporting description, or null.
- evidence.industry: quote supporting industry, or null.
- evidence.services: array of quotes, in the same order as services.
- evidence.contactRoles: map each email to a quote supporting its assigned role.

Supplied evidence:
{json.dumps(supplied_evidence, ensure_ascii=False)}
""".strip()


# Temporary compatibility alias.
# Removed when the enrichment orchestrator is migrated to APIProvider.
OllamaProvider = APIProvider
