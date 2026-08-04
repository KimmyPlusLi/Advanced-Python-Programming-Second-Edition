#!/usr/bin/env python3
"""Build the daily or weekly digest from matched jobs, maintaining seen-state.

State: data/state/seen_jobs.json — {job_id: {first_seen, last_seen, title,
company, url, matched_role, score}}. A job is NEW if its id is not in state.
Jobs not seen for `PRUNE_DAYS` are pruned weekly (posting closed).

Daily digest  = new matches only.
Weekly digest = all active matches grouped by role + skill-frequency trends
                (input for the agent's gap analysis).

Output: data/digests/{mode}-YYYY-MM-DD.md. The file contains `---8<---`
markers splitting it into chunks < ~3500 chars, so the agent can send each
chunk as one Telegram message. Summary JSON is printed to stdout.
"""

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = SKILL_DIR / "data"
STATE_PATH = DATA_DIR / "state" / "seen_jobs.json"
CHUNK_LIMIT = 3500
PRUNE_DAYS = 21


def chunked(lines):
    """Join markdown lines, inserting Telegram chunk markers."""
    out, size = [], 0
    for line in lines:
        if size + len(line) > CHUNK_LIMIT and size > 0:
            out.append("\n---8<---\n")
            size = 0
        out.append(line)
        size += len(line) + 1
    return "\n".join(out)


def fmt_job(j, state_entry=None):
    loc = f" — {j['location']}" if j.get("location") else ""
    age = ""
    if state_entry:
        age = f" _(first seen {state_entry['first_seen'][:10]})_"
    kws = ", ".join(j.get("keyword_hits", [])[:6])
    kw_line = f"\n  ‣ {kws}" if kws else ""
    return (f"• [{j['title']}]({j['url']}) — **{j['company']}**{loc} "
            f"(score {j['score']}){age}{kw_line}")


def skill_frequency(jobs, lexicon):
    counts = Counter()
    for j in jobs:
        text = (j.get("title", "") + " " + (j.get("description") or "")).lower()
        for skill in lexicon:
            if skill.lower() in text:
                counts[skill] += 1
    return counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["daily", "weekly"], required=True)
    ap.add_argument("--matched", default=str(DATA_DIR / "matched_jobs.json"))
    ap.add_argument("--profile", default=str(SKILL_DIR / "config" / "profile.json"))
    ap.add_argument("--date", help="override run date YYYY-MM-DD (for testing)")
    args = ap.parse_args()

    profile = json.loads(Path(args.profile).read_text())
    matched = json.loads(Path(args.matched).read_text())
    jobs = matched.get("jobs", [])
    now = (datetime.strptime(args.date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
           if args.date else datetime.now(timezone.utc))
    today = now.date().isoformat()

    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    state = json.loads(STATE_PATH.read_text()) if STATE_PATH.exists() else {}

    new_jobs = []
    for j in jobs:
        entry = state.get(j["id"])
        if entry is None:
            new_jobs.append(j)
            state[j["id"]] = {"first_seen": today, "last_seen": today,
                              "title": j["title"], "company": j["company"],
                              "url": j["url"], "matched_role": j["matched_role"],
                              "score": j["score"]}
        else:
            entry["last_seen"] = today
            entry["score"] = j["score"]

    pruned = 0
    if args.mode == "weekly":
        cutoff = (now - timedelta(days=PRUNE_DAYS)).date().isoformat()
        stale = [k for k, v in state.items() if v["last_seen"] < cutoff]
        for k in stale:
            del state[k]
        pruned = len(stale)

    dcfg = profile.get("digest", {})
    lines = []
    if args.mode == "daily":
        cap = dcfg.get("max_daily_items", 25)
        lines.append(f"**Job digest — {today}** ({len(new_jobs)} new match(es))")
        lines.append("")
        by_role = defaultdict(list)
        for j in new_jobs[:cap]:
            by_role[j["matched_role_label"]].append(j)
        for role, js in by_role.items():
            lines.append(f"__{role}__")
            for j in js:
                lines.append(fmt_job(j))
            lines.append("")
        if len(new_jobs) > cap:
            lines.append(f"…and {len(new_jobs) - cap} more (see weekly digest).")
    else:
        cap = dcfg.get("max_weekly_items", 60)
        active = [j for j in jobs if j["id"] in state][:cap]
        lines.append(f"**Weekly job digest — {today}**")
        lines.append(f"{len(jobs)} active matches across "
                     f"{len({j['company'] for j in jobs})} firms; "
                     f"{len(new_jobs)} new this run; {pruned} stale removed.")
        lines.append("")
        by_role = defaultdict(list)
        for j in active:
            by_role[j["matched_role_label"]].append(j)
        for role, js in by_role.items():
            lines.append(f"__{role} ({len(js)})__")
            for j in js:
                lines.append(fmt_job(j, state.get(j["id"])))
            lines.append("")
        freq = skill_frequency(jobs, profile.get("skill_lexicon", []))
        if freq:
            lines.append("__Most-demanded skills this week__")
            for skill, n in freq.most_common(15):
                lines.append(f"• {skill}: {n} posting(s)")
            lines.append("")
            lines.append("_Gap analysis follows in the next message(s)._")

    failures = matched.get("failures", [])
    if failures:
        lines.append("")
        lines.append("⚠️ __Sources that failed this run__")
        for f in failures:
            lines.append(f"• {f['company']}: {f['error'][:120]}")

    digest_dir = DATA_DIR / "digests"
    digest_dir.mkdir(parents=True, exist_ok=True)
    out_path = digest_dir / f"{args.mode}-{today}.md"
    out_path.write_text(chunked(lines))
    STATE_PATH.write_text(json.dumps(state, indent=2))

    print(json.dumps({
        "digest_path": str(out_path),
        "mode": args.mode,
        "new_matches": len(new_jobs),
        "active_matches": len(jobs),
        "pruned": pruned,
        "failures": len(failures),
        "should_notify": bool(new_jobs) or args.mode == "weekly"
                         or dcfg.get("notify_when_empty", False) or bool(failures),
    }, indent=2))


if __name__ == "__main__":
    main()
