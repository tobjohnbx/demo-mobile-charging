# file: rfid_read_simple.py
import RPi.GPIO as GPIO
import time
import requests
import json
import os
import sys
import asyncio
from datetime import datetime, timedelta
from mfrc522 import SimpleMFRC522
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from display import ChargingDisplay
from request_billing_run import create_nitrobox_billing_run
from request_create_usage import create_nitrobox_usage
from nitrobox_config import NitroboxConfig
from request_bearer_token import fetch_bearer_token
from request_get_plan_options import get_nitrobox_plan_options
from request_get_contract_details import get_option_idents_from_contract
from rfid_mapping import get_customer_info
from async_event_emitter import AsyncEventEmitter
from partner.inform_partner import inform_partner


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

def get_current_time_based_pricing(pricing_rules):
    """
    Determine which pricing rule to display based on current time
    
    Args:
        pricing_rules: List of pricing rules with time periods
        
    Returns:
        tuple: (price_amount, start_time, end_time, period_name) or None if no match
    """
    
    current_time = datetime.now().time()
    current_hour = current_time.hour
    current_minute = current_time.minute
    current_total_minutes = current_hour * 60 + current_minute
    
    for rule in pricing_rules:
        time_period = rule["criteria"]["timePeriod"]
        start_str = time_period["start"]  # e.g., "08:00:00"
        end_str = time_period["end"]      # e.g., "22:00:00"
        
        # Parse start and end times
        start_hour, start_minute = map(int, start_str.split(":")[0:2])
        end_hour, end_minute = map(int, end_str.split(":")[0:2])
        
        start_total_minutes = start_hour * 60 + start_minute
        end_total_minutes = end_hour * 60 + end_minute
        
        # Check if current time falls within this period
        if start_total_minutes <= end_total_minutes:
            # Normal period (e.g., 08:00-22:00)
            if start_total_minutes <= current_total_minutes < end_total_minutes:
                # Determine period name based on the actual time range and price
                price_amount = rule["price"]["amount"]
                if start_hour >= 6 and end_hour <= 22:
                    period_name = "Daytime"
                elif price_amount == 0.0:
                    period_name = "FREE"
                else:
                    period_name = "Standard"
                
                return (
                    price_amount,
                    f"{start_hour:02d}:{start_minute:02d}",
                    f"{end_hour:02d}:{end_minute:02d}",
                    period_name
                )
        else:
            # Overnight period (e.g., 22:00-08:00)
            if current_total_minutes >= start_total_minutes or current_total_minutes < end_total_minutes:
                price_amount = rule["price"]["amount"]
                period_name = "FREE" if price_amount == 0.0 else "Nighttime"
                
                return (
                    price_amount,
                    f"{start_hour:02d}:{start_minute:02d}",
                    f"{end_hour:02d}:{end_minute:02d}",
                    period_name
                )
    
    return None

def calculate_single_plan_cost(start_time, end_time, plan_options, plan_name):
    """
    Calculate cost for a single plan option
    
    Args:
        start_time: datetime when charging started
        end_time: datetime when charging ended  
        plan_options: The plan options containing pricing rules
        plan_name: Name of the plan for logging
        
    Returns:
        float: Cost for this plan option
    """
    if not plan_options:
        return 0.0
        
    # Handle different plan option structures
    if "pricingGroups" in plan_options:
        # Time-based pricing (blocking-time)
        pricing_rules = plan_options["pricingGroups"][0]["pricingRules"]
        quantity_type = plan_options.get("quantityType", "MINUTE")
        
        # Find pricing rule active during charging start
        temp_time = start_time.time()
        temp_total_minutes = temp_time.hour * 60 + temp_time.minute
        
        price_per_unit = 0.0
        for rule in pricing_rules:
            time_period = rule["criteria"]["timePeriod"]
            start_str = time_period["start"]
            end_str = time_period["end"]
            
            rule_start_hour, rule_start_minute = map(int, start_str.split(":")[0:2])
            rule_end_hour, rule_end_minute = map(int, end_str.split(":")[0:2])
            
            rule_start_total_minutes = rule_start_hour * 60 + rule_start_minute
            rule_end_total_minutes = rule_end_hour * 60 + rule_end_minute
            
            if rule_start_total_minutes <= rule_end_total_minutes:
                # Normal period
                if rule_start_total_minutes <= temp_total_minutes < rule_end_total_minutes:
                    price_per_unit = rule["price"]["amount"]
                    break
            else:
                # Overnight period
                if temp_total_minutes >= rule_start_total_minutes or temp_total_minutes < rule_end_total_minutes:
                    price_per_unit = rule["price"]["amount"]
                    break
                    
    elif "priceTiers" in plan_options:
        # Usage-based pricing (charging-time)
        price_tiers = plan_options["priceTiers"]
        quantity_type = plan_options.get("quantityType", "SECOND")
        
        # For now, use the last tier's price (highest quantity tier)
        # This could be enhanced to handle complex tier logic
        if price_tiers:
            price_per_unit = price_tiers[-1]["price"]
        else:
            price_per_unit = 0.0
    else:
        print(f"⚠️  Unknown plan structure for {plan_name}")
        return 0.0
    
    # Calculate duration based on quantity type
    duration_seconds = (end_time - start_time).total_seconds()
    
    if quantity_type.upper() == "SECOND":
        duration_units = duration_seconds
    elif quantity_type.upper() == "MINUTE":
        duration_units = duration_seconds / 60
    elif quantity_type.upper() == "HOUR":
        duration_units = duration_seconds / 3600
    else:
        print(f"⚠️  Unknown quantity type: {quantity_type}, using seconds")
        duration_units = duration_seconds
    
    cost = duration_units * price_per_unit
    
    print(f"💰 {plan_name} cost calculation:")
    print(f"   Duration: {duration_units:.2f} {quantity_type.lower()}")
    print(f"   Rate: €{price_per_unit:.4f}/{quantity_type.lower()}")
    print(f"   Cost: €{cost:.4f}")
    
    return cost

def calculate_total_charging_cost(start_time, end_time, all_plan_options):
    """
    Calculate total charging cost including both blocking-time and charging-time
    
    Args:
        start_time: datetime when charging started
        end_time: datetime when charging ended  
        all_plan_options: List of all plan options
        
    Returns:
        float: Total cost for the charging session
    """
    blocking_cost = 0.0
    charging_cost = 0.0
    
    for _, plan_options in all_plan_options:
        option_name = plan_options.get("optionName", "").lower()
        
        if "blocking" in option_name or "blocking-time" in option_name:
            blocking_cost = calculate_single_plan_cost(start_time, end_time, plan_options, "Blocking Fee")
        elif "charging" in option_name or "charging-time" in option_name:
            charging_cost = calculate_single_plan_cost(start_time, end_time, plan_options, "Charging Fee")
    
    total_cost = blocking_cost + charging_cost
    
    print("📊 Total Cost Summary:")
    print(f"   Blocking Fee: €{blocking_cost:.4f}")
    print(f"   Charging Fee: €{charging_cost:.4f}")
    print(f"   Total: €{total_cost:.4f}")
    
    return total_cost

def debug_pricing_periods(pricing_rules):
    """
    Debug function to show all available pricing periods
    """
    print("📋 Available pricing periods:")
    for i, rule in enumerate(pricing_rules):
        time_period = rule["criteria"]["timePeriod"]
        price = rule["price"]["amount"]
        currency = rule["price"]["currency"]
        print(f"   {i+1}. {time_period['start']}-{time_period['end']}: {currency}{price:.4f}")

def display_charging_fee(plan_options, display, fee_label="Charging Fee"):
    """
    Display charging fee information for usage-based pricing
    
    Args:
        plan_options: The plan options data containing pricing tiers
        display: The display object to show information on
        fee_label: The label to show for the fee (default: "Charging Fee")
        
    Returns:
        bool: True if successfully displayed, False otherwise
    """
    if not plan_options or not display:
        return False
        
    if "priceTiers" not in plan_options or len(plan_options["priceTiers"]) == 0:
        print("No priceTiers found in plan options")
        return False
    
    price_tiers = plan_options["priceTiers"]
    quantity_type = plan_options.get("quantityType", "SECOND")
    
    # Use the last tier's price (highest quantity tier)
    if price_tiers:
        price_amount = price_tiers[-1]["price"]
    else:
        price_amount = 0.0
    
    print(f"🔋 Charging Fee: €{price_amount:.4f}/{quantity_type.lower()}")
    
    # Display without time period since it's usage-based
    display.show_pricing_info(fee_label, None, None, price_amount, quantity_type)
    return True

def display_sequential_pricing(all_plan_options, display):
    """
    Display blocking fee for 3 seconds, then charging costs
    
    Args:
        all_plan_options: List of all plan options
        display: The display object to show information on
    """
    blocking_fee_option = None
    charging_fee_option = None
    
    # Find both blocking and charging options
    for option_ident, plan_options in all_plan_options:
        option_name = plan_options.get("optionName", "").lower()
        name = plan_options.get("name", "").lower()
        
        # Check if this is a blocking/time-based option
        if any(keyword in option_name or keyword in name for keyword in ["block", "blocking"]):
            if "pricingGroups" in plan_options:
                blocking_fee_option = (option_ident, plan_options)
                print(f"Found blocking fee option: {option_ident} ({plan_options.get('optionName', 'Unknown')})")
        
        # Check if this is a charging/usage-based option
        elif any(keyword in option_name or keyword in name for keyword in ["charging"]):
            if "priceTiers" in plan_options:
                charging_fee_option = (option_ident, plan_options)
                print(f"Found charging fee option: {option_ident} ({plan_options.get('optionName', 'Unknown')})")
    
    # Display blocking fee first for 3 seconds
    if blocking_fee_option and display:
        option_ident, plan_options = blocking_fee_option
        print("📱 Displaying blocking fee for 3 seconds...")
        success = display_time_based_blocking_fee(plan_options, display)
        if success:
            time.sleep(3)
        else:
            print("Failed to display blocking fee")
    
    # Then display charging costs
    if charging_fee_option and display:
        option_ident, plan_options = charging_fee_option
        print("📱 Displaying charging costs...")
        success = display_charging_fee(plan_options, display)
        if not success:
            print("Failed to display charging costs")
    elif not charging_fee_option:
        print("No charging fee option found")

def display_time_based_blocking_fee(plan_options, display, fee_label="Blocking Fee"):
    """
    Display the appropriate time-based fee based on current time
    
    Args:
        plan_options: The plan options data containing pricing rules
        display: The display object to show information on
        fee_label: The label to show for the fee (default: "Blocking Fee")
        
    Returns:
        bool: True if successfully displayed, False otherwise
    """
    if not plan_options or not display:
        return False
        
    if "pricingGroups" not in plan_options or len(plan_options["pricingGroups"]) == 0:
        print("No pricingGroups found in plan options")
        return False
    
    pricing_rules = plan_options["pricingGroups"][0]["pricingRules"]
    
    # Debug: Show all available pricing periods
    debug_pricing_periods(pricing_rules)
    
    # Show current time for comparison
    current_time = datetime.now().time()
    print(f"🕐 Current time: {current_time.strftime('%H:%M:%S')}")
    
    # Get the pricing for the current time
    current_pricing = get_current_time_based_pricing(pricing_rules)
    
    if current_pricing:
        price_amount, start_time, end_time, period_name = current_pricing
        quantity_type = plan_options["quantityType"]
        
        print(f"✅ Found matching time period: {period_name} ({start_time}-{end_time})")
        print(f"💰 Using exact price from matching period: €{price_amount:.4f}/{quantity_type.lower()}")
        
        # Display using the exact price from the matching time period
        # Use only the fee label without period descriptors
        display.show_pricing_info(fee_label, start_time, end_time, price_amount, quantity_type)
        return True
    else:
        print("Current time does not match any pricing period")
        return False

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
        charging_session_start = None
        current_plan_options = None  # Clear plan options when session ends
        all_stored_plan_options = []  # Clear all plan options when session ends
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

def toggle_relay():
    global charging_active
    print("Toggling relay")
    GPIO.output(RELAY_PIN, GPIO.HIGH if charging_active else GPIO.LOW)

try:
    print("Hold a tag near the reader...")

    # Set up event emitter and register partner notification
    global event_emitter
    event_emitter = AsyncEventEmitter()
    event_emitter.on("charging_finished", inform_partner)

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

        # Always have a small delay to prevent busy waiting
        time.sleep(0.1)

finally:
    GPIO.cleanup()
    if display:
        display.clear_display()
