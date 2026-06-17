import os
import requests
import json

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "openrouter/free"


def _get_config():
    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("No API key found. Set OPENROUTER_API_KEY or GROQ_API_KEY.")
    model = os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL)
    base = os.environ.get("OPENROUTER_BASE", OPENROUTER_URL)
    return api_key, model, base


def chat(prompt: str, system_prompt: str = None, model: str = None) -> dict:
    api_key, default_model, base_url = _get_config()
    model = model or default_model
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        resp = requests.post(
            url=base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "stream": False,
                "temperature": 0.7,
                "max_tokens": 4096,
            },
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return {"status": "success", "content": content}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}
