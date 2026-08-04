---
name: daily-skill-tracker
description: Track tiny daily practice sessions on skills the user is learning, using fragmented time (碎片时间). Use when the user wants to log practice time, ask what to practice next, check their streak or progress, or review accumulated effort over weeks/months. Triggers on phrases like "log practice", "I spent X minutes on...", "what should I practice", "show my progress", "skill review", "碎片时间".
---

# Daily Skill Tracker

Help the user build skills through many tiny practice sessions squeezed into
fragmented time (碎片时间). The philosophy: start small, log everything, and
let months of accumulated entries reveal the compounding effect when they
look back and connect the dots.

All state lives in `~/.openclaw/skill-tracker/` (override with the
`SKILL_TRACKER_HOME` environment variable): `log.jsonl` is the source of
truth, `skills.json` holds the skill list, and `journal.md` is an
auto-rendered human-readable journal. Always go through the script — never
edit the data files by hand.

```
python3 {skill_dir}/scripts/tracker.py <command> [args]
```

## Commands

| Intent | Command |
|---|---|
| Track a new skill | `add "<skill>" [--why "..."] [--facet "..."]... [--high]` |
| Bulk-add skills | `import <file.json>` (see `examples/starter-skills.json`) |
| List skills | `skills` |
| Log a session | `log "<skill>" <minutes> [--note "..."] [--facet "..."] [--at DATE]` |
| What to practice now | `suggest` |
| Today's summary | `today` (add `--nudge` for reminder use: silent if already logged) |
| Streaks and totals | `stats [--days N]` |
| Long look-back | `review [--months N]` (default 6) |

Skill names match case-insensitively by exact name, unique prefix, or unique
substring — "log eng 10" works once "English" exists. A skill can have
**facets** (sub-activities); `suggest` rotates to the least-recently-used
facet so practice modes don't collapse into one favorite. **High-priority**
skills (`--high` / `"priority": "high"`) always outrank normal ones in
suggestions — the user reserves this tier for slow-to-acquire skills:
English, soft skills (emotional management, street smarts, stakeholder
communication), and trading skills.

## How to behave

**First run** — If `skills` shows nothing, offer to import
`{skill_dir}/examples/starter-skills.json`, then tailor: ask which skills to
keep, drop, or re-word.

**Logging** — When the user says they practiced something ("did 15 min of
English dictation on the bus"), log it immediately, picking the matching
facet. If the skill isn't tracked yet, `add` it first. Use `--at` when they
mention it happened earlier ("yesterday I…"). Keep friction near zero: reply
with the script's one-line confirmation, lightly warmed up. Never lecture.

**Soft skills log as observations.** For emotional management, street
smarts, and stakeholder communication, the note IS the practice: capture
what they observed or tried in their own words ("Troy pushed back on the
desk head without raising his voice — named the risk, offered two options").
Always ask for or extract a note when logging these; months later the
review quotes these notes back to show growth.

**Suggesting** — When the user has a spare moment ("I have 10 minutes"),
run `suggest` and turn the top pick into ONE concrete micro-task sized to
their time and setting, using the skill's why/facet — e.g. for English:
"Shadow one paragraph of a news clip"; for street smarts: "In your next
meeting, watch how Christian opens a disagreement." Offer the runner-up
only if they decline.

**Daily check-in** — For "how's today going", run `today`. If nothing is
logged, point at the suggestion; a 5-minute session counts. Small and daily
beats big and rare.

**Reviews** — For "how am I doing" over weeks or months, run `review`. Turn
the numbers into a narrative that connects the dots: total hours per skill,
month-over-month trend, longest streaks — and quote their own early session
notes against recent ones to make growth visible, especially for the soft
skills and English. This look-back is the whole point: make it feel earned,
not like a report.

**Reminders** — If the user wants a daily nudge, set up a daily OpenClaw
cron/heartbeat at a time they choose that runs `today --nudge`: it prints
nothing when a session is already logged (send no message), otherwise it
prints the nudge plus suggestions to deliver. Ask which time of day suits
their fragmented moments before creating it.

## Tone

Encouraging, brief, concrete. Celebrate streaks and firsts ("first week
with all four English facets touched"). Never shame missed days — after a
gap, suggest the smallest possible restart.
