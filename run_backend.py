"""
Start the Fupo FastAPI backend. Run this from any directory; it sets up the
project root so the 'backend' package is found and settings/executables paths work.

Usage:
    python run_backend.py
"""
import os
import sys

# Project root = directory containing this script
_root = os.path.dirname(os.path.abspath(__file__))
if _root not in sys.path:
    sys.path.insert(0, _root)
os.chdir(_root)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api:app", host="127.0.0.1", port=8000, reload=True)
