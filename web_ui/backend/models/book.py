"""
Pydantic models for book data structures
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from enum import Enum


class SectionType(str, Enum):
    """Section types for book structure"""
    FRONT_MATTER = "front_matter"
    BODY = "body"
    BACK_MATTER = "back_matter"


class SpecialSectionType(str, Enum):
    """Special section types for semantic classification"""
    PREFACE = "preface"
    INTRODUCTION = "introduction"
    PROLOGUE = "prologue"
    MAIN_CHAPTER = "main_chapter"
    EPILOGUE = "epilogue"
    AFTERWORD = "afterword"
    APPENDIX = "appendix"
    AUTHOR_NOTE = "author_note"


class ContentBlock(BaseModel):
    """Individual content block within a chapter"""
    id: str
    type: str
    content: str
    epub_id: Optional[str] = None


class TOCEntry(BaseModel):
    """Table of Contents entry"""
    id: str
    title: str
    full_title: Optional[str] = None
    chapter_title: Optional[str] = None
    chapter_number: Optional[str] = None
    chapter_ref: Optional[str] = None
    ordinal: Optional[int] = None


class Chapter(BaseModel):
    """Chapter data structure"""
    id: str
    title: str
    ordinal: Optional[int] = None
    content_blocks: List[ContentBlock] = []
    section_type: SectionType = SectionType.BODY
    special_type: SpecialSectionType = SpecialSectionType.MAIN_CHAPTER


class BookMeta(BaseModel):
    """Book metadata"""
    title: str
    language: str
    schema_version: str
    source: str
    original_file: str
    work_number: Optional[str] = None
    title_chinese: Optional[str] = None
    title_english: Optional[str] = None
    author: Optional[str] = None
    author_chinese: Optional[str] = None
    author_english: Optional[str] = None
    volume: Optional[str] = None


class TOC(BaseModel):
    """Table of Contents"""
    id: str
    title: str
    title_en: Optional[str] = None
    entries: List[TOCEntry] = []


class BookStructure(BaseModel):
    """Complete book structure"""
    front_matter: Dict[str, Any] = {}
    body: Dict[str, List[Chapter]] = {"chapters": []}
    back_matter: Dict[str, Any] = {}


class Book(BaseModel):
    """Complete book data"""
    meta: BookMeta
    structure: BookStructure
    edit_history: List[Dict[str, Any]] = []


class WorkSummary(BaseModel):
    """Summary information for work listing"""
    work_id: str
    directory_name: str
    work_number: Optional[str] = None
    title: str
    title_chinese: Optional[str] = None
    title_english: Optional[str] = None
    author: Optional[str] = None
    author_chinese: Optional[str] = None
    author_english: Optional[str] = None
    volume: Optional[str] = None
    file_path: str
    chapter_count: int


class TranslateRequest(BaseModel):
    """Translation request"""
    text: str
    source_lang: str = "zh"
    target_lang: str = "en"


class TranslateResponse(BaseModel):
    """Translation response"""
    original: str
    translated: str
    source_lang: str
    target_lang: str


class ChapterUpdateRequest(BaseModel):
    """Request to update chapter metadata"""
    section_type: Optional[SectionType] = None
    special_type: Optional[SpecialSectionType] = None
    ordinal: Optional[int] = None


class ReorderRequest(BaseModel):
    """Request to reorder chapters"""
    chapter_id: str
    new_position: int


class SaveRequest(BaseModel):
    """Request to save modifications"""
    book: Book
    commit_message: Optional[str] = None
