
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
                "reasoning_effort": "none",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You classify contact email roles. "
                            "Use only the supplied website URL and email addresses. "
                            "Never browse or use external knowledge. "
                            "Preserve every supplied email exactly and return exactly "
                            "one classification per supplied email. "
                            "Return valid JSON only."

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
            contact_roles=data.get("contactRoles", []),
        )

    @staticmethod
    def _build_prompt(request: EnrichmentRequest) -> str:
        supplied_data = {
            "website_url": request.website_url,
            "extracted_emails": request.extracted_emails,
        }

        return f"""
    Classify the role of each supplied email address.

    Use the website URL and email address patterns as context.
    Do not browse or use external knowledge.

    Rules:
    - Classify only the supplied email addresses.
    - Never create, modify, or omit email addresses.
    - Use the email address and website URL to infer the most likely role.
    - If the role is ambiguous, use "general".
    - Return only the allowed role values.

    Allowed roles:
    sales, support, careers, general, partnerships, other

    Classification hints:
    - sales, business development, commercial -> sales
    - support, help, service desk -> support
    - careers, jobs, recruitment, hr -> careers
    - partner, alliances -> partnerships
    - info, contact, admin, office or unclear -> general
    - Other clearly identifiable functions -> other

    Return valid JSON only, using exactly this structure:

    {{
    "contactRoles": [
        {{"email": "example@example.com", "role": "general"}}
    ]
    }}

    Input:
    {json.dumps(supplied_data, ensure_ascii=False)}
    """

# Temporary compatibility alias.
# Removed when the enrichment orchestrator is migrated to APIProvider.
OllamaProvider = APIProvider
