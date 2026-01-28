"""
FastAPI backend for the Fupo desktop assistant.

This exposes your existing Python logic (weather, system monitor, NLP,
Spotify, Asana, etc.) as HTTP endpoints that a Tauri/TypeScript frontend
can call.

Run with:
    uvicorn backend.api:app --reload
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# NOTE: for now we just import simple helpers. As we integrate, we can
# refactor your existing modules (desktop_assistant.py, weather_api.py, etc.)
# and call into them from here.

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Fupo Assistant API", version="0.1.0")


class ChatRequest(BaseModel):
    text: str


class CommandRequest(BaseModel):
    text: str


@app.get("/health")
async def health() -> Dict[str, Any]:
    """Simple health check endpoint."""
    return {"status": "ok"}


@app.post("/api/chat")
async def chat(req: ChatRequest) -> Dict[str, Any]:
    """
    High-level chat endpoint.

    TODO:
      - Wire this to your existing ask_ai / ask_chatgpt / ask_grok /
        ask_cursor_cli logic.
      - Probably create a small wrapper class that reuses the
        DesktopAssistant AI methods in a non-GUI context.
    """
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text must not be empty")

    logger.info("CHAT request: %s", text)

    # Placeholder behaviour for now.
    # Replace with actual call into your AI logic.
    reply = f"(stub) You said: {text}"
    return {"display": reply, "spoken": reply}


@app.post("/api/command")
async def command(req: CommandRequest) -> Dict[str, Any]:
    """
    Text command endpoint (maps to process_command in your assistant).

    TODO:
      - Import and instantiate a non-GUI DesktopAssistant-like object
        (or factor out the command logic into a separate module) and
        call its process_command() method here.
    """
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text must not be empty")

    logger.info("COMMAND request: %s", text)

    # Placeholder response for now.
    reply = f"(stub) Command processed: {text}"
    return {"display": reply, "spoken": reply}


# TODO: add more endpoints as you wire things up:
#   - /api/weather?location=...
#   - /api/system (CPU/RAM/disk stats)
#   - /api/spotify (play/pause/like/etc.)
#   - /api/asana/task
#   - /api/scan, /api/scan/status
#   - /api/tools/screenshot

