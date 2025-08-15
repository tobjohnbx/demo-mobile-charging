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
        # GPIO Setup
        GPIO.setmode(GPIO.BOARD)  # Verwende Board-Pin Nummerierung
        
        # Button Setup (Pin 8 = GPIO 14, Pin 14 = GND)
        self.BUTTON_PIN = 8
        GPIO.setup(self.BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Display Setup (I2C Pins: Pin 3 = SDA, Pin 5 = SCL)
        # Pin 17 = 3.3V, Pin 39 = GND
        try:
            self.i2c = busio.I2C(board.SCL, board.SDA)
            self.display = SSD1306_I2C(128, 64, self.i2c)
        except Exception as e:
            print(f"Display-Initialisierung fehlgeschlagen: {e}")
            self.display = None
        
        # Fonts laden
        try:
            self.font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
            self.font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        except OSError:
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
                line_height = 25
            else:
                font = self.font_small
                line_height = 17
            
            # Text zentrieren
            text_width = draw.textsize(line, font=font)[0] if hasattr(draw, 'textsize') else len(line) * 8
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
        """Aufräumen beim Beenden"""
        GPIO.cleanup()
        if self.display:
            self.clear_display()
        print("GPIO und Display bereinigt")

# Hauptprogramm
if __name__ == "__main__":
    controller = ButtonDisplayController()
    controller.run()