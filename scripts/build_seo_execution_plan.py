#!/usr/bin/env python3
"""Turn SEO Gap recommendations into an explicit execution plan.

Only low-risk existing-page title changes can be AUTO_UPDATE candidates.
Everything else is REVIEW, CREATE_REVIEW or SKIP.
"""
from __future__ import annotations
import argparse, json, sqlite3
from pathlib import Path
from urllib.parse import urlparse

def locked(db: Path, page: str) -> bool:
    if not db.exists(): return False
    try:
        c=sqlite3.connect(db)
        return bool(c.execute("SELECT 1 FROM seo_experiments WHERE page=? AND status IN ('waiting','monitoring') LIMIT 1",(page,)).fetchone())
    except sqlite3.Error:
        return False

def local_html(root: Path, url: str) -> bool:
    p=urlparse(url).path.lstrip("/") or "index.html"
    f=root/p
    return f.exists() and f.suffix.lower()==".html"

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--tasks",default="seo-gap-agent/reports/dev_tasks.json")
    p.add_argument("--db",default="seo-gap-agent/data/seo_gap_agent.db")
    p.add_argument("--root",default=".")
    p.add_argument("--out",default="seo-gap-agent/reports/execution_plan.json")
    a=p.parse_args()
    tasks=json.loads(Path(a.tasks).read_text(encoding="utf-8")) if Path(a.tasks).exists() else []
    plan=[]
    for t in tasks:
        page=t.get("page",""); action=t.get("recommended_action",""); status=t.get("analysis_status")
        item={"query":t.get("query"),"page":page,"priority":t.get("priority"),"recommended_action":action}
        if status!="ok":
            item.update(decision="SKIP",reason="AI analysis unavailable")
        elif locked(Path(a.db),page):
            item.update(decision="SKIP",reason="Active SEO experiment locks this page")
        elif action=="create_new_page":
            item.update(decision="CREATE_REVIEW",reason="New pages require duplicate/orchestrator review before publishing")
        elif action!="improve_existing_page" or not local_html(Path(a.root),page):
            item.update(decision="REVIEW",reason="Not a safe local existing-page update")
        elif t.get("priority") not in {"high","medium"}:
            item.update(decision="REVIEW",reason="Low priority")
        elif not t.get("tasks",{}).get("title_fix","").strip():
            item.update(decision="REVIEW",reason="No safe title recommendation")
        else:
            item.update(decision="AUTO_UPDATE",reason="Existing local page; medium/high priority; title-only safe change")
        plan.append(item)
    out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding="utf-8")
    counts={}
    for x in plan: counts[x["decision"]]=counts.get(x["decision"],0)+1
    print(json.dumps(counts,ensure_ascii=False))
if __name__=="__main__": main()
