# job-posting-monitor

An [OpenClaw](https://openclaw.ai) skill that monitors company career sites,
matches openings against your profile, and sends daily/weekly digests to your
chat channel — plus a weekly skill-gap analysis telling you what to learn or
surface on your resume.

Ships configured for trading/finance careers (20 hedge funds, prop shops, and
banks; portfolio manager / prop trader / quant researcher / sell-side trader
roles), but every part of that is config: point it at any employers and any
roles.

## How it works

```
config/companies.json ──► scripts/fetch_jobs.py   ATS APIs (Greenhouse, Lever,
                              │                   Workday, Eightfold, generic
                              │                   JSON, HTML) — stdlib only.
                              │                   Script-hostile sites are
                              │                   fetched by the agent.
config/profile.json  ──► scripts/match_jobs.py    deterministic scoring:
                              │                   role title regexes +
                              │                   keyword/location bonuses
                         scripts/digest.py        dedup state, daily "what's
                              │                   new" / weekly overview +
                              │                   skill-demand trends
                         your chat channel        chunked messages; weekly
                                                  gap analysis follows
```

## Install

Drop this folder into your OpenClaw skills directory. Requires Python 3.8+
(standard library only — no pip installs).

## Setup (first run)

Tell your agent to set up the skill; it follows `references/SETUP.md`:

1. Fill `config/profile.json` (your background, target roles, locations).
2. `python3 scripts/fetch_jobs.py --verify` — repair any ATS entries marked
   `verified: false`. Shipped tokens are best-guess; firms change ATS
   vendors, so expect to fix a few.
3. Create two cron jobs (daily morning, weekly Sunday evening).

Beyond the digests: stated salary ranges are extracted and shown (💰, never
estimated — only what the posting says); an application tracker annotates
postings you've applied to (📨🎤🏆⛔🚫) and nudges follow-ups; every matched
JD is archived forever (full text, even after the posting dies) with
search/trend retrieval; per-posting deep dives explain fit, gaps, and what
to emphasize on your resume; an optional Adzuna aggregator source catches
relevant roles at firms not on your list; and the agent answers ad-hoc
questions between digests from local data.

## Customize

See the Customization section of `SKILL.md`. Short version: firms live in
`companies.json`; roles, matching strictness, locations, delivery channel,
and the skill-gap lexicon live in `profile.json`. No code edits needed.

## Privacy & safety

- Read-only monitoring: the skill never applies to jobs, contacts recruiters,
  or submits forms on your behalf.
- Nothing leaves your machine except fetches of public job boards and the
  digest messages to your own channel.
- `data/` (state, digests, your matches) is runtime-only and gitignored —
  keep it that way if you fork this publicly, and never commit a filled-in
  `profile.json`.

## License

MIT.
