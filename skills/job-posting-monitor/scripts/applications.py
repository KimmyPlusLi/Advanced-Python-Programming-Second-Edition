#!/usr/bin/env python3
"""Track job applications against monitored postings.

State: data/state/applications.json — {job_id: {company, title, url, status,
history: [{date, status, note}]}}. Statuses: applied, interviewing, offer,
rejected, withdrawn. Digests annotate tracked postings with a status emoji,
and the weekly digest includes a pipeline summary + follow-up nudges.

Usage:
  python3 applications.py mark <fragment> [--status applied] [--note "..."]
      fragment matches a job's id, company, or title in the JD archive /
      seen state; must be unambiguous (candidates are listed otherwise).
  python3 applications.py list [--status applied]
  python3 applications.py followups [--days 10]
      applications still in 'applied' with no update for N days.
"""

import argparse
import json
from datetime import date, datetime
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = SKILL_DIR / "data"
APPS_PATH = DATA_DIR / "state" / "applications.json"
STATUSES = ["applied", "interviewing", "offer", "rejected", "withdrawn"]
STATUS_EMOJI = {"applied": "📨", "interviewing": "🎤", "offer": "🏆",
                "rejected": "⛔", "withdrawn": "🚫"}


def load_apps():
    return json.loads(APPS_PATH.read_text()) if APPS_PATH.exists() else {}


def save_apps(apps):
    APPS_PATH.parent.mkdir(parents=True, exist_ok=True)
    APPS_PATH.write_text(json.dumps(apps, indent=2))


def known_jobs():
    """id -> {company, title, url} from the JD archive plus seen state."""
    jobs = {}
    archive = DATA_DIR / "jd_archive"
    if archive.exists():
        for p in archive.glob("*.json"):
            try:
                e = json.loads(p.read_text())
                jobs[e["id"]] = {"company": e.get("company", ""),
                                 "title": e.get("title", ""), "url": e.get("url", "")}
            except (json.JSONDecodeError, OSError, KeyError):
                continue
    state_path = DATA_DIR / "state" / "seen_jobs.json"
    if state_path.exists():
        for jid, e in json.loads(state_path.read_text()).items():
            jobs.setdefault(jid, {"company": e.get("company", ""),
                                  "title": e.get("title", ""), "url": e.get("url", "")})
    return jobs


def cmd_mark(args):
    needle = args.fragment.lower()
    jobs = known_jobs()
    hits = [(jid, j) for jid, j in jobs.items()
            if needle in jid.lower() or needle in j["company"].lower()
            or needle in j["title"].lower()]
    if not hits:
        print(f"no monitored posting matches {args.fragment!r}")
        return
    if len(hits) > 1:
        print(f"{args.fragment!r} is ambiguous — candidates:")
        for jid, j in hits:
            print(f"  [{jid}] {j['company']} — {j['title']}")
        return
    jid, j = hits[0]
    apps = load_apps()
    today = date.today().isoformat()
    entry = apps.get(jid, {**j, "history": []})
    entry["status"] = args.status
    entry["history"].append({"date": today, "status": args.status,
                             "note": args.note or ""})
    apps[jid] = entry
    save_apps(apps)
    print(f"{STATUS_EMOJI[args.status]} {j['company']} — {j['title']} -> {args.status}"
          + (f" ({args.note})" if args.note else ""))


def cmd_list(args):
    apps = load_apps()
    rows = [(jid, a) for jid, a in apps.items()
            if not args.status or a["status"] == args.status]
    if not rows:
        print("no tracked applications" + (f" with status {args.status}" if args.status else ""))
        return
    rows.sort(key=lambda r: r[1]["history"][-1]["date"], reverse=True)
    for jid, a in rows:
        last = a["history"][-1]
        note = f" — {last['note']}" if last.get("note") else ""
        print(f"{STATUS_EMOJI.get(a['status'], '?')} {a['status']:<13} {last['date']}  "
              f"{a['company']} — {a['title']}{note}  [{jid}]")
    print(f"\n{len(rows)} application(s)")


def followups_due(apps, days, today=None):
    today = today or date.today()
    due = []
    for jid, a in apps.items():
        if a.get("status") != "applied":
            continue
        last = a["history"][-1]["date"]
        age = (today - datetime.strptime(last, "%Y-%m-%d").date()).days
        if age >= days:
            due.append({"id": jid, "company": a["company"], "title": a["title"],
                        "days_since_update": age})
    due.sort(key=lambda d: -d["days_since_update"])
    return due


def cmd_followups(args):
    due = followups_due(load_apps(), args.days)
    if not due:
        print(f"nothing awaiting follow-up (threshold {args.days} days)")
        return
    for d in due:
        print(f"⏰ {d['company']} — {d['title']}: applied, "
              f"no update in {d['days_since_update']} days  [{d['id']}]")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("mark"); p.add_argument("fragment")
    p.add_argument("--status", choices=STATUSES, default="applied")
    p.add_argument("--note")
    p.set_defaults(fn=cmd_mark)
    p = sub.add_parser("list"); p.add_argument("--status", choices=STATUSES)
    p.set_defaults(fn=cmd_list)
    p = sub.add_parser("followups"); p.add_argument("--days", type=int, default=10)
    p.set_defaults(fn=cmd_followups)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
