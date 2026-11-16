# Website Contact & Business Information Extractor

A deterministic Apify Actor that crawls a website's homepage and a small set of same-domain pages to extract publicly displayed business contact information such as:

- email addresses
- phone numbers
- social profile URLs (LinkedIn, Facebook, Instagram, X/Twitter, YouTube)

The project uses HTML parsing and regex-based validation rather than an LLM or external API, so it runs without API keys and remains fast and transparent.

## Why this project exists

This Actor is designed to help with legitimate business research and contact-discovery workflows where the target website explicitly publishes contact details. It is intentionally narrow: it only follows same-domain links, prioritizes likely contact pages, and extracts information that is already visible in public web content.

## Important usage boundaries

Use this tool only on websites you are authorized to access and operate within the site's terms, robots.txt rules, and applicable privacy/data-protection laws. This project is not intended for mass harvesting of personal information.

Built-in safeguards include:

- rejecting private, loopback and non-public IP destinations
- blocking redirect chains that resolve to disallowed destinations
- honoring `robots.txt` when enabled
- limiting total pages crawled to a conservative cap
- refusing to bypass logins, CAPTCHAs, paywalls or access controls

## How it works

The implementation is split into two core pieces:

- `src/main.py` handles actor input, crawl loop, request safety checks, robots.txt enforcement, redirect handling, and dataset output.
- `src/extractor.py` extracts contact data from HTML, normalizes URLs, looks for visible social links, and ranks same-domain links for follow-up crawling.

The crawler:

1. validates the starting URL and rejects unsafe destinations
2. checks robots.txt if enabled
3. fetches the page with a small timeout and redirect cap
4. parses visible text and anchor tags for contact details
5. records the page as a dataset item
6. follows prioritized same-domain links until the page limit is reached
7. pushes a final summary with deduplicated results

## Project structure

```text
.
├── .actor/
│   ├── INPUT.example.json
│   └── actor.json
├── src/
│   ├── __init__.py
│   ├── __main__.py
│   ├── extractor.py
│   └── main.py
├── Dockerfile
├── README.md
├── requirements.txt
└── .gitignore
```

## Requirements

- Python 3.11+
- Docker (for containerized Apify deployment)
- Access to a website you're allowed to crawl

## Local development

Create and activate a virtual environment, install dependencies, and run the actor locally:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m src
```

For local execution, create a runtime input file at `storage/key_value_stores/default/INPUT.json` using the example in `.actor/INPUT.example.json`.

## Input schema

Example payload:

```json
{
  "startUrls": [{"url": "https://example.com"}],
  "maxPages": 10,
  "requestTimeoutSecs": 20,
  "respectRobotsTxt": true,
  "userAgent": "WebsiteContactExtractor/1.0 (+https://apify.com)"
}
```

Supported fields:

- `startUrls`: array of objects with a `url` value; required
- `maxPages`: maximum number of pages to crawl per starting URL (bounded by the actor logic, default 10)
- `requestTimeoutSecs`: per-request timeout in seconds
- `respectRobotsTxt`: whether to honor robots.txt for same-domain navigation
- `userAgent`: custom HTTP user agent header

## Output format

Each page fetch produces a dataset item like this:

```json
{
  "startUrl": "https://example.com",
  "pageUrl": "https://example.com/contact",
  "emails": ["info@example.com"],
  "phones": ["+1 555 123 4567"],
  "socialLinks": ["https://www.linkedin.com/company/example"],
  "statusCode": 200,
  "title": "Contact us",
  "error": null
}
```

At the end of the run, the actor also pushes a summary object that contains deduplicated contact data across all crawled pages:

```json
{
  "recordType": "summary",
  "results": {
    "https://example.com": {
      "pagesCrawled": 4,
      "uniqueEmails": ["info@example.com"],
      "uniquePhones": ["+1 555 123 4567"],
      "uniqueSocialLinks": ["https://www.linkedin.com/company/example"]
    }
  }
}
```

## Deployment

### Apify

1. Install the Apify CLI:
   ```bash
   npm install -g apify-cli
   ```
2. Log in:
   ```bash
   apify login
   ```
3. From this project directory, push the actor:
   ```bash
   apify push
   ```
4. Set the input in the Apify Console and run a test against a site you control or are authorized to crawl.
5. Review dataset output and logs before publishing.

The project includes a Dockerfile and actor metadata compatible with Apify Python actors.

## Production notes

Before using this in production or publishing it publicly, consider:

- validating against a range of allowed websites
- checking false positives such as `mailto:` and `tel:` links or generic text matches
- reviewing international phone parsing and duplicate URL handling
- keeping crawl limits conservative
- adding clear privacy and data-handling disclosures if distributing the actor
- confirming that pricing and storage costs are acceptable for your deployment model

This project intentionally favors accuracy, safety, and legal compliance over broad crawling and aggressive extraction.
