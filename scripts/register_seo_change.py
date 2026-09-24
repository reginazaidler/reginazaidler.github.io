#!/usr/bin/env python3
from __future__ import annotations
import argparse
import subprocess
import sys
from datetime import datetime, timezone

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--page", required=True)
    p.add_argument("--query", required=True)
    p.add_argument("--change-type", required=True)
    p.add_argument("--summary", required=True)
    args = p.parse_args()
    now = datetime.now(timezone.utc).isoformat()

    subprocess.run([
        sys.executable, "scripts/seo_experiments.py", "start",
        "--page", args.page,
        "--query", args.query,
        "--change-type", args.change_type,
        "--summary", args.summary,
        "--changed-at", now,
        "--deployed-at", now,
    ], check=True)

    subprocess.run([
        sys.executable, "scripts/indexing_queue.py",
        "--add", args.page,
        "--reason", "SEO experiment: " + args.query,
    ], check=True)

    print("SEO change registered and queued for indexing.")

if __name__ == "__main__":
    main()
