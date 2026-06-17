import json
import os
import copy
from datetime import datetime

try:
    os.makedirs("/data", exist_ok=True)
    MEMORY_FILE = "/data/memory.json"
except (PermissionError, OSError):
    MEMORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'workspace', 'memory.json')

DEFAULT = {
    "user": {
        "name": None,
        "language": "English",
        "location": None,
        "occupation": None,
        "interests": [],
        "preferences": {},
    },
    "facts": [],
    "conversation_count": 0,
    "last_seen": None,
}


def load() -> dict:
    if not os.path.exists(MEMORY_FILE):
        save(copy.deepcopy(DEFAULT))
        return copy.deepcopy(DEFAULT)
    try:
        with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for key, value in DEFAULT.items():
            if key not in data:
                data[key] = copy.deepcopy(value)
        for key, value in DEFAULT['user'].items():
            if key not in data['user']:
                data['user'][key] = copy.deepcopy(value)
        return data
    except (json.JSONDecodeError, KeyError):
        save(copy.deepcopy(DEFAULT))
        return copy.deepcopy(DEFAULT)


def save(data: dict):
    os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
    with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def update_last_seen():
    data = load()
    data['last_seen'] = datetime.now().strftime('%Y-%m-%d %H:%M')
    data['conversation_count'] += 1
    save(data)


def remember_fact(fact: str):
    data = load()
    fact_lower = fact.lower().strip()
    for existing in data['facts']:
        if existing.lower().strip() == fact_lower:
            return
    data['facts'].append(fact)
    if len(data['facts']) > 100:
        data['facts'] = data['facts'][-100:]
    save(data)


def update_user(key: str, value):
    data = load()
    if key in data['user']:
        data['user'][key] = value
        save(data)


def forget_all():
    save(copy.deepcopy(DEFAULT))


def build_memory_context() -> str:
    data = load()
    u = data['user']
    parts = []
    if u['name']:       parts.append(f"User's name is {u['name']}.")
    if u['location']:   parts.append(f"User is from {u['location']}.")
    if u['occupation']: parts.append(f"User works as {u['occupation']}.")
    if u['interests']:  parts.append(f"User is interested in: {', '.join(u['interests'])}.")
    if u['preferences']:
        for k, v in u['preferences'].items():
            parts.append(f"User prefers {k}: {v}.")
    if data['facts']:
        parts.append("Known facts: " + " | ".join(data['facts'][-30:]))
    return ' '.join(parts)
