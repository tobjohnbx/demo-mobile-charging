import requests
from nitrobox_config import NitroboxConfig


def get_nitrobox_plan_options(option_ident, bearer_token):
    """
    Get plan options from Nitrobox API for the specified plan
    
    Args:
        option_ident: The option identifier to retrieve options for
        bearer_token: The bearer token for API authentication
        
    Returns:
        dict: The price groups from the API response, or None if failed
    """
    if not bearer_token:
        print("ERROR: No bearer token provided for plan options request")
        return None
        
    if not option_ident:
        print("ERROR: No option identifier provided for plan options request")
        return None

    # Get configuration from environment
    try:
        config = NitroboxConfig.from_env()
    except RuntimeError as e:
        print(f"ERROR: Configuration error - {e}")
        return None

    # Construct the API URL for plan options
    # Extract base URL from the api_url (remove /v2/usages part)
    base_url = config.api_url.rsplit('/v2/', 1)[0]
    plan_options_url = f"{base_url}/v2/billing/plan-options/{option_ident}"
    
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {bearer_token}"
    }

    try:
        print(f"Fetching plan options from Nitrobox for option identifier: {option_ident}...")
        
        response = requests.get(
            plan_options_url,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            print("✅ Successfully retrieved plan options from Nitrobox")
            response_data = response.json()
            
            # Extract and return price groups from the response
            price_groups = response_data.get('priceGroups', [])
            print(f"Found {len(price_groups)} price groups")
            return price_groups
        else:
            print(f"❌ Failed to get plan options. Status: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Network error when calling Nitrobox API: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error when calling Nitrobox API: {e}")
        return None 