#!/usr/bin/env python3
"""Validate that the site consistently advertises its HTTPS origin."""

from __future__ import annotations

import argparse
import re
import sys
import time
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


def sitemap_urls(root: Path) -> list[str]:
    """Return the canonical URLs advertised in the sitemap."""
    document = ET.parse(root / "sitemap.xml")
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    return [
        (location.text or "").strip()
        for location in document.findall("sm:url/sm:loc", namespace)
        if (location.text or "").strip()
    ]


def live_redirect_errors(root: Path) -> list[str]:
    """Verify hosting-layer redirects without allowing urllib to follow them."""
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
            return None

    errors: list[str] = []
    opener = urllib.request.build_opener(NoRedirect)
    canonical_urls = sitemap_urls(root)
    paths = sorted({urlparse(url).path or "/" for url in canonical_urls})

    # Check every published path, not only the home page. This prevents a
    # server/CDN rule that redirects `/` while still serving HTTP 200 elsewhere.
    for source in HTTP_ORIGINS:
        for path in paths:
            source_url = f"{source}{path}"
            expected = f"{ORIGIN}{path}"
            request = urllib.request.Request(source_url, method="GET")
            try:
                response = opener.open(request, timeout=15)
                status = response.status
                location = response.headers.get("Location", "")
            except urllib.error.HTTPError as exc:
                status = exc.code
                location = exc.headers.get("Location", "")
            except urllib.error.URLError as exc:
                errors.append(f"{source_url}: live check failed: {exc.reason}")
                continue
            if status not in (301, 308):
                errors.append(f"{source_url}: expected permanent redirect (301/308), got {status}")
            elif location != expected:
                errors.append(f"{source_url}: expected direct redirect to {expected}, got {location}")

    # GitHub Pages' directory routing should permanently consolidate the
    # extensionless spelling to the canonical trailing-slash URL in one hop.
    pension_alias = f"{ORIGIN}/find-all-pension-funds"
    pension_canonical = f"{pension_alias}/"
    request = urllib.request.Request(pension_alias, method="GET")
    try:
        response = opener.open(request, timeout=15)
        status = response.status
        location = response.headers.get("Location", "")
    except urllib.error.HTTPError as exc:
        status = exc.code
        location = exc.headers.get("Location", "")
    except urllib.error.URLError as exc:
        errors.append(f"{pension_alias}: live check failed: {exc.reason}")
    else:
        if status not in (301, 308):
            errors.append(f"{pension_alias}: expected permanent redirect (301/308), got {status}")
        elif location != pension_canonical:
            errors.append(
                f"{pension_alias}: expected direct redirect to {pension_canonical}, got {location}"
            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--check-live-redirect", action="store_true")
    parser.add_argument("--live-attempts", type=int, default=1)
    parser.add_argument("--live-retry-delay", type=float, default=10)
    args = parser.parse_args()

    errors = page_errors(args.root) + sitemap_errors(args.root) + robots_errors(args.root)
    if args.check_live_redirect:
        live_errors: list[str] = []
        for attempt in range(1, max(args.live_attempts, 1) + 1):
            live_errors = live_redirect_errors(args.root)
            if not live_errors:
                break
            if attempt < args.live_attempts:
                print(f"Live redirect check failed (attempt {attempt}); retrying...")
                time.sleep(max(args.live_retry_delay, 0))
        errors += live_errors

    if errors:
        print("HTTPS SEO validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("HTTPS SEO validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
