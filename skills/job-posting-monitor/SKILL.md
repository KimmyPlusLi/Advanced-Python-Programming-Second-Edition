---
name: job-posting-monitor
description: Monitor a configurable list of company career sites (ships with ~20 hedge funds, prop shops, and banks) for roles matching the user's profile (default roles - portfolio manager, prop trader, quantitative researcher, sell-side trader). Sends daily and weekly digests to the user's chat channel and produces a weekly skill-gap / resume analysis. Use when the user asks about job monitoring, new postings, matched roles, digests, or skill gaps - or when a cron job fires for the daily/weekly run.
metadata: {"openclaw": {"emoji": "📈"}, "version": "1.0.0", "license": "MIT"}
---

# Job Posting Monitor

Pipeline: `fetch_jobs.py` (ATS APIs) + agent fetching (custom sites) →
`match_jobs.py` (scoring vs `config/profile.json`) → `digest.py` (dedup/state,
markdown digest) → message on the channel named in `profile.json` →
`digest.channel` (falling back to wherever the user normally messages you).
Everything personal — firms, roles, keywords, locations, delivery — lives in
`config/`; see Customization below.

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
2. Read `data/raw_jobs.json`. Two lists may need your help:
   - `agent_required`: companies configured for manual agent fetching.
   - `empty_sources`: scripted adapters that returned zero postings (usually
     a JS-rendered page defeating the `html_links` fallback).
   For each, fetch the careers URL yourself, extract open roles relevant to
   trading/PM/quant research, and append normalized jobs to
   `data/agent_jobs.json` as `{"jobs": [...]}` using the schema documented at
   the top of `scripts/fetch_jobs.py`. Set `id` to a stable value (the
   posting's canonical URL is fine). While you're there, note the site's
   underlying jobs XHR if you can spot one and record it in that company's
   `notes` in `config/companies.json` — converting the entry to `json_api`/
   `eightfold` makes future runs script-only. Skip a site gracefully if it is
   down — note it, don't stall the run. Time-box this: prioritize sites,
   don't exhaustively crawl.
3. `python3 scripts/match_jobs.py`
4. `python3 scripts/digest.py --mode daily`
5. The script prints JSON with `digest_path` and `should_notify`.
   - If `should_notify` is false: do nothing (quiet day — the user opted out
     of empty notifications). End the run silently.
   - Otherwise read the digest file and send it to the user on the configured
     channel (`digest.channel`). The file contains `---8<---` markers —
     send each chunk as a separate message, in order (chunks are sized for
     Telegram's 4,096-char limit, safe on other chat channels too). Keep the markdown links intact.

## Weekly run (cron, Sunday evening)

Steps 1–3 as above, then:

4. `python3 scripts/digest.py --mode weekly`
5. Send the weekly digest chunks on the configured channel (same chunk rule).
6. **Gap analysis**: follow `references/GAP_ANALYSIS.md`. Read the top
   `digest.gap_analysis_top_n` jobs from `data/matched_jobs.json` (fetch full
   descriptions for any job whose `description` is empty), compare
   requirements against `background` in `config/profile.json`, and send the
   resulting report on the configured channel after the digest. Save a copy to
   `data/digests/gap-analysis-YYYY-MM-DD.md`.

## JD archive (durable history)

`digest.py` archives every matched posting — full description included — to
`data/jd_archive/<job_id>.json`, forever: closed postings are marked
`status: closed`, never deleted, and description edits keep the prior text
in `previous_descriptions`. Retrieval via `scripts/jd_archive.py`:

- "what did that closed Citadel PM role require?" → `show citadel`
- "which postings ask for kdb?" → `search kdb`
- "is python demand growing?" → `trend python` (share of postings by month)
- `list --status closed`, `export` for the full archive as markdown.

Use the archive whenever the user asks about a posting no longer live, and
for requirement trends in the weekly gap analysis. interview-grill also reads
it when current matches are empty.

## Customization

Everything is config, no code edits needed. When the user asks to change
behavior, edit the matching knob and confirm what changed:

- **Firms** — add/remove entries in `config/companies.json`. Any employer
  works, not just finance: one entry = name, adapter, params (see the
  adapter docs in `scripts/fetch_jobs.py` and `references/SETUP.md`).
- **Target roles** — `profile.json` → `target_roles`: any set of roles, each
  with title regexes and a weight. The defaults (PM / prop trader / quant
  researcher / sell-side trader) are just a starting point; replace them
  wholesale for a different field.
- **Matching strictness** — `min_score` (raise = fewer, better matches),
  `exclude_title_patterns`, `keyword_bonuses` (align with the user's
  background), `locations`.
- **Delivery** — `digest.channel` (any channel the deployment can message),
  `notify_when_empty`, item caps, `gap_analysis_top_n`; cron times are set
  in the user's scheduler, not here.
- **Skill-gap lexicon** — `skill_lexicon` drives the weekly demand table;
  extend it with domain terms relevant to the user's field.

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
