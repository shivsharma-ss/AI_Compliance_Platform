# PRD Diff: GCP Deployment, CI Tooling, and Frontend Flows

## Scope (Compared to `compliance_marketplace`)
This diff adds a full Cloud Run deployment path for backend, frontend, and module microservices; introduces CI validation and image build checks; and updates frontend flows to support admin module management and user evaluation. It also adds cloud-mode behavior and configuration for module orchestration.

## Product Goals
- Provide a repeatable path to build, deploy, and host the app on GCP (Cloud Run + Cloud SQL + Artifact Registry).
- Ensure CI validates dependency health and container build viability.
- Enable admin and user flows aligned with cloud-hosted microservices and module controls.

## Requirements and Changes

### 1) GCP Hosting and Infrastructure (Cloud Run)
- Target platform: Cloud Run managed services for backend, frontend, and three microservices.
- Project defaults and region are hard-coded in scripts and workflows:
  - Project: `ai-compliance-platform-481511`
  - Region: `europe-west1`
  - Artifact Registry: `sentinel-containers`
- Cloud SQL Postgres 17 is provisioned by `scripts/gcp-setup.sh` with database `sentinel_db` and user `sentinel_admin`.
- Secrets are created in Secret Manager (`SECRET_KEY`, `DB_PASSWORD`, optional `OPENAI_API_KEY`).
- Cloud Run service account `sentinel-cloud-run@...` is granted:
  - `roles/cloudsql.client`
  - `roles/secretmanager.secretAccessor`
  - `roles/artifactregistry.reader`
- Optional VPC Connector `sentinel-connector` is provisioned for private connectivity.

Relevant files:
- `scripts/gcp-setup.sh`
- `scripts/deploy.sh`
- `.github/workflows/deploy.yml`

### 2) CI/CD: GitHub Actions Deployment Pipeline
- Pipeline is triggered on push to `main` and pull requests to `main`.
- Tests run before build:
  - Python 3.12
  - `pytest tests/ -v --tb=short`
- Build and push stages use Workload Identity Federation via GitHub secrets.
- Images built and pushed (tagged by commit SHA and `latest`):
  - `sentinel-backend`
  - `sentinel-frontend` (with `VITE_API_BASE` build arg from `BACKEND_URL`)
  - `sentinel-toxicity`
  - `sentinel-eu-ai`
  - `sentinel-presidio`
- Deploys Cloud Run services with resource and security settings:
  - Backend: 512Mi, CPU 1, concurrency 80, min instances 1, Cloud SQL attached, allow unauthenticated, secrets for `SECRET_KEY` and `OPENAI_API_KEY`, CORS and API path envs.
  - Frontend: 256Mi, CPU 0.5, min instances 0, allow unauthenticated.
  - Microservices: 2048Mi, CPU 2, concurrency 1, internal ingress, no unauthenticated.
- Runs `gcloud run jobs execute sentinel-migrate` for database migrations.

Relevant file:
- `.github/workflows/deploy.yml`

### 3) CI Tooling: Dependency and Image Verification
- CI workflow adds two validation steps:
  - `pip check` for backend dependency consistency.
  - Docker Buildx builds module images for linux/amd64 (no push).

Relevant file:
- `.github/workflows/ci-pip-and-image-check.yml`

### 4) Optional Cloud Build Pipeline (Alternate Path)
- `cloudbuild.yaml` mirrors tests and image builds, then deploys services.
- It uses `gke-deploy run --filename=k8s/ --cluster=sentinel-cluster`, which expects a `k8s/` directory and a GKE cluster.
- Cloud Run deploy steps use `--no-traffic` for frontend and microservices.
- Substitutions include `_BACKEND_URL` for frontend builds.

Relevant file:
- `cloudbuild.yaml`

### 5) Containerization and Build Context
- Backend container:
  - Python 3.12 slim, installs `gcc`, `libpq-dev`, runs `uvicorn` on `PORT` (default 8080).
- Frontend container:
  - Node 22, builds Vite app with `VITE_API_BASE`, serves static assets on `PORT`.
- Docker ignore files added to shrink build context and avoid secrets/logs.

Relevant files:
- `backend/Dockerfile`
- `frontend/Dockerfile`
- `backend/.dockerignore`
- `frontend/.dockerignore`

### 6) Backend Runtime Configuration (Cloud Mode)
- New config options:
  - `CLOUD_MODE`: disables Docker lifecycle control.
  - `PRESIDIO_URL`, `TOXICITY_URL`, `EU_AI_URL`: module endpoints in cloud.
  - `ENABLED_MODULES`: JSON array or comma-separated list to constrain active modules.
  - `SECRET_KEY`: required in production.
  - `BACKEND_CORS_ORIGINS`: accepts comma-separated input.
- Startup now only seeds default users when `SEED_DEFAULT_USERS=true`.
- Module admin API persists enabled flags in DB and blocks start/stop in cloud mode.
- Docker manager uses `/health` probes for service status in cloud mode; start/stop becomes no-op.

Relevant files:
- `backend/core/config.py`
- `backend/main.py`
- `backend/api/modules.py`
- `backend/managers/docker_manager.py`

### 7) Module Persistence and Rule Engine Behavior
- Adds a `module` table to persist enabled flags and seeds three module rows.
- Rule engine uses module enabled state to skip inactive services.
- Normalizes Cloud Run URLs and retries on transient module call failures.

Relevant files:
- `backend/models/module.py`
- `backend/schemas/module.py`
- `backend/alembic/versions/5b7f1d2a_add_module_table.py`
- `backend/services/rule_engine.py`

### 8) Frontend Flow Updates
- Auth store now uses `VITE_API_BASE` and routes by role.
- Login UI updated with branding and error display.
- Admin dashboard adds module marketplace cards, enable/disable toggles, start/stop controls for local Docker, and Cloud Run messaging with service links.
- User dashboard standardizes prompt evaluation and shows decision summaries.

Relevant files:
- `frontend/src/stores/auth.js`
- `frontend/src/views/Login.vue`
- `frontend/src/views/AdminDashboard.vue`
- `frontend/src/views/UserDashboard.vue`

## Risks and Gaps
- `backend/.dockerignore` excludes `alembic/` and `alembic.ini`, which may break `sentinel-migrate` if the migration job uses the backend image without bundled Alembic files.
- `cloudbuild.yaml` references `k8s/` and `sentinel-cluster`; if those assets do not exist, the Cloud Build path will fail.
- Microservices are deployed with internal ingress and no unauthenticated access; backend must reach them via internal routing and configured URLs.

## Acceptance Criteria
- CI passes `pip check` and module image build.
- GitHub Actions deploys all services to Cloud Run and runs migrations successfully.
- Backend `/health` is OK and frontend is reachable with correct API base.
- Admin UI lists modules and toggling enabled state persists in DB.
- Cloud mode prevents start/stop but shows module URLs and status.

## Deployment Readiness Runbook

### Prerequisites
- `gcloud` installed and authenticated.
- Artifact Registry and Cloud SQL APIs enabled in GCP project.

### Step 1: Provision Infrastructure
- Run `scripts/gcp-setup.sh`.
- Save outputs:
  - `SQL_CONNECTION_NAME`
  - Service account email
  - Artifact Registry name

### Step 2: Secrets in Secret Manager
- Create or confirm:
  - `SECRET_KEY`
  - `DB_PASSWORD`
  - `OPENAI_API_KEY` (optional)

### Step 3: GitHub Actions Secrets
Add to repo secrets:
- `WIF_PROVIDER`
- `WIF_SERVICE_ACCOUNT`
- `SQL_CONNECTION_NAME`
- `SERVICE_ACCOUNT_EMAIL`
- `BACKEND_CORS_ORIGINS` (frontend domain)
- `BACKEND_URL` (backend Cloud Run URL)

### Step 4: Database Migrations
- Ensure `sentinel-migrate` Cloud Run job exists.
- Confirm migration assets are present in the job image (see alembic ignore risk).

### Step 5: Deploy
Option A: GitHub Actions
- Merge or push to `main` to trigger `.github/workflows/deploy.yml`.

Option B: Local deploy
- `export SQL_CONNECTION_NAME=...`
- `./scripts/deploy.sh all`

Option C: Cloud Build
- `gcloud builds submit --config cloudbuild.yaml --substitutions=_BACKEND_URL=...`
- Requires `k8s/` and `sentinel-cluster` if using the gke-deploy step.

### Step 6: Post-Deploy Verification
- Backend: `GET /health`
- Frontend loads and login works against the Cloud Run backend.
- Admin panel shows module statuses and enabled flags persist.
- Microservice endpoints respond to `/health` and are reachable by backend.

## Required Configuration Values
Backend env (Cloud Run):
- `DATABASE_URL` (Cloud SQL socket URL)
- `SECRET_KEY`
- `API_V1_STR=/api/v1`
- `BACKEND_CORS_ORIGINS` (frontend URL list)
- `CLOUD_MODE=true`
- `PRESIDIO_URL`, `TOXICITY_URL`, `EU_AI_URL`
- `ENABLED_MODULES` (optional)

Frontend build env:
- `VITE_API_BASE` (backend Cloud Run URL)

Cloud Run resources (from `.github/workflows/deploy.yml`):
- Backend: 512Mi, CPU 1, concurrency 80, min instances 1
- Frontend: 256Mi, CPU 0.5, min instances 0
- Modules: 2048Mi, CPU 2, concurrency 1, internal ingress
