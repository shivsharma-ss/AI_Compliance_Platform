# GCP Cloud Run Deployment – Quick Start Guide

**TL;DR:** Run 3 scripts, update configs, deploy. Estimated time: 30-45 minutes (excluding migration).

---

## 🚀 Quick Start (5 Commands)

```bash
# 1. Setup infrastructure (creates Cloud SQL, Artifact Registry, IAM, Secrets)
chmod +x scripts/gcp-setup.sh
./scripts/gcp-setup.sh

# 2. Apply security fixes (removes dev secrets, gates seeding)
chmod +x scripts/security-remediation.sh
./scripts/security-remediation.sh

# 3. Build and push images (all services)
chmod +x scripts/deploy.sh
./scripts/deploy.sh all

# 4. View deployment status
gcloud run services list --project=ai-compliance-platform-481511 --region=europe-west1

# 5. Monitor logs (optional)
gcloud logging read "resource.type=cloud_run_revision" --project=ai-compliance-platform-481511 --limit=50
```

---

## 📚 Complete Documentation

| Document | Purpose |
|----------|---------|
| [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) | **In-depth guide** with all gcloud commands, troubleshooting, cost estimation |
| [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) | **Step-by-step checklist** for manual deployments, verification, smoke tests |
| [SECURITY_CHECKLIST.md](SECURITY_CHECKLIST.md) | **Security review** before/after deployment (created by security-remediation.sh) |

---

## 🔑 Key Values (Save These)

After running `./scripts/gcp-setup.sh`, you'll see:

```bash
Project ID:            ai-compliance-platform-481511
Region:                europe-west1
SQL Connection Name:   ai-compliance-platform-481511:europe-west1:sentinel-postgres
Service Account:       sentinel-cloud-run@ai-compliance-platform-481511.iam.gserviceaccount.com
```

Save the SQL Connection Name for CI/CD setup.

---

## 🔧 What Each Script Does

### `scripts/gcp-setup.sh` – Infrastructure Provisioning
Creates:
- Cloud SQL Postgres instance
- Database & user
- Artifact Registry repository
- Secret Manager secrets
- IAM service account with roles
- VPC Connector (optional)

**Time:** ~10-15 minutes  
**Cost:** ~$8/month (Cloud SQL) + $2-5 (other services)

### `scripts/security-remediation.sh` – Fix Dev Secrets
Modifies:
- `backend/core/config.py` – Removes default `SECRET_KEY`
- `backend/main.py` – Gates seeding behind `SEED_DEFAULT_USERS=false`
- Creates `.env.example` template
- Creates `SECURITY_CHECKLIST.md`

**Time:** < 1 minute  
**Important:** Commit these changes before deployment

### `scripts/deploy.sh` – Build & Deploy Services
Options:
- `./scripts/deploy.sh backend` – Backend only
- `./scripts/deploy.sh frontend` – Frontend only
- `./scripts/deploy.sh all` – All services

**Time:** ~10-15 minutes (backend), ~5 minutes (frontend), ~20 minutes per microservice

---

## ⚙️ Configuration Before Deployment

### 1. Set Environment Variables

```bash
export PROJECT_ID="ai-compliance-platform-481511"
export REGION="europe-west1"
export SQL_CONNECTION_NAME="ai-compliance-platform-481511:europe-west1:sentinel-postgres"  # From gcp-setup.sh
export SERVICE_ACCOUNT_EMAIL="sentinel-cloud-run@ai-compliance-platform-481511.iam.gserviceaccount.com"
```

### 2. Update CORS Origins

In the deployment command (or `scripts/deploy.sh`):
```bash
BACKEND_CORS_ORIGINS="https://your-actual-frontend-domain.com"
```

### 3. (Optional) Configure GitHub Actions

Create GitHub Secrets in your repo:
```bash
GCP_PROJECT_ID = ai-compliance-platform-481511
WIF_PROVIDER = (setup in GCP)
WIF_SERVICE_ACCOUNT = sentinel-cloud-run@ai-compliance-platform-481511.iam.gserviceaccount.com
SQL_CONNECTION_NAME = ai-compliance-platform-481511:europe-west1:sentinel-postgres
BACKEND_CORS_ORIGINS = https://your-domain.com
```

---

## 🧪 Verification After Deployment

```bash
# 1. Check all services are running
gcloud run services list --project=ai-compliance-platform-481511 --region=europe-west1

# 2. Test backend health
BACKEND_URL=$(gcloud run services describe sentinel-backend --project=ai-compliance-platform-481511 --region=europe-west1 --format="value(status.url)")
curl $BACKEND_URL/health

# 3. Test frontend loads
FRONTEND_URL=$(gcloud run services describe sentinel-frontend --project=ai-compliance-platform-481511 --region=europe-west1 --format="value(status.url)")
curl $FRONTEND_URL | head -20

# 4. Check logs for errors
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" --project=ai-compliance-platform-481511 --limit=20
```

---

## 🚨 Common Issues & Fixes

| Problem | Quick Fix |
|---------|-----------|
| "Authentication required" | Run `gcloud auth login` |
| "Permission denied" | Check service account IAM roles: `gcloud projects get-iam-policy ai-compliance-platform-481511 --flatten="bindings[].members" --filter="bindings.members:serviceAccount:sentinel-cloud-run*"` |
| Backend can't reach DB | Verify SQL connection name: `gcloud sql instances describe sentinel-postgres --format="value(connectionName)"` |
| CORS errors | Update `BACKEND_CORS_ORIGINS` in deployment: `gcloud run deploy sentinel-backend --update-env-vars=BACKEND_CORS_ORIGINS="https://your-domain.com"` |
| Image not found | Check Artifact Registry: `gcloud artifacts repositories list --location=europe-west1` |
| Out of memory | Increase memory: `gcloud run deploy SERVICE_NAME --memory=1024Mi` |

---

## 📊 Cost Breakdown

| Service | Estimated Monthly Cost |
|---------|------------------------|
| Cloud SQL (db-f1-micro) | ~€8 |
| Cloud Run (backend, min-instances=1) | ~€20 |
| Cloud Run (frontend, min-instances=0) | ~€5 |
| Cloud Run (microservices, min-instances=1 each) | ~€180 |
| Artifact Registry (images) | ~€1-2 |
| Cloud Storage (if using for static assets) | ~€2-5 |
| Cloud Logging/Monitoring | ~€0-5 |
| **Total** | **~€220-230/month** |

*Costs can be reduced by scaling down min-instances or using static hosting for frontend.*

---

## 🔐 Security Reminders

✅ **Do these before deploying:**
- [ ] Run `./scripts/security-remediation.sh`
- [ ] Review changes to `core/config.py` and `main.py`
- [ ] Verify no `.env` file is committed
- [ ] Generate strong `SECRET_KEY` (already done by gcp-setup.sh)
- [ ] Update `BACKEND_CORS_ORIGINS` to production domain
- [ ] Review SECURITY_CHECKLIST.md

❌ **Never do these:**
- [ ] Commit `.env` file
- [ ] Use default passwords
- [ ] Expose internal microservices publicly (use `--ingress=internal`)
- [ ] Skip Secret Manager for sensitive values
- [ ] Deploy without running migrations

---

## 📞 When Things Go Wrong

### 1. Check Logs Immediately

```bash
# Backend errors
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=sentinel-backend AND severity>=ERROR" \
  --project=ai-compliance-platform-481511 --limit=50 --format=json

# Check specific error pattern
gcloud logging read "textPayload=~'connection refused|database|ERROR'" \
  --project=ai-compliance-platform-481511 --limit=20
```

### 2. Check Service Status

```bash
# Detailed service info
gcloud run services describe sentinel-backend --project=ai-compliance-platform-481511 --region=europe-west1

# View recent revisions
gcloud run revisions list --service=sentinel-backend --project=ai-compliance-platform-481511 --region=europe-west1
```

### 3. Rollback to Previous Version

```bash
# Deploy previous image tag
gcloud run deploy sentinel-backend \
  --image=europe-west1-docker.pkg.dev/ai-compliance-platform-481511/sentinel-containers/sentinel-backend:v0.9.9 \
  --project=ai-compliance-platform-481511 \
  --region=europe-west1
```

### 4. Scale Down to Debug

```bash
# Temporarily disable auto-scaling
gcloud run deploy sentinel-backend \
  --min-instances=0 \
  --max-instances=1 \
  --project=ai-compliance-platform-481511 \
  --region=europe-west1
```

---

## 📖 Next Steps

1. **Read [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** for detailed instructions
2. **Follow [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** step-by-step
3. **Run `./scripts/gcp-setup.sh`** to provision infrastructure
4. **Run `./scripts/security-remediation.sh`** to fix security issues
5. **Run `./scripts/deploy.sh all`** to deploy all services
6. **Run smoke tests** (see Verification section above)
7. **Set up monitoring & alerts** in Cloud Console
8. **Enable CI/CD** via GitHub Actions or Cloud Build

---

## 💡 Pro Tips

- **Pre-warm containers:** Set `--min-instances=1` for critical services
- **Faster builds:** Use Cloud Build (faster than local docker builds)
- **Monitor costs:** Set up budget alerts in GCP Console
- **Blue-Green deploys:** Deploy new revision without traffic first with `--no-traffic`, then update traffic after testing
- **Efficient secrets:** Use Workload Identity Federation instead of service account keys

---

## 📞 Support

- **GCP Documentation:** https://cloud.google.com/run/docs
- **Troubleshooting:** https://cloud.google.com/run/docs/troubleshooting/general-errors
- **Community:** https://stackoverflow.com/questions/tagged/google-cloud-run

---

**Created:** 2025-12-17  
**Project:** Sentinel AI Compliance Platform  
**Region:** europe-west1 (Belgium)  
**Status:** Ready for deployment ✅
