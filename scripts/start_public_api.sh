#!/bin/bash

# MySalonCast Public API Startup Script
# This script starts the REST API server and PageKite tunnel

echo "🚀 Starting MySalonCast Public API..."
echo "======================================"

# Change to project directory
cd /home/elliottng/CascadeProjects/mysaloncast

# Start REST API server in background
echo "📡 Starting REST API server on port 8002..."
uv run uvicorn app.main:app --host 127.0.0.1 --port 8002 &
API_PID=$!
echo "   REST API started with PID: $API_PID"

# Wait a moment for the server to start
sleep 3

# Start PageKite tunnel
echo "🌐 Starting PageKite tunnel..."
echo "   Tunneling localhost:8002 → https://elliottng.pagekite.me/"
cd /home/elliottng/CascadeProjects
python pagekite.py --frontend=elliottng.pagekite.me:80 localhost:8002 elliottng.pagekite.me &
PAGEKITE_PID=$!
echo "   PageKite started with PID: $PAGEKITE_PID"

echo ""
echo "✅ Setup complete!"
echo "======================================"
echo "🌐 Public API URL: https://elliottng.pagekite.me/"
echo "📖 Swagger UI: https://elliottng.pagekite.me/docs"
echo "📚 ReDoc: https://elliottng.pagekite.me/redoc"
echo "📄 OpenAPI JSON: https://elliottng.pagekite.me/openapi.json"
echo ""
echo "💡 To stop services:"
echo "   kill $API_PID $PAGEKITE_PID"
echo ""
echo "📝 Process IDs saved to: /tmp/mysaloncast_pids.txt"
echo "$API_PID" > /tmp/mysaloncast_pids.txt
echo "$PAGEKITE_PID" >> /tmp/mysaloncast_pids.txt

# Keep the script running to show logs
echo "🔍 Monitoring services... (Press Ctrl+C to stop monitoring)"
wait
