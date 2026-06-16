import os
import json
import logging
from typing import AsyncGenerator

from openai import OpenAI

logger = logging.getLogger(__name__)

OPENROUTER_BASE = "https://openrouter.ai/api/v1"

MODELS_OPENROUTER = [
    "meta-llama/llama-3.3-70b-instruct",
    "mistralai/mistral-7b-instruct",
]
MODELS_GROQ = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]


def _get_client():
    or_key = os.environ.get("OPENROUTER_API_KEY")
    if or_key:
        return OpenAI(
            base_url=OPENROUTER_BASE,
            api_key=or_key,
            default_headers={
                "HTTP-Referer": "https://github.com/maruf99khan/Agent_doc",
                "X-Title": "Gonzo AI Agent",
            },
        ), "openrouter"
    gq_key = os.environ.get("GROQ_API_KEY")
    if gq_key:
        return OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=gq_key,
        ), "groq"
    raise RuntimeError(
        "No API key found. Set OPENROUTER_API_KEY or GROQ_API_KEY."
    )


def _get_model(provider):
    env_model = os.environ.get("OPENROUTER_MODEL") or os.environ.get("GROQ_MODEL")
    if env_model:
        return env_model
    if provider == "openrouter":
        return MODELS_OPENROUTER[0]
    return MODELS_GROQ[0]


def _build_messages(message: str, history: list[dict], system_extra: str = "") -> list[dict]:
    system = (
        "You are Gonzo, a helpful conversational AI. You respond naturally and helpfully. "
        "Format responses in Markdown."
    )
    if system_extra:
        system += f"\n\n{system_extra}"
    messages = [{"role": "system", "content": system}]
    for h in history[-20:]:
        role = "user" if h.get("role") != "assistant" else "assistant"
        messages.append({"role": role, "content": h.get("content", "")})
    messages.append({"role": "user", "content": message})
    return messages


async def chat_stream(
    message: str,
    history: list[dict],
    system_extra: str = "",
) -> AsyncGenerator[str, None]:
    try:
        client, provider = _get_client()
    except RuntimeError as e:
        yield json.dumps({"type": "error", "content": str(e)})
        return

    model = _get_model(provider)
    messages = _build_messages(message, history, system_extra)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=4096,
            stream=True,
        )

        for chunk in response:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield json.dumps({"type": "text", "content": delta.content})

        yield json.dumps({"type": "done"})

    except Exception as e:
        logger.error(f"AI chat failed: {e}", exc_info=True)
        err = str(e).lower()
        if "rate_limit" in err:
            yield json.dumps({"type": "error", "content": "Rate limited. Wait a moment and retry."})
        elif "insufficient_quota" in err:
            yield json.dumps({"type": "error", "content": "API quota exceeded or key invalid."})
        else:
            yield json.dumps({"type": "error", "content": f"AI error: {str(e)[:200]}"})
