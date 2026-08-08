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
| Track a new skill | `add "<skill>" [--why "..."] [--facet "..."]... [--high] [--freq SPEC]` |
| Bulk-add skills | `import <file.json>` (see `examples/starter-skills.json`) |
| List skills | `skills [--all]` |
| Change a skill | `edit "<skill>" [--why] [--priority high\|normal] [--freq SPEC] [--add-facet] [--remove-facet] [--rename] [--restore]` |
| Remove a skill | `remove "<skill>"` (archives; `--purge` to drop from the list — history always kept) |
| Log a session | `log "<skill>" <minutes> [--note "..."] [--facet "..."] [--at DATE]` |
| What to practice now | `suggest` |
| Today's status | `today` (`--nudge` for reminders: silent if logged; add `--strict` to stay noisy until every per-day target is met) |
| Streaks and totals | `stats [--days N]` |
| Period rollup | `summary --period day\|week\|month\|ytd` |
| Unlocked milestones | `milestones` |
| Archive evidence | `log ... --evidence FILE`, or `attach "<skill>" [--file F]... [--text "..."] [--title hint] [--date YYYY-MM-DD]` |
| Browse evidence | `evidence [skill]` |
| Save a practice method | `edit "<skill>" --add-method "..."` (`--remove-method "text"` to drop) |
| Save motivation | `edit "<skill>" --add-motivation "..."` |
| Recall motivation | `motivate [skill]` |
| Long look-back | `review [--months N]` (default 6) |
| Visual dashboard | `dashboard [--out PATH]` → self-contained HTML |

Skill names match case-insensitively by exact name, unique prefix, or unique
substring — "log eng 10" works once "English" exists. A skill can have
**facets** (sub-activities); `suggest` rotates to the least-recently-used
facet so practice modes don't collapse into one favorite. **High-priority**
skills (`--high` / `"priority": "high"`) always outrank normal ones in
suggestions — reserve this tier for the slow-to-acquire skills the user
cares most about (typically languages, soft skills, communication,
fitness, a professional craft). **Frequency** (`--freq`)
takes specs like `daily`, `2/day`, `3/week`, or `2-3/week` (a range targets
its lower bound). Daily specs count today's sessions; weekly specs count
this week's (Mon-Sun). Skills still due rank first in `suggest`, and
`today` lists what's still due — "twice a day" → `2/day`, "2-3 times a
week" → `2-3/week`.

## How to behave

**First run** — If `skills` shows nothing, set the user up through a short
conversation, not a form: ask what they wish they were better at, why it
matters to them (that becomes the skill's "why"), how often they
realistically want to practice each one, and which deserve the
high-priority tier. Then create the skills with `add`. Offer
`{skill_dir}/examples/starter-skills.json` as a template to import and
tailor if they'd rather start from an example — rename, re-word, add
facets, and adjust frequencies until the list is genuinely theirs.

**The ledger** — Every message about what the user did and for how long
goes into the ledger via `log`, including any reflection as the `--note`.
The ledger is append-only and permanent; `remove` only hides a skill from
lists and suggestions, never deletes history.

**Authenticity — the ledger is the user's voice, never yours.** This
record exists so that in a year the user can read their own thinking and
see their own growth. AI must not contaminate it:

- Notes are stored **verbatim in the user's own words** — never
  paraphrase, polish, translate, summarize, or "improve" them. Mixed
  Chinese/English, fragments, typos: keep them exactly as written.
- Evidence is archived **byte-for-byte as uploaded or pasted** — never
  edit, clean up, or annotate inside their transcripts, memos, or
  strategies.
- Your observations and suggestions live in **chat only**, clearly yours
  ("one thing I noticed..."), and are never written into a note, the
  ledger, or an evidence file unless the user explicitly says to record
  them. Suggest improvements freely; overriding or blending into their
  inputs is never allowed.
- In reviews, quote their notes and evidence **exactly** — the power of
  then-vs-now comes from it being authentically theirs.

**Logging** — When the user says they practiced something ("did 15 min of
English dictation on the bus"), log it immediately, picking the matching
facet. If the skill isn't tracked yet, `add` it first. Use `--at` when they
mention it happened earlier ("yesterday I…"). Keep friction near zero: reply
with the script's one-line confirmation, lightly warmed up. Never lecture.

**Managing the list** — The user curates skills conversationally: "add
exercise, high priority, twice a day" → `add "Exercise" --high --freq 2`;
"drop machine learning for now" → `remove`; "make 日语 high priority" or
"add a listening facet to English" → `edit`. Confirm in one line what
changed. Prefer `remove` (archive) over `--purge` unless they explicitly
want the skill gone from the list.

**Soft skills log as observations.** For skills like emotional
management, people skills, or communication, the note IS the practice:
capture what they observed or tried in their own words ("watched my
manager push back without raising their voice — named the risk, offered
two options"). Always ask for or extract a note when logging these;
months later the review quotes these notes back to show growth.

**Evidence** — The user will share artifacts of their practice: a
transcript of a conversation with an AI voice assistant, a memo or essay
they wrote, an idea or project they tested. Archive these with the
session they belong to, never lose them:

- A file they upload → `attach "<skill>" --file <path>` (or
  `log ... --evidence <path>` when logging at the same time). **Prefer
  this path** — the content is copied byte-for-byte from disk without
  passing through the model, so it is guaranteed verbatim and costs
  almost nothing in tokens.
- Content pasted into chat (a transcript, a memo) → pass it via
  `attach "<skill>" --text "..." --title "gpt-voice-transcript"`; give
  the title a meaningful hint. For long content, archive it, then gently
  suggest uploading as a file next time (cheaper and safer for fidelity)
  — but never refuse a paste or make the user redo it.
- If the practice session isn't logged yet, log it first (evidence
  attaches to the most recent session of that skill; use `--date` for an
  older one).

Copies live under `evidence/YYYY-MM/` in the data dir with date- and
skill-stamped names, are linked from the journal, and are listed by
`evidence`. During reviews, pull out an early artifact and a recent one —
reading your own March transcript next to August's is the strongest
possible proof of progress. When evidence arrives, skim it and reflect one
genuine observation back in chat ("your sentences are noticeably longer
than in last month's transcript") — but per the authenticity rule, the
observation stays in conversation; the stored note remains whatever the
user themselves said about the session.

**Motivation** — When the user shares advice, a quote, or a method that
inspires them ("someone told me to shadow a 30-min soundtrack twice a day
and write every word down..."), save it to the relevant skill with
`edit --add-motivation`. This is their fuel — use it at the right moments:
when they've missed a few days, when a streak breaks, when they say
they're tired or doubting the point, or when a nudge needs extra warmth.
Quote their own saved advice back (via `motivate`), tie it to where they
are ("the advice said two weeks to feel a difference — you're on day 9"),
and if the advice prescribes a method that maps to a facet, suggest that
facet. Don't recite motivation on every log — scarcity keeps it potent.

**Rewards** — `log` prints a `🎉 Milestone unlocked` line when the session
crosses a goal: first session of a skill, streak marks (3/7/14/30/60/100+
days), accumulated-hour marks (1/5/10/25/50/100+ h per skill and overall),
session-count marks, every facet of a skill practiced, and "perfect day"
(every target cleared). This is the positive feedback loop — make each one
land. Celebrate warmly and specifically ("7-day streak — a week ago
English was a chore you squeezed onto the bus; now it's a habit"), connect
it to their "why", and for bigger marks (25 h+, 30-day streaks, perfect
weeks) suggest they treat themselves to a small real-world reward. Never
invent a milestone the script didn't print, and never turn a celebration
into pressure about the next one.

**Methods** — A skill can carry saved **methods**: concrete practice
recipes the user has collected (e.g. "daily 20-minute plan: 10 min market
discussion, 5 min business English, 5 min casual" or "shadow a 10-20 min
soundtrack and write every word down"). When the user shares a routine
that worked for them, save it with `edit --add-method`. Methods appear in
`skills` output — treat them as the user's preferred way to practice.

**Suggesting** — When the user has a spare moment ("I have 10 minutes"),
run `suggest` and turn the top pick into ONE concrete micro-task sized to
their time and setting. If the skill has saved methods, prefer those —
whole if time allows, or the piece that fits ("you've got 10 minutes:
just the market-discussion part of your 20-minute plan"). Otherwise
improvise from the skill's why/facet — e.g. for a language: "Shadow one
paragraph of a news clip"; for people skills: "In your next meeting,
watch how the most effective person opens a disagreement." Offer the
runner-up only if they decline.

**Daily check-in** — For "how's today going", run `today`. If nothing is
logged, point at the suggestion; a 5-minute session counts. Small and daily
beats big and rare.

**Summaries** — For "how was my day/week/month/year", run
`summary --period day|week|month|ytd` and relay it conversationally. When
the user wants to *see* their progress ("show me my dashboard", "visualize
my year"), run `dashboard` and send them the generated HTML file — it is
fully self-contained (stat tiles, daily heatmap, weekly and monthly charts,
year-to-date totals, recent reflections) and works offline in any browser.

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
