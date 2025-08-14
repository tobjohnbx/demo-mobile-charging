# file: rfid_read_simple.py
import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
import time

# Use BCM pin numbering
GPIO.setmode(GPIO.BCM)

# Setup for RFID reader
reader = SimpleMFRC522()
charging_active = False

# Setup for LED
LED_PIN = 17
GPIO.setup(LED_PIN, GPIO.OUT)

# Debounce variables
last_tag_id = None
last_read_time = 0
DEBOUNCE_TIME = 2.0  # 2 seconds cooldown between reads of the same tag

def read_rfid():
    """
    Read the RFID card and return the tag ID and text
    """
    print("Hold a tag near the reader...")
    try:
        tag_id, text = reader.read()
        
        print(f"Tag ID: {tag_id}")
        if text:
            print(f"Text: {text.strip()}")
        else:
            print("No text data on tag.")
        
        return tag_id, text
    except:
        # Return None if no tag is detected or read fails
        return None, None

def should_process_tag(tag_id):
    """
    Check if we should process this tag based on debounce logic
    """
    global last_tag_id, last_read_time
    
    if tag_id is None:
        return False
    
    current_time = time.time()
    
    # If it's a different tag, always process it
    if tag_id != last_tag_id:
        return True
    
    # If it's the same tag, only process if enough time has passed
    if current_time - last_read_time >= DEBOUNCE_TIME:
        return True
    
    return False

def set_charging_state():
    global charging_active
    if charging_active:
        print("Stop charging.")
        charging_active = False
    else:
        print("Start charging.")
        charging_active = True

def toggle_led():
    print("Toggling LED")

try:
    while True:
        tag_id, text = read_rfid()
        
        if should_process_tag(tag_id):
            # Update tracking variables
            last_tag_id = tag_id
            last_read_time = time.time()
            
            set_charging_state()
            toggle_led()
            print("-" * 30)  # Add separator between reads
        else:
            # Small delay to prevent busy waiting
            time.sleep(0.1)
            
finally:
    GPIO.cleanup()
