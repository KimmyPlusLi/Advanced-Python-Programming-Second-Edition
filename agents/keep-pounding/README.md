# Keep Pounding 🥊

A deployable [OpenClaw](https://openclaw.ai) agent bundle: a corner coach
that turns fragmented time (碎片时间) into compounding skills over months
and years, chatting with you on Telegram.

## What's in this folder

```
keep-pounding/
├── workspace/            # the agent's persona
│   ├── IDENTITY.md       #   name, emoji, tagline
│   └── SOUL.md           #   personality and principles
├── skills/
│   └── daily-skill-tracker/   # the tracker skill (publishable to ClawHub)
├── my-skills.json        # PERSONAL skill list — do not publish
└── README.md
```

`my-skills.json` is the owner's private, customized skill list. Everything
under `skills/daily-skill-tracker/` is generic and safe to publish.

## Deploy (~15 min, on an always-on machine)

1. **Create the Telegram bot** — message @BotFather: `/newbot`, name it
   `Keep Pounding`, pick a username ending in `bot`, copy the token.
2. **Install OpenClaw** — `npm install -g openclaw@latest`, then
   `openclaw onboard`; choose Telegram and paste the token. Keep the bot
   token out of git and out of chats.
3. **Install the persona** — copy `workspace/*.md` into the OpenClaw
   workspace directory (`~/.openclaw/workspace/`).
4. **Install the skill** — `cp -r skills/daily-skill-tracker ~/.openclaw/skills/`
   and copy `my-skills.json` somewhere the agent can read.
5. **Pair** — DM the bot in Telegram and approve the pairing code on the
   machine.
6. **First conversation** —
   - "Import my skills from my-skills.json"
   - "Set up my daily nudge at <time>"
   - Hand it any practice you've already done so the ledger starts real.

Command names can drift between OpenClaw versions — `openclaw --help` and
docs.openclaw.ai are the source of truth.

## Daily use

Dictate into the chat: "did 10 min of shadowing on the bus, felt smoother
today." That's a complete ledger entry. Ask "what should I practice?" in a
spare moment, "how was my week?" for rollups, "show my dashboard" for the
visual, and share transcripts/memos as evidence. Milestones unlock as you
go. Keep pounding.
