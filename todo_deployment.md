# MySalonCast Deployment Todo List

**Target**: Deploy MCP server with async podcast generation to GCP staging and production environments.
**Note**: H denotes human, A denotes AI. **SQLite-based with Terraform + Secret Manager for production best practices.**

## Phase 1: Infrastructure & Configuration (1 hour)

#### **H1-1: GCP Project Setup**
- [x] Verify GCP project `my-salon-cast` exists and billing is enabled
- [x] Ensure you have Owner or Editor role on the project
- [x] Note your GCP project number (will be needed later)

#### **H1-2: API Keys Preparation**
- [x] Locate your Gemini API key
- [x] Locate your Google Cloud TTS API key  
- [x] Have both keys ready for Secret Manager storage

#### **A1-1: Update Terraform Configuration**
- [x] Modify `terraform/main.tf` for dual-environment setup (staging + production)
- [x] Add Cloud Storage buckets for staging/production (audio files + SQLite backups)
- [x] Add Secret Manager resources for API keys (shared across environments)
- [x] Configure Cloud Run services for MCP server (staging + production)
- [x] Set region to `us-west1`
- [x] Configure staging with lower resource limits (0.5GB RAM, 1 max instance)

#### **A1-2: SQLite Database Configuration** 
- [x] Update `app/database.py` to use SQLite with Cloud Storage backup
- [x] Add SQLite file backup/restore functionality to/from Cloud Storage
- [x] Configure startup logic to download latest SQLite file from GCS
- [x] Add periodic backup of SQLite to Cloud Storage (daily for cost optimization)
- [x] Keep existing SQLModel models unchanged

#### **A1-3: Environment Configuration**
- [x] Create `.env.staging` and `.env.production` templates
- [x] Update `app/main.py` to handle Cloud Run environment variables
- [x] Configure SQLite file paths for Cloud Run filesystem
- [x] Add Secret Manager integration for API key retrieval
- [x] Add environment detection logic (staging vs production)

## Phase 2: Storage & File Handling ✅ COMPLETED (1 hour)

#### **A2-1: Cloud Storage Integration** ✅ COMPLETED
- [x] **Enhanced `app/storage.py`** - Added `CloudStorageManager` class with async methods
  - `upload_audio_file_async()` - Uploads audio files to GCS with proper content types
  - `upload_audio_segment_async()` - Handles individual dialogue segments
  - `upload_podcast_episode_async()` - Comprehensive episode asset upload
  - Environment-aware fallback (local storage in dev, cloud in staging/prod)
  - Public URL generation for cloud-hosted audio files
- [x] **Environment detection** - Integrated with existing config system
  - Local environment: Uses local filesystem with warnings
  - Cloud environments: Activates GCS upload with bucket management
- [x] **Audio file upload** - Implemented in podcast workflow
  - Individual segments uploaded immediately after TTS generation
  - Final stitched audio uploaded before episode creation
  - Cloud URLs replace local paths in PodcastEpisode model
- [x] **File cleanup policies** - Built into existing StorageManager
- [x] **Updated `app/podcast_workflow.py`** - Integrated cloud storage seamlessly
  - Added CloudStorageManager initialization in PodcastGeneratorService
  - Cloud upload logic in `_generate_podcast_internal()` method
  - Progress logging for upload operations
  - Error handling with graceful fallback

#### **A2-2: File Path Management** ✅ COMPLETED  
- [x] **Updated `PodcastEpisode` model** - Now stores cloud URLs when available
  - `audio_filepath` contains GCS public URL in cloud environments
  - `dialogue_turn_audio_paths` updated with cloud URLs for individual segments
  - Backward compatibility maintained for local development
- [x] **Audio serving logic** - Cloud storage URLs served directly
  - Public URLs eliminate need for proxy serving in cloud environments
  - Local fallback maintains development workflow
- [x] **Signed URL capability** - Foundation laid in CloudStorageManager
  - Private audio access can be implemented when needed
  - Currently using public URLs for simplicity

**🧪 TESTING COMPLETED:**
- ✅ Service initialization with cloud storage integration
- ✅ Import compatibility and module loading
- ✅ MCP server operation with new storage backend
- ✅ Environment detection and fallback behavior
- ✅ Local development workflow preservation

**📊 TECHNICAL ACHIEVEMENTS:**
- Zero breaking changes to existing MCP functionality
- Seamless local/cloud environment switching
- Async-compatible storage operations
- Comprehensive error handling and logging
- Budget-conscious design (public URLs, efficient uploads)

## Phase 2.3: Text File Cloud Storage Integration (4-6 hours)

**🎯 OBJECTIVE:**
Extend cloud storage integration to handle text files (transcripts, outlines, persona research) for cloud deployment compatibility.

**📋 PROBLEM SOLVED:**
Current text file handling saves to temporary local files during generation, then accesses via MCP resources. This breaks in Cloud Run where container restarts cause temp files to disappear.

#### **A2-3: Text File Cloud Storage Integration**
- [x] **Extend CloudStorageManager** - Add text file upload methods
  - `upload_text_file_async()` - Generic text content upload to GCS
  - `upload_outline_async()` - Podcast outline JSON upload
  - `upload_persona_research_async()` - Individual persona research upload
  - Environment-aware behavior (local files in dev, GCS URLs in cloud)
  - Proper content-type handling for JSON/text files

- [x] **Update Podcast Workflow** - Integrate text file uploads
  - Upload outline JSON to GCS after generation
  - Upload persona research files to GCS after completion
  - Replace local file paths with GCS URLs in PodcastEpisode model
  - Maintain local fallback for development environment
  - Add progress logging for text file uploads

- [x] **Modify MCP Resources** - Handle cloud URLs vs local file paths
  - Update `podcast://{task_id}/outline` resource to download from GCS URLs
  - Update `research://{task_id}/{person_id}` resource for cloud access
  - Add caching mechanism for frequently accessed text files
  - Implement graceful fallback when files are unavailable
  - Maintain backward compatibility with local file paths

- [x] **Update PodcastEpisode Model** - Store cloud URLs for text files
  - Modify `llm_podcast_outline_path` to store GCS URLs when available
  - Modify `llm_persona_research_paths` to store GCS URLs for each research file
  - Add migration logic for existing local file path entries
  - Maintain field compatibility for local development

**🧪 TESTING PLAN:**
- [x] Test text file upload in cloud vs local environments
- [x] Verify MCP resources work with both local paths and GCS URLs
- [x] Test container restart scenarios (files persist via GCS)
- [x] Validate local development workflow remains unchanged
- [x] Performance testing for text file access latency

**📊 IMPLEMENTATION COMPLETED:**
- ✅ **4 new CloudStorageManager methods** for text file handling
- ✅ **Text file upload integration** in podcast workflow
- ✅ **Enhanced MCP resources** with cloud URL support and caching
- ✅ **PodcastEpisode model enhancements** with helper methods
- ✅ **Environment-aware behavior** (local fallback preserved)
- ✅ **Comprehensive error handling** with detailed logging

**📊 EXPECTED BENEFITS:**
- ✅ Cloud deployment compatibility for text file access
- ✅ Architectural consistency with audio file storage pattern  
- ✅ Natural backup/archival solution for generated content
- ✅ Stateless application design for horizontal scaling

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
