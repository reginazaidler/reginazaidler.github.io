#!/usr/bin/env python3
"""
sync_indexes.py
───────────────
Scans all HTML pages and adds any missing entries to sitemap.xml and llms.txt.
Designed to run frequently (e.g. every 30 minutes) so new articles are indexed fast.

Usage:
    python3 scripts/sync_indexes.py
    python3 scripts/sync_indexes.py --dry-run
"""
from __future__ import annotations

import argparse
import re
import subprocess
from datetime import date
from pathlib import Path

SITE_BASE = "https://vainzof.co.il"
SKIP_PAGES = {"choose-insurance-agent.html", "thanks.html"}
REMOVED_PAGE_LINK_RE = re.compile(
    r'<a\b[^>]*href=["\'][^"\']*calculator\.html(?:[?#][^"\']*)?["\'][^>]*>.*?</a>',
    re.IGNORECASE | re.DOTALL,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Sync sitemap.xml and llms.txt with all HTML pages")
    p.add_argument("--dry-run", action="store_true", help="Print changes without writing files")
    return p.parse_args()


def collect_pages(root: Path) -> list[Path]:
    return sorted(
        p for p in root.rglob("*.html")
        if ".git" not in p.parts
        and p.name not in SKIP_PAGES
    )


def remove_retired_page_links(root: Path, dry_run: bool) -> list[Path]:
    """Remove links to pages that were permanently retired from the site."""
    changed: list[Path] = []
    for path in sorted(p for p in root.rglob("*.html") if ".git" not in p.parts):
        content = path.read_text(encoding="utf-8", errors="ignore")
        cleaned = REMOVED_PAGE_LINK_RE.sub("", content)
        if cleaned == content:
            continue
        changed.append(path)
        print(f"[cleanup] {'[DRY] ' if dry_run else ''}Removed calculator link: {path}")
        if not dry_run:
            path.write_text(cleaned, encoding="utf-8")
    return changed


def has_noindex(path: Path) -> bool:
    content = path.read_text(encoding="utf-8", errors="ignore")[:2000]
    return bool(
        re.search(r"noindex", content, re.IGNORECASE)
        and re.search(r'name=["\']robots["\']', content, re.IGNORECASE)
    )


def page_url(path: Path, root: Path) -> str:
    parts = path.relative_to(root).parts
    if len(parts) == 1:
        return f"{SITE_BASE}/{parts[0]}"
    if len(parts) == 2 and parts[1] == "index.html":
        return f"{SITE_BASE}/{parts[0]}"
    return f"{SITE_BASE}/{'/'.join(parts)}"


def page_title(path: Path) -> str:
    content = path.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r"<title>(.*?)</title>", content, re.DOTALL)
    return m.group(1).strip() if m else path.stem


def sync_sitemap(sitemap: Path, pages: list[Path], root: Path, today: str, dry_run: bool) -> list[str]:
    if not sitemap.exists():
        print("[sitemap] sitemap.xml not found, skipping")
        return []

    content = sitemap.read_text(encoding="utf-8")
    added: list[str] = []

    for page in pages:
        if has_noindex(page):
            continue
        url = page_url(page, root)
        if url in content:
            continue
        entry = f"\n  <url>\n    <loc>{url}</loc>\n    <lastmod>{today}</lastmod>\n  </url>"
        content = content.replace("</urlset>", entry + "\n\n</urlset>")
        added.append(url)
        print(f"[sitemap] {'[DRY] ' if dry_run else ''}Added: {url}")

    if added and not dry_run:
        sitemap.write_text(content, encoding="utf-8")

    return added


def sync_llms(llms: Path, added_urls: list[str], root: Path, dry_run: bool) -> None:
    if not llms.exists() or not added_urls:
        return

    content = llms.read_text(encoding="utf-8")
    lines = content.splitlines(keepends=True)
    last_list_idx = max((i for i, l in enumerate(lines) if l.startswith("- ")), default=-1)

    new_lines: list[str] = []
    for url in added_urls:
        if url in content:
            continue
        slug = url.replace(f"{SITE_BASE}/", "")
        page = root / (slug if slug.endswith(".html") else f"{slug}/index.html")
        title = page_title(page) if page.exists() else slug
        new_lines.append(f"- {title}: {url}\n")
        print(f"[llms]    {'[DRY] ' if dry_run else ''}Added: {url}")

    if new_lines and not dry_run:
        insert_at = last_list_idx + 1 if last_list_idx != -1 else len(lines)
        for i, line in enumerate(new_lines):
            lines.insert(insert_at + i, line)
        llms.write_text("".join(lines), encoding="utf-8")


def git_commit_and_push(root: Path) -> None:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "sitemap.xml", "llms.txt"],
            cwd=root, capture_output=True, text=True
        )
        if not result.stdout.strip():
            print("[git] Nothing to commit")
            return
        subprocess.run(["git", "add", "sitemap.xml", "llms.txt"], cwd=root, check=True)
        subprocess.run(
            ["git", "commit", "-m", f"chore: auto-sync sitemap and llms.txt [{date.today()}]"],
            cwd=root, check=True
        )
        subprocess.run(["git", "push"], cwd=root, check=True)
        print("[git] Committed and pushed")
    except subprocess.CalledProcessError as e:
        print(f"[git] Error: {e}")


def main() -> None:
    args = parse_args()
    root = Path(".")
    today = date.today().isoformat()

    removed_links = remove_retired_page_links(root, args.dry_run)
    pages = collect_pages(root)
    added_urls = sync_sitemap(Path("sitemap.xml"), pages, root, today, args.dry_run)
    sync_llms(Path("llms.txt"), added_urls, root, args.dry_run)

    if added_urls and not args.dry_run:
        print(f"[sync] Added {len(added_urls)} new page(s) - committing...")
        git_commit_and_push(root)
    elif not added_urls and not removed_links:
        print("[sync] All pages already in sitemap, nothing to do")


if __name__ == "__main__":
    main()
