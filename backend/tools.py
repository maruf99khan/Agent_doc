import os
import sys
import re
import subprocess
import urllib.request
import shutil
import logging

from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
import requests

from security import is_safe_code, is_safe_shell_command, safe_pip_install, sanitize_web_content, WORKSPACE
from file_service import (
    read_file_content, write_file_content,
    create_pdf, create_docx, create_txt,
    get_file_path, list_files, save_upload,
)

logger = logging.getLogger(__name__)


def web_search(query: str, max_results: int = 5) -> str:
    try:
        results = list(DDGS().text(query, max_results=max_results))
        if not results:
            return "No results found."
        output = []
        for i, r in enumerate(results, 1):
            title = r.get('title', 'No title')
            body = sanitize_web_content(r.get('body', ''))
            url = r.get('href', '')
            output.append(f"{i}. {title}\n{body}\nSource: {url}")
        return '\n\n'.join(output)
    except Exception as e:
        logger.error("Web search failed: %s", e)
        return f"Search failed: {str(e)}"


def fetch_page(url: str) -> str:
    try:
        if not url.startswith(('http://', 'https://')):
            return "Invalid URL."
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        for tag in soup(['script', 'style', 'nav', 'footer', 'iframe']):
            tag.decompose()
        text = soup.get_text(separator='\n', strip=True)
        return sanitize_web_content(text)
    except Exception as e:
        logger.error("Failed to fetch page %s: %s", url, e)
        return f"Failed to fetch page: {str(e)}"


def run_code(code: str, auto_install: bool = True) -> dict:
    safe, reason = is_safe_code(code)
    if not safe:
        return {'success': False, 'output': '', 'error': f'Security blocked: {reason}'}

    os.makedirs(WORKSPACE, exist_ok=True)
    code_with_cd = f"""
import os
os.chdir(r'{WORKSPACE}')
""" + code

    tmp_path = os.path.join(WORKSPACE, '_temp_run.py')
    try:
        with open(tmp_path, 'w', encoding='utf-8') as f:
            f.write(code_with_cd)

        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True, text=True,
            timeout=120, cwd=WORKSPACE
        )
        output = result.stdout.strip()
        error = result.stderr.strip()

        if error and 'ModuleNotFoundError' in error and auto_install:
            module = re.search(r"No module named '([^']+)'", error)
            if module:
                pkg = module.group(1).split('.')[0]
                install_ok, _ = install_package(pkg)
                if install_ok:
                    result2 = subprocess.run(
                        [sys.executable, tmp_path],
                        capture_output=True, text=True,
                        timeout=120, cwd=WORKSPACE
                    )
                    return {
                        'success': result2.returncode == 0,
                        'output': result2.stdout.strip(),
                        'error': result2.stderr.strip(),
                        'installed': pkg
                    }

        return {
            'success': result.returncode == 0,
            'output': output,
            'error': error
        }
    except subprocess.TimeoutExpired:
        return {'success': False, 'output': '', 'error': 'Code timed out after 120 seconds.'}
    except Exception as e:
        logger.error("Code execution error: %s", e)
        return {'success': False, 'output': '', 'error': str(e)}
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def install_package(package: str) -> tuple:
    safe, reason = safe_pip_install(package)
    if not safe:
        return False, reason
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', package, '-q'],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0:
            return True, f"Installed {package}."
        return False, result.stderr.strip()
    except Exception as e:
        return False, str(e)


def download_file(url: str, filename: str) -> str:
    path = os.path.join(WORKSPACE, filename)
    try:
        os.makedirs(os.path.dirname(path) or WORKSPACE, exist_ok=True)
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response, open(path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
        size = os.path.getsize(path)
        return f"Downloaded to {filename} ({size:,} bytes)"
    except Exception as e:
        return f"Download failed: {str(e)}"


def run_shell_command(command: str, timeout: int = 120) -> str:
    safe, reason = is_safe_shell_command(command)
    if not safe:
        return f"Blocked: {reason}"
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True,
            text=True, timeout=timeout, cwd=WORKSPACE
        )
        output = (result.stdout + result.stderr).strip()
        return output if output else "Command ran with no output."
    except subprocess.TimeoutExpired:
        return f"Command timed out after {timeout}s."
    except Exception as e:
        return f"Error: {str(e)}"


TOOL_DEFINITIONS = [
    {
        "name": "web_search",
        "description": "Search the web using DuckDuckGo. Use this for any real-time information, news, research.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "fetch_page",
        "description": "Fetch the full text content of a webpage.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to fetch"}
            },
            "required": ["url"]
        }
    },
    {
        "name": "create_pdf",
        "description": "Create a PDF report from markdown-style text content.",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "The content to put in the PDF"},
                "name": {"type": "string", "description": "Filename (e.g. report.pdf)"}
            },
            "required": ["content", "name"]
        }
    },
    {
        "name": "create_docx",
        "description": "Create a Word document from text content (supports headings, lists).",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "The content for the document"},
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
                "content": {"type": "string", "description": "The text content"},
                "name": {"type": "string", "description": "Filename (e.g. notes.txt)"}
            },
            "required": ["content", "name"]
        }
    },
    {
        "name": "read_file",
        "description": "Read the contents of a file in the workspace.",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "The filename to read"}
            },
            "required": ["filename"]
        }
    },
    {
        "name": "write_file",
        "description": "Write content to a file in the workspace.",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "The filename to write"},
                "content": {"type": "string", "description": "The content to write"}
            },
            "required": ["filename", "content"]
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
    {
        "name": "run_code",
        "description": "Execute Python code in a sandboxed environment. Returns stdout/stderr.",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "The Python code to execute"}
            },
            "required": ["code"]
        }
    },
    {
        "name": "download_file",
        "description": "Download a file from a URL to the workspace.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to download from"},
                "filename": {"type": "string", "description": "The filename to save as"}
            },
            "required": ["url", "filename"]
        }
    },
]


TOOL_MAP = {
    "web_search": lambda args: web_search(args["query"]),
    "fetch_page": lambda args: fetch_page(args["url"]),
    "create_pdf": lambda args: create_pdf(args["content"], args.get("name", "report.pdf")),
    "create_docx": lambda args: create_docx(args["content"], args.get("name", "report.docx")),
    "create_txt": lambda args: create_txt(args["content"], args.get("name", "report.txt")),
    "read_file": lambda args: read_file_content(args["filename"]),
    "write_file": lambda args: write_file_content(args["filename"], args["content"]),
    "list_files": lambda args: str(list_files()),
    "run_code": lambda args: run_code(args["code"]),
    "download_file": lambda args: download_file(args["url"], args["filename"]),
}
