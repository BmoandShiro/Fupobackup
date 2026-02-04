"""
Backend helpers for scan, shortcuts, and executables.
No Qt dependency so FastAPI can use these without a QApplication.
"""

import json
import os
import threading
from typing import Any

try:
    import win32com.client
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

# Default paths for scan (Windows)
def _scan_paths():
    env = os.environ
    paths = [
        env.get("ProgramFiles", "C:\\Program Files"),
        env.get("ProgramFiles(x86)", "C:\\Program Files (x86)"),
        env.get("APPDATA", "") + "\\Microsoft\\Windows\\Start Menu\\Programs",
    ]
    for drive in ("D:\\", "F:\\"):
        if os.path.isdir(drive):
            paths.append(drive)
    return [p for p in paths if p and os.path.isdir(p)]


def get_shortcut_target(shortcut_path: str) -> str | None:
    if not WIN32_AVAILABLE:
        return None
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortcut(shortcut_path)
        return shortcut.Targetpath
    except Exception:
        return None


def find_shortcuts(directory: str) -> dict[str, str]:
    shortcuts = {}
    if not os.path.isdir(directory):
        return shortcuts
    for name in os.listdir(directory):
        if not name.lower().endswith(".lnk"):
            continue
        shortcut_path = os.path.join(directory, name)
        target = get_shortcut_target(shortcut_path)
        if target and target.lower().endswith(".exe"):
            key = os.path.splitext(name)[0].lower()
            shortcuts[key] = target
    return shortcuts


def find_executables(directory: str) -> dict[str, str]:
    exclusions = ["update", "uninstall"]
    result = {}
    for root, _dirs, files in os.walk(directory):
        for file in files:
            fl = file.lower()
            if not fl.endswith(".exe") or any(e in fl for e in exclusions):
                continue
            name = os.path.splitext(file)[0].lower()
            result[name] = os.path.join(root, file)
    return result


def load_executables(filename: str = "executables.json") -> dict[str, str]:
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_executables(executables: dict[str, str], filename: str = "executables.json") -> None:
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(executables, f, indent=4)


# In-memory scan state for /api/scan and /api/scan/status
_scan_state: dict[str, Any] = {
    "running": False,
    "progress": 0,
    "message": "",
    "error": None,
}
_scan_lock = threading.Lock()


def run_scan(cwd: str | None = None) -> None:
    """Run full scan in background; updates _scan_state."""
    with _scan_lock:
        if _scan_state["running"]:
            return
        _scan_state["running"] = True
        _scan_state["progress"] = 0
        _scan_state["message"] = "Scanning..."
        _scan_state["error"] = None

    base = cwd or os.getcwd()
    paths = _scan_paths()
    total = len(paths) + 1  # +1 for desktop shortcuts
    executables = {}

    try:
        for i, path in enumerate(paths):
            with _scan_lock:
                _scan_state["progress"] = int((i / total) * 100)
                _scan_state["message"] = f"Scanning {path[:50]}..."
            found = find_executables(path)
            executables.update(found)

        desktop = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")
        with _scan_lock:
            _scan_state["progress"] = int((total - 1) / total * 100)
            _scan_state["message"] = "Reading desktop shortcuts..."
        shortcuts = find_shortcuts(desktop)
        for name, path in shortcuts.items():
            executables[name] = path

        exec_file = os.path.join(base, "executables.json")
        save_executables(executables, exec_file)
        try:
            from backend.assistant_core import clear_caches
            clear_caches()
        except Exception:
            pass
        with _scan_lock:
            _scan_state["running"] = False
            _scan_state["progress"] = 100
            _scan_state["message"] = "Scan complete!"
    except Exception as e:
        with _scan_lock:
            _scan_state["running"] = False
            _scan_state["progress"] = 0
            _scan_state["message"] = "Scan failed."
            _scan_state["error"] = str(e)


def get_scan_state() -> dict[str, Any]:
    with _scan_lock:
        return dict(_scan_state)
