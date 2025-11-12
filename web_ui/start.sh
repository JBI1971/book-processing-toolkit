#!/bin/bash

# Book Review Interface - Startup Script
# This script starts both the backend (FastAPI) and frontend (React) servers

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

echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}  Book Review Interface - Starting Servers${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""

# Check if servers are already running
if [ -f "$PID_FILE" ]; then
    echo -e "${YELLOW}Warning: Server PID file exists. Servers may already be running.${NC}"
    echo -e "${YELLOW}Run ./stop.sh first to stop existing servers.${NC}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
    rm -f "$PID_FILE"
fi

# Check if .env exists in backend
if [ ! -f "backend/.env" ]; then
    echo -e "${YELLOW}Warning: backend/.env not found!${NC}"
    echo "Copying .env.example to .env..."
    cp backend/.env.example backend/.env
    echo -e "${RED}Please edit backend/.env and add your OPENAI_API_KEY${NC}"
    exit 1
fi

# Check if Python venv exists
if [ ! -d "backend/venv" ]; then
    echo -e "${YELLOW}Python virtual environment not found. Creating...${NC}"
    python3 -m venv backend/venv
    echo -e "${GREEN}Virtual environment created${NC}"
fi

# Activate venv and install Python dependencies
echo -e "${GREEN}Installing Python dependencies...${NC}"
source backend/venv/bin/activate
pip install -q -r backend/requirements.txt

# Start backend server in background
echo -e "${GREEN}Starting backend server on port 8000...${NC}"
cd backend
python app.py > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
cd ..

# Wait for backend to start
echo "Waiting for backend to initialize..."
sleep 3

# Check if backend is still running
if ! ps -p $BACKEND_PID > /dev/null; then
    echo -e "${RED}Backend failed to start. Check logs/backend.log${NC}"
    exit 1
fi

# Start frontend server
echo -e "${GREEN}Starting frontend server on port 5173...${NC}"
cd frontend
npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

# Wait for frontend to start
echo "Waiting for frontend to initialize..."
sleep 3

# Check if frontend is still running
if ! ps -p $FRONTEND_PID > /dev/null; then
    echo -e "${RED}Frontend failed to start. Check logs/frontend.log${NC}"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

# Save PIDs to file
echo "BACKEND_PID=$BACKEND_PID" > "$PID_FILE"
echo "FRONTEND_PID=$FRONTEND_PID" >> "$PID_FILE"

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}  Servers Started Successfully!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo -e "Backend API:  ${YELLOW}http://localhost:8000${NC}"
echo -e "Frontend:     ${YELLOW}http://localhost:5173${NC}"
echo -e "API Docs:     ${YELLOW}http://localhost:8000/docs${NC}"
echo ""
echo -e "Backend PID:  ${YELLOW}$BACKEND_PID${NC}"
echo -e "Frontend PID: ${YELLOW}$FRONTEND_PID${NC}"
echo ""
echo -e "Logs are being written to:"
echo -e "  - logs/backend.log"
echo -e "  - logs/frontend.log"
echo ""
echo -e "To stop servers, run: ${YELLOW}./stop.sh${NC}"
echo -e "Or press ${RED}Ctrl+C${NC} in this terminal"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Stopping servers...${NC}"
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    rm -f "$PID_FILE"
    echo -e "${GREEN}Servers stopped.${NC}"
    exit 0
}

# Set up trap for Ctrl+C
trap cleanup INT TERM

# Wait for processes (this keeps the script running)
wait
