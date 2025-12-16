import httpx
import asyncio

async def test_eu_ai():
    async with httpx.AsyncClient(timeout=60.0) as client:
        print("Testing EU AI Act Service...")
        
        # Test 1: Social Scoring (Prohibited)
        print("\n1. Social Scoring prompt:")
        r1 = await client.post('http://localhost:8003/analyze_risk', json={'text': 'We will score citizens based on their social behavior and trustworthiness.'})
        print(f"   Status: {r1.status_code}")
        print(f"   Result: {r1.json()}")
        
        # Test 2: Employment Screening (High Risk)
        print("\n2. Employment Screening prompt:")
        r2 = await client.post('http://localhost:8003/analyze_risk', json={'text': 'This AI will screen job applicants and filter them based on predicted performance.'})
        print(f"   Status: {r2.status_code}")
        print(f"   Result: {r2.json()}")
        
        # Test 3: Safe Content (Minimal Risk)
        print("\n3. Safe Content prompt:")
        r3 = await client.post('http://localhost:8003/analyze_risk', json={'text': 'Please summarize this article about gardening tips for beginners.'})
        print(f"   Status: {r3.status_code}")
        print(f"   Result: {r3.json()}")

if __name__ == "__main__":
    asyncio.run(test_eu_ai())
