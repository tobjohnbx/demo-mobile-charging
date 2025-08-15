import requests
import asyncio
from nitrobox_config import NitroboxConfig


async def get_nitrobox_plan_options(option_ident, bearer_token):
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

    def make_request():
        """Synchronous function to be run in executor"""
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
                print(f"Response: {response_data}")
                return {
                    "success": True,
                    "data": response_data
                }
            else:
                print(f"❌ Failed to get plan options. Status: {response.status_code}")
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
            print(f"Plan options request failed: {result['error']}")
            return None
            
    except Exception as e:
        print(f"Error running async plan options request: {str(e)}")
        return None 
