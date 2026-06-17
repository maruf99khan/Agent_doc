import os
from utils.openrouter import chat
from utils.prompts import SUMMARY_PROMPT


SUM_MODEL = os.environ.get("SUMMARY_MODEL", "google/gemma-3-4b-it")

def summarize(text: str) -> dict:
    try:
        prompt = SUMMARY_PROMPT.format(text=text)
        result = chat(prompt, model=SUM_MODEL)
        if result["status"] == "success":
            return {"status": "success", "result": result["content"]}
        return {"status": "error", "error_message": result["error_message"]}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def bullet_summary(text: str) -> dict:
    try:
        prompt = f"Extract exactly 5 key bullet points from the following document. Each bullet should be a single complete sentence.\n\n{text}"
        result = chat(prompt, model=SUM_MODEL)
        if result["status"] == "success":
            return {"status": "success", "result": result["content"]}
        return {"status": "error", "error_message": result["error_message"]}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def quick_summary(text: str) -> dict:
    try:
        short = text[:1500]
        prompt = f"Summarize the following text in exactly 50 words or less:\n\n{short}"
        result = chat(prompt, model=SUM_MODEL)
        if result["status"] == "success":
            return {"status": "success", "result": result["content"]}
        return {"status": "error", "error_message": result["error_message"]}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}
