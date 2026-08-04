#!/usr/bin/env python3
"""Score fetched jobs against config/profile.json.

Inputs:  data/raw_jobs.json (from fetch_jobs.py)
         data/agent_jobs.json (optional, written by the OpenClaw agent for
         custom career sites; either a list of normalized jobs or
         {"jobs": [...]})
Output:  data/matched_jobs.json — jobs with score >= profile.min_score,
         sorted by score, annotated with matched_role and score breakdown.

Scoring:
  - Title must match one target-role pattern (highest-weight wins) and no
    exclusion pattern, else score 0.
  - + keyword bonuses for description hits.
  - + location bonus if location matches include_patterns; excluded locations
    drop the job. Unknown/empty location kept if unknown_location_ok.
"""

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = SKILL_DIR / "data"


def compile_all(patterns):
    return [re.compile(p, re.IGNORECASE) for p in patterns]


def load_jobs(path):
    p = Path(path)
    if not p.exists():
        return []
    data = json.loads(p.read_text())
    jobs = data.get("jobs", data) if isinstance(data, dict) else data
    return jobs if isinstance(jobs, list) else []


def score_job(job, profile, compiled):
    title = job.get("title", "")
    if any(rx.search(title) for rx in compiled["exclude"]):
        return None

    # Longest pattern match wins (specificity: "sales trader" beats "trader"),
    # weight breaks ties.
    matched_role, best = None, (0, 0)
    for role, rxs in compiled["roles"]:
        for rx in rxs:
            m = rx.search(title)
            if m and (len(m.group(0)), role["weight"]) > best:
                matched_role, best = role, (len(m.group(0)), role["weight"])
    if matched_role is None:
        return None
    role_weight = matched_role["weight"]

    loc = job.get("location") or ""
    loc_cfg = profile["locations"]
    if loc and any(rx.search(loc) for rx in compiled["loc_exclude"]):
        return None
    loc_bonus = 0
    if loc:
        if any(rx.search(loc) for rx in compiled["loc_include"]):
            loc_bonus = loc_cfg.get("location_bonus", 0)
        elif compiled["loc_include"] and not loc_cfg.get("unknown_location_ok", True):
            # Named location that matches no preference: keep but no bonus.
            pass
    elif not loc_cfg.get("unknown_location_ok", True):
        return None

    text = (title + " " + (job.get("description") or "")).lower()
    kw_points, kw_hits = 0, []
    for kw, pts in profile.get("keyword_bonuses", {}).items():
        if kw.startswith("_"):
            continue
        if kw.lower() in text:
            kw_points += pts
            kw_hits.append(kw)

    return {
        **job,
        "matched_role": matched_role["key"],
        "matched_role_label": matched_role["label"],
        "score": role_weight + kw_points + loc_bonus,
        "score_breakdown": {"role": role_weight, "keywords": kw_points, "location": loc_bonus},
        "keyword_hits": sorted(kw_hits),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default=str(SKILL_DIR / "config" / "profile.json"))
    ap.add_argument("--raw", default=str(DATA_DIR / "raw_jobs.json"))
    ap.add_argument("--agent-jobs", default=str(DATA_DIR / "agent_jobs.json"))
    ap.add_argument("--out", default=str(DATA_DIR / "matched_jobs.json"))
    args = ap.parse_args()

    profile = json.loads(Path(args.profile).read_text())
    compiled = {
        "roles": [(r, compile_all(r["title_patterns"])) for r in profile["target_roles"]],
        "exclude": compile_all(profile.get("exclude_title_patterns", [])),
        "loc_include": compile_all(profile["locations"].get("include_patterns", [])),
        "loc_exclude": compile_all(profile["locations"].get("exclude_patterns", [])),
    }

    raw = load_jobs(args.raw) + load_jobs(args.agent_jobs)
    seen_ids, matched = set(), []
    for job in raw:
        jid = job.get("id") or job.get("url")
        if not jid or jid in seen_ids:
            continue
        seen_ids.add(jid)
        job.setdefault("id", jid)
        scored = score_job(job, profile, compiled)
        if scored and scored["score"] >= profile.get("min_score", 0):
            matched.append(scored)

    matched.sort(key=lambda j: -j["score"])
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    raw_data = {}
    raw_path = Path(args.raw)
    if raw_path.exists():
        raw_data = json.loads(raw_path.read_text())
        if not isinstance(raw_data, dict):
            raw_data = {}
    out = {
        "matched_at": datetime.now(timezone.utc).isoformat(),
        "total_scanned": len(seen_ids),
        "jobs": matched,
        "failures": raw_data.get("failures", []),
        "agent_required": raw_data.get("agent_required", []),
    }
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(f"scanned {len(seen_ids)} unique postings -> {len(matched)} matches "
          f"(min_score={profile.get('min_score', 0)}) -> {args.out}")


if __name__ == "__main__":
    main()
