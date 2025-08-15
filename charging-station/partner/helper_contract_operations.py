import sys
import os

# Add both current and parent directories to sys.path to enable imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from request_bearer_token import fetch_bearer_token
from request_get_contract import get_nitrobox_contract


def get_contract_for_customer(customer_info):
    """
    Retrieve contract details for a customer from Nitrobox API.
    
    Args:
        customer_info: Customer information containing contract_id
        
    Returns:
        dict: Contract details if successful, None if failed
    """
    # Get bearer token for Nitrobox API calls
    bearer_token = fetch_bearer_token()
    if not bearer_token:
        print("ERROR: Could not obtain bearer token for contract retrieval")
        return None
    
    # Get contract details from Nitrobox
    print(f"Getting contract details for customer contract ID: {customer_info.contract_id}")
    return get_nitrobox_contract(bearer_token, customer_info)


def extract_partner_properties(contract):
    """
    Extract partner-specific properties from contract JSON.
    
    Args:
        contract: Contract dictionary containing properties array
        
    Returns:
        tuple: (partner_id, commission_percentage) - None values if not found
    """
    if not contract or 'properties' not in contract:
        print("WARNING: Contract has no properties array")
        return None, None
    
    properties = contract['properties']
    partner_id = None
    commission_percentage = None
    
    for prop in properties:
        property_ident = prop.get('propertyIdent')
        property_value = prop.get('propertyValue')
        
        if property_ident == 'partner-id':
            partner_id = property_value
            print(f"Found partner-id: {partner_id}")
        elif property_ident == 'partner-comission-percentage':
            commission_percentage = property_value
            print(f"Found partner-comission-percentage: {commission_percentage}")
    
    return partner_id, commission_percentage


def get_partner_info_from_customer(customer_info):
    """
    Complete workflow to get partner information from customer data.
    
    Args:
        customer_info: Customer information containing contract_id
        
    Returns:
        tuple: (partner_id, commission_percentage) - None values if not found or error
    """
    # Get contract details
    contract = get_contract_for_customer(customer_info)
    
    if not contract:
        print("WARNING: Could not retrieve contract")
        return None, None

    # Extract partner properties from contract
    partner_id, commission_percentage = extract_partner_properties(contract)
    
    if not partner_id or not commission_percentage:
        print("Not relevant for partner.")
        return None, None
        
    return partner_id, commission_percentage 