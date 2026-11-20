# Website Contact & Business Information Extractor

Find publicly available contact information on websites—without manually checking every page.

**Website Contact & Business Information Extractor** crawls a website and its relevant internal pages to discover publicly listed email addresses, phone numbers, and social media profiles.

Enter a website URL, choose your crawl limit, and let the Actor do the work.

---

## What can it find?

- 📧 **Email addresses** – emails publicly displayed on the website
- 📞 **Phone numbers** – phone numbers found in page content and contact links
- 🌐 **Social media profiles** – links to LinkedIn, Facebook, Instagram, X/Twitter, YouTube, and other supported social platforms
- 📄 **Website pages** – the pages visited and their extraction results

All discovered contacts are collected from publicly accessible website content.

## How to use

### 1. Enter a website

Add the website you want to explore in the **Start URLs** field.

For example:

`https://example.com`

### 2. Choose your crawl limit

Specify how many pages the Actor can visit for each starting website.

- **Max pages:** Limits the number of pages crawled per website.
- **Request timeout:** Controls how long the Actor waits for a page to respond.
- **Respect robots.txt:** Allows the Actor to respect website crawling rules.

If you're trying it for the first time, start with a small page limit.

### 3. Run the Actor

Click **Start** and the Actor will visit the starting page and prioritize relevant internal pages, such as contact, about, and other pages that may contain contact information.

### 4. Explore your results

Review the results in the Apify Dataset. You can see the information found on individual pages as well as a consolidated summary of unique contacts for each website.

---

## What you'll get

Results are organized to make them easy to review and use.

### Contact information

| Field | Description |
|---|---|
| Emails | Email addresses discovered on the website |
| Phones | Phone numbers found during crawling |
| Social links | Social media profile URLs |

### Website information

| Field | Description |
|---|---|
| Website URL | Original website submitted |
| Page URL | Specific page where information was found |
| Page title | Title of the visited page |
| Status code | HTTP response status |
| Error | Any error encountered while processing the page |

### Consolidated summary

At the end of the crawl, the Actor also provides a summary for each website containing:

- Total pages crawled
- Unique email addresses
- Unique phone numbers
- Unique social profile links

Duplicates are removed from the consolidated contact summary.

---

## Who can use it?

**Sales & Business Development**

Discover publicly listed contact information when researching prospective businesses.

**Marketing Professionals**

Collect website contact details to support research and outreach planning.

**Small Businesses & Freelancers**

Find contact information on websites without manually navigating multiple pages.

**Researchers**

Gather publicly available contact information as part of website and business research.

**Recruiters**

Explore company websites to locate publicly listed contact channels.

---

## Simple, lightweight & transparent

- No API key required for the extraction process
- No AI-generated contact information
- Extracts information from website content rather than inventing contacts
- Crawls internal pages of the same website
- Prioritizes relevant pages for contact discovery
- Consolidates duplicate contacts in the final summary
- Uses crawl limits to help control execution

---

## Important limitations

- The Actor can only find information that is publicly accessible and present on the pages it visits.
- Not every website publishes email addresses or phone numbers.
- Some websites may block automated requests or limit access.
- Email addresses and phone numbers are **not independently verified** for accuracy or active status.
- The Actor does not guarantee that all contacts on a website will be discovered.
- It does not bypass authentication, CAPTCHAs, paywalls, or other access restrictions.
- Results depend on website structure, content, accessibility, and the configured page limit.

---

## Responsible use

Use this Actor responsibly and only on websites you are authorized to access.

Respect website terms of service, robots.txt instructions, applicable privacy laws, and data-protection requirements. Contact information should be used for legitimate purposes. This Actor is not intended for indiscriminate harvesting of personal information or spam.

---

## Get started

Enter a website URL, set your page limit, and start discovering publicly available business contact information.

**Less manual browsing. More organized contact research.**