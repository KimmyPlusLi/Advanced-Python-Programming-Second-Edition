#!/usr/bin/env python3
"""Distill the most testable interview topics into data/topics.json.

Sources, in order of preference:
  1. --jd FILE: any job description saved as a text file (pasted by the
     user) — standalone mode, no job-posting-monitor needed.
  2. Current matched JDs from the job-posting-monitor skill (path set in
     config/settings.json -> topics_source.matched_jobs_path, or --matched):
     topics ranked by JD-demand frequency x live-testability.
  3. job-posting-monitor's durable JD archive (data/jd_archive/ next to the
     matched file) — covers postings that have since closed.
  4. Built-in role priors (ROLE_PRIORS) when nothing else is available.

Usage: python3 build_topics.py [--matched PATH | --jd FILE] [--top N]
"""

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SETTINGS_PATH = SKILL_DIR / "config" / "settings.json"


def default_matched_path():
    rel = "../job-posting-monitor/data/matched_jobs.json"
    if SETTINGS_PATH.exists():
        try:
            cfg = json.loads(SETTINGS_PATH.read_text())
            rel = cfg.get("topics_source", {}).get("matched_jobs_path", rel)
        except json.JSONDecodeError:
            pass
    return (SKILL_DIR / rel).resolve() if not Path(rel).is_absolute() else Path(rel)

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


# Fallback priors when no JDs are available: per-role topic priority order.
# Replace or extend for non-finance fields — topic names must exist in TOPICS.
ROLE_PRIORS = {
    "portfolio_manager": [
        "portfolio construction & optimization", "risk management & drawdowns",
        "track record & pnl attribution", "macro & rates knowledge",
        "market awareness & current events", "alpha research & signals",
        "probability & expected value", "behavioral & fit",
        "statistics & time series", "mental math & quick estimation"],
    "prop_trader": [
        "mental math & quick estimation", "probability & expected value",
        "market making & adverse selection", "options pricing & greeks",
        "brainteasers & game theory", "market awareness & current events",
        "volatility & vol surface", "risk management & drawdowns", "behavioral & fit"],
    "quant_researcher": [
        "probability & expected value", "statistics & time series",
        "machine learning", "alpha research & signals", "coding (python/c++)",
        "brainteasers & game theory", "options pricing & greeks",
        "market microstructure & execution", "behavioral & fit"],
    "sell_side_trader": [
        "market microstructure & execution", "client & franchise skills",
        "market awareness & current events", "options pricing & greeks",
        "macro & rates knowledge", "mental math & quick estimation",
        "risk management & drawdowns", "behavioral & fit"],
}


def score_jobs(role_jobs, top):
    scores = []
    for topic, (weight, terms) in TOPICS.items():
        hits, firms, examples = 0, set(), []
        for j in role_jobs:
            text = (j.get("title", "") + " " + (j.get("description") or "")).lower()
            if any(t in text for t in terms):
                hits += 1
                if j.get("company"):
                    firms.add(j["company"])
                if len(examples) < 3 and j.get("url"):
                    examples.append(j["url"])
        if hits:
            scores.append({
                "topic": topic, "score": hits * weight, "jd_hits": hits,
                "testability": weight, "firms": sorted(firms),
                "example_jds": examples,
            })
    scores.sort(key=lambda t: -t["score"])
    return scores[:top]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--matched", default=str(default_matched_path()))
    ap.add_argument("--jd", help="text file containing one job description (standalone mode)")
    ap.add_argument("--top", type=int, default=12, help="topics kept per role")
    ap.add_argument("--out", default=str(SKILL_DIR / "data" / "topics.json"))
    args = ap.parse_args()

    out_roles = {}
    matched_path = Path(args.matched)
    jobs = []
    source = None
    if args.jd:
        text = Path(args.jd).read_text()
        out_roles["custom_jd"] = {
            "jobs_analyzed": 1,
            "topics": score_jobs([{"title": "", "description": text}], args.top),
        }
        source = f"jd_file:{args.jd}"
    else:
        if matched_path.exists():
            jobs = json.loads(matched_path.read_text()).get("jobs", [])
            source = str(matched_path)
        if not jobs:
            # Fall back to the monitor's durable JD archive (includes closed
            # postings — still real demand signal for interview prep).
            archive_dir = matched_path.parent / "jd_archive"
            for p in sorted(archive_dir.glob("*.json")) if archive_dir.exists() else []:
                try:
                    jobs.append(json.loads(p.read_text()))
                except (json.JSONDecodeError, OSError):
                    continue
            source = str(archive_dir) if jobs else None
    if jobs:
        by_role = defaultdict(list)
        for j in jobs:
            by_role[j.get("matched_role", "unknown")].append(j)
        for role, role_jobs in by_role.items():
            out_roles[role] = {
                "jobs_analyzed": len(role_jobs),
                "topics": score_jobs(role_jobs, args.top),
            }
    if not out_roles:
        # Built-in priors — standalone install or empty pipeline.
        for role, order in ROLE_PRIORS.items():
            out_roles[role] = {
                "jobs_analyzed": 0,
                "topics": [{
                    "topic": t, "score": (len(order) - i) * TOPICS[t][0],
                    "jd_hits": 0, "testability": TOPICS[t][0],
                    "firms": [], "example_jds": [],
                } for i, t in enumerate(order[:args.top])],
            }
        source = "builtin_priors"
        print("note: no matched JDs found — using built-in role priors "
              "(run job-posting-monitor, or pass --jd FILE, for JD-driven topics)")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "built_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "roles": out_roles,
    }, indent=2))
    print(f"built topics for {len(out_roles)} role(s) -> {out_path}")
    for role, info in out_roles.items():
        top3 = ", ".join(t["topic"] for t in info["topics"][:3]) or "(none)"
        print(f"  {role}: top topics — {top3}")


if __name__ == "__main__":
    main()
