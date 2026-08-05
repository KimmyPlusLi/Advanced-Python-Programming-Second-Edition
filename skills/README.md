# OpenClaw career skills

Two composable [OpenClaw](https://openclaw.ai) skills for running a job
search and interview prep with an AI agent. Both are stdlib-only Python +
markdown playbooks, fully configurable, MIT licensed.

- **[job-posting-monitor](job-posting-monitor/)** — monitors company career
  sites (ships with 20 hedge funds / prop shops / banks; any employers
  work), matches openings to your profile, sends daily/weekly chat digests,
  and produces a weekly skill-gap & resume analysis.
- **[interview-grill](interview-grill/)** — realistic mock interviews (voice
  or text) drilling the most testable topics from your matched JDs (or any
  pasted JD), with honest scoring, delivery coaching, optional language
  correction, verbatim session archives, and cross-session progress
  tracking. Works standalone; better together with the monitor.

- **[voice-bridge](voice-bridge/)** — companion Discord bot (Node.js) that
  turns interview-grill into a true spoken conversation: you talk in a voice
  channel, the agent hears you (STT) and answers aloud (TTS), relayed
  through the agent's normal Discord text integration. Job digests stay
  text; interviews become dialogue.

Each component's README covers install, setup, and customization.
