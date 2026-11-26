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
    monkeypatch.setattr(
        main,
        "extract_contacts",
        lambda *args: {
            "title": "Example",
            "emails": ["info@example.com"],
            "phones": [],
            "socialLinks": [],
            "internalLinks": [],
        },
    )
    monkeypatch.setattr(main, "Enricher", fail_if_called)

    asyncio.run(main.main())

    summary_records = [
        record for record in pushed_data if record.get("recordType") == "summary"
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
            return type(
                "FakeResult",
                (),
                {
                    "__dict__": {
                        "companyName": "Example Inc",
                        "contactRoles": [],
                    }
                },
            )()

    enricher_instances = []

    def fake_enricher_factory(**kwargs):
        instance = FakeEnricher(**kwargs)
        enricher_instances.append(instance)
        return instance

    monkeypatch.setattr(main, "Actor", FakeActor())
    monkeypatch.setattr(main.httpx, "AsyncClient", lambda **kwargs: FakeClient())
    monkeypatch.setattr(main, "validate_public_host", lambda url: None)
    monkeypatch.setattr(
        main,
        "extract_contacts",
        lambda *args: {
            "title": "Example",
            "emails": ["info@example.com"],
            "phones": [],
            "socialLinks": [],
            "internalLinks": [],
        },
    )
    monkeypatch.setattr(main, "Enricher", fake_enricher_factory)

    asyncio.run(main.main())

    summary_records = [
        record for record in pushed_data if record.get("recordType") == "summary"
    ]

    assert len(summary_records) == 1

    website_summary = next(iter(summary_records[0]["results"].values()))

    assert website_summary["pagesCrawled"] == 1
    assert website_summary["uniqueEmails"] == ["info@example.com"]
    assert "enrichment" in website_summary
    assert website_summary["enrichment"] is not None


def test_main_blocks_external_redirect_and_records_it(monkeypatch):
    pushed_data = []
    requested_urls = []

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
        status_code = 301
        url = "https://example.com/"
        text = ""
        headers = {
            "location": "https://example.org/",
        }

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_value, traceback):
            return False

        async def get(self, url):
            requested_urls.append(url)
            return FakeResponse()

    def fail_if_called(*args, **kwargs):
        raise AssertionError("External redirect must not be followed")

    monkeypatch.setattr(main, "Actor", FakeActor())
    monkeypatch.setattr(main.httpx, "AsyncClient", lambda **kwargs: FakeClient())
    monkeypatch.setattr(main, "validate_public_host", lambda url: None)
    monkeypatch.setattr(main, "extract_contacts", fail_if_called)

    asyncio.run(main.main())

    blocked_records = [
        record
        for record in pushed_data
        if record.get("error") == "External redirect blocked"
    ]

    assert len(blocked_records) == 1

    blocked_record = blocked_records[0]

    assert blocked_record["startUrl"] == "https://example.com"
    assert blocked_record["pageUrl"] == "https://example.com"
    assert blocked_record["statusCode"] == 301
    assert blocked_record["redirectUrl"] == "https://example.org/"
    assert blocked_record["emails"] == []
    assert blocked_record["phones"] == []
    assert blocked_record["socialLinks"] == []

    # Only the original URL should be requested.
    assert requested_urls == ["https://example.com"]


def test_main_rejects_private_subdomain_before_robots_check(monkeypatch):
    requested_urls = []
    robots_checked = []

    actor_input = {
        "startUrls": [{"url": "https://example.com"}],
        "maxPages": 2,
        "respectRobotsTxt": True,
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
            pass

    class FakeResponse:
        status_code = 200
        url = "https://example.com/"
        text = "<html><body>Example</body></html>"
        headers = {"content-type": "text/html"}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_value, traceback):
            return False

        async def get(self, url):
            requested_urls.append(url)
            return FakeResponse()

    def fake_getaddrinfo(host, *args, **kwargs):
        ip = "10.0.0.5" if host == "private.example.com" else "93.184.216.34"

        return [
            (
                main.socket.AF_INET,
                main.socket.SOCK_STREAM,
                main.socket.IPPROTO_TCP,
                "",
                (ip, 0),
            )
        ]

    async def fake_robots_allowed(client, url, user_agent, cache):
        robots_checked.append(url)
        return True

    monkeypatch.setattr(main, "Actor", FakeActor())
    monkeypatch.setattr(main.httpx, "AsyncClient", lambda **kwargs: FakeClient())
    monkeypatch.setattr(main.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(main, "robots_allowed", fake_robots_allowed)
    monkeypatch.setattr(
        main,
        "extract_contacts",
        lambda *args: {
            "title": "Example",
            "emails": [],
            "phones": [],
            "socialLinks": [],
            "internalLinks": ["https://private.example.com/contact"],
        },
    )

    asyncio.run(main.main())

    assert requested_urls == ["https://example.com"]
    assert robots_checked == ["https://example.com"]


def test_main_skips_redirect_destination_disallowed_by_robots(monkeypatch):
    requested_urls = []
    robots_checked = []

    actor_input = {
        "startUrls": [{"url": "https://example.com"}],
        "maxPages": 2,
        "respectRobotsTxt": True,
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
            pass

    class FakeResponse:
        status_code = 302
        url = "https://example.com/"
        text = ""
        headers = {"location": "https://www.example.com/private"}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_value, traceback):
            return False

        async def get(self, url):
            requested_urls.append(url)
            return FakeResponse()

    def fake_getaddrinfo(host, *args, **kwargs):
        return [
            (
                main.socket.AF_INET,
                main.socket.SOCK_STREAM,
                main.socket.IPPROTO_TCP,
                "",
                ("93.184.216.34", 0),
            )
        ]

    async def fake_robots_allowed(client, url, user_agent, cache):
        robots_checked.append(url)

        # Allow the starting page, but disallow the redirect destination.
        return "www.example.com" not in url

    monkeypatch.setattr(main, "Actor", FakeActor())
    monkeypatch.setattr(main.httpx, "AsyncClient", lambda **kwargs: FakeClient())
    monkeypatch.setattr(main.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(main, "robots_allowed", fake_robots_allowed)

    asyncio.run(main.main())

    assert len(requested_urls) == 1
    assert requested_urls[0] == "https://example.com"

    assert len(robots_checked) == 2
    assert "www.example.com" in robots_checked[1]


def test_main_blocks_private_ip_redirect_before_robots_check(monkeypatch):
    requested_urls = []
    robots_checked = []

    actor_input = {
        "startUrls": [{"url": "https://example.com"}],
        "maxPages": 2,
        "respectRobotsTxt": True,
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
            pass

    class FakeResponse:
        status_code = 302
        url = "https://example.com/"
        text = ""
        headers = {"location": "https://private.example.com/contact"}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_value, traceback):
            return False

        async def get(self, url):
            requested_urls.append(url)
            return FakeResponse()

    def fake_getaddrinfo(host, *args, **kwargs):
        ip = "10.0.0.5" if host == "private.example.com" else "93.184.216.34"

        return [
            (
                main.socket.AF_INET,
                main.socket.SOCK_STREAM,
                main.socket.IPPROTO_TCP,
                "",
                (ip, 0),
            )
        ]

    async def fake_robots_allowed(client, url, user_agent, cache):
        robots_checked.append(url)
        return True

    monkeypatch.setattr(main, "Actor", FakeActor())
    monkeypatch.setattr(main.httpx, "AsyncClient", lambda **kwargs: FakeClient())
    monkeypatch.setattr(main.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(main, "robots_allowed", fake_robots_allowed)

    asyncio.run(main.main())

    assert requested_urls == ["https://example.com"]
    assert robots_checked == ["https://example.com"]


def test_main_handles_host_becoming_private_during_redirect(monkeypatch):
    requested_urls = []
    robots_checked = []
    destination_lookups = 0

    actor_input = {
        "startUrls": [{"url": "https://example.com"}],
        "maxPages": 2,
        "respectRobotsTxt": True,
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
            pass

    class FakeResponse:
        status_code = 302
        url = "https://example.com/"
        text = ""
        headers = {"location": "https://www.example.com/private"}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_value, traceback):
            return False

        async def get(self, url):
            requested_urls.append(url)
            return FakeResponse()

    def fake_getaddrinfo(host, *args, **kwargs):
        nonlocal destination_lookups

        if host == "www.example.com":
            destination_lookups += 1
            ip = "93.184.216.34" if destination_lookups == 1 else "10.0.0.5"
        else:
            ip = "93.184.216.34"

        return [
            (
                main.socket.AF_INET,
                main.socket.SOCK_STREAM,
                main.socket.IPPROTO_TCP,
                "",
                (ip, 0),
            )
        ]

    async def fake_robots_allowed(client, url, user_agent, cache):
        robots_checked.append(url)
        return True

    monkeypatch.setattr(main, "Actor", FakeActor())
    monkeypatch.setattr(main.httpx, "AsyncClient", lambda **kwargs: FakeClient())
    monkeypatch.setattr(main.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(main, "robots_allowed", fake_robots_allowed)

    asyncio.run(main.main())

    assert requested_urls == ["https://example.com"]
    assert destination_lookups == 2
    assert len(robots_checked) == 2
