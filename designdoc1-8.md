# MySalonCast MCP Integration Design Document

## Task 1.8: Model Context Protocol Server and API Implementation

**Version:** 1.1  
**Date:** January 2025  
**Authors:** Product & Engineering Team  
**Status:** Design Phase

---

## 1. Executive Summary

This document outlines the design and implementation strategy for exposing MySalonCast's podcast generation capabilities through the Model Context Protocol (MCP), enabling seamless integration with AI assistants like Claude Desktop. The approach leverages FastMCP's capabilities to create a unified system serving both traditional REST API clients and MCP-enabled AI tools, with MCP tools and resources providing a superset of functionality beyond the core API.

**Key Objectives:**
- Enable Claude Desktop users to generate podcasts through natural conversation
- Provide rich, interactive access to intermediate outputs (persona profiles, outlines, transcripts)
- Support real-time status monitoring for long-running podcast generation
- Build foundation for advanced persona interaction features

---

## 2. Technical Architecture Overview

### 2.1 Unified FastAPI + MCP Approach (Revised)

**Strategy:** Unified approach with MCP server capabilities as a **superset** of REST API endpoints.

**Two Implementation Paths:**

1. **Core API Endpoints** → Auto-converted to MCP using `FastMCP.from_fastapi()`
2. **MCP-Specific Features** → Directly implemented using FastMCP decorators

```python
from fastmcp import FastMCP
from app.main import app  # Existing FastAPI application

# Path 1: Auto-generate MCP server from FastAPI endpoints
mcp_server = FastMCP.from_fastapi(
    app=app,
    name="MySalonCast MCP Server",
    route_maps=[
        RouteMap(methods=["POST"], pattern=r".*/generate.*", mcp_type=MCPType.TOOL),
        RouteMap(methods=["GET"], pattern=r".*/status.*", mcp_type=MCPType.RESOURCE),
    ]
)

# Path 2: Add MCP-specific tools/resources directly
@mcp_server.resource("persona://{podcast_id}/{person_id}/profile")
async def get_persona_profile(podcast_id: str, person_id: str) -> PersonaResearch:
    """Direct MCP resource - no REST API equivalent"""
    
@mcp_server.tool()
async def subscribe_to_podcast_updates(podcast_id: str) -> dict:
    """Direct MCP tool - optimized for AI interaction"""
```
