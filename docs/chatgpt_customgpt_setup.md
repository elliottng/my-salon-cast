# ChatGPT CustomGPT Setup Guide for MySalonCast API

## 🎯 **ChatGPT-Optimized OpenAPI Schema**

Use the **`openapi_chatgpt.json`** file specifically created for ChatGPT CustomGPT compatibility.

### **Key Fixes Applied:**

✅ **Single Production Server**: Only `https://elliottng.pagekite.me` (removed localhost)  
✅ **Short Descriptions**: All descriptions under 300 characters  
✅ **CORS Compliant**: Public HTTPS endpoint  
✅ **Clean Schema**: Minimal, focused structure  

## 🔐 **Privacy Policy Compliance**

✅ **Privacy Policy URL**: `https://elliottng.pagekite.me/privacy-policy`

### **Key Privacy Features:**
- **Data Retention**: Generated content stored for 30 days, source content processed in memory only
- **No Authentication Required**: No personal accounts or user data stored
- **HTTPS Encryption**: All data transmission encrypted
- **Limited Data Sharing**: Only with necessary AI services for processing
- **User Rights**: Access, deletion, and portability of generated content
- **Transparent Policies**: Clear explanation of data handling and processing

### **Privacy Compliance:**
- ✅ COPPA compliant (no data collection from children under 13)
- ✅ International data transfer disclosures
- ✅ Clear contact information for privacy inquiries
- ✅ Regular policy updates with notification procedures
- ✅ Comprehensive data handling documentation

## 🚀 **Step-by-Step Setup**

### **1. Get the ChatGPT-Ready Schema**
```bash
# The optimized schema is already generated
cat openapi_chatgpt.json
```

### **2. Configure CustomGPT in ChatGPT**

1. **Go to ChatGPT** → **My GPTs** → **Create a GPT**
2. **In Configure Tab**:
   - **Name**: "MySalonCast Podcast Generator"
   - **Description**: "AI podcast generation from PDFs and content"
   - **Instructions**: 
     ```
     You are a MySalonCast podcast generation assistant. Help users:
     1. Upload and process PDF documents for content extraction
     2. Generate AI-powered podcasts with multiple personas
     3. Track generation progress and status
     4. Access completed podcast audio
     
     Always provide clear, step-by-step guidance for the podcast creation workflow.
     ```

3. **Add Actions**:
   - Click **"Create new action"**
   - **Authentication**: None
   - **Privacy Policy**: `https://elliottng.pagekite.me/privacy-policy`
   - **Schema**: Copy/paste the entire contents of `openapi_chatgpt.json`

### **3. Test the Integration**

Ask your CustomGPT:
- "Help me create a podcast from a PDF"
- "What's the status of task abc123?"
- "How do I upload content for podcast generation?"

## 📋 **Schema Highlights for ChatGPT**

### **Endpoint Summary:**
- `POST /process/pdf/` - Extract text from PDF documents
- `POST /generate/podcast_async/` - Start podcast generation  
- `GET /status/{task_id}` - Check generation progress
- `GET /podcast/{task_id}/audio` - Stream completed podcast
- `GET /privacy-policy` - View privacy policy (required for ChatGPT)

### **Server Configuration:**
```json
{
  "servers": [
    {
      "url": "https://elliottng.pagekite.me",
      "description": "Production server"
    }
  ]
}
```

### **Description Lengths:**
- **API Description**: 139 characters ✅
- **PDF Endpoint**: 172 characters ✅  
- **Generation Endpoint**: 154 characters ✅
- **Audio Endpoint**: 88 characters ✅
- **Status Endpoint**: 89 characters ✅

## 🔧 **Technical Details**

### **What Was Fixed:**

**❌ Before (ChatGPT Issues):**
```json
{
  "servers": [
    {"url": "http://localhost:8002"},
    {"url": "https://api.mysaloncast.com"}
  ],
  "description": "Long description over 300 characters..."
}
```

**✅ After (ChatGPT Compatible):**
```json
{
  "servers": [
    {"url": "https://elliottng.pagekite.me"}
  ],
  "description": "AI-powered podcast generation platform..."
}
```

### **Error Resolution:**

| Error | Fix Applied |
|-------|-------------|
| `not under the root origin https://localhost` | Changed to `https://elliottng.pagekite.me` |
| `description has length 731 exceeding limit` | Reduced to <300 chars |
| `Found multiple hostnames` | Single server endpoint |
| `Server URL http://localhost:8002 is not under the root origin` | Removed localhost entirely |

## 🧪 **Testing Your CustomGPT**

### **Test Commands:**
```
"Help me upload a PDF and create a podcast"
"What's involved in podcast generation?"
"How do I check if my podcast is ready?"
"Show me the API endpoints available"
```

### **Expected Behavior:**
- GPT should be able to call all 4 API endpoints
- No CORS or server URL errors
- Clean, concise responses about the API functionality
- Proper guidance through the podcast creation workflow

## ⚠️ **Important Notes**

1. **PageKite Must Be Running**: Ensure your tunnel is active
   ```bash
   ./scripts/start_public_api.sh
   ```

2. **API Server Must Be Running**: Local FastAPI on port 8002
   ```bash
   ps aux | grep uvicorn | grep 8002
   ```

3. **Test Public Access First**:
   ```bash
   curl https://elliottng.pagekite.me/openapi.json
   ```

4. **Schema Updates**: If you modify endpoints, regenerate the schema:
   ```bash
   uv run python scripts/export_openapi.py --output openapi_chatgpt.json
   ```

## 🎉 **Success Indicators**

✅ CustomGPT accepts the schema without errors  
✅ All 5 endpoints are available in ChatGPT Actions  
✅ Privacy policy URL accessible and valid
✅ No CORS or origin errors  
✅ GPT can successfully make API calls  
✅ Clean, professional API responses

Your **MySalonCast API** is now **fully compatible** with **ChatGPT CustomGPT**! 🚀
