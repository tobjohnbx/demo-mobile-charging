# Nitrobox PDF Downloader (FastAPI)

Ein kleiner FastAPI-Webserver, der `customerIdent` per HTTP POST entgegennimmt, das aktuellste Dokument über die Nitrobox-API sucht und die zugehörige PDF lokal speichert.

## Endpunkte

- `POST /download`  
  Body (JSON):
  ```json
  { "customerIdent": "06cc07ed-8aa4-4111-ab75-a39ff18aba2c" }
  ```
  Antwort:
  ```json
  {
    "status": "ok",
    "customerIdent": "...",
    "documentIdent": "...",
    "savedPath": "downloads/<datei>.pdf",
    "bytes": 12345
  }
  ```

- `GET /healthz` – einfacher Health-Check

## Einrichtung

1. **Python 3.10+ installieren**

2. **Repository/Projekt entpacken** und ins Verzeichnis wechseln:
   ```bash
   cd nitrobox_pdf_server
   ```

3. **Virtuelle Umgebung (empfohlen):**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

4. **Abhängigkeiten installieren:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Konfiguration (.env):**  
   Erstellen Sie eine `.env`-Datei (oder kopieren Sie `.env.example`):
   ```ini
   NITROBOX_BASE_URL=https://api.nbx-stage-westeurope.nitrobox.io
   NITROBOX_OAUTH_REALM=demo-mobile-charging
   # Variante A: Client-ID und -Secret (bevorzugt)
   NITROBOX_CLIENT_ID=your_client_id
   NITROBOX_CLIENT_SECRET=your_client_secret
   # Variante B: Bereits base64-codierte Basic-Credentials (client_id:client_secret)
   # NITROBOX_BASIC_CREDENTIALS_B64=base64_of_clientid:secret
   DOWNLOAD_DIR=downloads
   LOG_LEVEL=INFO
   ```

## Start

```bash
uvicorn app:app --reload --port 8000
```

Jetzt können Sie z. B. mit `curl` testen:

```bash
curl -X POST http://localhost:8000/download \
  -H "Content-Type: application/json" \
  -d '{"customerIdent":"06cc07ed-8aa4-4111-ab75-a39ff18aba2c"}'
```

Die PDF wird im Ordner `downloads/` abgelegt.

## Hinweise

- Der Code folgt dem im HTTP-File gezeigten Flow:
  1. `POST /{realm}/oauth2/token?grant_type=client_credentials` mit Basic Auth
  2. `GET /v2/documents?search=customerDetail.customerIdent=='<ident>'&...&direction=DESC`
  3. erstes Dokument nehmen (`ident`)
  4. `GET /v2/files/{ident}` herunterladen und als PDF speichern
- Fehler werden als HTTP 4xx/5xx zurückgegeben und im Log ausgegeben.
- Passen Sie ggf. `NITROBOX_BASE_URL` und `NITROBOX_OAUTH_REALM` an Ihre Umgebung an.
```

requirements.txt enthält alle nötigen Pakete.


## Warten auf ein neues Dokument

Der Endpunkt `/download` kann optional auf ein **neues** Dokument warten. Dabei wird regelmäßig `/v2/documents` abgefragt
und mit bereits gespeicherten PDFs im `downloads/`-Ordner abgeglichen.

**Body (JSON):**
```json
{
  "customerIdent": "06cc07ed-8aa4-4111-ab75-a39ff18aba2c",
  "waitSeconds": 120,
  "pollSeconds": 5
}
```
- `waitSeconds` – maximale Wartezeit in Sekunden (Default: 120, via ENV `DEFAULT_WAIT_SECONDS`)
- `pollSeconds` – Abfrageintervall in Sekunden (Default: 5, via ENV `DEFAULT_POLL_SECONDS`)

Antwort bei Timeout (keine neue PDF in der Zeit): HTTP 204 mit Body
```json
{
  "status": "no_new_document",
  "customerIdent": "...",
  "latestDocumentIdent": "...",
  "message": "No new document within 120 seconds"
}
```
Wenn ein neues Dokument erscheint, wird es wie gewohnt gespeichert und mit `status=ok` bestätigt.


## Asynchroner Modus (202 Accepted)

`POST /download` blockiert nicht mehr, sondern startet einen **Hintergrund-Task** und antwortet sofort mit **202 Accepted**:
```json
{ "status": "accepted", "customerIdent": "..." }
```
Der Hintergrund-Task pollt die Nitrobox-API in Intervallen (`pollSeconds`) bis
- ein **neues** Dokument (noch nicht im `downloads/`-Ordner vorhanden) gefunden und gespeichert wurde, **oder**
- die maximale Wartezeit (`waitSeconds`) abläuft.

Standardwerte via ENV:
```
DEFAULT_WAIT_SECONDS=120
DEFAULT_POLL_SECONDS=5
```
Optional im Request überschreibbar:
```json
{
  "customerIdent": "…",
  "waitSeconds": 180,
  "pollSeconds": 3
}
```

### Wichtiges Verhalten nach Neustart (veraltete PDFs vermeiden)
- Die App merkt sich pro `customerIdent` den **zuletzt bekannten Dokument-Ident** in `.state/last_idents.json` (persistenter Speicher).
- Beim **ersten** Aufruf nach Neustart (wenn noch kein Eintrag existiert) wird **kein** altes Dokument heruntergeladen.
  Stattdessen wird der aktuelle Ident nur gespeichert und erst bei *Änderung* (neuer Ident) die PDF geholt.
- So wird verhindert, dass direkt nach dem Start ein veraltetes Dokument angezeigt wird, während das neue noch generiert wird.
