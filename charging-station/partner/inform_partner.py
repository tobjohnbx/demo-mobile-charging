import asyncio
from request_inform_partner_charging import request_partner_article

async def inform_partner(event_name, *args,**kwargs):    
    print("Trying to inform partner")
    # Example call to the partner article endpoint
    # You can modify these parameters based on your actual data
    result = await request_partner_article(
        partner="test_partner",
        article="test_article", 
        amount="100",
        currency="EUR",
        type_="charging",
        data={"event": event_name, "args": args, "kwargs": kwargs}
    )
    
    print("Partner request result:", result)