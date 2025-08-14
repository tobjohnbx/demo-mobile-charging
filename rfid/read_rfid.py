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

# Use BCM pin numbering
GPIO.setmode(GPIO.BCM)

# Nitrobox API Configuration
NITROBOX_API_URL = "https://api.nbx-stage-westeurope.nitrobox.io/v2/usages"
NITROBOX_BILLING_URL = "https://api.nbx-stage-westeurope.nitrobox.io/v2/billingrun"
NITROBOX_OAUTH_URL = "https://api.nbx-stage-westeurope.nitrobox.io/demo-mobile-charging/oauth2/token"
NITROBOX_CLIENT_CREDENTIALS = os.getenv('NITROBOX_CLIENT_CREDENTIALS')  # Base64 encoded client credentials from environment
NITROBOX_CONTRACT_ID = 2117046
NITROBOX_PRODUCT_IDENT = "9788b7d9-ab3e-4d7e-a483-258d12bc5078"
NITROBOX_DEBTOR_IDENT = "06cc07ed-8aa4-4111-ab75-a39ff18aba2c"

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
    if not NITROBOX_CLIENT_CREDENTIALS:
        print("ERROR: NITROBOX_CLIENT_CREDENTIALS environment variable not set")
        return None
        
    try:
        headers = {
            "Authorization": f"Basic {NITROBOX_CLIENT_CREDENTIALS}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        params = {
            "grant_type": "client_credentials"
        }
        
        print("Fetching new bearer token from Nitrobox...")
        
        response = requests.post(
            NITROBOX_OAUTH_URL,
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

            # Create usage record in Nitrobox
            success = create_nitrobox_usage(
                tag_id=last_tag_id,
                charging_start_time=charging_session_start,
                charging_end_time=charging_end_time
            )
            
            if success:
                print("Usage record successfully sent to Nitrobox")
                if display:
                    display.show_api_success("Billing processed")
                    time.sleep(2)
                    display.show_welcome_message()
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

def create_nitrobox_usage(tag_id, charging_start_time, charging_end_time, energy_consumed_kwh=None):
    """
    Create a usage record in Nitrobox for the charging session
    
    Args:
        tag_id: The RFID tag ID used for authentication
        charging_start_time: DateTime when charging started
        charging_end_time: DateTime when charging ended
        energy_consumed_kwh: Energy consumed in kWh (optional, can be calculated later)
    
    Returns:
        bool: True if successful, False otherwise
    """
    # Fetch bearer token
    bearer_token = fetch_bearer_token()
    if not bearer_token:
        print("ERROR: Could not obtain bearer token. Cannot create usage record.")
        return False
    
    if not NITROBOX_CONTRACT_ID:
        print("ERROR: NITROBOX_CONTRACT_ID not configured")
        return False
    
    # Calculate charging duration in seconds
    duration_seconds = int((charging_end_time - charging_start_time).total_seconds())
    
    # Generate unique usage identifier
    usage_ident = f"rfid-session-{tag_id}-{int(charging_start_time.timestamp())}"
    
    # Prepare the usage data according to Nitrobox API schema (matching curl example)
    usage_data = {
        "productIdent": NITROBOX_PRODUCT_IDENT,
        "contractId": NITROBOX_CONTRACT_ID,
        "usageIdent": usage_ident,
        "unitQuantities": [
            {
                "unitQuantity": duration_seconds,
                "unitQuantityType": "SECOND"
            }
        ],
        "startDate": charging_start_time.isoformat() + "+01:00",
        "endDate": charging_end_time.isoformat() + "Z",
        "taxLocation": {
            "country": "DE"
        }
    }
    
    
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"Bearer {bearer_token}"
    }
    
    try:
        print(f"Sending usage data to Nitrobox for {duration_seconds} seconds of charging...")
        
        response = requests.post(
            NITROBOX_API_URL,
            headers=headers,
            json=usage_data,
            timeout=30
        )
        
        if response.status_code == 201:
            print("✅ Successfully created usage record in Nitrobox")
            
            # After successful usage creation, trigger billing run
            billing_success = create_nitrobox_billing_run(bearer_token)
            if billing_success:
                print("✅ Billing run also successfully created")
            else:
                print("⚠️  Usage record created but billing run failed")
            
            return True
        else:
            print(f"❌ Failed to create usage record. Status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"Network error when calling Nitrobox API: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error when calling Nitrobox API: {e}")
        return False

def create_nitrobox_billing_run(bearer_token):
    """
    Create a billing run in Nitrobox
    
    Args:
        bearer_token: The bearer token for API authentication
    
    Returns:
        bool: True if successful, False otherwise
    """
    if not bearer_token:
        print("ERROR: No bearer token provided for billing run")
        return False
    
    if not NITROBOX_DEBTOR_IDENT:
        print("ERROR: NITROBOX_DEBTOR_IDENT not configured")
        return False
    
    # Use next day for processing date
    processing_date = (datetime.now() + timedelta(days=1)).isoformat() + "Z"
    
    # Prepare the billing run data according to the curl example
    billing_data = {
        "debtorIdent": NITROBOX_DEBTOR_IDENT,
        "processingDate": processing_date
    }
    
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"Bearer {bearer_token}"
    }
    
    try:
        print(f"Creating billing run in Nitrobox...")
        
        response = requests.post(
            NITROBOX_BILLING_URL,
            headers=headers,
            json=billing_data,
            timeout=30
        )
        
        if response.status_code == 200 or response.status_code == 201:
            print("✅ Successfully created billing run in Nitrobox")
            return True
        else:
            print(f"❌ Failed to create billing run. Status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"Network error when calling Nitrobox billing API: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error when calling Nitrobox billing API: {e}")
        return False

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
