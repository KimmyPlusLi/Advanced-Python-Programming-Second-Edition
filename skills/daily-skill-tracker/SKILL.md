---
name: daily-skill-tracker
description: Track tiny daily practice sessions on skills the user is learning, using fragmented time (碎片时间). Use when the user wants to log practice time, ask what to practice next, check their streak or progress, or review accumulated effort over weeks/months. Triggers on phrases like "log practice", "I spent X minutes on...", "what should I practice", "show my progress", "skill review", "碎片时间".
---

# Daily Skill Tracker

Help the user build skills through many tiny practice sessions squeezed into
fragmented time. The philosophy: start small, log everything, and let months of
accumulated entries reveal the compounding effect when they look back.

All state lives in `~/.openclaw/skill-tracker/` (override with the
`SKILL_TRACKER_HOME` environment variable) and is managed by the bundled
script. Always use the script — never edit the data files by hand.

```
python3 {skill_dir}/scripts/tracker.py <command> [args]
```

## Commands

| Intent | Command |
|---|---|
| Add a skill to work on | `tracker.py add "<skill>" [--why "reason"]` |
| List tracked skills | `tracker.py skills` |
| Log a session | `tracker.py log "<skill>" <minutes> [--note "what I did"]` |
| What to practice now | `tracker.py suggest` |
| Today's summary | `tracker.py today` |
| Streaks and totals | `tracker.py stats [--days N]` |
| Long look-back | `tracker.py review [--months N]` (default 6) |

Skill names are matched case-insensitively and by unambiguous prefix, so
"log rust 10" works once a skill named "Rust" exists.

## How to behave

**Logging** — When the user says they practiced something ("did 15 min of
leetcode on the bus"), log it immediately with `log`. If the skill isn't
tracked yet, run `add` first and ask for a one-line "why" only if they haven't
implied one. Keep friction near zero: one confirmation line back, e.g.
"Logged 15 min of LeetCode — 4-day streak, 3.2 h total." Never lecture.

**Suggesting** — When the user has a spare moment ("I have 10 minutes, what
should I do?"), run `suggest`. It prioritizes skills not practiced recently
and skills with the least total time, so weak areas don't get abandoned.
Offer one concrete micro-task sized to the time they have, based on the
skill's "why" and recent session notes.

**Daily check-in** — If asked how today is going, run `today`. If nothing is
logged yet, gently point at the suggested skill; a 5-minute session counts.
Small and daily beats big and rare.

**Reviews** — For "how am I doing" over weeks or months, run `review`. Turn
the numbers into a narrative that connects the dots: total hours per skill,
month-over-month trend, longest streaks, and quotes from their own early
session notes vs. recent ones to make the growth visible. This look-back is
the whole point of the skill — make it feel earned, not like a report.

**Reminders** — If the user wants a daily nudge, set up a daily cron/heartbeat
in OpenClaw (e.g. a HEARTBEAT.md entry or cron job) that runs
`tracker.py today` and messages them only if no session is logged yet that
day, including the current `suggest` result. Ask which time of day suits
their schedule before creating it.

## Tone

Encouraging, brief, concrete. Celebrate streaks and firsts ("first time
logging 日语 twice in one day"). Never shame missed days — after a gap, just
suggest the smallest possible restart.
