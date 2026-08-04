#!/usr/bin/env python3
"""Distill the most testable interview topics from matched job descriptions.

Reads ../../job-posting-monitor/data/matched_jobs.json (override with
--matched). For each target role, ranks topics by how often their trigger
terms appear across that role's JDs, weighted by how testable the topic is in
a live interview (testability weight). Output: data/topics.json with, per
role: ranked topics, demanding firms, and example JD urls — the raw material
for a session plan.

Usage: python3 build_topics.py [--matched PATH] [--top N]
"""

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_MATCHED = SKILL_DIR.parent / "job-posting-monitor" / "data" / "matched_jobs.json"

# topic -> (testability weight 1-3, trigger terms found in JD text)
# 3 = classic live-grill material, 2 = commonly probed, 1 = discussed.
TOPICS = {
    "mental math & quick estimation":      (3, ["mental math", "quick thinking", "fast-paced", "numerical", "arithmetic"]),
    "probability & expected value":        (3, ["probability", "statistics", "stochastic", "expected value", "games"]),
    "options pricing & greeks":            (3, ["option", "greeks", "black-scholes", "derivatives", "convexity"]),
    "volatility & vol surface":            (3, ["volatility", "vol surface", "skew", "vega", "variance"]),
    "market making & adverse selection":   (3, ["market making", "market maker", "bid-ask", "liquidity provision", "adverse selection"]),
    "brainteasers & game theory":          (3, ["puzzle", "brainteaser", "game theory", "poker", "strategic"]),
    "market microstructure & execution":   (2, ["microstructure", "execution", "order book", "order flow", "slippage", "transaction cost"]),
    "portfolio construction & optimization": (2, ["portfolio construction", "portfolio optimization", "sizing", "kelly", "allocation", "diversification"]),
    "risk management & drawdowns":         (2, ["risk management", "drawdown", "var", "stress", "hedging", "risk limits"]),
    "alpha research & signals":            (2, ["alpha", "signal", "research process", "backtesting", "factor"]),
    "statistics & time series":            (2, ["time series", "regression", "stationarity", "forecasting", "econometric"]),
    "machine learning":                    (2, ["machine learning", "deep learning", "feature", "overfitting", "model"]),
    "coding (python/c++)":                 (2, ["python", "c++", "programming", "coding", "software"]),
    "macro & rates knowledge":             (2, ["macro", "rates", "fed", "curve", "inflation", "fixed income"]),
    "equities & single-name knowledge":    (2, ["equities", "equity", "earnings", "single stock", "sector"]),
    "fx & commodities":                    (1, ["fx", "foreign exchange", "commodities", "energy", "metals"]),
    "market awareness & current events":   (3, ["markets", "market views", "current events", "trade idea", "trading ideas"]),
    "track record & pnl attribution":      (2, ["track record", "pnl", "p&l", "sharpe", "attribution", "performance"]),
    "client & franchise skills":           (1, ["client", "sales", "relationship", "coverage", "franchise"]),
    "behavioral & fit":                    (2, ["team", "collaborat", "communicat", "entrepreneurial", "ownership", "culture"]),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--matched", default=str(DEFAULT_MATCHED))
    ap.add_argument("--top", type=int, default=12, help="topics kept per role")
    ap.add_argument("--out", default=str(SKILL_DIR / "data" / "topics.json"))
    args = ap.parse_args()

    matched_path = Path(args.matched)
    if not matched_path.exists():
        raise SystemExit(f"{matched_path} not found — run the job-posting-monitor "
                         f"fetch+match pipeline first.")
    data = json.loads(matched_path.read_text())
    jobs = data.get("jobs", [])
    if not jobs:
        raise SystemExit("matched_jobs.json contains no jobs — nothing to build topics from.")

    by_role = defaultdict(list)
    for j in jobs:
        by_role[j.get("matched_role", "unknown")].append(j)

    out_roles = {}
    for role, role_jobs in by_role.items():
        scores = []
        for topic, (weight, terms) in TOPICS.items():
            hits, firms, examples = 0, set(), []
            for j in role_jobs:
                text = (j.get("title", "") + " " + (j.get("description") or "")).lower()
                if any(t in text for t in terms):
                    hits += 1
                    firms.add(j["company"])
                    if len(examples) < 3 and j.get("url"):
                        examples.append(j["url"])
            if hits:
                scores.append({
                    "topic": topic,
                    "score": hits * weight,
                    "jd_hits": hits,
                    "testability": weight,
                    "firms": sorted(firms),
                    "example_jds": examples,
                })
        scores.sort(key=lambda t: -t["score"])
        out_roles[role] = {
            "jobs_analyzed": len(role_jobs),
            "topics": scores[:args.top],
        }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "built_at": datetime.now(timezone.utc).isoformat(),
        "source": str(matched_path),
        "roles": out_roles,
    }, indent=2))
    print(f"built topics for {len(out_roles)} role(s) from {len(jobs)} JDs -> {out_path}")
    for role, info in out_roles.items():
        top3 = ", ".join(t["topic"] for t in info["topics"][:3]) or "(none)"
        print(f"  {role}: top topics — {top3}")


if __name__ == "__main__":
    main()
