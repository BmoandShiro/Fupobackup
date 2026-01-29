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

# Lazy-initialized singletons (settings are not cached; Spotify is until cleared)
_spotify_controller = None
_weather_api = None
_executables = None


def clear_caches() -> None:
    """Clear cached Spotify (and other) state so next request uses fresh settings."""
    global _spotify_controller
    _spotify_controller = None


def _load_settings() -> dict:
    """Read settings from disk every time so saved changes in the Settings tab are seen."""
    try:
        with open("settings.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        logger.warning("Failed to load settings: %s", e)
        return {}


def _get_setting(key: str, default: Any = None) -> Any:
    return _load_settings().get(key, default)


def _get_spotify():
    global _spotify_controller
    if _spotify_controller is not None:
        return _spotify_controller
    cid = (_get_setting("spotify_client_id") or "").strip()
    secret = (_get_setting("spotify_client_secret") or "").strip()
    redirect = (_get_setting("spotify_redirect_uri") or "http://localhost:8080").strip() or "http://localhost:8080"
    if not cid or not secret:
        logger.info("Spotify credentials not in settings (cid=%s, secret=%s); Spotify disabled for API.", bool(cid), bool(secret))
        return None
    try:
        from spotify_controller import SpotifyController
        _spotify_controller = SpotifyController(cid, secret, redirect)
        if _spotify_controller and getattr(_spotify_controller, "sp", None):
            logger.info("Spotify controller initialized for API.")
        else:
            logger.warning("Spotify controller created but sp is None (auth may be needed).")
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
    if "play" in c and "my" in c and "liked" in c and "song" not in c:
        return "play_liked_songs"
    if "play" in c and "discover weekly" in c:
        return "play_discover_weekly"
    if "play" in c and "release radar" in c:
        return "play_release_radar"
    if "play" in c and ("something similar" in c or "more like this" in c or "similar" in c):
        return "play_similar"
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
    if "create" in c and "playlist" in c:
        return "create_playlist"
    if "play" in c and "playlist" in c:
        return "play_playlist"
    if "play" in c and "daylist" in c:
        return "play_daylist"
    if "play" in c and "music" in c and "for" in c and "then stop" in c:
        return "timed_playback"
    if "play" in c and "music" in c:
        return "resume_playback"
    if any(w in c for w in ["like", "favorite"]) and "song" in c:
        return "like_song"
    if any(w in c for w in ["unlike", "remove", "unfavorite"]) and "song" in c:
        return "unlike_song"
    if "mute" in c:
        return "mute"
    if "add" in c and "queue" in c:
        return "add_to_queue"
    if "volume up" in c or (c.strip() in ["volume up", "vol up"]):
        return "volume_up"
    if "volume down" in c or (c.strip() in ["volume down", "vol down"]):
        return "volume_down"
    if any(w in c for w in ["set", "adjust"]) and "volume" in c:
        return "set_volume"
    if "increase" in c and "volume" in c:
        return "increase_volume"
    if "decrease" in c and "volume" in c:
        return "decrease_volume"
    if "add" in c and "playlist" in c:
        return "add_to_playlist"
    if "delete" in c and "playlist" in c:
        return "delete_playlist"
    if any(w in c for w in ["recommend", "find"]) and any(kw in c for kw in ["song", "artist", "genre", "music"]):
        return "get_recommendations"
    if "play" in c and ("genre" in c or re.search(r"play\s+(rock|pop|jazz|classical|hip.?hop|electronic|country|metal|indie|r&b|soul|folk|punk)\s*(music)?$", c)):
        return "play_genre"
    if "pause" in c:
        return "pause_playback"
    if "resume" in c:
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
    if intent == "play_liked_songs":
        if sp and getattr(sp, "sp", None):
            result = sp.play_liked_songs()
            return (result, result) if isinstance(result, str) else ("Playing your liked songs.", "Playing your liked songs.")
        return _spotify_unconfigured()
    if intent == "play_discover_weekly":
        if sp and getattr(sp, "sp", None):
            result = sp.play_discover_weekly()
            return (result, result) if isinstance(result, str) else ("Playing Discover Weekly.", "Playing Discover Weekly.")
        return _spotify_unconfigured()
    if intent == "play_release_radar":
        if sp and getattr(sp, "sp", None):
            result = sp.play_release_radar()
            return (result, result) if isinstance(result, str) else ("Playing Release Radar.", "Playing Release Radar.")
        return _spotify_unconfigured()
    if intent == "play_similar":
        if sp and getattr(sp, "sp", None):
            result = sp.play_similar()
            return (result, result) if isinstance(result, str) else ("Playing similar tracks.", "Playing similar tracks.")
        return _spotify_unconfigured()
    if intent == "mute":
        if sp and getattr(sp, "sp", None):
            result = sp.mute()
            return (result, result) if isinstance(result, str) else ("Spotify muted.", "Spotify muted.")
        return _spotify_unconfigured()
    if intent == "add_to_queue":
        if sp and getattr(sp, "sp", None):
            m_this = re.search(r"add\s+(?:this|the)\s*(?:song\s+)?to\s+queue", command, re.IGNORECASE)
            m_named = re.search(r"add\s+(.+?)\s+to\s+queue", command, re.IGNORECASE)
            if m_this or not m_named:
                uri = sp.get_current_track_uri()
                if not uri or (isinstance(uri, str) and not uri.startswith("spotify:track:")):
                    return "No track playing. Play something first or say 'add [song name] to queue'.", "No track playing."
                result = sp.add_to_queue(uri)
            else:
                query = m_named.group(1).strip()
                if query.lower() in ("this", "the", "this song", "the song"):
                    uri = sp.get_current_track_uri()
                    if not uri or (isinstance(uri, str) and not uri.startswith("spotify:track:")):
                        return "No track playing.", "No track playing."
                    result = sp.add_to_queue(uri)
                else:
                    result = sp.add_to_queue(query)
            return (result, result) if isinstance(result, str) else ("Added to queue.", "Added to queue.")
        return _spotify_unconfigured()
    if intent == "volume_up":
        if sp and getattr(sp, "sp", None):
            result = sp.increase_volume(10)
            return (result, result) if isinstance(result, str) else ("Volume up.", "Volume up.")
        return _spotify_unconfigured()
    if intent == "volume_down":
        if sp and getattr(sp, "sp", None):
            result = sp.decrease_volume(10)
            return (result, result) if isinstance(result, str) else ("Volume down.", "Volume down.")
        return _spotify_unconfigured()
    if intent == "set_volume":
        m = re.search(r"set\s+spotify\s+volume\s+to\s+(\d+)%?", command, re.IGNORECASE)
        if m and sp and getattr(sp, "sp", None):
            vol = min(100, max(0, int(m.group(1))))
            result = sp.set_volume(vol)
            return (result, result) if isinstance(result, str) else (f"Volume set to {vol}%.", f"Volume set to {vol}%.")
        return _spotify_unconfigured() if not sp else "Say 'set Spotify volume to [0-100]%'.", "Volume not specified."
    if intent == "increase_volume":
        m = re.search(r"increase\s+spotify\s+volume(?:\s+by\s+(\d+)%?)?", command, re.IGNORECASE)
        if m and sp and getattr(sp, "sp", None):
            amount = int(m.group(1)) if m.group(1) else 10
            result = sp.increase_volume(amount)
            return (result, result) if isinstance(result, str) else (f"Increased volume by {amount}%.", f"Increased volume.")
        return _spotify_unconfigured() if not sp else "Say 'increase Spotify volume' or 'increase Spotify volume by [N]%'.", "Not specified."
    if intent == "decrease_volume":
        m = re.search(r"decrease\s+spotify\s+volume(?:\s+by\s+(\d+)%?)?", command, re.IGNORECASE)
        if m and sp and getattr(sp, "sp", None):
            amount = int(m.group(1)) if m.group(1) else 10
            result = sp.decrease_volume(amount)
            return (result, result) if isinstance(result, str) else (f"Decreased volume by {amount}%.", f"Decreased volume.")
        return _spotify_unconfigured() if not sp else "Say 'decrease Spotify volume' or 'decrease Spotify volume by [N]%'.", "Not specified."
    if intent == "create_playlist":
        m = re.search(r"create\s+(?:a\s+)?playlist\s+called\s+(.+)", command, re.IGNORECASE)
        if m and sp and getattr(sp, "sp", None):
            name = m.group(1).strip()
            if name:
                result = sp.create_playlist(name)
                return (result, result) if isinstance(result, str) else (f"Created playlist '{name}'.", f"Created playlist.")
        if sp and getattr(sp, "sp", None):
            msg = "What would you like to name the playlist?"
            return (msg, msg, {"prompt_for": "playlist_name", "follow_up_prefix": "create a playlist called "})
        return _spotify_unconfigured()
    if intent == "add_to_playlist":
        m = re.search(r"add\s+(?:this|the)\s+song\s+to\s+my\s+(.+?)\s+playlist", command, re.IGNORECASE)
        if m and sp and getattr(sp, "sp", None):
            playlist_name = m.group(1).strip()
            uri = sp.get_current_track_uri()
            if not uri:
                return "No track playing. Play something first.", "No track playing."
            result = sp.add_to_playlist(playlist_name, uri)
            return (result, result) if isinstance(result, str) else (f"Added to {playlist_name}.", "Added to playlist.")
        return _spotify_unconfigured() if not sp else "Say 'add this song to my [playlist name] playlist'.", "Playlist name not specified."
    if intent == "delete_playlist":
        m = re.search(r"delete\s+playlist\s+(.+)", command, re.IGNORECASE)
        if m and sp and getattr(sp, "sp", None):
            name = m.group(1).strip()
            result = sp.delete_playlist(name)
            return (result, result) if isinstance(result, str) else (f"Deleted playlist '{name}'.", "Playlist deleted.")
        return _spotify_unconfigured() if not sp else "Say 'delete playlist [name]'.", "Playlist name not specified."
    if intent == "get_recommendations":
        m = re.search(r"(?:recommend|find)\s+(songs|artists)\s+like\s+(.+)|(?:recommend|find)\s+(\w+)\s+music", command, re.IGNORECASE)
        if m and sp and getattr(sp, "sp", None):
            if m.group(1) and m.group(2):
                seed_type = "song" if m.group(1).lower() == "songs" else "artist"
                seed_value = m.group(2).strip()
            elif m.group(3):
                seed_type = "genre"
                seed_value = m.group(3).strip()
            else:
                return "Say 'recommend songs like [X]' or 'find [genre] music'.", "Not specified."
            result = sp.get_recommendations(seed_type, seed_value)
            return (result, result) if isinstance(result, str) else (f"Playing recommendations for {seed_value}.", "Playing recommendations.")
        return _spotify_unconfigured() if not sp else "Say 'recommend songs like [X]' or 'find [genre] music'.", "Not specified."
    if intent == "timed_playback":
        m = re.search(r"play\s+music\s+for\s+(\d+)\s+(minutes|hours)\s+then\s+stop", command, re.IGNORECASE)
        if m and sp and getattr(sp, "sp", None):
            val, unit = int(m.group(1)), m.group(2).lower()
            seconds = val * 60 if unit == "minutes" else val * 3600
            result = sp.stop_after_time(seconds)
            return (result, result) if isinstance(result, str) else (f"Playback will stop in {val} {unit}.", f"Stopping in {val} {unit}.")
        return _spotify_unconfigured() if not sp else "Say 'play music for [N] minutes/hours then stop'.", "Not specified."
    if intent == "play_genre":
        m = re.search(r"play\s+(?:some\s+)?(.+?)\s*(?:music)?\s*$", command, re.IGNORECASE) or re.search(r"play\s+(.+?)\s+music", command, re.IGNORECASE)
        if m and sp and getattr(sp, "sp", None):
            genre = m.group(1).strip().lower()
            if not genre:
                return "Say 'play [genre]' or 'play [genre] music'.", "Genre not specified."
            result = sp.get_recommendations("genre", genre)
            return (result, result) if isinstance(result, str) else (f"Playing {genre} recommendations.", f"Playing {genre}.")
        return _spotify_unconfigured() if not sp else "Say 'play [genre]' or 'play [genre] music'.", "Genre not specified."

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
