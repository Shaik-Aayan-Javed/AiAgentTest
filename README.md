# AI Voice Assistant

An AI-powered virtual voice assistant that answers phone calls, responds to callers,
and escalates to you when needed. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
for the full design.

> **Status:** In development.
> Phase 1 (foundation) ✅ · Phase 2 (TTS) ✅ · Phase 3 (STT + echo) ✅ · Phase 4 (brain) ✅ · tiered response next.

---

## Architecture in one line

Three separate AIs behind swappable interfaces: **Whisper** (speech→text, self-hosted),
**Claude** (the reasoning brain, API), **Coqui XTTS-v2** (text→speech in *your* cloned
voice, self-hosted). Only Claude costs money.

---

## Prerequisites

- **Python 3.11+**
- **Docker Desktop** (for Coqui TTS, Redis, PostgreSQL)
- A **Deepgram API key** — optional, only if you flip STT to Deepgram later

---

## Setup

```bash
# 1. Clone and enter
git clone https://github.com/Shaik-Aayan-Javed/AiAgentTest
cd AiAgentTest

# 2. Create a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env        # then fill in any keys you have

# 5. Start the Docker services (Coqui TTS, Redis, Postgres)
docker compose up -d
# First boot downloads the XTTS-v2 model (~1.8GB) — give it 2–5 minutes.
```

---

## Run the server

```bash
uvicorn app.main:app --reload
```

- API docs (Swagger UI): http://localhost:8000/docs
- Health check: http://localhost:8000/api/health

---

## Try the TTS module (Phase 2)

### Option A — CLI script

```bash
python scripts/test_tts.py "Hello, thank you for calling. How can I help you today?"
```

Saves an audio file, prints timing/provider details, and offers to play it.

> No Docker yet? Set `TTS_PROVIDER=gtts` in `.env` to use the zero-setup fallback
> voice (generic, not cloned) so you can test the pipeline end-to-end.

### Option B — API

```bash
curl -X POST http://localhost:8000/api/tts/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text": "We are open Monday to Friday, nine to five."}'
```

Returns `audio_url`, latency, provider, and the preprocessed text.

---

## Cloning your voice (Coqui)

1. Record 15–30 seconds of clean speech (quiet room, normal pace).
2. Save it as `assets/voice_sample.wav`.
3. `docker compose restart coqui-tts` — the file is exposed to Coqui as the speaker
   `voice_sample` (matches `TTS_DEFAULT_VOICE` in `.env`).

The Voice Studio UI (a later phase) will let you record this in the browser.

---

## Try the STT module (Phase 3)

Speech-to-text. The default engine is **Whisper** (self-hosted, free). Install the
opt-in engine first:

```bash
pip install -r requirements-stt.txt
```

> On Python 3.14 this may fail (ctranslate2 wheels lag new Pythons). If so, either
> use a Python 3.12 venv, or set `STT_PROVIDER=deepgram` in `.env` and add a free
> `DEEPGRAM_API_KEY` — the module works identically either way.

Transcribe an audio file (record a quick voice memo and drop it in):

```bash
python scripts/test_stt.py my_recording.wav
```

Prints the transcript, confidence, detected language, latency, and the provider.

## Echo test — the full pipeline (STT → TTS)

Proves both modules work together: your recording is transcribed, then spoken back.

```bash
python scripts/test_loop.py my_recording.wav
```

```
[1/2] Transcribing my_recording.wav ...
  Heard (Whisper (faster-whisper), conf 0.94):
    'what are your opening hours'
[2/2] Speaking it back ...
  Spoken by Coqui XTTS-v2, saved to: app/static/audio/....wav
Play the echo now? [y/N]
```

The real assistant will slot Claude between these two steps
(`audio → STT → text → Claude → reply → TTS → audio`).

---

## Try the brain (Phase 4)

Now it *answers* instead of echoing. Add your Anthropic key to `.env`:

```bash
ANTHROPIC_API_KEY=sk-ant-...
```

**Text chat (no audio, no Docker — just the key):**

```bash
python scripts/test_conversation.py
# You: what are your opening hours?
# AI:  We're open Monday to Friday, nine to five. Is there anything else I can help with?
#      [Claude/claude-haiku-4-5 · 48+21 tok · 610 ms]
```

**Full voice pipeline (audio → STT → Claude → TTS → playback):**

```bash
python scripts/test_conversation.py my_recording.mp3
```

**Or via the API:**

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "What are your hours?"}]}'
```

Uses **Claude Haiku 4.5** (fast, low-cost) by default — swap to `claude-sonnet-5`
via `LLM_MODEL` in `.env` for harder queries. The default persona (in `config.py`)
is tuned for speech: plain text, one to three short sentences, no markdown.

**Swap the brain to Gemini** (optional) — set `LLM_PROVIDER=gemini`, add
`GEMINI_API_KEY` to `.env`, and `pip install google-genai`. Everything else is
unchanged (same interface). Get a key at aistudio.google.com; confirm
`GEMINI_MODEL` names a model your key can access.

---

## Tests

```bash
# Unit tests — no Docker, no API keys, no network
pytest tests/unit -v

# Everything
pytest -v
```

Unit tests cover the text-preprocessing pipeline and the TTS service orchestration
(caching, fallback, error handling) using fakes — they run anywhere.

---

## Project layout

```
app/
  config.py            # all settings from .env (one source of truth)
  main.py              # FastAPI app
  routers/             # HTTP layer (health, tts)
  services/tts/        # TTS: interface, providers, factory, orchestration
  utils/               # text preprocessing, audio, file lifecycle
scripts/               # CLI test tools
tests/                 # unit + integration
docs/ARCHITECTURE.md   # full design + roadmap
docker-compose.yml     # Coqui TTS + Redis + Postgres
```

Design rule: **high cohesion, low coupling.** Each provider does one thing; nothing
outside a service package imports a concrete provider — the factory selects it from
config, so any provider swaps with a one-line change.
