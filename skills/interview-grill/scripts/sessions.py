#!/usr/bin/env python3
"""Archive & retrieval CLI for mock-interview sessions.

Sessions are archived by the agent after every interview (schema in
references/INTERVIEW_FLOW.md) to data/sessions/*.json. This tool retrieves
them for iteration: revisit a topic's full question/answer history, replay a
session, or export the whole archive.

Usage:
  python3 sessions.py list [--role prop_trader]
  python3 sessions.py show 2026-08-03            # date or filename fragment
  python3 sessions.py topic "market making"      # cross-session topic history
  python3 sessions.py retake [--role R] [--max-score 3] [--limit 10]
  python3 sessions.py export [--out PATH]        # one markdown archive
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SESSIONS_DIR = SKILL_DIR / "data" / "sessions"


def load_sessions(role=None):
    sessions = []
    if SESSIONS_DIR.exists():
        for p in sorted(SESSIONS_DIR.glob("*.json")):
            try:
                s = json.loads(p.read_text())
            except (json.JSONDecodeError, OSError):
                continue
            s["_file"] = p.name
            if role and s.get("role") != role:
                continue
            sessions.append(s)
    return sessions


def overall(s):
    if isinstance(s.get("overall"), (int, float)):
        return s["overall"]
    scores = [q["score"] for q in s.get("questions", [])
              if isinstance(q.get("score"), (int, float))]
    return round(sum(scores) / len(scores), 2) if scores else None


def cmd_list(args):
    sessions = load_sessions(args.role)
    if not sessions:
        print("no archived sessions" + (f" for role {args.role}" if args.role else ""))
        return
    print(f"{'date':<12} {'role':<18} {'mode':<7} {'Qs':>3} {'overall':>7} {'comm':>5}  file")
    for s in sessions:
        print(f"{s.get('date','?'):<12} {s.get('role','?'):<18} "
              f"{s.get('mode','?'):<7} {len(s.get('questions',[])):>3} "
              f"{str(overall(s) or '-'):>7} {str(s.get('communication_score','-')):>5}  {s['_file']}")


def print_question(q, indent="  "):
    print(f"{indent}[{q.get('score','-')}/5] ({q.get('topic','?')})")
    if q.get("question"):
        print(f"{indent}Q: {q['question']}")
    for key, label in (("answer_full", "A"), ("answer_summary", "A(summary)"),
                       ("ideal_answer", "Ideal"), ("notes", "Notes")):
        if q.get(key):
            print(f"{indent}{label}: {q[key]}")


def cmd_show(args):
    matches = [s for s in load_sessions()
               if args.session in s["_file"] or args.session == s.get("date")]
    if not matches:
        print(f"no session matching {args.session!r} — try 'list'")
        return
    for s in matches:
        print(f"=== {s['_file']} — {s.get('role','?')} / {s.get('mode','?')} / "
              f"{s.get('difficulty','?')} — overall {overall(s)}, "
              f"communication {s.get('communication_score','-')}")
        for q in s.get("questions", []):
            print_question(q)
            print()
        if s.get("language_errors"):
            print("  English corrections:")
            for e in s["language_errors"]:
                print(f"    \"{e.get('said','')}\" -> \"{e.get('correct','')}\" ({e.get('type','')})")
        if s.get("drills_assigned"):
            print("  Drills assigned: " + "; ".join(s["drills_assigned"]))
        print()


def cmd_topic(args):
    needle = args.topic.lower()
    hits = []
    for s in load_sessions(args.role):
        for q in s.get("questions", []):
            if needle in (q.get("topic") or "").lower():
                hits.append((s.get("date", s["_file"][:10]), s.get("role", "?"), q))
    if not hits:
        print(f"no archived questions on topic matching {args.topic!r}")
        return
    hits.sort(key=lambda h: h[0])
    scores = [q["score"] for _, _, q in hits if isinstance(q.get("score"), (int, float))]
    print(f"=== topic history: {args.topic!r} — {len(hits)} question(s), "
          f"avg {round(sum(scores)/len(scores), 2) if scores else '-'}, "
          f"scores over time: {scores}")
    for date, role, q in hits:
        print(f"\n--- {date} ({role})")
        print_question(q)


def cmd_retake(args):
    """Low-scoring past questions, best candidates for a retake session."""
    candidates = []
    for s in load_sessions(args.role):
        for q in s.get("questions", []):
            sc = q.get("score")
            if isinstance(sc, (int, float)) and sc <= args.max_score:
                candidates.append({"date": s.get("date", s["_file"][:10]),
                                   "role": s.get("role", "?"), **q})
    # Worst and least-recently-retested first; one representative per topic
    # unless --all, so a retake session covers ground.
    candidates.sort(key=lambda q: (q.get("score", 0), q["date"]))
    if not args.all:
        seen, unique = set(), []
        for q in candidates:
            if q.get("topic") in seen:
                continue
            seen.add(q.get("topic"))
            unique.append(q)
        candidates = unique
    print(json.dumps(candidates[:args.limit], indent=2))


def cmd_export(args):
    sessions = load_sessions()
    out = Path(args.out) if args.out else SKILL_DIR / "data" / "sessions_archive.md"
    lines = [f"# Interview session archive — {len(sessions)} session(s)\n"]
    by_topic = defaultdict(list)
    for s in sessions:
        lines.append(f"\n## {s.get('date','?')} — {s.get('role','?')} "
                     f"({s.get('mode','?')}, overall {overall(s)})\n")
        for q in s.get("questions", []):
            lines.append(f"- **[{q.get('score','-')}/5] {q.get('topic','?')}** — "
                         f"{q.get('question','')}")
            if q.get("answer_full") or q.get("answer_summary"):
                lines.append(f"  - my answer: {q.get('answer_full') or q.get('answer_summary')}")
            if q.get("ideal_answer"):
                lines.append(f"  - ideal: {q['ideal_answer']}")
            if isinstance(q.get("score"), (int, float)) and q.get("topic"):
                by_topic[q["topic"]].append(q["score"])
    lines.append("\n## Topic averages\n")
    for topic, scores in sorted(by_topic.items(), key=lambda kv: sum(kv[1]) / len(kv[1])):
        lines.append(f"- {topic}: avg {round(sum(scores)/len(scores),2)} over {len(scores)} question(s)")
    out.write_text("\n".join(lines))
    print(f"exported {len(sessions)} session(s) -> {out}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list"); p.add_argument("--role"); p.set_defaults(fn=cmd_list)
    p = sub.add_parser("show"); p.add_argument("session"); p.set_defaults(fn=cmd_show)
    p = sub.add_parser("topic"); p.add_argument("topic"); p.add_argument("--role")
    p.set_defaults(fn=cmd_topic)
    p = sub.add_parser("retake"); p.add_argument("--role")
    p.add_argument("--max-score", type=float, default=3)
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--all", action="store_true", help="all questions, not one per topic")
    p.set_defaults(fn=cmd_retake)
    p = sub.add_parser("export"); p.add_argument("--out"); p.set_defaults(fn=cmd_export)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
