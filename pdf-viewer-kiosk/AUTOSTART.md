# Autostart / Kiosk auf Raspberry Pi

## Installation der Viewer/Tools
```bash
sudo apt update
sudo apt install -y evince python3-pip
# optional Datei-Events (schneller als Polling)
pip3 install watchdog
```

## FastAPI beim Booten starten (Systemd)
```bash
cd ~/pdf-viewer-kiosk
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

sudo cp nitrobox-api.service /etc/systemd/system/nitrobox-api.service
sudo systemctl daemon-reload
sudo systemctl enable nitrobox-api.service
sudo systemctl start nitrobox-api.service
```

## Kiosk (Vollbild) beim Booten starten
```bash
sudo cp pdf-kiosk.service /etc/systemd/system/pdf-kiosk.service
sudo systemctl daemon-reload
sudo systemctl enable pdf-kiosk.service
sudo systemctl start pdf-kiosk.service
```

Der Kiosk-Service deaktiviert Bildschirmschoner/DPMS (xset) und startet z. B. `evince --fullscreen`.
