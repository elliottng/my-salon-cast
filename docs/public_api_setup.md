# MySalonCast Public API Setup Guide

## 🚀 Quick Start After Reboot

### **Option 1: Use the Convenience Script (Recommended)**
```bash
cd /home/elliottng/CascadeProjects/mysaloncast
./scripts/start_public_api.sh
```

### **Option 2: Manual Setup**
```bash
# 1. Start REST API server
cd /home/elliottng/CascadeProjects/mysaloncast
uv run uvicorn app.main:app --host 127.0.0.1 --port 8002 &

# 2. Start PageKite tunnel
cd /home/elliottng/CascadeProjects
python pagekite.py --frontend=elliottng.pagekite.me:80 localhost:8002 elliottng.pagekite.me &
```

## 🛑 Stopping Services

### **Option 1: Use the Stop Script**
```bash
cd /home/elliottng/CascadeProjects/mysaloncast
./scripts/stop_public_api.sh
```

### **Option 2: Manual Stop**
```bash
# Stop specific processes (if you saved the PIDs)
kill <API_PID> <PAGEKITE_PID>

# OR stop all related processes
pkill -f "uvicorn.*app.main:app.*8002"
pkill -f "pagekite.py.*elliottng.pagekite.me"
```

## 🌐 Your Public URLs

Once running, your API will be available at:

- **Base URL**: https://elliottng.pagekite.me/
- **Swagger UI**: https://elliottng.pagekite.me/docs
- **ReDoc**: https://elliottng.pagekite.me/redoc
- **OpenAPI JSON**: https://elliottng.pagekite.me/openapi.json

## 📋 Available Scripts

| Script | Purpose |
|--------|---------|
| `scripts/start_public_api.sh` | Start both REST API and PageKite tunnel |
| `scripts/stop_public_api.sh` | Stop both services cleanly |
| `scripts/export_openapi.py` | Export OpenAPI schema from running server |

## 🔍 Troubleshooting

### **Check if services are running:**
```bash
# Check REST API
curl http://localhost:8002/docs

# Check PageKite tunnel
curl https://elliottng.pagekite.me/docs

# Check processes
ps aux | grep uvicorn
ps aux | grep pagekite
```

### **Check logs:**
```bash
# The start script shows live logs
# Or check with journalctl if running as systemd service
```

### **Common issues:**

1. **Port 8002 already in use:**
   ```bash
   pkill -f "uvicorn.*8002"
   ```

2. **PageKite won't connect:**
   - Check internet connection
   - Verify elliottng.pagekite.me domain is correct
   - Try restarting PageKite tunnel

3. **API not responding:**
   - Check if REST API started successfully on localhost:8002
   - Verify uvicorn process is running

## 🏃‍♂️ Quick Commands Reference

```bash
# Start everything
./scripts/start_public_api.sh

# Stop everything  
./scripts/stop_public_api.sh

# Test local API
curl http://localhost:8002/openapi.json

# Test public API
curl https://elliottng.pagekite.me/openapi.json

# Export current schema
uv run python scripts/export_openapi.py
```

## 🔐 Security Notes

- PageKite provides HTTPS automatically
- No authentication currently implemented
- Consider adding API keys for production use
- Monitor your PageKite usage quota

## 📊 PageKite Quota

- **Current plan**: 31 days remaining, 5 tunnels
- **Usage**: 1 tunnel (localhost:8002 → elliottng.pagekite.me)
- **Renewal**: Check pagekite.net for plan details
