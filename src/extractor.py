import re
from urllib.parse import urljoin, urlparse, urldefrag

import phonenumbers
from bs4 import BeautifulSoup

EMAIL_RE = re.compile(r"(?i)(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
SOCIAL_HOSTS = (
    "linkedin.com", "facebook.com", "instagram.com",
    "x.com", "twitter.com", "youtube.com",
)
SKIP_EXTENSIONS = (
    ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".pdf",
    ".zip", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".mp4", ".mp3", ".css", ".js",
)
CONTACT_HINTS = ("contact", "about", "team", "company", "imprint", "support")


def normalize_url(url: str) -> str:
    url = url.strip()

    # Extract destination from a Markdown link.
    match = re.fullmatch(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", url)
    if match:
        url = match.group(2)

    url = url.strip("<>").strip()
    url, _fragment = urldefrag(url)
    return url


def same_domain(url: str, base_host: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    base_host = base_host.lower()
    return host == base_host or host.endswith("." + base_host) or base_host.endswith("." + host)


def extract_contacts(html: str, page_url: str):
    soup = BeautifulSoup(html, "html.parser")
    emails = set(EMAIL_RE.findall(soup.get_text(" ", strip=True)))
    phones = set()
    socials = set()
    links = []

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        lower = href.lower()
        if lower.startswith("mailto:"):
            candidate = href[7:].split("?")[0].strip()
            if candidate:
                emails.add(candidate)
        elif lower.startswith("tel:"):
            candidate = href[4:].split("?")[0].strip()
            if candidate:
                phones.add(candidate)
        else:
            absolute = normalize_url(urljoin(page_url, href))
            host = (urlparse(absolute).hostname or "").lower()
            if any(host == domain or host.endswith("." + domain) for domain in SOCIAL_HOSTS):
                socials.add(absolute)
            elif absolute.startswith(("http://", "https://")) and same_domain(absolute, urlparse(page_url).hostname or ""):
                path = urlparse(absolute).path.lower()
                if not any(path.endswith(ext) for ext in SKIP_EXTENSIONS):
                    links.append(absolute)

    # Parse phone-like strings from visible text. No default region is assumed:
    # only numbers that phonenumbers can validate internationally are retained.
    text = soup.get_text(" ", strip=True)
    for match in re.findall(r"(?<!\w)(?:\+\d[\d\s().-]{6,}\d|\(\d{2,4}\)[\d\s.-]{5,}\d)", text):
        candidate = re.sub(r"\s+", " ", match).strip()
        try:
            parsed = phonenumbers.parse(candidate, None)
            if phonenumbers.is_possible_number(parsed) and phonenumbers.is_valid_number(parsed):
                phones.add(phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL))
        except phonenumbers.NumberParseException:
            continue

    title = soup.title.get_text(" ", strip=True) if soup.title else None
    return {
        "emails": sorted(e.lower() for e in emails if len(e) <= 254),
        "phones": sorted(phones),
        "socialLinks": sorted(socials),
        "internalLinks": links,
        "title": title,
    }


def prioritize_links(links, page_url, base_host):
    unique = []
    seen = set()
    for link in links:
        if not same_domain(link, base_host):
            continue
        parsed = urlparse(link)
        if parsed.scheme not in ("http", "https"):
            continue
        key = normalize_url(link)
        if key not in seen:
            seen.add(key)
            unique.append(key)

    def score(url):
        path = urlparse(url).path.lower()
        return (0 if any(hint in path for hint in CONTACT_HINTS) else 1, len(path))

    return sorted(unique, key=score)
