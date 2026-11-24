import asyncio
import json
import ipaddress
import socket
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser
from src.enricher import Enricher
from src.providers.base import EnrichmentRequest

import httpx
from apify import Actor

from src.extractor import (
    extract_contacts,
    normalize_url,
    prioritize_links,
    same_domain,
)


def validate_public_host(url: str) -> None:
    """Reject literal/private or locally resolving hosts to reduce SSRF risk."""
    parsed = urlparse(url)
    host = parsed.hostname
    if not host:
        raise ValueError("URL has no hostname")
    try:
        ip = ipaddress.ip_address(host)
        if not ip.is_global:
            raise ValueError("Private, loopback or non-public IP addresses are not allowed")
        return
    except ValueError as exc:
        if "not allowed" in str(exc):
            raise
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, None)}
        if not addresses or any(not ipaddress.ip_address(addr).is_global for addr in addresses):
            raise ValueError("Hostname resolves to a non-public IP address")
    except socket.gaierror as exc:
        raise ValueError(f"Could not resolve hostname: {host}") from exc


async def robots_allowed(client, url, user_agent, cache):
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    if robots_url not in cache:
        parser = RobotFileParser()
        parser.set_url(robots_url)
        try:
            response = await client.get(robots_url)
            if response.status_code < 400:
                parser.parse(response.text.splitlines())
            else:
                # If robots.txt is unavailable, treat it as no published rules.
                parser.parse(["User-agent: *", "Allow: /"])
        except httpx.HTTPError:
            # Fail closed when robots.txt cannot be checked.
            parser.parse(["User-agent: *", "Disallow: /"])
        cache[robots_url] = parser
    return cache[robots_url].can_fetch(user_agent, url)


async def main():
    async with Actor:
        Actor.log.info("Actor started; checking local input")
        actor_input = await Actor.get_input()

        actor_input = actor_input or {}
        start_urls = actor_input.get("startUrls") or []

        Actor.log.info("Number of start URLs: %s", len(start_urls))
        max_pages = max(1, min(int(actor_input.get("maxPages", 10)), 30))
        timeout = max(5, min(int(actor_input.get("requestTimeoutSecs", 20)), 60))
        respect_robots = actor_input.get("respectRobotsTxt", True)
        enable_enrichment = actor_input.get("enableEnrichment", False)
        llm_api_url = actor_input.get("llmApiUrl", "")
        llm_api_key = actor_input.get("llmApiKey")
        llm_model = actor_input.get("llmModel", "")
        llm_timeout = actor_input.get("llmTimeoutSecs", 60)
        user_agent = actor_input.get(
            "userAgent",
            "WebsiteContactExtractor/1.0 (+https://apify.com)"
        )

        if not start_urls:
            raise ValueError("Input must contain at least one startUrls entry.")

        headers = {"User-Agent": user_agent, "Accept": "text/html,application/xhtml+xml"}
        limits = httpx.Limits(max_connections=5, max_keepalive_connections=2)
        robots_cache = {}
        summary = {}

        async with httpx.AsyncClient(
            headers=headers, timeout=timeout, follow_redirects=False,
            max_redirects=5, limits=limits
        ) as client:
            for entry in start_urls:
                raw_url = entry.get("url") if isinstance(entry, dict) else str(entry)

                if not raw_url:
                    continue

                start_url = normalize_url(str(raw_url))

                if not start_url.startswith(("http://", "https://")):
                    start_url = normalize_url("https://" + start_url)
                Actor.log.info("Processing start URL: %s", start_url)
                parsed_start = urlparse(start_url)
                if not parsed_start.hostname:
                    Actor.log.warning("Skipping invalid URL: %s", raw_url)
                    continue

                try:
                    validate_public_host(start_url)
                except ValueError as exc:
                    Actor.log.warning("Skipping unsafe URL %s: %s", start_url, exc)
                    continue

                base_host = parsed_start.hostname.lower()
                queue = [start_url]
                visited = set()
                aggregate = {"emails": set(), "phones": set(), "socialLinks": set()}

                pages_done = 0
                enrichment_data = None

                while queue and pages_done < max_pages:
                    page_url = queue.pop(0)
                    if page_url in visited:
                        continue
                    visited.add(page_url)
                    if respect_robots:
                        allowed = await robots_allowed(client, page_url, user_agent, robots_cache)
                        Actor.log.info("Robots decision for %s: %s", page_url, allowed)

                        if not allowed:
                            Actor.log.info("Blocked by robots.txt; skipping %s", page_url)
                            continue
                    try:
                        request_url = page_url
                        redirect_blocked = False

                        for _redirect in range(6):
                            validate_public_host(request_url)
                            response = await client.get(request_url)

                            if response.status_code not in (301, 302, 303, 307, 308):
                                break

                            location = response.headers.get("location")
                            if not location:
                                break

                            redirect_url = normalize_url(urljoin(request_url, location))

                            if not same_domain(redirect_url, base_host):
                                Actor.log.warning(
                                    "External redirect blocked: %s -> %s",
                                    request_url,
                                    redirect_url,
                                )

                                await Actor.push_data({
                                    "startUrl": start_url,
                                    "pageUrl": page_url,
                                    "statusCode": response.status_code,
                                    "error": "External redirect blocked",
                                    "redirectUrl": redirect_url,
                                    "emails": [],
                                    "phones": [],
                                    "socialLinks": [],
                                })

                                redirect_blocked = True
                                break

                            request_url = redirect_url
                        else:
                            raise httpx.TooManyRedirects("Too many redirects")

                        if redirect_blocked:
                            continue

                        content_type = response.headers.get("content-type", "").lower()

                        if response.status_code >= 400:
                            await Actor.push_data({
                                "startUrl": start_url,
                                "pageUrl": page_url,
                                "statusCode": response.status_code,
                                "error": "HTTP error",
                                "emails": [],
                                "phones": [],
                                "socialLinks": [],
                            })
                            continue

                        if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
                            continue

                        result = extract_contacts(response.text, str(response.url))

                        pages_done += 1
                        for key in aggregate:
                            aggregate[key].update(result[key])

                        await Actor.push_data({
                            "startUrl": start_url,
                            "pageUrl": str(response.url),
                            "statusCode": response.status_code,
                            "title": result["title"],
                            "emails": result["emails"],
                            "phones": result["phones"],
                            "socialLinks": result["socialLinks"],
                            "error": None
                        })
                        for link in prioritize_links(result["internalLinks"], str(response.url), base_host):
                            if link not in visited and link not in queue:
                                queue.append(link)
                    except httpx.HTTPError as exc:
                        Actor.log.warning("Request failed for %s: %s", page_url, exc)
                        await Actor.push_data({
                            "startUrl": start_url, "pageUrl": page_url,
                            "statusCode": None, "error": str(exc)[:300],
                            "emails": [], "phones": [], "socialLinks": []
                        })

                    # Be polite: low request rate, sequential crawling.
                    await asyncio.sleep(0.5)

                if enable_enrichment:
                    try:
                        enricher = Enricher(
                            enabled=True,
                            api_url=llm_api_url,
                            api_key=llm_api_key,
                            model=llm_model,
                            timeout=llm_timeout,
                        )

                        enrichment_data = enricher.enrich(
                            EnrichmentRequest(
                                website_url=start_url,
                                extracted_emails=sorted(aggregate["emails"]),
                            )
                        )

                    except Exception as exc:
                        Actor.log.warning(
                            "AI enrichment setup failed for %s: %s",
                            start_url,
                            exc,
                        )

                summary[start_url] = {
                    "pagesCrawled": pages_done,
                    "uniqueEmails": sorted(aggregate["emails"]),
                    "uniquePhones": sorted(aggregate["phones"]),
                    "uniqueSocialLinks": sorted(aggregate["socialLinks"]),
                }

                if enable_enrichment:
                    summary[start_url]["enrichment"] = (
                        enrichment_data.__dict__ if enrichment_data else None
                    )

        await Actor.push_data({
            "recordType": "summary",
            "results": summary
        })


if __name__ == "__main__":
    asyncio.run(main())
