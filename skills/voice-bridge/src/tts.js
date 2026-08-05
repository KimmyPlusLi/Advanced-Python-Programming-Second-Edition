'use strict';

// Text-to-speech via the OpenAI speech API. Returns an MP3 buffer;
// @discordjs/voice transcodes it through ffmpeg (ffmpeg-static) at playback.

const MAX_TTS_CHARS = 3500;

function stripForSpeech(text) {
  return text
    .replace(/```[\s\S]*?```/g, ' (code omitted) ')
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')  // markdown links -> label
    .replace(/[*_`#>|]/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

async function synthesize(text, config) {
  const input = stripForSpeech(text).slice(0, MAX_TTS_CHARS);
  if (!input) return null;
  const resp = await fetch(`${config.openaiBaseUrl}/audio/speech`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${process.env.OPENAI_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      model: config.tts.model,
      voice: config.tts.voice,
      input,
      response_format: 'mp3',
      speed: config.tts.speed || 1.0,
    }),
  });
  if (!resp.ok) {
    throw new Error(`TTS failed: HTTP ${resp.status} ${await resp.text()}`);
  }
  return Buffer.from(await resp.arrayBuffer());
}

module.exports = { synthesize, stripForSpeech };
