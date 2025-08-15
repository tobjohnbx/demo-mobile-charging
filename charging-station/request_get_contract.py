import requests
from nitrobox_config import NitroboxConfig


def get_nitrobox_contract(bearer_token, customer_info):
    """
    Get contract details from Nitrobox for a specific customer

    Args:
        bearer_token: The bearer token for API authentication
        customer_info: CustomerInfo object containing contract_id and debtor_ident

    Returns:
        dict: Contract details if successful, None otherwise
    """
    if not bearer_token:
        print("ERROR: No bearer token provided for contract details request")
        return None

    # Get configuration from environment
    try:
        config = NitroboxConfig.from_env()
    except RuntimeError as e:
        print(f"ERROR: Configuration error - {e}")
        return None

    if not customer_info or not customer_info.contract_id:
        print("ERROR: No customer contract ID available")
        return None

    # Build the contracts endpoint URL
    # Convert the base API URL from usages to contracts endpoint
    base_api_url = config.api_url.replace("/v2/usages", "")
    contracts_url = f"{base_api_url}/v2/contracts/{customer_info.contract_id}"

    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {bearer_token}"
    }

    try:
        print(f"Getting contract details from Nitrobox for contract ID: {customer_info.contract_id}")

        response = requests.get(
            contracts_url,
            headers=headers,
            timeout=30
        )

        if response.status_code == 200:
            print("✅ Successfully retrieved contract details from Nitrobox")
            contract_data = response.json()
            print(f"   Contract status: {contract_data.get('status', 'Unknown')}")
            return contract_data
        else:
            print(f"❌ Failed to get contract details. Status: {response.status_code}")
            print(f"   Response: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Network error when calling Nitrobox contracts API: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error when calling Nitrobox contracts API: {e}")
        return None 