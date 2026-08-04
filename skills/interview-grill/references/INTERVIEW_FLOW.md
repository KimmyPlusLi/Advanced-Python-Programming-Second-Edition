# Interview session protocol

## 0. Voice capability check (once per session)

Voice does not depend on the LLM (a text-only model like Codex is fine):
OpenClaw transcribes inbound Telegram voice notes to text via its configured
speech-to-text provider, and outbound voice needs a configured TTS provider.
At session start in voice mode, determine what this deployment supports:

- STT + TTS → **full voice**: questions and debrief summary spoken, scorecard
  in text.
- STT only → **hybrid**: your questions in text, user answers by voice note.
  Tell the user once; hybrid still trains verbal delivery.
- Neither → text mode; tell the user what to configure (an STT/TTS provider
  in OpenClaw's config) to unlock voice.

## 1. Session setup

Collect (one message, sensible defaults): target role or specific matched
job, length (quick 6–8 Q / full 15–20 Q), difficulty (screen / final),
mode (text / voice). Build the plan:

- 60% top topics for the role from `data/topics.json`
- 25% weak topics from `scripts/progress.py`
- 15% behavioral/fit, themed to the target firm's style
  (prop shop → games/market making; hedge fund → track record, process,
  risk; bank → client scenarios, product knowledge, fit)

Write the plan down internally (topic per question slot) before Q1.
Announce the format briefly, then start — no lengthy preamble.

## 2. Question loop (repeat per slot)

1. Ask ONE question, in character. Voice mode: short sentences, numbers
   restated ("strike one-oh-five, that's 105").
2. Wait for the answer. Do not answer for them. Silence >2–3 min in a live
   session → one nudge ("Take your time — want to reason out loud?").
3. Evaluate silently, score 0–5:
   - 5 correct + crisp reasoning; 4 correct, minor slips; 3 right direction,
     incomplete; 2 significant errors; 1 mostly wrong; 0 no attempt.
   - Voice mode: also note delivery (structure, filler, confidence) — it
     adjusts the communication score, not the topic score.
4. Branch like a real interviewer:
   - Strong answer → one deeper follow-up on the same thread, then next slot.
   - Shaky answer → one neutral probe ("What's driving that?"), then move on.
   - Wrong answer → do NOT correct mid-session; note it for the debrief.
5. Occasionally (2–3 times per session) challenge a CORRECT answer
   ("Are you sure?") — pressure-testing conviction is standard in trading
   interviews; score how they defend it.

## 3. Debrief

1. Break character explicitly ("Okay, stepping out of interviewer mode.").
2. Per question: what they said, what a 5/5 answer looks like, their score.
3. **Delivery coaching** (voice/hybrid): quote their own phrasing back and
   show the tightened version — filler and hedging removed, answer-first
   structure. One or two rewrites per session beat a lecture.
4. **English correction**: the user wants their English fixed. During the
   interview, never correct language — only note mistakes silently (grammar,
   word choice, unnatural phrasing, misused finance terms; e.g. "the price
   go up" → "the price goes up", "make a hedge" → "put on a hedge"). In the
   debrief list each mistake as `they said → natural version`, and call out
   any error also made in previous sessions (see `recurring_language_errors`
   in progress.py output) — repetition is the priority signal. Judge from
   the transcript only; don't guess at pronunciation.
5. Scorecard (text, even in voice mode), then 2–3 targeted drills for the
   weakest topics, each tied to the firms/JDs demanding that topic
   (from `topics.json`).
6. Cross-reference job-posting-monitor's latest gap analysis if present
   (`../job-posting-monitor/data/digests/gap-analysis-*.md`): weakness that
   also appears as JD demand = flag as top priority.

## 4. Persist the session

Save `data/sessions/YYYY-MM-DD-<role>.json`:

```json
{
  "date": "YYYY-MM-DD",
  "role": "prop_trader",
  "target_firm": "Jane Street",
  "mode": "voice",
  "difficulty": "screen",
  "questions": [
    {
      "topic": "probability & expected value",
      "question": "…as asked…",
      "answer_full": "…their complete answer, verbatim (voice: the transcript). This is the archive — future review sessions replay it, so don't truncate…",
      "answer_summary": "…2-3 lines…",
      "ideal_answer": "…the 5/5 answer sketch given in the debrief…",
      "score": 3,
      "notes": "right EV setup, arithmetic slip on the conditional",
      "retake_of": "2026-08-01 optional — set when re-asking an archived question"
    }
  ],
  "communication_score": 4,
  "language_errors": [
    {"said": "the price go up", "correct": "the price goes up", "type": "grammar"},
    {"said": "make a hedge", "correct": "put on a hedge", "type": "finance idiom"}
  ],
  "overall": 3.4,
  "drills_assigned": ["…"]
}
```

Save the human-readable scorecard to `data/scorecards/YYYY-MM-DD-<role>.md`.
Topic strings MUST match `build_topics.py` topic names exactly — progress.py
aggregates on them.

## Interviewer style calibration

- Prop shop screen: rapid-fire, mental math under time pressure, games with
  EV, market-making a random variable ("make me a market on X"), betting
  challenges on confidence.
- Hedge fund (PM/QR): process-heavy — "walk me through a trade you'd put on
  now", sizing, drawdown behavior, where the alpha comes from, why it isn't
  arbitraged away; for QR add stats/ML depth and a research-design question.
- Bank (sell-side): product knowledge, client scenario role-play ("client
  wants to sell 2M of an illiquid name — walk me through it"), market
  awareness ("where's 10y? what moved this week?"), fit and pressure
  questions.
