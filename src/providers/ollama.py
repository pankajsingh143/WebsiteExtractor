"""Ollama implementation of the enrichment provider."""

import json
from urllib.request import Request, urlopen

from .base import EnrichmentProvider, EnrichmentRequest, EnrichmentResult


class OllamaProvider(EnrichmentProvider):
    """Enrich scraped website data using a local Ollama model."""

    def __init__(
        self,
        model: str = "qwen3.5:4b",
        base_url: str = "http://localhost:11434",
        timeout: float = 120.0,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @property
    def provider_name(self) -> str:
        return "ollama"

    def enrich(self, request: EnrichmentRequest) -> EnrichmentResult:
        prompt = self._build_prompt(request)

        payload = json.dumps(
            {
                "model": self.model,
                "stream": False,
                "think": False,
                "format": "json",
                "options": {
                    "temperature": 0,
                    "num_predict": 512,
                },
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a strict website data extraction engine. "
                            "Use ONLY the supplied scraped content. Never invent, "
                            "infer unsupported facts, browse, or use outside knowledge. "
                            "Return null or empty arrays when evidence is insufficient. "
                            "Return valid JSON only."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            }
        ).encode("utf-8")
        request = Request(
            f"{self.base_url}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=self.timeout) as response:
            result = json.loads(response.read().decode("utf-8"))

        content = result["message"]["content"]
        data = json.loads(content)

        return EnrichmentResult(
            business_name=data.get("businessName"),
            description=data.get("description"),
            industry=data.get("industry"),
            services=data.get("services", []),
            contact_roles=data.get("contactRoles", []),
        )

    @staticmethod
    def _build_prompt(request: EnrichmentRequest) -> str:
        evidence = {
            "scraped_text": request.scraped_text,
            "extracted_emails": request.extracted_emails,
        }

        return f"""
Extract business information from the supplied evidence.

Rules:
- Use only the supplied scraped text.
- Business name must be explicitly present in the text.
- Description must be a factual summary of the text.
- Industry must be explicitly supported; otherwise null.
- Services must be explicitly mentioned.
- Classify only the supplied email addresses.
- Never create, alter, or omit email addresses.
- If email role is unclear, use "general".
- Allowed email roles: sales, support, careers, general, partnerships, other.

Return exactly this JSON structure:
{{
  "businessName": null,
  "description": null,
  "industry": null,
  "services": [],
  "contactRoles": [
    {{"email": "", "role": "general"}}
  ] 
}}

Evidence:
{json.dumps(evidence, ensure_ascii=False)}
""".strip()