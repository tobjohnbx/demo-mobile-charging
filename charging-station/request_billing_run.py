def create_nitrobox_billing_run(bearer_token):
    """
    Create a billing run in Nitrobox

    Args:
        bearer_token: The bearer token for API authentication

    Returns:
        bool: True if successful, False otherwise
    """
    if not bearer_token:
        print("ERROR: No bearer token provided for billing run")
        return False

    if not NITROBOX_DEBTOR_IDENT:
        print("ERROR: NITROBOX_DEBTOR_IDENT not configured")
        return False

    # Use next day for processing date
    processing_date = (datetime.now() + timedelta(days=1)).isoformat() + "Z"

    # Prepare the billing run data according to the curl example
    billing_data = {
        "debtorIdent": NITROBOX_DEBTOR_IDENT,
        "processingDate": processing_date
    }

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"Bearer {bearer_token}"
    }

    try:
        print(f"Creating billing run in Nitrobox...")

        response = requests.post(
            NITROBOX_BILLING_URL,
            headers=headers,
            json=billing_data,
            timeout=30
        )

        if response.status_code == 200 or response.status_code == 201:
            print("✅ Successfully created billing run in Nitrobox")
            return True
        else:
            print(f"❌ Failed to create billing run. Status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"Network error when calling Nitrobox billing API: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error when calling Nitrobox billing API: {e}")
        return False
