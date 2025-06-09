# Remove Sync Wrapper, Non-Pydantic AI Path & Separate REST API
## Pre-Implementation Checklist



## Phase 1: Remove Non-Pydantic AI Path ⭐ (Start Here - Lowest Risk)
### Files to Modify

- [ ] `app/llm_service.py`
- [ ] `app/config.py`

### Tasks

- [ ] Delete `_legacy_generate_text_async` method (lines ~70-130 in llm_service.py)
- [ ] Simplify `generate_text_async` - remove conditional logic, always use Pydantic AI
- [ ] Remove legacy paths in `analyze_source_text_async` (lines ~220-280)
- [ ] Remove legacy paths in `research_persona_async` (lines ~350-420)
- [ ] Remove `use_pydantic_ai` from constructor
- [ ] Remove `use_pydantic_ai` flag from `app/config.py`

### Validation

- [ ] Run MCP tests: `uv run pytest tests/mcp/ -v`
- [ ] Verify no functional changes to MCP server behavior
- [ ] Check that all LLM operations use Pydantic AI

### Git Checkpoint

- [ ] Commit Phase 1: "Remove non-Pydantic AI legacy paths"
- [ ] Tag: `phase1-non-pydantic-removed`

## Phase 2: Remove unneeded REST API functionality⭐

### Overview
Remove 11 redundant REST API endpoints from app/main.py to create a minimal API surface optimized for OpenAI function calling.
**Goal**: Reduce from 15 endpoints to 4 essential endpoints

### Implementation Tasks

#### Remove These 11 Endpoints
- [x] Delete `process_url_endpoint()` function
- [x] Delete `process_youtube_endpoint()` function  
- [x] Delete `generate_podcast_elements_endpoint()` function
- [x] Delete `get_segment_audio()` function
- [x] Delete `delete_task_status()` function
- [x] Delete `cancel_task()` function
- [x] Delete `get_queue_status()` function
- [x] Delete `list_task_statuses()` function
- [x] Delete `root()` function
- [x] Delete `get_health()` function
- [x] Remove all corresponding `@app.post()`, `@app.get()`, `@app.delete()` decorators

#### Clean Up Imports
- [x] Remove unused imports after endpoint deletion
- [x] Remove unused models (`StatusListResponse` if not used elsewhere)

### Validation
- [x] Syntax check passed
- [ ] Quick MCP server test (optional)
- [ ] Commit Phase 2: "Remove unneeded REST API endpoints"
- [ ] Tag: `phase2-rest-api-simplified`

## Phase 3: Remove Sync Wrapper ⚠️ (Medium Risk - Task Runner Changes)
### Files to Modify

- [ ] `app/podcast_workflow.py`
- [ ] `app/task_runner.py`

### Tasks in `app/podcast_workflow.py`

- [ ] Delete `_run_podcast_generation_sync_wrapper` method (lines ~150-170)
- [ ] Update async task submission - replace sync wrapper call with direct async call
- [ ] Verify no other sync wrapper usage

### Tasks in `app/task_runner.py`

- [ ] Add `submit_async_task` method for direct async function handling
- [ ] Test async task submission works
- [ ] Ensure cancellation still works

#### Code Changes
```python
# In podcast_workflow.py - REPLACE:
await task_runner.submit_task(
    task_id,
    self._run_podcast_generation_sync_wrapper,  # OLD
    task_id,
    request_data
)

# WITH:
await task_runner.submit_async_task(
    task_id,
    self._run_podcast_generation_async,  # NEW - direct async
    task_id,
    request_data
)
```

### Validation

- [ ] Start MCP server successfully
- [ ] Test async podcast generation: Create a test podcast via MCP
- [ ] Verify task cancellation works
- [ ] Check task status tracking works
- [ ] Monitor logs for async execution

### Git Checkpoint

- [ ] Commit Phase 3: "Remove sync wrapper, use direct async task submission"
- [ ] Tag: `phase3-sync-wrapper-removed`

## Phase 4: Clean Up Configuration 🧹
### Files to Modify

- [ ] `app/config.py`
- [ ] `.env` files
- [ ] Documentation
- [ ] Environment variable documentation

### Tasks

- [ ] Remove `use_pydantic_ai` config field
- [ ] Update environment variable docs
- [ ] Remove legacy mode references from documentation
- [ ] Update deployment instructions (single server)
- [ ] Clean up environment variables

### Git Checkpoint

- [ ] Commit Phase 4: "Clean up configuration and documentation"
- [ ] Tag: `phase4-config-cleaned`

## Phase 5: Test Cleanup 🧪
### Tasks

- [ ] Find REST API tests: `find tests/ -name "*.py" -exec grep -l "app.main" {} \;`
- [ ] Delete REST-specific tests
- [ ] Update import statements in remaining tests
- [ ] Run full test suite: `uv run pytest -v`
- [ ] Fix any broken imports or test references

#### Validation Commands
```bash
# Run all MCP tests
uv run pytest tests/mcp/ -v

# Run async workflow tests
uv run pytest tests/test_podcast_workflow.py -v

# Run full test suite
uv run pytest -v

# Check for any lingering imports
grep -r "app.main" tests/ || echo "No app.main imports found"
grep -r "_legacy_" app/ || echo "No legacy methods found"
```

### Git Checkpoint

- [ ] Commit Phase 5: "Clean up tests and remove unused imports"
- [ ] Tag: `phase5-tests-cleaned`

## Final Validation ✅
### MCP Server Functionality

- [ ] Start server: `uv run python app/mcp_server.py`
- [ ] Test MCP tools: All tools work via Claude/MCP client
- [ ] Test OAuth flow: Authentication works
- [ ] Test podcast generation: End-to-end async generation works
- [ ] Test task management: Status tracking, cancellation work

### HTTP Endpoints (via MCP server)

- [ ] Health check: `curl http://localhost:8000/health`
- [ ] OAuth discovery: `curl http://localhost:8000/.well-known/oauth-authorization-server`
- [ ] MCP root: `curl http://localhost:8000/`

### Deployment Test

- [ ] Single server deployment works
- [ ] No duplicate server infrastructure
- [ ] All environment variables valid

## Success Criteria ✅

- [ ] ✅ Single server deployment (MCP server only)
- [ ] ✅ MCP server starts without errors
- [ ] ✅ All MCP tools and resources work
- [ ] ✅ Async podcast generation completes successfully
- [ ] ✅ No regression in MCP functionality
- [ ] ✅ Significantly reduced codebase complexity
- [ ] ✅ No duplicate server infrastructure
- [ ] ✅ Simplified deployment and maintenance

## Rollback Plan 🔄
### Emergency Rollback
```bash
# Quick rollback to main
git checkout main

# Or rollback to specific phase
git checkout phase2-rest-api-removed  # Go back to working state
```

### Phase-Specific Rollbacks

- **Phase 1 Issues**: `git checkout phase1-non-pydantic-removed~1`
- **Phase 2 Issues**: `git checkout phase2-rest-api-removed~1`
- **Phase 3 Issues**: `git checkout phase3-sync-wrapper-removed~1`

## Benefits Summary 📈
### Code Reduction:

- ~500+ lines removed from `app/main.py`
- ~200+ lines removed from `app/llm_service.py`
- ~100+ lines removed from sync wrapper
- Single server instead of two

### Operational Improvements:

- Single server to deploy and monitor
- Reduced resource usage
- Simplified configuration
- No REST API maintenance

### Technical Benefits:

- Direct async flow (cleaner architecture)
- Pydantic AI only (more reliable)
- Easier debugging
- Reduced complexity

## Notes & Observations 📝
### During Implementation

- Document any unexpected dependencies found
- Note any essential functionality that needs migration
- Record performance improvements observed
- Track any issues encountered and solutions

### Post-Implementation

- Update deployment documentation
- Update developer onboarding docs
- Consider cleanup of unused imports across codebase
- Plan for dependency audit with `uv tree`

---

**Implementation Priority**: Start with Phase 1 (lowest risk), validate thoroughly, then proceed sequentially. Each phase is designed to be independently reversible.
