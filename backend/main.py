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
from tools import TOOL_DEFINITIONS, TOOL_MAP
from agent_engine import process_message

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("gonzo")

WORKSPACE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'workspace')
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend', 'dist')
os.makedirs(WORKSPACE, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Gonzo AI Agent starting...")
    if not os.environ.get("GROQ_API_KEY"):
        logger.warning("GROQ_API_KEY not set! Create a .env file or set env variable.")
    else:
        logger.info("Groq API key found.")
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


# ── API Routes ──

@app.get("/api/health")
async def health():
    has_key = bool(os.environ.get("GROQ_API_KEY"))
    file_count = len(os.listdir(WORKSPACE)) if os.path.exists(WORKSPACE) else 0
    return {
        "status": "ok",
        "groq_configured": has_key,
        "files": file_count,
        "model": os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
    }


@app.post("/api/chat/stream")
async def chat_stream_endpoint(
    message: str = Form(...),
    history: str = Form(default="[]"),
    file_context: str = Form(default=""),
):
    try:
        history_data = json.loads(history) if isinstance(history, str) else history
    except json.JSONDecodeError:
        history_data = []

    async def event_stream():
        async for event in process_message(message, history_data, file_context):
            yield f"data: {event}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/files/upload")
async def upload_file(file: UploadFile = File(...)):
    contents = await file.read()
    result = file_service.save_upload(contents, file.filename)
    return result


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


# ── Serve Frontend (production) ──

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
