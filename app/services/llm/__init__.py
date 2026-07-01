"""LLM package.

Only the (dependency-free) interface is re-exported here so importing the package
does not pull in provider dependencies (anthropic). Import concrete pieces from
their explicit modules:

    from app.services.llm.factory import create_llm_provider
    from app.services.llm.service import get_llm_service, LLMService, Conversation
"""

from app.services.llm.base import LLMProvider, LLMResponse, Message

__all__ = ["LLMProvider", "LLMResponse", "Message"]
