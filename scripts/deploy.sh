#!/bin/bash

# MySalonCast Deployment Helper Script
# Simplified deployment with environment variable handling

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

echo -e "${BLUE}🚀 MySalonCast Deployment${NC}"
echo -e "${BLUE}========================${NC}"

# Automatically load environment variables from .env file
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"

if [[ -f "$ENV_FILE" ]]; then
    log_info "Loading environment variables from .env file..."
    set -a  # Export all variables
    source "$ENV_FILE"
    set +a  # Stop exporting
    log_success "Environment variables loaded from .env"
else
    log_warning "No .env file found at $ENV_FILE"
    if [[ -f "$PROJECT_ROOT/.env.template" ]]; then
        log_info "To get started:"
        echo "  1. cp .env.template .env"
        echo "  2. Edit .env and add your API keys"
        echo "  3. Run ./scripts/deploy.sh again"
    else
        log_error ".env.template file not found!"
        echo "Please ensure you're in the MySalonCast project directory"
    fi
fi

echo ""

# Check required environment variables
if [[ -z "$GEMINI_API_KEY" ]]; then
    log_error "GEMINI_API_KEY environment variable is required!"
    echo "Configure it in .env file or set with: export GEMINI_API_KEY='your-actual-api-key'"
    if [[ ! -f "$ENV_FILE" ]]; then
        echo "Run: cp .env.template .env"
        echo "Then edit .env with your actual API keys"
    fi
    exit 1
fi

# Optional Firecrawl configuration
FIRECRAWL_ENABLED=${FIRECRAWL_ENABLED:-false}
if [[ "$FIRECRAWL_ENABLED" == "true" ]] && [[ -z "$FIRECRAWL_API_KEY" ]]; then
    log_warning "FIRECRAWL_ENABLED=true but FIRECRAWL_API_KEY not set"
    log_warning "Setting FIRECRAWL_ENABLED=false"
    FIRECRAWL_ENABLED="false"
fi

# Build configuration
SERVICE_NAME=${SERVICE_NAME:-mysaloncast-api}
REGION=${REGION:-us-west1}
MEMORY=${MEMORY:-1Gi}
CPU=${CPU:-1}
MAX_INSTANCES=${MAX_INSTANCES:-10}

log_info "Deployment Configuration:"
echo "  Service Name: $SERVICE_NAME"
echo "  Region: $REGION"
echo "  Memory: $MEMORY"
echo "  CPU: $CPU"
echo "  Max Instances: $MAX_INSTANCES"
echo "  Gemini API: $(if [[ -n "$GEMINI_API_KEY" ]]; then echo "✅ Configured"; else echo "❌ Missing"; fi)"
echo "  Firecrawl: $(if [[ "$FIRECRAWL_ENABLED" == "true" ]]; then echo "✅ Enabled"; else echo "❌ Disabled"; fi)"
echo ""

# Build substitutions
SUBSTITUTIONS="_GEMINI_API_KEY=$GEMINI_API_KEY"
SUBSTITUTIONS+=",_SERVICE_NAME=$SERVICE_NAME"
SUBSTITUTIONS+=",_REGION=$REGION"
SUBSTITUTIONS+=",_MEMORY=$MEMORY"
SUBSTITUTIONS+=",_CPU=$CPU"
SUBSTITUTIONS+=",_MAX_INSTANCES=$MAX_INSTANCES"
SUBSTITUTIONS+=",_FIRECRAWL_ENABLED=$FIRECRAWL_ENABLED"

if [[ "$FIRECRAWL_ENABLED" == "true" ]]; then
    SUBSTITUTIONS+=",_FIRECRAWL_API_KEY=$FIRECRAWL_API_KEY"
fi

log_info "Starting Cloud Build deployment..."

gcloud builds submit \
    --config cloudbuild.yaml \
    --machine-type=e2-highcpu-8 \
    --substitutions="$SUBSTITUTIONS"

if [[ $? -eq 0 ]]; then
    log_success "Deployment completed successfully!"

    # Get service URL
    SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --format='value(status.url)' 2>/dev/null || echo "")

    if [[ -n "$SERVICE_URL" ]]; then
        echo ""
        log_success "🌐 Your API is live at:"
        echo "  📚 Documentation: $SERVICE_URL/docs"
        echo "  🔍 Health Check:  $SERVICE_URL/health"
        echo "  🔗 Service URL:   $SERVICE_URL"
    fi
else
    log_error "Deployment failed!"
    exit 1
fi
