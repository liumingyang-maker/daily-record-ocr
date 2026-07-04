"""PyInstaller entry point for packaged application."""

import sys
import os
from pathlib import Path

# Ensure the project root is in sys.path so `app` module is found
if getattr(sys, "frozen", False):
    # Running as packaged app
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(BASE_DIR))

from app.main import app
from app.settings import APP_HOST, APP_PORT

if __name__ == "__main__":
    import uvicorn
    import webbrowser
    import threading

    def open_browser():
        webbrowser.open(f"http://{APP_HOST}:{APP_PORT}")

    threading.Timer(2.0, open_browser).start()
    uvicorn.run(app, host=APP_HOST, port=APP_PORT)
