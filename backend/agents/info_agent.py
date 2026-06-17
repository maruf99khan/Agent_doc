import os
from utils.openrouter import chat
from utils.prompts import INFO_COLLECTION_PROMPT, TOPIC_RESEARCH_PROMPT


INFO_MODEL = os.environ.get("INFO_MODEL", "deepseek/deepseek-r1")

def extract_info(text: str) -> dict:
    try:
        prompt = INFO_COLLECTION_PROMPT.format(text=text)
        result = chat(prompt, model=INFO_MODEL)
        if result["status"] == "success":
            return {"status": "success", "result": result["content"]}
        return {"status": "error", "error_message": result["error_message"]}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def generate_report(text: str) -> dict:
    try:
        prompt = f"You are a professional report writer. Based on the following document, create a comprehensive analysis report with sections: Overview, Key Findings, Analysis, Recommendations, Conclusion.\n\n{text}"
        result = chat(prompt, model=INFO_MODEL)
        if result["status"] == "success":
            return {"status": "success", "result": result["content"]}
        return {"status": "error", "error_message": result["error_message"]}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def research_topic(topic: str) -> dict:
    try:
        prompt = TOPIC_RESEARCH_PROMPT.format(topic=topic)
        result = chat(prompt, model=INFO_MODEL)
        if result["status"] == "success":
            return {"status": "success", "result": result["content"]}
        return {"status": "error", "error_message": result["error_message"]}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}
