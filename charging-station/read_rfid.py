# file: rfid_read_simple.py
import RPi.GPIO as GPIO
import time
import os
import sys
import asyncio
import requests
from datetime import datetime, timedelta
from mfrc522 import SimpleMFRC522
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from display import ChargingDisplay
from request_billing_run import create_nitrobox_billing_run
from request_create_usage import create_nitrobox_usage
from request_bearer_token import fetch_bearer_token
from request_get_plan_options import get_nitrobox_plan_options
from request_get_contract_details import get_option_idents_from_contract
from rfid_mapping import get_customer_info
from async_event_emitter import AsyncEventEmitter
from partner.inform_partner_charging_started import inform_partner_charging_started
from partner.inform_partner_charging_stopped import inform_partner
from pricing_calculator import (
    calculate_total_charging_cost,
    display_sequential_pricing
)


# Use BCM pin numbering
GPIO.setmode(GPIO.BCM)

# Setup for RFID reader
reader = SimpleMFRC522()
charging_active = False
charging_session_start = None
current_charging_rate = None  # Store the current pricing rate per minute
current_plan_options = None  # Store the plan options for cost calculation
all_stored_plan_options = []  # Store all plan options for total cost calculation

# Setup for LED
RELAY_PIN = 17
GPIO.setup(RELAY_PIN, GPIO.OUT)

# Setup for coffee button
COFFEE_BUTTON_PIN = 14  # GPIO 14 (BCM) corresponds to Pin 8 (Board)
GPIO.setup(COFFEE_BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
last_button_state = True  # True = not pressed (Pull-up)
coffee_button_pressed = False
last_coffee_purchase_time = 0
COFFEE_DEBOUNCE_TIME = 1.0  # 1 second cooldown between coffee button presses

# Coffee product configuration
COFFEE_PRODUCT_IDENT = os.environ.get("NITROBOX_COFFEE_PRODUCT_IDENT", "coffee-product")
COFFEE_PRICE = 2.50  # Price in EUR

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
    global charging_active, charging_session_start, current_plan_options, all_stored_plan_options
    
    if charging_active:
        # Ending charging session
        charging_end_time = datetime.now()
        print("Stop charging.")
        
        # Emit charging_finished event to inform partner
        try:
            if 'event_emitter' in globals():
                asyncio.run(event_emitter.emit("charging_finished",
                                              tag_id=last_tag_id,
                                              duration_minutes=(charging_end_time - charging_session_start).total_seconds() / 60,
                                              customer_info=customer_info))
        except Exception as e:
            print(f"Warning: Failed to emit charging_finished event: {e}")

        # Calculate cost and show summary
        if display and charging_session_start:
            duration_minutes = (charging_end_time - charging_session_start).total_seconds() / 60
            
            # Calculate total cost from both blocking-time and charging-time plan options
            if all_stored_plan_options:
                cost = calculate_total_charging_cost(charging_session_start, charging_end_time, all_stored_plan_options)
            else:
                print("⚠️  No plan options available, cannot calculate accurate cost")
                cost = 0.0
                
            display.show_charging_stopped(duration_minutes, cost)
            time.sleep(2)

        # Create usage record in Nitrobox if we have a valid session
        if charging_session_start:
            duration_minutes = (charging_end_time - charging_session_start).total_seconds() / 60
            print(f"Charging session ended. Duration: {duration_minutes:.2f} minutes")

            # Fetch bearer token first
            bearer_token = get_bearer_token_with_error_handling()
            if not bearer_token:
                charging_active = False
                charging_session_start = None
                current_plan_options = None
                all_stored_plan_options = []
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
        toggle_relay()
        charging_session_start = None
        current_plan_options = None  # Clear plan options when session ends
        all_stored_plan_options = []  # Clear all plan options when session ends
    else:
        # Starting charging session
        charging_session_start = datetime.now()
        print(f"Start charging at {charging_session_start.strftime('%Y-%m-%d %H:%M:%S')}")
        charging_active = True
        toggle_relay()


        # Emit charging_started event to inform partner
        try:
            if 'event_emitter' in globals():
                asyncio.run(event_emitter.emit("charging_started",
                                              tag_id=last_tag_id,
                                              customer_info=customer_info))
        except Exception as e:
            print(f"Warning: Failed to emit charging_started event: {e}")

        # get plan options and display current pricing
        bearer_token = get_bearer_token_with_error_handling()
        if bearer_token and customer_info:
            # Get option identifiers from contract details using customer's contract
            option_idents = get_option_idents_from_contract(customer_info.contract_ident, bearer_token)
            
            # Get all plan options in parallel
            if option_idents:
                def get_single_plan_option(option_ident):
                    """Helper function to get plan options for a single identifier"""
                    return option_ident, get_nitrobox_plan_options(option_ident, bearer_token)
                
                all_plan_options = []
                
                # Get all plan options in parallel using ThreadPoolExecutor
                with ThreadPoolExecutor(max_workers=min(len(option_idents), 5)) as executor:
                    # Submit all requests
                    future_to_ident = {
                        executor.submit(get_single_plan_option, option_ident): option_ident 
                        for option_ident in option_idents
                    }
                    
                    # Collect results as they complete
                    for future in as_completed(future_to_ident):
                        try:
                            option_ident, plan_options = future.result()
                            if plan_options:
                                all_plan_options.append((option_ident, plan_options))
                                print(f"✅ Successfully retrieved plan options for {option_ident}")
                            else:
                                print(f"❌ Failed to retrieve plan options for {option_ident}")
                        except Exception as e:
                            option_ident = future_to_ident[future]
                            print(f"❌ Exception retrieving plan options for {option_ident}: {e}")
                
                # Store all plan options globally for total cost calculation
                all_stored_plan_options = all_plan_options.copy()
                print(f"📝 Stored {len(all_stored_plan_options)} plan options for cost calculation")

                # Display blocking fee for 3 seconds, then charging costs
                if all_plan_options and display:
                    display_sequential_pricing(all_plan_options, display)

def create_coffee_purchase(tag_id, customer_info):
    """
    Create a usage record in Nitrobox for a coffee purchase

    Args:
        tag_id: The RFID tag ID used for authentication
        customer_info: CustomerInfo object containing contract_id and debtor_ident

    Returns:
        bool: True if successful, False otherwise
    """
    if not tag_id or not customer_info:
        print("ERROR: No tag ID or customer info available for coffee purchase")
        return False

    # Get bearer token
    bearer_token = get_bearer_token_with_error_handling()
    if not bearer_token:
        return False

    # Create timestamps for coffee purchase (just a moment ago)
    purchase_time = datetime.now()

    # Show coffee purchase on display
    if display:
        display.show_text([
            "Coffee Purchase",
            f"Price: €{COFFEE_PRICE:.2f}",
            "Processing...",
            ""
        ])

    # Generate unique usage identifier for coffee
    usage_ident = f"coffee-{tag_id}-{int(purchase_time.timestamp())}"

    # Get configuration from environment
    try:
        config = NitroboxConfig.from_env()
    except RuntimeError as e:
        print(f"ERROR: Configuration error - {e}")
        if display:
            display.show_api_error("Config Error")
            time.sleep(2)
            display.show_welcome_message()
        return False

    # Prepare the usage data for coffee purchase
    usage_data = {
        "productIdent": COFFEE_PRODUCT_IDENT,
        "contractId": customer_info.contract_id,
        "usageIdent": usage_ident,
        "unitQuantities": [
            {
                "unitQuantity": 1,
                "unitQuantityType": "PIECE"
            }
        ],
        "startDate": purchase_time.isoformat() + "Z",
        "endDate": purchase_time.isoformat() + "Z",
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
        print(f"Sending coffee purchase data to Nitrobox...")

        response = requests.post(
            config.api_url,
            headers=headers,
            json=usage_data,
            timeout=30
        )

        if response.status_code == 201:
            print("✅ Successfully created coffee purchase record in Nitrobox")
            if display:
                display.show_api_success("Coffee Purchased")
                time.sleep(2)
                display.show_welcome_message()

            # After successful usage creation, trigger billing run
            billing_success = create_nitrobox_billing_run(bearer_token, customer_info)
            if billing_success:
                print("✅ Billing run also successfully created for coffee purchase")
            else:
                print("⚠️ Coffee purchase record created but billing run failed")

            return True
        else:
            print(f"❌ Failed to create coffee purchase record. Status: {response.status_code}")
            print(f"   Response: {response.text}")
            if display:
                display.show_api_error("Purchase Failed")
                time.sleep(2)
                display.show_welcome_message()
            return False

    except Exception as e:
        print(f"Error when calling Nitrobox API for coffee purchase: {e}")
        if display:
            display.show_api_error("API Error")
            time.sleep(2)
            display.show_welcome_message()
        return False

def check_coffee_button():
    """Check if coffee button is pressed and handle coffee purchase"""
    global last_button_state, coffee_button_pressed, last_coffee_purchase_time, last_tag_id

    # Skip if no tag has been read yet
    if not last_tag_id:
        return

    # Read current button state
    current_button_state = GPIO.input(COFFEE_BUTTON_PIN)

    # Button press detected (transition from HIGH to LOW)
    if last_button_state == True and current_button_state == False:
        current_time = time.time()

        # Check debounce
        if current_time - last_coffee_purchase_time >= COFFEE_DEBOUNCE_TIME:
            print("Coffee button pressed!")
            coffee_button_pressed = True

            # Get customer information for the last scanned RFID tag
            customer_info = get_customer_info(str(last_tag_id))
            if not customer_info:
                print(f"WARNING: No customer information found for RFID tag {last_tag_id}")
                if display:
                    display.show_api_error("Unknown card")
                    time.sleep(2)
                    display.show_welcome_message()
                return

            # Create coffee purchase
            create_coffee_purchase(last_tag_id, customer_info)

            # Update last purchase time
            last_coffee_purchase_time = current_time

        time.sleep(0.2)  # Debounce delay

    # Update button state
    last_button_state = current_button_state

def toggle_relay():
    global charging_active
    print("Toggling relay")
    GPIO.output(RELAY_PIN, GPIO.HIGH if charging_active else GPIO.LOW)

try:
    print("Hold a tag near the reader...")

    # Set up event emitter and register partner notification
    global event_emitter
    event_emitter = AsyncEventEmitter()
    event_emitter.on("charging_started", inform_partner_charging_started)
    event_emitter.on("charging_finished", inform_partner)

    # Add welcome message with coffee button instruction
    if display:
        display.show_text([
            "Ready",
            "Scan RFID card",
            "then press button",
            "for coffee"
        ])
        time.sleep(2)
        display.show_welcome_message()

    while True:
        # Check for RFID tag
        tag_id, text = read_rfid()
        
        # Check coffee button (can be pressed anytime after a tag has been read)
        check_coffee_button()

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

            # Show coffee button instruction after successful card read
            if display:
                time.sleep(1)  # Brief pause
                display.show_text([
                    "Card Accepted",
                    "",
                    "Press button",
                    "for coffee"
                ])
                time.sleep(2)
                display.show_welcome_message()

            print("-" * 30)  # Add separator between reads
            print("Hold a tag near the reader...")

        # Always have a small delay to prevent busy waiting
        time.sleep(0.1)

finally:
    GPIO.cleanup()
    if display:
        display.clear_display()
