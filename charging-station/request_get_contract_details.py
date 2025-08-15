import requests
import asyncio
from nitrobox_config import NitroboxConfig


async def get_nitrobox_contract_details(contract_ident, bearer_token):
    """
    Get contract details from Nitrobox API for the specified contract
    
    Args:
        contract_ident: The contract identifier to retrieve details for
        bearer_token: The bearer token for API authentication
        
    Returns:
        dict: The contract details from the API response, or None if failed
    """
    if not bearer_token:
        print("ERROR: No bearer token provided for contract details request")
        return None
        
    if not contract_ident:
        print("ERROR: No contract identifier provided for contract details request")
        return None

    # Get configuration from environment
    try:
        config = NitroboxConfig.from_env()
    except RuntimeError as e:
        print(f"ERROR: Configuration error - {e}")
        return None

    # Construct the API URL for contract details
    # Extract base URL from the api_url (remove /v2/usages part)
    base_url = config.api_url.rsplit('/v2/', 1)[0]
    contract_details_url = f"{base_url}/v2/contracts/{contract_ident}/details"
    
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {bearer_token}"
    }

    def make_request():
        """Synchronous function to be run in executor"""
        try:
            print(f"Fetching contract details from Nitrobox for contract: {contract_ident}...")
            
            response = requests.get(
                contract_details_url,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                print("✅ Successfully retrieved contract details from Nitrobox")
                response_data = response.json()
                print(f"Response: {response_data}")
                return {
                    "success": True,
                    "data": response_data
                }
            else:
                print(f"❌ Failed to get contract details. Status: {response.status_code}")
                print(f"   Response: {response.text}")
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                
        except requests.exceptions.RequestException as e:
            print(f"Network error when calling Nitrobox API: {e}")
            return {
                "success": False,
                "error": f"Network error: {str(e)}"
            }
        except Exception as e:
            print(f"Unexpected error when calling Nitrobox API: {e}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }

    try:
        # Run the synchronous request in a thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, make_request)
        
        if result["success"]:
            return result["data"]
        else:
            print(f"Contract details request failed: {result['error']}")
            return None
            
    except Exception as e:
        print(f"Error running async contract details request: {str(e)}")
        return None


async def get_option_idents_from_contract(contract_ident, bearer_token):
    """
    Get option identifiers from a contract's details
    
    Args:
        contract_ident: The contract identifier to retrieve option idents for
        bearer_token: The bearer token for API authentication
        
    Returns:
        list: List of option identifiers, or empty list if failed/none found
    """
    contract_details = await get_nitrobox_contract_details(contract_ident, bearer_token)
    
    if not contract_details:
        return []
    
    option_idents = []
    
    # Extract option identifiers from optionQuantities
    option_quantities = contract_details.get("optionQuantities", [])
    
    for phase_option in option_quantities:
        option_quantity_list = phase_option.get("optionQuantity", [])
        for option_item in option_quantity_list:
            option_ident = option_item.get("optionIdent")
            if option_ident:
                option_idents.append(option_ident)
    
    print(f"Found {len(option_idents)} option identifiers: {option_idents}")
    return option_idents