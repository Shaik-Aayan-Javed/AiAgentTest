"""LLM provider factory.

The single place that decides which concrete brain the app uses. Everything else
depends on the `LLMProvider` interface, never a concrete class — so swapping Claude
for another provider (or changing the model tier) is a one-line change here.
"""

from app.config import Settings, settings
from app.services.llm.base import LLMProvider
from app.services.llm.claude import ClaudeLLM
from app.services.llm.gemini import GeminiLLM


def create_llm_provider(cfg: Settings = settings) -> LLMProvider:
    """Build the configured LLM provider (Claude by default, Gemini optional)."""
    provider = cfg.llm_provider.lower()

    if provider == "gemini":
        return GeminiLLM(
            api_key=cfg.gemini_api_key,
            model=cfg.gemini_model,
            max_tokens=cfg.llm_max_tokens,
            temperature=cfg.llm_temperature,
        )

    # default: Claude
    return ClaudeLLM(
        api_key=cfg.anthropic_api_key,
        model=cfg.llm_model,
        max_tokens=cfg.llm_max_tokens,
        temperature=cfg.llm_temperature,
    )
