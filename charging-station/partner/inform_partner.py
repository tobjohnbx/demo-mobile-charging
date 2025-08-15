import sys
import os

# Add both current and parent directories to sys.path to enable imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import from same directory
import request_inform_partner_charging
request_partner_article = request_inform_partner_charging.request_partner_article
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
        dict: Dictionary with partner_id and commission_percentage, or None values if not found
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
    

async def inform_partner(event_name, *args, **kwargs):    
    print("Trying to inform partner")
    
    # Extract customer_info from kwargs
    customer_info = kwargs.get("customer_info")
    if not customer_info:
        print("WARNING: No customer_info provided to inform_partner")
        return
    
    # Get contract details
    contract = get_contract_for_customer(customer_info)
    
    if not contract:
        print("WARNING: Could not retrieve contract")
        return

    # Extract partner properties from contract
    partner_id, commission_percentage = extract_partner_properties(contract)
    
    if not partner_id or not commission_percentage:
        print("Not relevant for partner.")
        return

    result = await request_partner_article(
        partner=partner_id,
        article="test_article", 
        amount="100",
        currency="EUR",
        type_="charging"
    )
    
    print("Partner request result:", result)