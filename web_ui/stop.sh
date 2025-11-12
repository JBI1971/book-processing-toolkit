#!/bin/bash

# Book Review Interface - Shutdown Script
# This script stops both the backend (FastAPI) and frontend (React) servers

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# PID file to track running processes
PID_FILE="$SCRIPT_DIR/.server_pids"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}================================================${NC}"
echo -e "${YELLOW}  Book Review Interface - Stopping Servers${NC}"
echo -e "${YELLOW}================================================${NC}"
echo ""

# Check if PID file exists
if [ ! -f "$PID_FILE" ]; then
    echo -e "${YELLOW}No PID file found. Servers may not be running.${NC}"
    echo "Attempting to find and stop servers by port..."

    # Try to find processes by port
    BACKEND_PORT_PID=$(lsof -ti:8000 2>/dev/null)
    FRONTEND_PORT_PID=$(lsof -ti:5173 2>/dev/null)

    if [ -z "$BACKEND_PORT_PID" ] && [ -z "$FRONTEND_PORT_PID" ]; then
        echo -e "${GREEN}No servers found running on ports 8000 or 5173.${NC}"
        exit 0
    fi

    if [ -n "$BACKEND_PORT_PID" ]; then
        echo -e "Stopping backend (PID: ${YELLOW}$BACKEND_PORT_PID${NC})..."
        kill $BACKEND_PORT_PID 2>/dev/null
        sleep 1
        if ps -p $BACKEND_PORT_PID > /dev/null 2>&1; then
            echo -e "${RED}Backend didn't stop gracefully. Force killing...${NC}"
            kill -9 $BACKEND_PORT_PID 2>/dev/null
        fi
        echo -e "${GREEN}Backend stopped.${NC}"
    fi

    if [ -n "$FRONTEND_PORT_PID" ]; then
        echo -e "Stopping frontend (PID: ${YELLOW}$FRONTEND_PORT_PID${NC})..."
        kill $FRONTEND_PORT_PID 2>/dev/null
        sleep 1
        if ps -p $FRONTEND_PORT_PID > /dev/null 2>&1; then
            echo -e "${RED}Frontend didn't stop gracefully. Force killing...${NC}"
            kill -9 $FRONTEND_PORT_PID 2>/dev/null
        fi
        echo -e "${GREEN}Frontend stopped.${NC}"
    fi

    echo ""
    echo -e "${GREEN}Cleanup complete.${NC}"
    exit 0
fi

# Load PIDs from file
source "$PID_FILE"

STOPPED_COUNT=0
FAILED_COUNT=0

# Stop backend
if [ -n "$BACKEND_PID" ]; then
    echo -e "Stopping backend server (PID: ${YELLOW}$BACKEND_PID${NC})..."

    if ps -p $BACKEND_PID > /dev/null 2>&1; then
        kill $BACKEND_PID 2>/dev/null

        # Wait up to 5 seconds for graceful shutdown
        for i in {1..5}; do
            if ! ps -p $BACKEND_PID > /dev/null 2>&1; then
                break
            fi
            sleep 1
        done

        # Force kill if still running
        if ps -p $BACKEND_PID > /dev/null 2>&1; then
            echo -e "${RED}Backend didn't stop gracefully. Force killing...${NC}"
            kill -9 $BACKEND_PID 2>/dev/null
            sleep 1
        fi

        if ! ps -p $BACKEND_PID > /dev/null 2>&1; then
            echo -e "${GREEN}Backend stopped successfully.${NC}"
            ((STOPPED_COUNT++))
        else
            echo -e "${RED}Failed to stop backend.${NC}"
            ((FAILED_COUNT++))
        fi
    else
        echo -e "${YELLOW}Backend process not found (already stopped).${NC}"
    fi
else
    echo -e "${YELLOW}No backend PID in file.${NC}"
fi

# Stop frontend
if [ -n "$FRONTEND_PID" ]; then
    echo -e "Stopping frontend server (PID: ${YELLOW}$FRONTEND_PID${NC})..."

    if ps -p $FRONTEND_PID > /dev/null 2>&1; then
        kill $FRONTEND_PID 2>/dev/null

        # Wait up to 5 seconds for graceful shutdown
        for i in {1..5}; do
            if ! ps -p $FRONTEND_PID > /dev/null 2>&1; then
                break
            fi
            sleep 1
        done

        # Force kill if still running
        if ps -p $FRONTEND_PID > /dev/null 2>&1; then
            echo -e "${RED}Frontend didn't stop gracefully. Force killing...${NC}"
            kill -9 $FRONTEND_PID 2>/dev/null
            sleep 1
        fi

        if ! ps -p $FRONTEND_PID > /dev/null 2>&1; then
            echo -e "${GREEN}Frontend stopped successfully.${NC}"
            ((STOPPED_COUNT++))
        else
            echo -e "${RED}Failed to stop frontend.${NC}"
            ((FAILED_COUNT++))
        fi
    else
        echo -e "${YELLOW}Frontend process not found (already stopped).${NC}"
    fi
else
    echo -e "${YELLOW}No frontend PID in file.${NC}"
fi

# Also check and kill any processes on the ports (cleanup)
echo ""
echo "Checking for any remaining processes on ports 8000 and 5173..."

BACKEND_PORT_PID=$(lsof -ti:8000 2>/dev/null)
if [ -n "$BACKEND_PORT_PID" ]; then
    echo -e "${YELLOW}Found process on port 8000 (PID: $BACKEND_PORT_PID). Killing...${NC}"
    kill -9 $BACKEND_PORT_PID 2>/dev/null
fi

FRONTEND_PORT_PID=$(lsof -ti:5173 2>/dev/null)
if [ -n "$FRONTEND_PORT_PID" ]; then
    echo -e "${YELLOW}Found process on port 5173 (PID: $FRONTEND_PORT_PID). Killing...${NC}"
    kill -9 $FRONTEND_PORT_PID 2>/dev/null
fi

# Remove PID file
rm -f "$PID_FILE"
echo -e "${GREEN}PID file removed.${NC}"

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}  Shutdown Complete${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""

if [ $STOPPED_COUNT -gt 0 ]; then
    echo -e "${GREEN}Stopped $STOPPED_COUNT server(s).${NC}"
fi

if [ $FAILED_COUNT -gt 0 ]; then
    echo -e "${RED}Failed to stop $FAILED_COUNT server(s).${NC}"
    exit 1
fi

echo -e "${GREEN}All servers stopped successfully.${NC}"
exit 0
