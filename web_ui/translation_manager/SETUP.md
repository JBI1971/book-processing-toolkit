# Translation Manager - Setup Guide

Complete step-by-step setup guide for the Translation Management Interface.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [First Run](#first-run)
5. [Verification](#verification)
6. [Common Issues](#common-issues)

## System Requirements

### Software
- **Python**: 3.8 or higher
- **Node.js**: 16.x or higher
- **npm**: 8.x or higher
- **SQLite**: 3.x (usually pre-installed)

### Hardware
- **RAM**: 4GB minimum, 8GB recommended
- **Disk**: 1GB free space minimum
- **CPU**: Any modern processor

### Operating Systems
- ✅ macOS (tested)
- ✅ Linux (should work)
- ✅ Windows (with minor path adjustments)

## Installation

### Step 1: Verify Prerequisites

```bash
# Check Python version
python3 --version
# Expected: Python 3.8.x or higher

# Check Node.js version
node --version
# Expected: v16.x.x or higher

# Check npm version
npm --version
# Expected: 8.x.x or higher

# Check project structure
cd /Users/jacki/PycharmProjects/agentic_test_project
ls web_ui/translation_manager/
# Expected: backend/ frontend/ README.md start.sh stop.sh
```

### Step 2: Backend Setup

```bash
# Navigate to backend directory
cd web_ui/translation_manager/backend

# Create Python virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate
# Windows: venv\Scripts\activate

# Verify activation (should show venv in prompt)
which python
# Expected: .../backend/venv/bin/python

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Verify installation
python -c "import fastapi, uvicorn; print('✓ Backend dependencies installed')"
```

### Step 3: Frontend Setup

```bash
# Navigate to frontend directory
cd ../frontend  # or: cd web_ui/translation_manager/frontend

# Install dependencies
npm install

# Verify installation
npm list react react-dom react-router-dom axios
# Should show all packages installed
```

### Step 4: Create Logs Directory

```bash
# From translation_manager directory
cd ..  # or: cd web_ui/translation_manager
mkdir -p logs
```

## Configuration

### Step 1: Backend Environment File

```bash
cd backend

# Copy example environment file
cp .env.example .env

# Edit .env file
nano .env  # or use your preferred editor
```

**Required Settings in `.env`:**

```bash
# Path to catalog database (REQUIRED)
CATALOG_DB_PATH=/Users/jacki/project_files/translation_project/wuxia_catalog.db

# Source directory with wuxia_* folders (REQUIRED)
SOURCE_DIR=/Users/jacki/project_files/translation_project/wuxia_individual_files

# Output directory for translations (REQUIRED)
OUTPUT_DIR=/Users/jacki/project_files/translation_project/translations

# Log directory (OPTIONAL - defaults to ./logs)
LOG_DIR=./logs

# Backend port (OPTIONAL - defaults to 8001)
BACKEND_PORT=8001
```

**Verify Paths:**

```bash
# Check catalog database exists
ls -la /Users/jacki/project_files/translation_project/wuxia_catalog.db

# Check source directory exists
ls -la /Users/jacki/project_files/translation_project/wuxia_individual_files/ | head

# Create output directory if it doesn't exist
mkdir -p /Users/jacki/project_files/translation_project/translations
```

### Step 2: OpenAI API Key

The backend loads the OpenAI API key from the project root's `env_creds.yml` file.

**Verify API key is configured:**

```bash
# Check env_creds.yml exists in project root
cd /Users/jacki/PycharmProjects/agentic_test_project
ls -la env_creds.yml

# Verify it contains OPENAI_API_KEY
grep OPENAI_API_KEY env_creds.yml
```

If `env_creds.yml` doesn't exist, create it:

```yaml
# env_creds.yml
OPENAI_API_KEY: "sk-your-api-key-here"
```

### Step 3: Frontend Configuration (Optional)

```bash
cd web_ui/translation_manager/frontend

# Create .env file (optional - uses default if not present)
cat > .env << EOF
VITE_API_BASE_URL=http://localhost:8001
EOF
```

## First Run

### Option 1: Automated Startup (Recommended)

```bash
# From translation_manager directory
cd /Users/jacki/PycharmProjects/agentic_test_project/web_ui/translation_manager

# Start both servers
./start.sh

# Expected output:
# ==========================================
# Translation Manager - Startup
# ==========================================
#
# Checking backend...
# ✓ Backend started (PID: 12345)
#   Logs: logs/backend.log
#
# ✓ Frontend started (PID: 12346)
#   Logs: logs/frontend.log
#
# ==========================================
# Translation Manager is running!
# ==========================================
#
# 📱 Frontend UI:   http://localhost:5174
# 🔌 Backend API:   http://localhost:8001
# 📚 API Docs:      http://localhost:8001/docs
```

### Option 2: Manual Startup

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate
python app.py

# Expected output:
# INFO:     Started server process [12345]
# INFO:     Waiting for application startup.
# INFO:     Application startup complete.
# INFO:     Uvicorn running on http://0.0.0.0:8001
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev

# Expected output:
#   VITE v5.x.x  ready in xxx ms
#
#   ➜  Local:   http://localhost:5174/
#   ➜  Network: use --host to expose
```

## Verification

### Step 1: Check Backend Health

```bash
# Test backend is responding
curl http://localhost:8001/

# Expected output:
# {"status":"ok","service":"Translation Management API","catalog_db":true}

# Check API documentation
open http://localhost:8001/docs
# Should open interactive API documentation in browser
```

### Step 2: Check Frontend Access

```bash
# Open frontend in browser
open http://localhost:5174

# You should see:
# - Translation Manager header
# - Navigation: Works Catalog | Translation Jobs | Configuration
# - Works Catalog page with search bar
```

### Step 3: Test Database Connection

**In browser (http://localhost:5174):**
1. Go to "Works Catalog" page
2. Should see list of works from database
3. Try searching for a work by title or author

**If you see works listed, database connection is working! ✓**

### Step 4: Test Job Creation

**In browser:**
1. Select one or more works (click checkboxes)
2. Click "Start Translation" button
3. Configure job settings
4. Click "▶️ Start Translation"
5. Go to "Translation Jobs" page
6. Should see your job in the list with status "Queued" or "Running"

**Note**: Job won't actually translate unless OpenAI API key is configured correctly.

## Common Issues

### Issue: Backend fails to start

**Error: "Catalog database not found"**
```bash
# Check path in .env
cat backend/.env | grep CATALOG_DB_PATH

# Verify file exists
ls -la /path/to/wuxia_catalog.db

# Fix: Update path in .env to correct location
```

**Error: "ModuleNotFoundError"**
```bash
# Activate virtual environment
cd backend
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

**Error: "Address already in use"**
```bash
# Find process using port 8001
lsof -i:8001

# Kill the process
kill -9 <PID>

# Or change port in backend/.env
echo "BACKEND_PORT=8002" >> backend/.env
```

### Issue: Frontend fails to start

**Error: "EADDRINUSE: address already in use"**
```bash
# Find process using port 5174
lsof -i:5174

# Kill the process
kill -9 <PID>

# Or use different port
npm run dev -- --port 5175
```

**Error: "Cannot find module"**
```bash
# Clear and reinstall
rm -rf node_modules package-lock.json
npm install
```

### Issue: WebSocket not connecting

**Symptom: Jobs page doesn't show real-time updates**

**Fix 1: Check backend is running**
```bash
curl http://localhost:8001/
```

**Fix 2: Check CORS configuration**
- Open browser DevTools > Console
- Look for CORS errors
- Verify frontend port (5174) is allowed in backend CORS settings

**Fix 3: Test WebSocket directly**
```bash
# Install wscat
npm install -g wscat

# Connect to WebSocket
wscat -c ws://localhost:8001/ws

# Should see: Connected (press CTRL+C to quit)
# Send: ping
# Should receive: pong
```

### Issue: Jobs not running

**Symptom: Job stays in "Queued" status**

**Check 1: Backend logs**
```bash
tail -f logs/backend.log
# Look for errors
```

**Check 2: OpenAI API key**
```bash
# Verify key is loaded
cd /Users/jacki/PycharmProjects/agentic_test_project
python -c "from utils.load_env_creds import load_env_credentials; load_env_credentials(); import os; print('API key:', os.getenv('OPENAI_API_KEY')[:10] + '...')"
```

**Check 3: Source files exist**
```bash
ls -la /path/to/wuxia_individual_files/wuxia_*/
```

### Issue: Works catalog is empty

**Symptom: "No works found" message**

**Check 1: Database has data**
```bash
sqlite3 /path/to/wuxia_catalog.db "SELECT COUNT(*) FROM works;"
# Should show number > 0
```

**Check 2: Database path is correct**
```bash
cat backend/.env | grep CATALOG_DB_PATH
# Verify path matches actual database location
```

**Check 3: Restart backend**
```bash
# Stop backend
pkill -f "python app.py"

# Restart
cd backend
source venv/bin/activate
python app.py
```

## Next Steps

After successful setup:

1. **Browse Works**: Explore the catalog and search for books
2. **Create Test Job**: Try translating a single-volume work first
3. **Monitor Progress**: Watch the job on the Jobs page
4. **Check Outputs**: Verify translation files in OUTPUT_DIR
5. **Read Documentation**: Review README.md for full features

## Stopping the Application

```bash
# If using start.sh
# Press Ctrl+C in the terminal

# Or use stop script
./stop.sh

# Or manually
pkill -f "python app.py"
pkill -f "vite"
```

## Getting Help

If you encounter issues not covered here:

1. Check `logs/backend.log` for backend errors
2. Check `logs/frontend.log` for frontend errors
3. Open browser DevTools > Console for frontend errors
4. Review main README.md for troubleshooting
5. Check project CLAUDE.md for pipeline details
