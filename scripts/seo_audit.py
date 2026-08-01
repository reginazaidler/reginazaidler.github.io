#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import smtplib
import ssl
import sys
from dataclasses import asdict, dataclass
from datetime import date
from email.message import EmailMessage
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib import request

DEFAULT_EMAIL_RECIPIENTS = [
    "reginazaidler@gmail.com",
    "vainzofyuval@yahoo.com",
]


@dataclass
class PageAudit:
    page: str
    has_title: bool
    has_description: bool
    has_canonical: bool
    has_og_image: bool
    has_ld_json: bool
    h1_count: int
    noindex: bool


class SEOParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.has_title = False
        self.has_description = False
        self.has_canonical = False
        self.has_og_image = False
        self.has_ld_json = False
        self.h1_count = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs):
        attrs_dict = dict(attrs)
        if tag == "title":
            self._in_title = True

        if tag == "meta" and attrs_dict.get("name") == "description":
            self.has_description = True

        rel_attr = attrs_dict.get("rel")
        if tag == "link" and rel_attr:
            rel_values = rel_attr if isinstance(rel_attr, list) else str(rel_attr).split()
            if "canonical" in rel_values:
                self.has_canonical = True

        if tag == "meta" and attrs_dict.get("property") == "og:image":
            self.has_og_image = True

        if tag == "script" and attrs_dict.get("type") == "application/ld+json":
            self.has_ld_json = True

        if tag == "h1":
            self.h1_count += 1

    def handle_endtag(self, tag: str):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str):
        if self._in_title and data.strip():
            self.has_title = True


def audit_page(path: Path) -> PageAudit:
    parser = SEOParser()
    parser.feed(path.read_text(encoding="utf-8", errors="ignore"))
    return PageAudit(
        page=path.as_posix(),
        has_title=parser.has_title,
        has_description=parser.has_description,
        has_canonical=parser.has_canonical,
        has_og_image=parser.has_og_image,
        has_ld_json=parser.has_ld_json,
        h1_count=parser.h1_count,
        noindex=page_has_noindex(path),
    )


SKIP_PAGES = {"choose-insurance-agent.html", "thanks.html"}


def page_has_noindex(path: Path) -> bool:
    content = path.read_text(encoding="utf-8", errors="ignore")
    return bool(re.search(r'noindex', content[:2000], re.IGNORECASE)
                and re.search(r'name=["\']robots["\']', content[:2000], re.IGNORECASE))


def extract_page_title(path: Path) -> str:
    content = path.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r"<title>(.*?)</title>", content, re.DOTALL)
    return m.group(1).strip() if m else ""


def page_to_url(path: Path, root: Path) -> str:
    rel = path.relative_to(root)
    parts = rel.parts
    if len(parts) == 1:
        return f"https://vainzof.co.il/{parts[0]}"
    elif len(parts) == 2 and parts[1] == "index.html":
        return f"https://vainzof.co.il/{parts[0]}"
    return f"https://vainzof.co.il/{'/'.join(parts)}"


def sync_sitemap(sitemap_path: Path, pages: list[Path], root: Path, today: str) -> list[str]:
    """Add HTML pages missing from sitemap.xml. Returns list of added URLs."""
    if not sitemap_path.exists():
        return []
    content = sitemap_path.read_text(encoding="utf-8")
    added: list[str] = []
    for page in pages:
        if page.name in SKIP_PAGES:
            continue
        if page_has_noindex(page):
            continue
        url = page_to_url(page, root)
        if url in content:
            continue
        entry = f"\n  <url>\n    <loc>{url}</loc>\n    <lastmod>{today}</lastmod>\n  </url>"
        content = content.replace("</urlset>", entry + "\n\n</urlset>")
        added.append(url)
        print(f"[sync-sitemap] Added: {url}")
    if added:
        sitemap_path.write_text(content, encoding="utf-8")
    return added


def sync_llms_txt(llms_path: Path, added_urls: list[str], root: Path) -> None:
    """Append newly added pages to llms.txt."""
    if not llms_path.exists() or not added_urls:
        return
    content = llms_path.read_text(encoding="utf-8")
    lines = content.splitlines(keepends=True)
    last_list_idx = max((i for i, l in enumerate(lines) if l.startswith("- ")), default=-1)
    new_lines: list[str] = []
    for url in added_urls:
        if url in content:
            continue
        slug = url.replace("https://vainzof.co.il/", "")
        page_path = root / (slug if slug.endswith(".html") else f"{slug}/index.html")
        title = extract_page_title(page_path) if page_path.exists() else slug
        new_lines.append(f"- {title}: {url}\n")
        print(f"[sync-llms] Added: {url}")
    if new_lines:
        insert_at = last_list_idx + 1 if last_list_idx != -1 else len(lines)
        for i, line in enumerate(new_lines):
            lines.insert(insert_at + i, line)
        llms_path.write_text("".join(lines), encoding="utf-8")


def count_sitemap_urls(path: Path) -> int:
    xml = path.read_text(encoding="utf-8", errors="ignore")
    return len(re.findall(r"<loc>", xml))


def bool_count(items: list[PageAudit], field: str) -> int:
    return sum(1 for item in items if getattr(item, field))


def build_results(audits: list[PageAudit]) -> dict[str, Any]:
    indexable_audits = [a for a in audits if not a.noindex]
    noindex_pages = [a.page for a in audits if a.noindex]

    missing_description = [a.page for a in indexable_audits if not a.has_description]
    missing_canonical = [a.page for a in indexable_audits if not a.has_canonical]
    missing_og_image = [a.page for a in indexable_audits if not a.has_og_image]
    missing_ld_json = [a.page for a in indexable_audits if not a.has_ld_json]
    invalid_h1 = [{"page": a.page, "h1_count": a.h1_count} for a in indexable_audits if a.h1_count != 1]

    issues_total = (
        len(missing_description)
        + len(missing_canonical)
        + len(missing_og_image)
        + len(missing_ld_json)
        + len(invalid_h1)
    )

    sitemap_urls = count_sitemap_urls(Path("sitemap.xml")) if Path("sitemap.xml").exists() else 0

    return {
        "scan_date": date.today().isoformat(),
        "pages_scanned": len(audits),
        "indexable_pages_scanned": len(indexable_audits),
        "noindex_pages_scanned": len(noindex_pages),
        "sitemap_urls": sitemap_urls,
        "totals": {
            "title_ok": bool_count(indexable_audits, "has_title"),
            "description_ok": bool_count(indexable_audits, "has_description"),
            "canonical_ok": bool_count(indexable_audits, "has_canonical"),
            "og_image_ok": bool_count(indexable_audits, "has_og_image"),
            "ld_json_ok": bool_count(indexable_audits, "has_ld_json"),
            "h1_ok": len(indexable_audits) - len(invalid_h1),
        },
        "issues": {
            "missing_description": missing_description,
            "missing_canonical": missing_canonical,
            "missing_og_image": missing_og_image,
            "missing_ld_json": missing_ld_json,
            "invalid_h1": invalid_h1,
        },
        "issues_total": issues_total,
        "noindex_pages": noindex_pages,
        "pages": [asdict(a) for a in audits],
    }


def generate_markdown_report(results: dict[str, Any]) -> str:
    lines = [
        "# סריקת SEO - vainzof.co.il",
        "",
        f"תאריך סריקה: {results['scan_date']}",
        "היקף: בדיקת SEO טכנית על קבצי HTML סטטיים בריפו (`*.html`) + בדיקת `robots.txt` ו-`sitemap.xml`.",
        "הבדיקה מתמקדת בעמודים אינדקסביליים; עמודים עם `noindex` נספרים בנפרד ולא מסומנים כתקלה.",
        "",
        "## מתודולוגיה",
        "",
        "הסריקה בוצעה באמצעות סקריפט Python מקומי (`scripts/seo_audit.py`) שבודק לכל עמוד:",
        "- תגית `title`",
        "- `meta description`",
        "- `canonical`",
        "- `og:image`",
        "- קיום `h1` יחיד",
        "- קיום Schema (`application/ld+json`)",
        "",
        "## סיכום תוצאות",
        "",
        f"- נסרקו **{results['pages_scanned']} עמודי HTML** בסך הכול.",
        f"- מתוכם **{results['indexable_pages_scanned']} עמודים אינדקסביליים** ו-{results['noindex_pages_scanned']} עמודי `noindex`/הפניה.",
        f"- `title`: תקין ב-{results['totals']['title_ok']} עמודים אינדקסביליים.",
        f"- `meta description`: תקין ב-{results['totals']['description_ok']} עמודים אינדקסביליים.",
        f"- `canonical`: תקין ב-{results['totals']['canonical_ok']} עמודים אינדקסביליים.",
        f"- `og:image`: תקין ב-{results['totals']['og_image_ok']} עמודים אינדקסביליים.",
        f"- Schema (`ld+json`): תקין ב-{results['totals']['ld_json_ok']} עמודים אינדקסביליים.",
        f"- `h1`: תקין ב-{results['totals']['h1_ok']} עמודים אינדקסביליים.",
        f"- `sitemap.xml`: כולל {results['sitemap_urls']} כתובות URL.",
        "- `robots.txt`: קיים בריפו.",
        "",
        "## ממצאים",
        "",
    ]

    def add_missing_block(title: str, values: list[str]):
        lines.append(f"### {title}")
        if values:
            for index, value in enumerate(values, start=1):
                lines.append(f"{index}. `{value}`")
        else:
            lines.append("אין ממצאים.")
        lines.append("")

    issues = results["issues"]
    add_missing_block("עמודים ללא `meta description`", issues["missing_description"])
    add_missing_block("עמודים ללא `canonical`", issues["missing_canonical"])
    add_missing_block("עמודים ללא `og:image`", issues["missing_og_image"])
    add_missing_block("עמודים ללא Schema (`ld+json`)", issues["missing_ld_json"])

    lines.append("### עמודים עם חריגה בכמות `h1`")
    if issues["invalid_h1"]:
        for item in issues["invalid_h1"]:
            lines.append(f"- `{item['page']}` - נמצאו `{item['h1_count']}` תגיות `h1`.")
    else:
        lines.append("אין ממצאים.")

    lines.extend(
        [
            "",
            "## הערות",
            "",
            "- עמודי `noindex` והפניות לא נדרשים לכלול את כל תגיות ה-SEO ולכן אינם נספרים כממצאים לתיקון.",
            "- זוהי בדיקת SEO טכנית בסיסית בלבד, ללא בדיקת ביצועים/Core Web Vitals.",
            "- כברירת מחדל הסקריפט לא מתקן אוטומטית קבצים; הוא רק מדווח כדי למנוע שינויים לא בטוחים בתוכן.",
            "- כדי לנתח אינדוקס בפועל והופעה בתוצאות חיפוש, יש להשלים בדיקה ב-Google Search Console.",
            "",
        ]
    )

    return "\n".join(lines)


def post_webhook(url: str, payload: dict[str, Any]) -> None:
    req = request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with request.urlopen(req, timeout=20):
        return


def email_summary_subject(results: dict[str, Any]) -> str:
    return f"SEO Audit {results['scan_date']} | issues={results['issues_total']} | pages={results['pages_scanned']}"


def email_summary_body(results: dict[str, Any], report_path: str) -> str:
    issues = results["issues"]
    return "\n".join(
        [
            f"SEO scan date: {results['scan_date']}",
            f"Pages scanned: {results['pages_scanned']}",
            f"Issues total: {results['issues_total']}",
            f"Report file: {report_path}",
            "",
            "Issues:",
            f"- missing_description: {len(issues['missing_description'])}",
            f"- missing_canonical: {len(issues['missing_canonical'])}",
            f"- missing_og_image: {len(issues['missing_og_image'])}",
            f"- missing_ld_json: {len(issues['missing_ld_json'])}",
            f"- invalid_h1: {len(issues['invalid_h1'])}",
        ]
    )


def send_email_summary(
    results: dict[str, Any],
    report_path: str,
    recipients: list[str],
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    smtp_from: str,
) -> None:
    msg = EmailMessage()
    msg["Subject"] = email_summary_subject(results)
    msg["From"] = smtp_from
    msg["To"] = ", ".join(recipients)
    msg.set_content(email_summary_body(results, report_path))

    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
        server.starttls(context=context)
        server.login(smtp_user, smtp_password)
        server.send_message(msg)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit static HTML SEO tags and generate report")
    parser.add_argument(
        "--output-md",
        default="seo-scan-report.md",
        help="Path to markdown report output (default: seo-scan-report.md)",
    )
    parser.add_argument(
        "--output-json",
        default="",
        help="Optional path to write JSON audit output",
    )
    parser.add_argument(
        "--fail-on-issues",
        action="store_true",
        help="Exit with code 1 when issues are found (useful for CI)",
    )
    parser.add_argument(
        "--webhook-url",
        default="",
        help="Optional webhook URL to POST JSON summary after scan",
    )
    parser.add_argument(
        "--send-email",
        action="store_true",
        help="Send scan summary via SMTP email",
    )
    parser.add_argument(
        "--email-to",
        nargs="+",
        default=DEFAULT_EMAIL_RECIPIENTS,
        help="Email recipients for summary (default: project recipients)",
    )
    parser.add_argument(
        "--smtp-host",
        default="",
        help="SMTP host (required with --send-email)",
    )
    parser.add_argument(
        "--smtp-port",
        default=587,
        type=int,
        help="SMTP port (default: 587)",
    )
    parser.add_argument(
        "--smtp-user",
        default="",
        help="SMTP username (required with --send-email)",
    )
    parser.add_argument(
        "--smtp-password",
        default="",
        help="SMTP password (required with --send-email)",
    )
    parser.add_argument(
        "--smtp-from",
        default="",
        help="Sender address (required with --send-email)",
    )
    return parser.parse_args()


def collect_html_pages(root: Path) -> list[Path]:
    return sorted(
        page
        for page in root.rglob("*.html")
        if ".git" not in page.parts
        and "node_modules" not in page.parts
        and "__pycache__" not in page.parts
    )


def main() -> int:
    args = parse_args()
    root = Path(".")
    pages = collect_html_pages(root)

    # Sync sitemap.xml and llms.txt with any new pages
    today = date.today().isoformat()
    added_urls = sync_sitemap(Path("sitemap.xml"), pages, root, today)
    sync_llms_txt(Path("llms.txt"), added_urls, root)

    audits = [audit_page(page) for page in pages]
    results = build_results(audits)

    markdown_report = generate_markdown_report(results)
    Path(args.output_md).write_text(markdown_report, encoding="utf-8")

    if args.output_json:
        Path(args.output_json).write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.webhook_url:
        payload = {
            "scan_date": results["scan_date"],
            "pages_scanned": results["pages_scanned"],
            "issues_total": results["issues_total"],
            "issues": results["issues"],
        }
        post_webhook(args.webhook_url, payload)

    if args.send_email:
        smtp_values = [args.smtp_host, args.smtp_user, args.smtp_password, args.smtp_from]
        if not all(smtp_values):
            print("Missing SMTP args: --smtp-host --smtp-user --smtp-password --smtp-from", file=sys.stderr)
            return 2
        send_email_summary(
            results=results,
            report_path=args.output_md,
            recipients=args.email_to,
            smtp_host=args.smtp_host,
            smtp_port=args.smtp_port,
            smtp_user=args.smtp_user,
            smtp_password=args.smtp_password,
            smtp_from=args.smtp_from,
        )
        print(f"Email sent to: {', '.join(args.email_to)}")

    print(f"Wrote {args.output_md}")
    if args.output_json:
        print(f"Wrote {args.output_json}")

    if args.fail_on_issues and results["issues_total"] > 0:
        print(f"Found {results['issues_total']} SEO issue(s)")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
