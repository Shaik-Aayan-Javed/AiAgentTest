from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Twilio
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""
    owner_phone_number: str = ""
    takeover_phone_number: str = ""

    # AI services
    anthropic_api_key: str = ""
    deepgram_api_key: str = ""

    # STT — Whisper (primary, self-hosted) | Deepgram (optional)
    stt_provider: str = "whisper"              # "whisper" | "deepgram"
    stt_language: str = ""                     # "" = auto-detect
    whisper_model_size: str = "base"           # tiny | base | small | medium | large
    whisper_device: str = "cpu"                # "cpu" | "cuda"
    whisper_compute_type: str = "int8"         # int8 (CPU) | float16 (GPU)
    deepgram_model: str = "nova-2"

    # TTS — Coqui XTTS-v2 (Docker)
    coqui_tts_url: str = "http://localhost:8020"
    tts_provider: str = "coqui"                # "coqui" | "gtts"
    tts_default_voice: str = "voice_sample"    # speaker name = voice sample filename (no ext)
    tts_language: str = "en"
    tts_fallback_enabled: bool = True          # fall back to gTTS if Coqui fails
    audio_cleanup_max_age_seconds: int = 3600  # prune generated audio older than this

    # Data
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/voiceai"
    redis_url: str = "redis://localhost:6379"

    # Application behaviour
    server_url: str = "http://localhost:8000"
    semantic_match_threshold: float = 0.75
    escalation_confidence_threshold: float = 0.50
    max_call_turns: int = 20

    # Monitoring
    sentry_dsn: str = ""

    # Runtime environment
    environment: str = "development"

    # Voice cloning
    voice_sample_path: str = "assets/voice_sample.wav"


settings = Settings()
