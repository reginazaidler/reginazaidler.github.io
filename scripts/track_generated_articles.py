#!/usr/bin/env python3
"""
track_generated_articles.py
────────────────────────────
Scans the git log for auto-generated articles and keeps
reports/generated-articles.csv up to date.

Run every few hours via cron. Also safe to run manually.

Usage:
    python3 scripts/track_generated_articles.py
    python3 scripts/track_generated_articles.py --dry-run
"""
from __future__ import annotations

import argparse
import csv
import re
import subprocess
from datetime import date
from pathlib import Path

SITE_BASE = "https://vainzof.co.il"
CSV_PATH = Path("reports/generated-articles.csv")
CSV_HEADERS = ["date", "slug", "title", "keyword", "url", "status", "notes"]

# Patterns that identify auto-generated article commits
AUTO_COMMIT_PATTERNS = [
    r"^auto:",
    r"auto: trends report",
    r"generate_article",
    r"auto.?generat",
    r"\[agent\]",
    r"trends? article",
    r"new article:",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Track auto-generated articles in CSV")
    p.add_argument("--dry-run", action="store_true", help="Print without writing")
    p.add_argument("--since", default="6 months ago", help="How far back to scan git log")
    return p.parse_args()


def git_log(since: str) -> list[dict]:
    """Return list of {hash, date, message, files} for commits since `since`."""
    result = subprocess.run(
        ["git", "log", f"--since={since}", "--name-only",
         "--pretty=format:COMMIT|%H|%as|%s", "--diff-filter=A"],
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    entries: list[dict] = []
    current: dict | None = None
    for line in result.stdout.splitlines():
        if line.startswith("COMMIT|"):
            if current:
                entries.append(current)
            _, hash_, date_, msg = line.split("|", 3)
            current = {"hash": hash_, "date": date_, "message": msg, "files": []}
        elif line.strip().endswith(".html") and current is not None:
            current["files"].append(line.strip())
    if current:
        entries.append(current)
    return entries


def is_auto_generated(commit: dict) -> bool:
    msg = commit["message"].lower()
    return any(re.search(p, msg, re.IGNORECASE) for p in AUTO_COMMIT_PATTERNS)


def extract_title(slug: str) -> str:
    """Extract <title> from the HTML file if it exists."""
    for path in [Path(f"{slug}.html"), Path(slug) / "index.html"]:
        if path.exists():
            content = path.read_text(encoding="utf-8", errors="ignore")
            m = re.search(r"<title>(.*?)</title>", content, re.DOTALL)
            if m:
                return m.group(1).strip()
    return slug


def load_existing_csv() -> set[str]:
    """Return set of slugs already in the CSV."""
    if not CSV_PATH.exists():
        return set()
    with CSV_PATH.open(encoding="utf-8", newline="") as f:
        return {row["slug"] for row in csv.DictReader(f) if row.get("slug")}


def append_rows(rows: list[dict], dry_run: bool) -> None:
    if not rows:
        return
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_header = not CSV_PATH.exists()
    if dry_run:
        print(f"[dry-run] Would append {len(rows)} row(s):")
        for r in rows:
            print(f"  {r['date']} | {r['slug']} | {r['title'][:50]}")
        return
    with CSV_PATH.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        if write_header:
            writer.writeheader()
        writer.writerows(rows)


def git_commit_and_push() -> None:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", str(CSV_PATH)],
            capture_output=True, text=True
        )
        if not result.stdout.strip():
            return
        subprocess.run(["git", "add", str(CSV_PATH)], check=True)
        subprocess.run(
            ["git", "commit", "-m",
             f"chore: update generated-articles tracking log [{date.today()}]"],
            check=True
        )
        subprocess.run(["git", "push"], check=True)
        print("[git] Committed and pushed")
    except subprocess.CalledProcessError as e:
        print(f"[git] Error: {e}")


def main() -> None:
    args = parse_args()
    existing_slugs = load_existing_csv()
    commits = git_log(args.since)

    new_rows: list[dict] = []
    for commit in commits:
        if not is_auto_generated(commit):
            continue
        for filepath in commit["files"]:
            # Only root-level .html files (agent-generated articles)
            if "/" in filepath or not filepath.endswith(".html"):
                continue
            skip = {"index.html", "choose-insurance-agent.html", "thanks.html",
                    "about.html", "services.html", "faq.html", "articles.html",
                    "media.html", "reviews.html", "insurance-types.html"}
            if filepath in skip:
                continue
            slug = filepath.replace(".html", "")
            if slug in existing_slugs:
                continue
            title = extract_title(slug)
            row = {
                "date": commit["date"],
                "slug": slug,
                "title": title,
                "keyword": "",
                "url": f"{SITE_BASE}/{filepath}",
                "status": "",
                "notes": "",
            }
            new_rows.append(row)
            existing_slugs.add(slug)
            print(f"[track] Found: {slug} ({commit['date']})")

    if new_rows:
        append_rows(new_rows, args.dry_run)
        if not args.dry_run:
            git_commit_and_push()
    else:
        print("[track] No new auto-generated articles found")


if __name__ == "__main__":
    main()
