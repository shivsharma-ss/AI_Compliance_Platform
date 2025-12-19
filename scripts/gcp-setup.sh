#!/bin/bash
# GCP Cloud Run setup script - Automated infrastructure provisioning
# This script sets up all required GCP resources for production deployment

set -e

# Configuration
PROJECT_ID="ai-compliance-platform-481511"
REGION="europe-west1"
INSTANCE_NAME="sentinel-postgres"
DB_NAME="sentinel_db"
DB_USER="sentinel_admin"
SA_NAME="sentinel-cloud-run"
ARTIFACT_REPO="sentinel-containers"
VPC_CONNECTOR="sentinel-connector"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

# Check prerequisites
log_info "Checking prerequisites..."

if ! command -v gcloud &> /dev/null; then
    log_error "gcloud CLI not found. Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    log_error "Not authenticated. Run: gcloud auth login"
    exit 1
fi

# Set project
gcloud config set project $PROJECT_ID
log_success "Project set to $PROJECT_ID"

# Step 1: Create Cloud SQL Postgres instance
log_info "Step 1/7: Creating Cloud SQL Postgres instance..."

if gcloud sql instances describe $INSTANCE_NAME --project=$PROJECT_ID &>/dev/null; then
    log_warn "Cloud SQL instance already exists: $INSTANCE_NAME"
else
    gcloud sql instances create $INSTANCE_NAME \
        --project=$PROJECT_ID \
        --region=$REGION \
        --database-version=POSTGRES_17 \
        --tier=db-perf-optimized-N-2 \
        --storage-size=20GB \
        --storage-auto-increase \
        --backup-start-time=03:00 \
        --retained-backups-count=7
    
    log_success "Cloud SQL instance created: $INSTANCE_NAME"
fi

# Get connection name
SQL_CONNECTION_NAME=$(gcloud sql instances describe $INSTANCE_NAME \
    --project=$PROJECT_ID \
    --format="value(connectionName)")
log_success "SQL Connection Name: $SQL_CONNECTION_NAME"

# Step 2: Create database and user
log_info "Step 2/7: Creating database and user..."

if gcloud sql databases describe $DB_NAME --instance=$INSTANCE_NAME --project=$PROJECT_ID &>/dev/null; then
    log_warn "Database already exists: $DB_NAME"
else
    gcloud sql databases create $DB_NAME \
        --instance=$INSTANCE_NAME \
        --project=$PROJECT_ID
    log_success "Database created: $DB_NAME"
fi

# Check if user exists
if gcloud sql users describe $DB_USER --instance=$INSTANCE_NAME --project=$PROJECT_ID &>/dev/null; then
    log_warn "User already exists: $DB_USER"
    log_warn "To reset password, use: gcloud sql users set-password $DB_USER --instance=$INSTANCE_NAME --password=YOUR_PASSWORD"
else
    # Generate strong password
    DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    
    gcloud sql users create $DB_USER \
        --instance=$INSTANCE_NAME \
        --password=$DB_PASSWORD \
        --project=$PROJECT_ID
    
    log_success "User created: $DB_USER"
    log_info "Password: $DB_PASSWORD (SAVE THIS SECURELY)"
fi

# Step 3: Create Artifact Registry
log_info "Step 3/7: Creating Artifact Registry repository..."

if gcloud artifacts repositories describe $ARTIFACT_REPO --location=$REGION --project=$PROJECT_ID &>/dev/null; then
    log_warn "Artifact Registry repository already exists: $ARTIFACT_REPO"
else
    gcloud artifacts repositories create $ARTIFACT_REPO \
        --project=$PROJECT_ID \
        --repository-format=docker \
        --location=$REGION
    
    log_success "Artifact Registry repository created: $ARTIFACT_REPO"
fi

# Step 4: Create Secret Manager secrets
log_info "Step 4/7: Creating Secret Manager secrets..."

# Generate SECRET_KEY
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# Check and create SECRET_KEY secret
if gcloud secrets describe SECRET_KEY --project=$PROJECT_ID &>/dev/null; then
    log_warn "SECRET_KEY secret already exists"
else
    echo -n "$SECRET_KEY" | gcloud secrets create SECRET_KEY \
        --project=$PROJECT_ID \
        --replication-policy="automatic" \
        --data-file=-
    log_success "SECRET_KEY secret created"
fi

# For DB_PASSWORD, prompt user or use previously generated one
if ! gcloud secrets describe DB_PASSWORD --project=$PROJECT_ID &>/dev/null; then
    if [ -z "$DB_PASSWORD" ]; then
        read -sp "Enter database password (or press Enter to generate one): " DB_PASSWORD
        echo ""
        if [ -z "$DB_PASSWORD" ]; then
            DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
            log_info "Generated password: $DB_PASSWORD"
        fi
    fi
    
    echo -n "$DB_PASSWORD" | gcloud secrets create DB_PASSWORD \
        --project=$PROJECT_ID \
        --replication-policy="automatic" \
        --data-file=-
    log_success "DB_PASSWORD secret created"
else
    log_warn "DB_PASSWORD secret already exists"
fi

# Optional: Create OPENAI_API_KEY secret
if [ ! -z "$OPENAI_API_KEY" ]; then
    if gcloud secrets describe OPENAI_API_KEY --project=$PROJECT_ID &>/dev/null; then
        log_warn "OPENAI_API_KEY secret already exists"
    else
        echo -n "$OPENAI_API_KEY" | gcloud secrets create OPENAI_API_KEY \
            --project=$PROJECT_ID \
            --replication-policy="automatic" \
            --data-file=-
        log_success "OPENAI_API_KEY secret created"
    fi
fi

# List all secrets
log_info "Created secrets:"
gcloud secrets list --project=$PROJECT_ID --format="table(name,created)"

# Step 5: Create Service Account
log_info "Step 5/7: Creating Cloud Run service account..."

SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

if gcloud iam service-accounts describe $SA_EMAIL --project=$PROJECT_ID &>/dev/null; then
    log_warn "Service account already exists: $SA_EMAIL"
else
    gcloud iam service-accounts create $SA_NAME \
        --project=$PROJECT_ID \
        --display-name="Sentinel Cloud Run Service Account"
    log_success "Service account created: $SA_EMAIL"
fi

# Step 6: Grant IAM roles
log_info "Step 6/7: Granting IAM roles..."

declare -a ROLES=(
    "roles/cloudsql.client"
    "roles/secretmanager.secretAccessor"
    "roles/artifactregistry.reader"
)

for role in "${ROLES[@]}"; do
    if gcloud projects get-iam-policy $PROJECT_ID \
        --flatten="bindings[].members" \
        --filter="bindings.members:serviceAccount:$SA_EMAIL AND bindings.role:$role" \
        --format="value(bindings.role)" | grep -q "$role"; then
        log_warn "Role already assigned: $role"
    else
        gcloud projects add-iam-policy-binding $PROJECT_ID \
            --member=serviceAccount:$SA_EMAIL \
            --role=$role \
            --quiet
        log_success "Role granted: $role"
    fi
done

# Step 7: Create VPC Connector (optional)
log_info "Step 7/7: Creating VPC Connector (optional)..."

# Ensure VPC Access API is enabled
if ! gcloud services list --enabled --project=$PROJECT_ID | grep -q vpcaccess.googleapis.com; then
    log_info "Enabling VPC Access API..."
    gcloud services enable vpcaccess.googleapis.com --project=$PROJECT_ID
    log_success "VPC Access API enabled"
fi

if gcloud compute networks vpc-access connectors describe $VPC_CONNECTOR \
    --region=$REGION --project=$PROJECT_ID &>/dev/null; then
    log_warn "VPC Connector already exists: $VPC_CONNECTOR"
else
    log_info "Creating VPC Connector... (this may take 5-10 minutes)"
    # Use a dedicated /28 IP range for the connector (required by GCP)
    gcloud compute networks vpc-access connectors create $VPC_CONNECTOR \
        --project=$PROJECT_ID \
        --region=$REGION \
        --network=default \
        --range=10.8.0.0/28 \
        --min-throughput=200 \
        --max-throughput=1000
    
    log_success "VPC Connector created: $VPC_CONNECTOR"
fi

# Summary
log_info ""
log_info "╔════════════════════════════════════════════════════════════════╗"
log_info "║         GCP Infrastructure Setup Complete! 🎉                  ║"
log_info "╠════════════════════════════════════════════════════════════════╣"
log_info "║                                                                ║"
log_info "║ Project ID:            $PROJECT_ID"
log_info "║ Region:                $REGION"
log_info "║                                                                ║"
log_info "║ Cloud SQL Instance:    $INSTANCE_NAME"
log_info "║ SQL Connection Name:   $SQL_CONNECTION_NAME"
log_info "║ Database:              $DB_NAME"
log_info "║ DB User:               $DB_USER"
log_info "║                                                                ║"
log_info "║ Artifact Registry:     $ARTIFACT_REPO"
log_info "║ Service Account:       $SA_EMAIL"
log_info "║ VPC Connector:         $VPC_CONNECTOR"
log_info "║                                                                ║"
log_info "╠════════════════════════════════════════════════════════════════╣"
log_info "║                      Next Steps:                               ║"
log_info "║                                                                ║"
log_info "║ 1. Save these values for deployment:                           ║"
log_info "║    export SQL_CONNECTION_NAME=\"$SQL_CONNECTION_NAME\""
log_info "║    export SERVICE_ACCOUNT=\"$SA_EMAIL\""
log_info "║                                                                ║"
log_info "║ 2. Configure your GitHub Actions secrets:                      ║"
log_info "║    - WIF_PROVIDER: Workload Identity Federation provider      ║"
log_info "║    - WIF_SERVICE_ACCOUNT: $SA_EMAIL"
log_info "║    - SQL_CONNECTION_NAME: $SQL_CONNECTION_NAME"
log_info "║    - SERVICE_ACCOUNT_EMAIL: $SA_EMAIL"
log_info "║    - BACKEND_CORS_ORIGINS: your-frontend-domain.com           ║"
log_info "║    - BACKEND_URL: https://sentinel-backend-XXX.europe-west1...║"
log_info "║                                                                ║"
log_info "║ 3. Run: ./scripts/deploy.sh [backend|frontend|all]             ║"
log_info "║                                                                ║"
log_info "║ 4. Check DEPLOYMENT_GUIDE.md for detailed instructions        ║"
log_info "║                                                                ║"
log_info "╚════════════════════════════════════════════════════════════════╝"

# Save configuration to file
cat > .gcp-config << EOF
# GCP Configuration (generated at $(date))
export PROJECT_ID="$PROJECT_ID"
export REGION="$REGION"
export SQL_CONNECTION_NAME="$SQL_CONNECTION_NAME"
export SERVICE_ACCOUNT_EMAIL="$SA_EMAIL"
export ARTIFACT_REPO="$ARTIFACT_REPO"
export DB_NAME="$DB_NAME"
export DB_USER="$DB_USER"
export VPC_CONNECTOR="$VPC_CONNECTOR"
EOF

log_success "Configuration saved to .gcp-config (source this in future sessions)"
