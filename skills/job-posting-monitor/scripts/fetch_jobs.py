#!/usr/bin/env python3
"""Fetch job postings from ATS APIs (Greenhouse / Lever / Workday).

Stdlib only. Companies with adapter "agent" are not fetched here — they are
listed in the output under "agent_required" so the OpenClaw agent can fetch
them itself and write normalized jobs to data/agent_jobs.json.

Usage:
  python3 fetch_jobs.py                      # fetch all API-backed companies
  python3 fetch_jobs.py --company "Point72"  # one company only
  python3 fetch_jobs.py --verify             # probe endpoints, report status, fetch nothing else

Output: data/raw_jobs.json
  { "fetched_at": ..., "jobs": [...], "failures": [...], "agent_required": [...] }

Normalized job schema (also expected from the agent in agent_jobs.json):
  { "id": str, "company": str, "category": str, "title": str, "location": str,
    "url": str, "posted_at": str|null, "description": str, "source": str }
"""

import argparse
import hashlib
import html
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = SKILL_DIR / "data"
UA = "Mozilla/5.0 (job-posting-monitor personal skill; contact: owner)"
DESC_LIMIT = 5000


def http_json(url, payload=None, timeout=30):
    data = None
    headers = {"User-Agent": UA, "Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def strip_html(text):
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()[:DESC_LIMIT]


def job_id(company, key):
    return hashlib.sha1(f"{company}|{key}".encode()).hexdigest()[:16]


def fetch_greenhouse(company):
    token = company["params"]["board_token"]
    url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
    data = http_json(url)
    jobs = []
    for j in data.get("jobs", []):
        jobs.append({
            "id": job_id(company["name"], str(j.get("id"))),
            "company": company["name"],
            "category": company.get("category", ""),
            "title": j.get("title", ""),
            "location": (j.get("location") or {}).get("name", ""),
            "url": j.get("absolute_url", ""),
            "posted_at": j.get("updated_at"),
            "description": strip_html(j.get("content", "")),
            "source": "greenhouse",
        })
    return jobs


def fetch_lever(company):
    token = company["params"]["site_token"]
    url = f"https://api.lever.co/v0/postings/{token}?mode=json"
    data = http_json(url)
    jobs = []
    for j in data:
        cats = j.get("categories") or {}
        jobs.append({
            "id": job_id(company["name"], j.get("id", j.get("hostedUrl", ""))),
            "company": company["name"],
            "category": company.get("category", ""),
            "title": j.get("text", ""),
            "location": cats.get("location", ""),
            "url": j.get("hostedUrl", ""),
            "posted_at": None,
            "description": strip_html(j.get("descriptionPlain") or j.get("description", "")),
            "source": "lever",
        })
    return jobs


def fetch_workday(company):
    p = company["params"]
    host, tenant, site = p["host"], p["tenant"], p["site"]
    base = f"https://{host}/wday/cxs/{tenant}/{site}"
    terms = p.get("search_terms") or ["trader", "portfolio manager", "quantitative research"]
    seen, jobs = set(), []
    for term in terms:
        offset = 0
        while offset < p.get("max_results", 100):
            body = {"appliedFacets": {}, "limit": 20, "offset": offset, "searchText": term}
            data = http_json(f"{base}/jobs", payload=body)
            postings = data.get("jobPostings", [])
            if not postings:
                break
            for j in postings:
                path = j.get("externalPath", "")
                if not path or path in seen:
                    continue
                seen.add(path)
                jobs.append({
                    "id": job_id(company["name"], path),
                    "company": company["name"],
                    "category": company.get("category", ""),
                    "title": j.get("title", ""),
                    "location": j.get("locationsText", ""),
                    "url": f"https://{host}/en-US/{site}{path}",
                    "posted_at": j.get("postedOn"),
                    "description": strip_html(j.get("bulletFields") and " ".join(map(str, j["bulletFields"])) or ""),
                    "source": "workday",
                })
            offset += 20
    return jobs


ADAPTERS = {"greenhouse": fetch_greenhouse, "lever": fetch_lever, "workday": fetch_workday}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(SKILL_DIR / "config" / "companies.json"))
    ap.add_argument("--out", default=str(DATA_DIR / "raw_jobs.json"))
    ap.add_argument("--company", help="fetch only this company (name substring, case-insensitive)")
    ap.add_argument("--verify", action="store_true", help="probe endpoints and print status only")
    args = ap.parse_args()

    companies = json.loads(Path(args.config).read_text())["companies"]
    if args.company:
        needle = args.company.lower()
        companies = [c for c in companies if needle in c["name"].lower()]
        if not companies:
            sys.exit(f"no company matching {args.company!r}")

    all_jobs, failures, agent_required = [], [], []
    for c in companies:
        adapter = c.get("adapter", "agent")
        if adapter == "agent":
            agent_required.append({
                "company": c["name"], "category": c.get("category", ""),
                "careers_url": c.get("careers_url", ""), "notes": c.get("notes", ""),
            })
            if args.verify:
                print(f"AGENT     {c['name']}: fetched by the agent ({c.get('careers_url','')})")
            continue
        fn = ADAPTERS.get(adapter)
        if fn is None:
            failures.append({"company": c["name"], "error": f"unknown adapter {adapter!r}"})
            continue
        try:
            jobs = fn(c)
            if args.verify:
                print(f"OK        {c['name']}: {len(jobs)} postings via {adapter}")
            else:
                all_jobs.extend(jobs)
        except urllib.error.HTTPError as e:
            msg = f"HTTP {e.code} from {adapter} endpoint (token/params likely wrong — see references/SETUP.md)"
            failures.append({"company": c["name"], "error": msg})
            if args.verify:
                print(f"FAIL      {c['name']}: {msg}")
        except Exception as e:  # network, JSON, schema drift — never crash the run
            failures.append({"company": c["name"], "error": f"{type(e).__name__}: {e}"})
            if args.verify:
                print(f"FAIL      {c['name']}: {type(e).__name__}: {e}")

    if args.verify:
        return

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "jobs": all_jobs,
        "failures": failures,
        "agent_required": agent_required,
    }
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(f"wrote {len(all_jobs)} jobs, {len(failures)} failures, "
          f"{len(agent_required)} agent-fetch companies -> {args.out}")


if __name__ == "__main__":
    main()
