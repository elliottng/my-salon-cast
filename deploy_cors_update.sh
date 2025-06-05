#!/bin/bash
# Script to deploy CORS configuration updates to staging and production environments
# This script updates the ALLOWED_ORIGINS environment variable to include Claude.ai and MCP Inspector domains

set -e  # Exit on any error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== MySalonCast MCP Server CORS Update Deployment ===${NC}"
echo "This script will update CORS settings to allow connections from:"
echo "  - https://claude.ai"
echo "  - https://inspect.mcp.garden"
echo ""

# Project configuration
PROJECT_ID="my-salon-cast"
REGION="us-west1"
STAGING_SERVICE="mcp-server-staging"
PRODUCTION_SERVICE="mcp-server"

# Verify gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Verify user is logged in
echo "Verifying gcloud authentication..."
gcloud auth print-identity-token &> /dev/null || {
    echo -e "${RED}Error: Not authenticated with gcloud. Please run 'gcloud auth login' first.${NC}"
    exit 1
}

# Confirm project
echo "Using Google Cloud project: ${PROJECT_ID}"
gcloud config set project ${PROJECT_ID}

# Function to update CORS settings for a service
update_cors_settings() {
    local service_name=$1
    local environment=$2
    
    echo -e "\n${YELLOW}=== Updating CORS settings for ${environment} (${service_name}) ===${NC}"
    
    # Get current environment variables
    echo "Retrieving current environment variables..."
    local current_env=$(gcloud run services describe ${service_name} \
        --region=${REGION} \
        --format="value(spec.template.spec.containers[0].env)")
    
    # Check if ALLOWED_ORIGINS is already set
    local has_allowed_origins=$(echo "$current_env" | grep -c "ALLOWED_ORIGINS" || true)
    
    if [ "$has_allowed_origins" -gt 0 ]; then
        echo "ALLOWED_ORIGINS environment variable already exists, updating it..."
        # Update existing ALLOWED_ORIGINS variable
        gcloud run services update ${service_name} \
            --region=${REGION} \
            --update-env-vars="ALLOWED_ORIGINS=https://claude.ai,https://inspect.mcp.garden"
    else
        echo "Adding ALLOWED_ORIGINS environment variable..."
        # Add new ALLOWED_ORIGINS variable
        gcloud run services update ${service_name} \
            --region=${REGION} \
            --set-env-vars="ALLOWED_ORIGINS=https://claude.ai,https://inspect.mcp.garden"
    fi
    
    echo -e "${GREEN}✓ CORS settings updated for ${environment}${NC}"
}

# Deploy to staging
echo -e "\n${YELLOW}=== Starting deployment to STAGING environment ===${NC}"
read -p "Deploy CORS updates to staging? (y/n): " confirm_staging
if [[ $confirm_staging == [yY] || $confirm_staging == [yY][eE][sS] ]]; then
    update_cors_settings ${STAGING_SERVICE} "staging"
    echo -e "${GREEN}✓ Staging deployment complete${NC}"
else
    echo "Skipping staging deployment."
fi

# Deploy to production
echo -e "\n${YELLOW}=== Starting deployment to PRODUCTION environment ===${NC}"
read -p "Deploy CORS updates to production? (y/n): " confirm_prod
if [[ $confirm_prod == [yY] || $confirm_prod == [yY][eE][sS] ]]; then
    update_cors_settings ${PRODUCTION_SERVICE} "production"
    echo -e "${GREEN}✓ Production deployment complete${NC}"
else
    echo "Skipping production deployment."
fi

echo -e "\n${GREEN}=== Deployment process completed ===${NC}"
echo "To verify the changes:"
echo "1. Connect to your staging server using the MCP Inspector at https://inspect.mcp.garden/"
echo "2. Test Claude.ai integration with your MCP server"
echo ""
echo "If you encounter any issues, check the Cloud Run logs for errors."
