import os
import json
import logging
from typing import AsyncGenerator

from openai import OpenAI

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "mixtral-8x7b-32768"
FALLBACK_MODEL = "llama-3.1-8b-instant"
MAX_TOOL_ROUNDS = 5


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
        "Format responses in Markdown.\n\n"
        "Rules:\n"
        "- Be thorough but concise — direct answers, no fluff\n"
    )
    if memory_context:
        system += f"\n## What I know about the user\n{memory_context}\n"

    messages = [{"role": "system", "content": system}]
    for h in history[-20:]:
        role = h.get("role", "assistant") if h.get("role") == "assistant" else "user"
        messages.append({"role": role, "content": h.get("content", "")})
    messages.append({"role": "user", "content": message})
    return messages


def _build_tools(tool_defs: list[dict]) -> list[dict]:
    result = []
    for t in tool_defs:
        params = t.get("parameters", {})
        if "type" not in params:
            params = {"type": "object", "properties": params.get("properties", {}), **{k: v for k, v in params.items() if k != "properties"}}
        result.append({
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": params,
            }
        })
    return result


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
    tool_rounds = 0

    try:
        while tool_rounds < MAX_TOOL_ROUNDS:
            tool_rounds += 1
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=tools if tools else None,
                    tool_choice="auto" if tools else None,
                    temperature=0.7,
                    max_tokens=4096,
                )
            except Exception as api_err:
                err_str = str(api_err).lower()
                if "tool_use_failed" in err_str or "tool call validation failed" in err_str:
                    yield json.dumps({"type": "text", "content": "I tried to use a tool but there was an issue. Let me respond without tools."})
                    response = client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=0.7,
                        max_tokens=4096,
                    )
                else:
                    raise

            choice = response.choices[0]
            msg = choice.message

            if not msg.tool_calls:
                text = (msg.content or "").strip()
                if not text:
                    text = "Hello! I'm Gonzo. How can I help you today?"
                yield json.dumps({"type": "text", "content": text})
                break

            for tc in msg.tool_calls:
                fn_name = tc.function.name
                try:
                    fn_args = json.loads(tc.function.arguments) if tc.function.arguments else {}
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
                    "content": (result_str or "")[:5000],
                })

                yield json.dumps({
                    "type": "tool_result",
                    "name": fn_name,
                    "content": (result_str or "")[:1500],
                    "file": created_file,
                })

        if tool_rounds >= MAX_TOOL_ROUNDS:
            yield json.dumps({"type": "text", "content": "I've completed all the operations. What would you like to do next?"})

        yield json.dumps({"type": "done"})

    except Exception as e:
        logger.error(f"Groq chat failed: {e}", exc_info=True)
        err_msg = str(e)
        if "model_not_available" in err_msg.lower() or "does not exist" in err_msg.lower():
            yield json.dumps({"type": "error", "content": f"Model '{model}' unavailable. Check GROQ_MODEL in .env"})
        elif "rate_limit" in err_msg.lower():
            yield json.dumps({"type": "error", "content": "Rate limited by Groq. Wait a moment and retry."})
        elif "tool_use_failed" in err_msg.lower() or "failed to call a function" in err_msg.lower():
            yield json.dumps({"type": "error", "content": "The AI tried to use a tool but failed. Try rephrasing your request."})
        else:
            yield json.dumps({"type": "error", "content": f"AI error: {err_msg[:300]}"})
