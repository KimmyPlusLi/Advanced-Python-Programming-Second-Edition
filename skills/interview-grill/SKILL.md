---
name: interview-grill
description: Run realistic mock interviews (text or voice, over Telegram) for portfolio manager, prop trader, quantitative researcher, and sell-side trader roles, drilling the most testable topics extracted from job descriptions matched by the job-posting-monitor skill. Use when the user asks for interview prep, a mock interview, to be grilled/quizzed, or to review interview performance and weak areas.
metadata: {"openclaw": {"emoji": "🎤"}}
---

# Interview Grill

Companion to `../job-posting-monitor`. That skill finds matched postings;
this one turns their job descriptions into interview drills and runs them
like a real interviewer would — one question at a time, live follow-ups,
honest scoring, and a weakness log that shapes the next session.

All paths relative to this skill's directory. Runtime data lives in `data/`
(never commit). Scripts are Python 3 stdlib-only.

## Starting a session

1. Build/refresh the topic plan:
   `python3 scripts/build_topics.py`
   (reads `../job-posting-monitor/data/matched_jobs.json`; if it's missing or
   stale >7 days, run that skill's fetch+match first). Output:
   `data/topics.json` — ranked testable topics per role, with the firms/JDs
   demanding each.
2. Check `python3 scripts/progress.py` for weak topics from past sessions.
3. Ask the user (briefly, one message): which role or specific matched job to
   interview for, session length (quick ~15 min / full ~45 min), difficulty
   (screen / final round), and **text or voice**. Default: their
   highest-scored matched role, quick, screen, **voice** — the user
   specifically wants to polish verbal delivery, so prefer voice (or hybrid)
   whenever the deployment allows it.
4. Compose the session plan: ~60% top-ranked topics for that role from
   `topics.json`, ~25% weak topics from `progress.py`, ~15% behavioral/story
   questions tied to the target firm. Use `references/QUESTION_BANK.md` for
   question styles and what-good-looks-like; adapt numbers/underliers so
   questions are never repeated verbatim across sessions.

## Conducting the interview (both formats)

Follow `references/INTERVIEW_FLOW.md` strictly. The essentials:

- **Stay in character** as a professional interviewer from the target firm.
  Brief, neutral acknowledgements ("Okay." / "Walk me through that.") — no
  praise mid-question, no teaching until the debrief.
- **One question per message.** Never send a list of questions. Wait for the
  answer. Real interviews are a dialogue.
- **Probe like a real interviewer**: if the answer is right, push deeper
  ("And if vol doubles?"); if wrong or vague, give one neutral nudge, then
  move on and note it. Never reveal the answer mid-session.
- **Timebox**: quick = 6–8 questions, full = 15–20 including a market/story
  segment. Announce "last question" before the final one.
- Track every question, answer summary, and 0–5 score silently as you go.

## Text vs voice

- **Text mode**: Telegram text messages. Mental-math and probability
  questions get a "answer without tools, reply within ~60s" framing —
  remind the user once at the start, then trust them.
- **Voice mode**: the user answers with Telegram voice notes; transcribe and
  treat exactly like text answers. Reply with voice too when your deployment
  can send TTS voice notes — keep spoken questions short and natural, restate
  numbers clearly ("one hundred, strike one-oh-five"). If you cannot send
  voice, say so once and run hybrid (your questions in text, their answers by
  voice) — that still trains verbal delivery, which is the point.
  In voice mode also score **communication**: real interviews judge the
  delivery, not just the content. Listen for (via the transcript): filler
  words and hedging ("kind of", "I guess", "maybe like"), answer-first
  structure vs rambling toward the point, undefended flip-flopping under
  challenge, and rehearsed-sounding vs natural stories. Give concrete
  delivery feedback in the debrief — quote their own phrasing back and show
  the tightened version. Track a per-session communication score (0–5) so
  `progress.py` can show the trend.

## Debrief (always, end of session)

1. Per-question review: their answer, ideal answer sketch, score 0–5.
2. Delivery coaching and **English correction** — the user is polishing both
   interview communication and their English. Never correct language
   mid-interview; log mistakes silently and correct them in the debrief
   (`they said → natural version`), flagging errors that recur across
   sessions. Details in `references/INTERVIEW_FLOW.md`.
3. Session scorecard: overall, by topic, plus 2–3 concrete drills for the
   weakest areas. Send to Telegram; in voice mode send the scorecard as text
   (numbers don't belong in audio).
4. Save the session per the schema in `references/INTERVIEW_FLOW.md` to
   `data/sessions/<date>-<role>.json` and the scorecard markdown to
   `data/scorecards/`. This feeds `progress.py` and the next session's plan.
5. If a weak topic matches a gap already identified by job-posting-monitor's
   weekly gap analysis, say so — interview weakness + JD demand = top
   learning priority.

## Rules

- Honest scoring beats kindness: an inflated score costs the user a real
  offer. Score what was actually said, not what they probably meant.
- Never fabricate firm-specific interview questions as "known leaks"; frame
  everything as representative practice for that firm's style.
- The user can say "pause", "skip", or "end" at any time — comply instantly,
  then debrief whatever was covered.
