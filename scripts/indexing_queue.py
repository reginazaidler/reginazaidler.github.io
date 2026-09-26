#!/usr/bin/env python3
"""Maintain indexing queue and keep SEO experiment registry in sync."""
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path

REGISTRY=Path("seo-gap-agent/data/seo_experiments_registry.json")

def load(path):
    if not path.exists(): return []
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return []

def save(path, rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def sync_registry(url,status,at):
    rows=load(REGISTRY); changed=False
    for x in rows:
        if x.get("page")==url:
            x["indexing_status"]=status
            if status=="requested": x["indexing_requested_at"]=at
            changed=True
    if changed: save(REGISTRY,rows)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--queue",default="data/indexing-queue.json")
    p.add_argument("--add"); p.add_argument("--reason",default="page updated")
    p.add_argument("--requested",help="Mark URL as manually submitted in Search Console")
    p.add_argument("--clear",help="Legacy alias for --requested")
    p.add_argument("--print-pending",action="store_true")
    a=p.parse_args(); qpath=Path(a.queue); qpath.parent.mkdir(parents=True,exist_ok=True); q=load(qpath)
    now=datetime.now(timezone.utc).isoformat()
    if a.add and not any(x.get("url")==a.add and x.get("status")=="pending" for x in q):
        q.append({"url":a.add,"reason":a.reason,"queued_at":now,"status":"pending"})
        sync_registry(a.add,"queued",now)
    requested=a.requested or a.clear
    if requested:
        for x in q:
            if x.get("url")==requested and x.get("status")=="pending":
                x["status"]="requested"; x["requested_at"]=now
        sync_registry(requested,"requested",now)
    save(qpath,q)
    if a.print_pending:
        pending=[x for x in q if x.get("status")=="pending"]
        print(json.dumps(pending,ensure_ascii=False))
if __name__=="__main__": main()
