"""Backfill synthetic *past* snapshots for accounts you already track.

CLI wrapper around :func:`app.backfill.backfill_account` — the same logic is
exposed as ``POST /api/accounts/{id}/backfill`` (the dashboard's "Backfill"
button), so this script is only needed when you prefer a terminal.

Usage (locally or in the Render Shell):
    python -m scripts.backfill_history             # 60 days for every account
    python -m scripts.backfill_history --days 90
    python -m scripts.backfill_history --username nike

Re-running is safe: accounts whose history already spans --days are skipped.
"""

from __future__ import annotations

import argparse
import random

from app import database
from app.backfill import backfill_account
from app.models import Account


def backfill(days: int = 60, username: str | None = None) -> None:
    database.init_db()
    db = database.SessionLocal()
    try:
        query = db.query(Account)
        if username:
            query = query.filter_by(username=username.lstrip("@").strip().lower())
        accounts = query.all()
        if not accounts:
            print("no matching accounts — add them in the dashboard first")
            return

        for account in accounts:
            added = backfill_account(db, account, days)
            if added:
                print(f"@{account.username}: backfilled {added} daily snapshots ending at the real value")
            elif not account.snapshots:
                print(f"@{account.username}: no snapshots yet — click 'Collect now' first; skipped")
            else:
                print(f"@{account.username}: history already spans {days}d; skipped")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=60, help="total history span to reach (default 60)")
    parser.add_argument("--username", help="only backfill this account")
    args = parser.parse_args()
    random.seed(42)
    backfill(days=args.days, username=args.username)
    print("done — refresh the dashboard")
