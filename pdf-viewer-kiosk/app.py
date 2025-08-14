#!/usr/bin/env python3
import os
import re
import json
import time
import base64
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s"
)
logger = logging.getLogger("nitrobox-pdf-server")

app = FastAPI(title="Nitrobox PDF Downloader", version="1.1.0")

# --- Config ---
BASE_URL = os.getenv("NITROBOX_BASE_URL", "https://api.nbx-stage-westeurope.nitrobox.io")
OAUTH_REALM = os.getenv("NITROBOX_OAUTH_REALM", "demo-mobile-charging")
# Credentials: nur aus ENV/.env
CLIENT_ID = os.getenv("NITROBOX_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("NITROBOX_CLIENT_SECRET", "")
BASIC_CREDENTIALS_B64 = os.getenv("NITROBOX_BASIC_CREDENTIALS_B64", "")  # alternativ: base64(client:secret)

DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", "downloads"))
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

TIMEOUT = (10, 60)  # (connect, read) seconds

# --- Persistenter "last ident" Zustand ---
STATE_DIR = Path(os.getenv("STATE_DIR", ".state"))
STATE_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = STATE_DIR / "last_idents.json"

try:
    import threading
    _state_lock = threading.Lock()
except Exception:
    _state_lock = None

def _load_state() -> dict:
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.warning("Failed to load state file %s: %s", STATE_FILE, e)
    return {}

def _save_state(state: dict) -> None:
    tmp = STATE_FILE.with_suffix(".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        os.replace(tmp, STATE_FILE)
    except Exception as e:
        logger.warning("Failed to save state file %s: %s", STATE_FILE, e)

def get_last_ident(customer_ident: str) -> Optional[str]:
    state = _load_state()
    entry = state.get(customer_ident)
    if isinstance(entry, dict):
        return entry.get("lastDocumentIdent")
    if isinstance(entry, str):
        return entry
    return None

def set_last_ident(customer_ident: str, document_ident: str) -> None:
    if _state_lock:
        _state_lock.acquire()
    try:
        state = _load_state()
        state[customer_ident] = {
            "lastDocumentIdent": document_ident,
            "updatedAt": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        }
        _save_state(state)
    finally:
        if _state_lock:
            _state_lock.release()

class DownloadRequest(BaseModel):
    customerIdent: str
    waitSeconds: int | None = None
    pollSeconds: float | None = None

def _basic_auth_header() -> str:
    # Nur aus ENV
    if CLIENT_ID and CLIENT_SECRET:
        token = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode("utf-8")).decode("ascii")
        return f"Basic {token}"
    if BASIC_CREDENTIALS_B64:
        return f"Basic {BASIC_CREDENTIALS_B64}"
    raise RuntimeError("Missing credentials: set NITROBOX_CLIENT_ID and NITROBOX_CLIENT_SECRET, "
                       "or NITROBOX_BASIC_CREDENTIALS_B64")

def get_access_token() -> str:
    url = f"{BASE_URL}/{OAUTH_REALM}/oauth2/token"
    params = {"grant_type": "client_credentials"}
    headers = {
        "Authorization": _basic_auth_header(),
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    resp = requests.post(url, headers=headers, params=params, timeout=TIMEOUT)
    if resp.status_code != 200:
        logger.error("Token request failed: %s %s", resp.status_code, resp.text[:500])
        raise HTTPException(status_code=502, detail="Failed to obtain access token from Nitrobox")
    data = resp.json()
    token = data.get("access_token")
    if not token:
        raise HTTPException(status_code=502, detail="Nitrobox token response missing access_token")
    return token

def get_latest_document_ident(token: str, customer_ident: str) -> str:
    url = f"{BASE_URL}/v2/documents"
    search = f"customerDetail.customerIdent=='{customer_ident}'"
    params = {
        "search": search,
        "pageNumber": 0,
        "page": 0,
        "pageSize": 20,
        "size": 20,
        "sort": "documentDate,desc",
        "orderBy": "documentDate",
        "direction": "DESC",
    }
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    resp = requests.get(url, headers=headers, params=params, timeout=TIMEOUT)
    if resp.status_code != 200:
        logger.error("Documents request failed: %s %s", resp.status_code, resp.text[:500])
        raise HTTPException(status_code=502, detail="Failed to fetch documents for customer")
    data = resp.json()
    embedded = data.get("_embedded") or data.get("embedded") or {}
    items = None
    if isinstance(embedded, dict):
        items = embedded.get("documents") or embedded.get("items")
    if items is None and isinstance(embedded, list):
        items = embedded
    if not items:
        raise HTTPException(status_code=404, detail="No documents found for the given customerIdent")
    first = items[0]
    ident = first.get("ident") if isinstance(first, dict) else None
    if not ident:
        raise HTTPException(status_code=502, detail="Malformed documents response: missing ident")
    return ident

def download_file(token: str, file_ident: str) -> tuple[bytes, str]:
    url = f"{BASE_URL}/v2/files/{file_ident}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/pdf, application/octet-stream"}
    resp = requests.get(url, headers=headers, timeout=TIMEOUT)
    if resp.status_code != 200:
        logger.error("File download failed: %s %s", resp.status_code, resp.text[:500])
        raise HTTPException(status_code=502, detail="Failed to download file")
    filename = f"{file_ident}.pdf"
    cd = resp.headers.get("Content-Disposition") or resp.headers.get("content-disposition")
    if cd and "filename=" in cd:
        fn = cd.split("filename=")[-1].strip().strip('";')
        if fn:
            filename = fn
    return resp.content, filename

@app.on_event("startup")
def on_startup():
    """
    Beim Start: downloads/ säubern, sodass je customerIdent nur die aktuellste PDF bleibt.
    """
    try:
        pattern = re.compile(r"^(?P<cust>[A-Za-z0-9-]+)-(?P<doc>[A-Za-z0-9-]+)-(?P<ts>\d{8}T\d{6}Z)-.+\.pdf$")
        groups: dict[str, list[Path]] = {}
        for p in DOWNLOAD_DIR.glob("*.pdf"):
            m = pattern.match(p.name)
            if not m:
                continue
            cust = m.group("cust")
            groups.setdefault(cust, []).append(p)
        for cust, files in groups.items():
            if len(files) <= 1:
                continue
            files_sorted = sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)
            for old in files_sorted[1:]:
                try:
                    old.unlink()
                    logger.info("Startup cleanup: removed %s", old)
                except Exception as e:
                    logger.warning("Startup cleanup: could not remove %s: %s", old, e)
    except Exception as e:
        logger.warning("Startup cleanup failed: %s", e)

def process_download_background(customer_ident: str, wait_seconds: int, poll_seconds: float):
    """
    Background task with strict timeout:
    - initial ident holen
    - wenn noch kein lastIdent vorhanden: nur merken, NICHT downloaden (vermeidet alte Anzeige nach Neustart)
    - sonst: bis zur Deadline pollen, bis ein neuer ident auftaucht -> dann downloaden & lastIdent aktualisieren
    """
    # Parameter absichern
    try:
        wait_seconds = int(wait_seconds)
    except Exception:
        wait_seconds = 120
    try:
        poll_seconds = float(poll_seconds)
    except Exception:
        poll_seconds = 5.0
    if poll_seconds <= 0:
        poll_seconds = 1.0

    deadline = time.monotonic() + wait_seconds
    attempt = 1
    logger.info("[BG] Start for customerIdent=%s wait=%ss poll=%ss", customer_ident, wait_seconds, poll_seconds)

    # Token holen
    try:
        token = get_access_token()
    except Exception as e:
        logger.error("[BG] token error: %s", e)
        return

    # Initial ident
    try:
        current_ident = get_latest_document_ident(token, customer_ident)
    except HTTPException as e:
        logger.error("[BG] initial documents error: %s", e.detail)
        return
    except Exception as e:
        logger.error("[BG] initial documents error: %s", e)
        return

    known_ident = get_last_ident(customer_ident)

    # Erstaufruf -> nur merken, nicht downloaden
    if not known_ident:
        set_last_ident(customer_ident, current_ident)
        logger.info("[BG] No lastIdent for %s -> remember %s and exit (avoid showing old document)", customer_ident, current_ident)
        return

    last_logged_ident = None
    try:
        while True:
            now = time.monotonic()
            if now >= deadline:
                logger.info("[BG] Timeout reached for %s after %d attempts. Stopping.", customer_ident, attempt)
                break

            logger.info("[BG] Attempt %d for customer %s (known=%s, current=%s)", attempt, customer_ident, known_ident, current_ident)

            if current_ident != known_ident:
                try:
                    content, suggested_name = download_file(token, current_ident)
                    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
                    safe_name = suggested_name.replace("/", "_").replace("\\", "_")
                    local_name = f"{customer_ident}-{current_ident}-{timestamp}-{safe_name}"
                    dest = DOWNLOAD_DIR / local_name
                    with open(dest, "wb") as f:
                        f.write(content)
                    logger.info("[BG] Saved NEW PDF to %s", dest)
                    set_last_ident(customer_ident, current_ident)
                    logger.info("[BG] Finished after %d attempts (new document found for %s)", attempt, customer_ident)
                except Exception as e:
                    logger.error("[BG] download/save error: %s", e)
                break  # fertig

            if last_logged_ident != current_ident:
                logger.info("[BG] Latest ident %s equals lastIdent for %s. Waiting for a new document...", current_ident, customer_ident)
                last_logged_ident = current_ident

            # warten (gedeckelt bis zur Deadline)
            sleep_left = max(0.0, min(poll_seconds, max(0.0, deadline - time.monotonic())))
            if sleep_left == 0:
                logger.info("[BG] Timeout reached for %s after %d attempts (no new document).", customer_ident, attempt)
                break
            time.sleep(sleep_left)

            # refresh ident, 1 retry mit neuem Token
            try:
                current_ident = get_latest_document_ident(token, customer_ident)
            except Exception as e:
                logger.warning("[BG] polling documents failed once: %s", e)
                if time.monotonic() < deadline:
                    time.sleep(min(1.0, max(0.0, deadline - time.monotonic())))
                    try:
                        token = get_access_token()
                        current_ident = get_latest_document_ident(token, customer_ident)
                    except Exception as e2:
                        logger.error("[BG] polling retry failed: %s", e2)
                        break
                else:
                    break

            attempt += 1
    finally:
        logger.info("[BG] Exit background task for %s (attempts=%d)", customer_ident, attempt)

@app.post("/download", status_code=202)
def download_endpoint(payload: DownloadRequest, background_tasks: BackgroundTasks):
    """
    Non-blocking: startet einen Hintergrund-Task und liefert 202 Accepted zurück.
    Der Task sucht nach einem *neuen* Dokument und lädt es herunter.
    """
    customer_ident = payload.customerIdent.strip()
    if not customer_ident:
        raise HTTPException(status_code=400, detail="customerIdent must not be empty")

    DEFAULT_WAIT_SECONDS = int(os.getenv("DEFAULT_WAIT_SECONDS", "120"))
    DEFAULT_POLL_SECONDS = float(os.getenv("DEFAULT_POLL_SECONDS", "5"))
    wait_seconds = payload.waitSeconds if payload.waitSeconds is not None else DEFAULT_WAIT_SECONDS
    poll_seconds = payload.pollSeconds if payload.pollSeconds is not None else DEFAULT_POLL_SECONDS

    background_tasks.add_task(process_download_background, customer_ident, wait_seconds, poll_seconds)
    logger.info("Accepted download request for customerIdent=%s (bg wait=%ss poll=%ss)", customer_ident, wait_seconds, poll_seconds)
    return {"status": "accepted", "customerIdent": customer_ident}

@app.get("/healthz")
def healthz():
    return {"status": "ok"}
