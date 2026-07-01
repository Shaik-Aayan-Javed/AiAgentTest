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

    # TTS — Coqui XTTS-v2 (Docker)
    coqui_tts_url: str = "http://localhost:8020"

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
