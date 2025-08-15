import sys
import os

# Add both current and parent directories to sys.path to enable imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from request_pdf_download import request_pdf_download


async def inform_pdf_service(event_name, *args, **kwargs):    
    print("Trying to inform pdf service")
    
    # Extract customer_info from kwargs
    customer_info = kwargs.get("customer_info")
    if not customer_info:
        print("WARNING: No customer_info provided to inform_pdf_service")
        return
        
    try:
        result = await request_pdf_download(customer_info.debtor_ident)
        print(f"PDF download request completed: {result}")
        return result
    except Exception as e:
        print(f"Error calling PDF download service: {str(e)}")
        return {"error": str(e)}
    