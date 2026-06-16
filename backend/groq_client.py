import os
import json
import re
import logging
from typing import AsyncGenerator

from openai import OpenAI

logger = logging.getLogger(__name__)

MODEL_PREFERENCE = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
]
MAX_TOOL_ROUNDS = 5

TOOL_CALL_RE = re.compile(
    r'^\s*TOOL_CALL:\s*(\{.*?\})\s*$', re.MULTILINE | re.DOTALL
)


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
    return os.environ.get("GROQ_MODEL", MODEL_PREFERENCE[0])


def _try_models(client, messages, model_list, temperature=0.7, max_tokens=4096):
    errors = []
    for model in model_list:
        try:
            return model, client.chat.completions.create(
                model=model, messages=messages, temperature=temperature, max_tokens=max_tokens,
            )
        except Exception as e:
            err = str(e).lower()
            if "model_not_available" in err or "does not exist" in err or "decommissioned" in err:
                errors.append(f"{model}: decommissioned")
                continue
            raise
    raise RuntimeError(f"All models failed: {'; '.join(errors)}")


def _build_tools_description(tool_defs: list[dict]) -> str:
    lines = ["You have these tools available:"]
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
        lines.append(f"\n--- {name} ---\n{desc}\nParameters:\n{params_str}")
    lines.append("""

To call a tool, output ONLY this exact format on its own line (no other text on that line):
TOOL_CALL: {"tool": "<name>", "args": {<arguments>}}

For example:
TOOL_CALL: {"tool": "web_search", "args": {"query": "latest AI news 2026"}}

After the tool call line, you can continue with normal text on subsequent lines.
If you don't need to call a tool, just respond normally.""")
    return "\n".join(lines)


def _build_messages(
    message: str,
    history: list[dict],
    tool_defs: list[dict],
    memory_context: str = "",
) -> list[dict]:
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
    system += "\n" + _build_tools_description(tool_defs)

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
        logger.error(f"Groq chat failed: {e}", exc_info=True)
        err_msg = str(e)
        if "model_not_available" in err_msg.lower() or "does not exist" in err_msg.lower():
            yield json.dumps({"type": "error", "content": f"Model '{model}' unavailable. Check GROQ_MODEL in .env"})
        elif "rate_limit" in err_msg.lower():
            yield json.dumps({"type": "error", "content": "Rate limited by Groq. Wait a moment and retry."})
        else:
            yield json.dumps({"type": "error", "content": f"AI error: {err_msg[:300]}"})
