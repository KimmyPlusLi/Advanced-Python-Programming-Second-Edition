# Per-posting deep dive

Run when the user asks about one specific posting ("tell me more about the
Jane Street role", "am I a fit for that Point72 PM job?"). This is the
per-job version of the weekly gap analysis: evidence-based, no speculation.

## Gather

1. Locate the posting: `python3 scripts/jd_archive.py show <fragment>`
   (works for closed postings too). If the archived description is empty and
   the posting is still live, fetch its URL, then write the description back
   into the archive entry.
2. Load `background` from `config/profile.json` and, if the interview-grill
   skill is installed, its `progress.py` output (interview-tested strengths
   and weaknesses are stronger evidence than self-description).

## Produce (one message unless the user wants depth)

```
**<Company> — <Title>**  (score N, first seen <date>, <active|closed>)
<location or "location not specified"> · <stated comp or "comp not specified">

__Why it fits__          — 2–4 bullets, each citing JD language vs profile
__Gaps / risks__         — requirements you don't clearly meet; label each
                           learnable vs structural; flag any that interview
                           sessions confirmed as weak
__Resume emphasis__      — which of the user's EXISTING points to lead with
                           for this specific posting (suggestions, not
                           ghostwriting)
__Verdict & next step__  — apply now / prep X first / skip because Y;
                           offer to mark it: applications.py mark ...
```

## Rules

- Every claim in "Why it fits" and "Gaps" must trace to actual JD text or
  the user's stated profile — quote the JD phrase when it matters.
- Missing facts stay missing: "comp not specified", "seniority unclear".
  Never estimate a number the posting doesn't state.
- Resume emphasis reorders and highlights what the user already has; it
  never invents experience (same authenticity rule as interview-grill).
