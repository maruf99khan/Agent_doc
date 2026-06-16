import logging
from typing import AsyncGenerator
import json

import memory
import tools as tools_module
from groq_client import chat_stream as groq_stream

logger = logging.getLogger(__name__)


async def process_message(
    message: str,
    history: list[dict],
    file_context: str = "",
) -> AsyncGenerator[str, None]:
    memory_context = memory.build_memory_context()

    full_message = message
    if file_context:
        full_message = f"{message}\n\n[Attached file content:\n{file_context}\n]"

    memory.update_last_seen()
    memory.remember_fact(f"User asked: {message[:200]}")

    async def handle_tool(name: str, args: dict) -> tuple[str, str | None]:
        handler = tools_module.TOOL_MAP.get(name)
        if not handler:
            return json.dumps({"error": f"Unknown tool: {name}"}), None
        try:
            result = handler(args)
            if isinstance(result, dict):
                result_str = json.dumps(result)
            else:
                result_str = str(result)
            created_file = None
            if name in ("create_pdf", "create_docx", "create_txt"):
                created_file = args.get("name", "report")
            elif name == "write_file":
                created_file = args.get("filename")
            return result_str, created_file
        except Exception as e:
            logger.error(f"Tool {name} failed: {e}")
            return json.dumps({"error": str(e)}), None

    streaming_tool_map = {
        "definitions": tools_module.TOOL_DEFINITIONS,
        "handle_tool": handle_tool,
    }

    async for event in groq_stream(full_message, history, streaming_tool_map, memory_context):
        yield event
