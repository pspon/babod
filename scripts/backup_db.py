#!/usr/bin/env python3
"""Take a consistent snapshot of the SQLite database.

Uses SQLite's online backup API, so it is safe to run while the app is
serving requests (a plain ``cp`` of a WAL database is not).

    python scripts/backup_db.py --out /home/pi/babod-backups

Keeps the newest ``--keep`` snapshots and deletes older ones.  A nightly cron
entry on the Pi:

    0 3 * * * /usr/bin/python3 /home/pi/babod/scripts/backup_db.py \
        --db /home/pi/babod/data/babod.db --out /home/pi/babod-backups
"""

import argparse
import os
import sqlite3
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import storage  # noqa: E402


def backup(source, out_dir, keep):
    if not os.path.exists(source):
        raise SystemExit(f"No database at {source}")

    os.makedirs(out_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = os.path.join(out_dir, f"babod-{stamp}.db")

    with sqlite3.connect(source) as src, sqlite3.connect(target) as dst:
        src.backup(dst)

    snapshots = sorted(
        name for name in os.listdir(out_dir)
        if name.startswith("babod-") and name.endswith(".db")
    )
    for stale in snapshots[:-keep] if keep > 0 else []:
        os.remove(os.path.join(out_dir, stale))

    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=storage.db_path(), help="Database to back up")
    parser.add_argument("--out", default="backups", help="Directory for snapshots")
    parser.add_argument("--keep", type=int, default=14, help="Snapshots to retain")
    args = parser.parse_args()

    print(f"Backed up to {backup(args.db, args.out, args.keep)}")


if __name__ == "__main__":
    main()
