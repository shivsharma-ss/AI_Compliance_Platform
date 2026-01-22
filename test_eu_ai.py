import httpx
import asyncio
import json

async def print_response(label: str, response: httpx.Response) -> None:
    print(f"   Status: {response.status_code}")
    if not response.is_success:
        try:
            payload = response.json()
            print(f"   Error: {payload}")
        except json.JSONDecodeError:
            print(f"   Error: {response.text}")
        except Exception as exc:
            print(f"   Error: Failed to parse response ({exc})")
        return

    try:
        payload = response.json()
        print(f"   Result: {payload}")
    except json.JSONDecodeError:
        print(f"   Result: {response.text}")
    except Exception as exc:
        print(f"   Result: Failed to parse response ({exc})")


async def test_eu_ai():
    async with httpx.AsyncClient(timeout=60.0) as client:
        print("Testing EU AI Act Service...")

        # Test 1: Social Scoring (Prohibited)
        print("\n1. Social Scoring prompt:")
        r1 = await client.post('http://localhost:8003/analyze_risk', json={'text': 'We will score citizens based on their social behavior and trustworthiness.'})
        await print_response("Social Scoring", r1)

        # Test 2: Employment Screening (High Risk)
        print("\n2. Employment Screening prompt:")
        r2 = await client.post('http://localhost:8003/analyze_risk', json={'text': 'This AI will screen job applicants and filter them based on predicted performance.'})
        await print_response("Employment Screening", r2)

        # Test 3: Safe Content (Minimal Risk)
        print("\n3. Safe Content prompt:")
        r3 = await client.post('http://localhost:8003/analyze_risk', json={'text': 'Please summarize this article about gardening tips for beginners.'})
        await print_response("Safe Content", r3)

if __name__ == "__main__":
    asyncio.run(test_eu_ai())
