# voice-bridge — talk to your OpenClaw agent in a Discord voice channel

Continuous spoken conversation with your OpenClaw agent: put on headphones,
join a voice channel, and talk. The bridge captures each thing you say
(silence-delimited), transcribes it, and posts it into a paired text channel
where your agent already listens through its normal Discord integration; the
agent's reply is then spoken back into the voice channel. Built to give the
`interview-grill` skill a real interview feel — no push-to-talk, no voice
notes — but it bridges any conversation with the agent.

Because the transport is the agent's existing text channel, there is **no
OpenClaw API dependency**, and the full conversation stays readable in text —
which interview-grill needs anyway for verbatim session archiving.

```
you (headphones, voice channel)
  │ speech            ▲ TTS audio
  ▼                   │
voice-bridge bot ─────┘
  │ transcript         ▲ agent reply text
  ▼                    │
paired #text channel ──┘
  (OpenClaw agent's normal Discord integration)
```

## Prerequisites

- Node.js 18+ (uses global fetch/FormData).
- An OpenAI API key (STT via `gpt-4o-transcribe`, TTS via `gpt-4o-mini-tts`
  by default; models configurable).
- Your OpenClaw agent already connected to Discord as a bot, responding in a
  text channel (its standard Discord channel integration).

## Setup

1. **Create the bridge bot** at https://discord.com/developers/applications:
   New Application → Bot. Copy the token. Under *Privileged Gateway
   Intents*, enable **Message Content Intent**.
2. **Invite it** to your (private) server: OAuth2 → URL Generator → scope
   `bot`, permissions *View Channels, Send Messages, Read Message History,
   Connect, Speak* → open the generated URL.
3. **Pair the channels**: pick a text channel your OpenClaw agent responds
   in, and any voice channel. In Discord, enable Developer Mode and copy the
   server ID, text channel ID, and the OpenClaw bot's user ID.
4. **Configure**:
   ```
   cp config.example.json config.json   # fill the IDs
   cp .env.example .env                 # bridge bot token + OpenAI key
   npm install
   npm start
   ```

## Use

1. Join the voice channel with your headphones on.
2. In the paired text channel, type `!join`.
3. Say something like "let's do a mock interview for a prop trader role" —
   the agent picks it up through interview-grill and the whole session runs
   as a spoken back-and-forth. `!mute` / `!unmute` toggle spoken replies;
   `!leave` disconnects.

Set `allowedUserIds` in config.json to your own Discord user ID so the
bridge only ever transcribes you.

## Interview-grill fit

- In `skills/interview-grill/config/settings.json`, set
  `"channel": "discord"` — sessions and scorecards then flow through the
  paired channel.
- The bridge posts your words verbatim into the text channel, which is
  exactly what the skill archives (`answer_full`) — voice sessions get the
  same authentic-answer guarantees as text ones.
- Scorecards and digests remain text messages in the channel (numbers don't
  belong in audio); job-posting-monitor digests are unaffected and keep
  going to whatever channel its own config names (e.g. Telegram).

## Notes & tuning

- `silenceMs` (default 900): how long a pause ends your utterance. Raise it
  if it cuts you off mid-thought during slow mental math; lower it for
  snappier turns.
- Utterances shorter than ~0.4 s are ignored (coughs, clicks).
- The bridge speaks replies from the configured `agentUserId` only, and
  never transcribes its own audio.
- Costs: each utterance is one STT call and each agent reply one TTS call —
  a 45-minute session is typically well under a dollar with the default
  models; check current OpenAI pricing.
- Keep the server private: anyone in the voice channel could otherwise talk
  to your agent (and be transcribed). `allowedUserIds` is the guard.

## License

MIT.
