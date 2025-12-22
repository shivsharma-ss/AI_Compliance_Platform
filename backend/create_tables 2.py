import asyncio
from db.session import engine
from models.base import Base

# Import models so they are registered on Base.metadata before create_all runs
import models.user
import models.rule
import models.prompt

async def create_all():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

if __name__ == '__main__':
    asyncio.run(create_all())
