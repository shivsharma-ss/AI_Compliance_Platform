import asyncio
import httpx
import json
import pytest

async def print_response(label: str, response: httpx.Response) -> None:
    print(f"   {label} Status: {response.status_code}")
    if not response.is_success:
        try:
            payload = response.json()
            print(f"   {label} Error: {payload}")
        except json.JSONDecodeError:
            print(f"   {label} Error: {response.text}")
        except Exception as exc:
            print(f"   {label} Error: Failed to parse response ({exc})")
        return

    try:
        payload = response.json()
        print(f"   {label} Result: {payload}")
    except json.JSONDecodeError:
        print(f"   {label} Result: {response.text}")
    except Exception as exc:
        print(f"   {label} Result: Failed to parse response ({exc})")


@pytest.mark.asyncio
async def test_eu_ai():
    async with httpx.AsyncClient(timeout=60.0) as client:
        print("Testing EU AI Act Service...")

        r1 = await client.post(
            "http://localhost:8003/analyze_risk",
            json={"text": "We will score citizens based on their social behavior and trustworthiness."},
        )
        await print_response("Social Scoring", r1)
        assert r1.status_code == 200
        payload_1 = r1.json()
        assert "risk_level" in payload_1
        assert "category" in payload_1
        assert "confidence" in payload_1

        r2 = await client.post(
            "http://localhost:8003/analyze_risk",
            json={"text": "This AI will screen job applicants and filter them based on predicted performance."},
        )
        await print_response("Employment Screening", r2)
        assert r2.status_code == 200
        payload_2 = r2.json()
        assert "risk_level" in payload_2
        assert "category" in payload_2
        assert "confidence" in payload_2

        r3 = await client.post(
            "http://localhost:8003/analyze_risk",
            json={"text": "Please summarize this article about gardening tips for beginners."},
        )
        await print_response("Safe Content", r3)
        assert r3.status_code == 200
        payload_3 = r3.json()
        assert "risk_level" in payload_3
        assert "category" in payload_3
        assert "confidence" in payload_3


if __name__ == "__main__":
    asyncio.run(test_eu_ai())
