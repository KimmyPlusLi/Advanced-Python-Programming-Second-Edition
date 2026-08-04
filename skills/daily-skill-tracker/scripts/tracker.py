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


def parse_freq(v):
    """Freq spec -> (min_times, period). Accepts 1, "daily", "2/day",
    "3/week", "2-3/week" (a range counts its lower bound as the target)."""
    import re
    if isinstance(v, (int, float)):
        return max(1, int(v)), "day"
    s = str(v).strip().lower()
    if s in ("", "daily", "everyday", "every day"):
        return 1, "day"
    if s.isdigit():
        return max(1, int(s)), "day"
    m = re.fullmatch(r"(\d+)(?:\s*-\s*(\d+))?\s*(?:x\s*)?/\s*(day|week)", s)
    if not m:
        raise SystemExit(
            f"Bad frequency '{v}' — use forms like 'daily', '2/day', "
            f"'3/week', '2-3/week'."
        )
    return max(1, int(m.group(1))), m.group(3)


def freq_str(v):
    n, per = parse_freq(v)
    raw = str(v).strip().lower()
    times = raw.split("/")[0].strip() if "/" in raw else str(n)
    if per == "day" and times in ("", "1"):
        return "daily"
    return f"{times}x/{per}"


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
            "freq": args.freq,
            "added": date.today().isoformat(),
        }
    )
    save_skills(skills)
    extras = [x for x in (
        "high priority" if args.high else "",
        freq_str(args.freq) if parse_freq(args.freq) != (1, "day") else "",
    ) if x]
    print(f"Added skill: {args.name}" + (f" ({', '.join(extras)})" if extras else ""))


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
                "freq": item.get("freq", 1),
                "added": date.today().isoformat(),
            }
        )
        existing.add(item["name"].lower())
        added += 1
    save_skills(skills)
    print(f"Imported {added} new skill(s); {len(skills)} tracked in total.")


def active(skills):
    return [s for s in skills if not s.get("archived")]


def cmd_skills(args):
    skills = load_skills()
    shown = skills if args.all else active(skills)
    if not shown:
        print("No skills tracked yet. Add one with: tracker.py add \"<skill>\"")
        return
    by = per_skill(load_log())
    for s in sorted(shown, key=lambda s: (s["priority"] != "high", s["name"].lower())):
        entries = by.get(s["name"], [])
        total = sum(e["minutes"] for e in entries)
        mark = "★" if s["priority"] == "high" else " "
        line = f"{mark} {s['name']} — {fmt_minutes(total)} over {len(entries)} session(s)"
        if parse_freq(s.get("freq", 1)) != (1, "day"):
            line += f", target {freq_str(s['freq'])}"
        if s.get("archived"):
            line += " [archived]"
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
    """Rank: still due today > high priority > longest gap > least total time."""
    by = per_skill(entries)
    ranked = []
    for s in active(skills):
        sk = by.get(s["name"], [])
        last = entry_date(sk[-1]) if sk else None
        gap = (today - last).days if last else 10**6
        total = sum(e["minutes"] for e in sk)
        done_today = sum(1 for e in sk if entry_date(e) == today)
        fmin, per = parse_freq(s.get("freq", 1))
        if per == "day":
            due = max(0, fmin - done_today)
        else:
            week_start = today - timedelta(days=today.weekday())
            done_week = sum(1 for e in sk if week_start <= entry_date(e) <= today)
            due = 0 if done_today else max(0, fmin - done_week)
        ranked.append(
            (due == 0, s["priority"] != "high", -gap, total, s, gap, due, per)
        )
    ranked.sort(key=lambda r: (r[0], r[1], r[2], r[3], r[4]["name"].lower()))
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
    print("What to practice now (due & most neglected first, ★ = high priority):")
    for _, _, _, total, s, gap, due, per in rank_suggestions(skills, entries, today)[:3]:
        mark = "★" if s["priority"] == "high" else " "
        since = "never practiced" if gap >= 10**6 else (
            "practiced today" if gap == 0 else f"last practiced {gap}d ago"
        )
        line = f"{mark} {s['name']} — {since}, {fmt_minutes(total)} total"
        if due and per == "week":
            line += f" [{due} more this week]"
        elif due > 1:
            line += f" [{due} more today]"
        facet = next_facet(s, entries)
        if facet:
            line += f" → try: {facet}"
        print(line)
        if s.get("why"):
            print(f"    why: {s['why']}")


def cmd_today(args):
    entries = load_log()
    skills = load_skills()
    today = date.today()
    todays = [e for e in entries if entry_date(e) == today]
    still_due = [
        (s, due, per)
        for *_, s, _, due, per in rank_suggestions(skills, entries, today)
        if due > 0
    ]
    if todays:
        silent = not getattr(args, "strict", False) or not still_due
        if args.nudge and silent:
            return  # nudge mode: nothing to say, reminder stays quiet
        total = sum(e["minutes"] for e in todays)
        print(f"Today: {fmt_minutes(total)} across {len(todays)} session(s).")
        for e in todays:
            note = f" — {e['note']}" if e.get("note") else ""
            facet = f" ({e['facet']})" if e.get("facet") else ""
            print(f"  • {e['skill']}{facet}: {fmt_minutes(e['minutes'])}{note}")
        if still_due:
            print(
                "Still due: "
                + ", ".join(
                    s["name"]
                    + (f" ({d} more this week)" if per == "week"
                       else f" x{d}" if d > 1 else "")
                    for s, d, per in still_due
                )
            )
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


def cmd_edit(args):
    skills = load_skills()
    name = resolve_skill(args.skill, skills)
    if name is None:
        raise SystemExit(f"Unknown skill '{args.skill}'.")
    s = next(s for s in skills if s["name"] == name)
    if args.why is not None:
        s["why"] = args.why
    if args.priority:
        s["priority"] = args.priority
    if args.freq:
        parse_freq(args.freq)  # validate
        s["freq"] = args.freq
    if args.restore:
        s.pop("archived", None)
    if args.add_facet:
        s.setdefault("facets", []).extend(
            f for f in args.add_facet if f not in s.get("facets", [])
        )
    if args.remove_facet:
        s["facets"] = [f for f in s.get("facets", []) if f not in args.remove_facet]
    if args.rename:
        old = s["name"]
        s["name"] = args.rename
        entries = load_log()
        f = data_dir() / "log.jsonl"
        with f.open("w", encoding="utf-8") as fh:
            for e in entries:
                if e["skill"] == old:
                    e["skill"] = args.rename
                fh.write(json.dumps(e, ensure_ascii=False) + "\n")
        render_journal()
    save_skills(skills)
    print(f"Updated skill: {s['name']}")


def cmd_remove(args):
    skills = load_skills()
    name = resolve_skill(args.skill, skills)
    if name is None:
        raise SystemExit(f"Unknown skill '{args.skill}'.")
    if args.purge:
        save_skills([s for s in skills if s["name"] != name])
        print(f"Removed '{name}' from the skill list (logged history kept).")
        return
    next(s for s in skills if s["name"] == name)["archived"] = True
    save_skills(skills)
    print(
        f"Archived '{name}' — hidden from lists and suggestions, history kept. "
        f"Restore with: edit \"{name}\" --restore"
    )


def period_range(period: str, today: date):
    if period == "day":
        return today, today, f"Today ({today})"
    if period == "week":
        start = today - timedelta(days=today.weekday())
        return start, today, f"This week ({start} … {today})"
    if period == "month":
        return today.replace(day=1), today, f"{today:%B %Y}"
    return today.replace(month=1, day=1), today, f"Year to date ({today.year})"


def cmd_summary(args):
    entries = load_log()
    today = date.today()
    start, end, label = period_range(args.period, today)
    span = [e for e in entries if start <= entry_date(e) <= end]
    print(label)
    if not span:
        print("  No sessions logged in this period.")
        return
    days = {entry_date(e) for e in span}
    print(
        f"  {fmt_minutes(sum(e['minutes'] for e in span))} across "
        f"{len(span)} session(s) on {len(days)} day(s)."
    )
    by = per_skill(span)
    for name in sorted(by, key=lambda n: -sum(e["minutes"] for e in by[n])):
        sk = by[name]
        facets = sorted({e["facet"] for e in sk if e.get("facet")})
        line = f"  • {name}: {fmt_minutes(sum(e['minutes'] for e in sk))}, {len(sk)} session(s)"
        if facets:
            line += f" ({', '.join(facets)})"
        print(line)
    noted = [e for e in span if e.get("note")]
    if noted:
        print("  Notes:")
        for e in noted[-5:]:
            print(f"    {e['ts'][:10]} {e['skill']}: {e['note']}")


# ------------------------------------------------------------- dashboard

# Reference categorical palette (dataviz skill, validated): slots 1-7 + Other.
_SLOTS_LIGHT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100",
                "#e87ba4", "#008300", "#4a3aa7"]
_SLOTS_DARK = ["#3987e5", "#d95926", "#199e70", "#c98500",
               "#d55181", "#008300", "#9085e9"]
_OTHER = "#898781"


def _esc(s):
    import html
    return html.escape(str(s), quote=True)


def _nice_max(v):
    for step in (30, 60, 120, 240, 480, 960):
        if v <= step * 4:
            return ((int(v) // step) + 1) * step
    return ((int(v) // 960) + 1) * 960


def _bar_path(x, y, w, h, r):
    """Bar with rounded top corners, anchored to the baseline."""
    r = min(r, w / 2, h)
    return (f"M{x:.1f},{y + h:.1f} L{x:.1f},{y + r:.1f} "
            f"Q{x:.1f},{y:.1f} {x + r:.1f},{y:.1f} L{x + w - r:.1f},{y:.1f} "
            f"Q{x + w:.1f},{y:.1f} {x + w:.1f},{y + r:.1f} "
            f"L{x + w:.1f},{y + h:.1f} Z")


def _axis_label(minutes):
    return f"{minutes / 60:g}h" if minutes >= 60 else f"{minutes:g}m"


def cmd_dashboard(args):
    skills = load_skills()
    entries = load_log()
    today = date.today()
    out = Path(args.out) if args.out else data_dir() / "dashboard.html"

    # Stable color per skill: skills.json order fills slots 1-7, rest = Other.
    color_idx = {}
    for i, s in enumerate(skills):
        color_idx[s["name"]] = i if i < len(_SLOTS_LIGHT) else -1
    css_vars_l = "".join(f"--c{i}:{h};" for i, h in enumerate(_SLOTS_LIGHT))
    css_vars_d = "".join(f"--c{i}:{h};" for i, h in enumerate(_SLOTS_DARK))

    def color_of(name):
        i = color_idx.get(name, -1)
        return "var(--cother)" if i < 0 else f"var(--c{i})"

    ytd = [e for e in entries if entry_date(e).year == today.year]
    ytd_days = {entry_date(e) for e in ytd}
    all_dates = {entry_date(e) for e in entries}
    streak = streak_for(all_dates, today)
    sorted_ytd_dates = sorted(ytd_days)
    best = cur = 1 if sorted_ytd_dates else 0
    for a, b in zip(sorted_ytd_dates, sorted_ytd_dates[1:]):
        cur = cur + 1 if (b - a).days == 1 else 1
        best = max(best, cur)

    tiles = [
        (f"{sum(e['minutes'] for e in ytd) / 60:.1f} h", "practiced this year"),
        (str(len(ytd)), "sessions"),
        (str(len(ytd_days)), "active days"),
        (f"{streak} d", "current streak"),
        (f"{best} d", "longest streak this year"),
    ]
    tiles_html = "".join(
        f'<div class="tile"><div class="tile-v">{_esc(v)}</div>'
        f'<div class="tile-l">{_esc(l)}</div></div>'
        for v, l in tiles
    )

    # --- daily heatmap: last 26 weeks ---------------------------------
    per_day = defaultdict(float)
    day_skills = defaultdict(set)
    for e in entries:
        d = entry_date(e)
        per_day[d] += e["minutes"]
        day_skills[d].add(e["skill"])
    monday = today - timedelta(days=today.weekday())
    start = monday - timedelta(weeks=25)
    cell, gap = 12, 3
    cells, month_labels = [], []
    seen_month = None
    for w in range(26):
        wk = start + timedelta(weeks=w)
        if wk.month != seen_month:
            seen_month = wk.month
            month_labels.append(
                f'<text x="{w * (cell + gap)}" y="10" class="ax">{wk:%b}</text>'
            )
        for d in range(7):
            day = wk + timedelta(days=d)
            if day > today:
                continue
            m = per_day.get(day, 0)
            q = ("none" if m == 0 else "q1" if m < 10 else "q2" if m < 20
                 else "q3" if m < 40 else "q4")
            tip = f"{day} — " + (
                f"{fmt_minutes(m)}: " + ", ".join(sorted(day_skills[day]))
                if m else "no practice"
            )
            cells.append(
                f'<rect x="{w * (cell + gap)}" y="{16 + d * (cell + gap)}" '
                f'width="{cell}" height="{cell}" rx="3" class="hm {q}" '
                f'data-tip="{_esc(tip)}"/>'
            )
    hm_w = 26 * (cell + gap) - gap + 18  # right padding so the last month label fits
    hm_h = 16 + 7 * (cell + gap) - gap
    heatmap = (
        f'<svg viewBox="0 0 {hm_w} {hm_h}" role="img" '
        f'aria-label="Daily practice heatmap, last 26 weeks">'
        + "".join(month_labels) + "".join(cells) + "</svg>"
    )

    # --- weekly bars: last 12 ISO weeks (total minutes) ----------------
    weeks = []
    for i in range(11, -1, -1):
        wk = monday - timedelta(weeks=i)
        total = sum(
            per_day.get(wk + timedelta(days=d), 0) for d in range(7)
        )
        weeks.append((wk, total))
    W, H, pad_l, pad_b = 720, 180, 44, 22
    maxv = _nice_max(max([t for _, t in weeks] + [1]))
    plot_h = H - pad_b - 8
    grid, bars, xlabels = [], [], []
    for i in range(1, 5):
        y = 8 + plot_h * (1 - i / 4)
        grid.append(
            f'<line x1="{pad_l}" y1="{y:.1f}" x2="{W}" y2="{y:.1f}" class="grid"/>'
            f'<text x="{pad_l - 6}" y="{y + 3.5:.1f}" text-anchor="end" class="ax">'
            f"{_axis_label(maxv * i / 4)}</text>"
        )
    bw = (W - pad_l) / 12 * 0.62
    for i, (wk, total) in enumerate(weeks):
        x = pad_l + (W - pad_l) / 12 * (i + 0.19)
        h = plot_h * total / maxv
        if total > 0:
            bars.append(
                f'<path d="{_bar_path(x, 8 + plot_h - h, bw, h, 4)}" '
                f'fill="var(--c0)" data-tip="{_esc(f"Week of {wk}: {fmt_minutes(total)}")}"/>'
            )
        if i % 2 == 0:
            xlabels.append(
                f'<text x="{x + bw / 2:.1f}" y="{H - 6}" text-anchor="middle" '
                f'class="ax">{wk:%m/%d}</text>'
            )
    weekly = (
        f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Weekly practice minutes">'
        f'<line x1="{pad_l}" y1="{8 + plot_h}" x2="{W}" y2="{8 + plot_h}" class="base"/>'
        + "".join(grid) + "".join(bars) + "".join(xlabels) + "</svg>"
    )

    # --- monthly stacked by skill, current year ------------------------
    months = [f"{today.year:04d}-{m:02d}" for m in range(1, today.month + 1)]
    per_month = defaultdict(lambda: defaultdict(float))
    for e in ytd:
        key = e["skill"] if color_idx.get(e["skill"], -1) >= 0 else "Other"
        per_month[e["ts"][:7]][key] += e["minutes"]
    with_data = {k for mo in months for k, v in per_month[mo].items() if v > 0}
    stack_order = [
        s["name"] for s in skills
        if color_idx.get(s["name"], -1) >= 0 and s["name"] in with_data
    ]
    if "Other" in with_data:
        stack_order.append("Other")
    maxm = _nice_max(max([sum(per_month[mo].values()) for mo in months] + [1]))
    grid2, bars2, xlabels2 = [], [], []
    for i in range(1, 5):
        y = 8 + plot_h * (1 - i / 4)
        grid2.append(
            f'<line x1="{pad_l}" y1="{y:.1f}" x2="{W}" y2="{y:.1f}" class="grid"/>'
            f'<text x="{pad_l - 6}" y="{y + 3.5:.1f}" text-anchor="end" class="ax">'
            f"{_axis_label(maxm * i / 4)}</text>"
        )
    slot_w = (W - pad_l) / max(len(months), 6)
    bw2 = slot_w * 0.55
    for i, mo in enumerate(months):
        x = pad_l + slot_w * (i + 0.225)
        y = 8 + plot_h
        for name in stack_order:
            m = per_month[mo].get(name, 0)
            if m <= 0:
                continue
            h = plot_h * m / maxm
            y -= h
            fill = "var(--cother)" if name == "Other" else color_of(name)
            bars2.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw2:.1f}" height="{h:.1f}" '
                f'rx="2" fill="{fill}" class="seg" '
                f'data-tip="{_esc(f"{mo} {name}: {fmt_minutes(m)}")}"/>'
            )
        xlabels2.append(
            f'<text x="{x + bw2 / 2:.1f}" y="{H - 6}" text-anchor="middle" class="ax">'
            f"{datetime.strptime(mo, '%Y-%m'):%b}</text>"
        )
    monthly = (
        f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Monthly minutes by skill">'
        f'<line x1="{pad_l}" y1="{8 + plot_h}" x2="{W}" y2="{8 + plot_h}" class="base"/>'
        + "".join(grid2) + "".join(bars2) + "".join(xlabels2) + "</svg>"
    )
    legend = "".join(
        f'<span class="chip"><span class="swatch" style="background:'
        f'{"var(--cother)" if n == "Other" else color_of(n)}"></span>{_esc(n)}</span>'
        for n in stack_order
    )

    # --- YTD per-skill horizontal bars (single hue) --------------------
    by_ytd = per_skill(ytd)
    ranked = sorted(by_ytd, key=lambda n: -sum(e["minutes"] for e in by_ytd[n]))
    row_h, lab_w = 30, 220
    maxs = max([sum(e["minutes"] for e in by_ytd[n]) for n in ranked] + [1])
    rows = []
    for i, name in enumerate(ranked):
        total = sum(e["minutes"] for e in by_ytd[name])
        y = i * row_h
        w = (W - lab_w - 70) * total / maxs
        rows.append(
            f'<text x="{lab_w - 10}" y="{y + 19}" text-anchor="end" class="lbl">'
            f"{_esc(name)}</text>"
            f'<path d="M{lab_w},{y + 6} L{lab_w + max(w, 3):.1f},{y + 6} '
            f'Q{lab_w + max(w, 3) + 4:.1f},{y + 6} {lab_w + max(w, 3) + 4:.1f},{y + 10} '
            f'L{lab_w + max(w, 3) + 4:.1f},{y + 20} '
            f'Q{lab_w + max(w, 3) + 4:.1f},{y + 24} {lab_w + max(w, 3):.1f},{y + 24} '
            f'L{lab_w},{y + 24} Z" fill="var(--c0)" '
            f'data-tip="{_esc(f"{name}: {fmt_minutes(total)}, {len(by_ytd[name])} sessions")}"/>'
            f'<text x="{lab_w + max(w, 3) + 12:.1f}" y="{y + 19}" class="val">'
            f"{_esc(fmt_minutes(total))}</text>"
        )
    ytd_svg = (
        f'<svg viewBox="0 0 {W} {max(len(ranked), 1) * row_h}" role="img" '
        f'aria-label="Year-to-date minutes per skill">' + "".join(rows) + "</svg>"
    )

    # --- table view (accessibility) ------------------------------------
    trows = []
    for name in ranked:
        sk = by_ytd[name]
        last = entry_date(sk[-1])
        gap_d = (today - last).days
        trows.append(
            f"<tr><td>{_esc(name)}</td>"
            f'<td class="num">{fmt_minutes(sum(e["minutes"] for e in sk))}</td>'
            f'<td class="num">{len(sk)}</td>'
            f'<td class="num">{len({entry_date(e) for e in sk})}</td>'
            f"<td>{'today' if gap_d == 0 else _esc(f'{gap_d}d ago')}</td></tr>"
        )
    recent = [e for e in entries if e.get("note")][-8:]
    notes_html = "".join(
        f'<li><span class="nd">{_esc(e["ts"][:10])}</span> '
        f"<strong>{_esc(e['skill'])}</strong>"
        + (f' <span class="nf">· {_esc(e["facet"])}</span>' if e.get("facet") else "")
        + f" — {_esc(e['note'])}</li>"
        for e in reversed(recent)
    )

    page = f"""<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Skill tracker — {today.year}</title>
<style>
.viz-root {{
  color-scheme: light;
  --surface-1:#fcfcfb; --page:#f9f9f7; --ink:#0b0b0b; --ink2:#52514e;
  --muted:#898781; --grid:#e1e0d9; --base:#c3c2b7;
  --border:rgba(11,11,11,.10); --cother:{_OTHER}; {css_vars_l}
  --q1:#b7d3f6; --q2:#6da7ec; --q3:#2a78d6; --q4:#184f95; --hm0:#f0efec;
}}
@media (prefers-color-scheme: dark) {{
  :root:where(:not([data-theme="light"])) .viz-root {{
    color-scheme: dark;
    --surface-1:#1a1a19; --page:#0d0d0d; --ink:#ffffff; --ink2:#c3c2b7;
    --grid:#2c2c2a; --base:#383835; --border:rgba(255,255,255,.10); {css_vars_d}
    --q1:#104281; --q2:#1c5cab; --q3:#3987e5; --q4:#86b6ef; --hm0:#242423;
  }}
}}
:root[data-theme="dark"] .viz-root {{
  color-scheme: dark;
  --surface-1:#1a1a19; --page:#0d0d0d; --ink:#ffffff; --ink2:#c3c2b7;
  --grid:#2c2c2a; --base:#383835; --border:rgba(255,255,255,.10); {css_vars_d}
  --q1:#104281; --q2:#1c5cab; --q3:#3987e5; --q4:#86b6ef; --hm0:#242423;
}}
.viz-root {{
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  background: var(--page); color: var(--ink);
  margin: 0; padding: 24px; min-height: 100vh; box-sizing: border-box;
}}
.viz-root h1 {{ font-size: 20px; margin: 0 0 4px; }}
.viz-root .sub {{ color: var(--ink2); font-size: 13px; margin-bottom: 20px; }}
.card {{ background: var(--surface-1); border: 1px solid var(--border);
  border-radius: 10px; padding: 16px 18px; margin-bottom: 16px; }}
.card h2 {{ font-size: 13px; font-weight: 600; color: var(--ink2);
  margin: 0 0 12px; text-transform: uppercase; letter-spacing: .04em; }}
.tiles {{ display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 16px; }}
.tile {{ background: var(--surface-1); border: 1px solid var(--border);
  border-radius: 10px; padding: 14px 18px; flex: 1 1 120px; }}
.tile-v {{ font-size: 26px; font-weight: 650; }}
.tile-l {{ font-size: 12px; color: var(--ink2); margin-top: 2px; }}
svg {{ width: 100%; height: auto; display: block; overflow: visible; }}
.ax {{ font: 10.5px system-ui, sans-serif; fill: var(--muted);
  font-variant-numeric: tabular-nums; }}
.lbl {{ font: 12px system-ui, sans-serif; fill: var(--ink2); }}
.val {{ font: 11.5px system-ui, sans-serif; fill: var(--ink2);
  font-variant-numeric: tabular-nums; }}
.grid {{ stroke: var(--grid); stroke-width: 1; }}
.base {{ stroke: var(--base); stroke-width: 1; }}
.hm {{ fill: var(--hm0); }} .hm.q1 {{ fill: var(--q1); }}
.hm.q2 {{ fill: var(--q2); }} .hm.q3 {{ fill: var(--q3); }}
.hm.q4 {{ fill: var(--q4); }}
.seg {{ stroke: var(--surface-1); stroke-width: 2; }}
[data-tip]:hover {{ filter: brightness(1.12); cursor: default; }}
.legend {{ display: flex; flex-wrap: wrap; gap: 6px 14px; margin-top: 10px; }}
.chip {{ font-size: 12px; color: var(--ink2); display: inline-flex;
  align-items: center; gap: 6px; }}
.swatch {{ width: 10px; height: 10px; border-radius: 3px; display: inline-block; }}
table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
th {{ text-align: left; color: var(--ink2); font-weight: 600;
  border-bottom: 1px solid var(--base); padding: 6px 10px 6px 0; }}
td {{ border-bottom: 1px solid var(--grid); padding: 7px 10px 7px 0; }}
.num {{ font-variant-numeric: tabular-nums; }}
.notes {{ list-style: none; margin: 0; padding: 0; font-size: 13px; }}
.notes li {{ padding: 6px 0; border-bottom: 1px solid var(--grid); }}
.notes li:last-child {{ border-bottom: none; }}
.nd {{ color: var(--muted); font-variant-numeric: tabular-nums; }}
.nf {{ color: var(--ink2); }}
#tip {{ position: fixed; display: none; background: var(--ink);
  color: var(--page); font-size: 12px; padding: 5px 9px; border-radius: 6px;
  pointer-events: none; max-width: 320px; z-index: 10; }}
.wrap {{ overflow-x: auto; }}
</style>
<div class="viz-root">
<h1>Skill practice — {today.year}</h1>
<div class="sub">碎片时间, compounding. Generated {today}.</div>
<div class="tiles">{tiles_html}</div>
<div class="card"><h2>Daily — last 26 weeks</h2><div class="wrap">{heatmap}</div></div>
<div class="card"><h2>Weekly — last 12 weeks</h2>{weekly}</div>
<div class="card"><h2>Monthly by skill — {today.year}</h2>{monthly}
<div class="legend">{legend}</div></div>
<div class="card"><h2>Year to date by skill</h2>{ytd_svg}</div>
<div class="card"><h2>Table view</h2>
<table><thead><tr><th>Skill</th><th class="num">Time</th>
<th class="num">Sessions</th><th class="num">Days</th><th>Last</th></tr></thead>
<tbody>{"".join(trows)}</tbody></table></div>
<div class="card"><h2>Recent reflections</h2><ul class="notes">{notes_html}</ul></div>
<div id="tip"></div>
</div>
<script>
(function () {{
  var tip = document.getElementById('tip');
  document.addEventListener('mousemove', function (e) {{
    var t = e.target.closest ? e.target.closest('[data-tip]') : null;
    if (!t) {{ tip.style.display = 'none'; return; }}
    tip.textContent = t.getAttribute('data-tip');
    tip.style.display = 'block';
    var x = e.clientX + 12, y = e.clientY + 14;
    var r = tip.getBoundingClientRect();
    if (x + r.width > innerWidth - 8) x = e.clientX - r.width - 12;
    if (y + r.height > innerHeight - 8) y = e.clientY - r.height - 14;
    tip.style.left = x + 'px'; tip.style.top = y + 'px';
  }});
}})();
</script>
"""
    out.write_text("<!doctype html>\n" + page, encoding="utf-8")
    print(f"Dashboard written to {out}")


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
    sp.add_argument("--freq", default="daily",
                    help="target: 'daily', '2/day', '3/week', '2-3/week'")
    sp.set_defaults(func=cmd_add)

    sp = sub.add_parser("edit", help="update a skill's why/facets/priority/freq")
    sp.add_argument("skill")
    sp.add_argument("--why")
    sp.add_argument("--priority", choices=["high", "normal"])
    sp.add_argument("--freq", help="target: 'daily', '2/day', '3/week', '2-3/week'")
    sp.add_argument("--add-facet", action="append")
    sp.add_argument("--remove-facet", action="append")
    sp.add_argument("--rename", help="new name (rewrites logged history too)")
    sp.add_argument("--restore", action="store_true", help="un-archive the skill")
    sp.set_defaults(func=cmd_edit)

    sp = sub.add_parser("remove", help="archive a skill (history kept)")
    sp.add_argument("skill")
    sp.add_argument("--purge", action="store_true",
                    help="drop from the skill list entirely (log still kept)")
    sp.set_defaults(func=cmd_remove)

    sp = sub.add_parser("import", help="bulk-add skills from a JSON file")
    sp.add_argument("file")
    sp.set_defaults(func=cmd_import)

    sp = sub.add_parser("skills", help="list tracked skills")
    sp.add_argument("--all", action="store_true", help="include archived skills")
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
    sp.add_argument(
        "--strict",
        action="store_true",
        help="with --nudge: only stay silent once every per-day target is met",
    )
    sp.set_defaults(func=cmd_today)

    sp = sub.add_parser("stats", help="streaks and totals")
    sp.add_argument("--days", type=int, default=30)
    sp.set_defaults(func=cmd_stats)

    sp = sub.add_parser("review", help="long look-back over months")
    sp.add_argument("--months", type=int, default=6)
    sp.set_defaults(func=cmd_review)

    sp = sub.add_parser("summary", help="ledger rollup for a period")
    sp.add_argument("--period", choices=["day", "week", "month", "ytd"],
                    default="week")
    sp.set_defaults(func=cmd_summary)

    sp = sub.add_parser("dashboard", help="render the visual HTML dashboard")
    sp.add_argument("--out", help="output path (default: <data dir>/dashboard.html)")
    sp.set_defaults(func=cmd_dashboard)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        sys.exit(0)
