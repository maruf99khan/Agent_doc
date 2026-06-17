import os
from utils.openrouter import chat
from utils.prompts import DOCUMENT_CHECK_PROMPT


DOC_MODEL = os.environ.get("DOCUMENT_MODEL", "meta-llama/llama-3.2-3b-instruct")

def check_and_improve(text: str) -> dict:
    try:
        prompt = DOCUMENT_CHECK_PROMPT.format(text=text)
        result = chat(prompt, model=DOC_MODEL)
        if result["status"] == "success":
            return {"status": "success", "result": result["content"]}
        return {"status": "error", "error_message": result["error_message"]}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}
