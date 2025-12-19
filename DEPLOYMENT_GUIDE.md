# GCP Cloud Run Deployment Guide – Sentinel AI Compliance Platform

**Project ID:** `ai-compliance-platform-481511`  
**Region:** `europe-west1` (Belgium)  
**Services:** Backend (FastAPI), Frontend (Vue.js), Microservices (Toxicity, EU AI, Presidio)

---

## 📋 Table of Contents
1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Security Remediation](#security-remediation)
3. [Infrastructure Setup](#infrastructure-setup)
4. [Build & Push Images](#build--push-images)
5. [Deploy Services](#deploy-services)
6. [Run Migrations](#run-migrations)
7. [Configure Frontend](#configure-frontend)
8. [Monitoring & Logging](#monitoring--logging)
9. [CI/CD Setup](#cicd-setup)
10. [Troubleshooting](#troubleshooting)

---

## Pre-Deployment Checklist

- [ ] GCP project created and billing enabled
- [ ] `gcloud` CLI installed and authenticated
- [ ] Docker installed locally (for building images)
- [ ] Project ID set: `ai-compliance-platform-481511`
- [ ] Region set: `europe-west1`
- [ ] All dev secrets removed from code (see [Security Remediation](#security-remediation))
- [ ] OpenAI API key ready (if needed)
- [ ] Custom domain and DNS provider ready (optional but recommended)

---

## Security Remediation

### 1. Remove Default Secrets from Code
The following files contain dev credentials that **must not** be deployed to production:

#### File: `backend/core/config.py`
**Issue:** `SECRET_KEY` has a default placeholder value.  
**Fix:** Remove default; use Secret Manager only.

#### File: `backend/main.py`
**Issue:** Default admin/test users are seeded with predictable passwords.  
**Fix:** Gate seeding behind an environment flag.

#### File: `docker-compose.yml`
**Issue:** DB credentials are in plaintext (dev-only, but document why).  
**Fix:** Already dev-only, but ensure prod uses Secret Manager.

---

## Infrastructure Setup

### Step 1: Create Cloud SQL Postgres Instance

```bash
# Set environment variables for reuse
export PROJECT_ID="ai-compliance-platform-481511"
export REGION="europe-west1"
export INSTANCE_NAME="sentinel-postgres"
export DB_NAME="sentinel_db"
export DB_USER="sentinel_admin"

# Set your secure password (generate a strong one)
export DB_PASSWORD="YOUR_STRONG_PASSWORD_HERE"

# Create the Cloud SQL instance
gcloud sql instances create $INSTANCE_NAME \
  --project=$PROJECT_ID \
  --region=$REGION \
  --database-version=POSTGRES_17 \
  --tier=db-perf-optimized-N-2 \
  --storage-size=20GB \
  --storage-auto-increase \
  --backup-start-time=03:00 \
  --retained-backups-count=7

# Create database
gcloud sql databases create $DB_NAME \
  --instance=$INSTANCE_NAME \
  --project=$PROJECT_ID

# Create database user
gcloud sql users create $DB_USER \
  --instance=$INSTANCE_NAME \
  --password=$DB_PASSWORD \
  --project=$PROJECT_ID

# Get Cloud SQL connection name (you'll need this for Cloud Run)
gcloud sql instances describe $INSTANCE_NAME \
  --project=$PROJECT_ID \
  --format="value(connectionName)"
```

**Save the output** (connection name looks like `PROJECT_ID:REGION:INSTANCE_NAME`).

### Step 2: Create Artifact Registry

```bash
export ARTIFACT_REPO="sentinel-containers"

# Create Artifact Registry repository
gcloud artifacts repositories create $ARTIFACT_REPO \
  --project=$PROJECT_ID \
  --repository-format=docker \
  --location=$REGION

# Verify it was created
gcloud artifacts repositories list \
  --project=$PROJECT_ID \
  --location=$REGION
```

### Step 3: Create Secret Manager Secrets

```bash
# Generate a strong SECRET_KEY for JWT signing
export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# Create secrets in Secret Manager
echo -n "$SECRET_KEY" | gcloud secrets create SECRET_KEY \
  --project=$PROJECT_ID \
  --replication-policy="user-managed" \
  --locations=$REGION \
  --data-file=-

echo -n "$DB_PASSWORD" | gcloud secrets create DB_PASSWORD \
  --project=$PROJECT_ID \
  --replication-policy="user-managed" \
  --locations=$REGION \
  --data-file=-

# Optional: OpenAI API key (only if using OpenAI features)
# echo -n "YOUR_OPENAI_KEY" | gcloud secrets create OPENAI_API_KEY \
#   --project=$PROJECT_ID \
#   --replication-policy="user-managed" \
#   --locations=$REGION \
#   --data-file=-

# Verify secrets created
gcloud secrets list --project=$PROJECT_ID
```

### Step 4: Create Service Account for Cloud Run

```bash
export SA_NAME="sentinel-cloud-run"
export SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

# Create service account
gcloud iam service-accounts create $SA_NAME \
  --project=$PROJECT_ID \
  --display-name="Sentinel Cloud Run Service Account"

# Grant Cloud SQL Client role
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$SA_EMAIL \
  --role=roles/cloudsql.client

# Grant Secret Manager Secret Accessor role
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$SA_EMAIL \
  --role=roles/secretmanager.secretAccessor

# Grant Artifact Registry Reader role
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$SA_EMAIL \
  --role=roles/artifactregistry.reader

# Verify roles assigned
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:$SA_EMAIL" \
  --format="table(bindings.role)"
```

### Step 5: Create VPC Connector (Optional but Recommended)

For better security and private communication between services:

```bash
export VPC_CONNECTOR="sentinel-connector"

gcloud compute networks vpc-access connectors create $VPC_CONNECTOR \
  --project=$PROJECT_ID \
  --region=$REGION \
  --network=default \
  --range=10.8.0.0/28 \
  --min-throughput=200 \
  --max-throughput=1000

# NOTE: The IP range for the connector must be a /28 subnet (e.g., 10.8.0.0/28). Ensure the range does not overlap existing subnets.

# Verify
gcloud compute networks vpc-access connectors describe $VPC_CONNECTOR \
  --project=$PROJECT_ID \
  --region=$REGION
```

---

## Build & Push Images

### Prerequisites
- Authenticate Docker with Artifact Registry:

```bash
gcloud auth configure-docker ${REGION}-docker.pkg.dev
```

### Step 1: Build Backend Image

```bash
export IMAGE_TAG="latest"  # or "v1.0.0"
export BACKEND_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPO}/sentinel-backend:${IMAGE_TAG}"

# Build using Cloud Build (recommended)
gcloud builds submit ./backend \
  --project=$PROJECT_ID \
  --tag=$BACKEND_IMAGE \
  --timeout=1200s

# OR build locally and push:
# cd backend
# docker build -t $BACKEND_IMAGE .
# docker push $BACKEND_IMAGE
```

### Step 2: Build Frontend Image

```bash
# Determine backend Cloud Run URL (you'll get this after deploying backend, or use a placeholder)
export BACKEND_URL="https://sentinel-backend-GENERATED_URL.europe-west1.run.app"

export FRONTEND_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPO}/sentinel-frontend:${IMAGE_TAG}"

gcloud builds submit ./frontend \
  --project=$PROJECT_ID \
  --tag=$FRONTEND_IMAGE \
  --timeout=1200s \
  --build-arg=VITE_API_BASE=$BACKEND_URL
```

### Step 3: Build Microservice Images (Toxicity, EU AI, Presidio)

```bash
# Toxicity Service
export TOXICITY_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPO}/sentinel-toxicity:${IMAGE_TAG}"
gcloud builds submit ./modules/toxicity_service \
  --project=$PROJECT_ID \
  --tag=$TOXICITY_IMAGE \
  --timeout=1200s

# EU AI Service
export EU_AI_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPO}/sentinel-eu-ai:${IMAGE_TAG}"
gcloud builds submit ./modules/eu_ai_service \
  --project=$PROJECT_ID \
  --tag=$EU_AI_IMAGE \
  --timeout=1200s

# Presidio Service
export PRESIDIO_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPO}/sentinel-presidio:${IMAGE_TAG}"
gcloud builds submit ./modules/presidio_service \
  --project=$PROJECT_ID \
  --tag=$PRESIDIO_IMAGE \
  --timeout=1200s
```

---

## Deploy Services

### Prerequisites

Set environment variables (from previous steps):

```bash
export PROJECT_ID="ai-compliance-platform-481511"
export REGION="europe-west1"
export SA_EMAIL="sentinel-cloud-run@${PROJECT_ID}.iam.gserviceaccount.com"
export SQL_CONNECTION_NAME="YOUR_SQL_CONNECTION_NAME"  # e.g., ai-compliance-platform-481511:europe-west1:sentinel-postgres
export IMAGE_TAG="latest"
export ARTIFACT_REPO="sentinel-containers"

# Artifact Registry image base
export IMAGE_BASE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPO}"
```

### Step 1: Deploy Backend Service

```bash
gcloud run deploy sentinel-backend \
  --image=${IMAGE_BASE}/sentinel-backend:${IMAGE_TAG} \
  --project=$PROJECT_ID \
  --region=$REGION \
  --platform=managed \
  --service-account=$SA_EMAIL \
  --add-cloudsql-instances=$SQL_CONNECTION_NAME \
  --set-env-vars=\
API_V1_STR="/api/v1",\
BACKEND_CORS_ORIGINS="https://YOUR_FRONTEND_DOMAIN.com,http://localhost:5173",\
DATABASE_URL="postgresql+asyncpg://sentinel_admin:_db_password@/sentinel_db?host=/cloudsql/${SQL_CONNECTION_NAME}" \
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

**Important:** Replace `_db_password` with the actual DB password or use `${DB_PASSWORD}` if set in environment.

### Step 2: Get Backend URL and Redeploy Frontend

After backend is deployed, retrieve its URL:

```bash
export BACKEND_URL=$(gcloud run services describe sentinel-backend \
  --project=$PROJECT_ID \
  --region=$REGION \
  --format='value(status.url)')

echo "Backend URL: $BACKEND_URL"

# Rebuild frontend with correct backend URL
export FRONTEND_IMAGE="${IMAGE_BASE}/sentinel-frontend:${IMAGE_TAG}"

gcloud builds submit ./frontend \
  --project=$PROJECT_ID \
  --tag=$FRONTEND_IMAGE \
  --timeout=1200s \
  --build-arg=VITE_API_BASE=$BACKEND_URL
```

### Step 3: Deploy Frontend Service

```bash
gcloud run deploy sentinel-frontend \
  --image=${IMAGE_BASE}/sentinel-frontend:${IMAGE_TAG} \
  --project=$PROJECT_ID \
  --region=$REGION \
  --platform=managed \
  --service-account=$SA_EMAIL \
  --memory=256Mi \
  --cpu=0.5 \
  --timeout=3600 \
  --max-instances=5 \
  --min-instances=0 \
  --allow-unauthenticated \
  --ingress=all
```

### Step 4: Deploy Microservices (Optional)

#### Toxicity Service
```bash
gcloud run deploy sentinel-toxicity \
  --image=${IMAGE_BASE}/sentinel-toxicity:${IMAGE_TAG} \
  --project=$PROJECT_ID \
  --region=$REGION \
  --platform=managed \
  --service-account=$SA_EMAIL \
  --memory=2048Mi \
  --cpu=2 \
  --timeout=600 \
  --max-instances=3 \
  --min-instances=1 \
  --concurrency=1 \
  --ingress=internal \
  --no-allow-unauthenticated
```

#### EU AI Service
```bash
gcloud run deploy sentinel-eu-ai \
  --image=${IMAGE_BASE}/sentinel-eu-ai:${IMAGE_TAG} \
  --project=$PROJECT_ID \
  --region=$REGION \
  --platform=managed \
  --service-account=$SA_EMAIL \
  --memory=2048Mi \
  --cpu=2 \
  --timeout=600 \
  --max-instances=3 \
  --min-instances=1 \
  --concurrency=1 \
  --ingress=internal \
  --no-allow-unauthenticated
```

#### Presidio Service
```bash
gcloud run deploy sentinel-presidio \
  --image=${IMAGE_BASE}/sentinel-presidio:${IMAGE_TAG} \
  --project=$PROJECT_ID \
  --region=$REGION \
  --platform=managed \
  --service-account=$SA_EMAIL \
  --memory=2048Mi \
  --cpu=2 \
  --timeout=600 \
  --max-instances=3 \
  --min-instances=1 \
  --concurrency=1 \
  --ingress=internal \
  --no-allow-unauthenticated
```

---

## Run Migrations

After deploying the backend, run Alembic migrations to set up the database schema.

### Option A: Use Cloud Run Job (Recommended)

```bash
# Create and run a migration job
gcloud run jobs create sentinel-migrate \
  --image=${IMAGE_BASE}/sentinel-backend:${IMAGE_TAG} \
  --project=$PROJECT_ID \
  --region=$REGION \
  --platform=managed \
  --service-account=$SA_EMAIL \
  --add-cloudsql-instances=$SQL_CONNECTION_NAME \
  --set-env-vars=\
DATABASE_URL="postgresql+asyncpg://sentinel_admin:${DB_PASSWORD}@/sentinel_db?host=/cloudsql/${SQL_CONNECTION_NAME}" \
  --update-secrets=\
SECRET_KEY=projects/${PROJECT_ID}/secrets/SECRET_KEY:latest \
  --memory=512Mi \
  --cpu=1 \
  --task-timeout=600 \
  --command="alembic" \
  --args="upgrade,head"

# Execute the migration job
gcloud run jobs execute sentinel-migrate \
  --project=$PROJECT_ID \
  --region=$REGION
```

### Option B: Run Locally (if you have direct access to Cloud SQL)

```bash
# From your local machine with gcloud authenticated and Cloud SQL proxy running:
cd backend

# Set environment
export DATABASE_URL="postgresql+asyncpg://sentinel_admin:YOUR_PASSWORD@localhost:5433/sentinel_db"

# Run migration
alembic upgrade head
```

---

## Configure Frontend

### Option 1: Static Hosting (Recommended for Cost & Performance)

```bash
export FRONTEND_BUCKET="gs://sentinel-frontend-${PROJECT_ID}"

# Create Cloud Storage bucket
gsutil mb -l $REGION $FRONTEND_BUCKET

# Build frontend locally (if not done yet)
cd frontend
npm install
npm run build

# Upload assets to Cloud Storage
gsutil -m rsync -r -d dist/ $FRONTEND_BUCKET/

# Set public read access to bucket
gsutil iam ch serviceAccount:allUsers:objectViewer $FRONTEND_BUCKET

# (Optional) Enable versioning for rollback capability
gsutil versioning set on $FRONTEND_BUCKET
```

Then configure a Load Balancer + Cloud CDN to serve the bucket (see Cloud Console → Load Balancing).

### Option 2: Cloud Run (Simpler but Higher Cost)

Use the `gcloud run deploy sentinel-frontend` command from [Step 3 above](#step-3-deploy-frontend-service).

---

## Monitoring & Logging

### Enable Cloud Logging Sink

```bash
# Create a Cloud Logging sink to export logs
gcloud logging sinks create sentinel-logs \
  --log-filter='resource.type="cloud_run_revision"' \
  --destination=logging.googleapis.com/projects/$PROJECT_ID/logs/sentinel-app \
  --project=$PROJECT_ID
```

### Set Up Monitoring Alerts

```bash
# Example: Alert on high error rate (5xx responses)
gcloud alpha monitoring policies create \
  --notification-channels=YOUR_NOTIFICATION_CHANNEL_ID \
  --display-name="Sentinel Backend - High Error Rate" \
  --condition-display-name="Error rate > 5%" \
  --condition-threshold-value=0.05 \
  --condition-threshold-comparison=COMPARISON_GT
```

### View Logs

```bash
# Stream backend logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=sentinel-backend" \
  --project=$PROJECT_ID \
  --limit=100 \
  --format=json

# View in Cloud Console
# https://console.cloud.google.com/logs/query?project=ai-compliance-platform-481511
```

---

## CI/CD Setup

### Option 1: Cloud Build (Native GCP)

See `cloudbuild.yaml` in the repository root. Deploy using:

```bash
gcloud builds submit . \
  --config=cloudbuild.yaml \
  --project=$PROJECT_ID
```

### Option 2: GitHub Actions

See `.github/workflows/deploy.yml` in the repository root. Set up GitHub Secrets:

```bash
# In GitHub repo Settings → Secrets:
GCP_PROJECT_ID=ai-compliance-platform-481511
GCP_REGION=europe-west1
GCP_SERVICE_ACCOUNT_KEY=$(gcloud iam service-accounts keys create - \
  --iam-account=$SA_EMAIL --format=json)
```

Then push to main branch to trigger deployment.

---

## Troubleshooting

### Backend deployment fails with "DATABASE_URL not set"

**Solution:** Ensure the Secret Manager secret is created and the service account has `secretmanager.secretAccessor` role.

```bash
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:$SA_EMAIL"
```

### Frontend can't reach backend (CORS errors)

**Solution:** Update `BACKEND_CORS_ORIGINS` in backend deployment:

```bash
gcloud run deploy sentinel-backend \
  --update-env-vars=BACKEND_CORS_ORIGINS="https://YOUR_FRONTEND_DOMAIN.com" \
  --project=$PROJECT_ID \
  --region=$REGION
```

### Cloud SQL connection times out

**Solution:** Ensure the Cloud Run service account has `cloudsql.client` role and the SQL instance allows connections from Cloud Run.

```bash
# Check connectivity
gcloud sql connect $INSTANCE_NAME --project=$PROJECT_ID --user=$DB_USER
```

### Microservices (toxicity, eu_ai) OOM or timeout

**Solution:** Increase memory and CPU, and set `--concurrency=1`:

```bash
gcloud run deploy sentinel-toxicity \
  --memory=4096Mi \
  --cpu=2 \
  --concurrency=1 \
  --min-instances=1 \
  --project=$PROJECT_ID \
  --region=$REGION
```

### Cold starts for models are slow

**Solution:** Use `--min-instances=1` to keep a warm container, or pre-bake models into the image:

```dockerfile
# In Dockerfile, add model download at build time
RUN python -c "from transformers import AutoTokenizer; AutoTokenizer.from_pretrained('model-name')"
```

---

## Cost Estimation

| Service | CPU | Memory | Min Instances | Est. Monthly Cost (EUR) |
|---------|-----|--------|---------------|-------------------------|
| sentinel-backend | 1 | 512 Mi | 1 | ~€20 |
| sentinel-frontend | 0.5 | 256 Mi | 0 | ~€5 |
| sentinel-toxicity | 2 | 2 Gi | 1 | ~€60 |
| sentinel-eu-ai | 2 | 2 Gi | 1 | ~€60 |
| sentinel-presidio | 2 | 2 Gi | 1 | ~€60 |
| Cloud SQL (db-f1-micro) | - | - | - | ~€8 |
| Cloud Storage + CDN | - | - | - | ~€2–10 |
| **Total** | - | - | - | **~€215–225** |

*Note: Costs vary based on usage, egress, and storage. Use [GCP Pricing Calculator](https://cloud.google.com/products/calculator) for precise estimates.*

---

## Next Steps

1. ✅ Complete [Infrastructure Setup](#infrastructure-setup)
2. ✅ Fix security issues (see [Security Remediation](#security-remediation))
3. ✅ Build and push images (see [Build & Push Images](#build--push-images))
4. ✅ Deploy services (see [Deploy Services](#deploy-services))
5. ✅ Run migrations (see [Run Migrations](#run-migrations))
6. ✅ Configure DNS and custom domain
7. ✅ Set up monitoring and alerts (see [Monitoring & Logging](#monitoring--logging))
8. ✅ Enable CI/CD (see [CI/CD Setup](#cicd-setup))

---

**Support & Issues:**
- Check Cloud Run service details: `gcloud run services describe SERVICE_NAME --project=$PROJECT_ID --region=$REGION`
- Review Cloud Logs: `gcloud logging read "resource.type=cloud_run_revision" --project=$PROJECT_ID`
- GCP Support: https://cloud.google.com/support
