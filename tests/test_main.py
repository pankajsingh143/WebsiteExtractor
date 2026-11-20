import asyncio

from src import main


def test_main_skips_enrichment_when_disabled(monkeypatch):
    pushed_data = []

    actor_input = {
        "startUrls": [{"url": "https://example.com"}],
        "maxPages": 1,
        "respectRobotsTxt": False,
        "enableEnrichment": False,
    }

    class FakeActor:
        log = main.Actor.log

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_value, traceback):
            return False

        @staticmethod
        async def get_input():
            return actor_input

        @staticmethod
        async def push_data(data):
            pushed_data.append(data)

    class FakeResponse:
        status_code = 200
        url = "https://example.com/"
        text = "<html><body>Example website</body></html>"
        headers = {"content-type": "text/html"}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_value, traceback):
            return False

        async def get(self, url):
            return FakeResponse()

    def fail_if_called(*args, **kwargs):
        raise AssertionError("Enricher must not be constructed when disabled")

    monkeypatch.setattr(main, "Actor", FakeActor())
    monkeypatch.setattr(main.httpx, "AsyncClient", lambda **kwargs: FakeClient())
    monkeypatch.setattr(main, "validate_public_host", lambda url: None)
    monkeypatch.setattr(main, "extract_contacts", lambda *args: {
        "title": "Example",
        "emails": ["info@example.com"],
        "phones": [],
        "socialLinks": [],
        "internalLinks": [],
    })
    monkeypatch.setattr(main, "Enricher", fail_if_called)

    asyncio.run(main.main())

    summary_records = [
        record for record in pushed_data
        if record.get("recordType") == "summary"
    ]

    assert len(summary_records) == 1

    website_summary = next(iter(summary_records[0]["results"].values()))

    assert website_summary["pagesCrawled"] == 1
    assert website_summary["uniqueEmails"] == ["info@example.com"]
    assert "enrichment" not in website_summary

def test_main_runs_enrichment_when_enabled(monkeypatch):
    pushed_data = []

    actor_input = {
        "startUrls": [{"url": "https://example.com"}],
        "maxPages": 1,
        "respectRobotsTxt": False,
        "enableEnrichment": True,
    }

    class FakeActor:
        log = main.Actor.log

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_value, traceback):
            return False

        @staticmethod
        async def get_input():
            return actor_input

        @staticmethod
        async def push_data(data):
            pushed_data.append(data)

    class FakeResponse:
        status_code = 200
        url = "https://example.com/"
        text = "<html><body>Example website</body></html>"
        headers = {"content-type": "text/html"}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_value, traceback):
            return False

        async def get(self, url):
            return FakeResponse()

    class FakeEnricher:
        def __init__(self, **kwargs):
            self.called = False

        def enrich(self, request):
            self.called = True
            return type("FakeResult", (), {
                "__dict__": {
                    "companyName": "Example Inc",
                    "contactRoles": [],
                }
            })()

    enricher_instances = []

    def fake_enricher_factory(**kwargs):
        instance = FakeEnricher(**kwargs)
        enricher_instances.append(instance)
        return instance

    monkeypatch.setattr(main, "Actor", FakeActor())
    monkeypatch.setattr(main.httpx, "AsyncClient", lambda **kwargs: FakeClient())
    monkeypatch.setattr(main, "validate_public_host", lambda url: None)
    monkeypatch.setattr(main, "extract_contacts", lambda *args: {
        "title": "Example",
        "emails": ["info@example.com"],
        "phones": [],
        "socialLinks": [],
        "internalLinks": [],
    })
    monkeypatch.setattr(main, "Enricher", fake_enricher_factory)

    asyncio.run(main.main())

    summary_records = [
        record for record in pushed_data
        if record.get("recordType") == "summary"
    ]

    assert len(summary_records) == 1

    website_summary = next(iter(summary_records[0]["results"].values()))

    assert website_summary["pagesCrawled"] == 1
    assert website_summary["uniqueEmails"] == ["info@example.com"]
    assert "enrichment" in website_summary
    assert website_summary["enrichment"] is not None