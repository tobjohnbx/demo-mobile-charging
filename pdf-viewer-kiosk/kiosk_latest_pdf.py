#!/usr/bin/env python3
import os
import time
import subprocess
from pathlib import Path
from typing import Optional

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except Exception:
    WATCHDOG_AVAILABLE = False

DEFAULT_DIR = os.environ.get("DOWNLOAD_DIR", "downloads")
DEFAULT_VIEWER = os.environ.get("PDF_VIEWER", "evince")  # evince | chromium-browser | mupdf | xdg-open
FULLSCREEN_ARGS = {
    "evince": ["--fullscreen"],
    "chromium-browser": ["--kiosk", "--disable-infobars", "--noerrdialogs"],
    "chromium": ["--kiosk", "--disable-infobars", "--noerrdialogs"],
    "mupdf": [],
    "xdg-open": [],
}

class PDFKiosk:
    def __init__(self, directory: Path, viewer: str = "evince", poll_seconds: float = 3.0):
        self.directory = directory
        self.viewer = viewer
        self.poll_seconds = poll_seconds
        self.current_proc: Optional[subprocess.Popen] = None
        self.current_path: Optional[Path] = None
        self.fullscreen_args = FULLSCREEN_ARGS.get(viewer, [])

    def _latest_pdf(self) -> Optional[Path]:
        pdfs = list(self.directory.glob("*.pdf"))
        if not pdfs:
            return None
        return max(pdfs, key=lambda p: p.stat().st_mtime)

    def _open_pdf(self, path: Path):
        self._close_current()
        cmd = [self.viewer]
        if self.viewer.startswith("chromium"):
            cmd += self.fullscreen_args + [f"file://{path.resolve()}"]
        else:
            cmd += self.fullscreen_args + [str(path.resolve())]
        self.current_path = path
        self.current_proc = subprocess.Popen(cmd)

    def _close_current(self):
        if self.current_proc and self.current_proc.poll() is None:
            try:
                self.current_proc.terminate()
                try:
                    self.current_proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.current_proc.kill()
            except Exception:
                pass
        self.current_proc = None
        self.current_path = None

    def show_latest_now(self):
        latest = self._latest_pdf()
        if latest and latest != self.current_path:
            self._open_pdf(latest)

    def run_watchdog(self):
        class Handler(FileSystemEventHandler):
            def __init__(self, kiosk: "PDFKiosk"):
                self.kiosk = kiosk
            def on_created(self, event):
                if not event.is_directory and event.src_path.endswith(".pdf"):
                    time.sleep(0.2)
                    self.kiosk.show_latest_now()
            def on_modified(self, event):
                if not event.is_directory and event.src_path.endswith(".pdf"):
                    time.sleep(0.2)
                    self.kiosk.show_latest_now()

        observer = Observer()
        handler = Handler(self)
        observer.schedule(handler, str(self.directory), recursive=False)
        observer.start()
        try:
            self.show_latest_now()
            while True:
                time.sleep(1)
        finally:
            observer.stop()
            observer.join()
            self._close_current()

    def run_polling(self):
        self.show_latest_now()
        last_seen = self.current_path.stat().st_mtime if self.current_path else None
        try:
            while True:
                latest = self._latest_pdf()
                mtime = latest.stat().st_mtime if latest else None
                if latest and (self.current_path is None or latest != self.current_path or mtime != last_seen):
                    self._open_pdf(latest)
                    last_seen = mtime
                time.sleep(self.poll_seconds)
        finally:
            self._close_current()

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Open always the newest PDF in fullscreen and close the previous one.")
    parser.add_argument("--dir", default=DEFAULT_DIR, help="Downloads directory (default: downloads or $DOWNLOAD_DIR)")
    parser.add_argument("--viewer", default=DEFAULT_VIEWER, help="PDF viewer command (evince|chromium-browser|mupdf|xdg-open)")
    parser.add_argument("--poll-seconds", type=float, default=3.0, help="Polling interval if watchdog not available")
    args = parser.parse_args()

    directory = Path(args.dir)
    directory.mkdir(parents=True, exist_ok=True)

    kiosk = PDFKiosk(directory=directory, viewer=args.viewer, poll_seconds=args.poll_seconds)
    if WATCHDOG_AVAILABLE:
        kiosk.run_watchdog()
    else:
        kiosk.run_polling()

if __name__ == "__main__":
    main()
