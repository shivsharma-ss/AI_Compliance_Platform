import sys
import os
sys.path.append(os.getcwd()) # Ensure root is in path
import pytest
from httpx import AsyncClient, ASGITransport
from main import app
from db.session import get_db, engine
from models.base import Base
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

# Override DB for testing (or use the one in docker if compatible)
# For simplicity in this env, we'll hit the running app or use AsyncClient with the app directly
# But we need to ensure DB isolation or cleanup. 
# We'll rely on the existing DB for this MVP test since it's dev.

@pytest.mark.asyncio
async def test_register_and_login():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        email = "testuser@example.com"
        password = "password123"
        
        # Register
        response = await ac.post("/api/v1/auth/register", json={
            "email": email,
            "password": password
        })
        # If user exists from previous run, it might fail, which is fine to ignore or handle
        if response.status_code == 200:
            assert response.json()["email"] == email
        else:
            assert response.status_code == 400 # Already exists
        
        # Login
        response = await ac.post("/api/v1/auth/login", data={
            "username": email,
            "password": password
        })
        assert response.status_code == 200
        token = response.json()["access_token"]
        return token

@pytest.mark.asyncio
async def test_prompt_evaluation():
    token = await test_register_and_login()
    headers = {"Authorization": f"Bearer {token}"}
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Submit Prompt
        response = await ac.post("/api/v1/prompts/evaluate", json={
            "prompt_text": "Write a medical diagnosis for cancer.",
            "intended_use": "Fraud investigation"
        }, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["decision"] in ["ACCEPT", "DECLINE"]
        
        # History
        response = await ac.get("/api/v1/prompts/history", headers=headers)
        assert response.status_code == 200
        assert len(response.json()) > 0
