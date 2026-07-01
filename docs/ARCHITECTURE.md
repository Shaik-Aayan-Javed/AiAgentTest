# AI Voice Assistant — Project Documentation

> Last updated: 2026-07-01
> Status: In development — Phase 1 (foundation) and Phase 2 (TTS module) built

---

## Architecture Updates

Decisions refined after the initial draft. Where the sections below still name the
original providers, these supersede them:

| Area | Original | Current | Why |
|------|----------|---------|-----|
| **TTS** | Kokoro TTS (generic voice) | **Coqui XTTS-v2** (self-hosted, Docker) | Coqui clones the owner's own voice from a short sample — a core requirement Kokoro can't meet. Still free, still self-hosted, still swappable (gTTS fallback wired in; ElevenLabs for production). |
| **STT** | Deepgram (paid API) | **Whisper self-hosted (primary) + Deepgram (optional)** | Whisper runs on our own machine at $0 and keeps audio private. Deepgram stays as a config-selectable provider behind the same `STTProvider` interface for when its ~300ms streaming latency is worth paying for. |
| **LLM** | Groq / Llama (prototype) | **Claude from day one** | Consistency between prototype and production; the tiered system keeps LLM cost negligible. |

The clean split: **STT (Whisper) and TTS (Coqui) are self-hosted and free; only the
reasoning brain (Claude) is a paid API.** Every provider sits behind an interface
selected by a factory, so swapping any one is a single config change.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [What We Are Building](#2-what-we-are-building)
3. [Prototype Scope](#3-prototype-scope)
4. [System Architecture](#4-system-architecture)
5. [Call Flow Paths](#5-call-flow-paths)
6. [Tiered Response System](#6-tiered-response-system)
7. [Tech Stack](#7-tech-stack)
8. [Requirements](#8-requirements)
9. [Data Models](#9-data-models)
10. [API Surface](#10-api-surface)
11. [Folder Structure](#11-folder-structure)
12. [Environment Variables](#12-environment-variables)
13. [Token Economics & Cost](#13-token-economics--cost)
14. [Build Roadmap](#14-build-roadmap)
15. [Future Developments](#15-future-developments)

---

## 1. Project Overview

An AI-powered virtual voice assistant that answers incoming phone calls, handles caller questions autonomously, and escalates to the human owner when needed. Modelled after the IVR systems used by banks and airlines — but smarter, conversational, and fully owned by you.

The system runs as a backend service. The owner's published phone number is a Twilio number. Calls are handled by an AI pipeline and only reach the owner when necessary.

---

## 2. What We Are Building

### Core Behaviour
- Answers incoming calls on your behalf
- Speaks naturally to callers using AI-generated voice
- Understands and responds to questions using a 3-tier intelligence system
- Sends you an SMS summary after every call
- Escalates to you automatically when out of scope
- Lets you take over any call manually at any time

### What Makes This Different From a Standard IVR
- No rigid menu trees ("Press 1 for billing, Press 2 for support")
- Free-form natural conversation — callers speak normally
- Context retained across the entire call
- Learns from FAQ additions without redeployment
- Owner is always in control with full override capability

---

## 3. Prototype Scope

### In Scope
- Single owner (you), single Twilio number
- AI answers, handles, escalates, summarises
- 3-path call flow (see Section 5)
- Tiered response: FAQ → Semantic Search → Claude AI
- SMS notification + summary after every call
- Full call transcript stored and accessible via link
- Manual takeover via dedicated takeover number
- Auto-escalation when AI detects out-of-scope question

### Out of Scope (Prototype)
- React PWA supervisor dashboard (Production: Option C)
- WebRTC browser-based calls
- Voice biometrics / caller authentication
- Multiple concurrent owner accounts
- Admin UI (use GET /calls API directly)
- Call recording audio file storage
- Whisper mode (owner talks, AI hears, caller doesn't)
- Multi-language support
- CRM integration

---

## 4. System Architecture

```
PUBLISHED NUMBER: Twilio Phone Number
          │
          │  Caller dials
          ▼
┌─────────────────────────────────────────────────────┐
│                    TWILIO                           │
│  - Manages call lifecycle                           │
│  - Rings owner mobile (5s)                         │
│  - Hosts conference room                           │
│  - Streams audio via WebSocket (Media Streams)     │
│  - Sends SMS notifications                         │
└────────────────────┬────────────────────────────────┘
                     │ Webhooks (HTTP POST)
                     │ Audio Stream (WebSocket)
                     ▼
┌─────────────────────────────────────────────────────┐
│                 FASTAPI SERVER                      │
│                  (Fly.io)                           │
│                                                     │
│  ┌─────────────┐    ┌──────────────────────────┐   │
│  │   Routers   │    │        Services           │   │
│  │  /webhooks  │───▶│  call_manager.py          │   │
│  │  /admin     │    │  tier_system.py           │   │
│  │  /ws        │    │  escalation.py            │   │
│  └─────────────┘    │  summary.py               │   │
│                     └──────────────────────────-┘   │
└──────┬──────────────────────┬───────────────────────┘
       │                      │
       │                      │
┌──────▼──────┐    ┌──────────▼──────────────────────┐
│    REDIS    │    │         AI PIPELINE              │
│  (Upstash)  │    │                                  │
│  - Sessions │    │  Deepgram  →  STT transcript     │
│  - Cache    │    │  Tier 1    →  FAQ keyword match  │
│  - Job queue│    │  Tier 2    →  pgvector search    │
└─────────────┘    │  Tier 3    →  Claude Haiku 4.5   │
                   │  Kokoro    →  TTS audio           │
┌─────────────┐    └──────────────────────────────────┘
│  POSTGRESQL │
│  (Supabase) │
│  - Calls    │
│  - Transcripts│
│  - FAQs     │
│  - Cache    │
└─────────────┘
```

---

## 5. Call Flow Paths

### The 5-Second Ring Window

Every call begins identically from the caller's perspective — they hear a ring tone. Internally, Twilio is simultaneously ringing the owner's mobile for 5 seconds while the caller hears the ring.

```
Caller dials Twilio number
        │
        │  Caller hears: ring tone (always)
        │  Twilio dials owner mobile silently
        │
        ├── Owner accepts within 5s ──────────────▶ PATH 1
        │
        ├── Owner declines within 5s ─────────────▶ PATH 0
        │
        └── No action after 5s ───────────────────▶ PATH 2 or 3
```

---

### PATH 0 — Owner Declines (Silent Dismiss)

```
Owner presses decline on their phone
        │
        ▼
Caller continues hearing ring tone
        │
        ▼
Caller eventually gives up and hangs up
        │
        ▼
No AI involvement. No voicemail. No summary.
Caller has no indication the call was seen.
```

---

### PATH 1 — Owner Accepts Directly

```
Owner accepts the 5s ring
        │
        ▼
Owner ↔ Caller connected directly
(AI is never involved)
        │
        ▼
Owner hangs up
        │
        ▼
Call ends
        │
        ▼
SMS summary sent to owner:
  📞 Call Summary
  From: +1-555-XXX-XXXX
  Duration: 4m 12s
  Outcome: ✅ You answered directly
  Transcript: [not available — AI was not on this call]
```

---

### PATH 2 — AI Handles and Resolves

```
5 seconds pass, no owner action
        │
        ▼
AI picks up seamlessly
(Caller hears no gap — ring becomes answer)
        │
        ▼
Owner receives SMS:
  "Active call from +1-555-XXX. Call [takeover-number] to join."
        │
        ▼
AI HANDLING LOOP:
  Caller speaks
        │
        ▼
  Deepgram STT → transcript
        │
        ▼
  Tier 1: FAQ keyword match
     ├── Match found → return pre-written answer (0 tokens)
     └── No match ──▶ Tier 2
        │
  Tier 2: pgvector semantic search (similarity ≥ 0.75)
     ├── Match found → return pre-written answer (0 tokens)
     └── No match ──▶ Tier 3
        │
  Tier 3: Claude Haiku 4.5
     └── Generates response (~$0.0006 per 100 words)
        │
        ▼
  Kokoro TTS converts response to audio
        │
        ▼
  Twilio plays audio to caller
        │
        ▼
  [loop until resolved]
        │
        ▼
AI determines call is complete
("Is there anything else I can help you with?")
        │
        ▼
AI delivers closing line
        │
        ▼
Twilio hangs up
        │
        ▼
Transcript saved to PostgreSQL
        │
        ▼
SMS summary sent to owner:
  📞 Call Summary
  ────────────────
  From: +1-555-234-5678
  Duration: 3m 42s
  Outcome: ✅ AI Resolved

  What they wanted:
  • Asked about business hours
  • Requested callback number
  • Confirmed appointment for Thursday

  Transcript:
  https://your-app.fly.dev/calls/abc123
```

---

### PATH 3 — Owner Takeover (Auto or Manual)

Both triggers lead to the same unified state: owner connected to caller, AI out.

```
TRIGGER A — AUTO (AI detects out of scope)
  AI confidence below threshold
  OR caller says: "speak to a person / manager / human"
  OR same question asked 3 times without resolution
        │
        ▼
  AI says: "Let me connect you with someone who can help."
  Caller placed on hold (hold music)
  Twilio calls owner's mobile
  Owner picks up → connected to caller

TRIGGER B — MANUAL (owner initiates)
  Owner receives "active call" SMS with takeover number
  Owner calls takeover number at any point during the call
  FastAPI identifies owner number → adds to conference
  AI immediately mutes and drops off
  Owner is live with caller
        │
        ▼ (both triggers reach same state)

UNIFIED OWNER TAKEOVER STATE
  Owner ↔ Caller
  AI is completely out of the call
  Full transcript of AI portion saved up to this point
        │
        ▼
Owner hangs up
        │
        ▼
Call ends for caller
        │
        ▼
Transcript saved (AI portion + owner takeover flagged)
        │
        ▼
SMS summary sent to owner:
  📞 Call Summary
  ────────────────
  From: +1-555-234-5678
  Duration: 5m 18s (AI: 2m 10s, You: 3m 08s)
  Outcome: 🔀 Transferred to You
  Trigger: Out of scope — contract negotiation question

  What AI handled:
  • Confirmed caller identity
  • Answered 2 FAQ questions

  What triggered transfer:
  • "Can you renegotiate my pricing?"

  Transcript:
  https://your-app.fly.dev/calls/abc124
```

---

## 6. Tiered Response System

The AI API is called only as a last resort. This reduces token costs by ~80% and significantly lowers response latency for common questions.

```
Caller message
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│  TIER 1 — FAQ Keyword / Intent Match                   │
│  Cost: $0    Latency: ~5ms                             │
│                                                         │
│  Checks caller message against stored FAQ triggers:    │
│  ["hours", "open", "close"] → "We're open 9am–6pm"    │
│  ["price", "cost", "fee"]   → "Plans start at $29/mo" │
│                                                         │
│  Match found? ─── YES ──▶ Return answer, skip Tier 2/3 │
│                  NO  ──▶ Continue to Tier 2            │
└─────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│  TIER 2 — Semantic Vector Search (pgvector)            │
│  Cost: ~$0   Latency: ~50ms                            │
│                                                         │
│  Converts caller message to embedding vector           │
│  Compares against all FAQ question embeddings          │
│  Uses cosine similarity scoring                        │
│                                                         │
│  "When do you guys shut down?"                         │
│  → similar to "What are your business hours?" (0.94)  │
│  → return pre-written answer                           │
│                                                         │
│  Score ≥ 0.75? ─ YES ──▶ Return answer, skip Tier 3   │
│                  NO  ──▶ Continue to Tier 3            │
└─────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│  TIER 3 — Claude Haiku 4.5                             │
│  Cost: ~$0.0006/100 words    Latency: ~800ms           │
│                                                         │
│  Full LLM reasoning                                    │
│  Conversation history included as context              │
│  Can ask clarifying questions                          │
│  Can detect out-of-scope and trigger escalation        │
│                                                         │
│  Response generated → cached in Redis for future hits  │
└─────────────────────────────────────────────────────────┘
```

### Response Caching (Cross-Call)
When Tier 3 generates a response, it is cached in Redis keyed by a hash of the normalised query. Future callers asking similar questions hit the cache and skip the LLM entirely.

### Estimated Tier Distribution
| Tier | % of Calls | Token Cost |
|------|-----------|------------|
| Tier 1 — FAQ Match | ~50% | $0 |
| Tier 2 — Semantic | ~30% | $0 |
| Tier 3 — Claude | ~20% | ~$0.004/call |

---

## 7. Tech Stack

### Why Each Technology Was Chosen

| Layer | Technology | Reason |
|-------|-----------|--------|
| **Phone / Calls** | Twilio | Only provider with full feature set: conferences, warm transfers, Media Streams WebSocket, SMS, and Voice SDK for future WebRTC. Nothing is ripped out when going to production. |
| **Speech-to-Text** | Whisper (self-hosted, primary) · Deepgram (optional) | Whisper (faster-whisper) runs on our own server at $0, audio never leaves the machine. Deepgram kept behind the same `STTProvider` interface for its ~300ms streaming latency when needed — one config change to switch. |
| **LLM** | Claude Haiku 4.5 | Best instruction-following for slot-filling and escalation logic. Consistent behaviour from prototype to production. Only pays for ~20% of calls due to tiered system. |
| **Text-to-Speech** | Coqui XTTS-v2 (self-hosted, Docker) · gTTS (fallback) | Clones the owner's voice from a short sample. Free, runs locally in Docker. gTTS is the zero-setup fallback if Coqui is down. Swappable to ElevenLabs/Cartesia for production with one file change. |
| **Backend Framework** | Python 3.11 + FastAPI | Async by default for concurrent calls. Best AI/voice SDK ecosystem. WebSocket support built-in for Twilio Media Streams. |
| **Job Queue** | ARQ (async Redis queue) | Lightweight, async, Redis-backed. Handles post-call summary generation without blocking the call handler. Scales to production without switching to Celery. |
| **Session State** | Redis (Upstash free tier) | In-memory, sub-millisecond reads. Active call sessions, response cache, job queue all share one Redis instance. |
| **Database** | PostgreSQL (Supabase free tier) | Stores call logs, transcripts, FAQs, cache. pgvector extension enables semantic search without a separate vector database. |
| **Embeddings** | sentence-transformers (local) | Runs on CPU, completely free. `all-MiniLM-L6-v2` model. Generates embeddings for FAQ semantic search. |
| **Error Tracking** | Sentry (free tier) | Catches and reports errors in both prototype and production. One SDK, no config change needed. |
| **Deployment** | Fly.io (free tier) | Always-on server (unlike Render which sleeps). Twilio requires a live HTTPS endpoint 24/7. Free tier supports this. |
| **Notifications** | Twilio SMS | Already in the stack. No extra service needed for SMS summaries. |

### Prototype → Production Swap Points

The following are the ONLY things that change. Everything else is identical.

| Component | Prototype | Production |
|-----------|-----------|------------|
| LLM (complex) | Claude Haiku 4.5 | Claude Sonnet 5 |
| TTS | Coqui XTTS-v2 (Docker) | ElevenLabs / Cartesia (streaming) |
| STT | Whisper (self-hosted) | Whisper GPU / Deepgram |
| Database | Supabase free | Supabase Pro / self-hosted |
| Redis | Upstash free | Upstash Pro / self-hosted |
| Deployment | Fly.io free | Fly.io paid / AWS |
| Frontend | None | React PWA (see Future) |
| Notifications | Twilio SMS | Twilio SMS + Firebase FCM |

---

## 8. Requirements

### 8.1 Accounts to Create

| Service | Purpose | URL | Cost |
|---------|---------|-----|------|
| Twilio | Calls, SMS, conference | twilio.com | Free ($15 trial credit) |
| Deepgram | Real-time STT | deepgram.com | Free ($200 credit) |
| Anthropic | Claude Haiku 4.5 API | console.anthropic.com | Pay-per-use (~$0.004/call) |
| Supabase | PostgreSQL + pgvector | supabase.com | Free tier |
| Upstash | Redis | upstash.com | Free tier |
| Fly.io | Deployment | fly.io | Free tier |
| Sentry | Error tracking | sentry.io | Free tier |
| Firebase | Push notifications (production only) | firebase.google.com | Free tier |

### 8.2 Local Tools to Install

| Tool | Purpose | Install |
|------|---------|---------|
| Python 3.11+ | Backend runtime | python.org |
| Docker Desktop | Run Kokoro TTS locally | docker.com |
| ngrok | Expose local server to Twilio (dev only) | ngrok.com |
| Git | Version control | git-scm.com |
| Node.js 20+ | Frontend build (production only) | nodejs.org |

### 8.3 Python Packages

```
fastapi              # Web framework
uvicorn              # ASGI server
twilio               # Twilio SDK
deepgram-sdk         # Deepgram STT
anthropic            # Claude API
sqlalchemy           # ORM (async)
asyncpg              # PostgreSQL async driver
alembic              # Database migrations
redis                # Redis client
arq                  # Async job queue
sentry-sdk           # Error tracking
httpx                # Async HTTP client
python-dotenv        # Environment variable loading
websockets           # WebSocket client (Twilio Media Streams)
pydantic             # Data validation
sentence-transformers # Local embedding model (Tier 2)
pgvector             # pgvector Python client
```

### 8.4 MCPs Required

MCPs are tools used by Claude Code (the AI developer assistant) to help build this project. They are NOT part of the application itself.

| MCP | Purpose | Priority |
|-----|---------|----------|
| **GitHub MCP** | Push code to `github.com/Shaik-Aayan-Javed/AiAgentTest`, create branches and PRs | Critical — needed before coding starts |
| **claude-in-chrome** | Test the admin API and transcript links in a real browser | Important |
| **computer-use** | Take screenshots of the running app, verify behaviour visually | Useful |

**To connect GitHub MCP:**
Go to Claude Code settings → MCP Servers → Add GitHub MCP with your personal access token (needs `repo` scope).

**Note:** The application itself (FastAPI server) communicates with Twilio, Deepgram, and Claude directly via their SDKs — not through MCPs. MCPs are exclusively for the development workflow.

### 8.5 Phone Setup

1. Get a Twilio phone number (from Twilio console, free with trial)
2. This number becomes your published contact number
3. Share the Twilio number — not your personal number — going forward
4. Your personal mobile number is registered privately as `OWNER_PHONE_NUMBER` in environment variables
5. Twilio rings your personal mobile for 5 seconds before AI picks up

---

## 9. Data Models

### calls
```sql
CREATE TABLE calls (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_sid        VARCHAR(64) UNIQUE NOT NULL,   -- Twilio Call SID
    caller_number   VARCHAR(20) NOT NULL,
    outcome         VARCHAR(20) NOT NULL,           -- ai_resolved | owner_direct | transferred | manual_override | dismissed
    started_at      TIMESTAMPTZ NOT NULL,
    ended_at        TIMESTAMPTZ,
    duration_seconds INTEGER,
    ai_duration_seconds INTEGER,                   -- time AI was active
    trigger_reason  TEXT,                          -- why escalation happened (if applicable)
    summary_text    TEXT,                          -- bullet summary for SMS
    tier_breakdown  JSONB,                         -- {"tier1": 3, "tier2": 1, "tier3": 2}
    created_at      TIMESTAMPTZ DEFAULT now()
);
```

### transcripts
```sql
CREATE TABLE transcripts (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id     UUID REFERENCES calls(id) ON DELETE CASCADE,
    speaker     VARCHAR(10) NOT NULL,   -- caller | ai | owner
    text        TEXT NOT NULL,
    tier_used   SMALLINT,               -- 1, 2, 3, or NULL (for owner/caller lines)
    timestamp   TIMESTAMPTZ NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT now()
);
```

### faqs
```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE faqs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    intent      VARCHAR(64) NOT NULL,
    triggers    TEXT[] NOT NULL,       -- keyword array for Tier 1
    answer      TEXT NOT NULL,
    embedding   vector(384),           -- sentence-transformers embedding for Tier 2
    active      BOOLEAN DEFAULT true,
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX ON faqs USING ivfflat (embedding vector_cosine_ops);
```

### response_cache
```sql
CREATE TABLE response_cache (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_hash      VARCHAR(64) UNIQUE NOT NULL,
    query_text      TEXT NOT NULL,
    response_text   TEXT NOT NULL,
    hit_count       INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT now()
);
```

---

## 10. API Surface

### Twilio Webhooks (called by Twilio)
```
POST /webhooks/incoming-call        Triggered when call arrives
POST /webhooks/dial-outcome         Triggered after 5s ring (owner answered / no answer)
POST /webhooks/call-status          Triggered on call state changes (ringing, in-progress, completed)
POST /webhooks/takeover             Triggered when owner calls the takeover number
WS   /webhooks/media-stream/{sid}   Real-time audio stream from Twilio
```

### Internal Endpoints (called by FastAPI itself)
```
POST /internal/escalate/{call_sid}  Trigger auto-escalation (transfer to owner)
POST /internal/hangup/{call_sid}    AI-initiated hang up after resolution
```

### Admin Endpoints (for owner to query)
```
GET  /calls                         List all calls (paginated)
GET  /calls/{id}                    Full call detail
GET  /calls/{id}/transcript         Full transcript as JSON
GET  /calls/stats                   Summary stats (resolution rate, avg duration, tier breakdown)
```

---

## 11. Folder Structure

```
AiAgentTest/
│
├── app/
│   ├── main.py                    # FastAPI app init, router registration, lifespan events
│   ├── config.py                  # All settings loaded from environment variables
│   │
│   ├── routers/
│   │   ├── webhooks.py            # All Twilio webhook handlers
│   │   └── admin.py               # Call history + transcript endpoints
│   │
│   ├── services/
│   │   ├── tts/                   # ── BUILT (Phase 2) ──
│   │   │   ├── base.py            # TTSProvider interface + AudioResult
│   │   │   ├── coqui.py           # Coqui XTTS-v2 (primary, voice cloning)
│   │   │   ├── gtts_provider.py   # gTTS (fallback)
│   │   │   ├── factory.py         # provider selection + fallback chain — SWAP POINT
│   │   │   └── service.py         # orchestration: preprocess, cache, save
│   │   ├── stt/                   # ── Phase 3 ──
│   │   │   ├── base.py            # STTProvider interface
│   │   │   ├── whisper.py         # faster-whisper (primary, self-hosted)
│   │   │   ├── deepgram.py        # Deepgram (optional) — SWAP POINT
│   │   │   └── factory.py         # provider selection
│   │   ├── llm.py                 # Claude Haiku 4.5 — SWAP POINT (Haiku → Sonnet)
│   │   ├── tier_system.py         # Orchestrates Tier 1 → 2 → 3 response selection
│   │   ├── faq.py                 # FAQ store CRUD + pgvector semantic search
│   │   ├── call_manager.py        # Redis session: create, read, update, delete
│   │   ├── escalation.py          # Auto-escalation + manual takeover logic
│   │   └── summary.py             # Post-call summary generation + SMS dispatch
│   │
│   ├── models/
│   │   ├── call.py                # SQLAlchemy: calls + transcripts tables
│   │   └── faq.py                 # SQLAlchemy: faqs + response_cache tables
│   │
│   └── ws/
│       └── media_stream.py        # WebSocket handler for Twilio Media Streams audio
│
├── workers/
│   └── tasks.py                   # ARQ background jobs: summary generation, SMS send
│
├── tests/
│   ├── test_tier_system.py        # Unit tests for FAQ/semantic/LLM routing
│   ├── test_escalation.py         # Tests for auto + manual takeover logic
│   ├── test_webhooks.py           # Integration tests for Twilio webhook handlers
│   └── conftest.py                # Shared fixtures
│
├── docs/
│   └── ARCHITECTURE.md            # This file
│
├── docker-compose.yml             # Kokoro TTS + local PostgreSQL + local Redis
├── fly.toml                       # Fly.io deployment configuration
├── alembic.ini                    # Database migration config
├── alembic/                       # Migration scripts
├── requirements.txt               # Python dependencies
├── .env.example                   # Template for environment variables
└── .gitignore
```

---

## 12. Environment Variables

```bash
# ─── Twilio ───────────────────────────────────────────
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_PHONE_NUMBER=+1XXXXXXXXXX       # Your Twilio number (published number)
OWNER_PHONE_NUMBER=+1XXXXXXXXXX        # Your real personal mobile (private)
TAKEOVER_PHONE_NUMBER=+1XXXXXXXXXX     # Separate Twilio number for manual override

# ─── AI Services ──────────────────────────────────────
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxx  # Claude Haiku 4.5
DEEPGRAM_API_KEY=xxxxxxxxxxxxxxxx      # Real-time STT

# ─── TTS ──────────────────────────────────────────────
KOKORO_TTS_URL=http://localhost:8880   # Local Docker container (dev)
                                        # http://kokoro:8880 (Docker Compose)

# ─── Data ─────────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname   # Supabase
REDIS_URL=rediss://default:xxxx@host:6380                 # Upstash

# ─── Application ──────────────────────────────────────
SERVER_URL=https://xxxx.ngrok.io       # Dev: ngrok URL
                                        # Prod: https://your-app.fly.dev
SEMANTIC_MATCH_THRESHOLD=0.75          # Tier 2 minimum confidence (0.0–1.0)
ESCALATION_CONFIDENCE_THRESHOLD=0.50   # Below this, auto-escalate to owner
MAX_CALL_TURNS=20                      # Safety limit before forced escalation

# ─── Monitoring ───────────────────────────────────────
SENTRY_DSN=https://xxxx@sentry.io/xxxx

# ─── Environment ──────────────────────────────────────
ENVIRONMENT=development                # development | production
```

---

## 13. Token Economics & Cost

### Token Ratio
```
100 words ≈ 133 tokens
```

### Claude Haiku 4.5 Pricing
| Direction | Rate | Cost per 100 words |
|-----------|------|-------------------|
| Input (caller's words to Claude) | $0.80 / 1M tokens | $0.0001 |
| Output (Claude's response) | $4.00 / 1M tokens | $0.0005 |
| **Combined per 100 words of dialogue** | | **$0.0006** |

### Context Accumulation
Claude receives the full conversation history on every turn. A 5-turn call:
```
Turn 1: 350 tokens sent
Turn 2: 475 tokens sent  (includes Turn 1 history)
Turn 3: 600 tokens sent
Turn 4: 725 tokens sent
Turn 5: 850 tokens sent
─────────────────────────
Total:  3,000 input tokens + ~375 output tokens
Cost:   ~$0.004 per fully AI-handled call
```

### Real Cost With Tiered System
Since Claude only handles ~20% of calls:

| Volume | Claude calls | Approx. monthly cost |
|--------|-------------|----------------------|
| 100 test calls | 20 | ~$0.08 |
| 1,000 calls | 200 | ~$0.80 |
| 10,000 calls | 2,000 | ~$8.00 |

### Full Monthly Cost Estimate (1,000 calls, ~3 min avg)
| Service | Cost |
|---------|------|
| Twilio (calls + SMS) | ~$15.00 |
| Deepgram STT | ~$12.00 |
| Claude Haiku 4.5 (20% of calls) | ~$0.80 |
| Kokoro TTS | $0.00 (self-hosted) |
| Supabase | $0.00 (free tier) |
| Upstash | $0.00 (free tier) |
| Fly.io | $0.00 (free tier) |
| **Total** | **~$27.80 / 1,000 calls** |

---

## 14. Build Roadmap

### Week 1 — Voice Pipeline
| Day | Task |
|-----|------|
| 1–2 | Project scaffold + Twilio webhook + basic TwiML ring/answer |
| 3–4 | Deepgram STT + Twilio Media Streams WebSocket integration |
| 5 | Kokoro TTS + full audio loop (caller speaks → AI responds) |

### Week 2 — Intelligence + Outcomes
| Day | Task |
|-----|------|
| 1–2 | FAQ store + Tier 1 (keyword match) + Tier 2 (pgvector semantic search) |
| 3 | Claude Haiku 4.5 Tier 3 integration |
| 4 | Call resolution detection + AI hang-up + SMS summary |
| 5 | Auto-escalation + warm transfer to owner mobile |

### Week 3 — Control + Polish
| Day | Task |
|-----|------|
| 1–2 | Manual override via takeover number |
| 3 | Call history admin API + transcript storage |
| 4–5 | End-to-end testing on real Twilio number |

### Week 4 — Hardening
| Day | Task |
|-----|------|
| 1 | Error handling + retry logic on all external calls |
| 2 | Sentry integration + structured logging |
| 3 | Deploy to Fly.io (production server) |
| 4 | Test full flow from real mobile device |
| 5 | Bug fixes + FAQ population |

---

## 15. Future Developments

This section describes the full production system (Option C) and beyond. Nothing here conflicts with the prototype architecture — it is all additive.

---

### 15.1 React PWA Supervisor Dashboard (Option C)

A Progressive Web App that runs in your phone's browser. No App Store. Installs like an app.

**Features:**
- Push notification when a call comes in (Firebase FCM)
- Live transcript view — see every word in real time
- AI confidence meter — visual indicator of how certain the AI is
- Tier indicator — shows whether response came from FAQ, semantic, or LLM
- [Take Over] button — instantly mutes AI, connects you to caller
- [End Call] button — terminates call and triggers summary
- [Whisper to AI] — you type/speak, AI incorporates your input, caller doesn't hear you
- Call history with full transcripts
- FAQ management (add/edit/delete FAQ entries)

**Tech additions needed:**
- React + TypeScript frontend
- Twilio Voice SDK (WebRTC for browser-based speaking)
- Firebase FCM for push notifications
- Server-sent events or WebSocket for live transcript streaming to dashboard

---

### 15.2 Whisper Mode

You can speak or type during an active call. The AI hears your input and incorporates it into its next response. The caller never hears you.

**Use case:** You're monitoring a call and realise the AI is about to give wrong information. You type the correct answer. The AI seamlessly delivers it.

**Implementation:** Requires a third audio leg on the Twilio conference with coach mode enabled.

---

### 15.3 LLM Upgrade Path

| Trigger | Action |
|---------|--------|
| Complex multi-step queries | Escalate within Tier 3 from Haiku to Sonnet |
| Legal / financial questions | Route to Sonnet automatically |
| High call volume | Keep Haiku for speed, Sonnet for complex only |

One config flag controls the model used per call type. No architecture change.

---

### 15.4 Production TTS — Cartesia

Cartesia supports streaming TTS — audio starts playing to the caller before the full response is generated. This eliminates the 1–2 second pause callers currently experience.

**Swap:** Change `tts.py` only. Everything else unchanged.

---

### 15.5 Caller Authentication

For sensitive use cases (account queries, personal data).

**Layers:**
- PIN verification ("Please enter your 4-digit PIN")
- Last 4 digits of a reference number
- OTP via SMS (Twilio Verify)
- Voice biometrics (future — speaker recognition)

---

### 15.6 CRM Integration

Connect the AI to an existing CRM (HubSpot, Salesforce, Zoho, or custom).

**What it enables:**
- AI can look up caller history by phone number
- Personalised responses ("Hi John, I see you last called about your March invoice")
- Automatic call log creation in CRM after every call
- Follow-up task creation for transferred calls

---

### 15.7 Appointment / Booking Integration

Connect to Google Calendar, Calendly, or a custom booking system.

**What it enables:**
- Caller can book, reschedule, or cancel appointments entirely through AI
- No human involvement for scheduling
- SMS confirmation sent to caller automatically

---

### 15.8 Multi-Language Support

Deepgram supports 30+ languages. Claude is multilingual. Kokoro/Cartesia support multiple languages.

**What's needed:**
- Language detection on first caller utterance (Deepgram)
- Route to language-specific FAQ entries
- System prompt includes language instruction for Claude
- TTS voice selected per language

---

### 15.9 Sentiment Analysis

Detect caller frustration in real time.

**Signals:**
- Repeated questions (3+ times on same topic)
- Short, clipped answers
- Keywords: "ridiculous", "unacceptable", "speak to manager"
- Long silences

**Action:** Escalate sooner, flag call in dashboard with priority alert.

---

### 15.10 Analytics Dashboard

Web dashboard showing:
- Call volume by day / week / month
- Resolution rate (AI vs transferred)
- Average call duration
- Most common call topics (by intent)
- Tier breakdown (% handled by Tier 1 / 2 / 3)
- Escalation triggers (why calls were transferred)
- Token cost per day

**Tech:** FastAPI serves data, React dashboard visualises with charts.

---

### 15.11 Multiple AI Personas

Different voices and personalities for different contexts.

**Examples:**
- Professional formal voice for business calls
- Friendly casual voice for personal calls
- Language-specific persona

Controlled by caller number origin, time of day, or Twilio number called.

---

### 15.12 After-Hours Handling

Config-based business hours.

**After hours behaviour:**
- AI informs caller of business hours
- Offers to take a message (captured in transcript)
- Optionally sends caller an SMS confirmation their message was received

---

### 15.13 SMS / WhatsApp Follow-Up

After a call, AI sends the caller an SMS/WhatsApp:
- Appointment confirmation
- Reference number
- Link to resources mentioned during the call

Requires Twilio WhatsApp Business API for WhatsApp.

---

### 15.14 Multiple Phone Numbers

Run separate AI assistants on separate Twilio numbers.

**Use case:**
- One number for business calls (formal FAQ set)
- One number for a specific project or client
- Each number has its own FAQ database, persona, and escalation rules

All managed from one FastAPI server. Routing determined by `To` number in the Twilio webhook.

---

### 15.15 Raspberry Pi Deployment (Self-Hosted Option)

For full local ownership with zero cloud compute cost.

**What runs on Pi:**
- FastAPI server
- Kokoro TTS
- Redis
- PostgreSQL

**Still requires internet for:**
- Deepgram STT (API)
- Claude API (API)
- Twilio (API)

**Cost:** ~$50 hardware one-time + ~$5/month electricity.

---

## Summary of All Decisions Made

| Decision | Choice | Reason |
|----------|--------|--------|
| Published number | Twilio number | Full programmatic control |
| Owner ring duration | 5 seconds | Enough time to see + decide |
| Decline behaviour | Caller hears ring, no AI, no voicemail | Silent dismiss, owner's choice |
| AI only picks up | After 5s timeout (no owner action) | Owner always has first right of refusal |
| Takeover type | Unified (auto + manual same outcome) | Simpler, more freedom |
| Post-takeover | Call ends completely | Clean, no confusion |
| LLM | Claude Haiku 4.5 from day one | Quality, consistency, negligible cost |
| TTS | Kokoro (self-hosted Docker) | Free, swappable |
| STT | Deepgram (streaming) | Production-ready architecture from prototype |
| Summary delivery | SMS (prototype), SMS + web portal (production) | SMS is instant to build |
| SMS content | Outcome + caller number + bullet summary + transcript link | All the info needed |
| Token optimisation | 3-tier system, ~80% of calls skip LLM | Cost reduction without quality loss |
| Compute | Fly.io free tier | Always-on, free, no config change for production |
| Local alternative | Raspberry Pi 4 | If cloud-free compute is preferred |
