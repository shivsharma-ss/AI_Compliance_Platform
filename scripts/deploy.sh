#!/bin/bash
# Quick deployment script for GCP Cloud Run
# Usage: ./scripts/deploy.sh [backend|frontend|toxicity|eu-ai|presidio|all]

set -e

# Configuration
PROJECT_ID="ai-compliance-platform-481511"
REGION="europe-west1"
ARTIFACT_REPO="sentinel-containers"
IMAGE_TAG="${IMAGE_TAG:-latest}"
SERVICE_ACCOUNT="sentinel-cloud-run@${PROJECT_ID}.iam.gserviceaccount.com"
SQL_CONNECTION_NAME="${SQL_CONNECTION_NAME:-}"  # Set this before running
# Database defaults (set by gcp-setup.sh)
DB_USER="sentinel_admin"
DB_NAME="sentinel_db"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
log_info() {
    echo -e "${GREEN}ℹ️  $1${NC}"
}

log_warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check gcloud
    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI not found. Please install it first."
        exit 1
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker not found. Please install it first."
        exit 1
    fi
    
    # Check if authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        log_error "Not authenticated with gcloud. Run 'gcloud auth login'"
        exit 1
    fi
    
    # Set project
    gcloud config set project $PROJECT_ID
    
    log_info "Prerequisites check passed ✅"
}

# Build and push an image
build_and_push() {
    local service=$1
    local docker_path=$2
    
    log_info "Building $service image..."
    
    local image_url="${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPO}/${service}:${IMAGE_TAG}"
    local latest_url="${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPO}/${service}:latest"
    
    # Build for linux/amd64 so images run on Cloud Run
    docker build --platform=linux/amd64 -t $image_url -t $latest_url $docker_path
    
    log_info "Pushing $service image..."
    docker push $image_url
    docker push $latest_url
    
    log_info "$service image built and pushed ✅"
    echo $image_url
}

# Deploy backend
deploy_backend() {
    log_info "Deploying backend service..."
    
    local image_url=$(build_and_push "sentinel-backend" "./backend" | tail -n1)
    
    if [ -z "$SQL_CONNECTION_NAME" ]; then
        log_error "SQL_CONNECTION_NAME not set. Exiting."
        exit 1
    fi

    # Fetch DB password from Secret Manager and construct DATABASE_URL for Cloud Run
    DB_PWD=$(gcloud secrets versions access latest --secret=DB_PASSWORD --project=$PROJECT_ID)
    DATABASE_URL="postgresql+asyncpg://${DB_USER}:${DB_PWD}@/${DB_NAME}?host=/cloudsql/${SQL_CONNECTION_NAME}"

    gcloud run deploy sentinel-backend \
        --image=$image_url \
        --project=$PROJECT_ID \
        --region=$REGION \
        --platform=managed \
        --service-account=$SERVICE_ACCOUNT \
        --add-cloudsql-instances=$SQL_CONNECTION_NAME \
        --set-env-vars=API_V1_STR="/api/v1",DATABASE_URL="$DATABASE_URL" \
        --update-secrets=SECRET_KEY=SECRET_KEY:latest,DB_PASSWORD=DB_PASSWORD:latest \
        --memory=512Mi \
        --cpu=1 \
        --timeout=3600 \
        --max-instances=10 \
        --min-instances=1 \
        --concurrency=80 \
        --allow-unauthenticated
    
    log_info "Backend deployed ✅"
    gcloud run services describe sentinel-backend --project=$PROJECT_ID --region=$REGION --format="value(status.url)"
}

# Deploy frontend
deploy_frontend() {
    log_info "Deploying frontend service..."
    
    # Get backend URL
    local backend_url=$(gcloud run services describe sentinel-backend \
        --project=$PROJECT_ID \
        --region=$REGION \
        --format="value(status.url)" 2>/dev/null || echo "https://sentinel-backend.europe-west1.run.app")
    
    log_info "Using backend URL: $backend_url"
    
    log_info "Building frontend image with backend URL..."
    local image_url="${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPO}/sentinel-frontend:${IMAGE_TAG}"
    local latest_url="${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPO}/sentinel-frontend:latest"
    
    docker build --platform=linux/amd64 \
        -t $image_url \
        -t $latest_url \
        --build-arg VITE_API_BASE=$backend_url \
        ./frontend
    
    docker push $image_url
    docker push $latest_url
    
    gcloud run deploy sentinel-frontend \
        --image=$image_url \
        --project=$PROJECT_ID \
        --region=$REGION \
        --platform=managed \
        --service-account=$SERVICE_ACCOUNT \
        --memory=256Mi \
        --cpu=0.5 \
        --timeout=3600 \
        --max-instances=5 \
        --min-instances=0 \
        --allow-unauthenticated
    
    log_info "Frontend deployed ✅"
    local frontend_url=$(gcloud run services describe sentinel-frontend --project=$PROJECT_ID --region=$REGION --format="value(status.url)")
    echo "$frontend_url"

    # Auto-update backend CORS to allow the new frontend origin
    cors_json=$(printf '["%s"]' "$frontend_url")
    log_info "Updating backend CORS origins to: $cors_json"
    gcloud run services update sentinel-backend \
        --update-env-vars=BACKEND_CORS_ORIGINS="$cors_json" \
        --project=$PROJECT_ID \
        --region=$REGION || log_warn "Failed to update backend env var for CORS. You can set BACKEND_CORS_ORIGINS manually."

    # Quick CORS smoke test
    backend_url=$(gcloud run services describe sentinel-backend --project=$PROJECT_ID --region=$REGION --format="value(status.url)")
    log_info "Running CORS preflight test against backend: $backend_url"
    resp_headers=$(curl -s -I -X OPTIONS "$backend_url/api/v1/auth/login" -H "Origin: $frontend_url" -H "Access-Control-Request-Method: POST" || true)
    if echo "$resp_headers" | grep -q "Access-Control-Allow-Origin"; then
        log_info "CORS preflight looks good ✅"
    else
        log_warn "CORS preflight failed — backend may still block the frontend. Check BACKEND_CORS_ORIGINS on the backend service."
    fi
}

# Deploy toxicity service
deploy_toxicity() {
    log_info "Deploying toxicity service..."
    
    local image_url=$(build_and_push "sentinel-toxicity" "./modules/toxicity_service" | tail -n1)
    
    gcloud run deploy sentinel-toxicity \
        --image=$image_url \
        --project=$PROJECT_ID \
        --region=$REGION \
        --platform=managed \
        --service-account=$SERVICE_ACCOUNT \
        --memory=2048Mi \
        --cpu=2 \
        --timeout=600 \
        --max-instances=3 \
        --min-instances=1 \
        --concurrency=1 \
        --allow-unauthenticated
    
    # Fetch toxicity service URL and update backend env (enable cloud mode)
    toxicity_url=$(gcloud run services describe sentinel-toxicity --project=$PROJECT_ID --region=$REGION --format="value(status.url)" 2>/dev/null || true)
    if [ -n "$toxicity_url" ]; then
        log_info "Toxicity URL: $toxicity_url"
        log_info "Updating backend with TOXICITY_URL and enabling CLOUD_MODE"
        gcloud run services update sentinel-backend \
            --update-env-vars=TOXICITY_URL="$toxicity_url",CLOUD_MODE="true" \
            --project=$PROJECT_ID \
            --region=$REGION || log_warn "Failed to update backend env vars for toxicity"
    fi

    log_info "Toxicity service deployed ✅"
    }

# Deploy EU AI service
deploy_eu_ai() {
    log_info "Deploying EU AI service..."
    
    local image_url=$(build_and_push "sentinel-eu-ai" "./modules/eu_ai_service" | tail -n1)
    
    gcloud run deploy sentinel-eu-ai \
        --image=$image_url \
        --project=$PROJECT_ID \
        --region=$REGION \
        --platform=managed \
        --service-account=$SERVICE_ACCOUNT \
        --memory=2048Mi \
        --cpu=2 \
        --timeout=600 \
        --max-instances=3 \
        --min-instances=1 \
        --concurrency=1 \
        --allow-unauthenticated

    # Fetch EU AI service URL and update backend env
    eu_ai_url=$(gcloud run services describe sentinel-eu-ai --project=$PROJECT_ID --region=$REGION --format="value(status.url)" 2>/dev/null || true)
    if [ -n "$eu_ai_url" ]; then
        log_info "EU AI URL: $eu_ai_url"
        log_info "Updating backend with EU_AI_URL and enabling CLOUD_MODE"
        gcloud run services update sentinel-backend \
            --update-env-vars=EU_AI_URL="$eu_ai_url",CLOUD_MODE="true" \
            --project=$PROJECT_ID \
            --region=$REGION || log_warn "Failed to update backend env vars for EU AI"
    fi

    log_info "EU AI service deployed ✅"
}

# Deploy Presidio service
deploy_presidio() {
    log_info "Deploying Presidio service..."
    
    local image_url=$(build_and_push "sentinel-presidio" "./modules/presidio_service" | tail -n1)
    
    gcloud run deploy sentinel-presidio \
        --image=$image_url \
        --project=$PROJECT_ID \
        --region=$REGION \
        --platform=managed \
        --service-account=$SERVICE_ACCOUNT \
        --memory=2048Mi \
        --cpu=2 \
        --timeout=600 \
        --max-instances=3 \
        --min-instances=1 \
        --concurrency=1 \
        --allow-unauthenticated
    
    # Fetch presidio service URL and update backend env
    presidio_url=$(gcloud run services describe sentinel-presidio --project=$PROJECT_ID --region=$REGION --format="value(status.url)" 2>/dev/null || true)
    if [ -n "$presidio_url" ]; then
        log_info "Presidio URL: $presidio_url"
        log_info "Updating backend with PRESIDIO_URL and enabling CLOUD_MODE"
        gcloud run services update sentinel-backend \
            --update-env-vars=PRESIDIO_URL="$presidio_url",CLOUD_MODE="true" \
            --project=$PROJECT_ID \
            --region=$REGION || log_warn "Failed to update backend env vars for presidio"
    fi

    log_info "Presidio service deployed ✅"
}

# Deploy all services
deploy_all() {
    log_info "Deploying all services..."
    deploy_backend
    deploy_frontend
    deploy_toxicity
    deploy_eu_ai
    deploy_presidio
    log_info "All services deployed ✅"
}

# Main
check_prerequisites

case "${1:-all}" in
    backend)
        deploy_backend
        ;;
    frontend)
        deploy_frontend
        ;;
    toxicity)
        deploy_toxicity
        ;;
    eu-ai)
        deploy_eu_ai
        ;;
    presidio)
        deploy_presidio
        ;;
    all)
        deploy_all
        ;;
    *)
        echo "Usage: $0 [backend|frontend|toxicity|eu-ai|presidio|all]"
        exit 1
        ;;
esac

log_info "Deployment complete! 🚀"
