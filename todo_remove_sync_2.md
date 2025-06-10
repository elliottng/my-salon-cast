# Remove Synchronous Podcast Generation - Todo List

## Overview
Remove all synchronous podcast generation support, making the system purely asynchronous. Eliminate `_generate_podcast_internal()` by integrating its logic directly into `generate_podcast_async()`.

## Phase 0: Pre-Refactoring Safety Measures

### Safety and Documentation

  - [ ] Ensure all current changes are committed first
  
- [ ] **Create integration test baseline**
  - [ ] Write a test that captures current async behavior: `tests/test_async_generation_baseline.py`
  - [ ] Test should verify: task_id generation, status updates, background execution, webhook notifications
  - [ ] Run and ensure it passes before making any changes

## Phase 1: Core Logic Refactoring (Fix Circular Dependency)

### File: `app/podcast_workflow.py`

- [ ] **Extract core processing logic into new method**
  - [ ] Create `_execute_podcast_generation_core(self, task_id: str, request_data: PodcastRequest) -> None`
  - [ ] Move all actual processing logic from `_generate_podcast_internal()` to this new method
  - [ ] Include: content extraction, LLM analysis, persona research, outline generation, dialogue generation, TTS, audio stitching
  - [ ] This method should do the actual work without any task submission logic
  - [ ] Remove all `async_mode` conditional logic - just do the processing
  - [ ] **Add cancellation check points**: Check `task_runner.is_task_cancelled(task_id)` between major steps
  - [ ] **Preserve all logging**: Ensure all existing log statements are maintained

- [ ] **Integrate task submission logic into `generate_podcast_async()`**
  - [ ] Move task creation and submission logic from `_generate_podcast_internal()` into `generate_podcast_async()`
  - [ ] Include: task_id generation, initial status creation, capacity checking, task_runner submission
  - [ ] Method should directly handle all task submission responsibilities
  - [ ] Remove the call to `_generate_podcast_internal()` entirely

- [ ] **Update `_run_podcast_generation_async()` wrapper method**
  - [ ] Change the call from `self._generate_podcast_internal(request_data, async_mode=False, background_task_id=task_id)`
  - [ ] To: `await self._execute_podcast_generation_core(task_id, request_data)`
  - [ ] Keep all existing error handling, webhook notifications, and status management

## Phase 2: Remove Synchronous Methods and Internal Method

### File: `app/podcast_workflow.py`

- [ ] **Delete `generate_podcast_from_source()` method entirely**
  - [ ] Remove the complete method definition (lines ~45-55 approximately)
  - [ ] Remove all associated docstrings and comments

- [ ] **Delete `_generate_podcast_internal()` method entirely**
  - [ ] Remove the complete method definition (this eliminates the circular dependency)
  - [ ] Remove all associated docstrings and comments
  - [ ] This method becomes unnecessary since its logic is integrated into `generate_podcast_async()`

- [ ] **Delete development test function**
  - [ ] Remove `main_workflow_test()` function entirely
  - [ ] Remove the `if __name__ == "__main__":` block at the end of the file
  - [ ] Remove associated imports if they become unused

## Phase 3: Implement New `generate_podcast_async()` Logic

### File: `app/podcast_workflow.py`

- [ ] **Implement complete `generate_podcast_async()` method**
  - [ ] Add task_id generation: `task_id = str(uuid.uuid4())`
  - [ ] Add initial status creation: `status_manager.create_status(task_id, request_data.dict())`
  - [ ] Add initial status update: `status_manager.update_status(task_id, "preprocessing_sources", "Validating request...", 5.0)`
  - [ ] Add capacity checking: `if not task_runner.can_accept_new_task():`
  - [ ] Add error handling for capacity issues with proper status updates
  - [ ] Add task submission: `await task_runner.submit_async_task(task_id, self._run_podcast_generation_async, task_id, request_data)`
  - [ ] Add error handling for submission failures with proper status updates
  - [ ] Return task_id on success
  - [ ] Update docstring to reflect it's the single entry point for podcast generation

- [ ] **Clean up any remaining references**
  - [ ] Search for any calls to `_generate_podcast_internal()` and remove them
  - [ ] Verify no other code depends on the removed internal method

## Phase 4: Update API Layer (if needed)

### File: `app/main.py`

- [ ] **Review REST API endpoint behavior**
  - [ ] Verify `/generate/podcast_async/` endpoint works with new async-only behavior
  - [ ] Update response messages if needed to clarify all generation is now async
  - [ ] Ensure error handling works with new async-only pattern

- [ ] **Update endpoint documentation**
  - [ ] Update OpenAPI/FastAPI docstrings to reflect async-only behavior
  - [ ] Remove any references to synchronous generation options

## Phase 5: Clean Up and Validation

### File: `app/podcast_workflow.py`

- [ ] **Remove unused imports**
  - [ ] Check if any imports are no longer needed after removing sync code
  - [ ] Clean up any unused variables or constants

- [ ] **Update class docstrings and comments**
  - [ ] Update `PodcastGeneratorService` class docstring
  - [ ] Remove any comments referencing synchronous generation
  - [ ] Update method docstrings to reflect new async-only behavior

### Testing and Validation

- [ ] **Run baseline integration test**
  - [ ] Execute: `pytest tests/test_async_generation_baseline.py -v`
  - [ ] Ensure it still passes after refactoring
  - [ ] Compare logs before/after to ensure no behavioral changes

- [ ] **Test cancellation behavior**
  - [ ] Start a long-running generation
  - [ ] Cancel it mid-process
  - [ ] Verify cancellation is handled gracefully
  - [ ] Check that status is updated to "cancelled"

- [ ] **Test concurrent generation**
  - [ ] Submit multiple podcast generation requests
  - [ ] Verify capacity checking still works
  - [ ] Ensure no race conditions in new structure

- [ ] **Test error scenarios**
  - [ ] Test with invalid source content
  - [ ] Test with LLM service failure
  - [ ] Test with TTS service failure
  - [ ] Verify all errors are properly logged and status updated

- [ ] **Performance validation**
  - [ ] Measure generation time before/after refactoring
  - [ ] Should be same or slightly better (no more async_mode checks)
  - [ ] Check memory usage patterns remain consistent

## Phase 6: Monitoring and Observability Updates

### Logging and Metrics

- [ ] **Update log messages**
  - [ ] Replace references to "sync/async mode" with just "async generation"
  - [ ] Add clear log entries for new method boundaries
  - [ ] Log entry when entering `_execute_podcast_generation_core()`
  - [ ] Log exit with success/failure status

- [ ] **Add performance metrics**
  - [ ] Add timing logs for total generation time
  - [ ] Log time spent in each major phase (analysis, research, outline, dialogue, TTS)
  - [ ] Consider adding metrics collection if available

### Error Tracking

- [ ] **Enhance error categorization**
  - [ ] Distinguish between task submission errors vs processing errors
  - [ ] Add error codes for different failure types
  - [ ] Ensure stack traces are preserved for debugging

## Phase 7: Documentation and Communication

### Code Documentation

- [ ] **Update method docstrings**
  - [ ] `generate_podcast_async()`: Document as the single entry point
  - [ ] `_execute_podcast_generation_core()`: Document as internal processing method
  - [ ] `_run_podcast_generation_async()`: Document as task runner wrapper

- [ ] **Update API documentation**
  - [ ] Remove any references to synchronous generation
  - [ ] Update OpenAPI schema if needed
  - [ ] Update README if it mentions sync generation

### Team Communication

- [ ] **Create migration notes**
  - [ ] Document what was changed and why
  - [ ] List any behavioral differences (should be none)
  - [ ] Note performance improvements if any

## Success Criteria

- [ ] **Single async entry point**: Only `generate_podcast_async()` method exists
- [ ] **No circular dependencies**: Task submission in `generate_podcast_async()`, execution in `_execute_podcast_generation_core()`
- [ ] **Clean method structure**: 
  - [ ] `generate_podcast_async()` handles task submission only
  - [ ] `_execute_podcast_generation_core()` handles processing only  
  - [ ] `_run_podcast_generation_async()` wraps execution for task runner
- [ ] **Consistent behavior**: All generation goes through background task system
- [ ] **Working status tracking**: Status manager correctly tracks progress through new flow
- [ ] **Error handling**: All error scenarios properly handled and logged
- [ ] **No unused code**: All sync-related code and `_generate_podcast_internal()` removed

## Validation Commands

```bash
# 1. Run all existing tests
pytest tests/ -v

# 2. Test async generation via API
curl -X POST http://localhost:8000/generate/podcast_async/ \
  -H "Content-Type: application/json" \
  -d '{"source_content": "Test content", "source_type": "document", "user_provided_title": "Test"}'

# 3. Check task status
curl http://localhost:8000/status/{task_id}

# 4. Verify no references to removed methods
grep -r "generate_podcast_from_source" app/
grep -r "_generate_podcast_internal" app/
grep -r "async_mode" app/

# 5. Check for any broken imports
python -m py_compile app/podcast_workflow.py
```

## Rollback Plan

If issues are discovered after deployment:

1. **Immediate rollback**
   - [ ] Git revert the merge commit
   - [ ] Deploy previous version
   - [ ] Notify team of rollback

2. **Investigation**
   - [ ] Review logs for error patterns
   - [ ] Check if issue is in refactoring or coincidental
   - [ ] Create targeted fix if minor issue

3. **Re-attempt**
   - [ ] Fix identified issues
   - [ ] Add test coverage for discovered edge case
   - [ ] Re-deploy with extra monitoring