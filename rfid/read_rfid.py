# file: rfid_read_simple.py
import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522

# Use BCM pin numbering
GPIO.setmode(GPIO.BCM)

# Setup for RFID reader
reader = SimpleMFRC522()
charging_active = False

# Setup for LED
LED_PIN = 17
GPIO.setup(LED_PIN, GPIO.OUT)


def read_rfid():
    """
    Read the RFID card and return the tag ID and text
    """
    print("Hold a tag near the reader...")
    tag_id, text = reader.read()

    print(f"Tag ID: {tag_id}")
    if text:
        print(f"Text: {text.strip()}")
    else:
        print("No text data on tag.")

    return tag_id, text

def set_charging_state():
    global charging_active
    if charging_active:
        print("Stop charging.")
        charging_active = False
    else:
        print("Start charging.")
        charging_active = True

def toggle_relay():
    global charging_active
    print("Toggling relay")
    GPIO.output(RELAY_PIN, GPIO.LOW if charging_active else GPIO.HIGH)

try:
    while True:
        tag_id, text = read_rfid()
        set_charging_state()
        toggle_relay()

        print("-" * 30)  # Add separator between reads
finally:
    GPIO.cleanup()
