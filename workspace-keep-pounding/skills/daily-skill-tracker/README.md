# daily-skill-tracker

An [OpenClaw](https://openclaw.ai) skill for building hard-to-acquire skills
through tiny practice sessions squeezed into fragmented time (碎片时间).

Some skills — a language, communication, emotional steadiness, a craft —
don't yield to a weekend of effort. They only yield to hundreds of small
sessions, and the hard part is the middle: week one you notice nothing, week
two you feel a flicker, and most people quit before the compounding shows.
This skill defends that middle. Log a few minutes whenever you can, in plain
chat. Get nudged only when something is actually due. Unlock milestones as
effort accumulates. Then — five months or a year later — look back at the
ledger and read your own early notes next to your recent ones. That's the
compounding effect, made visible, in your own words.

## What it does

- **Zero-friction logging** — "did 10 min of shadowing on the bus" is a
  complete log entry: skill, facet, minutes, timestamp, and your reflection,
  stored verbatim.
- **Facets** — a skill like a language is really several practice modes
  (dictation, speaking, reading, writing); suggestions rotate to the
  least-recently-used facet so you don't collapse into one favorite.
- **Priorities & frequencies** — mark slow-to-acquire skills high priority;
  set each skill's cadence (`daily`, `2/day`, `3/week`, `2-3/week`). Skills
  still due rank first when you ask "what should I practice?"
- **Silent-unless-needed reminders** — a daily nudge that stays quiet once
  you've practiced (or, in strict mode, until every target is met).
- **Milestone rewards** — first sessions, streaks, accumulated hours,
  perfect days: a 🎉 at the moment you earn it, and a permanent trophy list.
- **Evidence archive** — attach transcripts, memos, or work you produced to
  any session; archived byte-for-byte and linked from the journal.
- **Motivation store** — save the advice that inspires you per skill; the
  agent brings it back at low moments, tied to where you actually are.
- **Summaries & dashboard** — day/week/month/year-to-date rollups in chat,
  plus a self-contained HTML dashboard: stat tiles, a daily heatmap, weekly
  and monthly charts, per-skill totals, milestones, and recent reflections.
  Light/dark, hover tooltips, works offline.
- **An append-only ledger in your voice** — removing a skill archives it;
  history is never deleted. Notes and evidence are stored exactly as you
  wrote them: the AI may coach in chat, but never rewrites your record.

## Install

Copy this folder into your OpenClaw skills directory:

```bash
cp -r daily-skill-tracker ~/.openclaw/skills/
```

Your data lives separately in `~/.openclaw/skill-tracker/` (override with
`SKILL_TRACKER_HOME`), so updating or reinstalling the skill never touches
your history:

- `log.jsonl` — one line per session; the source of truth
- `skills.json` — your skill list (why, facets, priority, frequency)
- `journal.md` — auto-rendered, human-readable journal grouped by month
- `achievements.jsonl` — your unlocked milestones
- `evidence/YYYY-MM/` — archived artifacts, date- and skill-stamped
- `dashboard.html` — the visual dashboard, regenerated on request

## Make it yours

The skill ships with a **generic template** — customize it in conversation:

1. On first run the agent interviews you: what do you want to get better
   at, why does it matter, how often will you realistically practice, and
   which skills deserve the high-priority tier.
2. Or start from `examples/starter-skills.json`: import it, then rename,
   re-word the whys, add facets, and adjust frequencies until it's yours.
   You can also edit the JSON directly before importing.
3. Everything stays editable by message afterwards: "add 日语, high
   priority, twice a day", "move X to 2-3 times a week", "add a listening
   facet to Spanish", "drop chess for now" (archives, history kept),
   "remember this advice for my writing: ...".

## Quick start (CLI, for the curious)

```bash
python3 scripts/tracker.py import examples/starter-skills.json
python3 scripts/tracker.py add "Public speaking" --high --freq 2-3/week
python3 scripts/tracker.py log "Language learning" 10 --facet "Writing" --note "wrote a diary entry"
python3 scripts/tracker.py suggest          # what to practice in a spare moment
python3 scripts/tracker.py summary --period week
python3 scripts/tracker.py review           # the 6-month look-back
python3 scripts/tracker.py dashboard        # visual HTML dashboard
```

In OpenClaw you never type these — just talk to the agent.

Stdlib-only Python 3; no dependencies.

## License

MIT — see [LICENSE](LICENSE).
