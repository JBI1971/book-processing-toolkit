# Translation Manager

A comprehensive web-based interface for managing book translation jobs in the Book Processing Toolkit.

## Features

### 1. Book Catalog Browser
- **Search & Filter**: Find books by title, author, or work number
- **Metadata Display**: View Chinese/English titles, authors, volume counts
- **Multi-select**: Select multiple works for batch translation
- **Status Tracking**: See translation status for each work

### 2. Translation Job Management
- **Job Creation**: Start translation jobs with configurable parameters
- **Real-time Monitoring**: Track progress via WebSocket connections
- **Job Queue**: Automatic queue management with concurrent processing
- **Job Control**: Pause/resume/cancel running jobs

### 3. Progress Monitoring
- **Live Updates**: Real-time progress bars and status updates
- **Work-by-work Tracking**: See which work is currently being translated
- **Success/Failure Counts**: Track completed and failed works
- **Detailed Statistics**: Token usage, time estimates, error logs

### 4. Configuration Management
- **Path Configuration**: Set catalog, source, and output directories
- **Model Selection**: Choose between GPT-4o, GPT-4o-mini, etc.
- **Parameter Tuning**: Adjust temperature, retries, concurrency
- **Environment Display**: View current configuration and system info

## Architecture

```
translation_manager/
├── backend/                 # FastAPI backend
│   ├── app.py              # Main API server
│   ├── requirements.txt    # Python dependencies
│   └── .env               # Configuration (create from .env.example)
│
├── frontend/               # React frontend
│   ├── src/
│   │   ├── pages/         # WorkListPage, JobsPage, ConfigPage
│   │   ├── api/           # API client with WebSocket support
│   │   └── App.jsx        # Main application
│   ├── package.json       # Node dependencies
│   └── vite.config.js     # Vite configuration
│
├── logs/                   # Application logs
├── start.sh               # Startup script
├── stop.sh                # Shutdown script
└── README.md              # This file
```

## Quick Start

### Prerequisites

- Python 3.8+
- Node.js 16+
- SQLite database with work catalog
- OpenAI API key (loaded from project root `env_creds.yml`)

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your paths:
#   - CATALOG_DB_PATH
#   - SOURCE_DIR
#   - OUTPUT_DIR
```

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install
```

### 3. Start Application

**Option A: Use startup script (recommended)**
```bash
# From translation_manager directory
./start.sh
```

**Option B: Manual start**
```bash
# Terminal 1 - Backend
cd backend
source venv/bin/activate
python app.py

# Terminal 2 - Frontend
cd frontend
npm run dev
```

### 4. Access Application

- **Frontend UI**: http://localhost:5174
- **Backend API**: http://localhost:8001
- **API Documentation**: http://localhost:8001/docs

## Usage Guide

### Creating a Translation Job

1. **Browse Works**
   - Go to "Works Catalog" page
   - Use search to filter by title, author, or work number
   - Click checkboxes to select works

2. **Configure Job**
   - Click "Start Translation" button
   - Choose translation model (GPT-4o-mini recommended for cost)
   - Set temperature (0.3 default for consistency)
   - Set max retries (3 default)

3. **Monitor Progress**
   - Go to "Translation Jobs" page
   - View real-time progress updates
   - Click job card to see detailed information
   - Watch completed/failed counts update live

4. **Review Results**
   - Translation outputs saved to configured OUTPUT_DIR
   - Logs saved to configured LOG_DIR
   - Check job statistics for token usage and costs

### Managing Jobs

**Pause a Job**
- Click "Pause" button on running job
- Job will stop after completing current work

**View Job Details**
- Click on any job card
- See full work list with status indicators
- View error messages if job failed
- Check statistics and timing information

**Cancel a Job**
- Click "Pause" on running job
- Job cannot be resumed (implementation choice)

## API Endpoints

### Works

- `GET /api/works` - List all works (with optional `?search=query`)
- `GET /api/works/{work_number}` - Get detailed work information

### Jobs

- `POST /api/jobs` - Create new translation job
- `GET /api/jobs` - List all jobs
- `GET /api/jobs/{job_id}` - Get job status
- `DELETE /api/jobs/{job_id}` - Cancel job

### WebSocket

- `WS /ws` - Real-time job updates

## Configuration

### Backend Environment Variables

Create `backend/.env`:

```bash
# Required
CATALOG_DB_PATH=/path/to/wuxia_catalog.db
SOURCE_DIR=/path/to/wuxia_individual_files
OUTPUT_DIR=/path/to/translations

# Optional
LOG_DIR=./logs
BACKEND_PORT=8001
```

### Frontend Environment Variables

Create `frontend/.env` (optional):

```bash
VITE_API_BASE_URL=http://localhost:8001
```

### Translation Pipeline Integration

The backend integrates with existing translation scripts:
- `processors.translation_config.TranslationConfig`
- `processors.volume_manager.VolumeManager`
- `scripts.translate_work.WorkTranslationOrchestrator`

## Development

### Backend Development

```bash
cd backend
source venv/bin/activate

# Run with hot reload
uvicorn app:app --reload --port 8001

# View API docs
open http://localhost:8001/docs
```

### Frontend Development

```bash
cd frontend

# Run dev server with hot reload
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Adding Features

**New API Endpoint:**
1. Add endpoint function to `backend/app.py`
2. Add corresponding method to `frontend/src/api/client.js`
3. Use in React components

**New Page:**
1. Create component in `frontend/src/pages/`
2. Add route in `frontend/src/App.jsx`
3. Add navigation link in header

## Troubleshooting

### Backend won't start

**Check 1: Virtual environment**
```bash
cd backend
source venv/bin/activate
python --version  # Should show Python 3.8+
```

**Check 2: Dependencies**
```bash
pip install -r requirements.txt
```

**Check 3: Environment file**
```bash
ls -la .env  # File should exist
cat .env     # Check paths are correct
```

**Check 4: Database access**
```bash
ls -la /path/to/wuxia_catalog.db  # File should exist
```

### Frontend won't start

**Check 1: Node version**
```bash
node --version  # Should show v16+
npm --version   # Should show v8+
```

**Check 2: Dependencies**
```bash
rm -rf node_modules package-lock.json
npm install
```

**Check 3: Port conflict**
```bash
lsof -i:5174  # Check if port is in use
```

### WebSocket not connecting

**Check 1: Backend running**
```bash
curl http://localhost:8001/
```

**Check 2: CORS configuration**
- Backend allows `http://localhost:5173` and `http://localhost:3000`
- Check `frontend/vite.config.js` port matches

**Check 3: Browser console**
- Open browser DevTools > Network tab
- Look for WS connection in network requests
- Check error messages

### Jobs not running

**Check 1: API key**
- OpenAI API key loaded from project root `env_creds.yml`
- Verify key is valid and has credits

**Check 2: Source files**
```bash
ls -la /path/to/wuxia_individual_files/wuxia_*/
```

**Check 3: Backend logs**
```bash
tail -f logs/backend.log
```

**Check 4: Job processor**
- Job processor runs as background task in backend
- Check `app.py` lifespan function is working

## Performance Considerations

### Concurrent Jobs

- Backend processes one job at a time (sequential)
- Each job processes multiple works sequentially
- To run multiple jobs concurrently, run multiple backend instances on different ports

### Large Catalogs

- Frontend loads all works at once (up to 100 by default)
- Adjust `limit` parameter in `/api/works` for larger catalogs
- Consider implementing pagination for 1000+ works

### WebSocket Connections

- Each browser tab creates one WebSocket connection
- Connections auto-reconnect on disconnect
- Ping/pong keepalive every 30 seconds

## Security Notes

⚠️ **This is a development/internal tool. Do NOT expose to public internet without:**

1. Authentication (add user login)
2. Authorization (role-based access control)
3. Rate limiting (prevent API abuse)
4. Input validation (sanitize all inputs)
5. HTTPS (encrypt all traffic)
6. API key encryption (don't store in plaintext)

## Integration with Existing Pipeline

This interface integrates seamlessly with the existing Book Processing Toolkit:

1. **Catalog Database**: Uses same `wuxia_catalog.db` as other scripts
2. **Source Files**: Reads from same `wuxia_individual_files` directory
3. **Translation Scripts**: Calls `scripts/translate_work.py` orchestrator
4. **Volume Management**: Uses `processors/volume_manager.py`
5. **Configuration**: Compatible with `processors/translation_config.py`

## Future Enhancements

Potential features for future versions:

- [ ] Batch processing pipeline integration (6-stage processing)
- [ ] Preview translated content before saving
- [ ] Validation report viewer
- [ ] TOC/chapter alignment visualization
- [ ] Multiple concurrent job support
- [ ] Job scheduling and queuing priorities
- [ ] Email notifications on job completion
- [ ] Cost estimation before starting jobs
- [ ] Export job history and statistics
- [ ] User authentication and multi-user support

## Support

For issues or questions:

1. Check this README troubleshooting section
2. Review backend logs in `logs/backend.log`
3. Check browser console for frontend errors
4. Review project CLAUDE.md for pipeline details

## License

Part of the Book Processing Toolkit project.
