#!/usr/bin/env python3
"""Validate that the site consistently advertises its HTTPS origin."""

from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


ORIGIN = "https://vainzof.co.il"
HTTP_ORIGINS = ("http://vainzof.co.il", "http://www.vainzof.co.il")


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.canonicals: list[str] = []
        self.urls: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        rel = (values.get("rel") or "").lower().split()
        if tag == "link" and "canonical" in rel:
            self.canonicals.append(values.get("href") or "")

        for attribute in ("href", "src", "action"):
            if values.get(attribute):
                self.urls.append((attribute, values[attribute] or ""))


def page_errors(root: Path) -> list[str]:
    errors: list[str] = []
    for page in sorted(root.rglob("*.html")):
        if ".git" in page.parts:
            continue
        parser = PageParser()
        parser.feed(page.read_text(encoding="utf-8"))
        relative_page = page.relative_to(root)

        if len(parser.canonicals) != 1:
            errors.append(f"{relative_page}: expected one canonical, found {len(parser.canonicals)}")
        elif not parser.canonicals[0].startswith(f"{ORIGIN}/"):
            errors.append(f"{relative_page}: canonical is not on the HTTPS origin: {parser.canonicals[0]}")

        for attribute, url in parser.urls:
            if url.startswith(HTTP_ORIGINS) or url.startswith("//vainzof.co.il") or url.startswith("//www.vainzof.co.il"):
                errors.append(f"{relative_page}: insecure internal {attribute}: {url}")
    return errors


def sitemap_errors(root: Path) -> list[str]:
    sitemap = root / "sitemap.xml"
    errors: list[str] = []
    try:
        document = ET.parse(sitemap)
    except (ET.ParseError, OSError) as exc:
        return [f"sitemap.xml: cannot parse sitemap: {exc}"]

    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locations = document.findall("sm:url/sm:loc", namespace)
    if not locations:
        errors.append("sitemap.xml: no URL entries found")
    for location in locations:
        url = (location.text or "").strip()
        if not url.startswith(f"{ORIGIN}/"):
            errors.append(f"sitemap.xml: non-HTTPS or unexpected origin: {url}")
    return errors


def robots_errors(root: Path) -> list[str]:
    content = (root / "robots.txt").read_text(encoding="utf-8")
    expected = f"Sitemap: {ORIGIN}/sitemap.xml"
    return [] if re.search(rf"^{re.escape(expected)}$", content, re.MULTILINE) else [
        f"robots.txt: expected {expected}"
    ]


def live_redirect_errors() -> list[str]:
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
            return None

    errors: list[str] = []
    opener = urllib.request.build_opener(NoRedirect)
    for source in HTTP_ORIGINS:
        request = urllib.request.Request(f"{source}/", method="HEAD")
        try:
            response = opener.open(request, timeout=15)
            status = response.status
            location = response.headers.get("Location", "")
        except urllib.error.HTTPError as exc:
            status = exc.code
            location = exc.headers.get("Location", "")
        except urllib.error.URLError as exc:
            errors.append(f"{source}/: live check failed: {exc.reason}")
            continue
        if status not in (301, 308):
            errors.append(f"{source}/: expected permanent redirect (301/308), got {status}")
        elif urlparse(location).scheme != "https":
            errors.append(f"{source}/: redirect is not HTTPS: {location}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--check-live-redirect", action="store_true")
    args = parser.parse_args()

    errors = page_errors(args.root) + sitemap_errors(args.root) + robots_errors(args.root)
    if args.check_live_redirect:
        errors += live_redirect_errors()

    if errors:
        print("HTTPS SEO validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("HTTPS SEO validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
