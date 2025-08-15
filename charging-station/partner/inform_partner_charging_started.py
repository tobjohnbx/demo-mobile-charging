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
from helper_contract_operations import get_partner_info_from_customer


async def inform_partner_charging_started(event_name, *args, **kwargs):    
    print("Trying to inform partner")
    
    # Extract customer_info from kwargs
    customer_info = kwargs.get("customer_info")
    if not customer_info:
        print("WARNING: No customer_info provided to inform_partner_charging_started")
        return
    
    # Get partner information using helper function
    partner_id, commission_percentage = get_partner_info_from_customer(customer_info)
    
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