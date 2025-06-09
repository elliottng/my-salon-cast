#!/bin/bash

# MySalonCast Public API Stop Script
# This script stops the REST API server and PageKite tunnel

echo "🛑 Stopping MySalonCast Public API..."
echo "====================================="

# Stop processes using saved PIDs
if [ -f /tmp/mysaloncast_pids.txt ]; then
    echo "📝 Using saved process IDs..."
    while read pid; do
        if kill -0 $pid 2>/dev/null; then
            echo "   Stopping process $pid"
            kill $pid
        fi
    done < /tmp/mysaloncast_pids.txt
    rm /tmp/mysaloncast_pids.txt
fi

# Also stop any remaining uvicorn processes for this project
echo "🔍 Stopping any remaining uvicorn processes..."
pkill -f "uvicorn.*app.main:app.*8002"

# Stop any remaining pagekite processes
echo "🌐 Stopping any PageKite processes..."
pkill -f "pagekite.py.*elliottng.pagekite.me"

echo ""
echo "✅ All services stopped!"
echo "====================================="
