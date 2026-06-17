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

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the internet for current information on any topic",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_file",
            "description": "Create or save a file with content. Use this when the user asks you to save something to a file, create a document, write code, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Filename with extension (e.g. report.md, script.py)"},
                    "content": {"type": "string", "description": "Full file content"},
                },
                "required": ["filename", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the content of a file from the workspace",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Filename to read"},
                },
                "required": ["filename"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List all files in the workspace with their sizes",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
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
    raise RuntimeError("No API key found. Set OPENROUTER_API_KEY or GROQ_API_KEY.")


def _get_model(provider):
    env_model = os.environ.get("OPENROUTER_MODEL") or os.environ.get("GROQ_MODEL")
    if env_model:
        return env_model
    if provider == "openrouter":
        return MODELS_OPENROUTER[0]
    return MODELS_GROQ[0]


def _build_messages(message: str, history: list[dict], system_extra: str = "") -> list[dict]:
    system = (
        "You are Gonzo, a helpful AI assistant with access to tools:\n"
        "- **web_search(query)** — search the internet for current info\n"
        "- **create_file(filename, content)** — save content to a file (user can download it)\n"
        "- **read_file(filename)** — read a file from the workspace\n"
        "- **list_files()** — list all files in the workspace\n\n"
        "When the user asks you to search something, summarize a file, "
        "create/modify a document, or analyze content — use the appropriate tool. "
        "Always use create_file when the user asks you to save or create something. "
        "Format your responses in Markdown."
    )
    if system_extra:
        system += f"\n\n{system_extra}"
    messages = [{"role": "system", "content": system}]
    for h in history[-20:]:
        role = "user" if h.get("role") != "assistant" else "assistant"
        messages.append({"role": role, "content": h.get("content", "")})
    messages.append({"role": "user", "content": message})
    return messages


def _execute_tool(tool_call) -> tuple[str, dict | None]:
    func_name = tool_call.function.name
    try:
        args = json.loads(tool_call.function.arguments)
    except json.JSONDecodeError:
        return f"Error: invalid arguments for {func_name}", None

    if func_name == "web_search":
        try:
            from duckduckgo_search import DDGS
            ddgs = DDGS()
            results = list(ddgs.text(args["query"], max_results=5))
            if not results:
                return "No search results found.", None
            out = []
            for r in results:
                title = r.get("title", "")
                body = r.get("body", "")
                href = r.get("href", "")
                out.append(f"- **{title}**: {body}\n  {href}")
            return "\n\n".join(out), None
        except ImportError:
            return "Web search unavailable (package not installed).", None
        except Exception as e:
            return f"Search failed: {e}", None

    if func_name == "create_file":
        from file_service import write_file_content
        filename = args["filename"]
        content = args["content"]
        write_file_content(filename, content)
        return f"File saved: {filename}", {"filename": filename, "url": f"/api/files/download/{filename}"}

    if func_name == "read_file":
        from file_service import read_file_content
        filename = args["filename"]
        try:
            content = read_file_content(filename)
            return f"--- {filename} ---\n{content}", None
        except FileNotFoundError:
            return f"Error: File '{filename}' not found in workspace.", None

    if func_name == "list_files":
        from file_service import list_files
        files = list_files()
        if not files:
            return "No files in workspace.", None
        lines = []
        for f in files:
            lines.append(f"- {f['name']} ({f['size']} bytes)")
        return "Files in workspace:\n" + "\n".join(lines), None

    return f"Unknown tool: {func_name}", None


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
    created_files = []

    try:
        for _ in range(5):
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,
                max_tokens=4096,
                stream=False,
                tools=TOOLS,
            )

            choice = response.choices[0]
            msg = choice.message
            finish = choice.finish_reason

            if msg.content:
                yield json.dumps({"type": "text", "content": msg.content})

            if finish == "tool_calls" and msg.tool_calls:
                messages.append(msg)
                for tc in msg.tool_calls:
                    result, file_info = _execute_tool(tc)
                    if file_info:
                        created_files.append(file_info)
                    logger.info(f"Tool {tc.function.name}: {result[:80]}")
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    })
            else:
                for f in created_files:
                    yield json.dumps({"type": "file_created", **f})
                yield json.dumps({"type": "done"})
                return

        yield json.dumps({"type": "done"})

    except Exception as e:
        logger.error(f"AI chat failed: {e}", exc_info=True)
        err = str(e).lower()
        if "rate_limit" in err:
            yield json.dumps({"type": "error", "content": "Rate limited. Wait and retry."})
        elif "insufficient_quota" in err:
            yield json.dumps({"type": "error", "content": "API quota exceeded or key invalid."})
        else:
            yield json.dumps({"type": "error", "content": f"AI error: {str(e)[:200]}"})
