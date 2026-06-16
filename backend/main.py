import os
import json
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import memory
import file_service
from groq_client import chat_stream

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("gonzo")

WORKSPACE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'workspace')
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend', 'dist')
os.makedirs(WORKSPACE, exist_ok=True)


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


# ── Chat API ──

@app.post("/api/chat/stream")
async def chat_endpoint(
    message: str = Form(...),
    history: str = Form(default="[]"),
    file_context: str = Form(default=""),
):
    try:
        history_data = json.loads(history) if isinstance(history, str) else history
    except json.JSONDecodeError:
        history_data = []

    full_message = message
    if file_context:
        full_message = f"{message}\n\n---\nAttached file contents:\n{file_context}\n---"

    memory.update_last_seen()
    memory.remember_fact(f"User asked: {message[:200]}")

    return _stream_response(chat_stream(full_message, history_data))


# ── Job Endpoints ──

@app.post("/api/jobs/summarize")
async def job_summarize(filename: str = Form(...)):
    try:
        content = file_service.read_file_content(filename)
    except FileNotFoundError as e:
        return _stream_response(_single_error(str(e)))
    return _stream_response(chat_stream(
        f"Please summarize the following content:\n\n{content[:8000]}",
        [],
        "You are a summarization assistant. Provide a clear, concise summary."
    ))


@app.post("/api/jobs/write")
async def job_write(filename: str = Form(...), content: str = Form(...)):
    file_service.write_file_content(filename, content)
    return {"status": "ok", "filename": filename, "url": f"/api/files/download/{filename}"}


@app.post("/api/jobs/rewrite")
async def job_rewrite(filename: str = Form(...), instructions: str = Form(default="")):
    try:
        original = file_service.read_file_content(filename)
    except FileNotFoundError as e:
        return _stream_response(_single_error(str(e)))
    return _stream_response(chat_stream(
        f"Original content of {filename}:\n\n{original[:6000]}\n\n"
        f"Rewrite instructions: {instructions}\n\n"
        f"Return ONLY the rewritten content, no extra text.",
        [],
        "You are a document rewriting assistant. Output only the rewritten document."
    ))


@app.post("/api/jobs/report")
async def job_report(topic: str = Form(...), history: str = Form(default="")):
    try:
        history_data = json.loads(history) if isinstance(history, str) and history else []
    except json.JSONDecodeError:
        history_data = []

    filename = topic.strip().replace(" ", "_")[:40] + ".md"
    full_content = [""]

    async def gen():
        async for event in chat_stream(
            f"Write a detailed report about: {topic}\n\n"
            f"Format with markdown headings, bullet points, and sections.",
            history_data,
            "You are a report writer. Create comprehensive, well-structured documents."
        ):
            data = json.loads(event)
            if data.get("type") == "text":
                full_content[0] += data["content"]
            yield event

        text_content = full_content[0].strip()
        if text_content:
            try:
                file_service.write_file_content(filename, text_content)
                yield json.dumps({
                    "type": "file_created",
                    "filename": filename,
                    "url": f"/api/files/download/{filename}",
                })
            except Exception as e:
                yield json.dumps({"type": "error", "content": f"Failed to save report: {e}"})

        yield json.dumps({"type": "done"})

    return _stream_response(gen())


def _single_error(msg):
    async def gen():
        yield json.dumps({"type": "error", "content": msg})
        yield json.dumps({"type": "done"})
    return gen()


# ── File Endpoints ──

@app.post("/api/files/upload")
async def upload_file(file: UploadFile = File(...)):
    contents = await file.read()
    result = file_service.save_upload(contents, file.filename)
    return result


@app.get("/api/files/read/{filename:path}")
async def read_file(filename: str):
    try:
        content = file_service.read_file_content(filename)
        return {"filename": filename, "content": content[:50000]}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")


@app.get("/api/files/download/{filename:path}")
async def download_named_file(filename: str):
    path = os.path.join(WORKSPACE, os.path.basename(filename))
    if not os.path.exists(path) or not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path=path,
        filename=os.path.basename(filename),
        media_type="application/octet-stream",
    )


@app.get("/api/files/list")
async def list_files_endpoint():
    return file_service.list_files()


@app.delete("/api/files/{file_id}")
async def delete_file_endpoint(file_id: str):
    if file_service.delete_file(file_id):
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
