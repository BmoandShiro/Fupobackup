"""
Headless command runner for the API. Loads settings, Spotify, weather, executables,
and runs the same intent/action logic as desktop_assistant without Qt.

Used by /api/command. Expects to run with cwd = project root (e.g. via run_backend.py)
so settings.json, .spotify_cache, and executables.json are found.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from typing import Any, Tuple

from backend import helpers

logger = logging.getLogger(__name__)

# Lazy-initialized singletons
_spotify_controller = None
_weather_api = None
_executables = None
_settings = None


def _load_settings() -> dict:
    global _settings
    if _settings is not None:
        return _settings
    try:
        with open("settings.json", "r", encoding="utf-8") as f:
            _settings = json.load(f)
    except FileNotFoundError:
        _settings = {}
    return _settings


def _get_setting(key: str, default: Any = None) -> Any:
    return _load_settings().get(key, default)


def _get_spotify():
    global _spotify_controller
    if _spotify_controller is not None:
        return _spotify_controller
    cid = _get_setting("spotify_client_id", "")
    secret = _get_setting("spotify_client_secret", "")
    redirect = _get_setting("spotify_redirect_uri", "http://localhost:8080")
    if not cid or not secret:
        logger.info("Spotify credentials not in settings; Spotify disabled for API.")
        return None
    try:
        from spotify_controller import SpotifyController
        _spotify_controller = SpotifyController(cid, secret, redirect)
        if _spotify_controller and getattr(_spotify_controller, "sp", None):
            logger.info("Spotify controller initialized for API.")
        else:
            _spotify_controller = None
    except Exception as e:
        logger.warning("Could not init Spotify for API: %s", e)
        _spotify_controller = None
    return _spotify_controller


def _get_weather_api():
    global _weather_api
    if _weather_api is not None:
        return _weather_api
    try:
        from weather_api import WeatherAPI
        _weather_api = WeatherAPI()
    except Exception as e:
        logger.warning("Could not init WeatherAPI for API: %s", e)
        _weather_api = None
    return _weather_api


def _get_executables() -> dict:
    global _executables
    if _executables is not None:
        return _executables
    _executables = helpers.load_executables("executables.json")
    return _executables


def _parse_song_and_artist(text: str) -> Tuple[str, str | None]:
    text = (text or "").strip()
    lower = text.lower()
    if " by " in lower:
        idx = lower.index(" by ")
        return text[:idx].strip(), text[idx + 4 :].strip()
    return text, None


def _simple_intent(command: str) -> str:
    c = command.lower().strip()
    if any(w in c for w in ["weather", "forecast", "alerts"]):
        return "weather"
    if any(w in c for w in ["start", "launch", "open"]) and "play" not in c:
        return "start_program"
    if "play" in c and "song" in c and "liked" in c:
        return "play_liked_song"
    if "play" in c and "song" in c:
        return "play_song"
    if "play" in c and ("artist radio" in c or "radio" in c):
        return "play_radio"
    if "play" in c and "artist" in c:
        return "play_artist"
    if "play" in c and "album" in c:
        return "play_album"
    if "play" in c and "playlist" in c:
        return "play_playlist"
    if "play" in c and "daylist" in c:
        return "play_daylist"
    if any(w in c for w in ["like", "favorite"]) and "song" in c:
        return "like_song"
    if any(w in c for w in ["unlike", "remove", "unfavorite"]) and "song" in c:
        return "unlike_song"
    if "pause" in c:
        return "pause_playback"
    if "resume" in c or ("play" in c and "music" in c):
        return "resume_playback"
    if any(w in c for w in ["skip", "next"]):
        return "skip_track"
    if any(w in c for w in ["previous", "back"]):
        return "previous_track"
    if any(w in c for w in ["check", "current", "playing"]) and "song" in c:
        return "get_current_song"
    if any(w in c for w in ["toggle", "switch"]) and "shuffle" in c:
        return "toggle_shuffle"
    if any(w in c for w in ["toggle", "switch"]) and "repeat" in c:
        return "toggle_repeat"
    if any(w in c for w in ["check", "system", "status"]):
        return "check_system"
    if any(w in c for w in ["screenshot", "capture", "screen", "snap"]):
        return "take_screenshot"
    return "unknown"


def run_command(command: str) -> Tuple[str, str]:
    """Run a voice/text command and return (display_message, spoken_message)."""
    command = (command or "").strip()
    if not command:
        return "No command provided.", "No command provided."

    intent = _simple_intent(command)
    logger.info("API command: intent=%s text=%s", intent, command[:80])

    # --- Play song ---
    if intent == "play_song":
        m = re.search(r"play\s+(?:a\s+)?song\s+(.+)", command, re.IGNORECASE)
        if m:
            raw = m.group(1).strip()
            song_name, artist = _parse_song_and_artist(raw)
            search_query = f"{song_name} {artist}" if artist else song_name
            sp = _get_spotify()
            if not sp or not getattr(sp, "sp", None):
                msg = "Spotify is not configured or not authenticated. Add Spotify credentials in Settings and ensure you've logged in (e.g. from the desktop app once)."
                return msg, msg
            result = sp.play_song(search_query)
            if isinstance(result, str):
                return result, result
            return f"Playing {search_query} on Spotify.", f"Playing {search_query}."
        return "Song name not specified. Say 'play a song [name]'.", "Song name not specified."

    # --- Other Spotify intents (no extra args) ---
    sp = _get_spotify()
    if intent == "pause_playback":
        if sp and getattr(sp, "sp", None):
            sp.pause_playback()
            return "Paused.", "Paused."
        return _spotify_unconfigured()
    if intent == "resume_playback":
        if sp and getattr(sp, "sp", None):
            sp.resume_playback()
            return "Resuming.", "Resuming."
        return _spotify_unconfigured()
    if intent == "skip_track":
        if sp and getattr(sp, "sp", None):
            sp.skip_track()
            return "Skipped.", "Skipped."
        return _spotify_unconfigured()
    if intent == "previous_track":
        if sp and getattr(sp, "sp", None):
            sp.previous_track()
            return "Previous track.", "Previous track."
        return _spotify_unconfigured()
    if intent == "get_current_song":
        if sp and getattr(sp, "sp", None):
            msg = sp.get_current_song()
            return msg, msg
        return _spotify_unconfigured()
    if intent == "like_song":
        if sp and getattr(sp, "sp", None):
            msg = sp.like_current_song()
            return msg, msg
        return _spotify_unconfigured()
    if intent == "unlike_song":
        if sp and getattr(sp, "sp", None):
            msg = sp.unlike_current_song()
            return msg, msg
        return _spotify_unconfigured()
    if intent == "toggle_shuffle":
        if sp and getattr(sp, "sp", None):
            msg = sp.toggle_shuffle()
            return msg, msg
        return _spotify_unconfigured()
    if intent == "toggle_repeat":
        if sp and getattr(sp, "sp", None):
            msg = sp.toggle_repeat()
            return msg, msg
    if intent == "play_daylist":
        if sp and getattr(sp, "sp", None):
            result = sp.play_daylist()
            return (result, result) if isinstance(result, str) else ("Playing your Daylist.", "Playing your Daylist.")
        return _spotify_unconfigured()

    # --- Play artist radio / artist / album / playlist (with name) ---
    if intent == "play_radio":
        m = re.search(r"play\s+(?:artist\s+)?radio\s+(.+)", command, re.IGNORECASE)
        if m and sp and getattr(sp, "sp", None):
            name = m.group(1).strip()
            result = sp.play_artist_radio(name)
            return (result, result) if isinstance(result, str) else (f"Playing radio for {name}.", f"Playing radio for {name}.")
        return _spotify_unconfigured() if not sp else "Artist name not specified.", "Artist name not specified."
    if intent == "play_artist":
        m = re.search(r"play\s+artist\s+(.+)", command, re.IGNORECASE)
        if m and sp and getattr(sp, "sp", None):
            name = m.group(1).strip()
            result = sp.play_artist(name)
            return (result, result) if isinstance(result, str) else (f"Playing artist {name}.", f"Playing artist {name}.")
        return _spotify_unconfigured() if not sp else "Artist name not specified.", "Artist name not specified."
    if intent == "play_album":
        m = re.search(r"play\s+album\s+(.+)", command, re.IGNORECASE)
        if m and sp and getattr(sp, "sp", None):
            name = m.group(1).strip()
            result = sp.play_album(name)
            return (result, result) if isinstance(result, str) else (f"Playing album {name}.", f"Playing album {name}.")
        return _spotify_unconfigured() if not sp else "Album name not specified.", "Album name not specified."
    if intent == "play_playlist":
        m = re.search(r"play\s+playlist\s+(.+)", command, re.IGNORECASE)
        if m and sp and getattr(sp, "sp", None):
            name = m.group(1).strip()
            result = sp.play_playlist(name)
            return (result, result) if isinstance(result, str) else (f"Playing playlist {name}.", f"Playing playlist {name}.")
        return _spotify_unconfigured() if not sp else "Playlist name not specified.", "Playlist name not specified."
    if intent == "play_liked_song":
        m = re.search(r"play\s+(?:the\s+)?song\s+(.+)\s+from\s+my\s+liked", command, re.IGNORECASE)
        if m and sp and getattr(sp, "sp", None):
            name = m.group(1).strip()
            result = sp.play_liked_song(name)
            return (result, result) if isinstance(result, str) else (f"Playing {name} from liked songs.", f"Playing {name}.")
        return _spotify_unconfigured() if not sp else "Song name not specified.", "Song name not specified."

    # --- Weather ---
    if intent == "weather":
        api = _get_weather_api()
        if not api:
            return "Weather is not available.", "Weather is not available."
        location = "auto"
        # Simple location extraction: remove common words
        for word in ["weather", "forecast", "alerts", "what's", "what is", "the", "in"]:
            command = re.sub(rf"\b{re.escape(word)}\b", "", command, flags=re.IGNORECASE)
        location = command.strip() or "auto"
        try:
            display, spoken = api.get_weather(location, spoken_request=command, detailed=False)
            return display, spoken
        except Exception as e:
            msg = f"Weather error: {e}"
            return msg, msg

    # --- Start program ---
    if intent == "start_program":
        m = re.search(r"(?:start|launch|open)\s+(.+)", command, re.IGNORECASE)
        if m:
            name = m.group(1).strip().lower()
            if name in ["program", "application", "app"]:
                return "Please specify which program to start.", "Please specify which program to start."
            execs = _get_executables()
            if name in execs:
                try:
                    subprocess.Popen(execs[name], shell=True)
                    return f"Started {name}.", f"Started {name}."
                except Exception as e:
                    msg = f"Error starting {name}: {e}"
                    return msg, msg
            # Fuzzy match
            try:
                from fuzzywuzzy import process as fw_process
                choices = list(execs.keys())
                if not choices:
                    return "No programs in list. Run 'Scan for Programs' first.", "No programs in list."
                best, score = fw_process.extractOne(name, choices)
                if score >= 84:
                    subprocess.Popen(execs[best], shell=True)
                    return f"Started {best}.", f"Started {best}."
                return f"Could not find a close match for '{name}'. Try scanning for programs.", f"Could not find '{name}'."
            except ImportError:
                return f"'{name}' not in program list. Run 'Scan for Programs' or add the path.", f"'{name}' not found."
        return "Program not specified.", "Program not specified."

    # --- Check system ---
    if intent == "check_system":
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage(os.path.expanduser("~"))
            msg = (
                f"CPU {cpu:.1f}%. RAM {ram.percent:.1f}% ({ram.used / 1024**3:.1f} of {ram.total / 1024**3:.1f} GB). "
                f"Disk {disk.percent:.1f}%."
            )
            return msg, msg
        except Exception as e:
            return f"System check failed: {e}", f"System check failed: {e}"

    # --- Screenshot ---
    if intent == "take_screenshot":
        try:
            from datetime import datetime
            import pyautogui
            save_dir = _get_setting("screenshot_dir", os.path.join(os.path.expanduser("~"), "Pictures", "Screenshots"))
            os.makedirs(save_dir, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(save_dir, f"screenshot_{ts}.png")
            pyautogui.screenshot().save(path)
            msg = f"Screenshot saved to {path}"
            return msg, msg
        except Exception as e:
            return f"Screenshot failed: {e}", f"Screenshot failed: {e}"

    return "I'm not sure how to do that. Try 'play song [name]', 'pause', 'weather', or 'start [program]'.", "Unknown command."


def _spotify_unconfigured() -> Tuple[str, str]:
    msg = (
        "Spotify is not configured or not authenticated. "
        "Add Spotify Client ID and Secret in Settings (e.g. from the desktop app's Settings > Configure), "
        "then log in once so the API can use Spotify."
    )
    return msg, msg
