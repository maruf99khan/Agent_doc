import os
import json
import re
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

_TOOL_NAMES = {t["function"]["name"] for t in TOOLS}


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
        "You are Gonzo, a document processing AI assistant. Help users work with their documents.\n\n"
        "When a user uploads a document, you can extract its text content. Offer to:\n"
        "- **Review** the document (grammar, clarity, tone, structure)\n"
        "- **Summarize** it (executive summary, bullet points, key takeaways)\n"
        "- **Extract information** (entities, facts, structured data)\n"
        "- **Research** related topics using the web_search tool\n"
        "- **Save** results as files using the create_file tool\n\n"
        "Rules:\n"
        "- Be proactive. When a document is uploaded, ask if they want review, summary, or extraction.\n"
        "- Only use read_file when the user explicitly names a file. If they say 'summarize it' without naming a file, just respond conversationally.\n"
        "- Use create_file when the user asks to save, create, or export something.\n"
        "- Use web_search when the user wants research on a topic.\n"
        "- Format responses in Markdown.\n"
        "- CRITICAL: You have function calling tools available. ALWAYS call the function directly instead of outputting JSON or describing what function you would call. Do not write 'Here is a JSON for a function call' — just call the function."
    )
    if system_extra:
        system += f"\n\n{system_extra}"
    messages = [{"role": "system", "content": system}]
    for h in history[-20:]:
        role = "user" if h.get("role") != "assistant" else "assistant"
        messages.append({"role": role, "content": h.get("content", "")})
    messages.append({"role": "user", "content": message})

    MAX_CHARS = 80000
    total = sum(len(str(m.get("content", ""))) for m in messages)
    while total > MAX_CHARS and len(messages) > 2:
        removed = messages.pop(1)
        total -= len(str(removed.get("content", "")))

    return messages


def _parse_json_tool_call(text: str):
    """Fallback: try to extract a tool call from text that looks like JSON."""
    text = text.strip()
    for m in re.finditer(r'\{[^{}]*\}', text, re.DOTALL):
        block = m.group()
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        name = data.get("name") or data.get("function")
        if name in _TOOL_NAMES:
            params = data.get("parameters") or data.get("arguments") or {}
            class FakeToolCall:
                pass
            tc = FakeToolCall()
            tc.function = FakeToolCall()
            tc.function.name = name
            tc.function.arguments = json.dumps(params)
            tc.id = "fallback_" + name
            return tc, None
    return None, None


def _execute_tool(tool_call, session_id: str = "default") -> tuple[str, dict | None]:
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
        filename = args["filename"]
        content = args["content"]
        ext = os.path.splitext(filename)[1].lower()
        if ext == ".pdf":
            from file_service import create_pdf
            create_pdf(content, filename, session_id=session_id)
        elif ext == ".docx":
            from file_service import create_docx
            create_docx(content, filename, session_id=session_id)
        else:
            from file_service import write_file_content
            write_file_content(filename, content, session_id=session_id)
        return f"File saved: {filename}", {"filename": filename, "url": f"/api/files/download/{filename}"}

    if func_name == "read_file":
        from file_service import read_file_content, extract_text, get_file_path
        filename = args["filename"]
        path = get_file_path(filename, session_id=session_id)
        if not path:
            return f"Error: File '{filename}' not found in workspace.", None
        ext = os.path.splitext(filename)[1].lower()
        if ext in ('.pdf', '.docx'):
            content = extract_text(filename, session_id=session_id) or "[No extractable text found]"
        else:
            content = read_file_content(filename, session_id=session_id)
        return f"--- {filename} ---\n{content}", None

    if func_name == "list_files":
        from file_service import list_files
        files = list_files(session_id=session_id)
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
    session_id: str = "default",
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

            if finish == "tool_calls" and msg.tool_calls:
                messages.append(msg)
                for tc in msg.tool_calls:
                    tool_name = tc.function.name
                    try:
                        t_args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        t_args = {}
                    detail = t_args.get("query") or t_args.get("filename") or ""
                    yield json.dumps({"type": "tool_progress", "tool": tool_name, "detail": detail})

                    result, file_info = _execute_tool(tc, session_id=session_id)
                    if file_info:
                        created_files.append(file_info)
                    logger.info(f"Tool {tc.function.name}: {result[:80]}")
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    })
                continue

            text = (msg.content or "").strip()
            parsed, _ = _parse_json_tool_call(text)
            if parsed:
                logger.info(f"Fallback JSON tool: {parsed.function.name}")
                try:
                    t_args = json.loads(parsed.function.arguments)
                except json.JSONDecodeError:
                    t_args = {}
                detail = t_args.get("query") or t_args.get("filename") or ""
                yield json.dumps({"type": "tool_progress", "tool": parsed.function.name, "detail": detail})

                result, file_info = _execute_tool(parsed, session_id=session_id)
                if file_info:
                    created_files.append(file_info)
                messages.append({
                    "role": "system",
                    "content": f"Tool executed: {result}",
                })
                continue

            if msg.content:
                yield json.dumps({"type": "text", "content": msg.content})

            for f in created_files:
                yield json.dumps({"type": "file_created", **f})
            yield json.dumps({"type": "done"})
            return

        for f in created_files:
            yield json.dumps({"type": "file_created", **f})
        yield json.dumps({"type": "warning", "content": "I reached my tool use limit and may not have finished. Try asking again or breaking the task into smaller steps."})
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
