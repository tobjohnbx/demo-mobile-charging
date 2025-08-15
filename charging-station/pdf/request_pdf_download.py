import requests
import asyncio
import json


async def request_pdf_download(customer_ident: str, wait_seconds: int = 120, poll_seconds: int = 5):
    """
    Make an async HTTP POST request to the PDF download service endpoint.
    
    Args:
        customer_ident: Customer identifier for PDF download
        wait_seconds: How long to wait for new document (default: 120)
        poll_seconds: Polling interval in seconds (default: 5)
    """
    url = "http://192.168.179.32:8000/download"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    payload = {
        "customerIdent": customer_ident,
        "waitSeconds": wait_seconds,
        "pollSeconds": poll_seconds
    }
    
    def make_request():
        """Synchronous function to be run in executor"""
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            return {
                "status": response.status_code,
                "response": response.text,
                "json_response": response.json() if response.headers.get('content-type') == 'application/json' else None,
                "url": url,
                "payload": payload
            }
        except Exception as e:
            return {
                "error": str(e),
                "url": url,
                "payload": payload
            }
    
    try:
        # Run the synchronous request in a thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, make_request)
        
        print(f"PDF download request sent to: {url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        if "error" in result:
            print(f"Error making PDF download request to {url}: {result['error']}")
        else:
            print(f"Response status: {result['status']}")
            print(f"Response: {result['response']}")
            if result.get('json_response'):
                print(f"JSON Response: {json.dumps(result['json_response'], indent=2)}")
        
        return result
                
    except Exception as e:
        print(f"Error making PDF download request to {url}: {str(e)}")
        return {
            "error": str(e),
            "url": url,
            "payload": payload
        } 