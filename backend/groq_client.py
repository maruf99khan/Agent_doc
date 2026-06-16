import os
import json
import re
import logging
from typing import AsyncGenerator

from openai import OpenAI

logger = logging.getLogger(__name__)

OPENROUTER_BASE = "https://openrouter.ai/api/v1"

MODEL_PREFERENCE = [
    "meta-llama/llama-3.3-70b-instruct",
    "mistralai/mistral-7b-instruct",
    "google/gemma-2-27b-it",
]
MAX_TOOL_ROUNDS = 5

TOOL_CALL_RE = re.compile(
    r'^\s*TOOL_CALL:\s*(\{.*?\})\s*$', re.MULTILINE | re.DOTALL
)


def _get_client():
    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "API key not set. Set OPENROUTER_API_KEY (https://openrouter.ai/keys) "
            "or GROQ_API_KEY environment variable."
        )
    return OpenAI(
        base_url=OPENROUTER_BASE,
        api_key=api_key,
        default_headers={
            "HTTP-Referer": "https://github.com/maruf99khan/Agent_doc",
            "X-Title": "Gonzo AI Agent",
        },
    )


def _get_model():
    return os.environ.get("OPENROUTER_MODEL", MODEL_PREFERENCE[0])


def _try_models(client, messages, model_list, temperature=0.7, max_tokens=4096):
    errors = []
    for model in model_list:
        try:
            return model, client.chat.completions.create(
                model=model, messages=messages, temperature=temperature, max_tokens=max_tokens,
            )
        except Exception as e:
            err = str(e).lower()
            if any(w in err for w in ("model_not_available", "does not exist", "decommissioned", "not found", "overloaded")):
                errors.append(f"{model}: unavailable")
                continue
            raise
    raise RuntimeError(f"All models failed: {'; '.join(errors)}")


def _build_tools_description(tool_defs: list[dict]) -> str:
    lines = []
    for t in tool_defs:
        name = t["name"]
        desc = t["description"]
        props = t.get("parameters", {}).get("properties", {})
        required = t.get("parameters", {}).get("required", [])
        params_desc = []
        for pname, pinfo in props.items():
            req = " (required)" if pname in required else ""
            pdesc = pinfo.get("description", "")
            params_desc.append(f"  - {pname}{req}: {pdesc}")
        params_str = "\n".join(params_desc) if params_desc else "  - (no parameters)"
        lines.append(f"--- {name} ---\n{desc}\nParameters:\n{params_str}")
    lines.append("""
To call a file tool, output ONLY this exact format on its own line:
TOOL_CALL: {"tool": "<name>", "args": {<arguments>}}

Example:
TOOL_CALL: {"tool": "create_txt", "args": {"content": "...", "name": "notes.txt"}}""")
    return "\n".join(lines)


def _build_messages(
    message: str,
    history: list[dict],
    tool_defs: list[dict],
    memory_context: str = "",
) -> list[dict]:
    system = (
        "You are Gonzo, a conversational AI. You chat naturally like a normal person. "
        "You can also work with files when the user needs it.\n\n"
        "Your file abilities:\n"
        "- Read files and show their content\n"
        "- Create new files (txt, pdf, docx)\n"
        "- Write/rewrite content to files\n"
        "- Analyze and summarize file contents\n"
        "- List available files\n\n"
        "When the user asks for file work, use the file tool to do it, then tell them what you did. "
        "When just chatting, respond naturally. Don't invent tasks \u2014 only use tools when the user explicitly asks for file operations.\n"
        "Format responses in Markdown."
    )
    if memory_context:
        system += f"\n\n## What I know about the user\n{memory_context}\n"
    system += "\n\n" + _build_tools_description(tool_defs)

    messages = [{"role": "system", "content": system}]
    for h in history[-20:]:
        role = h.get("role", "assistant") if h.get("role") == "assistant" else "user"
        messages.append({"role": role, "content": h.get("content", "")})
    messages.append({"role": "user", "content": message})
    return messages


def _parse_tool_calls(text: str) -> list[dict]:
    calls = []
    for match in TOOL_CALL_RE.finditer(text):
        try:
            obj = json.loads(match.group(1))
            if isinstance(obj, dict) and "tool" in obj and isinstance(obj["tool"], str):
                calls.append(obj)
        except (json.JSONDecodeError, ValueError):
            continue
    return calls


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

    tool_defs = tool_map.get("definitions", [])
    handle_fn = tool_map.get("handle_tool")
    messages = _build_messages(message, history, tool_defs, memory_context)
    tool_rounds = 0

    try:
        while tool_rounds < MAX_TOOL_ROUNDS:
            tool_rounds += 1

            model, response = _try_models(
                client, messages, [model] + [m for m in MODEL_PREFERENCE if m != model]
            )

            choice = response.choices[0]
            text = (choice.message.content or "").strip()

            if not text:
                text = "Hello! I'm Gonzo. How can I help you today?"

            tool_calls = _parse_tool_calls(text)

            if not tool_calls:
                yield json.dumps({"type": "text", "content": text})
                break

            clean_text = TOOL_CALL_RE.sub("", text).strip()
            if clean_text:
                yield json.dumps({"type": "text", "content": clean_text})

            for tc in tool_calls:
                fn_name = tc["tool"]
                fn_args = tc.get("args", {})

                yield json.dumps({"type": "tool_call", "name": fn_name, "args": fn_args})

                if handle_fn:
                    result_str, created_file = await handle_fn(fn_name, fn_args)
                else:
                    result_str = json.dumps({"error": "No handler"})
                    created_file = None

                messages.append({"role": "assistant", "content": text})
                messages.append({
                    "role": "user",
                    "content": f"Tool '{fn_name}' returned:\n{result_str[:5000]}"
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
        logger.error(f"AI chat failed: {e}", exc_info=True)
        err_msg = str(e)
        if "model_not_available" in err_msg.lower() or "does not exist" in err_msg.lower():
            yield json.dumps({"type": "error", "content": f"Model '{model}' unavailable. Check OPENROUTER_MODEL env var."})
        elif "rate_limit" in err_msg.lower():
            yield json.dumps({"type": "error", "content": "Rate limited. Wait a moment and retry."})
        elif "insufficient_quota" in err_msg.lower() or "403" in err_msg:
            yield json.dumps({"type": "error", "content": "API quota exceeded or key invalid. Check your OpenRouter credits."})
        else:
            yield json.dumps({"type": "error", "content": f"AI error: {err_msg[:300]}"})
