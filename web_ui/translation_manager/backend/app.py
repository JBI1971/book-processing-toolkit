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

from processors.translation_config import TranslationConfig
from processors.volume_manager import VolumeManager
from scripts.translate_work import WorkTranslationOrchestrator

# Configuration - Load from environment or use EnvironmentConfig defaults
try:
    from utils.environment_config import get_or_create_env_config
    env_config = get_or_create_env_config()

    # Use WUXIA_* environment variables (consistent with project standards)
    # Fall back to EnvironmentConfig defaults
    CATALOG_DB_PATH = os.getenv('WUXIA_CATALOG_PATH', str(env_config.catalog_path))
    SOURCE_DIR = os.getenv('WUXIA_SOURCE_DIR', str(env_config.source_dir))
    OUTPUT_DIR = os.getenv('WUXIA_OUTPUT_DIR', str(env_config.output_dir))
    LOG_DIR = os.getenv('WUXIA_LOG_DIR', str(env_config.log_dir))
except ImportError:
    # Fallback if environment_config not available
    CATALOG_DB_PATH = os.getenv(
        'WUXIA_CATALOG_PATH',
        '/Users/jacki/project_files/translation_project/wuxia_catalog.db'
    )
    SOURCE_DIR = os.getenv(
        'WUXIA_SOURCE_DIR',
        '/Users/jacki/project_files/translation_project/cleaned/COMPLETE_ALL_BOOKS'
    )
    OUTPUT_DIR = os.getenv(
        'WUXIA_OUTPUT_DIR',
        './translation_data/outputs'
    )
    LOG_DIR = os.getenv(
        'WUXIA_LOG_DIR',
        './logs/translation'
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
    model: str = "gpt-4.1-nano"
    temperature: float = 0.3
    max_retries: int = 3
    output_dir: Optional[str] = None


class DetailedProgress(BaseModel):
    """Detailed progress information"""
    current_volume: Optional[str] = None
    current_chapter: Optional[str] = None
    total_chapters: int = 0
    completed_chapters: int = 0
    total_blocks: int = 0
    completed_blocks: int = 0
    current_chapter_blocks: int = 0
    current_chapter_completed: int = 0

    @property
    def chapter_progress_pct(self) -> float:
        """Calculate chapter-level progress percentage"""
        if self.total_chapters == 0:
            return 0.0
        return (self.completed_chapters / self.total_chapters) * 100

    @property
    def block_progress_pct(self) -> float:
        """Calculate block-level progress percentage"""
        if self.total_blocks == 0:
            return 0.0
        return (self.completed_blocks / self.total_blocks) * 100

    @property
    def current_chapter_pct(self) -> float:
        """Calculate current chapter progress percentage"""
        if self.current_chapter_blocks == 0:
            return 0.0
        return (self.current_chapter_completed / self.current_chapter_blocks) * 100


class TranslationJobStatus(BaseModel):
    """Current status of a translation job"""
    job_id: str
    work_numbers: List[str]
    status: str  # queued, running, paused, completed, failed
    progress: float = 0.0  # 0-100 (work-level progress)
    current_work: Optional[str] = None
    completed_works: List[str] = []
    failed_works: List[str] = []
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    error_message: Optional[str] = None
    statistics: Dict[str, Any] = {}
    detailed_progress: Optional[DetailedProgress] = None


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

# Include workflow router
try:
    from web_ui.translation_manager.backend.api.workflow import router as workflow_router
    app.include_router(workflow_router)
except ImportError as e:
    logger.warning(f"Could not load workflow router: {e}")
    # Continue without workflow endpoints for now


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


def get_detailed_progress(work_number: str, volume: Optional[str] = None) -> Optional[DetailedProgress]:
    """
    Get detailed translation progress for a work/volume.

    Reads checkpoint files and output JSON to calculate:
    - Chapter-level progress
    - Block-level progress
    - Current chapter progress
    """
    # Check for checkpoint file
    checkpoint_dir = Path(LOG_DIR) / "checkpoints"
    if volume:
        checkpoint_file = checkpoint_dir / f"{work_number}_{volume}_checkpoint.json"
    else:
        checkpoint_file = checkpoint_dir / f"{work_number}_checkpoint.json"

    if checkpoint_file.exists():
        try:
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                checkpoint_data = json.load(f)

            # Extract progress from checkpoint
            total_chapters = checkpoint_data.get('total_chapters', 0)
            completed_chapters = checkpoint_data.get('completed_chapters', 0)

            # Get current chapter info
            current_chapter_info = checkpoint_data.get('current_chapter', {})
            current_chapter = current_chapter_info.get('chapter_id')
            current_chapter_blocks = current_chapter_info.get('total_blocks', 0)
            current_chapter_completed = current_chapter_info.get('completed_blocks', 0)

            # Calculate total blocks from all chapters
            chapter_progress = checkpoint_data.get('chapter_progress', [])
            total_blocks = sum(ch.get('total_blocks', 0) for ch in chapter_progress)
            completed_blocks = sum(ch.get('completed_blocks', 0) for ch in chapter_progress)

            return DetailedProgress(
                current_volume=volume,
                current_chapter=current_chapter,
                total_chapters=total_chapters,
                completed_chapters=completed_chapters,
                total_blocks=total_blocks,
                completed_blocks=completed_blocks,
                current_chapter_blocks=current_chapter_blocks,
                current_chapter_completed=current_chapter_completed
            )
        except Exception as e:
            logger.error(f"Error reading checkpoint for {work_number}: {e}")

    # Fall back to checking output files
    output_dir = Path(OUTPUT_DIR) / work_number
    if output_dir.exists():
        # Look for translated JSON files
        if volume:
            translated_file = output_dir / f"translated_{work_number}_{volume}.json"
        else:
            translated_file = output_dir / f"translated_{work_number}.json"

        if translated_file.exists():
            try:
                with open(translated_file, 'r', encoding='utf-8') as f:
                    translated_data = json.load(f)

                # Count completed chapters/blocks
                chapters = translated_data.get('structure', {}).get('body', {}).get('chapters', [])
                total_chapters = len(chapters)
                completed_chapters = 0
                total_blocks = 0
                completed_blocks = 0

                for chapter in chapters:
                    blocks = chapter.get('content_blocks', [])
                    total_blocks += len(blocks)

                    # Check if chapter is translated (has translated_annotated_content)
                    translated_count = sum(
                        1 for block in blocks
                        if block.get('translated_annotated_content') is not None
                    )
                    completed_blocks += translated_count

                    if translated_count == len(blocks):
                        completed_chapters += 1

                return DetailedProgress(
                    current_volume=volume,
                    total_chapters=total_chapters,
                    completed_chapters=completed_chapters,
                    total_blocks=total_blocks,
                    completed_blocks=completed_blocks
                )
            except Exception as e:
                logger.error(f"Error reading translated file for {work_number}: {e}")

    return None


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


async def periodic_progress_update(job_id: str, work_number: str, manager: ConnectionManager):
    """
    Periodically broadcast detailed progress updates for an active translation.
    Runs until cancelled.
    """
    while True:
        try:
            await asyncio.sleep(5)  # Update every 5 seconds

            # Get current progress
            progress = get_detailed_progress(work_number)
            if progress:
                await manager.broadcast({
                    'type': 'progress_update',
                    'job_id': job_id,
                    'work_number': work_number,
                    'detailed_progress': progress.dict()
                })
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in periodic progress update: {e}")


async def process_translation_job(job_id: str, job_data: dict):
    """Process a translation job"""
    job = translation_jobs[job_id]

    # Create translation config
    config = TranslationConfig(
        model=job_data.get('model', 'gpt-4.1-nano'),
        temperature=job_data.get('temperature', 0.3),
        max_retries=job_data.get('max_retries', 3),
        output_dir=Path(job_data.get('output_dir', OUTPUT_DIR))
    )

    total_works = len(job.work_numbers)

    for i, work_number in enumerate(job.work_numbers):
        # Update current work
        job.current_work = work_number
        job.progress = (i / total_works) * 100

        # Get detailed progress for this work
        detailed_progress = get_detailed_progress(work_number)
        if detailed_progress:
            job.detailed_progress = detailed_progress

        await manager.broadcast({
            'type': 'job_progress',
            'job_id': job_id,
            'current_work': work_number,
            'progress': job.progress,
            'completed': i,
            'total': total_works,
            'detailed_progress': detailed_progress.dict() if detailed_progress else None
        })

        try:
            # Run translation in executor to avoid blocking
            orchestrator = WorkTranslationOrchestrator(config)

            # Start a background task to periodically update progress
            progress_task = asyncio.create_task(
                periodic_progress_update(job_id, work_number, manager)
            )

            result = await asyncio.to_thread(
                orchestrator.translate_work,
                work_number
            )

            # Cancel progress updates
            progress_task.cancel()
            try:
                await progress_task
            except asyncio.CancelledError:
                pass

            if result.get('success', True):
                job.completed_works.append(work_number)
            else:
                job.failed_works.append(work_number)

            # Update statistics
            job.statistics = result.get('statistics', {})

            # Final progress update for this work
            final_progress = get_detailed_progress(work_number)
            if final_progress:
                job.detailed_progress = final_progress
                await manager.broadcast({
                    'type': 'work_complete',
                    'job_id': job_id,
                    'work_number': work_number,
                    'detailed_progress': final_progress.dict()
                })

        except Exception as e:
            logger.error(f"Error translating {work_number}: {e}")
            job.failed_works.append(work_number)

    # Final progress update
    job.progress = 100.0
    job.detailed_progress = None


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


@app.get("/api/progress/{work_number}", response_model=DetailedProgress)
async def get_work_progress(work_number: str, volume: Optional[str] = None):
    """Get detailed progress for a work/volume"""
    progress = get_detailed_progress(work_number, volume)
    if not progress:
        raise HTTPException(status_code=404, detail="No progress data found")
    return progress


@app.get("/api/jobs/{job_id}/progress", response_model=DetailedProgress)
async def get_job_detailed_progress(job_id: str):
    """Get detailed progress for the current work in a job"""
    if job_id not in translation_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = translation_jobs[job_id]
    if not job.current_work:
        raise HTTPException(status_code=404, detail="No active work in job")

    # Try to get progress for current work
    progress = get_detailed_progress(job.current_work)
    if not progress:
        raise HTTPException(status_code=404, detail="No progress data for current work")

    return progress


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
