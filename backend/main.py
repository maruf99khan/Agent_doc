import os
import json
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import memory
import file_service
from groq_client import chat_stream

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("gonzo")

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend', 'dist')


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Gonzo AI Agent starting...")
    if os.environ.get("OPENROUTER_API_KEY"):
        logger.info("OpenRouter API key found.")
    elif os.environ.get("GROQ_API_KEY"):
        logger.info("Groq API key found (fallback).")
    else:
        logger.warning("No API key set! Set OPENROUTER_API_KEY in env.")
    yield
    logger.info("Gonzo AI Agent shutting down.")


app = FastAPI(title="Gonzo AI Agent", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_session(request: Request) -> str:
    return request.headers.get("X-Session-ID", "default")


def _stream_response(async_gen):
    async def event_stream():
        try:
            async for event in async_gen:
                yield f"data: {event}\n\n"
        except Exception as e:
            logger.error(f"Stream crashed: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'content': f'Server error: {str(e)[:200]}'})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


# ── Chat API (handles everything via AI tools) ──

@app.post("/api/chat/stream")
async def chat_endpoint(
    request: Request,
    message: str = Form(...),
    history: str = Form(default="[]"),
    file_context: str = Form(default=""),
):
    session_id = _get_session(request)
    try:
        history_data = json.loads(history) if isinstance(history, str) else history
    except json.JSONDecodeError:
        history_data = []

    full_message = message
    if file_context:
        full_message = f"{message}\n\n---\nAttached file contents:\n{file_context}\n---"

    memory.update_last_seen()
    memory.remember_fact(f"User asked: {message[:200]}")

    return _stream_response(chat_stream(full_message, history_data, session_id=session_id))


# ── File Endpoints ──

@app.post("/api/files/upload")
async def upload_file(request: Request, file: UploadFile = File(...)):
    session_id = _get_session(request)
    contents = await file.read()
    result = file_service.save_upload(contents, file.filename, session_id=session_id)
    return result


@app.get("/api/files/read/{filename:path}")
async def read_file(request: Request, filename: str):
    session_id = _get_session(request)
    try:
        content = file_service.read_file_content(filename, session_id=session_id)
        return {"filename": filename, "content": content[:50000]}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")


@app.get("/api/files/download/{filename:path}")
async def download_named_file(request: Request, filename: str):
    session_id = _get_session(request)
    path = file_service.get_file_path(os.path.basename(filename), session_id)
    if not path:
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path=path,
        filename=os.path.basename(filename),
        media_type="application/octet-stream",
    )


@app.get("/api/files/list")
async def list_files_endpoint(request: Request):
    session_id = _get_session(request)
    return file_service.list_files(session_id=session_id)


@app.delete("/api/files/{filename:path}")
async def delete_file_endpoint(request: Request, filename: str):
    session_id = _get_session(request)
    if file_service.delete_file(filename, session_id=session_id):
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="File not found")


# ── Memory ──

@app.get("/api/memory")
async def get_memory():
    data = memory.load()
    return {
        "user": data["user"],
        "facts": data["facts"][-20:],
        "conversation_count": data["conversation_count"],
        "last_seen": data["last_seen"],
    }


@app.post("/api/memory/forget")
async def forget_memory():
    memory.forget_all()
    return {"status": "memory cleared"}


# ── Agent Endpoints (simple prompt-based, no function calling) ──

@app.post("/api/agent/check")
async def agent_check(request: Request):
    from agents.document_agent import check_and_improve
    body = await request.json()
    text = body.get("text", "")
    quick = body.get("quick", False)
    if quick and len(text) > 600:
        text = text[:500]
    result = check_and_improve(text)
    return result


@app.post("/api/agent/summarize")
async def agent_summarize(request: Request):
    from agents.summary_agent import summarize, bullet_summary, quick_summary
    body = await request.json()
    style = body.get("style", "full")
    text = body.get("text", "")
    if style == "bullet":
        result = bullet_summary(text)
    elif style == "quick":
        result = quick_summary(text)
    else:
        result = summarize(text)
    return {"status": result.get("status"), "result": result.get("result"), "error_message": result.get("error_message"), "style": style}


@app.post("/api/agent/extract")
async def agent_extract(request: Request):
    from agents.info_agent import extract_info, generate_report, research_topic
    body = await request.json()
    atype = body.get("type", "entities")
    text = body.get("text", "")
    if atype == "report":
        result = generate_report(text)
    elif atype == "research":
        topic = body.get("topic", "")
        result = research_topic(topic) if topic else {"status": "error", "error_message": "No topic provided"}
    else:
        result = extract_info(text)
    return {"status": result.get("status"), "result": result.get("result"), "error_message": result.get("error_message"), "type": atype}


# ── Health ──

@app.get("/api/health")
async def health():
    return {"status": "ok"}


# ── Serve Frontend ──

if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
    logger.info(f"Serving frontend from {FRONTEND_DIR}")
else:
    logger.info(f"Frontend build not found at {FRONTEND_DIR}. Run 'npm run build' in frontend/ for production.")


if __name__ == "__main__":
    import uvicorn
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=True)
