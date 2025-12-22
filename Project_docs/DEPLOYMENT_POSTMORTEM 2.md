# Deployment Postmortem — Sentinel AI Compliance Platform

**Date:** 2025-12-18

## Executive summary
This document records every deployment issue we encountered during the Cloud Run migration and how we fixed them. It includes root causes, concrete fixes, verification steps, and prevention recommendations so we avoid the same problems in future deployments.

---

## Short timeline
- Inspected failures during Cloud Run deployments (backend, Presidio, Toxicity).
- Fixed Dockerfile and backend bugs (NumPy ABI pinning, pip check in builds, model pre-caching, CLOUD_MODE behavior, CORS formats, Dockerfile syntax, deploy script fixes).
- Verified fixes via successful image builds, Cloud Run revisions, /health checks, and authenticated login flow from the frontend.

---

## Issues, root causes, fixes, verification, and prevention

### 1. Backend import-time failures (ModuleNotFoundError and settings parse errors)
- Root cause: broken import paths and env parsing issues during Settings initialization.
- Fix: use package-relative imports and ensure envs are provided/parsed in the format pydantic expects.
- Verification: Cloud Run logs no longer show import errors; Uvicorn started successfully and `/api/v1/auth/login` returned 200.
- Prevention: add import-time tests (quick `python -c 'import <package>'`) in CI.

### 2. Presidio: "numpy.dtype size changed" (ABI mismatch)
- Root cause: incompatible NumPy version vs compiled C extensions (spaCy/thinc/presidio).
- Fix: pin `numpy==1.25.2` in `modules/presidio_service/Dockerfile`; run `pip check` in image build; pre-download spaCy model at build time.
- Verification: Build logs show `pip check` success and spaCy model download; Cloud Run `/health` returned activated true.
- Prevention: pin binary packages, run `pip check` in CI and during image builds.

### 3. Toxicity: Dockerfile heredoc error + large runtime downloads
- Root cause: malformed heredoc caused a build failure; Detoxify model downloads at runtime cause long cold starts.
- Fix: fix heredoc, pin `numpy`, and pre-cache Detoxify/HF model during image build.
- Verification: Docker build passes; /health reported `model_loaded:true`.
- Prevention: lint Dockerfiles and bake models into images.

### 4. Startup probe failures / cold starts
- Root cause: large model downloads happening at container runtime causing startup probe to fail.
- Fix: pre-download heavy artifacts in image build so containers start promptly.
- Verification: Cloud Run startup probes passed; services became Ready.
- Prevention: always cache heavy resources at build-time or increase probe timeouts only as a last resort.

### 5. Image architecture mismatch (local arm64 -> cloud amd64)
- Root cause: local builds on Apple Silicon produced images incompatible with Cloud Run.
- Fix: `scripts/deploy.sh` updated to build for `linux/amd64` (buildx or --platform).
- Verification: Cloud Run accepted and ran the linux/amd64 images.
- Prevention: Build for target architecture in CI or use multi-arch builds.

### 6. Deploy script bugs and missing post-deploy configuration
- Root cause: syntax bug and missing post-deploy env updates (CLOUD_MODE, PRESIDIO_URL, TOXICITY_URL, CORS).
- Fix: fix deploy script, set cloud environment variables post-deploy, and update CORS.
- Verification: envs visible in Cloud Run service spec.
- Prevention: lint deploy scripts and add smoke-tests after deploy.

### 7. `BACKEND_CORS_ORIGINS` pydantic parse error
- Root cause: pydantic expected JSON for complex env types; plain string caused `SettingsError`.
- Fix: set `BACKEND_CORS_ORIGINS` to a JSON-array string (e.g. `'["https://sentinel-frontend-...run.app"]'`) in Cloud Run.
- Verification: OPTIONS preflight returned `Access-Control-Allow-Origin`; POST login with Origin returned 200 + token.
- Prevention: standardize env formats; add deploy-time validation script to parse envs.

### 8. Frontend login showing "Login failed"
- Root cause: CORS blocking responses and (secondary) potential API base build-time misconfig.
- Fix: fixed backend CORS; verified backend logs show POST /auth/login; inspected bundle to confirm `VITE_API_BASE` usage.
- Verification: `OPTIONS` and `POST` with Origin succeeded; backend logs show login requests.
- Prevention: add E2E smoke test for login; ensure `VITE_API_BASE` is passed during the frontend build in deploy script.

### 9. Cloud-mode UX: start/stop controls
- Root cause: UI offered local Docker controls while running on Cloud Run.
- Fix: add `CLOUD_MODE` env flag; backend returns 400 for start/stop requests in cloud; UI hides controls.
- Verification: UI hides start/stop; backend responds 400 to local-control endpoints when in cloud mode.
- Prevention: Use config flags to gate local-only behavior and assert them in tests.

### 10. Temporary ingress change
- Actioned: temporarily allowed external health checks to validate services; recommended to revert to internal-only ingress.
- Prevention: use internal probes or authenticated endpoints for health checks.

### 11. Seeding & test accounts
- Action: `seed_data.py` can create admin and test users behind `SEED_DEFAULT_USERS` flag; created a test user for validation.
- Prevention: do not enable seeding in production; keep test credentials in Secret Manager for CI tests.

---

## Verification commands we used (examples)
- `gcloud run services list --region=europe-west1`
- `gcloud logging read 'resource.type="cloud_run_revision" AND textPayload:"/api/v1/auth/login"'`
- `curl -i -X OPTIONS "https://.../api/v1/auth/login" -H 'Origin: https://...frontend...' -H 'Access-Control-Request-Method: POST'`
- `curl -i -X POST "https://.../api/v1/auth/login" -H 'Origin: ...' -H 'Content-Type: application/x-www-form-urlencoded' --data 'username=admin@sentinel.ai&password=admin123'`
- `docker buildx build --platform linux/amd64 modules/presidio_service --file modules/presidio_service/Dockerfile --load`

---

## CI changes made in this session
We added a CI workflow that:
- **runs `pip check`** for the backend (installs `backend/requirements.txt` and runs `pip check`),
- **builds module images** for `linux/amd64` (Presidio and Toxicity). Image builds will surface `pip check` failures baked into the image builds.

See `.github/workflows/ci-pip-and-image-check.yml` for details.

---

## Concrete next actions (recommended)
- Add automated E2E smoke tests: login flow, module /health checks, and CORS validation after deploy.
- Add deploy-time env parsing validation script and run it in the deploy pipeline (fail fast if envs are malformed).
- Add linter jobs for `deploy.sh` (shellcheck) and Dockerfile linter (hadolint).

---

If you want, I can open a PR with the post-mortem and the CI workflow file, and I can start on the E2E smoke test job next.

(End of postmortem)
