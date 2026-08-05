'use strict';

// Speech-to-text via the OpenAI audio transcription API (utterance-level:
// each silence-delimited chunk of speech is sent as one WAV). Swap the model
// in config (e.g. whisper-1, gpt-4o-transcribe).

async function transcribe(wavBuffer, config) {
  const form = new FormData();
  form.append('file', new Blob([wavBuffer], { type: 'audio/wav' }), 'utterance.wav');
  form.append('model', config.stt.model);
  if (config.stt.language) form.append('language', config.stt.language);

  const resp = await fetch(`${config.openaiBaseUrl}/audio/transcriptions`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${process.env.OPENAI_API_KEY}` },
    body: form,
  });
  if (!resp.ok) {
    throw new Error(`STT failed: HTTP ${resp.status} ${await resp.text()}`);
  }
  const data = await resp.json();
  return (data.text || '').trim();
}

module.exports = { transcribe };
