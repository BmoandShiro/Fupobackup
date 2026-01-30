"""
FastAPI backend for the Fupo desktop assistant.

This exposes your existing Python logic (weather, system monitor, NLP,
Spotify, Asana, etc.) as HTTP endpoints that a Tauri/TypeScript frontend
can call.

Run with (from project root):
    python run_backend.py
  or:
    cd path/to/Fupobackup && python -m uvicorn backend.api:app --reload
"""

from __future__ import annotations

import asyncio
import logging
import os
import threading
from typing import Any, Dict, List

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend import helpers
from backend.assistant_core import clear_caches as assistant_clear_caches, run_command as run_assistant_command

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Fupo Assistant API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:1420", "http://127.0.0.1:1420", "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Optional: speech recognition for /api/mics
try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False

# Optional: audio ducking (pycaw)
_ducking_enabled = False
_ducking_thread = None
_ducking_stop = threading.Event()
_volume_interface = None
_volume_init_error: str | None = None  # last error when pycaw init failed (so UI can show it)

def _init_volume():
    global _volume_interface, _volume_init_error
    if _volume_interface is not None:
        return _volume_interface
    _volume_init_error = None
    try:
        from ctypes import cast, POINTER
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        device = AudioUtilities.GetSpeakers()
        # Prefer EndpointVolume (modern pycaw); fallback to Activate (no _ctl)
        volume = getattr(device, "EndpointVolume", None)
        if volume is not None:
            _volume_interface = cast(volume, POINTER(IAudioEndpointVolume))
            return _volume_interface
        from comtypes import CLSCTX_ALL
        interface = getattr(device, "Activate", None)
        if interface is not None:
            iface = interface(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            _volume_interface = cast(iface, POINTER(IAudioEndpointVolume))
            return _volume_interface
        _volume_init_error = "pycaw device has no EndpointVolume or Activate (update pycaw?)"
        return None
    except Exception as e:
        _volume_init_error = str(e)
        logger.warning("Volume control (pycaw) unavailable: %s", e)
        return None


class ChatRequest(BaseModel):
    text: str


class CommandRequest(BaseModel):
    text: str


class PathRequest(BaseModel):
    path: str


class DuckingRequest(BaseModel):
    enabled: bool


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
    Text command endpoint. Runs the same logic as the desktop assistant
    (Spotify, weather, start program, etc.) via assistant_core.run_command.
    """
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text must not be empty")

    logger.info("COMMAND request: %s", text)
    try:
        result = await asyncio.to_thread(run_assistant_command, text)
        display, spoken = result[0], result[1]
        extra = result[2] if len(result) > 2 else {}
        return {"display": display, "spoken": spoken, **extra}
    except Exception as e:
        logger.exception("Command failed: %s", e)
        msg = str(e)
        return {"display": msg, "spoken": msg}


# --- Settings (read/write settings.json) ---

SETTINGS_FILE = "settings.json"


def _settings_path() -> str:
    return os.path.join(os.getcwd(), SETTINGS_FILE)


@app.get("/api/settings")
async def get_settings() -> Dict[str, Any]:
    """Return full settings from settings.json."""
    path = _settings_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            import json
            return json.load(f)
    except Exception as e:
        logger.warning("Failed to read settings: %s", e)
        return {}


@app.put("/api/settings")
async def put_settings(req: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """Merge provided settings into settings.json and return full settings."""
    import json as json_mod
    path = _settings_path()
    current: Dict[str, Any] = {}
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                current = json_mod.load(f)
        except Exception as e:
            logger.warning("Failed to read settings for merge: %s", e)
    if isinstance(req, dict):
        current.update(req)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json_mod.dump(current, f, indent=4)
    except Exception as e:
        logger.exception("Failed to write settings: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
    assistant_clear_caches()
    return current


# --- Home tab: mics, shortcuts, scan, path, ducking ---

@app.get("/api/mics")
async def list_mics() -> Dict[str, Any]:
    """List available microphones (device index and name)."""
    if not SR_AVAILABLE:
        raise HTTPException(status_code=501, detail="speech_recognition not installed")
    names = sr.Microphone.list_microphone_names()
    mics = [
        {"index": i, "name": name}
        for i, name in enumerate(names)
    ]
    return {"mics": mics, "message": "\n".join(
        f'Microphone "{name}" at device_index={i}' for i, name in enumerate(names)
    )}


@app.get("/api/shortcuts")
async def get_shortcuts() -> Dict[str, Any]:
    """List desktop shortcuts (name -> target path)."""
    desktop = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")
    shortcuts = helpers.find_shortcuts(desktop)
    lines = [f"{name}: {path}" for name, path in shortcuts.items()]
    return {"shortcuts": shortcuts, "message": "\n".join(lines)}


@app.post("/api/scan")
async def start_scan() -> Dict[str, Any]:
    """Start scanning for programs in background. Poll /api/scan/status for progress."""
    state = helpers.get_scan_state()
    if state.get("running"):
        return {"status": "already_running", "message": "Scan already in progress."}
    thread = threading.Thread(target=helpers.run_scan, daemon=True)
    thread.start()
    return {"status": "started", "message": "Scan started. Poll /api/scan/status for progress."}


@app.get("/api/scan/status")
async def scan_status() -> Dict[str, Any]:
    """Return current scan progress (running, progress 0-100, message)."""
    return helpers.get_scan_state()


@app.post("/api/path")
async def add_path(req: PathRequest) -> Dict[str, Any]:
    """Add an executable path to the list (basename used as key)."""
    path = req.path.strip()
    if not path or not os.path.isfile(path):
        raise HTTPException(status_code=400, detail="path must be an existing file")
    base = os.getcwd()
    exec_file = os.path.join(base, "executables.json")
    executables = helpers.load_executables(exec_file)
    name = os.path.basename(path).lower()
    executables[name] = path
    helpers.save_executables(executables, exec_file)
    return {"message": f"Added {name} to the list.", "name": name}


@app.post("/api/ducking")
async def set_ducking(req: DuckingRequest) -> Dict[str, Any]:
    """Enable or disable audio ducking (lower system volume when speaking)."""
    global _ducking_enabled, _ducking_thread, _ducking_stop
    vol = _init_volume()
    if vol is None:
        msg = "Audio ducking unavailable (pycaw not set up)."
        if _volume_init_error:
            msg += f" Reason: {_volume_init_error}"
        else:
            msg += " Install with: pip install pycaw comtypes. See Help tab for full setup."
        raise HTTPException(status_code=501, detail=msg)
    if req.enabled:
        if _ducking_enabled:
            return {"enabled": True, "message": "Audio ducking already enabled."}
        try:
            from audio_ducking import monitor_and_adjust_volume
        except ImportError:
            raise HTTPException(status_code=501, detail="audio_ducking module not found")
        from backend.assistant_core import _get_setting
        ratio = int(_get_setting("audio_ducking_ratio", 50))
        ratio = max(0, min(100, ratio))  # duck amount: 100 = silent, 0 = no duck
        _ducking_stop.clear()
        original = vol.GetMasterVolumeLevelScalar()
        reduce = original * (1.0 - ratio / 100.0)  # 100% duck = 0 volume (silent)
        _ducking_thread = threading.Thread(
            target=monitor_and_adjust_volume,
            args=(vol, 15, reduce, _ducking_stop),
            daemon=True,
        )
        _ducking_thread.start()
        _ducking_enabled = True
        return {"enabled": True, "message": "Audio ducking enabled."}
    else:
        if not _ducking_enabled:
            return {"enabled": False, "message": "Audio ducking already disabled."}
        _ducking_stop.set()
        if _ducking_thread and _ducking_thread.is_alive():
            _ducking_thread.join(timeout=2.0)
        _ducking_enabled = False
        return {"enabled": False, "message": "Audio ducking disabled."}


@app.get("/api/ducking")
async def get_ducking() -> Dict[str, Any]:
    """Return whether audio ducking is enabled and if pycaw is available (with error if not)."""
    vol = _init_volume()
    out: Dict[str, Any] = {"enabled": _ducking_enabled, "spotify_enabled": _spotify_ducking_enabled}
    if vol is None:
        out["available"] = False
        if _volume_init_error:
            out["error"] = _volume_init_error
    else:
        out["available"] = True
    sp = _get_spotify_for_ducking()
    out["spotify_available"] = sp is not None and getattr(sp, "sp", None) is not None
    return out


# Spotify ducking (separate from system ducking)
_spotify_ducking_enabled = False
_spotify_ducking_thread = None
_spotify_duck_stop = threading.Event()


def _get_spotify_for_ducking():
    """Lazy get Spotify controller for ducking (avoids circular import at module load)."""
    from backend.assistant_core import _get_spotify
    return _get_spotify()


@app.post("/api/ducking/spotify")
async def set_spotify_ducking(req: DuckingRequest) -> Dict[str, Any]:
    """Enable or disable Spotify-only audio ducking (lowers Spotify volume when speaking)."""
    global _spotify_ducking_enabled, _spotify_ducking_thread, _spotify_duck_stop
    sp = _get_spotify_for_ducking()
    if sp is None or getattr(sp, "sp", None) is None:
        raise HTTPException(
            status_code=503,
            detail="Spotify not configured or not authenticated. Add credentials in Settings and log in.",
        )
    try:
        from audio_ducking import monitor_spotify_duck
    except ImportError:
        raise HTTPException(status_code=501, detail="audio_ducking module (pyaudio) required for Spotify ducking")
    if req.enabled:
        if _spotify_ducking_enabled:
            return {"enabled": True, "message": "Spotify ducking already enabled."}
        from backend.assistant_core import _get_setting
        ratio = int(_get_setting("spotify_ducking_ratio", 100))
        ratio = max(0, min(100, ratio))
        _spotify_duck_stop.clear()
        _spotify_ducking_thread = threading.Thread(
            target=monitor_spotify_duck,
            args=(sp, 15, ratio, _spotify_duck_stop),
            daemon=True,
        )
        _spotify_ducking_thread.start()
        _spotify_ducking_enabled = True
        return {"enabled": True, "message": "Spotify ducking enabled."}
    else:
        if not _spotify_ducking_enabled:
            return {"enabled": False, "message": "Spotify ducking already disabled."}
        _spotify_duck_stop.set()
        if _spotify_ducking_thread and _spotify_ducking_thread.is_alive():
            _spotify_ducking_thread.join(timeout=2.0)
        _spotify_ducking_enabled = False
        return {"enabled": False, "message": "Spotify ducking disabled."}


@app.get("/api/ducking/spotify")
async def get_spotify_ducking() -> Dict[str, Any]:
    """Return whether Spotify ducking is enabled and if Spotify is available."""
    sp = _get_spotify_for_ducking()
    available = sp is not None and getattr(sp, "sp", None) is not None
    return {"enabled": _spotify_ducking_enabled, "available": available}


# --- Weather ---

@app.get("/api/weather")
async def get_weather(location: str | None = None) -> Dict[str, Any]:
    """Get weather for city name, US ZIP (5 or 5+4), or auto (IP). Returns display, spoken, and resolved location."""
    from backend.assistant_core import _get_weather_api
    api_obj = _get_weather_api()
    if api_obj is None:
        raise HTTPException(status_code=503, detail="Weather API not available")
    city = (location or "").strip() or "auto"
    try:
        result = await asyncio.to_thread(api_obj.get_weather, city, "", True)
        display, spoken = result[0], result[1]
        resolved_location = result[2] if len(result) > 2 else None
        return {"display": display, "spoken": spoken, "location": resolved_location}
    except Exception as e:
        logger.exception("Weather request failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# --- System (CPU/RAM/disk, headless with psutil) ---

@app.get("/api/system")
async def get_system() -> Dict[str, Any]:
    """Return current CPU, RAM, and disk usage (no Qt)."""
    try:
        import psutil
    except ImportError:
        raise HTTPException(status_code=501, detail="psutil not installed")
    cpu_percent = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory()
    # Use home drive on Windows for disk, else /
    root = os.path.expanduser("~")
    if os.name == "nt" and len(root) >= 2 and root[1] == ":":
        root = root[:2] + os.sep
    try:
        disk = psutil.disk_usage(root)
        disk_percent = disk.percent
    except Exception:
        disk_percent = 0.0
    return {
        "cpu_percent": round(cpu_percent, 1),
        "ram_percent": round(ram.percent, 1),
        "ram_used_gb": round(ram.used / (1024 ** 3), 2),
        "ram_total_gb": round(ram.total / (1024 ** 3), 2),
        "disk_percent": round(disk_percent, 1),
    }


# --- Tools (screenshot) ---

@app.post("/api/tools/screenshot")
async def take_screenshot() -> Dict[str, Any]:
    """Take a screenshot and save to the folder from settings (or default Pictures/Screenshots)."""
    from backend.assistant_core import _get_setting
    from datetime import datetime
    try:
        import pyautogui
    except ImportError:
        raise HTTPException(status_code=501, detail="pyautogui not installed")
    save_dir = _get_setting("screenshot_dir", os.path.join(os.path.expanduser("~"), "Pictures", "Screenshots"))
    os.makedirs(save_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(save_dir, f"screenshot_{ts}.png")
    try:
        await asyncio.to_thread(pyautogui.screenshot().save, path)
    except Exception as e:
        logger.exception("Screenshot failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
    return {"path": path, "message": f"Screenshot saved to {path}"}

