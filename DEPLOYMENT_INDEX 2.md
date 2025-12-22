# 🚀 GCP Cloud Run Deployment – START HERE

**Project:** Sentinel AI Compliance Platform  
**Target:** GCP Cloud Run (europe-west1, Belgium)  
**Status:** ✅ Ready for Production Deployment

---

## 📖 Choose Your Path

### ⚡ Quick Deployment (30-45 minutes)
**Best for:** Developers who want to deploy immediately

1. **Read:** [DEPLOYMENT_QUICK_START.md](DEPLOYMENT_QUICK_START.md) (5 min)
2. **Run:** `./scripts/gcp-setup.sh` (15 min)
3. **Run:** `./scripts/security-remediation.sh` (1 min)
4. **Run:** `./scripts/deploy.sh all` (20 min)
5. **Verify:** Smoke tests & logs

### 📋 Manual Deployment (45-60 minutes)
**Best for:** DevOps/Operators who prefer understanding each step

1. **Read:** [DEPLOYMENT_PLAN_COMPLETE.md](DEPLOYMENT_PLAN_COMPLETE.md) (10 min)
2. **Read:** [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) (30 min)
3. **Follow:** [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) step-by-step
4. **Review:** [SECURITY_CHECKLIST.md](SECURITY_CHECKLIST.md)

### 🏢 Enterprise Deployment (2-3 hours)
**Best for:** Large organizations with security/compliance requirements

1. **Review:** [DEPLOYMENT_PLAN_COMPLETE.md](DEPLOYMENT_PLAN_COMPLETE.md)
2. **Security:** Complete [SECURITY_CHECKLIST.md](SECURITY_CHECKLIST.md)
3. **Manual:** Follow [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
4. **Verify:** [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)
5. **Audit:** Penetration testing, compliance review
6. **CI/CD:** Setup GitHub Actions or Cloud Build

---

## 📚 Documentation Index

| Document | Purpose | Reading Time | Audience |
|----------|---------|--------------|----------|
| **[DEPLOYMENT_QUICK_START.md](DEPLOYMENT_QUICK_START.md)** | 5-step quick start | 5 min | Everyone |
| **[DEPLOYMENT_PACKAGE.md](DEPLOYMENT_PACKAGE.md)** | What you received | 5 min | Everyone |
| **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** | Complete step-by-step | 30 min | DevOps, Operators |
| **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** | Verification checklist | 45 min | QA, Verification |
| **[DEPLOYMENT_PLAN_COMPLETE.md](DEPLOYMENT_PLAN_COMPLETE.md)** | Executive summary | 10 min | Managers, Leads |
| **[SECURITY_CHECKLIST.md](SECURITY_CHECKLIST.md)** | Security review | 20 min | Security, Leads |

---

## 🔧 Automation Scripts

```bash
# 1️⃣ Setup GCP Infrastructure (15 min)
chmod +x scripts/gcp-setup.sh
./scripts/gcp-setup.sh
# Creates: Cloud SQL, Artifact Registry, Secrets, IAM, VPC Connector

# 2️⃣ Fix Security (1 min)
chmod +x scripts/security-remediation.sh
./scripts/security-remediation.sh
# Removes: Dev secrets, gates seeding, creates templates

# 3️⃣ Build & Deploy (20 min)
chmod +x scripts/deploy.sh
./scripts/deploy.sh all  # or: backend|frontend|toxicity|eu-ai|presidio
# Builds images, pushes to Artifact Registry, deploys to Cloud Run
```

---

## 🎯 What Gets Deployed

```
Cloud Run Services (europe-west1)
├─ sentinel-backend          (FastAPI, API Gateway, 512Mi, 1 CPU)
├─ sentinel-frontend         (Vue.js, SPA, 256Mi, 0.5 CPU)
├─ sentinel-toxicity         (Model inference, internal, 2GB, 2 CPU)
├─ sentinel-eu-ai            (Model inference, internal, 2GB, 2 CPU)
└─ sentinel-presidio         (PII detection, internal, 2GB, 2 CPU)

Cloud SQL
└─ sentinel-postgres         (PostgreSQL 18, db-f1-micro, automated backups)

Secret Manager
├─ SECRET_KEY               (JWT signing key)
├─ DB_PASSWORD              (Database password)
└─ OPENAI_API_KEY           (Optional)

Artifact Registry
└─ sentinel-containers      (Docker images for all services)
```

---

## 💰 Estimated Costs

| Service | Cost/Month |
|---------|------------|
| Cloud SQL | €8 |
| Cloud Run Services | €265 |
| Other (Storage, Logging, etc.) | €10 |
| **TOTAL** | **~€280/month** |

*(Includes costs from day 1. Costs may vary based on usage.)*

---

## ✅ Pre-Deployment Checklist

- [ ] GCP project created and billing enabled
- [ ] `gcloud` CLI installed (`gcloud version`)
- [ ] Docker installed (`docker --version`)
- [ ] Authenticated with GCP (`gcloud auth login`)
- [ ] Project ID: `ai-compliance-platform-481511`
- [ ] Region: `europe-west1`

---

## 🚀 Quick Start (Copy-Paste)

### Step 1: Setup Infrastructure
```bash
cd /Users/shiva/Desktop/practice\ projects/AI\ Compliance\ Platform
chmod +x scripts/gcp-setup.sh
./scripts/gcp-setup.sh
```

### Step 2: Fix Security
```bash
chmod +x scripts/security-remediation.sh
./scripts/security-remediation.sh

# Commit changes
git add -A
git commit -m "security: Remove dev secrets and gate seeding"
```

### Step 3: Deploy Services
```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh all
```

### Step 4: Verify Deployment
```bash
# Check services
gcloud run services list --project=ai-compliance-platform-481511 --region=europe-west1

# Test backend
BACKEND=$(gcloud run services describe sentinel-backend --project=ai-compliance-platform-481511 --region=europe-west1 --format="value(status.url)")
curl $BACKEND/health

# View logs
gcloud logging read "resource.type=cloud_run_revision" --project=ai-compliance-platform-481511 --limit=20
```

---

## 🔐 Security First

### What's Been Done ✅
- Removed dev secrets from code
- Setup GCP Secret Manager for all sensitive values
- Gated database seeding behind environment flag
- Configured IAM with minimal required permissions
- Set internal ingress for microservices (not publicly exposed)

### What You Need to Do
- [ ] Review [SECURITY_CHECKLIST.md](SECURITY_CHECKLIST.md)
- [ ] Update `BACKEND_CORS_ORIGINS` to your production domain
- [ ] Verify `.env` file is in `.gitignore`
- [ ] Generate strong `SECRET_KEY` (auto-done by gcp-setup.sh)
- [ ] Enable monitoring and alerts

---

## 📊 Deployment Timeline

| Step | Time | What Happens |
|------|------|--------------|
| **gcp-setup.sh** | 15 min | Creates all GCP infrastructure |
| **security-remediation.sh** | 1 min | Removes dev secrets, gates seeding |
| **deploy.sh all** | 20 min | Builds images, pushes, deploys services |
| **Database migrations** | 5-10 min | Runs Alembic migrations (after deploy) |
| **Smoke tests** | 5 min | Verifies health, auth, database |
| **Total** | **45-60 min** | Full production deployment |

---

## 🎁 What You've Received

### 📚 Documentation (5 Files)
✅ DEPLOYMENT_QUICK_START.md – 5-minute quick start  
✅ DEPLOYMENT_GUIDE.md – Complete detailed guide  
✅ DEPLOYMENT_CHECKLIST.md – Step-by-step verification  
✅ DEPLOYMENT_PLAN_COMPLETE.md – Executive summary  
✅ SECURITY_CHECKLIST.md – Security review

### 🔧 Automation Scripts (3 Files)
✅ scripts/gcp-setup.sh – Infrastructure provisioning  
✅ scripts/security-remediation.sh – Security hardening  
✅ scripts/deploy.sh – Build & deployment

### ⚙️ CI/CD Configuration (2 Files)
✅ .github/workflows/deploy.yml – GitHub Actions  
✅ cloudbuild.yaml – Cloud Build alternative

### 🔐 Code Updates (2 Files)
✅ backend/core/config.py – Updated (no default SECRET_KEY)  
✅ backend/main.py – Updated (SEED_DEFAULT_USERS flag)

---

## 🔄 Next Steps

### Right Now (5 minutes)
1. Read [DEPLOYMENT_QUICK_START.md](DEPLOYMENT_QUICK_START.md)
2. Review this README

### In the Next 15 minutes
1. Run `./scripts/gcp-setup.sh`
2. Save the output values
3. Run `./scripts/security-remediation.sh`

### In the Next 20 minutes
1. Update CORS origins in your domain
2. Run `./scripts/deploy.sh all`
3. Wait for deployment to complete

### In the Next 5-10 minutes
1. Run smoke tests
2. Check logs for errors
3. Verify backend health endpoint

---

## 📞 Having Issues?

### Quick Help
- **Cannot connect to GCP?** → Run `gcloud auth login`
- **Docker not found?** → Install Docker Desktop
- **Images not building?** → Check available disk space
- **Backend can't reach DB?** → Check Cloud SQL connection settings
- **CORS errors?** → Update `BACKEND_CORS_ORIGINS` environment variable

### Full Troubleshooting
→ See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md#troubleshooting) (Troubleshooting section)

### View Logs
```bash
gcloud logging read "resource.type=cloud_run_revision" \
  --project=ai-compliance-platform-481511 \
  --limit=100
```

---

## 🎓 Learn More

- **GCP Cloud Run:** https://cloud.google.com/run/docs
- **Cloud SQL:** https://cloud.google.com/sql/docs/postgres
- **Secret Manager:** https://cloud.google.com/secret-manager/docs
- **Cloud Build:** https://cloud.google.com/build/docs
- **Artifact Registry:** https://cloud.google.com/artifact-registry/docs

---

## ✨ You're All Set!

Your Sentinel AI Compliance Platform is ready for production deployment.

**Next Step:** Read [DEPLOYMENT_QUICK_START.md](DEPLOYMENT_QUICK_START.md) (5 min)

Then run: `./scripts/gcp-setup.sh` (15 min)

Then: `./scripts/deploy.sh all` (20 min)

**Total:** ~45 minutes to production! 🚀

---

**Status:** ✅ DEPLOYMENT READY  
**Created:** 2025-12-17  
**Project ID:** ai-compliance-platform-481511  
**Region:** europe-west1 (Belgium)

---

## 📋 File Structure

```
PROJECT_ROOT/
├── DEPLOYMENT_INDEX.md              ← You are here
├── DEPLOYMENT_QUICK_START.md        ← Read next
├── DEPLOYMENT_GUIDE.md              ← Detailed guide
├── DEPLOYMENT_CHECKLIST.md          ← Verification
├── DEPLOYMENT_PLAN_COMPLETE.md      ← Executive summary
├── SECURITY_CHECKLIST.md            ← Security review
├── DEPLOYMENT_PACKAGE.md            ← What you received
├── cloudbuild.yaml                  ← Cloud Build CI/CD
├── scripts/
│   ├── gcp-setup.sh                 ← 1️⃣ Run first
│   ├── security-remediation.sh      ← 2️⃣ Run second
│   └── deploy.sh                    ← 3️⃣ Run third
├── .github/
│   └── workflows/
│       └── deploy.yml               ← GitHub Actions
└── [... rest of project files ...]
```

---

Good luck! 🎉
