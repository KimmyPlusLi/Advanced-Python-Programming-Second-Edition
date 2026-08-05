'use strict';

// Discord voice bridge for an OpenClaw agent.
//
// Flow: user talks in a voice channel -> bot captures each utterance
// (silence-delimited), transcribes it (STT), and posts the text into a paired
// text channel where the OpenClaw agent already listens via its normal
// Discord integration -> the agent's text reply in that channel is spoken
// back into the voice channel (TTS). No private OpenClaw API needed: the
// existing text integration is the transport, and the whole conversation
// stays visible/auditable in the text channel.
//
// Commands (in the paired text channel):
//   !join   join the caller's current voice channel and start bridging
//   !leave  disconnect
//   !mute / !unmute   pause/resume speaking replies aloud

require('dotenv').config();
const fs = require('node:fs');
const path = require('node:path');
const { Readable } = require('node:stream');
const { Client, GatewayIntentBits } = require('discord.js');
const {
  joinVoiceChannel, EndBehaviorType, createAudioPlayer, createAudioResource,
  AudioPlayerStatus, VoiceConnectionStatus, entersState, StreamType,
} = require('@discordjs/voice');
const prism = require('prism-media');
const { pcmToWav } = require('./wav');
const { transcribe } = require('./stt');
const { synthesize } = require('./tts');

const CONFIG_PATH = process.env.VOICE_BRIDGE_CONFIG
  || path.join(__dirname, '..', 'config.json');
const config = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
config.openaiBaseUrl = config.openaiBaseUrl || 'https://api.openai.com/v1';

for (const v of ['DISCORD_TOKEN', 'OPENAI_API_KEY']) {
  if (!process.env[v]) {
    console.error(`missing env var ${v} (see .env.example)`);
    process.exit(1);
  }
}

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
    GatewayIntentBits.GuildVoiceStates,
  ],
});

const state = {
  connection: null,
  player: null,
  textChannel: null,
  muted: false,
  speaking: new Set(),     // user ids currently being captured
  ttsQueue: [],
  playing: false,
};

function log(...args) { console.log(new Date().toISOString(), ...args); }

// ---------- TTS playback queue ----------

async function pumpQueue() {
  if (state.playing || !state.player || state.ttsQueue.length === 0) return;
  state.playing = true;
  const text = state.ttsQueue.shift();
  try {
    const mp3 = await synthesize(text, config);
    if (mp3) {
      const resource = createAudioResource(Readable.from(mp3), {
        inputType: StreamType.Arbitrary,
      });
      state.player.play(resource);
      await new Promise((resolve) => {
        const done = () => { cleanup(); resolve(); };
        const cleanup = () => {
          state.player.off(AudioPlayerStatus.Idle, done);
          state.player.off('error', onErr);
        };
        const onErr = (e) => { log('player error:', e.message); cleanup(); resolve(); };
        state.player.on(AudioPlayerStatus.Idle, done);
        state.player.on('error', onErr);
      });
    }
  } catch (e) {
    log('TTS error:', e.message);
  } finally {
    state.playing = false;
    pumpQueue();
  }
}

function speak(text) {
  if (state.muted || !text) return;
  state.ttsQueue.push(text);
  pumpQueue();
}

// ---------- voice capture ----------

function startCapture(connection) {
  connection.receiver.speaking.on('start', (userId) => {
    if (state.speaking.has(userId)) return;
    if (config.allowedUserIds?.length && !config.allowedUserIds.includes(userId)) return;
    if (userId === client.user.id) return;
    state.speaking.add(userId);

    const opus = connection.receiver.subscribe(userId, {
      end: { behavior: EndBehaviorType.AfterSilence, duration: config.silenceMs || 900 },
    });
    const decoder = new prism.opus.Decoder({ rate: 48000, channels: 1, frameSize: 960 });
    const chunks = [];
    opus.pipe(decoder);
    decoder.on('data', (c) => chunks.push(c));
    decoder.on('error', (e) => log('decoder error:', e.message));

    opus.once('end', async () => {
      state.speaking.delete(userId);
      const pcm = Buffer.concat(chunks);
      // Ignore blips shorter than ~0.4s (48kHz mono s16le = 96000 B/s).
      if (pcm.length < 96000 * 0.4) return;
      try {
        const text = await transcribe(pcmToWav(pcm), config);
        if (!text) return;
        log(`heard <${userId}>: ${text}`);
        const member = await state.textChannel.guild.members.fetch(userId).catch(() => null);
        const name = member?.displayName || 'user';
        const prefix = config.agentUserId && config.mentionAgent
          ? `<@${config.agentUserId}> ` : '';
        await state.textChannel.send(`${prefix}🎙 **${name}**: ${text}`);
      } catch (e) {
        log('STT error:', e.message);
      }
    });
  });
}

// ---------- commands & agent replies ----------

client.on('messageCreate', async (msg) => {
  if (msg.guildId !== config.guildId) return;
  if (config.textChannelId && msg.channelId !== config.textChannelId) return;

  // Agent replies -> speak them.
  if (msg.author.bot && msg.author.id !== client.user.id) {
    if (!config.agentUserId || msg.author.id === config.agentUserId) {
      if (state.connection) speak(msg.content);
    }
    return;
  }
  if (msg.author.bot) return;

  const cmd = msg.content.trim().toLowerCase();
  if (cmd === '!join') {
    const voiceChannel = msg.member?.voice?.channel;
    if (!voiceChannel) { await msg.reply('Join a voice channel first, then `!join`.'); return; }
    state.textChannel = msg.channel;
    state.connection = joinVoiceChannel({
      channelId: voiceChannel.id,
      guildId: msg.guildId,
      adapterCreator: voiceChannel.guild.voiceAdapterCreator,
      selfDeaf: false,
    });
    state.player = createAudioPlayer();
    state.connection.subscribe(state.player);
    try {
      await entersState(state.connection, VoiceConnectionStatus.Ready, 15_000);
    } catch {
      await msg.reply('Could not connect to the voice channel.');
      state.connection.destroy(); state.connection = null;
      return;
    }
    startCapture(state.connection);
    await msg.reply(`Bridged to **${voiceChannel.name}**. Speak when ready; `
      + 'everything you say is transcribed here for the agent, and its replies are spoken back.');
    log('joined voice channel', voiceChannel.id);
  } else if (cmd === '!leave') {
    state.connection?.destroy();
    state.connection = null; state.player = null; state.ttsQueue.length = 0;
    await msg.reply('Left the voice channel.');
  } else if (cmd === '!mute') {
    state.muted = true; await msg.reply('Replies will no longer be spoken (still posted as text).');
  } else if (cmd === '!unmute') {
    state.muted = false; await msg.reply('Speaking replies again.');
  }
});

client.once('ready', () => log(`voice bridge ready as ${client.user.tag}`));
client.login(process.env.DISCORD_TOKEN);
