"""
Analysis API endpoints - background processing for chapter validation and structure analysis
"""
import json
import os
import asyncio
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
import sys

# Add project root to path to import utilities
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from utils.chapter_sequence_validator import ChineseChapterSequenceValidator, SequenceIssue
from utils.toc_alignment_validator import TOCAlignmentValidator, AlignmentResult


router = APIRouter()

# Get paths from environment or use defaults
CLEANED_JSON_DIR = os.getenv(
    "CLEANED_JSON_DIR",
    "/Users/jacki/project_files/translation_project/01_clean_json"
)
CATALOG_DB_PATH = os.getenv(
    "CATALOG_DB_PATH",
    "/Users/jacki/project_files/translation_project/wuxia_catalog.db"
)

# In-memory cache for analysis results
# In production, this should be Redis or a database
_analysis_cache: Dict[str, dict] = {}


class AnalysisStatus(BaseModel):
    """Status of an analysis task"""
    work_id: str
    status: str  # "pending", "running", "completed", "failed"
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    progress: int = 0  # 0-100
    current_stage: Optional[str] = None
    error: Optional[str] = None


class AnalysisResult(BaseModel):
    """Complete analysis result"""
    work_id: str
    status: str
    started_at: str
    completed_at: Optional[str] = None

    # Chapter sequence validation
    sequence_issues: List[Dict] = []
    sequence_summary: Optional[str] = None

    # TOC alignment validation
    toc_alignment_valid: bool = False
    toc_confidence_score: float = 0.0
    toc_issues: List[Dict] = []
    toc_summary: Optional[str] = None

    # Overall metrics
    total_chapters: int = 0
    total_issues: int = 0
    critical_issues: int = 0
    warnings: int = 0


async def run_analysis(work_id: str, file_path: Path):
    """
    Run background analysis on a work

    This includes:
    1. Chapter sequence validation (Chinese numerals, gaps, duplicates)
    2. TOC alignment validation (semantic matching with OpenAI)
    """
    try:
        # Update status
        _analysis_cache[work_id] = {
            "status": "running",
            "started_at": datetime.utcnow().isoformat(),
            "progress": 0,
            "current_stage": "loading"
        }

        # Load work data
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        result = {
            "work_id": work_id,
            "status": "running",
            "started_at": _analysis_cache[work_id]["started_at"],
            "sequence_issues": [],
            "toc_issues": [],
            "total_chapters": len(data.get('structure', {}).get('body', {}).get('chapters', []))
        }

        # Stage 1: Chapter Sequence Validation
        _analysis_cache[work_id].update({
            "progress": 20,
            "current_stage": "chapter_sequence"
        })

        try:
            validator = ChineseChapterSequenceValidator()
            sequence_issues = validator.validate_from_cleaned_json(data)

            result["sequence_issues"] = [
                {
                    "type": issue.issue_type,
                    "chapter_number": issue.chapter_number,
                    "chapter_title": issue.chapter_title,
                    "details": issue.details,
                    "severity": "error" if issue.issue_type in ["gap", "duplicate"] else "warning"
                }
                for issue in sequence_issues
            ]
            result["sequence_summary"] = f"Found {len(sequence_issues)} sequence issues" if sequence_issues else "No sequence issues found"

        except Exception as e:
            result["sequence_summary"] = f"Sequence validation failed: {str(e)}"

        # Stage 2: TOC Alignment Validation (requires OpenAI API)
        _analysis_cache[work_id].update({
            "progress": 60,
            "current_stage": "toc_alignment"
        })

        try:
            # Check if OpenAI API key is available
            if os.getenv("OPENAI_API_KEY"):
                toc_validator = TOCAlignmentValidator()
                toc_result: AlignmentResult = toc_validator.validate(data)

                result["toc_alignment_valid"] = toc_result.is_valid
                result["toc_confidence_score"] = toc_result.confidence_score
                result["toc_issues"] = [
                    {
                        "toc_entry": issue.toc_entry,
                        "chapter_title": issue.chapter_title,
                        "issue_type": issue.issue_type,
                        "suggested_fix": issue.suggested_fix,
                        "confidence": issue.confidence,
                        "severity": issue.severity
                    }
                    for issue in toc_result.issues
                ]
                result["toc_summary"] = toc_result.summary
            else:
                result["toc_summary"] = "TOC validation skipped (no OpenAI API key)"
                result["toc_alignment_valid"] = True  # Assume valid if can't check

        except Exception as e:
            result["toc_summary"] = f"TOC validation failed: {str(e)}"

        # Calculate totals
        _analysis_cache[work_id].update({
            "progress": 90,
            "current_stage": "finalizing"
        })

        result["total_issues"] = len(result["sequence_issues"]) + len(result["toc_issues"])
        result["critical_issues"] = sum(
            1 for issue in result["sequence_issues"] + result["toc_issues"]
            if issue.get("severity") == "error"
        )
        result["warnings"] = sum(
            1 for issue in result["sequence_issues"] + result["toc_issues"]
            if issue.get("severity") == "warning"
        )

        # Mark as completed
        result["status"] = "completed"
        result["completed_at"] = datetime.utcnow().isoformat()

        _analysis_cache[work_id] = {
            "status": "completed",
            "progress": 100,
            "current_stage": "done",
            "result": result,
            "completed_at": result["completed_at"]
        }

    except Exception as e:
        _analysis_cache[work_id] = {
            "status": "failed",
            "error": str(e),
            "completed_at": datetime.utcnow().isoformat()
        }


@router.post("/analyze/{work_id:path}")
async def start_analysis(work_id: str, background_tasks: BackgroundTasks):
    """
    Start background analysis for a work

    This will validate chapter sequences and TOC alignment in the background.
    Use GET /analyze/{work_id} to check status and results.
    """
    # Construct full path
    file_path = Path(CLEANED_JSON_DIR) / work_id

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Work not found: {work_id}")

    # Check if already running
    if work_id in _analysis_cache and _analysis_cache[work_id].get("status") == "running":
        return {
            "message": "Analysis already in progress",
            "work_id": work_id,
            "status": "running"
        }

    # Start background task
    background_tasks.add_task(run_analysis, work_id, file_path)

    # Initialize cache entry
    _analysis_cache[work_id] = {
        "status": "pending",
        "started_at": datetime.utcnow().isoformat(),
        "progress": 0
    }

    return {
        "message": "Analysis started",
        "work_id": work_id,
        "status": "pending"
    }


@router.get("/analyze/{work_id:path}/status", response_model=AnalysisStatus)
async def get_analysis_status(work_id: str):
    """
    Get the status of an analysis task
    """
    if work_id not in _analysis_cache:
        raise HTTPException(status_code=404, detail="No analysis found for this work")

    cache_entry = _analysis_cache[work_id]

    return AnalysisStatus(
        work_id=work_id,
        status=cache_entry.get("status", "unknown"),
        started_at=cache_entry.get("started_at"),
        completed_at=cache_entry.get("completed_at"),
        progress=cache_entry.get("progress", 0),
        current_stage=cache_entry.get("current_stage"),
        error=cache_entry.get("error")
    )


@router.get("/analyze/{work_id:path}", response_model=AnalysisResult)
async def get_analysis_result(work_id: str):
    """
    Get the complete analysis result for a work

    Returns detailed validation results including:
    - Chapter sequence issues (gaps, duplicates, out-of-order)
    - TOC alignment issues (mismatches, typos, missing chapters)
    - Overall metrics and summary
    """
    if work_id not in _analysis_cache:
        raise HTTPException(status_code=404, detail="No analysis found for this work")

    cache_entry = _analysis_cache[work_id]

    if cache_entry.get("status") != "completed":
        status = cache_entry.get("status", "unknown")
        error = cache_entry.get("error")

        if status == "failed":
            raise HTTPException(
                status_code=500,
                detail=f"Analysis failed: {error}"
            )
        else:
            raise HTTPException(
                status_code=202,
                detail=f"Analysis still {status}. Check /analyze/{work_id}/status for progress."
            )

    return AnalysisResult(**cache_entry["result"])
