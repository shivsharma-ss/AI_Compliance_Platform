# GCP Cloud Run Deployment Checklist

**Project:** Sentinel AI Compliance Platform  
**GCP Project ID:** `ai-compliance-platform-481511`  
**Region:** `europe-west1` (Belgium)  
**Date:** 2025-12-17

---

## 📋 Pre-Deployment Verification

### Infrastructure Prerequisites
- [ ] GCP project created and billing enabled
- [ ] `gcloud` CLI installed (`gcloud version`)
- [ ] Docker installed (`docker --version`)
- [ ] Authenticated with GCP (`gcloud auth login`)
- [ ] Project ID configured (`gcloud config get-value project`)

### Repository Readiness
- [ ] Repository cloned locally
- [ ] All dependencies installed:
  - [ ] Backend: `pip install -r backend/requirements.txt`
  - [ ] Frontend: `npm install` (from `frontend/` directory)
- [ ] Tests pass locally:
  - [ ] Backend: `cd backend && pytest tests/ -v`
  - [ ] Frontend: `npm run lint` (if available)

### Code Security Review
- [ ] No hardcoded secrets in code (checked with: `grep -r "CHANGE_THIS" .`)
- [ ] No database credentials in plaintext
- [ ] No API keys committed to repository
- [ ] `.env` and `.env.local` in `.gitignore`
- [ ] CORS origins configured appropriately
- [ ] Default credentials (admin@sentinel.ai / admin123) will NOT be seeded in prod

---

## 🔧 Infrastructure Setup

### Step 1: Provision GCP Resources (Automated)

```bash
# Make scripts executable
chmod +x scripts/*.sh

# Run automated setup
./scripts/gcp-setup.sh
```

This will create:
- [ ] Cloud SQL Postgres instance (`sentinel-postgres`)
- [ ] Database (`sentinel_db`) and user (`sentinel_admin`)
- [ ] Artifact Registry repository (`sentinel-containers`)
- [ ] Secret Manager secrets (`SECRET_KEY`, `DB_PASSWORD`, `OPENAI_API_KEY`)
- [ ] IAM Service Account (`sentinel-cloud-run`)
- [ ] IAM role bindings (Cloud SQL Client, Secret Manager Accessor, Artifact Registry Reader)
- [ ] VPC Connector (`sentinel-connector`)

**Save the output**, especially:
- `SQL_CONNECTION_NAME` (format: `PROJECT:REGION:INSTANCE`)
- `SERVICE_ACCOUNT_EMAIL` (format: `sentinel-cloud-run@PROJECT_ID.iam.gserviceaccount.com`)

### Step 2: Verify Infrastructure

```bash
# Verify Cloud SQL instance
gcloud sql instances describe sentinel-postgres --project=ai-compliance-platform-481511

# Verify Artifact Registry
gcloud artifacts repositories list --project=ai-compliance-platform-481511 --location=europe-west1

# Verify secrets
gcloud secrets list --project=ai-compliance-platform-481511

# Verify service account
gcloud iam service-accounts list --project=ai-compliance-platform-481511 | grep sentinel
```

---

## 🔒 Security Remediation

### Step 1: Remove Dev Secrets

```bash
# Run security remediation script
chmod +x scripts/security-remediation.sh
./scripts/security-remediation.sh
```

This will:
- [ ] Update `core/config.py` to remove `SECRET_KEY` default
- [ ] Gate seeding behind `SEED_DEFAULT_USERS=false`
- [ ] Create `.env.example` template
- [ ] Verify `.env` is in `.gitignore`
- [ ] Create `SECURITY_CHECKLIST.md`

### Step 2: Verify Changes

```bash
# Check that no dev secrets are exposed
grep -r "CHANGE_THIS" . --include="*.py"  # Should be empty
grep -r "admin123" . --include="*.py"  # Should be empty (except comments)

# Verify .gitignore
cat .gitignore | grep ".env"
```

### Step 3: Commit Changes

```bash
git add -A
git commit -m "security: Remove dev secrets and gate seeding"
git push origin main
```

---

## 🏗️ Build & Push Container Images

### Step 1: Authenticate Docker

```bash
export PROJECT_ID="ai-compliance-platform-481511"
export REGION="europe-west1"
gcloud auth configure-docker ${REGION}-docker.pkg.dev
```

### Step 2: Build Backend Image

```bash
export IMAGE_TAG="v1.0.0"  # Use semantic versioning
export ARTIFACT_REPO="sentinel-containers"

gcloud builds submit ./backend \
  --project=$PROJECT_ID \
  --tag="${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPO}/sentinel-backend:${IMAGE_TAG}" \
  --timeout=1200s
```

- [ ] Backend image built and pushed

### Step 3: Build Frontend Image

```bash
# First, deploy backend to get its URL (skip if already deployed)
export BACKEND_URL="https://sentinel-backend-XXXXX.europe-west1.run.app"

gcloud builds submit ./frontend \
  --project=$PROJECT_ID \
  --tag="${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPO}/sentinel-frontend:${IMAGE_TAG}" \
  --timeout=1200s \
  --build-arg=VITE_API_BASE=$BACKEND_URL
```

- [ ] Frontend image built and pushed

### Step 4: Build Microservice Images

```bash
# Toxicity Service
gcloud builds submit ./modules/toxicity_service \
  --project=$PROJECT_ID \
  --tag="${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPO}/sentinel-toxicity:${IMAGE_TAG}" \
  --timeout=1200s

# EU AI Service
gcloud builds submit ./modules/eu_ai_service \
  --project=$PROJECT_ID \
  --tag="${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPO}/sentinel-eu-ai:${IMAGE_TAG}" \
  --timeout=1200s

# Presidio Service
gcloud builds submit ./modules/presidio_service \
  --project=$PROJECT_ID \
  --tag="${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPO}/sentinel-presidio:${IMAGE_TAG}" \
  --timeout=1200s
```

- [ ] All microservice images built and pushed

---

## 🚀 Deploy Services to Cloud Run

### Prerequisites

Set environment variables:

```bash
export PROJECT_ID="ai-compliance-platform-481511"
export REGION="europe-west1"
export SQL_CONNECTION_NAME="ai-compliance-platform-481511:europe-west1:sentinel-postgres"
export SERVICE_ACCOUNT_EMAIL="sentinel-cloud-run@ai-compliance-platform-481511.iam.gserviceaccount.com"
export IMAGE_TAG="v1.0.0"
export ARTIFACT_REPO="sentinel-containers"
export IMAGE_BASE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPO}"
```

### Step 1: Deploy Backend

```bash
gcloud run deploy sentinel-backend \
  --image=${IMAGE_BASE}/sentinel-backend:${IMAGE_TAG} \
  --project=$PROJECT_ID \
  --region=$REGION \
  --platform=managed \
  --service-account=$SERVICE_ACCOUNT_EMAIL \
  --add-cloudsql-instances=$SQL_CONNECTION_NAME \
  --set-env-vars=\
API_V1_STR="/api/v1",\
BACKEND_CORS_ORIGINS="https://your-frontend-domain.com,http://localhost:5173" \
  --update-secrets=\
SECRET_KEY=projects/${PROJECT_ID}/secrets/SECRET_KEY:latest,\
OPENAI_API_KEY=projects/${PROJECT_ID}/secrets/OPENAI_API_KEY:latest \
  --memory=512Mi \
  --cpu=1 \
  --timeout=3600 \
  --max-instances=10 \
  --min-instances=1 \
  --concurrency=80 \
  --allow-unauthenticated \
  --ingress=all
```

- [ ] Backend service deployed
- [ ] Backend URL: `gcloud run services describe sentinel-backend --project=$PROJECT_ID --region=$REGION --format="value(status.url)"`

### Step 2: Deploy Frontend

Update BACKEND_URL with the URL from Step 1, then:

```bash
export BACKEND_URL="<URL from Step 1>"

# Rebuild frontend with correct backend URL
gcloud builds submit ./frontend \
  --project=$PROJECT_ID \
  --tag="${IMAGE_BASE}/sentinel-frontend:${IMAGE_TAG}" \
  --timeout=1200s \
  --build-arg=VITE_API_BASE=$BACKEND_URL

# Deploy
gcloud run deploy sentinel-frontend \
  --image=${IMAGE_BASE}/sentinel-frontend:${IMAGE_TAG} \
  --project=$PROJECT_ID \
  --region=$REGION \
  --platform=managed \
  --service-account=$SERVICE_ACCOUNT_EMAIL \
  --memory=256Mi \
  --cpu=0.5 \
  --timeout=3600 \
  --max-instances=5 \
  --min-instances=0 \
  --allow-unauthenticated \
  --ingress=all
```

- [ ] Frontend service deployed
- [ ] Frontend URL: `gcloud run services describe sentinel-frontend --project=$PROJECT_ID --region=$REGION --format="value(status.url)"`

### Step 3: Deploy Microservices

```bash
# Toxicity Service
gcloud run deploy sentinel-toxicity \
  --image=${IMAGE_BASE}/sentinel-toxicity:${IMAGE_TAG} \
  --project=$PROJECT_ID \
  --region=$REGION \
  --platform=managed \
  --service-account=$SERVICE_ACCOUNT_EMAIL \
  --memory=2048Mi \
  --cpu=2 \
  --timeout=600 \
  --max-instances=3 \
  --min-instances=1 \
  --concurrency=1 \
  --ingress=internal \
  --no-allow-unauthenticated

# EU AI Service
gcloud run deploy sentinel-eu-ai \
  --image=${IMAGE_BASE}/sentinel-eu-ai:${IMAGE_TAG} \
  --project=$PROJECT_ID \
  --region=$REGION \
  --platform=managed \
  --service-account=$SERVICE_ACCOUNT_EMAIL \
  --memory=2048Mi \
  --cpu=2 \
  --timeout=600 \
  --max-instances=3 \
  --min-instances=1 \
  --concurrency=1 \
  --ingress=internal \
  --no-allow-unauthenticated

# Presidio Service
gcloud run deploy sentinel-presidio \
  --image=${IMAGE_BASE}/sentinel-presidio:${IMAGE_TAG} \
  --project=$PROJECT_ID \
  --region=$REGION \
  --platform=managed \
  --service-account=$SERVICE_ACCOUNT_EMAIL \
  --memory=2048Mi \
  --cpu=2 \
  --timeout=600 \
  --max-instances=3 \
  --min-instances=1 \
  --concurrency=1 \
  --ingress=internal \
  --no-allow-unauthenticated
```

- [ ] All microservices deployed

---

## 🗄️ Run Database Migrations

### Option A: Using Cloud Run Job (Recommended)

```bash
# Create migration job (one-time)
gcloud run jobs create sentinel-migrate \
  --image=${IMAGE_BASE}/sentinel-backend:${IMAGE_TAG} \
  --project=$PROJECT_ID \
  --region=$REGION \
  --platform=managed \
  --service-account=$SERVICE_ACCOUNT_EMAIL \
  --add-cloudsql-instances=$SQL_CONNECTION_NAME \
  --set-env-vars=DATABASE_URL="postgresql+asyncpg://sentinel_admin:PASSWORD@/sentinel_db?host=/cloudsql/${SQL_CONNECTION_NAME}" \
  --update-secrets=SECRET_KEY=projects/${PROJECT_ID}/secrets/SECRET_KEY:latest \
  --memory=512Mi \
  --cpu=1 \
  --task-timeout=600 \
  --command="alembic" \
  --args="upgrade,head"

# Execute migration
gcloud run jobs execute sentinel-migrate \
  --project=$PROJECT_ID \
  --region=$REGION \
  --wait
```

- [ ] Database migrations completed

### Option B: Manual (if you have Cloud SQL proxy access)

```bash
cd backend
alembic upgrade head
```

---

## 🌐 Configure Frontend & Custom Domain

### Option A: Cloud Storage + Cloud CDN (Recommended)

```bash
# Create bucket
gsutil mb -l $REGION gs://sentinel-frontend-${PROJECT_ID}

# Build and upload
cd frontend
npm run build
gsutil -m rsync -r dist/ gs://sentinel-frontend-${PROJECT_ID}/

# Enable versioning
gsutil versioning set on gs://sentinel-frontend-${PROJECT_ID}
```

Then configure Load Balancer + Cloud CDN (manual step in GCP Console).

- [ ] Frontend bucket created
- [ ] Assets uploaded
- [ ] Cloud CDN configured

### Option B: Custom Domain (Optional)

```bash
# Map custom domain to Cloud Run (or Load Balancer)
gcloud run domain-mappings create \
  --service=sentinel-frontend \
  --domain=yourdomain.com \
  --region=$REGION \
  --project=$PROJECT_ID

# Verify DNS (check email for verification)
```

- [ ] Custom domain mapped
- [ ] DNS records updated
- [ ] SSL certificate provisioned

---

## 📊 Monitoring & Logging

### Step 1: Enable Cloud Logging

```bash
# Create logging sink (optional)
gcloud logging sinks create sentinel-logs \
  --log-filter='resource.type="cloud_run_revision"' \
  --destination=logging.googleapis.com/projects/$PROJECT_ID/logs/sentinel-app \
  --project=$PROJECT_ID
```

- [ ] Cloud Logging enabled

### Step 2: View Logs

```bash
# Stream backend logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=sentinel-backend" \
  --project=$PROJECT_ID \
  --limit=50 \
  --format=json

# View in Cloud Console
# https://console.cloud.google.com/logs/query?project=ai-compliance-platform-481511
```

- [ ] Logs accessible

### Step 3: Set Up Monitoring Alerts

In [Cloud Console → Cloud Monitoring](https://console.cloud.google.com/monitoring):
- [ ] Alert Policy: High error rate (5xx > 5%)
- [ ] Alert Policy: High latency (p95 > 5s)
- [ ] Alert Policy: Cloud SQL CPU > 80%
- [ ] Alert Policy: Cloud Run out of memory

---

## 🔄 CI/CD Setup

### Option A: GitHub Actions (Recommended)

```bash
# Create GitHub Secrets in repository settings:
# - GCP_PROJECT_ID: ai-compliance-platform-481511
# - WIF_PROVIDER: (Google Cloud setup)
# - WIF_SERVICE_ACCOUNT: sentinel-cloud-run@ai-compliance-platform-481511.iam.gserviceaccount.com
# - SQL_CONNECTION_NAME: ai-compliance-platform-481511:europe-west1:sentinel-postgres
# - SERVICE_ACCOUNT_EMAIL: sentinel-cloud-run@ai-compliance-platform-481511.iam.gserviceaccount.com
# - BACKEND_CORS_ORIGINS: https://your-domain.com
# - BACKEND_URL: https://sentinel-backend-XXX.europe-west1.run.app
# - OPENAI_API_KEY: sk-XXX (if using OpenAI)

# Commit and push
git add .github/workflows/deploy.yml
git commit -m "ci: Add GitHub Actions deployment workflow"
git push origin main
```

- [ ] GitHub Actions workflow deployed
- [ ] Secrets configured
- [ ] First workflow run successful

### Option B: Cloud Build (Alternative)

```bash
gcloud builds submit . \
  --config=cloudbuild.yaml \
  --project=$PROJECT_ID
```

- [ ] Cloud Build pipeline created

---

## ✅ Smoke Tests

### Test Backend

```bash
export BACKEND_URL=$(gcloud run services describe sentinel-backend \
  --project=$PROJECT_ID \
  --region=$REGION \
  --format="value(status.url)")

# Health check
curl $BACKEND_URL/health

# Auth endpoint
curl -X POST $BACKEND_URL/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"TestPass123"}'
```

- [ ] Backend /health responds
- [ ] Backend /api/v1/auth/register accessible

### Test Frontend

```bash
export FRONTEND_URL=$(gcloud run services describe sentinel-frontend \
  --project=$PROJECT_ID \
  --region=$REGION \
  --format="value(status.url)")

curl $FRONTEND_URL  # Should return HTML
```

- [ ] Frontend loads successfully

### Test Database Connection

```bash
# Check backend logs for DB connection errors
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=sentinel-backend" \
  --project=$PROJECT_ID \
  --limit=20
```

- [ ] No connection errors in logs

---

## 📈 Performance & Security Validation

### Performance Checks
- [ ] Backend response time < 1s (check Cloud Monitoring)
- [ ] Frontend assets cached (check Cloud CDN)
- [ ] Database query performance acceptable (< 500ms)
- [ ] No timeout errors in logs

### Security Checks
- [ ] CORS headers correct (only frontend domain allowed)
- [ ] JWT tokens issued and validated
- [ ] No sensitive data in logs
- [ ] HTTPS enforced (redirect HTTP → HTTPS)
- [ ] SQL injection prevention working
- [ ] Rate limiting active (if configured)

---

## 🎯 Post-Deployment Tasks

- [ ] Notify team of deployment
- [ ] Update documentation with production URLs
- [ ] Configure external monitoring (Datadog, New Relic, etc.) if needed
- [ ] Schedule security audit
- [ ] Plan capacity management (monitor costs)
- [ ] Set up on-call rotation for production support
- [ ] Document rollback procedure
- [ ] Schedule regular backup verification

---

## 📞 Rollback Procedure

If something goes wrong:

```bash
# Revert to previous image version
export PREVIOUS_IMAGE_TAG="v0.9.9"

gcloud run deploy sentinel-backend \
  --image=${IMAGE_BASE}/sentinel-backend:${PREVIOUS_IMAGE_TAG} \
  --project=$PROJECT_ID \
  --region=$REGION \
  --no-traffic  # Deploy without receiving traffic first

# After verification, update traffic
gcloud run update-traffic sentinel-backend \
  --to-revisions LATEST=100 \
  --project=$PROJECT_ID \
  --region=$REGION
```

---

## 📞 Support & Troubleshooting

| Issue | Solution |
|-------|----------|
| Backend can't connect to DB | Check Cloud SQL proxy, IAM roles, connection string |
| CORS errors from frontend | Update `BACKEND_CORS_ORIGINS` env var |
| High cold start times | Increase `--min-instances` or pre-warm containers |
| Out of memory errors | Increase `--memory` or optimize code |
| Slow queries | Check Cloud SQL logs, add indexes |

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for detailed troubleshooting.

---

## 📝 Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Deployment Lead | | | |
| Security Review | | | |
| Product Owner | | | |

---

**Last Updated:** 2025-12-17  
**Next Review:** After first production deployment
