#!/bin/bash
# Security remediation script - removes dev secrets and gates seeding

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}ℹ️  $1${NC}"
}

log_warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_info "Starting security remediation..."

# 1. Update core/config.py to require SECRET_KEY
log_info "1. Updating core/config.py to require SECRET_KEY..."

cat > backend/core/config.py << 'EOF'
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Sentinel AI Compliance Gateway"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    DATABASE_URL: str
    
    # Security
    SECRET_KEY: str  # No default - must be provided in production
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    
    # Seeding
    SEED_DEFAULT_USERS: bool = False  # Gate seeding behind flag

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def split_cors_origins(cls, value):
        """Allow comma-separated env var for CORS origins."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value
    
    class Config:
        env_file = ".env"

settings = Settings()
EOF

log_info "core/config.py updated ✅"

# 2. Update main.py to gate seeding
log_info "2. Updating main.py to gate seeding..."

cat > backend/main.py << 'EOF'
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
EOF

log_info "main.py updated ✅"

# 3. Create a migration helper script
log_info "3. Creating migration helper script..."

cat > backend/migrate.sh << 'EOF'
#!/bin/bash
# Migration helper - run inside Cloud Run job or locally with Cloud SQL proxy

set -e

echo "Running Alembic migrations..."
alembic upgrade head
echo "✅ Migrations completed successfully"
EOF

chmod +x backend/migrate.sh

log_info "migrate.sh created ✅"

# 4. Create .env.example template
log_info "4. Creating .env.example template..."

cat > backend/.env.example << 'EOF'
# Database
DATABASE_URL=postgresql+asyncpg://sentinel_admin:YOUR_PASSWORD@localhost/sentinel_db

# Security - NEVER commit real values to Git!
SECRET_KEY=GENERATE_A_STRONG_SECRET_KEY_HERE

# CORS - Update for production
BACKEND_CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Seeding (dev only)
SEED_DEFAULT_USERS=true

# OpenAI (optional)
OPENAI_API_KEY=sk-YOUR_KEY_HERE
EOF

log_info ".env.example created ✅"

# 5. Verify .gitignore includes sensitive files
log_info "5. Checking .gitignore..."

if [ ! -f .gitignore ]; then
    log_warn ".gitignore not found, creating one..."
    cat > .gitignore << 'EOF'
# Environment
.env
.env.local
.env.*.local
venv/
env/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Node
node_modules/
dist/
.npm

# Docker
.docker/

# Secrets
secrets/
*.key
*.pem
EOF
    log_info ".gitignore created ✅"
else
    if grep -q ".env" .gitignore; then
        log_info ".env already in .gitignore ✅"
    else
        echo ".env" >> .gitignore
        log_info "Added .env to .gitignore ✅"
    fi
fi

# 6. Create security checklist
log_info "6. Creating security checklist..."

cat > SECURITY_CHECKLIST.md << 'EOF'
# Security Checklist for Production Deployment

## Before Deploying to Cloud Run ✅

- [ ] **Secrets Management**
  - [ ] All sensitive values moved to GCP Secret Manager
  - [ ] `SECRET_KEY` is a strong, randomly generated value
  - [ ] Database password is strong and unique
  - [ ] `.env` file is in `.gitignore` and never committed
  - [ ] No hardcoded API keys or credentials in code

- [ ] **Code Review**
  - [ ] No logging of sensitive data (passwords, tokens, PII)
  - [ ] SQL injection prevention verified (using ORM/parameterized queries)
  - [ ] XSS prevention in frontend (using Vue templating)
  - [ ] CSRF tokens present for state-changing operations
  - [ ] Authentication/Authorization checks on all protected endpoints

- [ ] **Configuration**
  - [ ] `SEED_DEFAULT_USERS=false` in production
  - [ ] `BACKEND_CORS_ORIGINS` limited to actual frontend domain
  - [ ] Debug mode disabled in production
  - [ ] Database connections use SSL/TLS
  - [ ] HTTP redirects to HTTPS configured

- [ ] **Infrastructure**
  - [ ] Cloud SQL instance has automated backups enabled
  - [ ] Cloud SQL backups are stored securely (geo-replicated)
  - [ ] Cloud Run service account has minimal required IAM roles
  - [ ] Service-to-service communication uses private ingress
  - [ ] VPC connector used for private database access (optional but recommended)
  - [ ] DDoS protection enabled (if applicable)

- [ ] **Monitoring & Logging**
  - [ ] Cloud Logging is enabled and monitoring critical errors
  - [ ] Log retention policy is set appropriately (e.g., 30 days)
  - [ ] Alerts configured for high error rates, timeouts, quota limits
  - [ ] Failed authentication attempts are logged
  - [ ] SQL injection/XSS attempt patterns are monitored

- [ ] **Compliance**
  - [ ] GDPR requirements met (if applicable)
  - [ ] Data retention policies defined and automated
  - [ ] User data deletion capability implemented
  - [ ] Terms of Service and Privacy Policy available
  - [ ] Audit logs maintained for compliance

- [ ] **Testing**
  - [ ] Security tests pass (see `test_*.py` files)
  - [ ] Load testing completed to ensure scalability
  - [ ] Penetration testing performed (if required)
  - [ ] API rate limiting tested

## Ongoing Operations ✅

- [ ] **Regular Updates**
  - [ ] Python dependencies updated monthly
  - [ ] Node.js dependencies updated monthly
  - [ ] Security patches applied immediately
  - [ ] GCP SDK and tools kept up-to-date

- [ ] **Monitoring**
  - [ ] Review logs weekly for suspicious activity
  - [ ] Monitor Cloud SQL query performance
  - [ ] Check Cloud Run error rates and latency
  - [ ] Verify backup integrity

- [ ] **Incident Response**
  - [ ] Incident response plan documented
  - [ ] Contact list for security incidents
  - [ ] Rollback procedure tested
  - [ ] Data breach notification process ready

## Resources

- [GCP Security Best Practices](https://cloud.google.com/security/best-practices)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Cloud SQL Security](https://cloud.google.com/sql/docs/postgres/security)
- [Cloud Run Security](https://cloud.google.com/run/docs/security)
EOF

log_info "SECURITY_CHECKLIST.md created ✅"

log_info "✅ Security remediation completed!"
log_info ""
log_info "Next steps:"
log_info "1. Review changes to backend/core/config.py and backend/main.py"
log_info "2. Create Secret Manager secrets (see DEPLOYMENT_GUIDE.md)"
log_info "3. Verify .env file is in .gitignore and not committed"
log_info "4. Review SECURITY_CHECKLIST.md before production deployment"

chmod +x scripts/security-remediation.sh

log_info "Security remediation complete! 🔒"
