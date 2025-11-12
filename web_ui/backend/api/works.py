"""
Works API endpoints - list and retrieve book works
"""
import json
import os
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from models import Book, WorkSummary

router = APIRouter()

# Get paths from environment or use defaults
CLEANED_JSON_DIR = os.getenv(
    "CLEANED_JSON_DIR",
    "/Users/jacki/project_files/translation_project/01_clean_json"
)


def scan_works(search: Optional[str] = None) -> List[WorkSummary]:
    """
    Scan the cleaned JSON directory for all works

    Args:
        search: Optional search string to filter by title, author, or work_number

    Returns:
        List of WorkSummary objects
    """
    works = []
    cleaned_dir = Path(CLEANED_JSON_DIR)

    if not cleaned_dir.exists():
        return works

    # Iterate through all subdirectories
    for work_dir in sorted(cleaned_dir.iterdir()):
        if not work_dir.is_dir():
            continue

        # Find all cleaned JSON files in this directory
        for json_file in work_dir.glob("cleaned_*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                meta = data.get('meta', {})
                structure = data.get('structure', {})
                body = structure.get('body', {})
                chapters = body.get('chapters', [])

                # Create work summary
                work_id = f"{work_dir.name}/{json_file.name}"
                title = meta.get('title_chinese', meta.get('title', 'Unknown'))
                author = meta.get('author_chinese', meta.get('author'))

                summary = WorkSummary(
                    work_id=work_id,
                    directory_name=work_dir.name,
                    work_number=meta.get('work_number'),
                    title=title,
                    title_chinese=meta.get('title_chinese'),
                    title_english=meta.get('title_english'),
                    author=author,
                    author_chinese=meta.get('author_chinese'),
                    author_english=meta.get('author_english'),
                    volume=meta.get('volume'),
                    file_path=str(json_file),
                    chapter_count=len(chapters)
                )

                # Apply search filter if provided
                if search:
                    search_lower = search.lower()
                    if not any([
                        search_lower in title.lower() if title else False,
                        search_lower in author.lower() if author else False,
                        search_lower in summary.work_number.lower() if summary.work_number else False,
                    ]):
                        continue

                works.append(summary)

            except Exception as e:
                print(f"Error loading {json_file}: {e}")
                continue

    # Sort works by directory_name (wuxia number like wuxia_0001) and volume
    def sort_key(work: WorkSummary):
        # Primary sort: directory_name (wuxia_0001, wuxia_0002, etc.)
        dir_name = work.directory_name or "ZZZZZ"  # Put None at end

        # Secondary sort: volume (handle None and convert to sortable value)
        volume = work.volume or ""

        return (dir_name, volume)

    works.sort(key=sort_key)

    return works


@router.get("/works", response_model=List[WorkSummary])
async def list_works(
    search: Optional[str] = Query(None, description="Search by title, author, or work number")
):
    """
    List all available works with optional filtering

    Query Parameters:
        search: Optional search string to filter results

    Returns:
        List of work summaries
    """
    works = scan_works(search=search)
    return works


@router.get("/works/{work_id:path}", response_model=Book)
async def get_work(work_id: str):
    """
    Get detailed information for a specific work

    Path Parameters:
        work_id: The work identifier (folder_name/filename.json)

    Returns:
        Complete book data including structure and content
    """
    # Construct full path
    file_path = Path(CLEANED_JSON_DIR) / work_id

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Work not found: {work_id}")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Parse into Book model (this will validate the structure)
        book = Book(**data)
        return book

    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Invalid JSON in file: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error loading work: {str(e)}"
        )
