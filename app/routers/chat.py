"""Chat HTTP API — direct access to the reasoning brain.

Thin layer over LLMService. This is the plain single-completion endpoint (client
passes the history). The tiered FAQ → semantic → Claude routing comes in Phase 5;
this endpoint always goes straight to the LLM.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.llm.base import Message
from app.services.llm.service import get_llm_service

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., min_length=1)


class ChatResponse(BaseModel):
    text: str
    input_tokens: int
    output_tokens: int
    model: str
    provider: str
    latency_ms: int


@router.post("", response_model=ChatResponse, summary="Chat with the AI brain")
async def chat(req: ChatRequest) -> ChatResponse:
    service = get_llm_service()
    messages = [Message(role=m.role, content=m.content) for m in req.messages]
    try:
        reply = await service.reply(messages)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM request failed: {exc}")

    return ChatResponse(
        text=reply.text,
        input_tokens=reply.input_tokens,
        output_tokens=reply.output_tokens,
        model=reply.model,
        provider=reply.provider,
        latency_ms=reply.latency_ms,
    )
