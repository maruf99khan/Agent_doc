from utils.openrouter import chat
from utils.prompts import DOCUMENT_CHECK_PROMPT


def check_and_improve(text: str) -> dict:
    try:
        prompt = DOCUMENT_CHECK_PROMPT.format(text=text)
        result = chat(prompt)
        if result["status"] == "success":
            return {"status": "success", "result": result["content"]}
        return {"status": "error", "error_message": result["error_message"]}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}
