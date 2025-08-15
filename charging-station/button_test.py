import RPi.GPIO as GPIO
import time
from PIL import Image, ImageDraw, ImageFont
import board
import busio
from adafruit_ssd1306 import SSD1306_I2C

class ButtonDisplayController:
    """
    Controller für Button-Display Interaktion auf Raspberry Pi 3
    """
    
    def __init__(self):
        # GPIO Setup - Prüfe aktuellen Modus und verwende ihn
        try:
            # Versuche den aktuellen Modus zu ermitteln
            current_mode = GPIO.getmode()
            if current_mode is None:
                # Kein Modus gesetzt, verwende BCM (wie in read_rfid.py)
                GPIO.setmode(GPIO.BCM)
                self.use_bcm = True
                self.BUTTON_PIN = 14  # GPIO 14 (BCM) entspricht Pin 8 (Board)
            elif current_mode == GPIO.BCM:
                # BCM Modus ist bereits gesetzt
                self.use_bcm = True
                self.BUTTON_PIN = 14  # GPIO 14 (BCM)
            else:  # GPIO.BOARD
                # Board Modus ist bereits gesetzt
                self.use_bcm = False
                self.BUTTON_PIN = 8  # Pin 8 (Board)
                
            print(f"GPIO Modus: {'BCM' if self.use_bcm else 'BOARD'}, Button Pin: {self.BUTTON_PIN}")
                
        except Exception as e:
            print(f"GPIO Setup Fehler: {e}")
            # Cleanup und neu versuchen
            GPIO.cleanup()
            GPIO.setmode(GPIO.BCM)
            self.use_bcm = True
            self.BUTTON_PIN = 14
        
        # Button Setup mit Pull-up Widerstand
        GPIO.setup(self.BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Display Setup (I2C Pins: Pin 3 = SDA, Pin 5 = SCL)
        # Pin 17 = 3.3V, Pin 39 = GND
        try:
            self.i2c = busio.I2C(board.SCL, board.SDA)
            self.display = SSD1306_I2C(128, 64, self.i2c)
            print("Display erfolgreich initialisiert")
        except Exception as e:
            print(f"Display-Initialisierung fehlgeschlagen: {e}")
            self.display = None
        
        # Fonts laden
        try:
            self.font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
            self.font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        except OSError:
            print("Standard-Fonts verwenden (TrueType-Fonts nicht gefunden)")
            self.font_large = ImageFont.load_default()
            self.font_small = ImageFont.load_default()
        
        # Status variablen
        self.button_pressed = False
        self.last_button_state = True  # True = nicht gedrückt (Pull-up)
        
        # Display initialisieren
        if self.display:
            self.clear_display()
            self.show_ready_message()
    
    def clear_display(self):
        """Display löschen"""
        if self.display:
            self.display.fill(0)
            self.display.show()
    
    def show_text(self, text_lines):
        """Text auf Display anzeigen
        
        Args:
            text_lines: Liste von Text-Zeilen zum Anzeigen
        """
        if not self.display:
            print(f"Display nicht verfügbar. Text: {text_lines}")
            return
        
        # Neues Bild erstellen
        image = Image.new("1", (self.display.width, self.display.height))
        draw = ImageDraw.Draw(image)
        
        # Text-Zeilen anzeigen
        y_position = 5
        for i, line in enumerate(text_lines):
            if i == 0:  # Erste Zeile größer
                font = self.font_large
                line_height = 20
            else:
                font = self.font_small
                line_height = 15
            
            # Text zentrieren (vereinfachte Methode)
            try:
                # Neuere PIL Versionen
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
            except AttributeError:
                # Ältere PIL Versionen
                try:
                    text_width = draw.textsize(line, font=font)[0]
                except AttributeError:
                    # Fallback
                    text_width = len(line) * 8
            
            x_position = max(0, (self.display.width - text_width) // 2)
            
            draw.text((x_position, y_position), line, font=font, fill=255)
            y_position += line_height
        
        # Auf Display anzeigen
        self.display.image(image)
        self.display.show()
    
    def show_ready_message(self):
        """Bereites-Status anzeigen"""
        self.show_text([
            "System bereit",
            "",
            "Drücke Button",
            "für Nachricht"
        ])
    
    def show_button_pressed_message(self):
        """Nachricht wenn Button gedrückt wurde"""
        self.show_text([
            "Button gedrückt!",
            "",
            f"Zeit: {time.strftime('%H:%M:%S')}",
            "Raspberry Pi 3"
        ])
    
    def check_button(self):
        """Button-Status prüfen und entsprechend reagieren"""
        current_button_state = GPIO.input(self.BUTTON_PIN)
        
        # Button-Druck erkennen (Flanke von HIGH zu LOW)
        if self.last_button_state == True and current_button_state == False:
            print("Button wurde gedrückt!")
            self.button_pressed = True
            self.show_button_pressed_message()
            time.sleep(0.2)  # Entprellen
        
        # Button losgelassen (nach 3 Sekunden zurück zum Ready-Status)
        elif self.last_button_state == False and current_button_state == True:
            print("Button wurde losgelassen!")
            time.sleep(3)  # 3 Sekunden warten
            self.show_ready_message()
            self.button_pressed = False
        
        self.last_button_state = current_button_state
    
    def run(self):
        """Hauptschleife"""
        print("Button-Display Controller gestartet...")
        print(f"Button Pin: {self.BUTTON_PIN} ({'BCM' if self.use_bcm else 'BOARD'} Modus)")
        print("Drücke Ctrl+C zum Beenden")
        
        try:
            while True:
                self.check_button()
                time.sleep(0.1)  # Kurze Pause
        
        except KeyboardInterrupt:
            print("\nProgramm beendet")
        
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Aufräumen beim Beenden - GPIO nicht zurücksetzen wenn andere Scripts laufen"""
        print("Programm wird beendet...")
        if self.display:
            self.clear_display()
        # GPIO.cleanup() NICHT aufrufen, da andere Scripts möglicherweise noch laufen
        print("Display bereinigt (GPIO bleibt für andere Scripts aktiv)")

# Hauptprogramm
if __name__ == "__main__":
    controller = ButtonDisplayController()
    controller.run()