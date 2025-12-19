# Sentinel AI Compliance Gateway

FastAPI + Vue.js demo platform for prompt-level governance aligned to the EU AI Act. The app lets analysts submit prompts for automated policy checks, stores an audit trail, and gives admins dashboards plus rule management. Optional microservices handle PII detection, toxicity, and simple EU AI Act risk labeling.

## What’s inside
- **Backend (FastAPI, async SQLAlchemy):** Auth (JWT), user roles, prompt evaluation, rule CRUD (admin), admin analytics, Docker-managed module control.
- **Frontend (Vue 3 + Vite + Pinia + vue-router):** Login, user dashboard for prompt submission/history, admin dashboard shell.
- **Microservices (FastAPI):**
  - `presidio_service`: spaCy + Presidio for PII.
  - `toxicity_service`: Detoxify for toxicity scoring.
  - `eu_ai_service`: Zero-shot classifier (BART) fallback heuristics for EU AI Act risk labels.
- **Database:** PostgreSQL (docker-compose) with users, rules, prompt requests/evaluations.
- **Containerization:** `docker-compose.yml` runs DB, backend, frontend, and optional modules.

## Repo structure
- `backend/` – FastAPI app, models, services, tests, Alembic stub.
- `frontend/` – Vue app (Vite) with auth flow and dashboards.
- `modules/` – Optional services (`presidio_service`, `toxicity_service`, `eu_ai_service`).
- `docker-compose.yml` – Local stack orchestration.
- `seed_data.py` – Creates an admin (`admin@sentinel.ai` / `admin123`) and test user (`user@test.com` / `user123`).
- `Project_docs/PRD.txt` – Product context and MVP requirements.

## Prerequisites
- Python 3.11+ (backend Dockerfile targets 3.12).
- Node 18+ (or use docker-compose for frontend).
- Docker & Docker Compose (for full stack and modules).
- PostgreSQL (if running backend outside Docker).

## Quick start (docker-compose)
From the repo root:
```bash
docker-compose up --build
```
Services:
- API: http://localhost:8000
- Frontend (Vite dev): http://localhost:5173
- Postgres: localhost:5432 (user `sentinel_user`, pwd `sentinel_password`, db `sentinel_db`)
- Modules: Presidio `sentinel-presidio` (8000 internal), Toxicity `sentinel-toxicity` (8002), EU AI `sentinel-eu-ai` (8003)

Optional module activation (downloads models on-demand):
```bash
curl -X POST http://localhost:8001/activate           # presidio_service (if exposed)
curl -X POST http://localhost:8003/activate           # eu_ai_service
```
> Note: `eu_ai_service` downloads a transformer model on first activation; `toxicity_service` loads its model at startup.

Seed default accounts (after DB is up):
```bash
python seed_data.py
```

## Backend: run locally without Docker
1) Create `.env` in `backend/` (pydantic-settings loads it):
```bash
DATABASE_URL=postgresql+asyncpg://sentinel_user:sentinel_password@localhost:5432/sentinel_db
SECRET_KEY=dev-secret-change-me
ACCESS_TOKEN_EXPIRE_MINUTES=30
OPENAI_API_KEY=                     # optional; current rule engine is rules + modules only
```
2) Install deps and init tables:
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python create_tables.py
```
3) Run the API:
```bash
uvicorn main:app --reload --port 8000
```

## Frontend: run locally without Docker
```bash
cd frontend
npm install
npm run dev -- --host  # expects backend at http://localhost:8000
```

## API walk-through
Base URL defaults to `http://localhost:8000/api/v1`.

Auth:
```bash
# register
curl -X POST http://localhost:8000/api/v1/auth/register -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}'

# login (form-encoded)
curl -X POST http://localhost:8000/api/v1/auth/login -d "username=user@example.com&password=password123"
```

Prompt evaluation:
```bash
TOKEN="..."  # access_token from login
curl -X POST http://localhost:8000/api/v1/prompts/evaluate \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"prompt_text":"Write a medical diagnosis","intended_use":"Fraud investigation","context":""}'
```
History (user-scoped):
```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/prompts/history
```

Admin endpoints (require `role=admin`):
- Rules CRUD: `GET/POST /api/v1/rules`
- Analytics: `GET /api/v1/admin/users/stats`, `GET /api/v1/admin/users/{user_id}/history`
- Module controls: `GET /api/v1/modules`, `POST /api/v1/modules/{module}/start|stop`

## Rule engine notes
- Regex-based rules (`Rule` model) with severity BLOCK/WARN; active rules fetched per request.
- Microservice hooks (PII, Toxicity, EU AI Act) consulted if corresponding containers are running.
- Decision: DECLINE on any BLOCK rule or high-risk module finding; otherwise ACCEPT with a reason summary.

## Data model (summary)
- `users`: email, hashed_password, role (`user`/`admin`), is_active.
- `rules`: name, description, type (`REGEX`, `KEYWORD`, `LLM`), payload_json, severity, is_active, version, timestamps.
- `promptrequest`: prompt text, intended_use, context, decision, reason_summary, user_id, created_at.
- `promptevaluation`: request_id, llm metadata, triggered_rules_json, trace_json.

## Testing
Backend tests (uses the running app/db configured in `.env`):
```bash
cd backend
pytest
```

## Deployment notes
- Each component has a Dockerfile; deploy as separate services (e.g., Google Cloud Run).
- Store secrets (DB URL, SECRET_KEY, OpenAI keys) in a secret manager; never bake into images.
- For faster cold starts, pre-download models in module images (`DOWNLOAD_MODELS=1` build arg).

## Troubleshooting
- **DB connection errors:** ensure Postgres is up and `DATABASE_URL` matches docker-compose credentials.
- **Model downloads slow/fail:** run module `/activate` endpoints once; consider building with `DOWNLOAD_MODELS=1`.
- **Unauthorized (401/403):** confirm JWT is present, not expired, and role is correct for admin routes.

