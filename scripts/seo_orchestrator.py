#!/usr/bin/env python3
"""Pre-publish SEO orchestrator for the Trends Agent.

The orchestrator prevents automatic creation of a new article when the proposed
topic already has a plausible home on the site. It compares the proposed H1 and
keyword with existing indexable HTML pages and returns CREATE, UPDATE or SKIP.

This is intentionally conservative: a possible duplicate is never auto-published.
"""
from __future__ import annotations

import argparse
import json
import re
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

STOPWORDS = {
    "של","על","עם","את","מה","איך","כל","או","אם","גם","זה","זו","האם","כדי",
    "the","a","an","and","or","of","to","for","in","on","with","how","what",
}

def words(text: str) -> set[str]:
    clean = re.sub(r"[^0-9A-Za-zא-ת ]+", " ", unescape(text).lower())
    return {w for w in clean.split() if len(w) > 1 and w not in STOPWORDS}

def page_signals(path: Path) -> tuple[str, str]:
    html = path.read_text(encoding="utf-8", errors="ignore")
    title_m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    h1_m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.I | re.S)
    strip_tags = lambda s: re.sub(r"<[^>]+>", " ", s or "")
    return strip_tags(title_m.group(1) if title_m else ""), strip_tags(h1_m.group(1) if h1_m else "")

def similarity(target: set[str], candidate: set[str]) -> float:
    if not target or not candidate:
        return 0.0
    return len(target & candidate) / max(1, len(target))

def decide(root: Path, h1: str, keyword: str, proposed_slug: str) -> dict:
    target = words(f"{h1} {keyword}")
    matches = []
    excluded = {"index.html","articles.html","about.html","contact.html","thanks.html","faq.html"}
    for path in root.glob("*.html"):
        if path.name in excluded or path.stem == proposed_slug:
            continue
        title, existing_h1 = page_signals(path)
        score = similarity(target, words(f"{title} {existing_h1}"))
        if score >= 0.35:
            matches.append({"page": path.name, "title": title, "h1": existing_h1, "score": round(score, 3)})
    matches.sort(key=lambda x: x["score"], reverse=True)
    best = matches[0] if matches else None
    if best and best["score"] >= 0.72:
        action = "UPDATE"
        reason = "Strong overlap with an existing page. Prefer improving that page instead of creating a competing URL."
    elif best and best["score"] >= 0.50:
        action = "SKIP"
        reason = "Possible topic overlap. Hold automatic publishing for review rather than risk keyword cannibalization."
    else:
        action = "CREATE"
        reason = "No strong existing-page overlap found."
    return {"action": action, "reason": reason, "proposed_slug": proposed_slug, "best_match": best, "matches": matches[:5]}

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--h1", required=True)
    p.add_argument("--keyword", required=True)
    p.add_argument("--slug", required=True)
    p.add_argument("--root", default=".")
    p.add_argument("--output", default="reports/orchestrator-decision.json")
    args = p.parse_args()
    result = decide(Path(args.root), args.h1, args.keyword, args.slug)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["action"] == "CREATE" else 10

if __name__ == "__main__":
    raise SystemExit(main())
