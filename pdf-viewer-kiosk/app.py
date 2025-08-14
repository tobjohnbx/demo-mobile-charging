#!/usr/bin/env python3
import os
import base64
import logging
from typing import Optional
from datetime import datetime
from pathlib import Path

import requests
from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
import time
import re
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s"
)
logger = logging.getLogger("nitrobox-pdf-server")

app = FastAPI(title="Nitrobox PDF Downloader", version="1.0.0")

@app.on_event("startup")
def on_startup():
    """
    Beim Start: downloads/ säubern, sodass je customerIdent nur die aktuellste PDF bleibt.
    """
    try:
        # Reuse cleanup logic: keep newest per customer
        from pathlib import Path
        import re
        groups = {}
        pattern = re.compile(r"^(?P<customer>[A-Za-z0-9-]+)-(?P<doc>[A-Za-z0-9-]+)-(?P<ts>\d{8}T\d{6}Z)-.+\.pdf$")
        for p in DOWNLOAD_DIR.glob("*.pdf"):
            m = pattern.match(p.name)
            if not m:
                continue
            cust = m.group("customer")
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

# --- Config ---
BASE_URL = os.getenv("NITROBOX_BASE_URL", "https://api.nbx-stage-westeurope.nitrobox.io")
OAUTH_REALM = os.getenv("NITROBOX_OAUTH_REALM", "demo-mobile-charging")
CLIENT_ID = os.getenv("NITROBOX_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("NITROBOX_CLIENT_SECRET", "")
BASIC_CREDENTIALS_B64 = os.getenv("NITROBOX_BASIC_CREDENTIALS_B64", "")  # optional, base64(client_id:client_secret)
DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", "downloads"))
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

TIMEOUT = (10, 60)  # (connect, read) seconds


class DownloadRequest(BaseModel):
    customerIdent: str
    waitSeconds: int | None = None
    pollSeconds: float | None = None


def _basic_auth_header() -> str:
    """
    Build the HTTP Basic Authorization header value.
    Prefers explicit client id/secret; falls back to pre-encoded base64 if provided.
    """
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
    # match IntelliJ HTTP search param, encoded quotes around ident
    # Example: search=customerDetail.customerIdent=='<customerIdent>'
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
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    resp = requests.get(url, headers=headers, params=params, timeout=TIMEOUT)
    if resp.status_code != 200:
        logger.error("Documents request failed: %s %s", resp.status_code, resp.text[:500])
        raise HTTPException(status_code=502, detail="Failed to fetch documents for customer")
    data = resp.json()
    embedded = data.get("_embedded") or data.get("embedded") or {}
    # Sometimes it's a dict with a 'documents' array; handle both shapes.
    items = None
    if isinstance(embedded, dict):
        items = embedded.get("documents") or embedded.get("items")
        # IntelliJ example uses _embedded[0]; also support _embedded as list
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
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/pdf, application/octet-stream",
    }
    resp = requests.get(url, headers=headers, timeout=TIMEOUT)
    if resp.status_code != 200:
        logger.error("File download failed: %s %s", resp.status_code, resp.text[:500])
        raise HTTPException(status_code=502, detail="Failed to download file")
    # Try to infer a filename from Content-Disposition
    filename = f"{file_ident}.pdf"
    cd = resp.headers.get("Content-Disposition") or resp.headers.get("content-disposition")
    if cd and "filename=" in cd:
        # naive parse; remove quotes if present
        fn = cd.split("filename=")[-1].strip().strip('";')
        if fn:
            filename = fn
    return resp.content, filename



def download_endpoint(payload: DownloadRequest):
    """
    Wartet optional auf ein *neues* Dokument (im Vergleich zu bereits heruntergeladenen PDFs),
    wiederholt die Doc-Abfrage und lädt erst dann herunter.
    - payload.waitSeconds: maximale Wartezeit (Standard: 120s, via ENV DEFAULT_WAIT_SECONDS)
    - payload.pollSeconds: Intervall zwischen Abfragen (Standard: 5s, via ENV DEFAULT_POLL_SECONDS)
    """
    customer_ident = payload.customerIdent.strip()
    if not customer_ident:
        raise HTTPException(status_code=400, detail="customerIdent must not be empty")
    logger.info("Received download request for customerIdent=%s", customer_ident)

    # Defaults (ENV override-able)
    DEFAULT_WAIT_SECONDS = int(os.getenv("DEFAULT_WAIT_SECONDS", "120"))
    DEFAULT_POLL_SECONDS = float(os.getenv("DEFAULT_POLL_SECONDS", "5"))
    wait_seconds = payload.waitSeconds if payload.waitSeconds is not None else DEFAULT_WAIT_SECONDS
    poll_seconds = payload.pollSeconds if payload.pollSeconds is not None else DEFAULT_POLL_SECONDS

    # Build set of already-downloaded document idents (loose match: "-<ident>-" in filename)
    def is_ident_downloaded(doc_ident: str) -> bool:
        for p in DOWNLOAD_DIR.glob("*.pdf"):
            name = p.name
            # quick containment check
            if f"-{doc_ident}-" in name:
                return True
        return False

    token = get_access_token()

    t0 = time.time()
    last_seen_ident = None
    while True:
        try:
            document_ident = get_latest_document_ident(token, customer_ident)
        except HTTPException as e:
            # If token expired or transient, retry once with a fresh token
            if e.status_code == 502:
                logger.info("Retrying with fresh token after 502 from documents...")
                token = get_access_token()
                document_ident = get_latest_document_ident(token, customer_ident)
            else:
                raise

        if not is_ident_downloaded(document_ident):
            # Found a *new* document -> download and save
            content, suggested_name = download_file(token, document_ident)
            timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
            safe_name = suggested_name.replace("/", "_").replace("\\", "_")
            local_name = f"{customer_ident}-{document_ident}-{timestamp}-{safe_name}"
            dest = DOWNLOAD_DIR / local_name
            with open(dest, "wb") as f:
                f.write(content)
            logger.info("Saved NEW PDF to %s", dest)
            return JSONResponse({
                "status": "ok",
                "customerIdent": customer_ident,
                "documentIdent": document_ident,
                "savedPath": str(dest),
                "bytes": len(content)
            })

        # else: latest is already downloaded -> wait/poll again until timeout
        if last_seen_ident != document_ident:
            logger.info("Latest document %s already downloaded. Waiting for a new one...", document_ident)
            last_seen_ident = document_ident

        if time.time() - t0 >= wait_seconds:
            # Timeout: nothing new
            return JSONResponse({
                "status": "no_new_document",
                "customerIdent": customer_ident,
                "latestDocumentIdent": document_ident,
                "message": f"No new document within {wait_seconds} seconds"
            }, status_code=204)

        time.sleep(poll_seconds)



def _already_downloaded(doc_ident: str) -> bool:
    for p in DOWNLOAD_DIR.glob("*.pdf"):
        if f"-{doc_ident}-" in p.name:
            return True
    return False


def process_download_background(customer_ident: str, wait_seconds: int, poll_seconds: float):
    """
    Background task:
    - polls documents for the latest ident
    - compares against existing downloads
    - downloads new PDF when available
    - stops after wait_seconds if nothing new appeared
    """
    logger.info("[BG] Start for customerIdent=%s wait=%ss poll=%ss", customer_ident, wait_seconds, poll_seconds)
    try:
        token = get_access_token()
    except Exception as e:
        logger.error("[BG] token error: %s", e)
        return

    t0 = time.time()
    last_logged_ident = None

    while True:
        try:
            document_ident = get_latest_document_ident(token, customer_ident)
        except HTTPException as e:
            if e.status_code == 502:
                # retry with fresh token once
                try:
                    logger.info("[BG] retrying with fresh token...")
                    token = get_access_token()
                    document_ident = get_latest_document_ident(token, customer_ident)
                except Exception as ie:
                    logger.error("[BG] failed after retry: %s", ie)
                    break
            else:
                logger.error("[BG] documents error: %s", e.detail)
                break
        except Exception as e:
            logger.error("[BG] unexpected documents error: %s", e)
            break

        if not _already_downloaded(document_ident):
            try:
                content, suggested_name = download_file(token, document_ident)
                timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
                safe_name = suggested_name.replace("/", "_").replace("\\", "_")
                local_name = f"{customer_ident}-{document_ident}-{timestamp}-{safe_name}"
                dest = DOWNLOAD_DIR / local_name
                with open(dest, "wb") as f:
                    f.write(content)
                logger.info("[BG] Saved NEW PDF to %s", dest)
            except Exception as e:
                logger.error("[BG] download/save error: %s", e)
            break  # finished

        if last_logged_ident != document_ident:
            logger.info("[BG] Latest document %s already downloaded. Waiting for a new one...", document_ident)
            last_logged_ident = document_ident

        if time.time() - t0 >= wait_seconds:
            logger.info("[BG] No new document within %ss. Stopping.", wait_seconds)
            break

        time.sleep(poll_seconds)

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.post("/download", status_code=202)
def download_endpoint(payload: DownloadRequest, background_tasks: BackgroundTasks):
    """
    Non-blocking: startet einen Hintergrund-Task und liefert 202 Accepted zurück.
    Der Task sucht nach einem *neuen* Dokument und lädt es herunter.
    Warte-/Polling-Zeiten sind optional steuerbar, betreffen nur den Hintergrund-Task.
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

