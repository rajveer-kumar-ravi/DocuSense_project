"""Gemini 3 Flash chat via emergentintegrations."""
from __future__ import annotations

import os
import uuid

from emergentintegrations.llm.chat import LlmChat, UserMessage


def _model_name() -> str:
    return os.environ.get("GEMINI_MODEL", "gemini-3-flash-preview")


async def ask(system_prompt: str, user_text: str, session_id: str | None = None) -> str:
    """Single-turn LLM call with given system prompt + user text."""
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise RuntimeError("EMERGENT_LLM_KEY missing")
    chat = LlmChat(
        api_key=api_key,
        session_id=session_id or str(uuid.uuid4()),
        system_message=system_prompt,
    ).with_model("gemini", _model_name())
    resp = await chat.send_message(UserMessage(text=user_text))
    return resp if isinstance(resp, str) else str(resp)
