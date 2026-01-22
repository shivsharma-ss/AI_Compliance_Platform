import asyncio
import sys
import os
import secrets
from typing import Optional, Tuple
from pathlib import Path

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from db.session import AsyncSessionLocal
from models.user import User
from core.security import get_password_hash
from sqlalchemy import select

LOCAL_ENVS = {"local", "development", "dev"}


def is_truthy(value: Optional[str]) -> bool:
    return value is not None and value.strip().lower() in {"1", "true", "yes", "y"}


def is_local_env() -> bool:
    env = os.getenv("APP_ENV") or os.getenv("ENVIRONMENT") or os.getenv("ENV")
    if env is None:
        return False
    return env.strip().lower() in LOCAL_ENVS


def build_password(env_value: Optional[str]) -> Tuple[str, bool]:
    cleaned = env_value.strip() if env_value is not None else ""
    if cleaned:
        return cleaned, False
    return secrets.token_urlsafe(24), True


def write_generated_password(label: str, email: str, password: str) -> None:
    default_dir = str(Path.home() / ".spotixx-secrets")
    output_dir = Path(os.getenv("SEED_OUTPUT_DIR", default_dir)).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(output_dir, 0o700)
    output_file = output_dir / f"{label}_credentials.txt"
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    fd = os.open(output_file, flags, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(f"email={email}\npassword={password}\n")
    os.chmod(output_file, 0o600)


async def seed():
    is_local = is_local_env()
    admin_email_env = os.getenv("ADMIN_EMAIL")
    admin_password_env = os.getenv("ADMIN_PASSWORD")
    admin_email = (admin_email_env or "admin@spotixx.com").strip()
    seed_confirm = is_truthy(os.getenv("SEED_CONFIRM"))
    explicit_admin = bool(admin_email_env and admin_password_env)

    if not is_local and not (explicit_admin or seed_confirm):
        raise RuntimeError(
            "Refusing to seed non-local environment without ADMIN_EMAIL/ADMIN_PASSWORD or SEED_CONFIRM=true."
        )

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == admin_email))
        if not result.scalars().first():
            print("Creating admin...")
            admin_password, generated = build_password(admin_password_env)
            admin = User(
                email=admin_email,
                hashed_password=get_password_hash(admin_password),
                role="admin",
                is_active=True
            )
            db.add(admin)
            if generated:
                write_generated_password("admin", admin_email, admin_password)
        else:
            print("Admin already exists.")

        seed_test_user = is_local or is_truthy(os.getenv("SEED_TEST_USER"))
        if seed_test_user:
            test_email_env = os.getenv("TEST_USER_EMAIL")
            test_password_env = os.getenv("TEST_USER_PASSWORD")
            test_email = (test_email_env or "user@test.com").strip()
            result = await db.execute(select(User).where(User.email == test_email))
            if not result.scalars().first():
                print("Creating test user...")
                test_password, generated = build_password(test_password_env)
                user = User(
                    email=test_email,
                    hashed_password=get_password_hash(test_password),
                    role="user",
                    is_active=True
                )
                db.add(user)
                if generated:
                    write_generated_password("test_user", test_email, test_password)
            else:
                print("Test user already exists.")
        else:
            print("Skipping test user creation.")
        
        await db.commit()
        print("Seeding complete.")


if __name__ == "__main__":
    asyncio.run(seed())
