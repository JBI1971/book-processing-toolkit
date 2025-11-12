# Book Review Interface - Quick Start Guide

## Prerequisites

1. **Python 3.8+** with venv support
2. **Node.js 16+** with npm
3. **OpenAI API Key** for translation features

## Quick Start

### 1. Configure Environment

First time only:

```bash
cd web_ui
cp backend/.env.example backend/.env
# Edit backend/.env and add your OPENAI_API_KEY
```

### 2. Start Servers

```bash
./start.sh
```

This will:
- Create Python virtual environment (if needed)
- Install all dependencies
- Start backend on http://localhost:8000
- Start frontend on http://localhost:5173
- Create log files in `logs/` directory
- Save process IDs to `.server_pids` file

### 3. Stop Servers

```bash
./stop.sh
```

This will:
- Gracefully stop both servers
- Force kill if graceful shutdown fails
- Clean up port bindings (8000 and 5173)
- Remove PID tracking file

**Alternative:** Press `Ctrl+C` in the terminal where `start.sh` is running.

## Access Points

Once started:

- **Frontend UI**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs (Swagger UI)

## Server Logs

Logs are written to:

- `logs/backend.log` - FastAPI server output
- `logs/frontend.log` - Vite dev server output

View logs in real-time:

```bash
# Backend logs
tail -f logs/backend.log

# Frontend logs
tail -f logs/frontend.log
```

## Troubleshooting

### Servers won't start

1. **Check if ports are already in use:**
   ```bash
   lsof -i :8000  # Backend port
   lsof -i :5173  # Frontend port
   ```

2. **Kill existing processes:**
   ```bash
   ./stop.sh
   ```

3. **Check logs for errors:**
   ```bash
   cat logs/backend.log
   cat logs/frontend.log
   ```

### Backend fails to start

- Verify `.env` file exists in `backend/` directory
- Check `OPENAI_API_KEY` is set correctly
- Verify paths in `.env` point to valid directories:
  - `CLEANED_JSON_DIR`
  - `REVIEWED_JSON_DIR`

### Frontend fails to start

- Run `npm install` manually in `frontend/` directory:
  ```bash
  cd frontend
  npm install
  ```

### Can't connect to backend

- Ensure backend is running: `curl http://localhost:8000/health`
- Check CORS settings in `backend/app.py`
- Verify `VITE_API_BASE_URL` in frontend (should be `http://localhost:8000/api`)

### Stale PID file

If you see "Servers may already be running":

```bash
# Force cleanup
./stop.sh

# Or manually remove PID file
rm .server_pids
```

## Manual Start (Advanced)

If you prefer manual control:

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Development Mode

Both servers run in development mode by default:

- **Backend**: Auto-reload on code changes (uvicorn `--reload`)
- **Frontend**: Hot Module Replacement (Vite HMR)

Simply save your changes and the servers will automatically restart/reload.

## Production Deployment

For production, you'll need to:

1. Build the frontend:
   ```bash
   cd frontend
   npm run build
   ```

2. Serve the backend with a production ASGI server:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -k uvicorn.workers.UvicornWorker backend.app:app
   ```

3. Serve the frontend build with nginx or similar

See deployment documentation for details.

## Environment Variables

### Backend (`backend/.env`)

```bash
# Required
OPENAI_API_KEY=your_api_key_here

# Paths (adjust to your setup)
CLEANED_JSON_DIR=/path/to/cleaned_json
REVIEWED_JSON_DIR=/path/to/reviewed_json

# Optional
BACKEND_PORT=8000
```

### Frontend (`frontend/.env`)

```bash
# Optional - defaults to http://localhost:8000/api
VITE_API_BASE_URL=http://localhost:8000/api
```

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `./start.sh` | Start both servers in background |
| `./stop.sh` | Stop both servers gracefully |
| `Ctrl+C` | Stop servers (if started in foreground) |

## Directory Structure

```
web_ui/
├── start.sh              # Startup script
├── stop.sh               # Shutdown script
├── .server_pids          # Process IDs (auto-generated)
├── logs/                 # Server logs
│   ├── backend.log
│   └── frontend.log
├── backend/              # FastAPI backend
│   ├── .env             # Environment config
│   ├── venv/            # Python virtual environment
│   └── app.py           # Main application
└── frontend/            # React frontend
    ├── node_modules/    # Node dependencies
    └── src/             # Source code
```

## Support

For issues or questions:

1. Check logs in `logs/` directory
2. Verify environment configuration
3. Ensure all dependencies are installed
4. Try stopping and restarting: `./stop.sh && ./start.sh`
