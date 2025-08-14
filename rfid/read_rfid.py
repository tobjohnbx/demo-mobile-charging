# file: rfid_read_simple.py
import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522

reader = SimpleMFRC522()

try:
    print("Hold a tag near the reader...")
    tag_id, text = reader.read()
    print(f"Tag ID: {tag_id}")
    if text:
        print(f"Text: {text.strip()}")
    else:
        print("No text data on tag.")
finally:
    GPIO.cleanup()