# daily-skill-tracker

An [OpenClaw](https://openclaw.ai) skill for building hard-to-acquire skills
through tiny practice sessions squeezed into fragmented time (碎片时间).

Log a few minutes whenever you can. Get nudged only on days you haven't
practiced. Then — five months or a year later — look back at the journal and
see the accumulated hours, the streaks, and your own early notes next to your
recent ones. That's the compounding effect, made visible.

## Install

Copy this folder into your OpenClaw skills directory:

```bash
cp -r daily-skill-tracker ~/.openclaw/skills/
```

Your data lives separately in `~/.openclaw/skill-tracker/` (override with
`SKILL_TRACKER_HOME`), so updating or reinstalling the skill never touches
your history:

- `log.jsonl` — one line per session; the source of truth
- `skills.json` — your skill list (why, facets, priority)
- `journal.md` — auto-rendered, human-readable journal grouped by month

## Quick start

```bash
python3 scripts/tracker.py import examples/starter-skills.json   # or add your own
python3 scripts/tracker.py add "日语" --why "..." --high --freq 2   # twice a day
python3 scripts/tracker.py log "English" 10 --facet "Writing" --note "wrote a standup update from scratch"
python3 scripts/tracker.py suggest        # what to practice in a spare moment
python3 scripts/tracker.py summary --period week   # day|week|month|ytd rollup
python3 scripts/tracker.py stats          # streaks and totals
python3 scripts/tracker.py review         # the 6-month look-back
python3 scripts/tracker.py dashboard      # visual HTML dashboard
python3 scripts/tracker.py remove "ML"    # archive (history kept); edit --restore undoes
```

In OpenClaw you never type these — just say "did 10 min of English writing on
the bus" and the agent logs it, or "I have 15 free minutes" and it suggests
the most neglected skill with a concrete micro-task.

## Design notes

- **Facets** — a skill like English is really several practice modes
  (dictation, speaking, reading, writing); suggestions rotate to the
  least-recently-used facet.
- **Priority** — mark slow-to-acquire skills (soft skills, languages) as
  high; they always outrank normal skills in suggestions.
- **Soft skills log as observations** — for skills like "street smarts" the
  note is the practice; reviews quote early notes against recent ones.
- **Frequency targets** — `--freq` takes `daily`, `2/day`, `3/week`, or
  `2-3/week`; skills still due (today, or this week for weekly targets)
  rank first in suggestions.
- **Silent-unless-needed reminders** — `today --nudge` prints nothing once
  you've practiced, so a daily cron only pings you when it should
  (`--strict` keeps nudging until every per-day target is met).
- **Append-only ledger** — removing a skill archives it; logged history is
  never deleted, so the multi-year record stays intact.
- **Visual dashboard** — `dashboard` renders a self-contained HTML page:
  stat tiles, GitHub-style daily heatmap, weekly bars, monthly stacked by
  skill, year-to-date totals, a table view, and your recent reflections.
  Light and dark mode, hover tooltips, no external dependencies.
- Stdlib-only Python 3; no dependencies.
