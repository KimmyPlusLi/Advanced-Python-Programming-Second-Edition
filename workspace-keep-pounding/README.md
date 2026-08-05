# workspace-keep-pounding 🥊

The OpenClaw **agent workspace** for `keep-pounding` — a corner coach that
turns fragmented time (碎片时间) into compounding skills, chatting with you
on Telegram. This folder is laid out to be copied verbatim to
`~/.openclaw/workspace-keep-pounding` on the machine that runs OpenClaw.

```
workspace-keep-pounding/
├── IDENTITY.md           # agent name, emoji, tagline
├── SOUL.md               # personality and principles
├── skills/
│   └── daily-skill-tracker/   # the tracker skill (generic, ClawHub-publishable)
├── my-skills.json        # PERSONAL skill list — do not publish
└── README.md
```

Workspace-level skills (`skills/` inside the workspace) load only for this
agent, which is exactly what we want: Keep Pounding is the tracker.

## Deploy

On an always-on machine with OpenClaw installed (`npm install -g
openclaw@latest`, `openclaw onboard` once for Claude auth + the Telegram
token from @BotFather):

1. **Install the workspace**

   ```bash
   cp -r workspace-keep-pounding ~/.openclaw/workspace-keep-pounding
   ```

2. **Register the agent** — add `keep-pounding` to the agent list in
   `~/.openclaw/openclaw.json` (schema per your OpenClaw version — see
   `openclaw agents --help` / docs.openclaw.ai; newer versions can do
   `openclaw agents add keep-pounding --workspace ~/.openclaw/workspace-keep-pounding`):

   ```jsonc
   {
     "agents": {
       "list": [
         {
           "id": "keep-pounding",
           "identity": { "name": "Keep Pounding", "emoji": "🥊" },
           "workspace": "~/.openclaw/workspace-keep-pounding"
         }
       ]
     }
   }
   ```

3. **Bind Telegram to the agent** — route the Telegram bot (or a specific
   chat) to `keep-pounding` in the bindings section, so DMs to the bot go
   to this agent rather than the default one:

   ```jsonc
   {
     "bindings": [
       { "agentId": "keep-pounding", "match": { "channel": "telegram" } }
     ]
   }
   ```

4. **Restart the gateway, pair, and say hello** — DM the bot, approve the
   pairing code on the machine, then:
   - "Import my skills from my-skills.json"
   - "Set up my daily nudge at <time>"
   - Hand it any practice already done so the ledger starts real.

Exact config keys drift between OpenClaw versions — treat the snippets as
the shape, and `openclaw --help` / docs.openclaw.ai as the source of truth.
Keep the bot token out of git and out of chats.

## Daily use

Dictate into the chat: "did 10 min of shadowing on the bus, felt smoother
today." That's a complete ledger entry. Ask "what should I practice?" in a
spare moment, "how was my week?" for rollups, "show my dashboard" for the
visual, and share transcripts/memos as evidence. Milestones unlock as you
go. Keep pounding.
