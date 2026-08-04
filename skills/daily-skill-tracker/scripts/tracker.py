#!/usr/bin/env python3
"""Daily skill tracker — log tiny practice sessions, watch them compound.

Stdlib-only CLI backing the OpenClaw `daily-skill-tracker` skill.
Data lives in ~/.openclaw/skill-tracker (override: SKILL_TRACKER_HOME):
  skills.json  — tracked skills (name, why, facets, priority)
  log.jsonl    — one JSON line per practice session (source of truth)
  journal.md   — human-readable journal, re-rendered after every log
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path


def data_dir() -> Path:
    root = os.environ.get("SKILL_TRACKER_HOME")
    d = Path(root) if root else Path.home() / ".openclaw" / "skill-tracker"
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_skills() -> list:
    f = data_dir() / "skills.json"
    if not f.exists():
        return []
    return json.loads(f.read_text(encoding="utf-8")).get("skills", [])


def save_skills(skills: list) -> None:
    f = data_dir() / "skills.json"
    f.write_text(
        json.dumps({"skills": skills}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_log() -> list:
    f = data_dir() / "log.jsonl"
    if not f.exists():
        return []
    entries = []
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            entries.append(json.loads(line))
    entries.sort(key=lambda e: e["ts"])
    return entries


def append_log(entry: dict) -> None:
    f = data_dir() / "log.jsonl"
    with f.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def resolve_skill(query: str, skills: list):
    """Match case-insensitively: exact, then unique prefix, then unique substring."""
    q = query.strip().lower()
    names = [s["name"] for s in skills]
    exact = [n for n in names if n.lower() == q]
    if exact:
        return exact[0]
    prefix = [n for n in names if n.lower().startswith(q)]
    if len(prefix) == 1:
        return prefix[0]
    sub = [n for n in names if q in n.lower()]
    if len(sub) == 1:
        return sub[0]
    candidates = prefix or sub
    if candidates:
        raise SystemExit(
            f"Ambiguous skill '{query}' — matches: " + ", ".join(sorted(candidates))
        )
    return None


def fmt_minutes(minutes: float) -> str:
    if minutes < 60:
        return f"{minutes:g} min"
    return f"{minutes / 60:.1f} h"


def entry_date(e: dict) -> date:
    return datetime.fromisoformat(e["ts"]).date()


def streak_for(dates: set, today: date) -> int:
    """Consecutive practice days ending today (or yesterday if today not yet logged)."""
    if not dates:
        return 0
    day = today if today in dates else today - timedelta(days=1)
    n = 0
    while day in dates:
        n += 1
        day -= timedelta(days=1)
    return n


def per_skill(entries: list) -> dict:
    by = defaultdict(list)
    for e in entries:
        by[e["skill"]].append(e)
    return by


# ---------------------------------------------------------------- commands


def cmd_add(args):
    skills = load_skills()
    if any(s["name"].lower() == args.name.lower() for s in skills):
        raise SystemExit(f"Skill '{args.name}' already exists.")
    skills.append(
        {
            "name": args.name,
            "why": args.why or "",
            "facets": args.facet or [],
            "priority": "high" if args.high else "normal",
            "added": date.today().isoformat(),
        }
    )
    save_skills(skills)
    print(f"Added skill: {args.name}" + (" (high priority)" if args.high else ""))


def cmd_import(args):
    skills = load_skills()
    existing = {s["name"].lower() for s in skills}
    incoming = json.loads(Path(args.file).read_text(encoding="utf-8"))
    added = 0
    for item in incoming:
        if item["name"].lower() in existing:
            continue
        skills.append(
            {
                "name": item["name"],
                "why": item.get("why", ""),
                "facets": item.get("facets", []),
                "priority": item.get("priority", "normal"),
                "added": date.today().isoformat(),
            }
        )
        existing.add(item["name"].lower())
        added += 1
    save_skills(skills)
    print(f"Imported {added} new skill(s); {len(skills)} tracked in total.")


def cmd_skills(args):
    skills = load_skills()
    if not skills:
        print("No skills tracked yet. Add one with: tracker.py add \"<skill>\"")
        return
    by = per_skill(load_log())
    for s in sorted(skills, key=lambda s: (s["priority"] != "high", s["name"].lower())):
        entries = by.get(s["name"], [])
        total = sum(e["minutes"] for e in entries)
        mark = "★" if s["priority"] == "high" else " "
        line = f"{mark} {s['name']} — {fmt_minutes(total)} over {len(entries)} session(s)"
        if entries:
            last = entry_date(entries[-1])
            gap = (date.today() - last).days
            line += f", last: {'today' if gap == 0 else f'{gap}d ago'}"
        print(line)
        if s.get("why"):
            print(f"    why: {s['why']}")
        if s.get("facets"):
            print(f"    facets: {', '.join(s['facets'])}")


def cmd_log(args):
    skills = load_skills()
    name = resolve_skill(args.skill, skills)
    if name is None:
        raise SystemExit(
            f"Unknown skill '{args.skill}'. Add it first: tracker.py add \"{args.skill}\""
        )
    when = (
        datetime.fromisoformat(args.at) if args.at else datetime.now()
    )
    entry = {
        "ts": when.isoformat(timespec="seconds"),
        "skill": name,
        "minutes": args.minutes,
    }
    if args.facet:
        entry["facet"] = args.facet
    if args.note:
        entry["note"] = args.note
    append_log(entry)
    render_journal()

    entries = [e for e in load_log() if e["skill"] == name]
    total = sum(e["minutes"] for e in entries)
    dates = {entry_date(e) for e in entries}
    streak = streak_for(dates, date.today())
    bits = [f"Logged {fmt_minutes(args.minutes)} of {name}"]
    if streak > 1:
        bits.append(f"{streak}-day streak")
    bits.append(f"{fmt_minutes(total)} total over {len(entries)} session(s)")
    print(" — ".join(bits))


def rank_suggestions(skills, entries, today):
    by = per_skill(entries)
    ranked = []
    for s in skills:
        sk = by.get(s["name"], [])
        last = entry_date(sk[-1]) if sk else None
        gap = (today - last).days if last else 10**6
        total = sum(e["minutes"] for e in sk)
        ranked.append((s["priority"] != "high", -gap, total, s, gap))
    ranked.sort(key=lambda r: (r[0], r[1], r[2], r[3]["name"].lower()))
    return ranked


def next_facet(skill, entries):
    """Least-recently-used facet of this skill, so practice modes rotate."""
    facets = skill.get("facets") or []
    if not facets:
        return None
    last_used = {f: None for f in facets}
    for e in entries:
        if e["skill"] == skill["name"] and e.get("facet") in last_used:
            last_used[e["facet"]] = e["ts"]
    return min(facets, key=lambda f: (last_used[f] is not None, last_used[f] or ""))


def cmd_suggest(args):
    skills = load_skills()
    if not skills:
        print("No skills tracked yet.")
        return
    entries = load_log()
    today = date.today()
    print("What to practice now (most neglected first, ★ = high priority):")
    for _, _, total, s, gap in rank_suggestions(skills, entries, today)[:3]:
        mark = "★" if s["priority"] == "high" else " "
        since = "never practiced" if gap >= 10**6 else (
            "practiced today" if gap == 0 else f"last practiced {gap}d ago"
        )
        line = f"{mark} {s['name']} — {since}, {fmt_minutes(total)} total"
        facet = next_facet(s, entries)
        if facet:
            line += f" → try: {facet}"
        print(line)
        if s.get("why"):
            print(f"    why: {s['why']}")


def cmd_today(args):
    entries = load_log()
    today = date.today()
    todays = [e for e in entries if entry_date(e) == today]
    if todays:
        if args.nudge:
            return  # already practiced — stay silent so the reminder skips
        total = sum(e["minutes"] for e in todays)
        print(f"Today: {fmt_minutes(total)} across {len(todays)} session(s).")
        for e in todays:
            note = f" — {e['note']}" if e.get("note") else ""
            facet = f" ({e['facet']})" if e.get("facet") else ""
            print(f"  • {e['skill']}{facet}: {fmt_minutes(e['minutes'])}{note}")
        return
    print("Nothing logged today yet. Even 5 minutes counts.")
    cmd_suggest(args)


def cmd_stats(args):
    skills = load_skills()
    entries = load_log()
    if not entries:
        print("No sessions logged yet.")
        return
    today = date.today()
    cutoff = today - timedelta(days=args.days)
    recent = [e for e in entries if entry_date(e) >= cutoff]
    all_dates = {entry_date(e) for e in entries}
    active = len({entry_date(e) for e in recent})
    print(
        f"Overall: {fmt_minutes(sum(e['minutes'] for e in entries))} across "
        f"{len(entries)} sessions since {entry_date(entries[0])}."
    )
    print(
        f"Last {args.days} days: {fmt_minutes(sum(e['minutes'] for e in recent))}, "
        f"active on {active}/{args.days} days. "
        f"Current streak: {streak_for(all_dates, today)} day(s)."
    )
    by = per_skill(entries)
    order = {s["name"]: s for s in skills}
    for name in sorted(by, key=lambda n: -sum(e["minutes"] for e in by[n])):
        sk = by[name]
        total = sum(e["minutes"] for e in sk)
        dates = {entry_date(e) for e in sk}
        gap = (today - entry_date(sk[-1])).days
        mark = "★" if order.get(name, {}).get("priority") == "high" else " "
        print(
            f"{mark} {name}: {fmt_minutes(total)}, {len(sk)} sessions, "
            f"{len(dates)} days, streak {streak_for(dates, today)}, "
            f"last {'today' if gap == 0 else f'{gap}d ago'}"
        )


def cmd_review(args):
    entries = load_log()
    if not entries:
        print("No sessions logged yet.")
        return
    today = date.today()
    months = []
    y, m = today.year, today.month
    for _ in range(args.months):
        months.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    months.reverse()
    span = [e for e in entries if e["ts"][:7] in months]
    if not span:
        print(f"No sessions in the last {args.months} months.")
        return

    print(f"Look-back: last {args.months} months "
          f"({months[0]} … {months[-1]})\n")
    total = sum(e["minutes"] for e in span)
    days = {entry_date(e) for e in span}
    print(
        f"You showed up on {len(days)} days and accumulated "
        f"{fmt_minutes(total)} across {len(span)} sessions."
    )

    by_month = defaultdict(lambda: defaultdict(float))
    for e in span:
        by_month[e["ts"][:7]][e["skill"]] += e["minutes"]
    print("\nMonth by month:")
    for mo in months:
        sk = by_month.get(mo)
        if not sk:
            print(f"  {mo}: —")
            continue
        parts = ", ".join(
            f"{name} {fmt_minutes(mins)}"
            for name, mins in sorted(sk.items(), key=lambda kv: -kv[1])
        )
        print(f"  {mo}: {fmt_minutes(sum(sk.values()))} ({parts})")

    print("\nPer skill — then vs. now:")
    by = per_skill(span)
    for name in sorted(by, key=lambda n: -sum(e["minutes"] for e in by[n])):
        sk = by[name]
        dates = sorted({entry_date(e) for e in sk})
        best = cur = 1
        for a, b in zip(dates, dates[1:]):
            cur = cur + 1 if (b - a).days == 1 else 1
            best = max(best, cur)
        print(
            f"  {name}: {fmt_minutes(sum(e['minutes'] for e in sk))} "
            f"over {len(sk)} sessions, longest streak {best} day(s)"
        )
        noted = [e for e in sk if e.get("note")]
        if noted:
            first, last = noted[0], noted[-1]
            print(f"    first note ({first['ts'][:10]}): {first['note']}")
            if last is not first:
                print(f"    latest note ({last['ts'][:10]}): {last['note']}")


def render_journal() -> None:
    entries = load_log()
    lines = [
        "# Practice journal",
        "",
        "_Auto-generated by daily-skill-tracker — the source of truth is log.jsonl._",
    ]
    by_month = defaultdict(list)
    for e in entries:
        by_month[e["ts"][:7]].append(e)
    for mo in sorted(by_month):
        sub = by_month[mo]
        lines += [
            "",
            f"## {mo} — {fmt_minutes(sum(e['minutes'] for e in sub))} "
            f"across {len(sub)} sessions",
            "",
        ]
        for e in sub:
            facet = f" · {e['facet']}" if e.get("facet") else ""
            note = f" — {e['note']}" if e.get("note") else ""
            lines.append(
                f"- **{e['ts'][:10]}** {e['skill']}{facet}: "
                f"{fmt_minutes(e['minutes'])}{note}"
            )
    (data_dir() / "journal.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None):
    p = argparse.ArgumentParser(prog="tracker.py", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("add", help="track a new skill")
    sp.add_argument("name")
    sp.add_argument("--why", help="one-line reason this skill matters")
    sp.add_argument("--facet", action="append", help="sub-activity (repeatable)")
    sp.add_argument("--high", action="store_true", help="high priority in suggestions")
    sp.set_defaults(func=cmd_add)

    sp = sub.add_parser("import", help="bulk-add skills from a JSON file")
    sp.add_argument("file")
    sp.set_defaults(func=cmd_import)

    sp = sub.add_parser("skills", help="list tracked skills")
    sp.set_defaults(func=cmd_skills)

    sp = sub.add_parser("log", help="log a practice session")
    sp.add_argument("skill")
    sp.add_argument("minutes", type=float)
    sp.add_argument("--note", help="what you did / noticed")
    sp.add_argument("--facet", help="which sub-activity")
    sp.add_argument("--at", help="backdate, ISO datetime or YYYY-MM-DD")
    sp.set_defaults(func=cmd_log)

    sp = sub.add_parser("suggest", help="what to practice now")
    sp.set_defaults(func=cmd_suggest)

    sp = sub.add_parser("today", help="today's sessions (or a nudge)")
    sp.add_argument(
        "--nudge",
        action="store_true",
        help="print nothing if already practiced today (for reminders)",
    )
    sp.set_defaults(func=cmd_today)

    sp = sub.add_parser("stats", help="streaks and totals")
    sp.add_argument("--days", type=int, default=30)
    sp.set_defaults(func=cmd_stats)

    sp = sub.add_parser("review", help="long look-back over months")
    sp.add_argument("--months", type=int, default=6)
    sp.set_defaults(func=cmd_review)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
