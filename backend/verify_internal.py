import httpx
import asyncio
import sys

async def check():
    """
    Execute a sequence of HTTP POST requests to the spotixx-presidio /analyze endpoint and print each response.
    
    Sends test texts (phone number, email, person name, and address) to spotixx-presidio, printing each request's HTTP status code and any parsed JSON response body. Any raised exception is caught and printed to stdout.
    """
    try:
        timeout = httpx.Timeout(5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            print("Checking 415-555-0199...")
            r1 = await client.post('http://spotixx-presidio:8000/analyze', json={'text': 'My phone number is 415-555-0199 call me.'})
            print(f"Phone Status: {r1.status_code}")
            print(f"Phone Body: {r1.json()}")

            print("\nChecking Email (spotixx-presidio)...")
            r2 = await client.post('http://spotixx-presidio:8000/analyze', json={'text': 'My email is test@example.com'})
            print(f"Email Status: {r2.status_code}")

            print("\nChecking Service Name (spotixx-presidio)...")
            r3 = await client.post('http://spotixx-presidio:8000/analyze', json={'text': 'Service name: spotixx-presidio'})
            print(f"Service Name Status: {r3.status_code}")
            print(f"Service Name Body: {r3.json()}")

            print("\nChecking Person Name (spotixx-presidio)...")
            r4 = await client.post('http://spotixx-presidio:8000/analyze', json={'text': 'My name is John Doe.'})
            print(f"Name Status: {r4.status_code}")
            print(f"Name Body: {r4.json()}")

            print("\nChecking Address (spotixx-presidio)...")
            r5 = await client.post('http://spotixx-presidio:8000/analyze', json={'text': 'I live at 123 Main St, San Francisco, CA.'})
            print(f"Address Status: {r5.status_code}")
            print(f"Address Body: {r5.json()}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check())