"""LLM provider factory.

The single place that decides which concrete brain the app uses. Everything else
depends on the `LLMProvider` interface, never a concrete class — so swapping Claude
for another provider (or changing the model tier) is a one-line change here.
"""

from app.config import Settings, settings
from app.services.llm.base import LLMProvider


def create_llm_provider(cfg: Settings = settings) -> LLMProvider:
    """Build the configured LLM provider (Claude by default, Gemini optional).

    Provider modules are imported lazily inside each branch so you only need the
    SDK for the provider you actually use — a Gemini user doesn't need `anthropic`
    installed, and a Claude user doesn't need `google-genai`.
    """
    provider = cfg.llm_provider.lower()

    if provider == "gemini":
        from app.services.llm.gemini import GeminiLLM

        return GeminiLLM(
            api_key=cfg.gemini_api_key,
            model=cfg.gemini_model,
            max_tokens=cfg.llm_max_tokens,
            temperature=cfg.llm_temperature,
        )

    # default: Claude
    from app.services.llm.claude import ClaudeLLM

    return ClaudeLLM(
        api_key=cfg.anthropic_api_key,
        model=cfg.llm_model,
        max_tokens=cfg.llm_max_tokens,
        temperature=cfg.llm_temperature,
    )
