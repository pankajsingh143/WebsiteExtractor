import unittest

from src.extractor import (
    extract_contacts,
    normalize_url,
    prioritize_links,
    same_domain,
)
from src.main import validate_public_host


class ExtractorTests(unittest.TestCase):
    def test_normalize_url_removes_fragment(self):
        self.assertEqual(
            normalize_url("https://example.com/contact#top"),
            "https://example.com/contact",
        )

    def test_same_domain_matches_base_and_subdomains(self):
        self.assertTrue(same_domain("https://example.com/about", "example.com"))
        self.assertTrue(same_domain("https://www.example.com/contact", "example.com"))
        self.assertTrue(same_domain("https://example.com", "example.com"))
        self.assertFalse(same_domain("https://not-example.com", "example.com"))

    def test_extract_contacts_handles_emails_phones_and_social_links(self):
        html = """
        <html>
          <head><title>Example Contact</title></head>
          <body>
            <a href="mailto:hello@example.com">Email</a>
            <a href="tel:+1-415-555-2671">Call</a>
            <a href="https://www.linkedin.com/company/example">LinkedIn</a>
            <a href="/contact">Contact</a>
            <a href="/about-us">About</a>
            <p>Call +1 (415) 555-2671 or reach us at hello@example.com</p>
          </body>
        </html>
        """

        result = extract_contacts(html, "https://example.com/")

        self.assertEqual(result["emails"], ["hello@example.com"])
        self.assertIn("+1 415-555-2671", result["phones"])
        self.assertIn("+1-415-555-2671", result["phones"])
        self.assertEqual(result["socialLinks"], ["https://www.linkedin.com/company/example"])
        self.assertEqual(result["title"], "Example Contact")
        self.assertCountEqual(result["internalLinks"], ["https://example.com/contact", "https://example.com/about-us"])

    def test_prioritize_links_prefers_contact_paths(self):
        links = [
            "https://example.com/blog/post-1",
            "https://example.com/contact",
            "https://example.com/about",
        ]

        prioritized = prioritize_links(links, "https://example.com/", "example.com")
        self.assertEqual(prioritized, [
            "https://example.com/about",
            "https://example.com/contact",
            "https://example.com/blog/post-1",
        ])

    def test_validate_public_host_accepts_public_domain_and_rejects_private_ip(self):
        validate_public_host("https://example.com")

        with self.assertRaises(ValueError):
            validate_public_host("http://127.0.0.1")

        with self.assertRaises(ValueError):
            validate_public_host("http://10.0.0.5")


if __name__ == "__main__":
    unittest.main()
