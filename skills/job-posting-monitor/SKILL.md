---
name: job-posting-monitor
description: Monitor ~20 hedge fund, prop shop, and bank career sites for portfolio manager, prop trader, quantitative researcher, and sell-side trader roles. Sends daily and weekly digests to Telegram and produces a weekly skill-gap / resume analysis. Use when the user asks about job monitoring, new postings, matched roles, digests, or skill gaps — or when a cron job fires for the daily/weekly run.
metadata: {"openclaw": {"emoji": "📈"}}
---

# Job Posting Monitor

Pipeline: `fetch_jobs.py` (ATS APIs) + agent fetching (custom sites) →
`match_jobs.py` (scoring vs `config/profile.json`) → `digest.py` (dedup/state,
markdown digest) → **Telegram message via your normal messaging channel**.

All paths below are relative to this skill's directory. Scripts are Python 3
stdlib-only. Runtime files live in `data/` (never commit them).

## First-time setup

If `config/profile.json` still contains `TODO` markers, run the setup flow in
`references/SETUP.md` first: interview the user to fill the profile, run
`python3 scripts/fetch_jobs.py --verify` and repair unverified ATS entries,
then create the two cron jobs (daily weekday morning run, Sunday evening
weekly run) pointing at this skill.

## Daily run (cron or "run my job digest")

1. `python3 scripts/fetch_jobs.py`
2. Read `data/raw_jobs.json` → `agent_required` lists companies whose career
   sites you must fetch yourself (URL + notes provided). For each, fetch the
   page (and per-role search pages where the notes suggest), extract open
   roles relevant to trading/PM/quant research, and append normalized jobs to
   `data/agent_jobs.json` as `{"jobs": [...]}` using the schema documented at
   the top of `scripts/fetch_jobs.py`. Set `id` to a stable value (the
   posting's canonical URL is fine). Skip a site gracefully if it is down —
   note it, don't stall the run. Time-box this: prioritize sites, don't
   exhaustively crawl.
3. `python3 scripts/match_jobs.py`
4. `python3 scripts/digest.py --mode daily`
5. The script prints JSON with `digest_path` and `should_notify`.
   - If `should_notify` is false: do nothing (quiet day — the user opted out
     of empty notifications). End the run silently.
   - Otherwise read the digest file and send it to the user on **Telegram**.
     The file contains `---8<---` markers — send each chunk as a separate
     message, in order. Keep the markdown links intact.

## Weekly run (cron, Sunday evening)

Steps 1–3 as above, then:

4. `python3 scripts/digest.py --mode weekly`
5. Send the weekly digest chunks to Telegram (same chunk rule).
6. **Gap analysis**: follow `references/GAP_ANALYSIS.md`. Read the top
   `digest.gap_analysis_top_n` jobs from `data/matched_jobs.json` (fetch full
   descriptions for any job whose `description` is empty), compare
   requirements against `background` in `config/profile.json`, and send the
   resulting report to Telegram after the digest. Save a copy to
   `data/digests/gap-analysis-YYYY-MM-DD.md`.

## Rules

- **Read-only monitoring.** Never apply to jobs, create accounts, contact
  recruiters, or submit any form on the user's behalf.
- Respect the sites: modest request rates, no crawling beyond job listings.
- If an ATS adapter starts failing (see `failures` in the digest footer),
  attempt to fix `config/companies.json` per `references/SETUP.md` (web-search
  the firm's current ATS) and tell the user what changed.
- Never invent postings. Every digest item must carry a real URL you fetched.
- Adding/removing firms = editing `config/companies.json`; changing match
  behavior = editing `config/profile.json`. Prefer config edits over code
  edits.
