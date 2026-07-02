"""LLM provider factory + fallback chain.

The single place that decides which brain the app uses. Everything else depends on
the `LLMProvider` interface, never a concrete class.

Default behaviour is a **priority chain**: Claude first, Gemini as fallback. The
fallback answers when the primary has no API key configured, or when the primary
call fails at runtime (bad key, rate limit, outage). The returned
`LLMResponse.provider` tells you which one actually answered.

Provider modules are imported lazily and missing SDKs are tolerated, so you only
need the SDK(s) for the provider(s) you actually have keys for.
"""

from app.config import Settings, settings
from app.services.llm.base import LLMProvider
from app.services.llm.fallback import FallbackLLMProvider


def _build_one(name: str, cfg: Settings) -> LLMProvider | None:
    """Build a single provider by name. Returns None if its SDK isn't installed."""
    name = name.strip().lower()
    if not name:
        return None
    try:
        if name == "gemini":
            from app.services.llm.gemini import GeminiLLM

            return GeminiLLM(
                api_key=cfg.gemini_api_key,
                model=cfg.gemini_model,
                max_tokens=cfg.llm_max_tokens,
                temperature=cfg.llm_temperature,
            )
        if name == "claude":
            from app.services.llm.claude import ClaudeLLM

            return ClaudeLLM(
                api_key=cfg.anthropic_api_key,
                model=cfg.llm_model,
                max_tokens=cfg.llm_max_tokens,
                temperature=cfg.llm_temperature,
            )
    except ImportError:
        # SDK for this provider not installed — treat it as unavailable.
        return None
    raise ValueError(f"Unknown LLM provider: {name!r}")


def create_llm_provider(cfg: Settings = settings) -> LLMProvider:
    """Build the configured LLM provider (a fallback chain by default)."""
    primary = _build_one(cfg.llm_provider, cfg)

    fallback = None
    fb_name = cfg.llm_fallback_provider.strip().lower()
    if fb_name and fb_name != cfg.llm_provider.strip().lower():
        fallback = _build_one(fb_name, cfg)

    if primary and fallback:
        return FallbackLLMProvider(primary, fallback)
    if primary:
        return primary
    if fallback:
        return fallback
    raise RuntimeError(
        "No LLM provider available — install `anthropic` and/or `google-genai` "
        "and set the matching API key in .env"
    )
