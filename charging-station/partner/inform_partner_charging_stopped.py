import sys
import os

# Add both current and parent directories to sys.path to enable imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import helper and commission request modules
from helper_contract_operations import get_partner_info_from_customer
from request_inform_partner_comission import request_partner_commission


async def inform_partner(event_name, *args, **kwargs):    
    print("Trying to inform partner that charging stopped")
    
    # Extract customer_info from kwargs
    customer_info = kwargs.get("customer_info")
    if not customer_info:
        print("WARNING: No customer_info provided to inform_partner")
        return
    
    # Get partner information using helper function
    partner_id, commission_percentage = get_partner_info_from_customer(customer_info)
    
    if not partner_id or not commission_percentage:
        print("Not relevant for partner.")
        return

    # Call commission endpoint for charging stopped event
    result = await request_partner_commission(
        partner=partner_id,
        commission=commission_percentage,
        amount="100",  # This might need to be extracted from charging session data
        currency="EUR"
    )
    
    print("Partner commission request result:", result)
    
   