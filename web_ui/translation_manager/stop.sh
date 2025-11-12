#!/bin/bash
# Translation Manager - Stop Script
# Stops both backend and frontend servers

set -e

echo "Stopping Translation Manager..."

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

PID_FILE=".server_pids"

if [ -f "$PID_FILE" ]; then
    while read pid; do
        if [ -n "$pid" ]; then
            echo "Stopping process $pid..."
            kill $pid 2>/dev/null || true
        fi
    done < "$PID_FILE"
    rm -f "$PID_FILE"
    echo "✓ All servers stopped"
else
    echo "No server PIDs found"
fi

# Also kill any python/node processes on the ports
echo "Cleaning up ports..."
lsof -ti:8001 | xargs kill -9 2>/dev/null || true
lsof -ti:5174 | xargs kill -9 2>/dev/null || true

echo "✓ Translation Manager stopped"
