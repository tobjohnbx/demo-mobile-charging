import requests
import asyncio


async def request_partner_article(partner: str, article: str, amount: str, currency: str, type_: str, data=None):
    """
    Make an async HTTP POST request to the partner article endpoint using requests library.
    
    Args:
        partner: Partner identifier
        article: Article identifier  
        amount: Amount value
        currency: Currency code
        type_: Type identifier
        data: Optional JSON data to send in request body
    """
    url = f"http://192.168.179.29/partner/{partner}/article/{article}/amount/{amount}/currency/{currency}/type/{type_}"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    def make_request():
        """Synchronous function to be run in executor"""
        try:
            response = requests.post(url, json=data, headers=headers, timeout=30)
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