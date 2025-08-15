# Nitrobox PDF Downloader (FastAPI, Kiosk-ready)

Server für Messebetrieb: nimmt `customerIdent` per POST an, wartet asynchron auf ein **neues** Dokument, lädt es herunter und der Kiosk zeigt **immer die neueste PDF**.

## Endpunkte

- `POST /download` – non-blocking, **202 Accepted**
  ```json
  { "customerIdent": "06cc07ed-8aa4-4111-ab75-a39ff18aba2c", "waitSeconds": 120, "pollSeconds": 5 }
  ```
  Antwort:
  ```json
  { "status": "accepted", "customerIdent": "..." }
  ```

- `GET /healthz` – Health-Check

## Verhalten gegen "altes Dokument nach Neustart"

- Persistenter Speicher in `.state/last_idents.json`: pro `customerIdent` wird der **zuletzt bekannte** `documentIdent` gesichert.
- Beim **ersten** Aufruf nach Neustart (wenn noch kein Eintrag existiert) wird **kein** altes Dokument geladen:
  der aktuelle Ident wird nur gespeichert, bis ein **neuer** Ident erscheint → dann PDF-Download & Anzeige.
- Beim App-Start wird `downloads/` bereinigt: **pro Customer** bleibt nur die neueste PDF erhalten.

## Installation

1. Python 3.10+
2. Projekt entpacken, dann:
   ```bash
   cd nitrobox_pdf_server
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   cp .env.example .env  # und Credentials eintragen
   ```

## Start

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

Swagger-UI: `http://<pi-ip>:8000/docs`

## Konfiguration (.env)

```ini
NITROBOX_BASE_URL=https://api.nbx-stage-westeurope.nitrobox.io
NITROBOX_OAUTH_REALM=demo-mobile-charging

# Credentials NUR aus Umgebungsvariablen:
NITROBOX_CLIENT_ID=your_client_id
NITROBOX_CLIENT_SECRET=your_client_secret
# oder alternativ bereits base64-codiert:
# NITROBOX_BASIC_CREDENTIALS_B64=base64(client_id:client_secret)

DOWNLOAD_DIR=downloads
STATE_DIR=.state
LOG_LEVEL=INFO

# Polling-Defaults (können pro Request überschrieben werden)
DEFAULT_WAIT_SECONDS=120
DEFAULT_POLL_SECONDS=5
```

## Kiosk

- `kiosk_latest_pdf.py` überwacht `downloads/` und öffnet **immer die neueste PDF im Vollbild**, schließt alte Anzeige.
- Standard-Viewer: `evince --fullscreen` (alternativ `chromium-browser --kiosk`, `mupdf`, `xdg-open`).

## Systemd (Autostart)

Siehe `AUTOSTART.md`:
- `nitrobox-api.service`: startet die API beim Booten (bindet an `0.0.0.0:8000`).
- `pdf-kiosk.service`: startet nach Desktop, deaktiviert Screen-Blanking (xset), zeigt neueste PDF.

## Logs & Polling-Zähler

- Background-Task loggt **Attempts** und beendet sich zuverlässig nach Timeout (monotonic-Deadline).
- Logs via:
  ```bash
  journalctl -u nitrobox-api.service -f
  ```
