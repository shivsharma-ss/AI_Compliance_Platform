from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings
from api import auth, prompts
from sqlalchemy import select

from db.session import engine, AsyncSessionLocal
from models.base import Base
from models.user import User
from core.security import get_password_hash

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(prompts.router, prefix=f"{settings.API_V1_STR}/prompts", tags=["prompts"])
# New Rule Router
from api import rules
app.include_router(rules.router, prefix=f"{settings.API_V1_STR}/rules", tags=["rules"])

# New Admin Analytics Router
from api import admin
app.include_router(admin.router, prefix=f"{settings.API_V1_STR}/admin", tags=["admin"])

# New Modules Router
from api import modules
app.include_router(modules.router, prefix=f"{settings.API_V1_STR}/modules", tags=["modules"])

@app.on_event("startup")
async def ensure_schema_and_seed_users():
    # Create tables if they don't exist (idempotent)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed default admin and test user only if SEED_DEFAULT_USERS=true (dev-only)
    if settings.SEED_DEFAULT_USERS:
        default_users = [
            ("admin@sentinel.ai", "admin123", "admin"),
            ("user@test.com", "user123", "user"),
        ]
        async with AsyncSessionLocal() as session:
            created = False
            for email, password, role in default_users:
                result = await session.execute(select(User).where(User.email == email))
                if result.scalars().first() is None:
                    session.add(
                        User(
                            email=email,
                            hashed_password=get_password_hash(password),
                            role=role,
                            is_active=True,
                        )
                    )
                    created = True
            if created:
                await session.commit()

@app.get("/")
def read_root():
    return {"message": "Welcome to the Sentinel AI Compliance Gateway API"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
