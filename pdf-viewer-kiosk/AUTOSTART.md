# Autostart / Kiosk auf Raspberry Pi

## Installation der Viewer/Tools
```bash
sudo apt update
sudo apt install -y evince python3-pip
# optional für Datei-Events:
pip3 install watchdog
```

## Systemd Service anlegen
```bash
mkdir -p ~/nitrobox_pdf_server
# Projekt hierher kopieren/entpacken

# Service-Datei
sudo tee /etc/systemd/system/pdf-kiosk.service >/dev/null <<'EOF'
[Unit]
Description=PDF Kiosk (show newest PDF fullscreen)
After=graphical.target

[Service]
Type=simple
User=pi
WorkingDirectory=%h/nitrobox_pdf_server
Environment=DISPLAY=:0
Environment=DOWNLOAD_DIR=%h/nitrobox_pdf_server/downloads
ExecStart=/usr/bin/python3 %h/nitrobox_pdf_server/kiosk_latest_pdf.py --viewer evince
Restart=always
RestartSec=3

[Install]
WantedBy=graphical.target

EOF

sudo systemctl daemon-reload
sudo systemctl enable pdf-kiosk.service
sudo systemctl start pdf-kiosk.service
```

## Optionen
- Standard-Viewer: `evince` (Vollbild). Alternativ:
  - `chromium-browser --kiosk` (PDF im Browser, Kiosk-Mode)
  - `mupdf` (leichtgewichtig, ohne Menü)
- Umgebung:
  - `DOWNLOAD_DIR` definiert den Zielordner (muss zu deinem FastAPI-Server passen).
  - `DISPLAY=:0` setzt die Standard-X-Session (für Raspberry Pi Desktop).

Der Kiosk-Prozess beobachtet den Ordner `downloads/`. Sobald eine neue PDF erscheint (vom API-Downloader), wird diese im Vollbild geöffnet und die alte Anzeige beendet.


## FastAPI beim Booten starten (Systemd)

```bash
# venv erstellen (falls noch nicht geschehen)
cd ~/nitrobox_pdf_server
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Service installieren
sudo cp nitrobox-api.service /etc/systemd/system/nitrobox-api.service
sudo systemctl daemon-reload
sudo systemctl enable nitrobox-api.service
sudo systemctl start nitrobox-api.service
```

- Die App führt beim Start automatisch eine **Aufräumroutine** aus:
  Es bleibt pro `customerIdent` nur die neueste PDF im `downloads/`-Ordner.
- Optional kannst du die Bereinigung manuell ausführen:
  ```bash
  python cleanup_downloads.py
  ```
- Der Kiosk-Service (`pdf-kiosk.service`) startet nach dem Desktop und **wartet** optional auf die API (Unit-Dependency gesetzt).
