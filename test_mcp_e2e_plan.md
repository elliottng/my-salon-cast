# MySalonCast MCP End-to-End Testing Plan

## Overview
This document outlines the comprehensive testing strategy for the FastMCP async tools and resources implementation.

## Testing Approach

### 1. MCP Client Setup
We'll create a Python-based MCP client using the `mcp` package to interact with our server.

#### Client Requirements:
- Connect to the MCP server via SSE transport
- Execute tools and retrieve results
- Access resources
- Handle async operations properly

### 2. Test Categories

#### A. Tool Testing

**Test 1: Basic Connectivity**
- Connect to MCP server
- Call `hello` tool
- Verify response

**Test 2: Async Generation with Individual Parameters**
- Call `generate_podcast_async` with valid URLs
- Verify task_id returned
- Check initial status is "queued"
- Poll status until completion
- Verify all status transitions

**Test 3: Task Status Monitoring**
- Submit multiple tasks
- Query status at different stages
- Verify progress updates
- Check final results

**Test 5: Error Handling**
- Invalid URLs
- Missing required parameters
- Non-existent task IDs
- Conflicting parameters (both URL and PDF)

#### B. Resource Testing

**Test 6: Transcript Resource**
- Complete a podcast generation
- Access `podcast://{task_id}/transcript`
- Verify transcript content

**Test 7: Audio Resource**
- Access `podcast://{task_id}/audio`
- Verify file path and metadata
- Check file existence

**Test 8: Metadata Resource**
- Access `podcast://{task_id}/metadata`
- Verify all fields populated
- Check timestamps

**Test 9: Configuration Resource**
- Access `config://supported_formats`
- Verify structure and content

**Test 10: Resource Error Handling**
- Access resources for non-existent tasks
- Access resources for incomplete tasks
- Verify appropriate errors

#### C. Integration Testing

**Test 11: Full Workflow**
- Submit async task
- Monitor progress
- Access all resources after completion
- Verify consistency

**Test 12: Concurrent Tasks**
- Submit multiple tasks simultaneously
- Verify queue management
- Check resource isolation

**Test 13: Long-Running Tasks**
- Submit task with multiple sources
- Verify intermediate status updates
- Test timeout handling

### 3. Test Data

#### Valid Test Cases:
```python
test_cases = [
    {
        "name": "Single URL",
        "params": {
            "source_urls": ["https://example.com/article"],
            "podcast_length": "3-5 minutes"
        }
    },
    {
        "name": "Multiple URLs",
        "params": {
            "source_urls": ["https://example1.com", "https://example2.com"],
            "prominent_persons": ["John Doe"],
            "custom_prompt": "Focus on technical aspects"
        }
    },
    {
        "name": "Custom Configuration",
        "params": {
            "source_urls": ["https://example.com"],
            "podcast_name": "Test Podcast",
            "podcast_tagline": "Testing MCP Integration",
            "output_language": "es",
            "dialogue_style": "formal"
        }
    }
]
```

#### Invalid Test Cases:
```python
error_cases = [
    {
        "name": "No Sources",
        "params": {},
        "expected_error": "Must provide either source_urls or source_pdf_path"
    },
    {
        "name": "Both URL and PDF",
        "params": {
            "source_urls": ["https://example.com"],
            "source_pdf_path": "/path/to/file.pdf"
        },
        "expected_error": "Cannot provide both"
    },
    {
        "name": "Invalid Language",
        "params": {
            "source_urls": ["https://example.com"],
            "output_language": "xyz"
        },
        "expected_error": "Unsupported language"
    }
]
```

### 4. Test Implementation Structure

```
tests/
├── mcp/
│   ├── __init__.py
│   ├── client.py           # MCP client wrapper
│   ├── test_tools.py       # Tool testing
│   ├── test_resources.py   # Resource testing
│   ├── test_integration.py # Full workflow tests
│   └── fixtures.py         # Test data and utilities
└── run_mcp_tests.py        # Test runner
```

### 5. Performance Benchmarks

- Tool response time < 500ms for task submission
- Status query response time < 100ms
- Resource access time < 200ms
- Full podcast generation (3-5 min) < 2 minutes

### 6. Documentation Requirements

- Example client code
- Common integration patterns
- Troubleshooting guide
- API reference with all parameters

## Next Steps

1. Install MCP client package
2. Create test client wrapper
3. Implement test cases progressively
4. Document findings and issues
5. Create CI/CD integration
