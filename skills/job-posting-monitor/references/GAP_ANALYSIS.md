# Weekly gap analysis playbook

Goal: turn the week's matched postings into concrete advice — what the user
already matches, what they're missing, and what to change on the resume.
This is agent work (reading comprehension), run after the weekly digest.

## Inputs

- Top `digest.gap_analysis_top_n` jobs from `data/matched_jobs.json`
  (highest score first). If a job's `description` is empty (common for
  Workday/agent sources), fetch its URL, read the full posting, and write
  the description into the job's archive entry in `data/jd_archive/` so it
  is captured before the posting dies.
- The durable JD archive (`scripts/jd_archive.py`) for history:
  `trend <term>` shows how often a requirement appears month over month, and
  closed postings still count as demand evidence — use them for the
  week-over-week section instead of relying only on the previous report.
- `background` from `config/profile.json` (skills, credentials, asset
  classes, track record).
- The skill-frequency table from the weekly digest (demand trends).

## Method

1. For each posting, extract the stated requirements into four buckets:
   **technical** (languages, ML/stats, tooling), **market** (asset class,
   strategy style, product knowledge), **credentials** (degrees, FINRA
   series, CFA), **experience** (years, track record, P&L ownership,
   client/flow experience).
2. Aggregate across postings per target role — a requirement matters if it
   appears in ≥3 postings or in every posting of one role.
3. Compare against the user's profile. Classify each aggregated requirement:
   - ✅ **Have & visible** — in their skills/credentials already.
   - 📝 **Have but hidden** — they plausibly have it (infer from background)
     but it isn't stated → resume fix, not a learning task.
   - 📚 **Gap — learnable** — genuinely missing, acquirable (a language,
     kdb+, a certification, a product area).
   - 🚧 **Gap — structural** — needs seat time (track record length, P&L
     size, client franchise). Flag honestly; suggest positioning, not
     pretending.
4. Be conservative about "Have but hidden": only infer what the stated
   background supports. Never suggest claiming skills they don't have.

## Output format (send to Telegram after the weekly digest)

```
**Skill-gap report — <date>** (based on top N postings)

__Where you're strong__
• <requirement> — appears in X postings; covered by <profile item>

__Add to resume (you have it, postings ask for it, it's not stated)__
• <item> — asked in X postings (<example firms>) → suggested bullet: "<draft>"

__Worth acquiring (highest demand first)__
• <skill> — X postings; effort: <low/med/high>; how: <course/cert/project>

__Structural gaps (be aware, position around them)__
• <gap> — <honest one-line positioning advice>

__This week vs last__
• <new requirement trends, if a previous gap-analysis file exists in data/digests/>
```

Keep it under ~3 Telegram messages. Rank by demand frequency × relevance to
the user's preferred role. Save the report to
`data/digests/gap-analysis-YYYY-MM-DD.md` (it feeds next week's trend line).
