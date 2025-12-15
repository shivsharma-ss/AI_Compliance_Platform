import httpx
import asyncio
import sys

async def check():
    try:
        async with httpx.AsyncClient() as client:
            print("Checking 415-555-0199...")
            r1 = await client.post('http://spotixx-presidio:8000/analyze', json={'text': 'My phone number is 415-555-0199 call me.'})
            print(f"Phone Status: {r1.status_code}")
            print(f"Phone Body: {r1.json()}")

            print("\nChecking Email (spotixx-presidio)...")
            r2 = await client.post('http://spotixx-presidio:8000/analyze', json={'text': 'My email is test@example.com'})
            print(f"Email Status: {r2.status_code}")

            print("\nChecking Email (presidio-service)...")
            r3 = await client.post('http://presidio-service:8000/analyze', json={'text': 'My email is test@example.com'})
            print(f"Service Name Status: {r3.status_code}")
            print(f"Service Name Body: {r3.json()}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check())
