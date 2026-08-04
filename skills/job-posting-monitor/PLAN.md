# PLAN — job-posting-monitor (OpenClaw skill)

## Goal

An OpenClaw skill that monitors ~20 career sites of hedge funds, prop shops, and
big banks, matches openings against my background for four target roles —
**portfolio manager, prop trader, quantitative researcher, sell-side trader** —
and sends **daily** and **weekly** digests to my **Telegram** through the
OpenClaw agent. The weekly digest also identifies **skill gaps**: what I should
acquire or surface on my resume to be competitive for the roles that keep
appearing.

## Brainstorm summary / design decisions

### 1. Hybrid fetching: scripts for ATS APIs, agent for custom sites

Most firms sit on one of a few applicant-tracking systems with public JSON APIs:

| ATS        | Endpoint pattern                                              | Auth |
|------------|---------------------------------------------------------------|------|
| Greenhouse | `GET boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true` | none |
| Lever      | `GET api.lever.co/v0/postings/{token}?mode=json`              | none |
| Workday    | `POST {host}/wday/cxs/{tenant}/{site}/jobs` (JSON body)       | none |

Those are handled by a deterministic Python script (stdlib only, no pip
dependencies) — cheap, fast, reproducible. Three more scripted adapters extend
coverage to custom sites: `eightfold` (Millennium, Morgan Stanley), `json_api`
(any JSON endpoint, fully described in config — url/body templates plus a
dot-path field map, so fixing a source is a config edit, not code), and
`html_links` (server-rendered listing pages). Sites that defeat all of these
(JS-rendered, e.g. Citadel/Goldman until their XHR endpoints are captured) are
flagged per-run as `empty_sources`/`agent_required`, and the OpenClaw agent
fetches those pages itself, writing normalized jobs into
`data/agent_jobs.json`, which the pipeline merges. Principle: **scripts do everything mechanical; the LLM only
does what scripts can't** (rendering JS-heavy pages, reading unstructured HTML,
judgment calls).

ATS tokens in `config/companies.json` are best-guess and marked
`"verified": false` — firms change ATS vendors. First-time setup runs
`fetch_jobs.py --verify`, and the agent web-searches to fix any failing entry,
then flips `verified` to true. The pipeline degrades gracefully: a failing
company is reported in the digest footer, never crashes the run.

### 2. Deterministic matching; LLM only for gap analysis

Role matching is regex/keyword scoring in Python, configured in
`config/profile.json` (title patterns per role, exclusion patterns like
intern/campus/engineer, location preferences, asset-class keyword bonuses).
Reproducible and tunable without touching code. The **gap analysis** is the
opposite: it needs real reading comprehension, so it is an agent task defined
by a prompt playbook (`references/GAP_ANALYSIS.md`) run weekly over the top
matched postings.

### 3. State store for dedup and lifecycle

`data/state/seen_jobs.json` records every matched job with first/last-seen
dates. Daily digest = **new** matches only. Weekly digest = all **active**
matches grouped by role, plus skill-frequency trends, plus the gap analysis.
Jobs unseen for 21 days are pruned (posting closed). This also enables
"posting velocity" signals over time (which firms are hiring which roles).

### 4. Telegram-first delivery

Digests are compact markdown files written to `data/digests/`. The agent sends
them to Telegram via its normal message tool, splitting at the `---8<---`
chunk markers the digest script emits (each chunk < 3,500 chars, safely under
Telegram's 4,096 limit). Daily runs with zero new matches send nothing by
default (`notify_when_empty: false` in profile) to avoid noise.

### 5. Scheduling

Two OpenClaw cron jobs, created during setup:
- **Daily** (weekday mornings): fetch → agent-fetch → match → daily digest → Telegram.
- **Weekly** (Sunday evening): same, then weekly digest + gap analysis → Telegram.

## The 20 targets

Hedge funds (8): Citadel, Millennium, Point72, Balyasny, ExodusPoint,
Squarepoint, D. E. Shaw, Two Sigma.
Prop shops (8): Citadel Securities, Jane Street, Jump Trading, Hudson River
Trading, Optiver, IMC, SIG, DRW.
Banks (4): Goldman Sachs, J.P. Morgan, Morgan Stanley, UBS.

All editable in `config/companies.json`; adding a firm is one JSON entry.

## Architecture / data flow

```
config/companies.json ─┐
config/profile.json ───┤
                       ▼
scripts/fetch_jobs.py ──► data/raw_jobs.json      (ATS APIs, stdlib urllib)
agent fetches "agent"-adapter sites ──► data/agent_jobs.json
                       ▼
scripts/match_jobs.py ──► data/matched_jobs.json  (score = role title match
                                                   + keyword/location bonuses)
                       ▼
scripts/digest.py --mode daily|weekly
      ├── updates data/state/seen_jobs.json (dedup, prune)
      └── writes data/digests/{daily,weekly}-YYYY-MM-DD.md (chunked)
                       ▼
agent: send chunks to Telegram; weekly: run GAP_ANALYSIS.md playbook first
```

## File layout

```
skills/job-posting-monitor/
├── SKILL.md                  # OpenClaw skill entry: workflows, cron, Telegram rules
├── PLAN.md                   # this file
├── config/
│   ├── companies.json        # 20 firms: adapter, endpoint params, verified flag
│   └── profile.json          # background, target roles, patterns, locations, skills
├── scripts/
│   ├── fetch_jobs.py         # ATS adapters (greenhouse/lever/workday) + --verify
│   ├── match_jobs.py         # scoring engine
│   └── digest.py             # state, dedup, daily/weekly markdown, chunking
├── references/
│   ├── SETUP.md              # first-run: profile interview, verify adapters, cron
│   └── GAP_ANALYSIS.md       # prompt playbook for weekly skill-gap report
└── data/                     # runtime only (gitignored): raw/matched/state/digests
```

## Phases

1. **v1 (this commit):** full pipeline + 20-company config + SKILL.md workflows
   + setup & gap-analysis playbooks. Pipeline validated end-to-end on fixture
   data (this dev sandbox has no open outbound network).
2. **First run on OpenClaw:** verify/fix ATS endpoints, fill profile via a
   short interview, create the two cron jobs, send a test digest.
3. **Later ideas (not built yet):** posting-velocity trends per firm; LinkedIn/
   eFinancialCareers as supplementary sources; compensation extraction where
   posted (NYC pay-transparency law); interview-prep pack per matched role;
   auto-tailored resume bullet suggestions per specific posting.

## Open questions (defaults chosen, easy to change)

- **Locations:** defaulted to NYC / Greenwich / Chicago / London + remote;
  edit `profile.json`.
- **Seniority floor:** internships/campus/graduate programs are excluded by
  default; experienced-hire only.
- **Quiet days:** no Telegram message when a daily run finds nothing new
  (flip `notify_when_empty`).
