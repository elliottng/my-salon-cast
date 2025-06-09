# MySalonCast OpenAPI Quick Reference

## 🚀 Access Points

| Type | URL | Description |
|------|-----|-------------|
| **Swagger UI** | `http://localhost:8002/docs` | Interactive API testing interface |
| **ReDoc** | `http://localhost:8002/redoc` | Beautiful API documentation |
| **Raw JSON Schema** | `http://localhost:8002/openapi.json` | Machine-readable OpenAPI 3.1.0 schema |

## 📋 API Endpoints

### 1. **PDF Text Extraction**
```
POST /process/pdf/
```
- **Tag**: `content`
- **Purpose**: Extract text from PDF documents
- **Input**: Multipart form with PDF file
- **Output**: Extracted text snippet and metadata
- **Use Case**: Prepare content for podcast generation

### 2. **Async Podcast Generation**
```
POST /generate/podcast_async/
```
- **Tag**: `generation`
- **Purpose**: Start AI-powered podcast creation
- **Input**: JSON with content sources and preferences
- **Output**: Task ID for tracking progress
- **Use Case**: Begin podcast generation workflow

### 3. **Audio Streaming**
```
GET /podcast/{podcast_id}/audio
```
- **Tag**: `playback`
- **Purpose**: Stream completed podcast audio
- **Input**: Podcast ID from generation process
- **Output**: HTML page with audio player
- **Use Case**: Listen to or download generated podcasts

### 4. **Status Tracking**
```
GET /status/{task_id}
```
- **Tag**: `status`
- **Purpose**: Monitor podcast generation progress
- **Input**: Task ID from generation request
- **Output**: Detailed status information and results
- **Use Case**: Track completion and access generated artifacts

## 🛠️ Export OpenAPI Schema

### Basic Export
```bash
# Export to openapi.json (default)
uv run python scripts/export_openapi.py
```

### Custom Export Options
```bash
# Custom output file
uv run python scripts/export_openapi.py --output docs/my_schema.json

# Different server URL
uv run python scripts/export_openapi.py --url https://api.mysaloncast.com

# Help and options
uv run python scripts/export_openapi.py --help
```

## 🔧 Using the Schema

### Client SDK Generation
```bash
# Generate Python client
openapi-generator generate -i openapi.json -g python -o clients/python

# Generate JavaScript client
openapi-generator generate -i openapi.json -g javascript -o clients/js

# Generate Java client
openapi-generator generate -i openapi.json -g java -o clients/java
```

### API Testing Tools
```bash
# Test with Newman (Postman CLI)
newman run <(curl -s http://localhost:8002/openapi.json)

# Import into Insomnia/Postman
# File -> Import -> openapi.json
```

### Documentation Generation
```bash
# Generate static docs with Redoc CLI
redoc-cli build openapi.json --output docs/static-api-docs.html

# Generate with Swagger Codegen
swagger-codegen generate -i openapi.json -l html2 -o docs/swagger-docs
```

## 📊 Schema Information

- **OpenAPI Version**: 3.1.0
- **API Version**: 1.0.0
- **Total Endpoints**: 4
- **Response Models**: PodcastStatus, PodcastRequest
- **Authentication**: None (development), Bearer token (production)
- **Content Types**: JSON, multipart/form-data, HTML

## 🎯 Integration Examples

### cURL Commands
```bash
# Extract PDF text
curl -X POST "http://localhost:8002/process/pdf/" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "pdf_file=@document.pdf"

# Start podcast generation
curl -X POST "http://localhost:8002/generate/podcast_async/" \
     -H "accept: application/json" \
     -H "Content-Type: application/json" \
     -d '{"content_sources": ["https://example.com"], "custom_prompt": "Create a podcast about AI"}'

# Check status
curl -X GET "http://localhost:8002/status/task-123" \
     -H "accept: application/json"
```

### Python Client Example
```python
import requests

# Start podcast generation
response = requests.post(
    "http://localhost:8002/generate/podcast_async/",
    json={
        "content_sources": ["https://example.com"],
        "custom_prompt": "Create an engaging podcast about AI trends"
    }
)
task_id = response.json()["task_id"]

# Monitor progress
status_response = requests.get(f"http://localhost:8002/status/{task_id}")
print(status_response.json())
```

## 🔄 Typical Workflow

1. **Extract Content** (if using PDFs)
   ```
   POST /process/pdf/ → Get extracted text
   ```

2. **Start Generation**
   ```
   POST /generate/podcast_async/ → Get task_id
   ```

3. **Monitor Progress**
   ```
   GET /status/{task_id} → Check completion
   ```

4. **Access Results**
   ```
   GET /podcast/{podcast_id}/audio → Stream/download
   ```

## 📚 Additional Resources

- [OpenAPI 3.1.0 Specification](https://spec.openapis.org/oas/v3.1.0)
- [FastAPI OpenAPI Docs](https://fastapi.tiangolo.com/tutorial/metadata/)
- [OpenAPI Generator](https://openapi-generator.tech/)
- [Swagger Tools](https://swagger.io/tools/)
