#!/usr/bin/env python3
"""Track SEO changes as measurable experiments.

Commands:
  start    Record the before-metrics and exact change.
  evaluate Compare the latest GSC metrics after the waiting period.

This tool does not claim causation. Results are directional evidence only.
"""
from __future__ import annotations
import argparse, json, sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

def conn(path: Path):
    c=sqlite3.connect(path); c.row_factory=sqlite3.Row
    c.execute("""CREATE TABLE IF NOT EXISTS seo_experiments(
      id INTEGER PRIMARY KEY AUTOINCREMENT, page TEXT NOT NULL, query TEXT NOT NULL,
      changed_at TEXT NOT NULL, change_type TEXT NOT NULL, change_summary TEXT NOT NULL,
      before_clicks REAL, before_impressions REAL, before_ctr REAL, before_position REAL,
      status TEXT NOT NULL DEFAULT 'waiting', evaluated_at TEXT,
      after_clicks REAL, after_impressions REAL, after_ctr REAL, after_position REAL,
      result TEXT, notes TEXT)""")
    c.commit(); return c

def latest_metric(c,page,query):
    return c.execute("""SELECT clicks,impressions,ctr,position,start_date,end_date
      FROM query_page_metrics WHERE page=? AND query=? ORDER BY fetched_at DESC LIMIT 1""",(page,query)).fetchone()

def start(args):
    c=conn(Path(args.db)); m=latest_metric(c,args.page,args.query)
    if not m: raise SystemExit("No GSC baseline found for this page/query.")
    c.execute("""INSERT INTO seo_experiments(page,query,changed_at,change_type,change_summary,
      before_clicks,before_impressions,before_ctr,before_position)
      VALUES(?,?,?,?,?,?,?,?,?)""",(args.page,args.query,datetime.now(timezone.utc).isoformat(),
      args.change_type,args.summary,m["clicks"],m["impressions"],m["ctr"],m["position"]))
    c.commit(); print("SEO experiment recorded.")

def classify(before,after,min_impressions):
    if after["impressions"] < min_impressions: return "not_enough_data"
    pos_delta=before["position"]-after["position"]
    ctr_delta=after["ctr"]-before["ctr"]
    if pos_delta >= 1.0 or ctr_delta >= 0.01: return "improved"
    if pos_delta <= -1.0 or ctr_delta <= -0.01: return "declined"
    return "no_meaningful_change"

def evaluate(args):
    c=conn(Path(args.db)); now=datetime.now(timezone.utc)
    rows=c.execute("SELECT * FROM seo_experiments WHERE status='waiting'").fetchall()
    out=[]
    for e in rows:
        changed=datetime.fromisoformat(e["changed_at"])
        if now-changed < timedelta(days=args.wait_days): continue
        m=latest_metric(c,e["page"],e["query"])
        if not m: continue
        before={"position":e["before_position"],"ctr":e["before_ctr"]}
        after={"position":m["position"],"ctr":m["ctr"],"impressions":m["impressions"]}
        result=classify(before,after,args.min_impressions)
        c.execute("""UPDATE seo_experiments SET status='evaluated',evaluated_at=?,
          after_clicks=?,after_impressions=?,after_ctr=?,after_position=?,result=? WHERE id=?""",
          (now.isoformat(),m["clicks"],m["impressions"],m["ctr"],m["position"],result,e["id"]))
        out.append({"id":e["id"],"page":e["page"],"query":e["query"],"result":result,
          "before":{"clicks":e["before_clicks"],"impressions":e["before_impressions"],"ctr":e["before_ctr"],"position":e["before_position"]},
          "after":{"clicks":m["clicks"],"impressions":m["impressions"],"ctr":m["ctr"],"position":m["position"]},
          "caution":"Directional evidence only; other search changes may have contributed."})
    c.commit()
    p=Path(args.report); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"evaluated":len(out)},ensure_ascii=False))

def main():
    p=argparse.ArgumentParser(); p.add_argument("--db",default="seo-gap-agent/data/seo_gap_agent.db")
    sub=p.add_subparsers(dest="cmd",required=True)
    s=sub.add_parser("start"); s.add_argument("--page",required=True); s.add_argument("--query",required=True)
    s.add_argument("--change-type",required=True); s.add_argument("--summary",required=True); s.set_defaults(fn=start)
    e=sub.add_parser("evaluate"); e.add_argument("--wait-days",type=int,default=14)
    e.add_argument("--min-impressions",type=int,default=20); e.add_argument("--report",default="seo-gap-agent/reports/experiment_results.json"); e.set_defaults(fn=evaluate)
    a=p.parse_args(); a.fn(a)
if __name__=="__main__": main()
