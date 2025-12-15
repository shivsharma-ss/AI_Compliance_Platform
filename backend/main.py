from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings
from api import auth, prompts

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)

# CORS (Allow frontend)
origins = ["http://localhost:5173", "http://localhost:3000", "*"] # Adjust for prod

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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

@app.get("/")
def read_root():
    return {"message": "Welcome to Spotixx AI Governance Gateway API"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
