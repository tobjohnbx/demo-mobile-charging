import requests
from nitrobox_config import NitroboxConfig


def fetch_bearer_token():
    """
    Fetch a bearer token using OAuth2 client credentials flow

    Returns:
        str: Bearer token if successful, None otherwise
    """
    # Get configuration from environment
    try:
        config = NitroboxConfig.from_env()
    except RuntimeError as e:
        print(f"ERROR: Configuration error - {e}")
        return None

    if not config.client_credentials_b64:
        print("ERROR: NITROBOX_CLIENT_CREDENTIALS environment variable not set")
        return None

    try:
        headers = {
            "Authorization": f"Basic {config.client_credentials_b64}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        params = {
            "grant_type": "client_credentials"
        }

        print("Fetching new bearer token from Nitrobox...")

        response = requests.post(
            config.oauth_url,
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