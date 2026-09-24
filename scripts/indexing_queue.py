#!/usr/bin/env python3
"""Maintain a small queue of changed URLs that should be manually requested for indexing."""
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path

def load(path):
    if not path.exists(): return []
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return []

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--queue",default="data/indexing-queue.json")
    p.add_argument("--add")
    p.add_argument("--reason",default="page updated")
    p.add_argument("--clear")
    p.add_argument("--print-pending",action="store_true")
    a=p.parse_args(); qpath=Path(a.queue); qpath.parent.mkdir(parents=True,exist_ok=True); q=load(qpath)
    now=datetime.now(timezone.utc).isoformat()
    if a.add and not any(x.get("url")==a.add and x.get("status")=="pending" for x in q):
        q.append({"url":a.add,"reason":a.reason,"queued_at":now,"status":"pending"})
    if a.clear:
        for x in q:
            if x.get("url")==a.clear and x.get("status")=="pending":
                x["status"]="done"; x["done_at"]=now
    qpath.write_text(json.dumps(q,ensure_ascii=False,indent=2),encoding="utf-8")
    if a.print_pending:
        pending=[x for x in q if x.get("status")=="pending"]
        print(json.dumps(pending,ensure_ascii=False))
if __name__=="__main__": main()
