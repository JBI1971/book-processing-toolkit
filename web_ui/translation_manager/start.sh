#!/bin/bash
# Translation Manager - Startup Script
# Starts both backend and frontend servers

set -e

echo "=========================================="
echo "Translation Manager - Startup"
echo "=========================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Create PID file
PID_FILE=".server_pids"
echo "" > "$PID_FILE"

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down servers...${NC}"
    if [ -f "$PID_FILE" ]; then
        while read pid; do
            if [ -n "$pid" ]; then
                kill $pid 2>/dev/null || true
            fi
        done < "$PID_FILE"
        rm -f "$PID_FILE"
    fi
    echo -e "${GREEN}Shutdown complete${NC}"
}

trap cleanup EXIT INT TERM

# Check backend setup
echo -e "\n${YELLOW}Checking backend...${NC}"
if [ ! -d "backend/venv" ]; then
    echo -e "${RED}Backend virtual environment not found. Setting up...${NC}"
    cd backend
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    cd ..
fi

if [ ! -f "backend/.env" ]; then
    echo -e "${RED}Backend .env file not found${NC}"
    echo "Please create backend/.env from backend/.env.example"
    exit 1
fi

# Check frontend setup
echo -e "\n${YELLOW}Checking frontend...${NC}"
if [ ! -d "frontend/node_modules" ]; then
    echo -e "${RED}Frontend dependencies not installed. Installing...${NC}"
    cd frontend
    npm install
    cd ..
fi

# Start backend
echo -e "\n${GREEN}Starting backend server...${NC}"
cd backend
source venv/bin/activate
python app.py > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID >> "../$PID_FILE"
cd ..
echo -e "${GREEN}✓ Backend started (PID: $BACKEND_PID)${NC}"
echo "  Logs: logs/backend.log"

# Wait for backend to start
sleep 2

# Start frontend
echo -e "\n${GREEN}Starting frontend server...${NC}"
cd frontend
npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID >> "../$PID_FILE"
cd ..
echo -e "${GREEN}✓ Frontend started (PID: $FRONTEND_PID)${NC}"
echo "  Logs: logs/frontend.log"

# Display access URLs
echo -e "\n=========================================="
echo -e "${GREEN}Translation Manager is running!${NC}"
echo "=========================================="
echo ""
echo "📱 Frontend UI:   http://localhost:5174"
echo "🔌 Backend API:   http://localhost:8001"
echo "📚 API Docs:      http://localhost:8001/docs"
echo ""
echo "Press Ctrl+C to stop all servers"
echo "=========================================="

# Keep script running
wait
