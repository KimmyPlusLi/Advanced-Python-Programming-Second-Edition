#!/usr/bin/env python3
"""Fetch job postings from every configured career site. Stdlib only.

Adapters:
  greenhouse — GET boards-api.greenhouse.io/v1/boards/{board_token}/jobs
  lever      — GET api.lever.co/v0/postings/{site_token}
  workday    — POST {host}/wday/cxs/{tenant}/{site}/jobs, paged per search term
  eightfold  — GET {host}/api/apply/v2/jobs?domain=&query=&start=, paged
  json_api   — any JSON endpoint, fully configured by params (url/body
               templates with {term}/{offset}, dot-path field mapping)
  html_links — plain-HTML fallback: extract <a> links whose text looks like a
               relevant role. Crude but dependency-free; JS-rendered sites
               yield nothing and are flagged in "empty_sources".
  agent      — last resort only: listed under "agent_required" for the
               OpenClaw agent to fetch manually into data/agent_jobs.json.

Sources that error land in "failures"; sources that return zero jobs land in
"empty_sources" — both are surfaced in the digest so they get fixed.

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
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = SKILL_DIR / "data"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/126.0 Safari/537.36 job-posting-monitor/1.0 (personal job search)")
DESC_LIMIT = 5000
DEFAULT_TERMS = ["trader", "portfolio manager", "quantitative research"]


def http_get(url, payload=None, timeout=30, accept="application/json"):
    data = None
    headers = {"User-Agent": UA, "Accept": accept, "Accept-Language": "en"}
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def http_json(url, payload=None, timeout=30):
    return json.loads(http_get(url, payload, timeout))


def dig(obj, dotted, default=None):
    """dig({'a':{'b':[{'c':1}]}}, 'a.b.0.c') -> 1"""
    cur = obj
    for part in dotted.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
        else:
            return default
        if cur is None:
            return default
    return cur


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


def fetch_eightfold(company):
    p = company["params"]
    host = p["host"]
    domain = p.get("domain", "")
    seen, jobs = set(), []
    for term in p.get("search_terms") or DEFAULT_TERMS:
        start = 0
        while start < p.get("max_results", 100):
            q = urllib.parse.urlencode(
                {"domain": domain, "query": term, "num": 20, "start": start})
            data = http_json(f"https://{host}/api/apply/v2/jobs?{q}")
            positions = data.get("positions", [])
            if not positions:
                break
            for j in positions:
                pid = str(j.get("id", ""))
                if not pid or pid in seen:
                    continue
                seen.add(pid)
                locs = j.get("locations") or ([j["location"]] if j.get("location") else [])
                jobs.append({
                    "id": job_id(company["name"], pid),
                    "company": company["name"],
                    "category": company.get("category", ""),
                    "title": j.get("name", ""),
                    "location": "; ".join(map(str, locs)),
                    "url": j.get("canonicalPositionUrl")
                           or f"https://{host}/careers?pid={pid}",
                    "posted_at": None,
                    "description": strip_html(j.get("job_description", "")),
                    "source": "eightfold",
                })
            start += 20
    return jobs


def fetch_json_api(company):
    """Generic configurable JSON adapter, so a newly discovered endpoint is a
    config edit, not a code change.

    params:
      url            — template; may contain {term} and {offset}
      method         — GET (default) or POST
      body           — POST body template (dict); string values may contain
                       {term}/{offset} placeholders
      jobs_path      — dot path to the postings array in the response
      map            — {"title": "...", "url": "...", "location": "...",
                        "id": "...", "description": "...", "posted_at": "..."}
                       dot paths within each posting object
      url_prefix     — prepended to relative mapped urls
      search_terms   — optional; loop {term} over these
      page_size / max_results — optional {offset} paging
    """
    p = company["params"]
    mapping = p["map"]
    seen, jobs = set(), []

    def render(template, term, offset):
        if isinstance(template, str):
            return template.replace("{term}", term).replace("{offset}", str(offset))
        if isinstance(template, dict):
            return {k: render(v, term, offset) for k, v in template.items()}
        return template

    terms = p.get("search_terms") or [""]
    for term in terms:
        offset, page = 0, p.get("page_size", 0)
        while True:
            url = render(p["url"], urllib.parse.quote(term), offset)
            body = render(p.get("body"), term, offset) if p.get("body") else None
            data = http_json(url, payload=body if p.get("method", "GET") == "POST" else None)
            postings = dig(data, p["jobs_path"], []) or []
            if not isinstance(postings, list) or not postings:
                break
            for j in postings:
                url_val = str(dig(j, mapping.get("url", "url"), "") or "")
                if url_val and not url_val.startswith("http"):
                    url_val = p.get("url_prefix", "") + url_val
                key = str(dig(j, mapping.get("id", "id"), "") or url_val)
                if not key or key in seen:
                    continue
                seen.add(key)
                jobs.append({
                    "id": job_id(company["name"], key),
                    "company": company["name"],
                    "category": company.get("category", ""),
                    "title": str(dig(j, mapping.get("title", "title"), "") or ""),
                    "location": str(dig(j, mapping.get("location", ""), "") or ""),
                    "url": url_val,
                    "posted_at": dig(j, mapping.get("posted_at", ""), None),
                    "description": strip_html(str(dig(j, mapping.get("description", ""), "") or "")),
                    "source": "json_api",
                })
            offset += page
            if not page or offset >= p.get("max_results", 100):
                break
    return jobs


LINK_RX = re.compile(r"<a\b[^>]*?href=[\"']([^\"'#]+)[\"'][^>]*>(.*?)</a>",
                     re.IGNORECASE | re.DOTALL)
DEFAULT_LINK_PATTERNS = [
    r"trader", r"trading", r"portfolio\s*manager", r"\bpm\b",
    r"quant", r"research(er)?\b", r"market\s*mak", r"strategist",
]


def fetch_html_links(company):
    """Plain-HTML fallback: harvest role-looking links from listing pages.

    Works on server-rendered career pages; JS-rendered pages return zero jobs
    and get flagged as an empty source. No description/location — the matcher
    scores on title alone, and digest links go to the posting page.
    """
    p = company.get("params", {})
    pages = p.get("pages") or [company["careers_url"]]
    patterns = [re.compile(rx, re.IGNORECASE)
                for rx in p.get("include_link_patterns", DEFAULT_LINK_PATTERNS)]
    seen, jobs = set(), []
    for page in pages:
        html_text = http_get(page, accept="text/html,application/xhtml+xml")
        for href, inner in LINK_RX.findall(html_text):
            title = strip_html(inner)
            if not title or len(title) > 120:
                continue
            if not any(rx.search(title) for rx in patterns):
                continue
            url = urllib.parse.urljoin(page, html.unescape(href))
            if url in seen:
                continue
            seen.add(url)
            jobs.append({
                "id": job_id(company["name"], url),
                "company": company["name"],
                "category": company.get("category", ""),
                "title": title,
                "location": "",
                "url": url,
                "posted_at": None,
                "description": "",
                "source": "html_links",
            })
    return jobs


ADAPTERS = {
    "greenhouse": fetch_greenhouse,
    "lever": fetch_lever,
    "workday": fetch_workday,
    "eightfold": fetch_eightfold,
    "json_api": fetch_json_api,
    "html_links": fetch_html_links,
}


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

    all_jobs, failures, empty_sources, agent_required = [], [], [], []
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
            if not jobs:
                empty_sources.append({
                    "company": c["name"], "adapter": adapter,
                    "careers_url": c.get("careers_url", ""), "notes": c.get("notes", ""),
                })
            if args.verify:
                mark = "OK   " if jobs else "EMPTY"
                print(f"{mark}     {c['name']}: {len(jobs)} postings via {adapter}")
            else:
                all_jobs.extend(jobs)
        except urllib.error.HTTPError as e:
            msg = f"HTTP {e.code} from {adapter} endpoint (params likely wrong — see references/SETUP.md)"
            failures.append({"company": c["name"], "error": msg,
                             "careers_url": c.get("careers_url", "")})
            if args.verify:
                print(f"FAIL      {c['name']}: {msg}")
        except Exception as e:  # network, JSON, schema drift — never crash the run
            failures.append({"company": c["name"], "error": f"{type(e).__name__}: {e}",
                             "careers_url": c.get("careers_url", "")})
            if args.verify:
                print(f"FAIL      {c['name']}: {type(e).__name__}: {e}")

    if args.verify:
        return

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "jobs": all_jobs,
        "failures": failures,
        "empty_sources": empty_sources,
        "agent_required": agent_required,
    }
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(f"wrote {len(all_jobs)} jobs, {len(failures)} failures, "
          f"{len(empty_sources)} empty sources, "
          f"{len(agent_required)} agent-fetch companies -> {args.out}")


if __name__ == "__main__":
    main()
