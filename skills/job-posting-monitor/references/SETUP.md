# First-time setup

Run this flow once (or whenever the user says matching is off / sources broke).

## 1. Fill the profile

`config/profile.json` ships with `TODO` markers. Interview the user briefly
(Telegram, a few questions max per message):

- Career summary: years, seat (sell-side/buy-side), firms, asset classes.
- Current skills (languages, modeling, market skills) and credentials
  (CFA, FINRA series, degrees).
- Track-record highlights they're willing to state (Sharpe, PnL, AUM).
- Preferred locations, and whether remote is acceptable.
- Any firms to add/remove from `config/companies.json`.

Then update `background`, `locations`, and tune `keyword_bonuses` toward
their asset classes (e.g. a rates trader → bump "rates", "fixed income",
"futures"). Leave `min_score` at 60 initially; recalibrate after the first
digest (too noisy → raise; too quiet → lower or add title patterns).

## 2. Verify the data sources

```
python3 scripts/fetch_jobs.py --verify
```

For each `FAIL`:

1. Web-search "<firm> greenhouse board" / "<firm> careers workday" or open the
   firm's careers page and inspect where the jobs XHR goes
   (`boards-api.greenhouse.io/v1/boards/<token>/...`,
   `api.lever.co/v0/postings/<token>`, or
   `<tenant>.wd<N>.myworkdayjobs.com/wday/cxs/<tenant>/<site>/jobs`).
2. Update the entry in `config/companies.json`:
   - Greenhouse: `"params": {"board_token": "..."}`
   - Lever: `"params": {"site_token": "..."}`
   - Workday: `"params": {"host": "x.wd5.myworkdayjobs.com", "tenant": "x",
     "site": "SiteName", "search_terms": ["trader", "portfolio manager",
     "quantitative research"]}`
   - No API at all → `"adapter": "agent"` and a good `careers_url`.
3. Re-run `--verify` until every non-agent entry is `OK`, then set
   `"verified": true` on the fixed entries.

Firms whose notes mention a probable hidden JSON API (Millennium/Eightfold,
Goldman/higher.gs.com, Optiver, Jane Street): while fetching as agent, watch
for a JSON endpoint and record it in `notes` — future runs get cheaper.

## 3. Create the cron jobs

Create two OpenClaw cron jobs in the user's timezone (ask if unknown):

- **Daily** — weekdays 07:30 local:
  prompt: "Run the job-posting-monitor skill daily digest."
- **Weekly** — Sunday 18:00 local:
  prompt: "Run the job-posting-monitor skill weekly digest with gap analysis."

## 4. Smoke test

Run the full daily flow once end-to-end (fetch → agent fetch → match →
digest → Telegram) while the user watches, and confirm:
message chunks arrive intact, links work, match quality is sane. Adjust
`min_score` / patterns per their feedback and record any tuning decisions in
`profile.json`'s `_comment` fields.
