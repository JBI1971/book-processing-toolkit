"""
Edit API endpoints - save modifications, reorder chapters, update metadata
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from models import (
    Book,
    ChapterUpdateRequest,
    ReorderRequest,
    SaveRequest,
)

router = APIRouter()

# Get paths from environment or use defaults
CLEANED_JSON_DIR = os.getenv(
    "CLEANED_JSON_DIR",
    "/Users/jacki/project_files/translation_project/01_clean_json"
)
REVIEWED_JSON_DIR = os.getenv(
    "REVIEWED_JSON_DIR",
    "/Users/jacki/project_files/translation_project/02_reviewed_json"
)


def add_edit_history_entry(book: Book, action: str, details: Dict[str, Any]) -> None:
    """
    Add an entry to the book's edit history

    Args:
        book: The book object to update
        action: The type of action performed
        details: Additional details about the action
    """
    if not hasattr(book, 'edit_history') or book.edit_history is None:
        book.edit_history = []

    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "action": action,
        **details
    }
    book.edit_history.append(entry)


@router.put("/works/{work_id:path}/chapters/{chapter_id}")
async def update_chapter(work_id: str, chapter_id: str, update: ChapterUpdateRequest):
    """
    Update chapter metadata (section type, special type, ordinal)

    Path Parameters:
        work_id: The work identifier (folder_name/filename.json)
        chapter_id: The chapter identifier

    Request Body:
        section_type: Optional new section type
        special_type: Optional new special type
        ordinal: Optional new ordinal

    Returns:
        Updated chapter data
    """
    # Load the work
    file_path = Path(CLEANED_JSON_DIR) / work_id

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Work not found: {work_id}")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        book = Book(**data)

        # Find the chapter
        chapter_found = False
        for chapter in book.structure.body.get('chapters', []):
            if chapter.id == chapter_id:
                # Update fields if provided
                if update.section_type is not None:
                    chapter.section_type = update.section_type
                if update.special_type is not None:
                    chapter.special_type = update.special_type
                if update.ordinal is not None:
                    chapter.ordinal = update.ordinal

                chapter_found = True

                # Add to edit history
                add_edit_history_entry(book, "update_chapter", {
                    "chapter_id": chapter_id,
                    "updates": update.dict(exclude_none=True)
                })

                break

        if not chapter_found:
            raise HTTPException(status_code=404, detail=f"Chapter not found: {chapter_id}")

        # Save back to file (in-memory update, actual save happens with SaveRequest)
        # For now, return the updated chapter
        updated_chapter = next(c for c in book.structure.body['chapters'] if c.id == chapter_id)
        return updated_chapter

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating chapter: {str(e)}")


@router.post("/works/{work_id:path}/reorder")
async def reorder_chapters(work_id: str, reorder: ReorderRequest):
    """
    Reorder a chapter to a new position

    Path Parameters:
        work_id: The work identifier

    Request Body:
        chapter_id: The chapter to move
        new_position: The new position (0-indexed)

    Returns:
        Success message
    """
    file_path = Path(CLEANED_JSON_DIR) / work_id

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Work not found: {work_id}")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        book = Book(**data)
        chapters = book.structure.body.get('chapters', [])

        # Find the chapter
        chapter_index = next((i for i, c in enumerate(chapters) if c.id == reorder.chapter_id), None)

        if chapter_index is None:
            raise HTTPException(status_code=404, detail=f"Chapter not found: {reorder.chapter_id}")

        if reorder.new_position < 0 or reorder.new_position >= len(chapters):
            raise HTTPException(status_code=400, detail="Invalid new position")

        # Remove and reinsert
        chapter = chapters.pop(chapter_index)
        chapters.insert(reorder.new_position, chapter)

        # Add to edit history
        add_edit_history_entry(book, "reorder_chapter", {
            "chapter_id": reorder.chapter_id,
            "old_position": chapter_index,
            "new_position": reorder.new_position
        })

        return {"message": "Chapter reordered successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reordering chapter: {str(e)}")


@router.post("/works/{work_id:path}/save")
async def save_work(work_id: str, save_request: SaveRequest):
    """
    Save modifications to the reviewed JSON directory

    Path Parameters:
        work_id: The work identifier

    Request Body:
        book: The complete modified book data
        commit_message: Optional message describing the changes

    Returns:
        Path to the saved file
    """
    try:
        # Create reviewed directory structure
        reviewed_dir = Path(REVIEWED_JSON_DIR)
        work_path_parts = Path(work_id).parts

        if len(work_path_parts) < 2:
            raise HTTPException(status_code=400, detail="Invalid work_id format")

        # Create subdirectory for this work
        work_subdir = reviewed_dir / work_path_parts[0]
        work_subdir.mkdir(parents=True, exist_ok=True)

        # Create output filename (replace 'cleaned' with 'reviewed')
        filename = work_path_parts[1].replace('cleaned_', 'reviewed_')
        output_path = work_subdir / filename

        # Add commit message to edit history if provided
        if save_request.commit_message:
            add_edit_history_entry(save_request.book, "save", {
                "commit_message": save_request.commit_message
            })

        # Save the file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(save_request.book.dict(), f, ensure_ascii=False, indent=2)

        return {
            "message": "Work saved successfully",
            "path": str(output_path),
            "work_id": f"{work_path_parts[0]}/{filename}"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving work: {str(e)}")
