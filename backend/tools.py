import logging
from file_service import (
    read_file_content, write_file_content,
    create_pdf, create_docx, create_txt,
    list_files,
)

logger = logging.getLogger(__name__)


TOOL_DEFINITIONS = [
    {
        "name": "read_file",
        "description": "Read the contents of a file from the workspace.",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Filename to read"}
            },
            "required": ["filename"]
        }
    },
    {
        "name": "write_file",
        "description": "Write or overwrite text content to a file.",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Filename to write"},
                "content": {"type": "string", "description": "Content to write"}
            },
            "required": ["filename", "content"]
        }
    },
    {
        "name": "create_pdf",
        "description": "Create a PDF document from text content.",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Content for the PDF"},
                "name": {"type": "string", "description": "Filename (e.g. report.pdf)"}
            },
            "required": ["content", "name"]
        }
    },
    {
        "name": "create_docx",
        "description": "Create a Word document from text content.",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Content for the document"},
                "name": {"type": "string", "description": "Filename (e.g. report.docx)"}
            },
            "required": ["content", "name"]
        }
    },
    {
        "name": "create_txt",
        "description": "Save text content as a plain text file.",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Content to save"},
                "name": {"type": "string", "description": "Filename (e.g. notes.txt)"}
            },
            "required": ["content", "name"]
        }
    },
    {
        "name": "list_files",
        "description": "List all files in the workspace.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
]


TOOL_MAP = {
    "read_file": lambda args: read_file_content(args["filename"]),
    "write_file": lambda args: write_file_content(args["filename"], args["content"]),
    "create_pdf": lambda args: create_pdf(args["content"], args.get("name", "report.pdf")),
    "create_docx": lambda args: create_docx(args["content"], args.get("name", "report.docx")),
    "create_txt": lambda args: create_txt(args["content"], args.get("name", "report.txt")),
    "list_files": lambda args: str(list_files()),
}
