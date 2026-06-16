import os
import json
import logging
from typing import AsyncGenerator

from openai import OpenAI

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "llama-3.3-70b-versatile"
FALLBACK_MODEL = "llama-3.1-8b-instant"


def _get_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Groq API key not set. Get a free key at https://console.groq.com/keys "
            "and set the GROQ_API_KEY environment variable."
        )
    return OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=api_key,
    )


def _get_model():
    return os.environ.get("GROQ_MODEL", DEFAULT_MODEL)


def _build_messages(message: str, history: list[dict], memory_context: str = "") -> list[dict]:
    system = (
        "You are Gonzo — a raw, direct AI research and document agent. "
        "Your purpose: research topics, create/edit documents (PDF, DOCX, TXT), "
        "analyze uploaded files, gather information from web and file content, and summarize. "
        "When you search the web or fetch pages, cite sources clearly. "
        "When you create or write files, tell the user the filename. "
        "Format responses in Markdown for readability.\n\n"
        "Rules:\n"
        "- Be thorough but concise — direct answers, no fluff\n"
    )
    if memory_context:
        system += f"\n## What I know about the user\n{memory_context}\n"

    messages = [{"role": "system", "content": system}]

    for h in history[-20:]:
        role = h.get("role", "user")
        if role == "assistant":
            messages.append({"role": "assistant", "content": h.get("content", "")})
        else:
            messages.append({"role": "user", "content": h.get("content", "")})

    messages.append({"role": "user", "content": message})
    return messages


def _build_tools(tool_defs: list[dict]) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t.get("parameters", {}),
            }
        }
        for t in tool_defs
    ]


async def chat_stream(
    message: str,
    history: list[dict],
    tool_map: dict,
    memory_context: str = "",
) -> AsyncGenerator[str, None]:
    model = _get_model()

    try:
        client = _get_client()
    except RuntimeError as e:
        yield json.dumps({"type": "error", "content": str(e)})
        return

    messages = _build_messages(message, history, memory_context)
    tools = _build_tools(tool_map.get("definitions", []))

    try:
        # Phase 1: Tool-calling loop (non-streaming)
        while True:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None,
                temperature=0.7,
                max_tokens=4096,
            )

            choice = response.choices[0]
            msg = choice.message

            if not tools or not msg.tool_calls:
                # Phase 2: Stream the final text
                if msg.content:
                    yield json.dumps({"type": "text", "content": msg.content})
                break

            for tc in msg.tool_calls:
                fn_name = tc.function.name
                try:
                    fn_args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    fn_args = {}

                yield json.dumps({"type": "tool_call", "name": fn_name, "args": fn_args})

                handle_fn = tool_map.get("handle_tool")
                if handle_fn:
                    result_str, created_file = await handle_fn(fn_name, fn_args)
                else:
                    result_str = json.dumps({"error": "No handler"})
                    created_file = None

                messages.append(msg)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result_str[:5000],
                })

                yield json.dumps({
                    "type": "tool_result",
                    "name": fn_name,
                    "content": result_str[:1500],
                    "file": created_file,
                })

        yield json.dumps({"type": "done"})

    except Exception as e:
        logger.error(f"Groq chat failed: {e}", exc_info=True)
        if "model_not_available" in str(e).lower() or "does not exist" in str(e).lower():
            yield json.dumps({"type": "error", "content": f"Model '{model}' unavailable. Check GROQ_MODEL in .env"})
        elif "rate_limit" in str(e).lower():
            yield json.dumps({"type": "error", "content": "Rate limited by Groq. Wait a moment and retry."})
        else:
            yield json.dumps({"type": "error", "content": f"AI error: {str(e)}"})
