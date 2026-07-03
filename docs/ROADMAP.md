# Build Roadmap

Living checklist for the AI voice assistant. Tick items as they land.
See [ARCHITECTURE.md](ARCHITECTURE.md) for the full design.

---

## ✅ Phase 1 — Backend foundation
- [x] `config.py` — all settings from `.env`
- [x] `main.py` — FastAPI app, CORS, static audio
- [x] provider-aware health router (`/api/health`)
- [x] `docker-compose` — Coqui + Redis + PostgreSQL

## ✅ Phase 2 — TTS module
- [x] `tts/base` — interface + `AudioResult`
- [x] `tts/coqui` — voice cloning (primary)
- [x] `tts/gtts_provider` — fallback
- [x] `tts/factory` — selection + auto-fallback chain
- [x] `tts/service` — preprocess, cache, persist
- [x] `utils/text_processor`, `utils/audio`, `utils/file_manager`
- [x] `routers/tts` — `POST /api/tts/synthesize`, `GET /api/tts/voices`
- [x] `scripts/test_tts.py`

## ✅ Phase 3 — STT module + echo loop
- [x] `stt/base` — interface + `TranscriptResult`
- [x] `stt/whisper_provider` — faster-whisper (primary, self-hosted)
- [x] `stt/deepgram` — Deepgram via httpx REST (optional)
- [x] `stt/factory`, `stt/service`
- [x] `routers/stt` — `POST /api/stt/transcribe`
- [x] `scripts/test_stt.py`, `scripts/test_loop.py` (STT→TTS echo)

---

## ✅ Phase 4 — LLM brain (makes it *answer*)
- [x] `llm/base` — interface + `Message` / `LLMResponse`
- [x] `llm/claude` — Claude (Anthropic SDK, `claude-haiku-4-5`)
- [x] `llm/factory` — provider selection
- [x] `llm/service` — system prompt + completion + latency
- [x] `Conversation` — multi-turn context holder
- [x] `routers/chat` — `POST /api/chat`
- [x] `scripts/test_conversation.py` — text REPL + audio pipeline (STT→Claude→TTS)
- [x] unit tests (fakes)

## ▶ Phase 5 — Tiered response + Training backend
- [ ] Tier 1 — FAQ store + CRUD
- [ ] Tier 2 — knowledge base + embeddings (sentence-transformers + pgvector)
- [ ] persona / system-prompt config
- [ ] tier orchestration (FAQ → semantic → Claude)
- [ ] response-tester API (shows tier used, tokens, latency)

---

## ✅ Phase 6 — Frontend shell + Live voice
- [x] React + Vite, dark premium theme (Tailwind)
- [x] Sidebar, Header (live health status), routing, API client
- [x] `POST /api/converse` — one-call voice turn (STT → LLM → TTS)
- [x] **Live panel** — push-to-talk mic → hear the reply (MediaRecorder + auto-play)
- [x] Dashboard panel — provider status cards + quick text ask

## Phase 7 — TTS Lab + STT Lab + Voice Studio panels
- [ ] TTS Lab: text → generate → waveform + play + save
- [ ] STT Lab: upload / record → transcript + confidence
- [ ] Voice Studio: record voice sample, test the cloned voice

## ✅ Phase 8 — Voice Studio
- [x] `POST/GET/DELETE /api/voice/sample` + serve saved sample
- [x] in-browser voice-sample recording (client-side WAV encode)
- [x] sample management (record / play / delete) + cloned-voice test
- [ ] (setup) Coqui running + `TTS_PROVIDER=coqui` to hear the cloned voice

## Phase 9 — Training Center (UI)
- [ ] FAQ manager, knowledge base, persona editor, response tester
- [ ] 🔊 "hear it in your voice" previews

## Phase 10 — Dashboard + polish
- [ ] overview cards, quick test, health widgets, animations, QA

---

## Separate track — Call Handling (the phone product)
Layered on top of everything above. See [ARCHITECTURE.md §14](ARCHITECTURE.md).
- [ ] Twilio webhooks + 5-second ring
- [ ] AI answer loop on a live call
- [ ] auto + manual takeover
- [ ] SMS summaries + transcript storage
