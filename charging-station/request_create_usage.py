import requests
from datetime import datetime
from nitrobox_config import NitroboxConfig


def create_nitrobox_usage(tag_id, charging_start_time, charging_end_time, bearer_token, customer_info, product_ident, button_release_count=None):
    """
    Create a usage record in Nitrobox for the charging session

    Args:
        tag_id: The RFID tag ID used for authentication
        charging_start_time: DateTime when charging started
        charging_end_time: DateTime when charging ended
        bearer_token: The bearer token for API authentication
        customer_info: CustomerInfo object containing contract_id and debtor_ident
        product_ident: The product identifier for Nitrobox
        button_release_count: Number of times the button was released during charging session (optional)

    Returns:
        bool: True if successful, False otherwise
    """
    if not bearer_token:
        print("ERROR: No bearer token provided for usage creation")
        return False

    # Get configuration from environment
    try:
        config = NitroboxConfig.from_env()
    except RuntimeError as e:
        print(f"ERROR: Configuration error - {e}")
        return False

    if not customer_info or not customer_info.contract_id:
        print("ERROR: No customer contract ID available")
        return False

    # Calculate charging duration in seconds
    duration_seconds = int((charging_end_time - charging_start_time).total_seconds())

    # Generate unique usage identifier
    usage_ident = f"rfid-session-{tag_id}-{int(charging_start_time.timestamp())}"
    if button_release_count is not None:
        usage_ident += "-coffee"

    # Prepare the usage data according to Nitrobox API schema (matching curl example)
    unit_quantities = [
        {
            "unitQuantity": duration_seconds,
            "unitQuantityType": "SECOND"
        }
    ]
    
    # Only add button count if it was provided
    if button_release_count is not None:
        unit_quantities = [
            {
                "unitQuantity": button_release_count,
                "unitQuantityType": "PC"
            }
        ]
    
    usage_data = {
        "productIdent": product_ident,
        "contractId": customer_info.contract_id,
        "usageIdent": usage_ident,
        "unitQuantities": unit_quantities,
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
        if button_release_count is not None:
            print(f"Sending usage data to Nitrobox for {duration_seconds} seconds of charging with {button_release_count} button releases...")
        else:
            print(f"Sending usage data to Nitrobox for {duration_seconds} seconds of charging...")

        response = requests.post(
            config.api_url,
            headers=headers,
            json=usage_data,
            timeout=30
        )

        if response.status_code == 201:
            print("✅ Successfully created usage record in Nitrobox")
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
