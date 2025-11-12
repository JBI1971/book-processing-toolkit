# Translation Manager - Quick Reference

**Location**: `/Users/jacki/PycharmProjects/agentic_test_project/web_ui/translation_manager/`

## Quick Start

```bash
# Navigate to translation manager
cd /Users/jacki/PycharmProjects/agentic_test_project/web_ui/translation_manager

# First-time setup
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your paths

cd ../frontend
npm install

# Start application
cd ..
./start.sh
```

## Access URLs

- **Frontend**: http://localhost:5174
- **Backend**: http://localhost:8001
- **API Docs**: http://localhost:8001/docs

## Configuration

Edit `backend/.env`:
```bash
CATALOG_DB_PATH=/Users/jacki/project_files/translation_project/wuxia_catalog.db
SOURCE_DIR=/Users/jacki/project_files/translation_project/wuxia_individual_files
OUTPUT_DIR=/Users/jacki/project_files/translation_project/translations
```

## Key Features

1. **Works Catalog** - Browse and search 400+ wuxia works
2. **Batch Translation** - Select multiple works, configure parameters
3. **Job Monitoring** - Real-time progress with WebSocket updates
4. **Configuration** - Manage paths and translation settings

## Documentation

- **README.md** - Complete user guide
- **SETUP.md** - Detailed setup instructions
- **DEPLOYMENT.md** - Production deployment guide
- **ARCHITECTURE.md** - Technical architecture
- **SUMMARY.md** - Delivery summary

## Common Commands

```bash
# Start servers
./start.sh

# Stop servers
./stop.sh

# View backend logs
tail -f logs/backend.log

# View frontend logs
tail -f logs/frontend.log

# Restart backend only
cd backend
source venv/bin/activate
python app.py

# Restart frontend only
cd frontend
npm run dev
```

## File Structure

```
translation_manager/
├── backend/          # FastAPI server
│   ├── app.py       # Main application
│   └── .env         # Configuration
├── frontend/        # React application
│   └── src/
│       ├── pages/   # UI pages
│       └── api/     # API client
├── logs/            # Application logs
├── start.sh         # Startup script
├── stop.sh          # Shutdown script
└── *.md            # Documentation
```

## Troubleshooting

**Backend won't start**:
```bash
# Check .env exists
ls backend/.env

# Check database path
ls -la /path/to/wuxia_catalog.db

# Reinstall dependencies
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

**Frontend won't start**:
```bash
# Reinstall dependencies
cd frontend
rm -rf node_modules package-lock.json
npm install
```

**WebSocket not connecting**:
- Check backend is running: `curl http://localhost:8001/`
- Check browser console for errors
- Verify CORS settings in `backend/app.py`

## Integration

The Translation Manager integrates with:
- SQLite catalog database (`wuxia_catalog.db`)
- Translation scripts (`scripts/translate_work.py`)
- Volume manager (`processors/volume_manager.py`)
- OpenAI API (via `env_creds.yml`)

## Next Steps

1. Run `./start.sh` to launch application
2. Open http://localhost:5174 in browser
3. Browse works catalog
4. Select a work and create test job
5. Monitor progress on Jobs page
6. Check output in configured OUTPUT_DIR

## Support

- See **README.md** for full documentation
- See **SETUP.md** for installation help
- See **DEPLOYMENT.md** for production setup
- Check logs in `logs/` directory
- Review backend logs for errors
- Check browser console for frontend issues

---

**Created**: 2025-01-10
**Version**: 1.0.0
**Status**: Production Ready ✅
