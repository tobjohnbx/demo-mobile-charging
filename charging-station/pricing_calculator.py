"""
Pricing and cost calculation functions for the EV charging station.

This module contains all functions related to:
- Time-based pricing calculations
- Usage-based pricing calculations
- Cost calculations for charging sessions
- Display functions for pricing information
"""

import time
from datetime import datetime


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


def calculate_tiered_cost(total_units, price_tiers, plan_name):
    """
    Calculate cost using tiered pricing structure
    
    Args:
        total_units: Total number of units (seconds, minutes, etc.)
        price_tiers: List of price tiers with quantity and price
        plan_name: Name for logging purposes
        
    Returns:
        float: Total cost based on tiered pricing
        
    Example:
        price_tiers = [
            {"quantity": 5.0, "price": 0.0, "type": "FLAT"},  # First 5 units free
            {"quantity": 1.0, "price": 0.01, "type": "FLAT"}  # Each additional unit €0.01
        ]
        
        For 10 units:
        - First 5 units: 5 × €0.0 = €0.00
        - Next 5 units: 5 × €0.01 = €0.05
        - Total: €0.05
    """
    if not price_tiers:
        return 0.0
    
    total_cost = 0.0
    remaining_units = total_units
    
    print(f"🔢 Calculating tiered pricing for {plan_name}:")
    print(f"   Total units to process: {total_units:.2f}")
    
    for i, tier in enumerate(price_tiers):
        tier_quantity = tier["quantity"]
        tier_price = tier["price"]
        tier_type = tier.get("type", "FLAT")
        
        if remaining_units <= 0:
            break
            
        # Calculate units to apply this tier pricing to
        units_in_this_tier = min(remaining_units, tier_quantity)
        tier_cost = units_in_this_tier * tier_price
        
        total_cost += tier_cost
        remaining_units -= units_in_this_tier
        
        print(f"   Tier {i+1}: {units_in_this_tier:.2f} units × €{tier_price:.4f} = €{tier_cost:.4f}")
        
        # If this tier doesn't fully consume remaining units and it's the last tier,
        # apply the last tier's rate to all remaining units
        if i == len(price_tiers) - 1 and remaining_units > 0:
            additional_cost = remaining_units * tier_price
            total_cost += additional_cost
            print(f"   Remaining {remaining_units:.2f} units × €{tier_price:.4f} = €{additional_cost:.4f}")
            break
    
    print(f"   💰 Total tiered cost: €{total_cost:.4f}")
    return total_cost


def test_tiered_pricing():
    """
    Test function to verify tiered pricing calculation works correctly
    """
    print("🧪 Testing tiered pricing calculation...")
    
    # Example from user: 5 seconds free, then €0.01 per second
    example_tiers = [
        {"quantity": 5.0, "price": 0.0, "type": "FLAT"},
        {"quantity": 1.0, "price": 0.01, "type": "FLAT"}
    ]
    
    test_cases = [
        (3.0, 0.0),    # 3 seconds = €0.00 (all in free tier)
        (5.0, 0.0),    # 5 seconds = €0.00 (exactly free tier)
        (7.0, 0.02),   # 7 seconds = €0.02 (5 free + 2×€0.01)
        (10.0, 0.05),  # 10 seconds = €0.05 (5 free + 5×€0.01)
        (15.0, 0.10)   # 15 seconds = €0.10 (5 free + 10×€0.01)
    ]
    
    print("Expected vs Actual results:")
    for units, expected in test_cases:
        actual = calculate_tiered_cost(units, example_tiers, "Test")
        status = "✅" if abs(actual - expected) < 0.001 else "❌"
        print(f"{status} {units} units: Expected €{expected:.2f}, Got €{actual:.2f}")
        print()


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
        # Usage-based pricing (charging-time) with tiered pricing
        price_tiers = plan_options["priceTiers"]
        quantity_type = plan_options.get("quantityType", "SECOND")
        
        # Calculate duration in the appropriate units
        duration_seconds = (end_time - start_time).total_seconds()
        
        if quantity_type.upper() == "SECOND":
            total_units = duration_seconds
        elif quantity_type.upper() == "MINUTE":
            total_units = duration_seconds / 60
        elif quantity_type.upper() == "HOUR":
            total_units = duration_seconds / 3600
        else:
            print(f"⚠️  Unknown quantity type: {quantity_type}, using seconds")
            total_units = duration_seconds
        
        # Calculate cost using tiered pricing
        cost = calculate_tiered_cost(total_units, price_tiers, plan_name)
        
        print(f"💰 {plan_name} tiered cost calculation:")
        print(f"   Total {quantity_type.lower()}: {total_units:.2f}")
        print(f"   Cost: €{cost:.4f}")
        
        return cost
    else:
        print(f"⚠️  Unknown plan structure for {plan_name}")
        return 0.0
    
    # Calculate duration based on quantity type for time-based pricing
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