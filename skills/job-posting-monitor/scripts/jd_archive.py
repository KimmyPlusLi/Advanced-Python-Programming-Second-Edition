#!/usr/bin/env python3
"""Retrieve archived job descriptions (built by digest.py in data/jd_archive/).

The archive keeps every matched posting ever seen — full description text
included — even after the posting closes and its URL dies. Use it to revisit
requirements, trend demand over time, and feed interview prep from dead JDs.

Usage:
  python3 jd_archive.py list [--company X] [--role R] [--status active|closed]
  python3 jd_archive.py show <id-or-title/company fragment>
  python3 jd_archive.py search <term> [--company X]   # term in title/description
  python3 jd_archive.py trend <term>                  # postings mentioning term, by month
  python3 jd_archive.py export [--out PATH]           # whole archive as markdown
"""

import argparse
import json
from collections import Counter
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
ARCHIVE_DIR = SKILL_DIR / "data" / "jd_archive"


def load(company=None, role=None, status=None):
    entries = []
    if ARCHIVE_DIR.exists():
        for p in sorted(ARCHIVE_DIR.glob("*.json")):
            try:
                e = json.loads(p.read_text())
            except (json.JSONDecodeError, OSError):
                continue
            if company and company.lower() not in e.get("company", "").lower():
                continue
            if role and role != e.get("matched_role"):
                continue
            if status and e.get("status") != status:
                continue
            entries.append(e)
    entries.sort(key=lambda e: e.get("first_archived", ""))
    return entries


def text_of(e):
    parts = [e.get("title", ""), e.get("description", "")]
    parts += [d.get("description", "") for d in e.get("previous_descriptions", [])]
    return " ".join(parts).lower()


def cmd_list(args):
    entries = load(args.company, args.role, args.status)
    if not entries:
        print("no archived JDs match")
        return
    print(f"{'first seen':<12} {'status':<7} {'role':<18} company — title")
    for e in entries:
        print(f"{e.get('first_archived','?'):<12} {e.get('status','?'):<7} "
              f"{e.get('matched_role','?'):<18} {e.get('company','?')} — "
              f"{e.get('title','?')}  [{e['id']}]")
    print(f"\n{len(entries)} JD(s)")


def cmd_show(args):
    needle = args.jd.lower()
    hits = [e for e in load()
            if needle in e["id"] or needle in e.get("title", "").lower()
            or needle in e.get("company", "").lower()]
    if not hits:
        print(f"nothing matching {args.jd!r} — try 'list'")
        return
    for e in hits:
        print(f"=== {e.get('company')} — {e.get('title')} "
              f"[{e.get('status')}, first seen {e.get('first_archived')}"
              + (f", closed {e['closed_on']}" if e.get("closed_on") else "") + "]")
        print(f"role: {e.get('matched_role')}  score: {e.get('score')}  "
              f"location: {e.get('location') or '?'}")
        print(f"url: {e.get('url')}")
        print(f"\n{e.get('description') or '(no description captured)'}")
        for prev in e.get("previous_descriptions", []):
            print(f"\n--- earlier version (until {prev['archived_until']}):")
            print(prev["description"])
        print()


def cmd_search(args):
    term = args.term.lower()
    hits = [e for e in load(args.company) if term in text_of(e)]
    if not hits:
        print(f"no archived JD mentions {args.term!r}")
        return
    for e in hits:
        print(f"- {e.get('company')} — {e.get('title')} "
              f"({e.get('status')}, {e.get('first_archived')}) [{e['id']}]")
    print(f"\n{len(hits)} of {len(load(args.company))} archived JD(s) mention {args.term!r}")


def cmd_trend(args):
    term = args.term.lower()
    entries = load()
    by_month, hits_by_month = Counter(), Counter()
    for e in entries:
        month = (e.get("first_archived") or "")[:7]
        if not month:
            continue
        by_month[month] += 1
        if term in text_of(e):
            hits_by_month[month] += 1
    if not by_month:
        print("archive is empty")
        return
    print(f"postings mentioning {args.term!r} by month first seen:")
    for month in sorted(by_month):
        n, total = hits_by_month[month], by_month[month]
        pct = f"{100 * n // total}%" if total else "-"
        print(f"  {month}: {n}/{total} ({pct})")


def cmd_export(args):
    entries = load()
    out = Path(args.out) if args.out else SKILL_DIR / "data" / "jd_archive_export.md"
    lines = [f"# JD archive — {len(entries)} posting(s)\n"]
    for e in entries:
        lines.append(f"\n## {e.get('company')} — {e.get('title')} "
                     f"({e.get('status')}, first seen {e.get('first_archived')})\n")
        lines.append(f"role: {e.get('matched_role')} · {e.get('location') or '?'} · "
                     f"[posting]({e.get('url')})\n")
        lines.append(e.get("description") or "_(no description captured)_")
    out.write_text("\n".join(lines))
    print(f"exported {len(entries)} JD(s) -> {out}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list")
    p.add_argument("--company"); p.add_argument("--role")
    p.add_argument("--status", choices=["active", "closed"])
    p.set_defaults(fn=cmd_list)
    p = sub.add_parser("show"); p.add_argument("jd"); p.set_defaults(fn=cmd_show)
    p = sub.add_parser("search"); p.add_argument("term"); p.add_argument("--company")
    p.set_defaults(fn=cmd_search)
    p = sub.add_parser("trend"); p.add_argument("term"); p.set_defaults(fn=cmd_trend)
    p = sub.add_parser("export"); p.add_argument("--out"); p.set_defaults(fn=cmd_export)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
