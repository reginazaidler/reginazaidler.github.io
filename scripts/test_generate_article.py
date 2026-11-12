import json
import re
import unittest
from pathlib import Path

from scripts.generate_article import build_html, linkify


def json_ld(html):
    return [
        json.loads(payload)
        for payload in re.findall(
            r'<script type="application/ld\+json">(.*?)</script>', html, re.S
        )
    ]


class GenerateArticleTest(unittest.TestCase):
    def test_internal_links_render_once(self):
        source = (
            '[איך בודקים & משווים](check-insurance-policies.html), '
            'insurance-types.html. '
            '<a href="insurance-types.html">insurance-types.html</a> '
            'https://example.com/insurance-types.html'
        )
        expected = (
            '<a href="check-insurance-policies.html">איך בודקים &amp; משווים</a>, '
            '<a href="insurance-types.html">סוגי ביטוחים בישראל</a>. '
            '<a href="insurance-types.html">insurance-types.html</a> '
            'https://example.com/insurance-types.html'
        )
        self.assertEqual(linkify(source), expected)
        self.assertEqual(linkify(expected), expected)

    def test_faq_schema_uses_visible_questions_and_answers(self):
        meta = dict(slug="test", h1="Test", keyword="test", meta_description="Test")
        article = dict(intro="Intro", sections=[])
        for faq in (None, [], [{"q": "Question", "a": " "}], [None]):
            with self.subTest(faq=faq):
                html = build_html(meta, dict(article, faq=faq), "2026-11-08")
                self.assertEqual([data["@type"] for data in json_ld(html)], ["Article"])

        faq = [{"q": "מה בודקים?", "a": "בודקים את תנאי הפוליסה."}]
        html = build_html(meta, dict(article, faq=faq), "2026-11-08")
        self.assertIn(f'<h3>{faq[0]["q"]}</h3>', html)
        self.assertIn(f'<p>{faq[0]["a"]}</p>', html)
        self.assertEqual(json_ld(html)[1], {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [{
                "@type": "Question",
                "name": faq[0]["q"],
                "acceptedAnswer": {"@type": "Answer", "text": faq[0]["a"]},
            }],
        })

    def test_published_article(self):
        path = Path(__file__).resolve().parents[1] / "double-insurance-claim-check.html"
        html = path.read_text(encoding="utf-8")
        self.assertNotRegex(html, r'\]\(<a\b')
        faq_section = html.split('<section id="faq"', 1)[1].split("</section>", 1)[0]
        visible = re.findall(r"<h3>(.*?)</h3>\s*<p>(.*?)</p>", faq_section)
        schema = next(data for data in json_ld(html) if data["@type"] == "FAQPage")
        self.assertEqual(len(visible), 3)
        self.assertEqual(
            [(item["name"], item["acceptedAnswer"]["text"]) for item in schema["mainEntity"]],
            visible,
        )
