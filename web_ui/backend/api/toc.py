"""
TOC generation API endpoint
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from pydantic import BaseModel
from models import Chapter, SectionType

router = APIRouter()


class TOCRegenerateRequest(BaseModel):
    """Request to regenerate TOC from chapters"""
    chapters: List[Chapter]


class TOCEntry(BaseModel):
    """TOC entry"""
    id: str
    title: str
    full_title: str
    chapter_title: str
    chapter_number: int
    chapter_id: str


@router.post("/toc/regenerate")
async def regenerate_toc(request: TOCRegenerateRequest):
    """
    Regenerate TOC from chapter list

    Request Body:
        chapters: List of chapters with section_type

    Returns:
        Regenerated TOC structure organized by section
    """
    try:
        toc_entries = []

        # Group chapters by section type
        sections = {
            SectionType.FRONT_MATTER: [],
            SectionType.BODY: [],
            SectionType.BACK_MATTER: []
        }

        for chapter in request.chapters:
            sections[chapter.section_type].append(chapter)

        # Generate TOC entries for body chapters (main content)
        chapter_number = 1
        for chapter in sections[SectionType.BODY]:
            entry = TOCEntry(
                id=f"toc_{chapter.id}",
                title=chapter.title,
                full_title=chapter.title,
                chapter_title=chapter.title,
                chapter_number=chapter_number,
                chapter_id=chapter.id
            )
            toc_entries.append(entry)
            chapter_number += 1

        return {
            "entries": [entry.dict() for entry in toc_entries],
            "sections": {
                "front_matter": [ch.dict() for ch in sections[SectionType.FRONT_MATTER]],
                "body": [ch.dict() for ch in sections[SectionType.BODY]],
                "back_matter": [ch.dict() for ch in sections[SectionType.BACK_MATTER]]
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"TOC regeneration failed: {str(e)}"
        )
