# file: rfid_read_simple.py
import RPi.GPIO as GPIO
import time
import requests
import json
import os
from datetime import datetime, timedelta
from mfrc522 import SimpleMFRC522
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from display import ChargingDisplay
from request_billing_run import create_nitrobox_billing_run
from create_nitrobox_usage import create_nitrobox_usage
from nitrobox_config import NitroboxConfig


# Use BCM pin numbering
GPIO.setmode(GPIO.BCM)

# Setup for RFID reader
reader = SimpleMFRC522()
charging_active = False
charging_session_start = None

# Setup for LED
RELAY_PIN = 17
GPIO.setup(RELAY_PIN, GPIO.OUT)

# Setup for display
try:
    display = ChargingDisplay()
    print("Display initialized successfully")
except Exception as e:
    print(f"Warning: Could not initialize display: {e}")
    display = None

# Debounce variables
last_tag_id = None
last_read_time = 0
DEBOUNCE_TIME = 2.0  # 2 seconds cooldown between reads of the same tag

def fetch_bearer_token():
    """
    Fetch a bearer token using OAuth2 client credentials flow

    Returns:
        str: Bearer token if successful, None otherwise
    """
    # Get configuration from environment
    try:
        config = NitroboxConfig.from_env()
    except RuntimeError as e:
        print(f"ERROR: Configuration error - {e}")
        return None

    if not config.client_credentials_b64:
        print("ERROR: NITROBOX_CLIENT_CREDENTIALS environment variable not set")
        return None

    try:
        headers = {
            "Authorization": f"Basic {config.client_credentials_b64}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        params = {
            "grant_type": "client_credentials"
        }

        print("Fetching new bearer token from Nitrobox...")

        response = requests.post(
            config.oauth_url,
            headers=headers,
            params=params,
            timeout=30
        )

        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get("access_token")

            if access_token:
                print("✅ Successfully fetched bearer token")
                return access_token
            else:
                print("❌ No access_token in response")
                return None
        else:
            print(f"❌ Failed to fetch bearer token. Status: {response.status_code}")
            print(f"   Response: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Network error when fetching bearer token: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error when fetching bearer token: {e}")
        return None

def read_rfid():
    """
    Read the RFID card and return the tag ID and text
    """
    try:
        tag_id, text = reader.read()
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
    global charging_active, charging_session_start
    
    if charging_active:
        # Ending charging session
        charging_end_time = datetime.now()
        print("Stop charging.")
        
        # Update display
        if display:
            duration_minutes = (charging_end_time - charging_session_start).total_seconds() / 60
            display.show_charging_stopped(duration_minutes)

        # Create usage record in Nitrobox if we have a valid session
        if charging_session_start:
            duration_minutes = (charging_end_time - charging_session_start).total_seconds() / 60
            print(f"Charging session ended. Duration: {duration_minutes:.2f} minutes")

            # Fetch bearer token first
            bearer_token = fetch_bearer_token()
            if not bearer_token:
                print("Failed to get bearer token for usage record")
                if display:
                    display.show_api_error("Auth failed")
                    time.sleep(2)
                    display.show_welcome_message()
                charging_active = False
                charging_session_start = None
                return

            # Create usage record in Nitrobox
            success = create_nitrobox_usage(
                tag_id=last_tag_id,
                charging_start_time=charging_session_start,
                charging_end_time=charging_end_time,
                bearer_token=bearer_token
            )
            
            if success:
                print("Usage record successfully sent to Nitrobox")
                if display:
                    display.show_api_success("Billing processed")
                    time.sleep(2)
                    display.show_welcome_message()

                # After successful usage creation, trigger billing run
                billing_success = create_nitrobox_billing_run(bearer_token)
                if billing_success:
                    print("✅ Billing run also successfully created")
                else:
                    print("⚠️  Usage record created but billing run failed")
            else:
                print("Failed to send usage record to Nitrobox")
                if display:
                    display.show_api_error("Billing failed")
                    time.sleep(2)
                    display.show_welcome_message()

        charging_active = False
        charging_session_start = None
    else:
        # Starting charging session
        charging_session_start = datetime.now()
        print(f"Start charging at {charging_session_start.strftime('%Y-%m-%d %H:%M:%S')}")
        charging_active = True

        # Update display
        if display:
            display.show_charging_started(last_tag_id, charging_session_start)

def toggle_relay():
    global charging_active
    print("Toggling relay")
    GPIO.output(RELAY_PIN, GPIO.HIGH if charging_active else GPIO.LOW)

try:
    print("Hold a tag near the reader...")
    last_charging_display_update = 0

    while True:
        tag_id, text = read_rfid()

        if should_process_tag(tag_id):
            print(f"Tag ID: {tag_id}")

            # Show card detected on display
            if display:
                display.show_card_detected(tag_id)
                time.sleep(1)  # Brief pause to show card detection

            if text:
                print(f"Text: {text.strip()}")
            else:
                print("No text data on tag.")

            # Update tracking variables
            last_tag_id = tag_id
            last_read_time = time.time()

            set_charging_state()
            toggle_relay()
            print("-" * 30)  # Add separator between reads
            print("Hold a tag near the reader...")
        else:
            # Update charging display periodically during active session
            current_time = time.time()
            if charging_active and display and (current_time - last_charging_display_update) > 5:
                duration_minutes = (datetime.now() - charging_session_start).total_seconds() / 60
                display.show_charging_active(charging_session_start, duration_minutes)
                last_charging_display_update = current_time

            # Small delay to prevent busy waiting
            time.sleep(0.1)

finally:
    GPIO.cleanup()
    if display:
        display.clear_display()
