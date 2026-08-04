# interview-grill

An [OpenClaw](https://openclaw.ai) skill that runs realistic mock interviews
over chat — **voice or text** — drilling the most testable topics from real
job descriptions, scoring you honestly, coaching your delivery, and tracking
your improvement across sessions.

Pairs with the `job-posting-monitor` skill (it drills what your actual
matched JDs demand) but works standalone: paste any job description, or use
the built-in role priors. Ships tuned for trading/finance interviews
(mental math, EV games, options, market making, behavioral); the topic and
question banks are extensible to any field.

## What a session looks like

1. `build_topics.py` ranks what to drill (JD-driven when available).
2. The agent interviews you in character — one question at a time, live
   follow-ups, pressure-testing, no answers revealed mid-session. Voice mode
   uses voice notes both ways (needs STT/TTS configured in OpenClaw; degrades
   gracefully to hybrid or text).
3. Debrief: per-question scores vs 5/5 answer sketches, delivery coaching,
   optional language correction (for non-native speakers), scorecard, drills.
4. Everything is archived verbatim. `sessions.py` retrieves it:
   `list` / `show <date>` / `topic "market making"` (cross-session history
   with score trajectory) / `retake` (re-attempt your weakest questions,
   see the delta) / `export`. `progress.py` tracks weak topics,
   communication trend, and recurring language errors.

## Install

Drop this folder into your OpenClaw skills directory. Python 3.8+, stdlib
only. Optional: install `job-posting-monitor` alongside for JD-driven topics.

## Customize

`config/settings.json`: preferred mode (voice/text), coaching toggles
(delivery, language), channel, session defaults, and the path to matched
JDs. To adapt to another field, extend `TOPICS`/`ROLE_PRIORS` in
`scripts/build_topics.py` and add sections to
`references/QUESTION_BANK.md`. Details in `SKILL.md` → Customization.

## Authenticity guarantee

Built into the skill's rules: your answers are archived **verbatim** and
never rewritten; all AI feedback is a clearly-labeled suggestion alongside
your answer, never a replacement; coaching teaches structure, not scripts to
memorize; and the skill will not ghostwrite answers for real interviews.
Your preparation stays yours.

## License

MIT.
