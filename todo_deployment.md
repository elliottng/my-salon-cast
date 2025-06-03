# MySalonCast Deployment Todo List

**Target**: Deploy MCP server with async podcast generation to GCP staging and production environments.
**Note**: H denotes human, A denotes AI. **SQLite-based with Terraform + Secret Manager for production best practices.**

## Phase 1: Infrastructure & Configuration (1 hour)

#### **H1-1: GCP Project Setup**
- [ ] Verify GCP project `my-salon-cast` exists and billing is enabled
- [ ] Ensure you have Owner or Editor role on the project
- [ ] Note your GCP project number (will be needed later)

#### **H1-2: API Keys Preparation**
- [ ] Locate your Gemini API key
- [ ] Locate your Google Cloud TTS API key  
- [ ] Have both keys ready for Secret Manager storage

#### **A1-1: Update Terraform Configuration**
- [ ] Modify `terraform/main.tf` for dual-environment setup (staging + production)
- [ ] Add Cloud Storage buckets for staging/production (audio files + SQLite backups)
- [ ] Add Secret Manager resources for API keys (shared across environments)
- [ ] Configure Cloud Run services for MCP server (staging + production)
- [ ] Set region to `us-west1`
- [ ] Configure staging with lower resource limits (0.5GB RAM, 1 max instance)

#### **A1-2: SQLite Database Configuration** 
- [ ] Update `app/database.py` to use SQLite with Cloud Storage backup
- [ ] Add SQLite file backup/restore functionality to/from Cloud Storage
- [ ] Configure startup logic to download latest SQLite file from GCS
- [ ] Add periodic backup of SQLite to Cloud Storage (daily for cost optimization)
- [ ] Keep existing SQLModel models unchanged

#### **A1-3: Environment Configuration**
- [ ] Create `.env.staging` and `.env.production` templates
- [ ] Update `app/main.py` to handle Cloud Run environment variables
- [ ] Configure SQLite file paths for Cloud Run filesystem
- [ ] Add Secret Manager integration for API key retrieval
- [ ] Add environment detection logic (staging vs production)

## Phase 2: Storage & File Handling

#### **A2-1: Cloud Storage Integration**
- [ ] Enhance `app/storage.py` to support Cloud Storage
- [ ] Add environment detection (local vs staging/production)
- [ ] Implement audio file upload to appropriate GCS bucket
- [ ] Add file cleanup policies for budget management
- [ ] Update `app/podcast_workflow.py` to use cloud storage paths

#### **A2-2: File Path Management**
- [ ] Update `PodcastEpisode` model to store GCS paths instead of local paths
- [ ] Modify audio serving logic for cloud storage URLs
- [ ] Add signed URL generation for private audio access

## Phase 3: MCP Server Deployment Configuration (1 hour)

#### **A3-1: MCP Server Containerization**
- [ ] Update `Dockerfile` for production deployment
- [ ] Add health checks specific to MCP server
- [ ] Optimize container size and startup time
- [ ] Add proper signal handling for graceful shutdown

#### **A3-2: Cloud Build Configuration**
- [ ] Create `cloudbuild.yaml` for automated deployment
- [ ] Configure staging and production builds
- [ ] Add environment-specific deployment steps
- [ ] Set up automated testing in build pipeline

#### **A3-3: MCP Server Configuration**
- [ ] Update `app/mcp_server.py` for staging/production environments
- [ ] Add proper error handling and logging
- [ ] Configure service startup for Cloud Run
- [ ] Add production monitoring endpoints

## Phase 4: Secret Management & Security (30 minutes)

#### **H4-1: Store API Keys in Secret Manager**
```bash
# You'll run these commands:
echo "your-gemini-key" | gcloud secrets create gemini-api-key --data-file=-
echo "your-tts-key" | gcloud secrets create google-tts-api-key --data-file=-
```

#### **A4-1: Secret Manager Integration**
- [ ] Update application to fetch secrets from Secret Manager
- [ ] Add service account permissions for secret access
- [ ] Update environment configuration to use secrets
- [ ] Add fallback handling for local development

## Phase 5: Infrastructure Deployment (30 minutes)

#### **H5-1: Deploy Infrastructure**
```bash
# You'll run these commands in Windsurf terminal:
cd terraform/
terraform init
terraform plan
terraform apply  # Type 'yes' when prompted
```
#### **H5-2: Verify Infrastructure**
- [ ] Check Cloud Storage buckets are created
- [ ] Verify Secret Manager secrets are accessible

#### **A5-1: Database Initialization**
- [ ] Create initial SQLite database file
- [ ] Add database initialization to deployment pipeline
- [ ] Set up separate staging/production SQLite files on Cloud Storage

## Phase 6: Application Deployment (45 minutes)

#### **H6-1: Initial Application Deployment**
```bash
# You'll run these commands:
gcloud builds submit --config=cloudbuild.yaml
```
#### **H6-2: Database Setup**
```bash
# No database setup needed for SQLite
```
#### **A6-1: Deployment Pipeline Setup**
- [ ] Configure Cloud Build triggers for automatic deployment
- [ ] Set up branch-based deployment (main → production, dev → staging)
- [ ] Add deployment verification steps
- [ ] Configure rollback procedures

#### **A6-2: Service Configuration**
- [ ] Configure Cloud Run services with appropriate resources
- [ ] Set up environment variables from Secret Manager
- [ ] Configure scaling parameters for budget optimization
- [ ] Add custom domains if requested

---

## Phase 7: Testing & Verification (45 minutes)

#### **H7-1: End-to-End Testing**
- [ ] Test MCP server connectivity from Claude Desktop or MCP client
- [ ] Verify async podcast generation workflow
- [ ] Test file storage and retrieval
- [ ] Confirm staging and production environments work

#### **H7-2: Performance Validation**
- [ ] Generate a test podcast to verify full pipeline
- [ ] Check audio file upload to Cloud Storage
- [ ] Verify SQLite database persistence
- [ ] Test concurrent generation limits

#### **A7-1: Monitoring Setup**
- [ ] Deploy basic capacity monitoring endpoints
- [ ] Configure Cloud Logging structured logging
- [ ] Set up basic alerting for critical errors
- [ ] Create simple monitoring dashboard

## Phase 8: Documentation & Handoff (30 minutes)

#### **A8-1: Deployment Documentation**
- [ ] Create deployment status summary
- [ ] Document all URLs and endpoints
- [ ] Create troubleshooting guide
- [ ] Document scaling and upgrade procedures

#### **A8-2: Operational Procedures**
- [ ] Create monitoring and maintenance procedures
- [ ] Document backup and recovery processes
- [ ] Create cost monitoring guidelines
- [ ] Document upgrade thresholds and procedures

## Phase 9: Production Readiness (15 minutes)

#### **H9-1: Final Verification**
- [ ] Test production MCP server with real Claude Desktop integration
- [ ] Verify staging → production promotion workflow
- [ ] Confirm monitoring and alerting work
- [ ] Document final URLs and access information

#### **A9-1: Production Checklist**
- [ ] Verify all security configurations
- [ ] Confirm backup procedures are active
- [ ] Validate monitoring coverage
- [ ] Complete deployment documentation

## Success Criteria

### **Deployment Success**
- [ ] Staging MCP server accessible and functional
- [ ] Production MCP server accessible and functional
- [ ] Async podcast generation working end-to-end
- [ ] Audio files properly stored in Cloud Storage
- [ ] SQLite database persistence working correctly
- [ ] Cost monitoring active and under budget targets

### **Operational Success**
- [ ] Monitoring dashboard accessible
- [ ] Automated deployments working
- [ ] Capacity monitoring and alerting functional
- [ ] Documentation complete and accessible
- [ ] Rollback procedures tested and documented

### **Performance Targets**
- [ ] Podcast generation completes within X minutes
- [ ] System supports max 4 concurrent generations
- [ ] Monthly costs under $25 (staging + production with Secret Manager)
- [ ] 99%+ uptime for MCP servers

---

## Emergency Contacts & Resources

### **If Things Go Wrong**
- **Database Issues**: Check SQLite file integrity
- **Deployment Failures**: Check Cloud Build logs
- **MCP Server Issues**: Check Cloud Run logs
- **Cost Overruns**: Check GCP Billing dashboard

### **Key Commands for Troubleshooting**
```bash
# Check service status
gcloud run services list

# View logs
gcloud logs tail --service=mysaloncast-mcp-staging   # for staging
gcloud logs tail --service=mysaloncast-mcp-production  # for production

# Check capacity metrics
curl https://YOUR-SERVICE-URL/system/capacity
```

## Post-Deployment Next Steps

### **Immediate (Week 1)**
- [ ] Set up Claude Desktop MCP integration
- [ ] Test with real podcast generation workloads
- [ ] Monitor costs and performance
- [ ] Fine-tune scaling parameters
