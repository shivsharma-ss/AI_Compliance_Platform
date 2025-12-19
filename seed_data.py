import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from db.session import get_db, AsyncSessionLocal
from models.user import User
from core.security import get_password_hash
from sqlalchemy import select

async def seed():
    async with AsyncSessionLocal() as db:
        # 1. Create Admin
        result = await db.execute(select(User).where(User.email == "admin@sentinel.ai"))
        if not result.scalars().first():
            print("Creating admin...")
            admin = User(
                email="admin@sentinel.ai",
                hashed_password=get_password_hash("admin123"),
                role="admin",
                is_active=True
            )
            db.add(admin)
        else:
            print("Admin already exists.")

        # 2. Create User
        result = await db.execute(select(User).where(User.email == "user@test.com"))
        if not result.scalars().first():
            print("Creating test user...")
            user = User(
                email="user@test.com",
                hashed_password=get_password_hash("user123"),
                role="user",
                is_active=True
            )
            db.add(user)
        else:
            print("Test user already exists.")
        
        await db.commit()
        print("Seeding complete.")

if __name__ == "__main__":
    asyncio.run(seed())
