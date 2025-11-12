#!/usr/bin/env python3
"""
Translation Management Interface - Backend API
FastAPI server for managing batch translation jobs

Features:
- Work catalog browsing from SQLite database
- Translation job creation and monitoring
- Real-time progress updates via WebSocket
- Job queue management
"""

import os
import sys
import json
import asyncio
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from processors.translation_config import TranslationConfig
from processors.volume_manager import VolumeManager
from scripts.translate_work import WorkTranslationOrchestrator

# Configuration
CATALOG_DB_PATH = os.getenv(
    'CATALOG_DB_PATH',
    '/Users/jacki/project_files/translation_project/wuxia_catalog.db'
)
SOURCE_DIR = os.getenv(
    'SOURCE_DIR',
    '/Users/jacki/project_files/translation_project/wuxia_individual_files'
)
OUTPUT_DIR = os.getenv(
    'OUTPUT_DIR',
    '/Users/jacki/project_files/translation_project/translations'
)
LOG_DIR = os.getenv(
    'LOG_DIR',
    './logs'
)


# Pydantic Models
class WorkSummary(BaseModel):
    """Summary of a work for catalog display"""
    work_number: str
    title_chinese: str
    title_english: Optional[str] = None
    author_chinese: str
    author_english: Optional[str] = None
    total_volumes: int
    directory_name: Optional[str] = None
    character_count: Optional[int] = None
    word_count: Optional[int] = None
    estimated_tokens: Optional[int] = None
    translation_status: str = "not_started"  # not_started, in_progress, completed, failed


class WorkDetail(BaseModel):
    """Detailed work information"""
    work_number: str
    title_chinese: str
    title_english: Optional[str] = None
    author_chinese: str
    author_english: Optional[str] = None
    category: Optional[str] = None
    summary: Optional[str] = None
    volumes: List[Dict[str, Any]]
    total_chapters: int
    total_volumes: int


class TranslationJobCreate(BaseModel):
    """Create a new translation job"""
    work_numbers: List[str]
    model: str = "gpt-4o-mini"
    temperature: float = 0.3
    max_retries: int = 3
    output_dir: Optional[str] = None


class TranslationJobStatus(BaseModel):
    """Current status of a translation job"""
    job_id: str
    work_numbers: List[str]
    status: str  # queued, running, paused, completed, failed
    progress: float = 0.0  # 0-100
    current_work: Optional[str] = None
    completed_works: List[str] = []
    failed_works: List[str] = []
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    error_message: Optional[str] = None
    statistics: Dict[str, Any] = {}


class ConnectionManager:
    """WebSocket connection manager for real-time updates"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                disconnected.append(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            if connection in self.active_connections:
                self.active_connections.remove(connection)


# Global state
manager = ConnectionManager()
translation_jobs: Dict[str, TranslationJobStatus] = {}
job_queue: asyncio.Queue = asyncio.Queue()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    # Startup: Start job processor
    job_processor_task = asyncio.create_task(job_processor())

    yield

    # Shutdown: Cancel job processor
    job_processor_task.cancel()
    try:
        await job_processor_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Translation Management API",
    description="Backend API for managing book translation jobs",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Database helpers
def get_db_connection():
    """Get SQLite database connection"""
    if not Path(CATALOG_DB_PATH).exists():
        raise HTTPException(status_code=500, detail=f"Catalog database not found: {CATALOG_DB_PATH}")
    return sqlite3.connect(CATALOG_DB_PATH)


def estimate_work_tokens(directory_name: str) -> Optional[int]:
    """
    Estimate total tokens for a work by reading all its JSON files
    Chinese text is roughly 1.5-2 characters per token
    """
    if not directory_name:
        return None

    work_dir = Path(SOURCE_DIR) / directory_name
    if not work_dir.exists():
        return None

    total_chars = 0
    for json_file in work_dir.glob("*.json"):
        try:
            # Get file size as rough estimate (faster than parsing JSON)
            total_chars += json_file.stat().st_size
        except Exception:
            continue

    if total_chars == 0:
        return None

    # Estimate: Chinese JSON is roughly 2 chars per token (including JSON overhead)
    # For just text content, it's closer to 1.5 chars/token
    return int(total_chars / 2)


def get_works_from_db(search: Optional[str] = None, limit: int = 100) -> List[WorkSummary]:
    """Get works from catalog database"""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT DISTINCT
            w.work_number,
            w.title_chinese,
            COALESCE(wc.consensus_title_english, w.title_english) as title_english,
            w.author_chinese,
            COALESCE(wc.consensus_author_english, w.author_english) as author_english,
            COUNT(DISTINCT wf.volume) as volume_count,
            MIN(wf.directory_name) as directory_name,
            SUM(wf.character_count) as total_character_count,
            SUM(wf.word_count) as total_word_count,
            SUM(wf.estimated_tokens) as total_estimated_tokens
        FROM works w
        LEFT JOIN work_files wf ON w.work_id = wf.work_id
        LEFT JOIN works_consensus_translations wc ON w.work_id = wc.work_id
        WHERE 1=1
    """

    params = []
    if search:
        query += """ AND (
            w.title_chinese LIKE ? OR
            w.title_english LIKE ? OR
            w.author_chinese LIKE ? OR
            w.author_english LIKE ? OR
            w.work_number LIKE ?
        )"""
        search_param = f"%{search}%"
        params.extend([search_param, search_param, search_param, search_param, search_param])

    query += " GROUP BY w.work_number"
    query += " ORDER BY MIN(wf.directory_name)"
    query += f" LIMIT {limit}"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    works = []
    for row in rows:
        directory_name = row[6]
        character_count = row[7] if row[7] else None
        word_count = row[8] if row[8] else None
        estimated_tokens = row[9] if row[9] else None

        works.append(WorkSummary(
            work_number=row[0],
            title_chinese=row[1],
            title_english=row[2],
            author_chinese=row[3],
            author_english=row[4],
            total_volumes=row[5] or 1,
            directory_name=directory_name,
            character_count=character_count,
            word_count=word_count,
            estimated_tokens=estimated_tokens
        ))

    return works


def get_work_detail(work_number: str) -> WorkDetail:
    """Get detailed work information"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get work info
    cursor.execute("""
        SELECT
            w.work_number,
            w.title_chinese,
            w.title_english,
            w.author_chinese,
            w.author_english,
            w.category_english,
            w.summary
        FROM works w
        WHERE w.work_number = ?
        LIMIT 1
    """, (work_number,))

    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Work {work_number} not found")

    # Get volumes
    cursor.execute("""
        SELECT
            wf.volume,
            wf.directory_name,
            wf.filename
        FROM work_files wf
        JOIN works w ON wf.work_id = w.work_id
        WHERE w.work_number = ?
        ORDER BY wf.volume
    """, (work_number,))

    volume_rows = cursor.fetchall()
    conn.close()

    volumes = [
        {
            'volume': vol[0] or 'single',
            'directory_name': vol[1],
            'filename': vol[2]
        }
        for vol in volume_rows
    ]

    return WorkDetail(
        work_number=row[0],
        title_chinese=row[1],
        title_english=row[2],
        author_chinese=row[3],
        author_english=row[4],
        category=row[5],
        summary=row[6],
        volumes=volumes,
        total_volumes=len(volumes),
        total_chapters=0  # TODO: Calculate from source files
    )


# Job processing
async def job_processor():
    """Background task that processes translation jobs from the queue"""
    while True:
        try:
            # Get next job from queue
            job_data = await job_queue.get()
            job_id = job_data['job_id']
            job = translation_jobs.get(job_id)

            if not job:
                continue

            # Update status
            job.status = "running"
            job.start_time = datetime.now().isoformat()
            await manager.broadcast({
                'type': 'job_update',
                'job_id': job_id,
                'status': job.status,
                'start_time': job.start_time
            })

            # Process job
            try:
                await process_translation_job(job_id, job_data)
                job.status = "completed"
                job.end_time = datetime.now().isoformat()
            except Exception as e:
                job.status = "failed"
                job.error_message = str(e)
                job.end_time = datetime.now().isoformat()

            # Broadcast completion
            await manager.broadcast({
                'type': 'job_complete',
                'job_id': job_id,
                'status': job.status,
                'end_time': job.end_time,
                'error_message': job.error_message
            })

        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Error in job processor: {e}")


async def process_translation_job(job_id: str, job_data: dict):
    """Process a translation job"""
    job = translation_jobs[job_id]

    # Create translation config
    config = TranslationConfig(
        model=job_data.get('model', 'gpt-4o-mini'),
        temperature=job_data.get('temperature', 0.3),
        max_retries=job_data.get('max_retries', 3),
        output_dir=Path(job_data.get('output_dir', OUTPUT_DIR))
    )

    total_works = len(job.work_numbers)

    for i, work_number in enumerate(job.work_numbers):
        # Update current work
        job.current_work = work_number
        job.progress = (i / total_works) * 100

        await manager.broadcast({
            'type': 'job_progress',
            'job_id': job_id,
            'current_work': work_number,
            'progress': job.progress,
            'completed': i,
            'total': total_works
        })

        try:
            # Run translation in executor to avoid blocking
            orchestrator = WorkTranslationOrchestrator(config)
            result = await asyncio.to_thread(
                orchestrator.translate_work,
                work_number
            )

            if result.get('success', True):
                job.completed_works.append(work_number)
            else:
                job.failed_works.append(work_number)

            # Update statistics
            job.statistics = result.get('statistics', {})

        except Exception as e:
            print(f"Error translating {work_number}: {e}")
            job.failed_works.append(work_number)

    # Final progress update
    job.progress = 100.0


# API Endpoints

@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "ok",
        "service": "Translation Management API",
        "catalog_db": Path(CATALOG_DB_PATH).exists()
    }


@app.get("/api/works", response_model=List[WorkSummary])
async def list_works(search: Optional[str] = None, limit: int = 100):
    """List all works from catalog"""
    try:
        return get_works_from_db(search, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/works/{work_number}", response_model=WorkDetail)
async def get_work(work_number: str):
    """Get detailed work information"""
    return get_work_detail(work_number)


@app.post("/api/jobs", response_model=TranslationJobStatus)
async def create_job(job_request: TranslationJobCreate, background_tasks: BackgroundTasks):
    """Create a new translation job"""
    # Generate job ID
    job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Create job status
    job = TranslationJobStatus(
        job_id=job_id,
        work_numbers=job_request.work_numbers,
        status="queued",
        completed_works=[],
        failed_works=[]
    )

    # Store job
    translation_jobs[job_id] = job

    # Add to queue
    await job_queue.put({
        'job_id': job_id,
        'model': job_request.model,
        'temperature': job_request.temperature,
        'max_retries': job_request.max_retries,
        'output_dir': job_request.output_dir or OUTPUT_DIR
    })

    return job


@app.get("/api/jobs", response_model=List[TranslationJobStatus])
async def list_jobs():
    """List all translation jobs"""
    return list(translation_jobs.values())


@app.get("/api/jobs/{job_id}", response_model=TranslationJobStatus)
async def get_job(job_id: str):
    """Get job status"""
    if job_id not in translation_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return translation_jobs[job_id]


@app.delete("/api/jobs/{job_id}")
async def cancel_job(job_id: str):
    """Cancel a running job"""
    if job_id not in translation_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = translation_jobs[job_id]
    if job.status == "running":
        job.status = "paused"
        return {"message": "Job paused (will stop after current work)"}

    return {"message": "Job not running"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    port = int(os.getenv("BACKEND_PORT", "8001"))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
