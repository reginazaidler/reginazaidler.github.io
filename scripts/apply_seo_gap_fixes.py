#!/usr/bin/env python3
"""Apply only low-risk SEO Gap Agent fixes to existing local HTML pages.

Safe mode deliberately limits automation to title and meta-description changes.
Content sections, FAQ, trust claims and CTA changes remain recommendations until
we add source-aware factual QA.
"""
from __future__ import annotations
import argparse, json, re
from pathlib import Path
from urllib.parse import urlparse

def local_path(root: Path, page_url: str) -> Path | None:
    path = urlparse(page_url).path.lstrip("/") or "index.html"
    candidate = root / path
    try:
        candidate.resolve().relative_to(root.resolve())
    except ValueError:
        return None
    return candidate if candidate.suffix.lower() == ".html" else None

def replace_title(html: str, value: str) -> tuple[str, bool]:
    value = value.strip()
    if not value or "<" in value or ">" in value:
        return html, False
    new, n = re.subn(r"<title[^>]*>.*?</title>", f"<title>{value}</title>", html, count=1, flags=re.I|re.S)
    return new, bool(n)

def replace_meta(html: str, value: str) -> tuple[str, bool]:
    value = value.strip()
    if not value or "<" in value or ">" in value:
        return html, False
    pattern = r'(<meta\s+name=["\']description["\']\s+content=["\'])(.*?)(["\'][^>]*>)'
    new, n = re.subn(pattern, lambda m: m.group(1)+value+m.group(3), html, count=1, flags=re.I|re.S)
    return new, bool(n)

def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--tasks", default="seo-gap-agent/reports/dev_tasks.json")
    p.add_argument("--root", default=".")
    p.add_argument("--report", default="seo-gap-agent/reports/applied_fixes.json")
    p.add_argument("--apply", action="store_true")
    args=p.parse_args()
    root=Path(args.root)
    tasks_path=Path(args.tasks)
    tasks=json.loads(tasks_path.read_text(encoding="utf-8")) if tasks_path.exists() else []
    results=[]
    seen=set()
    for task in tasks:
        if task.get("analysis_status") != "ok" or task.get("recommended_action") != "improve_existing_page":
            continue
        if task.get("priority") not in {"high","medium"}:
            continue
        path=local_path(root, task.get("page",""))
        if not path or not path.exists() or path in seen:
            continue
        seen.add(path)
        html=path.read_text(encoding="utf-8")
        original=html
        fixes=task.get("tasks",{})
        html,title_changed=replace_title(html, fixes.get("title_fix",""))
        # We do not yet receive a dedicated meta-description recommendation.
        # Keep the current meta description rather than repurposing body-copy advice.
        changed=html != original
        item={"page":str(path),"query":task.get("query"),"title_changed":title_changed,"changed":changed,"mode":"apply" if args.apply else "dry-run"}
        results.append(item)
        if changed and args.apply:
            path.write_text(html, encoding="utf-8")
    out=Path(args.report); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"eligible_pages":len(results),"changed_pages":sum(1 for x in results if x["changed"]),"apply":args.apply},ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
