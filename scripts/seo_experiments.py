#!/usr/bin/env python3
"""Track SEO changes as measurable experiments.

Records a baseline, deployment metadata, indexing-request status and follow-up
checkpoints. Results are directional evidence only and do not claim causation.
"""
from __future__ import annotations
import argparse, json, sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

CHECKPOINTS=(7,14,21,28)
REGISTRY_PATH=Path("seo-gap-agent/data/seo_experiments_registry.json")

def conn(path: Path):
    c=sqlite3.connect(path); c.row_factory=sqlite3.Row
    c.execute("""CREATE TABLE IF NOT EXISTS seo_experiments(
      id INTEGER PRIMARY KEY AUTOINCREMENT, page TEXT NOT NULL, query TEXT NOT NULL,
      changed_at TEXT NOT NULL, change_type TEXT NOT NULL, change_summary TEXT NOT NULL,
      before_clicks REAL, before_impressions REAL, before_ctr REAL, before_position REAL,
      status TEXT NOT NULL DEFAULT 'waiting', evaluated_at TEXT,
      after_clicks REAL, after_impressions REAL, after_ctr REAL, after_position REAL,
      result TEXT, notes TEXT,
      pr_number INTEGER, commit_sha TEXT, deployed_at TEXT,
      indexing_requested_at TEXT, indexing_status TEXT DEFAULT 'not_requested')""")
    existing={r["name"] for r in c.execute("PRAGMA table_info(seo_experiments)")}
    for name,sqltype,default in [
        ("pr_number","INTEGER",None),("commit_sha","TEXT",None),("deployed_at","TEXT",None),
        ("indexing_requested_at","TEXT",None),("indexing_status","TEXT","'not_requested'")]:
        if name not in existing:
            suffix=f" DEFAULT {default}" if default else ""
            c.execute(f"ALTER TABLE seo_experiments ADD COLUMN {name} {sqltype}{suffix}")
    c.execute("""CREATE TABLE IF NOT EXISTS seo_experiment_checks(
      id INTEGER PRIMARY KEY AUTOINCREMENT, experiment_id INTEGER NOT NULL,
      checkpoint_days INTEGER NOT NULL, checked_at TEXT NOT NULL,
      clicks REAL, impressions REAL, ctr REAL, position REAL, result TEXT,
      UNIQUE(experiment_id, checkpoint_days))""")
    c.commit(); return c

def latest_metric(c,page,query):
    return c.execute("""SELECT clicks,impressions,ctr,position,start_date,end_date
      FROM query_page_metrics WHERE page=? AND query=? ORDER BY fetched_at DESC LIMIT 1""",(page,query)).fetchone()

def _load_registry():
    if not REGISTRY_PATH.exists(): return []
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))

def _save_registry(rows):
    REGISTRY_PATH.parent.mkdir(parents=True,exist_ok=True)
    REGISTRY_PATH.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def sync_registry(c):
    rows=_load_registry()
    added=0
    for x in rows:
        exists=c.execute("SELECT 1 FROM seo_experiments WHERE page=? AND query=? AND commit_sha=? LIMIT 1",
                         (x["page"],x["query"],x.get("commit_sha"))).fetchone()
        if exists: continue
        c.execute("""INSERT INTO seo_experiments(page,query,changed_at,change_type,change_summary,
          before_clicks,before_impressions,before_ctr,before_position,pr_number,commit_sha,deployed_at,
          indexing_requested_at,indexing_status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
          (x["page"],x["query"],x["changed_at"],x["change_type"],x["change_summary"],
           x.get("before_clicks"),x.get("before_impressions"),x.get("before_ctr"),x.get("before_position"),
           x.get("pr_number"),x.get("commit_sha"),x.get("deployed_at",x["changed_at"]),
           x.get("indexing_requested_at"),x.get("indexing_status","not_requested")))
        added+=1
    c.commit()
    return added

def start(args):
    c=conn(Path(args.db)); sync_registry(c); m=latest_metric(c,args.page,args.query)
    if not m: raise SystemExit("No GSC baseline found for this page/query.")
    changed=args.changed_at or datetime.now(timezone.utc).isoformat()
    c.execute("""INSERT INTO seo_experiments(page,query,changed_at,change_type,change_summary,
      before_clicks,before_impressions,before_ctr,before_position,pr_number,commit_sha,deployed_at,
      indexing_requested_at,indexing_status)
      VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(args.page,args.query,changed,args.change_type,args.summary,
      m["clicks"],m["impressions"],m["ctr"],m["position"],args.pr_number,args.commit_sha,
      args.deployed_at or changed,args.indexing_requested_at,
      "requested" if args.indexing_requested_at else "not_requested"))
    c.commit(); print("SEO experiment recorded.")

def classify(before,after,min_impressions):
    if after["impressions"] < min_impressions: return "not_enough_data"
    pos_delta=before["position"]-after["position"]; ctr_delta=after["ctr"]-before["ctr"]
    if pos_delta >= 1.0 or ctr_delta >= 0.01: return "improved"
    if pos_delta <= -1.0 or ctr_delta <= -0.01: return "declined"
    return "no_meaningful_change"

def mark_indexing(args):
    c=conn(Path(args.db)); ts=args.at or datetime.now(timezone.utc).isoformat()
    row=c.execute("SELECT id FROM seo_experiments WHERE page=? AND query=? ORDER BY changed_at DESC LIMIT 1",
                  (args.page,args.query)).fetchone()
    if not row: raise SystemExit("No experiment found.")
    c.execute("UPDATE seo_experiments SET indexing_requested_at=?, indexing_status='requested' WHERE id=?",(ts,row["id"]))
    c.commit(); print("Indexing request recorded.")

def evaluate(args):
    c=conn(Path(args.db)); sync_registry(c); now=datetime.now(timezone.utc); out=[]
    rows=c.execute("SELECT * FROM seo_experiments WHERE status IN ('waiting','monitoring')").fetchall()
    for e in rows:
        changed=datetime.fromisoformat(e["changed_at"])
        age=(now-changed).days
        m=latest_metric(c,e["page"],e["query"])
        if not m: continue
        before={"position":e["before_position"],"ctr":e["before_ctr"]}
        after={"position":m["position"],"ctr":m["ctr"],"impressions":m["impressions"]}
        result=classify(before,after,args.min_impressions)
        for days in CHECKPOINTS:
            if age < days: continue
            exists=c.execute("SELECT 1 FROM seo_experiment_checks WHERE experiment_id=? AND checkpoint_days=?",
                             (e["id"],days)).fetchone()
            if exists: continue
            c.execute("""INSERT INTO seo_experiment_checks(experiment_id,checkpoint_days,checked_at,
              clicks,impressions,ctr,position,result) VALUES(?,?,?,?,?,?,?,?)""",
              (e["id"],days,now.isoformat(),m["clicks"],m["impressions"],m["ctr"],m["position"],result))
            out.append({"id":e["id"],"checkpoint_days":days,"page":e["page"],"query":e["query"],
              "result":result,"before":{"clicks":e["before_clicks"],"impressions":e["before_impressions"],
              "ctr":e["before_ctr"],"position":e["before_position"]},
              "after":{"clicks":m["clicks"],"impressions":m["impressions"],"ctr":m["ctr"],"position":m["position"]},
              "indexing_status":e["indexing_status"],
              "caution":"Directional evidence only; other search changes may have contributed."})
        if age >= 28:
            c.execute("""UPDATE seo_experiments SET status='evaluated',evaluated_at=?,
              after_clicks=?,after_impressions=?,after_ctr=?,after_position=?,result=? WHERE id=?""",
              (now.isoformat(),m["clicks"],m["impressions"],m["ctr"],m["position"],result,e["id"]))
        elif age >= 7:
            c.execute("UPDATE seo_experiments SET status='monitoring' WHERE id=?",(e["id"],))
    c.commit()
    p=Path(args.report); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"new_checkpoints":len(out)},ensure_ascii=False))

def main():
    p=argparse.ArgumentParser(); p.add_argument("--db",default="seo-gap-agent/data/seo_gap_agent.db")
    sub=p.add_subparsers(dest="cmd",required=True)
    s=sub.add_parser("start"); s.add_argument("--page",required=True); s.add_argument("--query",required=True)
    s.add_argument("--change-type",required=True); s.add_argument("--summary",required=True)
    s.add_argument("--pr-number",type=int); s.add_argument("--commit-sha"); s.add_argument("--changed-at")
    s.add_argument("--deployed-at"); s.add_argument("--indexing-requested-at"); s.set_defaults(fn=start)
    i=sub.add_parser("mark-indexing"); i.add_argument("--page",required=True); i.add_argument("--query",required=True)
    i.add_argument("--at"); i.set_defaults(fn=mark_indexing)
    e=sub.add_parser("evaluate"); e.add_argument("--min-impressions",type=int,default=20)
    e.add_argument("--report",default="seo-gap-agent/reports/experiment_results.json"); e.set_defaults(fn=evaluate)
    a=p.parse_args(); a.fn(a)
if __name__=="__main__": main()
