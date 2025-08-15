import requests
import asyncio


async def request_partner_commission(partner: str, commission: str, amount: str, currency: str):
    """
    Make an async HTTP POST request to the partner commission endpoint using requests library.
    
    Args:
        partner: Partner identifier
        commission: Commission identifier  
        amount: Amount value
        currency: Currency code
    """
    url = f"http://192.168.179.29/partner/{partner}/commission/{commission}/amount/{amount}/currency/{currency}"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    def make_request():
        """Synchronous function to be run in executor"""
        try:
            response = requests.post(url, headers=headers, timeout=30)
            return {
                "status": response.status_code,
                "response": response.text,
                "url": url
            }
        except Exception as e:
            return {
                "error": str(e),
                "url": url
            }
    
    try:
        # Run the synchronous request in a thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, make_request)
        
        print(f"Request sent to: {url}")
        if "error" in result:
            print(f"Error making request to {url}: {result['error']}")
        else:
            print(f"Response status: {result['status']}")
            print(f"Response: {result['response']}")
        
        return result
                
    except Exception as e:
        print(f"Error making request to {url}: {str(e)}")
        return {
            "error": str(e),
            "url": url
        } 