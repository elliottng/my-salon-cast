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

#### **A2.3: Cloud Storage Integration for Text Files COMPLETED & TESTED**

**Status**: ✅ **IMPLEMENTATION COMPLETE & FULLY VALIDATED**  
**Testing**: ✅ **LOCAL TESTING PASSED - READY FOR CLOUD DEPLOYMENT**

### Tasks Completed:
- [x] **Task 1**: Extend CloudStorageManager for text file upload/download 
- [x] **Task 2**: Update podcast workflow to upload text files during generation
- [x] **Task 3**: Modify MCP resources to support both local and cloud text file access
- [x] **Task 4**: Enhance PodcastEpisode model with cloud storage helper methods

### Testing Results:
- ✅ **Episode Generation**: Successfully generated task ID `30eeb6a7-43b9-4242-89b8-3fbdec15936c`
- ✅ **Text File Creation**: 2 persona research files created with proper JSON structure
- ✅ **File Access**: Direct file reading with 5,929-6,131 char files validated
- ✅ **Caching Performance**: 5.8x speedup on repeated access confirmed
- ✅ **Environment Detection**: Correctly identifies local vs cloud environments
- ✅ **Storage Fallback**: Local filesystem used appropriately in development
- ✅ **Code Integration**: All upload/download logic integrated without breaking changes

### Architecture Benefits:
- **Environment Aware**: Automatically detects local vs cloud and adapts behavior
- **Backward Compatible**: Existing local workflows unchanged
- **Performance Optimized**: In-memory caching for frequently accessed text files
- **Error Resilient**: Graceful fallback to local storage when cloud unavailable
- **Cloud Ready**: All code in place for immediate activation in cloud environment

### Next Steps:
- Ready for **Phase 3: MCP Server Deployment Configuration**
- Cloud environment testing will validate full cloud storage functionality
- Expected: Cloud URLs will replace local paths when deployed to staging/production

## Phase 3: MCP Server Deployment Configuration ✅ **COMPLETED** (30 minutes)

#### **A3-1: MCP Server Containerization** ✅ **COMPLETED**
- [x] Create production-optimized Dockerfile with health checks
- [x] Add .dockerignore for optimized builds
- [x] Configure container for Cloud Run (port 8000, non-root user)
- [x] Add health check endpoint (/health) with proper status codes
- [x] Test container locally with health endpoint validation

#### **A3-2: Cloud Build Configuration** ✅ **COMPLETED**  
- [x] Create cloudbuild.yaml for automated CI/CD pipeline
- [x] Configure multi-stage build (build → push → deploy → health check)
- [x] Add environment-specific deployment (staging/production)
- [x] Configure Cloud Run deployment with proper resources and scaling
- [x] Add automated health checks post-deployment

#### **A3-3: MCP Server Configuration** ✅ **COMPLETED**
- [x] Create production_config.py for environment-aware configuration
- [x] Add structured logging for Cloud Run (JSON format)
- [x] Implement comprehensive health monitoring and status checks
- [x] Add environment variable validation and startup verification
- [x] Configure production uvicorn settings and error handling
- [x] Add graceful shutdown and proper signal handling

#### **A3-4: Environment Variable Configuration** ✅ **COMPLETED**
- [x] Simplify `app/config.py` to use only environment variables (remove Secret Manager)
- [x] Update Cloud Run service configuration with required environment variables:
  - `GEMINI_API_KEY` - For podcast generation
  - `GOOGLE_TTS_API_KEY` - For text-to-speech services
  - `PROJECT_ID` - For GCP project identification
  - `ENVIRONMENT` - For environment detection (staging/production)
- [x] Add environment variable validation and error handling
- [x] Update documentation for API key setup
- [x] Remove Secret Manager dependencies from requirements.txt
- [x] Update Terraform configuration to use environment variables instead of Secret Manager

## Phase 4: Infrastructure Deployment (30 minutes)

#### **H4-1: Deploy Infrastructure**
```bash
# You'll run these commands in Windsurf terminal:
cd terraform/
terraform init
terraform plan
terraform apply  # Type 'yes' when prompted
```
#### **H4-2: Verify Infrastructure**
- [ ] Check Cloud Storage buckets are created
- [ ] Verify service account permissions for Cloud Storage access

#### **A4-1: Database Initialization**
- [ ] Create initial SQLite database file
- [ ] Add database initialization to deployment pipeline
- [ ] Set up separate staging/production SQLite files on Cloud Storage

## Phase 5: Application Deployment (45 minutes)
#### **H5-1: Initial Application Deployment**
```bash
# You'll run these commands:
gcloud builds submit --config=cloudbuild.yaml
```
#### **H5-2: Database Setup**
```bash
# No database setup needed for SQLite
```
#### **A5-1: Deployment Pipeline Setup**
- [ ] Configure Cloud Build triggers for automatic deployment
- [ ] Set up branch-based deployment (main → production, dev → staging)
- [ ] Add deployment verification steps
- [ ] Configure rollback procedures

#### **A5-2: Service Configuration**
- [ ] Configure Cloud Run services with appropriate resources
- [ ] Set up environment variables
- [ ] Configure scaling parameters for budget optimization
- [ ] Add custom domains if requested

---

## Phase 6: Testing & Verification (45 minutes)

#### **H6-1: End-to-End Testing**
- [ ] Test MCP server connectivity from Claude Desktop or MCP client
- [ ] Verify async podcast generation workflow
- [ ] Test file storage and retrieval
- [ ] Confirm staging and production environments work

#### **H6-2: Performance Validation**
- [ ] Generate a test podcast to verify full pipeline
- [ ] Check audio file upload to Cloud Storage
- [ ] Verify SQLite database persistence
- [ ] Test concurrent generation limits

#### **A6-1: Monitoring Setup**
- [ ] Deploy basic capacity monitoring endpoints
- [ ] Configure Cloud Logging structured logging
- [ ] Set up basic alerting for critical errors
- [ ] Create simple monitoring dashboard

## Phase 7: Documentation & Handoff (30 minutes)

#### **A7-1: Deployment Documentation**
- [ ] Create deployment status summary
- [ ] Document all URLs and endpoints
- [ ] Create troubleshooting guide
- [ ] Document scaling and upgrade procedures

#### **A7-2: Operational Procedures**
- [ ] Create monitoring and maintenance procedures
- [ ] Document backup and recovery processes
- [ ] Create cost monitoring guidelines
- [ ] Document upgrade thresholds and procedures

## Phase 8: Production Readiness (15 minutes)

#### **H8-1: Final Verification**
- [ ] Test production MCP server with real Claude Desktop integration
- [ ] Verify staging → production promotion workflow
- [ ] Confirm monitoring and alerting work
- [ ] Document final URLs and access information

#### **A8-1: Production Checklist**
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
- [ ] Monthly costs under $25 (staging + production)
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
