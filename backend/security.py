import re
import os
import sys

WORKSPACE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'workspace')

BLOCKED_COMMANDS = [
    'format', 'del ', 'rd ', 'rmdir', 'shutdown', 'restart',
    'regedit', 'reg ', 'netsh', 'net user', 'net localgroup',
    'bcdedit', 'diskpart', 'cipher', 'sfc', 'attrib',
    'icacls', 'takeown', 'runas',
    'wmic', 'taskkill', 'sc stop', 'sc delete',
    'rm -rf',
    '__import__', 'eval(', 'exec(',
]

BLOCKED_SHELL_COMMANDS = [
    'rmdir /s', 'rm -rf', 'format ', 'del /f /s', 'del /f',
    'shutdown', 'rd /s', 'rd /q', 'del /s', 'del /q',
    'reg delete', 'reg add', 'regedit', 'netsh',
    'net user', 'net localgroup', 'bcdedit', 'diskpart',
    'cipher', 'sfc', 'icacls', 'takeown', 'runas',
    'wmic', 'taskkill /f', 'sc stop', 'sc delete',
]

BLOCKED_PATHS = [
    'C:\\Windows',
    os.environ.get('SYSTEMROOT', 'C:\\Windows'),
]

INJECTION_PATTERNS = [
    r'ignore\s+previous\s+instructions',
    r'ignore\s+all\s+instructions',
    r'disregard\s+.*\s+instructions',
    r'you\s+are\s+now\s+.*\s+AI',
    r'new\s+instructions\s*:',
    r'system\s*:\s*you',
    r'forget\s+everything',
    r'act\s+as\s+if',
    r'pretend\s+you\s+are',
    r'jailbreak',
    r'DAN\s+mode',
    r'developer\s+mode',
    r'\[SYSTEM\]',
    r'\[INST\]',
    r'<\|system\|>',
    r'override\s+safety',
]


def is_safe_code(code: str) -> tuple:
    code_lower = code.lower()
    for cmd in BLOCKED_COMMANDS:
        if cmd.lower() in code_lower:
            return False, f"Blocked dangerous command: '{cmd}'"
    path_pattern = re.findall(r'["\']([A-Za-z]:\\[^"\']+)["\']', code)
    for path in path_pattern:
        for blocked in BLOCKED_PATHS:
            if path.lower().startswith(blocked.lower()):
                return False, f"Blocked access to protected path: {path}"
    return True, "ok"


def is_safe_shell_command(command: str) -> tuple:
    cmd_lower = command.lower().strip()
    for blocked in BLOCKED_SHELL_COMMANDS:
        if blocked in cmd_lower:
            return False, f"Blocked dangerous command: '{blocked}'"
    return True, "ok"


def is_safe_path(path: str) -> tuple:
    abs_path = os.path.abspath(path)
    workspace_abs = os.path.abspath(WORKSPACE)
    if not abs_path.startswith(workspace_abs):
        for blocked in BLOCKED_PATHS:
            if abs_path.lower().startswith(blocked.lower()):
                return False, f"Access denied to protected path: {blocked}"
    return True, "ok"


def sanitize_web_content(text: str) -> str:
    for pattern in INJECTION_PATTERNS:
        text = re.sub(pattern, '[REMOVED]', text, flags=re.IGNORECASE)
    text = re.sub(r'(?i)(system|assistant|user)\s*:\s*', '', text)
    if len(text) > 8000:
        text = text[:8000] + '... [truncated for safety]'
    return text


def safe_pip_install(package: str) -> tuple:
    blocked_packages = [
        'os', 'sys', 'subprocess', 'socket', 'ctypes',
        'keylogger', 'trojan', 'malware', 'hack', 'crack',
    ]
    pkg_clean = package.strip().lower().split('==')[0].split('>=')[0]
    for b in blocked_packages:
        if b in pkg_clean:
            return False, f"Blocked suspicious package: {package}"
    if not re.match(r'^[a-zA-Z0-9_\-\.\[\]>=<,\s]+$', package):
        return False, f"Invalid package name: {package}"
    return True, "ok"
