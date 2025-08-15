# file: rfid_read_simple.py
import RPi.GPIO as GPIO
import time
import requests
import json
import os
import sys
from datetime import datetime, timedelta
from mfrc522 import SimpleMFRC522

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from display import ChargingDisplay
from request_billing_run import create_nitrobox_billing_run
from request_create_usage import create_nitrobox_usage
from nitrobox_config import NitroboxConfig
from request_bearer_token import fetch_bearer_token
from request_get_plan_options import get_nitrobox_plan_options
from request_get_contract_details import get_option_idents_from_contract
from rfid_mapping import get_customer_info


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

# Pricing display variables
pricing_display_start = 0
pricing_display_active = False
PRICING_DISPLAY_DURATION = 5.0  # Show pricing for 5 seconds



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

def get_bearer_token_with_error_handling():
    """
    Fetch bearer token with standardized error handling for charging station
    Returns bearer token or None, handles display updates
    """
    bearer_token = fetch_bearer_token()
    if not bearer_token:
        print("Failed to get bearer token")
        if display:
            display.show_api_error("Auth failed")
            time.sleep(2)
            display.show_welcome_message()
    return bearer_token

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

def set_charging_state(customer_info):
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
            bearer_token = get_bearer_token_with_error_handling()
            if not bearer_token:
                charging_active = False
                charging_session_start = None
                return

            # Create usage record in Nitrobox
            success = create_nitrobox_usage(
                tag_id=last_tag_id,
                charging_start_time=charging_session_start,
                charging_end_time=charging_end_time,
                bearer_token=bearer_token,
                customer_info=customer_info
            )
            
            if success:
                print("Usage record successfully sent to Nitrobox")
                if display:
                    display.show_api_success("Billing processed")
                    time.sleep(2)
                    display.show_welcome_message()

                # After successful usage creation, trigger billing run
                billing_success = create_nitrobox_billing_run(bearer_token, customer_info)
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

        # get plan options and display current pricing
        bearer_token = get_bearer_token_with_error_handling()
        if bearer_token:
            config = NitroboxConfig.from_env()
            # Get option identifiers from contract details
            option_idents = get_option_idents_from_contract(config.contract_ident, bearer_token)
            
            # Use the first option identifier to get plan options
            if option_idents:
                plan_options = get_nitrobox_plan_options(option_idents[0], bearer_token)
                if plan_options and display:
                    # Extract pricing from pricingGroups structure
                    pricing_rules = plan_options["pricingGroups"][0]["pricingRules"]
                    # Find the pricing rule for 08:00-22:00 (daytime pricing)
                    daytime_price = None
                    for rule in pricing_rules:
                        time_period = rule["criteria"]["timePeriod"]
                        if time_period["start"] == "08:00:00" and time_period["end"] == "22:00:00":
                            daytime_price = rule["price"]["amount"]
                            break
                    
                    if daytime_price is not None:
                        display.show_pricing_info("08:00", "22:00", daytime_price, plan_options["quantityType"])
                        # Start pricing display timer (non-blocking)
                        global pricing_display_start, pricing_display_active
                        pricing_display_start = time.time()
                        pricing_display_active = True
                        print(f"DEBUG: Timer variables set - start: {pricing_display_start}, active: {pricing_display_active}")

                        return  # Exit early to avoid overriding the pricing display

def toggle_relay():
    global charging_active
    print("Toggling relay")
    GPIO.output(RELAY_PIN, GPIO.HIGH if charging_active else GPIO.LOW)

try:
    print("Hold a tag near the reader...")
    last_charging_display_update = 0

    while True:
        tag_id, text = read_rfid()
        current_time = time.time()
        
        # DEBUG: Check if we're even getting to this point
        print(f"DEBUG: Loop iteration - tag_id: {tag_id}, pricing_active: {pricing_display_active}")
        
        # Check if pricing display timer has expired (do this every loop)
        if pricing_display_active:
            elapsed = current_time - pricing_display_start
            print(f"DEBUG: Timer check - elapsed: {elapsed:.1f}s, active: {charging_active}")
            if elapsed >= PRICING_DISPLAY_DURATION:
                print("DEBUG: Timer expired, switching display")
                pricing_display_active = False
                if display and charging_active:
                    print("DEBUG: Showing charging started")
                    display.show_charging_started(last_tag_id, charging_session_start)
                    last_charging_display_update = current_time  # Reset timer for periodic updates

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

            # Get customer information for this RFID tag
            customer_info = get_customer_info(str(tag_id))
            if not customer_info:
                print(f"WARNING: No customer information found for RFID tag {tag_id}")
                if display:
                    display.show_api_error("Unknown card")
                    time.sleep(2)
                    display.show_welcome_message()
                continue  # Skip processing if no customer info found

            set_charging_state(customer_info)
            toggle_relay()
            print("-" * 30)  # Add separator between reads
            print("Hold a tag near the reader...")
        else:
            # Update charging display periodically during active session (only when no tag processing)
            if charging_active and display and not pricing_display_active and (current_time - last_charging_display_update) > 5:
                duration_minutes = (datetime.now() - charging_session_start).total_seconds() / 60
                display.show_charging_active(charging_session_start, duration_minutes)
                last_charging_display_update = current_time

        # Always have a small delay to prevent busy waiting
        time.sleep(0.1)

finally:
    GPIO.cleanup()
    if display:
        display.clear_display()
