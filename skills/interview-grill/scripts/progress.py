#!/usr/bin/env python3
"""Aggregate past mock-interview sessions into a weakness report.

Reads data/sessions/*.json (schema in references/INTERVIEW_FLOW.md), computes
per-topic average scores and trends, and prints a JSON report the agent uses
to plan the next session (and the user can read directly).

Usage: python3 progress.py [--min-sessions 1]
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SESSIONS_DIR = SKILL_DIR / "data" / "sessions"
WEAK_THRESHOLD = 3.0  # avg score below this (out of 5) = weak topic


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-sessions", type=int, default=1)
    args = ap.parse_args()

    sessions = []
    if SESSIONS_DIR.exists():
        for p in sorted(SESSIONS_DIR.glob("*.json")):
            try:
                s = json.loads(p.read_text())
                s["_file"] = p.name
                sessions.append(s)
            except (json.JSONDecodeError, OSError):
                continue

    if len(sessions) < args.min_sessions:
        print(json.dumps({"sessions": len(sessions), "weak_topics": [],
                          "note": "no session history yet — plan from topics.json only"}))
        return

    topic_scores = defaultdict(list)   # topic -> [(session_date, score), ...]
    for s in sessions:
        date = s.get("date", s["_file"][:10])
        for q in s.get("questions", []):
            if isinstance(q.get("score"), (int, float)) and q.get("topic"):
                topic_scores[q["topic"]].append((date, q["score"]))

    report = []
    for topic, entries in topic_scores.items():
        entries.sort()
        scores = [sc for _, sc in entries]
        half = max(1, len(scores) // 2)
        early, late = scores[:half], scores[len(scores) - half:]
        report.append({
            "topic": topic,
            "asked": len(scores),
            "avg_score": round(sum(scores) / len(scores), 2),
            "recent_avg": round(sum(late) / len(late), 2),
            "trend": round(sum(late) / len(late) - sum(early) / len(early), 2),
            "last_asked": entries[-1][0],
        })
    report.sort(key=lambda t: (t["recent_avg"], -t["asked"]))

    comm = [(s.get("date", s["_file"][:10]), s["communication_score"])
            for s in sessions
            if isinstance(s.get("communication_score"), (int, float))]
    communication = None
    if comm:
        scores = [c for _, c in sorted(comm)]
        communication = {
            "sessions_scored": len(scores),
            "avg": round(sum(scores) / len(scores), 2),
            "latest": scores[-1],
            "history": scores[-8:],
        }

    lang_counts = defaultdict(lambda: {"count": 0, "correct": "", "type": ""})
    for s in sessions:
        for err in s.get("language_errors", []):
            key = (err.get("said") or "").strip().lower()
            if not key:
                continue
            lang_counts[key]["count"] += 1
            lang_counts[key]["correct"] = err.get("correct", "")
            lang_counts[key]["type"] = err.get("type", "")
    recurring = sorted(
        ({"said": k, **v} for k, v in lang_counts.items() if v["count"] >= 2),
        key=lambda e: -e["count"])

    print(json.dumps({
        "sessions": len(sessions),
        "last_session": sessions[-1].get("date", sessions[-1]["_file"][:10]),
        "weak_topics": [t for t in report if t["recent_avg"] < WEAK_THRESHOLD],
        "communication": communication,
        "recurring_language_errors": recurring,
        "all_topics": report,
    }, indent=2))


if __name__ == "__main__":
    main()
