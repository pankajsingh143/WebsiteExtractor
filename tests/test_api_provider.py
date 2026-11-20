
import json
import pytest


from urllib.error import HTTPError
from src.providers.api_provider import APIProvider
from src.providers.base import EnrichmentRequest


class MockResponse:
    def __init__(self, data):
        self.data = json.dumps(data).encode("utf-8")

    def read(self):
        return self.data

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


def test_api_provider_sends_config_and_parses_response(monkeypatch):
    captured = {}

    mock_response_data = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "businessName": "Example Company",
                            "description": "Example Company provides consulting.",
                            "industry": None,
                            "services": ["consulting"],
                            "contactRoles": [
                                {"email": "info@example.com", "role": "general"}
                            ],
                            "evidence": {
                                "businessName": "Example Company",
                                "description": "Example Company provides consulting.",
                                "industry": None,
                                "services": ["consulting"],
                                "contactRoles": {},
                            },
                        }
                    )
                }
            }
        ]
    }

    def mock_urlopen(http_request, timeout):
        captured["url"] = http_request.full_url
        captured["headers"] = dict(http_request.header_items())
        captured["payload"] = json.loads(http_request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return MockResponse(mock_response_data)

    class MockOpener:
        def open(self, http_request, timeout):
            return mock_urlopen(http_request, timeout)


    def mock_build_opener(*handlers):
        return MockOpener()

    monkeypatch.setattr(
        "src.providers.api_provider.build_opener",
        mock_build_opener,
    )

    provider = APIProvider(
        api_url="https://llm.example.com/v1/chat/completions",
        api_key="test-api-key",
        model="test-model",
        timeout=45,
    )

    request = EnrichmentRequest(
        scraped_text="Example Company provides consulting.",
        extracted_emails=["info@example.com"],
    )

    result = provider.enrich(request)

    assert captured["url"] == "https://llm.example.com/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-api-key"
    assert captured["timeout"] == 45
    assert captured["payload"]["model"] == "test-model"
    assert captured["payload"]["temperature"] == 0
    assert captured["payload"]["response_format"] == {"type": "json_object"}

    assert result.business_name == "Example Company"
    assert result.services == ["consulting"]
    assert result.contact_roles == [
        {"email": "info@example.com", "role": "general"}
    ]
    assert result.evidence["businessName"] == "Example Company"


def test_api_provider_works_without_api_key(monkeypatch):
    captured = {}

    mock_response_data = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "businessName": None,
                            "description": None,
                            "industry": None,
                            "services": [],
                            "contactRoles": [],
                            "evidence": {},
                        }
                    )
                }
            }
        ]
    }

    def mock_urlopen(http_request, timeout):
        captured["headers"] = dict(http_request.header_items())
        return MockResponse(mock_response_data)

    class MockOpener:
        def open(self, http_request, timeout):
            return mock_urlopen(http_request, timeout)


    def mock_build_opener(*handlers):
        return MockOpener()

    monkeypatch.setattr("src.providers.api_provider.build_opener", mock_build_opener)

    provider = APIProvider(
        api_url="http://localhost:1234/v1/chat/completions",
        model="test-model",
    )

    provider.enrich(
        EnrichmentRequest(
            scraped_text="No business information",
            extracted_emails=[],
        )
    )

    assert "Authorization" not in captured["headers"]


def test_api_provider_rejects_redirects(monkeypatch):
    def mock_build_opener(*handlers):
        class MockOpener:
            def open(self, http_request, timeout):
                raise HTTPError(
                    http_request.full_url,
                    302,
                    "Found",
                    {},
                    None,
                )

        return MockOpener()

    monkeypatch.setattr(
        "src.providers.api_provider.build_opener",
        mock_build_opener,
    )

    provider = APIProvider(
        api_url="https://llm.example.com/v1/chat/completions",
        model="test-model",
    )

    request = EnrichmentRequest(
        scraped_text="Example evidence",
        extracted_emails=[],
    )

    with pytest.raises(ValueError, match="redirects are not allowed"):
        provider.enrich(request)
