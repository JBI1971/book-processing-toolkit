#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clean Input JSON - Transform any book JSON into discrete block structure.

Takes a raw book JSON file and transforms it into a clean, structured format
with discrete content blocks suitable for EPUB generation.

This processor includes:
- TOC parsing into structured array with chapter references
- OpenAI-based topology validation to detect metadata vs actual chapters
- Catalog metadata enrichment (work_number, title, author, volume)
- Multi-author format parsing
- Chapter numbering detection and validation
"""

import json
import argparse
import re
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import logging

# OpenAI client for topology validation
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Catalog metadata extractor
import sys
from utils.catalog_metadata import CatalogMetadataExtractor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# =========================
# CONFIG (edit if needed)
# =========================
DEFAULT_INPUT_PATH = "./input/book.json"
DEFAULT_OUTPUT_PATH = "./output/cleaned_book.json"
DEFAULT_LANGUAGE = "zh-Hant"

# Chinese numeral patterns including special cases
CHINESE_NUMERALS = {
    '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
    '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
    '廿': 20, '卅': 30, '卌': 40, '百': 100, '千': 1000
}

# =========================
# Helper Functions
# =========================

def detect_language(text: str) -> str:
    """Detect language from text sample."""
    # Simple heuristic based on character ranges
    if any('\u4e00' <= c <= '\u9fff' for c in text[:100]):
        return "zh-Hant"  # Traditional Chinese (common for wuxia novels)
    return "en"


def parse_chinese_number(text: str) -> Optional[int]:
    """
    Parse Chinese numerals including special cases like 廿 (20), 卅 (30), 卌 (40).

    Examples:
        第一章 -> 1
        第二十章 -> 20
        第廿一章 -> 21
        第卅五章 -> 35
        第二一回 -> 21 (two-digit format: 2*10 + 1)
        第三五回 -> 35 (two-digit format: 3*10 + 5)
    """
    # Extract Chinese numeral pattern
    match = re.search(r'第([一二三四五六七八九十廿卅卌百千]+)[章回]', text)
    if not match:
        return None

    numeral_text = match.group(1)

    # Handle special cases
    if '廿' in numeral_text:
        # 廿 = 20
        base = 20
        remainder = numeral_text.replace('廿', '')
        if remainder:
            for char in remainder:
                if char in CHINESE_NUMERALS:
                    base += CHINESE_NUMERALS[char]
        return base

    if '卅' in numeral_text:
        # 卅 = 30
        base = 30
        remainder = numeral_text.replace('卅', '')
        if remainder:
            for char in remainder:
                if char in CHINESE_NUMERALS:
                    base += CHINESE_NUMERALS[char]
        return base

    if '卌' in numeral_text:
        # 卌 = 40
        base = 40
        remainder = numeral_text.replace('卌', '')
        if remainder:
            for char in remainder:
                if char in CHINESE_NUMERALS:
                    base += CHINESE_NUMERALS[char]
        return base

    # NEW: Handle two-digit format (二一 = 21, 三五 = 35, etc.)
    # This format is used in some books where each digit is written separately
    # Pattern: [一-九][一-九] without 十/百/千 multipliers
    if len(numeral_text) == 2:
        first_char = numeral_text[0]
        second_char = numeral_text[1]

        # Check if both are single digits (1-9)
        if (first_char in CHINESE_NUMERALS and second_char in CHINESE_NUMERALS and
            CHINESE_NUMERALS[first_char] <= 9 and CHINESE_NUMERALS[second_char] <= 9):
            # This is the two-digit format: AB means A*10 + B
            return CHINESE_NUMERALS[first_char] * 10 + CHINESE_NUMERALS[second_char]

    # Standard parsing for other numbers
    result = 0
    temp = 0

    for char in numeral_text:
        if char not in CHINESE_NUMERALS:
            continue

        val = CHINESE_NUMERALS[char]

        if val >= 10:
            if temp == 0:
                temp = 1
            result += temp * val
            temp = 0
        else:
            temp = val

    result += temp
    return result if result > 0 else None


def parse_multi_author(creator: str) -> List[str]:
    """
    Parse multi-author format like "司‧臥‧獨‧諸" into individual names.

    Common formats:
        司‧臥‧獨‧諸 -> [司馬紫煙, 臥龍生, 獨孤紅, 諸葛青雲]
        司馬紫煙／臥龍生／獨孤紅／諸葛青雲 -> [司馬紫煙, 臥龍生, 獨孤紅, 諸葛青雲]
    """
    # Mapping for abbreviated names
    author_map = {
        '司': '司馬紫煙',
        '臥': '臥龍生',
        '獨': '獨孤紅',
        '諸': '諸葛青雲'
    }

    # If already full names separated by ／
    if '／' in creator:
        return [name.strip() for name in creator.split('／') if name.strip()]

    # If abbreviated with ‧ or other separators
    if '‧' in creator or '·' in creator:
        parts = re.split(r'[‧·]', creator)
        authors = []
        for part in parts:
            part = part.strip()
            if part in author_map:
                authors.append(author_map[part])
            elif part:
                authors.append(part)
        return authors

    # Single author
    return [creator.strip()] if creator.strip() else []


def extract_text_from_single_node(node: Dict[str, Any]) -> str:
    """Extract all text from a single node (including nested content)."""
    if isinstance(node, str):
        return node

    content = node.get("content", "")
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        texts = []
        for item in content:
            if isinstance(item, str):
                texts.append(item)
            elif isinstance(item, dict):
                texts.append(extract_text_from_single_node(item))
        return " ".join(texts)

    return ""


def extract_blocks_from_nodes(nodes: List[Any], start_id: int = 0, context: str = "") -> List[Dict[str, Any]]:
    """
    Extract discrete content blocks from structured nodes.
    Each block is a separate element that can be referenced in EPUB.
    """
    blocks = []
    block_id = start_id

    for node in nodes:
        if isinstance(node, str):
            if node.strip():
                blocks.append({
                    "id": f"block_{block_id:04d}",
                    "type": "text",
                    "content": node.strip(),
                    "epub_id": f"text_{block_id}",
                    "metadata": {}
                })
                block_id += 1

        elif isinstance(node, dict):
            tag = node.get("tag", "").lower()
            content = node.get("content", "")

            # Heading elements
            if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                text = extract_text_from_single_node(node)
                if text.strip():
                    blocks.append({
                        "id": f"block_{block_id:04d}",
                        "type": "heading",
                        "content": text.strip(),
                        "epub_id": f"heading_{block_id}",
                        "metadata": {"level": int(tag[1])}
                    })
                    block_id += 1

            # Paragraph elements
            elif tag == "p":
                text = extract_text_from_single_node(node)
                if text.strip():
                    blocks.append({
                        "id": f"block_{block_id:04d}",
                        "type": "paragraph",
                        "content": text.strip(),
                        "epub_id": f"para_{block_id}",
                        "metadata": {}
                    })
                    block_id += 1

            # Division elements - recurse into children
            elif tag in ("div", "section", "article", "body"):
                if isinstance(content, list):
                    nested_blocks = extract_blocks_from_nodes(content, block_id, context)
                    blocks.extend(nested_blocks)
                    block_id += len(nested_blocks)
                elif isinstance(content, str) and content.strip():
                    blocks.append({
                        "id": f"block_{block_id:04d}",
                        "type": "text",
                        "content": content.strip(),
                        "epub_id": f"text_{block_id}",
                        "metadata": {}
                    })
                    block_id += 1

            # List elements
            elif tag in ("ul", "ol"):
                if isinstance(content, list):
                    list_items = extract_blocks_from_nodes(content, block_id, context)
                    if list_items:
                        blocks.append({
                            "id": f"block_{block_id:04d}",
                            "type": f"list_{tag}",
                            "content": list_items,
                            "epub_id": f"list_{block_id}",
                            "metadata": {}
                        })
                        block_id += 1

            elif tag == "li":
                text = extract_text_from_single_node(node)
                if text.strip():
                    blocks.append({
                        "id": f"block_{block_id:04d}",
                        "type": "list_item",
                        "content": text.strip(),
                        "epub_id": f"li_{block_id}",
                        "metadata": {}
                    })
                    block_id += 1

            # Other elements with nested content
            elif isinstance(content, list):
                nested_blocks = extract_blocks_from_nodes(content, block_id, context)
                blocks.extend(nested_blocks)
                block_id += len(nested_blocks)

            elif isinstance(content, str) and content.strip():
                blocks.append({
                    "id": f"block_{block_id:04d}",
                    "type": "text",
                    "content": content.strip(),
                    "epub_id": f"text_{block_id}",
                    "metadata": {"tag": tag}
                })
                block_id += 1

    return blocks


def parse_content_into_blocks(content: Any, chapter_title: str) -> List[Dict[str, Any]]:
    """
    Parse content into discrete blocks (headings, paragraphs, etc.)
    suitable for EPUB generation with proper internal linking.
    """
    blocks = []
    block_id_counter = 0

    if isinstance(content, str):
        # Simple string content - split into paragraphs
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        for para in paragraphs:
            blocks.append({
                "id": f"block_{block_id_counter:04d}",
                "type": "paragraph",
                "content": para,
                "epub_id": f"para_{block_id_counter}",
                "metadata": {}
            })
            block_id_counter += 1

    elif isinstance(content, list):
        # Structured content with HTML-like tags
        blocks = extract_blocks_from_nodes(content, block_id_counter, chapter_title)

    return blocks


def parse_toc_blob_to_array(toc_text: str) -> List[Dict[str, Any]]:
    """
    Parse TOC blob text into structured array with chapter references.

    Input example:
        " 目錄   第一章　神秘的年輕人 第二章　從天而降的救星 ..."

    Output:
        [
            {
                "full_title": "第一章　神秘的年輕人",
                "chapter_title": "神秘的年輕人",
                "chapter_number": 1,
                "chapter_id": "chapter_0001"
            },
            ...
        ]
    """
    toc_entries = []

    # Remove TOC header
    toc_text = re.sub(r'^.*?目[錄录]', '', toc_text, flags=re.MULTILINE)

    # Pattern for chapter entries: 第N章/回　Title
    # Fixed pattern: capture title greedily until next chapter marker, back_matter section, or end
    # This handles TOCs with non-chapter entries like 後記 (afterword) and 附錄 (appendix)
    pattern = r'第([一二三四五六七八九十廿卅卌百千]+)[章回][\s　]*(.*?)(?=第[一二三四五六七八九十廿卅卌百千]+[章回]|後記|後记|附錄|附录|$)'

    matches = re.finditer(pattern, toc_text)

    for match in matches:
        full_match = match.group(0).strip()
        chapter_num = parse_chinese_number(full_match)

        if chapter_num is None:
            continue

        # Extract title directly from capture group (2)
        title = match.group(2).strip()

        toc_entries.append({
            "full_title": full_match,
            "chapter_title": title,
            "chapter_number": chapter_num,
            "chapter_id": f"chapter_{chapter_num:04d}"
        })

    return toc_entries


def extract_text_with_newlines(nodes: List[Any]) -> str:
    """
    Extract text from nodes with newlines between them for pattern matching.
    This ensures ^ anchor in regex matches the start of each node's content.
    """
    texts = []
    for node in nodes:
        if isinstance(node, str):
            if node.strip():
                texts.append(node)
        elif isinstance(node, dict):
            node_text = extract_text_from_single_node(node)
            if node_text.strip():
                texts.append(node_text)
    return "\n".join(texts)


def split_combined_title_and_chapter(content: Any, chapter_title: str) -> List[Dict[str, Any]]:
    """
    Detect and split combined title page + chapter content.

    Common patterns:
    1. Title page with 《書名》作者 followed by 第一回 content
    2. Title page followed by simplified format: 一　玄鐵令

    Returns:
        List of sections: [
            {"type": "title_page", "content": original_format, "title": "..."},
            {"type": "body_chapter", "content": original_format, "title": "第N回　..." or "一　..."}
        ]

    Note: Returns content in original format (str or list) for proper block parsing.
    """
    # Extract full text for pattern matching
    if isinstance(content, str):
        full_text = content
        is_structured = False
    elif isinstance(content, list):
        # Use newline-separated extraction for proper ^ anchor matching
        full_text = extract_text_with_newlines(content)
        is_structured = True
    else:
        full_text = str(content)
        is_structured = False

    # Pattern to find embedded chapter headings
    # Pattern 1: Standard format (第N回/章　標題)
    chapter_pattern_standard = r'第([一二三四五六七八九十廿卅卌百千]+)[章回][\s　]+([^\n]{2,50})'

    # Pattern 2: Simplified format (一　標題, 二　標題, etc.)
    # Only matches at line start to avoid false positives in body text
    chapter_pattern_simplified = r'^([一二三四五六七八九十廿卅卌百千]+)[\s　]+([^\n]{2,50})'

    # Check if content contains title page markers
    has_title_markers = bool(re.search(r'[《》].*?[》]', full_text[:200]))

    # Find all chapter headings in content (try both patterns)
    chapter_matches_standard = list(re.finditer(chapter_pattern_standard, full_text))
    chapter_matches_simplified = list(re.finditer(chapter_pattern_simplified, full_text, re.MULTILINE))

    # Combine matches and sort by position
    chapter_matches = sorted(
        chapter_matches_standard + chapter_matches_simplified,
        key=lambda m: m.start()
    )

    if has_title_markers and chapter_matches:
        # This is a combined title page + chapter
        sections = []

        # Find where the first chapter starts
        first_chapter_match = chapter_matches[0]
        split_text_pos = first_chapter_match.start()

        # If content is structured (list), we need to split it differently
        if is_structured and isinstance(content, list):
            # Split structured content by finding the chapter heading node
            title_page_nodes = []
            chapter_nodes = []
            current_section = title_page_nodes
            found_chapter = False

            for node in content:
                node_text = extract_text_from_single_node(node) if isinstance(node, dict) else str(node)

                # Check if this node contains a chapter heading (either pattern)
                if (re.search(chapter_pattern_standard, node_text) or
                    re.search(chapter_pattern_simplified, node_text, re.MULTILINE)):
                    found_chapter = True
                    current_section = chapter_nodes

                current_section.append(node)

            # Create sections
            if title_page_nodes:
                sections.append({
                    "type": "title_page",
                    "content": title_page_nodes,
                    "title": chapter_title
                })

            if chapter_nodes:
                # Extract chapter title from first node (try both patterns)
                first_text = extract_text_from_single_node(chapter_nodes[0]) if chapter_nodes else ""
                match = re.search(chapter_pattern_standard, first_text)
                if not match:
                    match = re.search(chapter_pattern_simplified, first_text, re.MULTILINE)
                chapter_full_title = match.group(0).strip() if match else "Unknown Chapter"

                sections.append({
                    "type": "body_chapter",
                    "content": chapter_nodes,
                    "title": chapter_full_title
                })

        else:
            # String content - split by text position
            title_page_content = full_text[:split_text_pos].strip()
            if title_page_content:
                sections.append({
                    "type": "title_page",
                    "content": title_page_content,
                    "title": chapter_title
                })

            # Extract each chapter section
            for i, match in enumerate(chapter_matches):
                chapter_full_title = match.group(0).strip()
                chapter_start = match.start()

                # Determine end position
                if i + 1 < len(chapter_matches):
                    chapter_end = chapter_matches[i + 1].start()
                else:
                    chapter_end = len(full_text)

                chapter_content = full_text[chapter_start:chapter_end].strip()

                sections.append({
                    "type": "body_chapter",
                    "content": chapter_content,
                    "title": chapter_full_title
                })

        return sections

    # No split needed
    return []


def classify_chapter_with_ai(title: str, content_preview: str, openai_client) -> Dict[str, Any]:
    """
    Use OpenAI to classify chapter as:
    - book_metadata: Book title, author info, publisher info, etc.
    - front_matter: Preface, introduction, author's note
    - body_chapter: Actual story chapter
    - back_matter: Afterword, appendix

    Returns:
        {
            "classification": "book_metadata" | "front_matter" | "body_chapter" | "back_matter",
            "confidence": 0.0-1.0,
            "reasoning": "explanation"
        }
    """
    if not openai_client:
        # Fallback: enhanced heuristic-based classification

        # Pattern 1: Book title with author (《書名》作者)
        # Enhanced to catch more variants
        if re.search(r'《[^》]+》', title):
            return {
                "classification": "title_page",
                "confidence": 0.95,
                "reasoning": "Title contains book title markers 《》"
            }

        # Pattern 2: Publisher/platform info
        # Enhanced with more publisher keywords
        if re.search(r'好讀書櫃|出版|版權|publishing|haodoo|好讀網站|編輯|排版|製作', title, re.IGNORECASE):
            return {
                "classification": "title_page",
                "confidence": 0.95,
                "reasoning": "Title contains publisher/copyright info"
            }

        # Pattern 3: Standalone author attribution pages
        # Enhanced to catch more formats
        if re.search(r'^[^第]*著$|^作者[:：]|^\S+\s+著\s*$', title):
            return {
                "classification": "title_page",
                "confidence": 0.9,
                "reasoning": "Title is author attribution page"
            }

        # Pattern 4: Short title with metadata-like content
        # New: Detect very short titles (<10 chars) with publication keywords in content
        if len(title.strip()) < 10 and re.search(r'好讀書櫃|出版|版權|haodoo|製作|整理', content_preview):
            return {
                "classification": "title_page",
                "confidence": 0.85,
                "reasoning": "Short title with publication metadata in content"
            }

        # Pattern 5: Front matter keywords (preface, introduction, etc.)
        if re.search(r'^(序|前言|引言|序章|楔子|序幕|導讀|前記)', title):
            return {
                "classification": "front_matter",
                "confidence": 0.9,
                "reasoning": "Title matches front matter keywords"
            }

        # Pattern 6: Back matter keywords
        if re.search(r'^(後記|跋|附錄|尾聲|結語|編後記)', title):
            return {
                "classification": "back_matter",
                "confidence": 0.9,
                "reasoning": "Title matches back matter keywords"
            }

        # Pattern 7: Actual chapter titles (第N章/回)
        if re.search(r'第[一二三四五六七八九十廿卅卌百千]+[章回]', title):
            return {
                "classification": "body_chapter",
                "confidence": 0.95,
                "reasoning": "Title matches chapter pattern 第N章/回"
            }

        # Pattern 8: Check content preview for title page indicators (enhanced)
        if re.search(r'《[^》]+》|好讀書櫃|版權所有|出版|haodoo|整理製作|排版', content_preview):
            return {
                "classification": "title_page",
                "confidence": 0.8,
                "reasoning": "Content preview contains title page markers"
            }

        # Pattern 9: Multi-author format (司‧臥‧獨‧諸 style)
        if re.search(r'[‧·／/]{2,}', title):
            return {
                "classification": "title_page",
                "confidence": 0.85,
                "reasoning": "Title contains multi-author separator patterns"
            }

        return {
            "classification": "body_chapter",
            "confidence": 0.5,
            "reasoning": "Default classification (no clear pattern detected)"
        }

    try:
        prompt = f"""Classify this book section into one of these categories:
- book_metadata: Book title, author, publisher info (e.g., "《龍虎風雲》司馬紫煙／臥龍生／獨孤紅／諸葛青雲")
- front_matter: Preface, introduction, author's note (序, 前言, 引言)
- body_chapter: Main story chapter (第一章, 第二章, etc.)
- back_matter: Afterword, appendix (後記, 跋, 附錄)

Title: {title}
Content preview: {content_preview[:200]}

Respond in JSON format:
{{
    "classification": "book_metadata" | "front_matter" | "body_chapter" | "back_matter",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}}"""

        response = openai_client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {"role": "system", "content": "You are a Chinese literature structure analyst."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)
        return result

    except Exception as e:
        logger.warning(f"AI classification failed: {e}")
        # Fallback to heuristic - USE SAME LOGIC AS PRIMARY FALLBACK

        # Pattern 1: Book title with author (《書名》作者)
        if re.search(r'《[^》]+》', title):
            return {
                "classification": "title_page",
                "confidence": 0.95,
                "reasoning": "Fallback: Title contains book title markers 《》"
            }

        # Pattern 2: Publisher/platform info
        if re.search(r'好讀書櫃|出版|版權|publishing|haodoo|好讀網站|編輯|排版|製作', title, re.IGNORECASE):
            return {
                "classification": "title_page",
                "confidence": 0.95,
                "reasoning": "Fallback: Title contains publisher/copyright info"
            }

        # Pattern 3: Front matter keywords
        if re.search(r'^(序|前言|引言|序章|楔子|序幕|導讀|前記)', title):
            return {
                "classification": "front_matter",
                "confidence": 0.9,
                "reasoning": "Fallback: Title matches front matter keywords"
            }

        # Pattern 4: Back matter keywords - THIS WAS MISSING!
        if re.search(r'^(後記|跋|附錄|尾聲|結語|編後記)', title):
            return {
                "classification": "back_matter",
                "confidence": 0.9,
                "reasoning": "Fallback: Title matches back matter keywords"
            }

        # Pattern 5: Actual chapter titles (第N章/回)
        if re.search(r'第[一二三四五六七八九十廿卅卌百千]+[章回]', title):
            return {
                "classification": "body_chapter",
                "confidence": 0.95,
                "reasoning": "Fallback: Title matches chapter pattern 第N章/回"
            }

        return {
            "classification": "body_chapter",
            "confidence": 0.5,
            "reasoning": "Fallback: default classification"
        }


def detect_toc(chapter: Dict[str, Any], index: int) -> bool:
    """Detect if a chapter is a table of contents."""
    title = chapter.get("title", "").lower()

    # Common TOC indicators
    toc_indicators = ["目錄", "目录", "contents", "table of contents", "toc"]

    # Check title
    if any(indicator in title for indicator in toc_indicators):
        return True

    # Check if it's the first section and has short lines
    if index == 0:
        content = chapter.get("content", "")
        if isinstance(content, str):
            lines = [line.strip() for line in content.split("\n") if line.strip()]
            if len(lines) >= 5:
                short_lines = sum(1 for line in lines if len(line) <= 15)
                if short_lines / len(lines) > 0.7:  # 70% short lines
                    return True

    return False


def clean_book_json(
    input_path: str,
    language_hint: Optional[str] = None,
    catalog_path: Optional[str] = None,
    directory_name: Optional[str] = None,
    use_ai_validation: bool = True
) -> Dict[str, Any]:
    """
    Clean and structure a book JSON file into discrete blocks.

    Args:
        input_path: Path to input JSON file
        language_hint: Optional language hint (zh, zh-Hans, zh-Hant, en, etc.)
        catalog_path: Path to wuxia_catalog.db for metadata enrichment
        directory_name: Directory name for catalog lookup (e.g., 'wuxia_0114')
        use_ai_validation: Use OpenAI for topology validation

    Returns:
        Cleaned book structure with discrete content blocks
    """
    # Initialize OpenAI client if available and requested
    openai_client = None
    if use_ai_validation and OPENAI_AVAILABLE:
        api_key = os.environ.get('OPENAI_API_KEY')
        if api_key:
            openai_client = OpenAI(api_key=api_key)
            logger.info("OpenAI client initialized for topology validation")
        else:
            logger.warning("OPENAI_API_KEY not found, using heuristic validation")

    # Initialize catalog extractor if available
    catalog_extractor = None
    if catalog_path and Path(catalog_path).exists():
        try:
            catalog_extractor = CatalogMetadataExtractor(catalog_path)
            logger.info(f"Catalog extractor initialized: {catalog_path}")
        except Exception as e:
            logger.warning(f"Could not initialize catalog extractor: {e}")

    # Load input
    input_data = json.loads(Path(input_path).read_text(encoding="utf-8"))

    # Extract metadata from source
    source_metadata = input_data.get("metadata", {})
    book_title = source_metadata.get("title", "Untitled")
    book_creator = source_metadata.get("creator", "Unknown")

    # Parse authors from creator field
    authors = parse_multi_author(book_creator)
    author_chinese = "、".join(authors) if authors else "Unknown"

    # Detect language
    if not language_hint:
        sample_text = str(input_data)[:1000]
        language_hint = detect_language(sample_text)

    # Initialize cleaned structure
    cleaned_book = {
        "meta": {
            "title": book_title,
            "language": language_hint,
            "schema_version": "2.0.0",
            "source": "cleaned-input",
            "original_file": str(Path(input_path).name),
            "author_chinese": author_chinese
        },
        "structure": {
            "front_matter": {},
            "body": {
                "chapters": []
            },
            "back_matter": {}
        }
    }

    # Enrich with catalog metadata if available
    if catalog_extractor and directory_name:
        try:
            cleaned_book = catalog_extractor.enrich_json_metadata(cleaned_book, directory_name)
            logger.info(f"Enriched metadata from catalog for {directory_name}")
        except Exception as e:
            logger.warning(f"Could not enrich metadata: {e}")

    # Process chapters
    chapters = input_data.get("chapters", [])
    if not chapters:
        # Try other common field names
        chapters = input_data.get("sections", [])

    # Track actual chapter numbers for proper ordinal assignment
    body_chapters = []
    front_matter_sections = []
    back_matter_sections = []
    toc_parsed = None

    for idx, chapter in enumerate(chapters):
        if not isinstance(chapter, dict):
            continue

        chapter_title = chapter.get("title", f"Chapter {idx + 1}")

        # Check if this is TOC
        if detect_toc(chapter, idx):
            # Parse TOC into structured array
            content = chapter.get("content", "")
            if isinstance(content, list):
                content_text = extract_text_from_single_node({"content": content})
            else:
                content_text = str(content)

            toc_array = parse_toc_blob_to_array(content_text)

            if toc_array:
                # Store in proper nested structure matching restructure_toc.py output format
                cleaned_book["structure"]["front_matter"]["toc"] = [{
                    "id": "toc_0000",
                    "title": "Table of Contents",
                    "title_en": "Table of Contents",
                    "entries": toc_array
                }]
                toc_parsed = True
                logger.info(f"Parsed TOC with {len(toc_array)} entries")
            else:
                # Fallback: store as blob if parsing fails
                cleaned_book["structure"]["front_matter"]["toc"] = [{
                    "id": "toc_0000",
                    "content": content_text
                }]
                logger.warning("TOC parsing failed, stored as blob")

            continue

        # Check if this is a combined title page + chapter
        content = chapter.get("content", "")
        split_sections = split_combined_title_and_chapter(content, chapter_title)

        if split_sections:
            logger.info(f"Split combined page '{chapter_title}' into {len(split_sections)} sections")

            for section in split_sections:
                section_type = section["type"]
                section_content = section["content"]
                section_title = section["title"]

                # Process content into blocks
                content_blocks = parse_content_into_blocks(section_content, section_title)

                if section_type == "title_page":
                    # Add to front_matter
                    front_matter_sections.append({
                        "id": f"title_page_{len(front_matter_sections):04d}",
                        "type": "title_page",
                        "title": section_title,
                        "content_blocks": content_blocks
                    })
                    logger.info(f"  → Title page section: {section_title}")

                elif section_type == "body_chapter":
                    # Extract chapter number
                    chapter_num = parse_chinese_number(section_title)
                    ordinal = chapter_num if chapter_num is not None else len(body_chapters) + 1

                    body_chapters.append({
                        "id": f"chapter_{ordinal:04d}",
                        "title": section_title,
                        "ordinal": ordinal,
                        "content_blocks": content_blocks,
                        "metadata": {
                            "classification": "body_chapter",
                            "confidence": 1.0,
                            "source": "split_from_combined"
                        }
                    })
                    logger.info(f"  → Chapter {ordinal}: {section_title[:40]}")

            continue

        # Standard chapter processing (not combined)
        # Get content preview for AI classification
        if isinstance(content, list):
            content_preview = extract_text_from_single_node({"content": content})[:500]
        else:
            content_preview = str(content)[:500]

        # Classify chapter with AI or heuristics
        classification = classify_chapter_with_ai(chapter_title, content_preview, openai_client)

        logger.debug(f"Chapter '{chapter_title}': {classification['classification']} (confidence: {classification['confidence']:.2f})")

        # Handle title pages / book metadata
        if classification["classification"] in ("book_metadata", "title_page"):
            # Add to front_matter instead of skipping
            content_blocks = parse_content_into_blocks(content, chapter_title)
            front_matter_sections.append({
                "id": f"title_page_{len(front_matter_sections):04d}",
                "type": "title_page",
                "title": chapter_title,
                "content_blocks": content_blocks,
                "metadata": {
                    "classification": classification["classification"],
                    "confidence": classification["confidence"],
                    "reasoning": classification.get("reasoning", "")
                }
            })
            logger.info(f"Added title page to front_matter: {chapter_title}")
            continue

        # Handle front_matter sections (preface, introduction, etc.)
        if classification["classification"] == "front_matter":
            content_blocks = parse_content_into_blocks(content, chapter_title)
            front_matter_sections.append({
                "id": f"front_matter_{len(front_matter_sections):04d}",
                "type": classification["classification"],
                "title": chapter_title,
                "content_blocks": content_blocks,
                "metadata": {
                    "classification": classification["classification"],
                    "confidence": classification["confidence"],
                    "reasoning": classification.get("reasoning", "")
                }
            })
            logger.info(f"Added to front_matter: {chapter_title}")
            continue

        # Handle back_matter sections (afterword, appendix, etc.)
        if classification["classification"] == "back_matter":
            content_blocks = parse_content_into_blocks(content, chapter_title)
            back_matter_sections.append({
                "id": f"back_matter_{len(back_matter_sections):04d}",
                "type": classification["classification"],
                "title": chapter_title,
                "content_blocks": content_blocks,
                "metadata": {
                    "classification": classification["classification"],
                    "confidence": classification["confidence"],
                    "reasoning": classification.get("reasoning", "")
                }
            })
            logger.info(f"Added to back_matter: {chapter_title}")
            continue

        # Process content into blocks
        content_blocks = parse_content_into_blocks(content, chapter_title)

        # Detect chapter number from title
        chapter_num = parse_chinese_number(chapter_title)

        # Determine proper ordinal - use parsed chapter number if available
        # This ensures multi-volume books preserve actual chapter numbers (21, 22, 23...)
        # instead of resetting to sequential (1, 2, 3...)
        if chapter_num is not None:
            ordinal = chapter_num
        else:
            # Fallback: sequential numbering if no chapter number found
            ordinal = len(body_chapters) + 1

        cleaned_chapter = {
            "id": f"chapter_{ordinal:04d}",
            "title": chapter_title,
            "ordinal": ordinal,
            "content_blocks": content_blocks,
            "metadata": {
                "classification": classification["classification"],
                "confidence": classification["confidence"]
            }
        }

        body_chapters.append(cleaned_chapter)

    # Assign body chapters
    cleaned_book["structure"]["body"]["chapters"] = body_chapters

    # Add front_matter sections (title pages, etc.)
    if front_matter_sections:
        cleaned_book["structure"]["front_matter"]["sections"] = front_matter_sections
        logger.info(f"Added {len(front_matter_sections)} front_matter sections")

    # Add back_matter sections (afterword, appendix, etc.)
    if back_matter_sections:
        cleaned_book["structure"]["back_matter"]["sections"] = back_matter_sections
        logger.info(f"Added {len(back_matter_sections)} back_matter sections")

    # Check if TOC needs to be generated or regenerated
    # Regenerate if:
    # 1. No TOC was parsed, OR
    # 2. TOC exists but has fewer entries than body chapters (misalignment from splits)
    toc_entry_count = 0
    if toc_parsed and cleaned_book["structure"]["front_matter"].get("toc"):
        toc_data = cleaned_book["structure"]["front_matter"]["toc"]
        if isinstance(toc_data, list) and len(toc_data) > 0:
            # Check if entries exist
            if isinstance(toc_data[0], dict) and "entries" in toc_data[0]:
                toc_entry_count = len(toc_data[0]["entries"])
            elif isinstance(toc_data[0], dict) and "chapter_number" in toc_data[0]:
                # Old format
                toc_entry_count = len(toc_data)

    should_regenerate = (not toc_parsed) or (toc_entry_count < len(body_chapters))

    logger.debug(f"TOC regeneration check: toc_parsed={toc_parsed}, toc_entry_count={toc_entry_count}, body_chapters={len(body_chapters)}, should_regenerate={should_regenerate}")

    if should_regenerate:
        if not toc_parsed:
            logger.warning("No TOC found, generating from chapter titles")
        else:
            logger.warning(f"TOC has {toc_entry_count} entries but {len(body_chapters)} chapters, regenerating")

        generated_toc_entries = []
        for ch in body_chapters:
            chapter_num = ch["ordinal"]
            title = ch["title"]

            # Match both standard format (第N章/回) and simplified format (N　Title)
            if re.search(r'第[一二三四五六七八九十廿卅卌百千]+[章回]', title):
                # Standard format: 第一章　標題
                generated_toc_entries.append({
                    "full_title": title,
                    "chapter_title": re.sub(r'第[一二三四五六七八九十廿卅卌百千]+[章回][\s　]*', '', title),
                    "chapter_number": chapter_num,
                    "chapter_id": ch["id"]
                })
            elif re.match(r'^[一二三四五六七八九十廿卅卌百千]+[\s　]+', title):
                # Simplified format: 一　標題
                generated_toc_entries.append({
                    "full_title": title,
                    "chapter_title": re.sub(r'^[一二三四五六七八九十廿卅卌百千]+[\s　]+', '', title),
                    "chapter_number": chapter_num,
                    "chapter_id": ch["id"]
                })
            else:
                # No chapter marker, use title as-is
                generated_toc_entries.append({
                    "full_title": title,
                    "chapter_title": title,
                    "chapter_number": chapter_num,
                    "chapter_id": ch["id"]
                })

        if generated_toc_entries:
            # Store in proper nested structure matching restructure_toc.py output format
            cleaned_book["structure"]["front_matter"]["toc"] = [{
                "id": "toc_0000",
                "title": "Table of Contents",
                "title_en": "Table of Contents",
                "entries": generated_toc_entries
            }]
            logger.info(f"Generated TOC with {len(generated_toc_entries)} entries")

    return cleaned_book


def print_summary(cleaned_book: Dict[str, Any]):
    """Print a summary of the cleaned book structure."""
    print("=" * 70)
    print("CLEANED BOOK SUMMARY")
    print("=" * 70)

    meta = cleaned_book["meta"]
    print(f"\n📖 Title: {meta.get('title', 'N/A')}")
    print(f"   Author: {meta.get('author_chinese', 'N/A')}")
    if 'work_number' in meta:
        print(f"   Work Number: {meta['work_number']}")
    if 'volume' in meta:
        print(f"   Volume: {meta['volume']}")
    print(f"   Language: {meta['language']}")
    print(f"   Schema: {meta['schema_version']}")

    structure = cleaned_book["structure"]

    # Front matter
    front = structure.get("front_matter", {})
    if front:
        print(f"\n📑 FRONT MATTER:")
        for key, value in front.items():
            if key == "toc" and isinstance(value, list):
                if value and isinstance(value[0], dict) and "chapter_number" in value[0]:
                    print(f"  - TOC: {len(value)} structured entries")
                    for i, entry in enumerate(value[:3]):
                        print(f"      {i+1}. {entry.get('full_title', 'N/A')}")
                    if len(value) > 3:
                        print(f"      ... and {len(value) - 3} more")
                else:
                    print(f"  - TOC: {len(value)} blob entry")

    # Body
    chapters = structure["body"]["chapters"]
    total_blocks = sum(len(ch.get("content_blocks", [])) for ch in chapters)

    print(f"\n📚 BODY:")
    print(f"  Chapters: {len(chapters)}")
    print(f"  Total content blocks: {total_blocks:,}")
    if chapters:
        print(f"  Average blocks per chapter: {total_blocks/len(chapters):.1f}")

    print(f"\n📊 CHAPTERS:")
    for i, ch in enumerate(chapters[:10], 1):  # Show first 10
        blocks = len(ch.get("content_blocks", []))
        classification = ch.get("metadata", {}).get("classification", "unknown")
        print(f"  {ch['ordinal']:2d}. {ch['title'][:40]:40s} - {blocks:3d} blocks [{classification}]")

    if len(chapters) > 10:
        print(f"  ... and {len(chapters) - 10} more chapters")

    print(f"\n🔗 EPUB READY:")
    print(f"  ✓ Each block has unique ID and EPUB ID")
    print(f"  ✓ Block types: heading, paragraph, text, list")
    print(f"  ✓ TOC with chapter references")
    print(f"  ✓ Metadata enriched from catalog")
    print("=" * 70)


# =========================
# Main
# =========================
def main():
    parser = argparse.ArgumentParser(
        description='Clean book JSON into discrete block structure for EPUB generation'
    )

    parser.add_argument(
        '--input',
        default=DEFAULT_INPUT_PATH,
        help=f'Input book JSON file (default: {DEFAULT_INPUT_PATH})'
    )

    parser.add_argument(
        '--output',
        default=None,
        help=f'Output cleaned JSON file (default: {DEFAULT_OUTPUT_PATH})'
    )

    parser.add_argument(
        '--output-dir',
        default=None,
        help='Base output directory (e.g., /path/to/01_clean_json). '
             'Will create subfolder matching source folder name.'
    )

    parser.add_argument(
        '--language',
        help='Language hint (zh, zh-Hans, zh-Hant, en, etc.)'
    )

    parser.add_argument(
        '--catalog-path',
        help='Path to wuxia_catalog.db for metadata enrichment'
    )

    parser.add_argument(
        '--directory-name',
        help='Directory name for catalog lookup (e.g., wuxia_0114)'
    )

    parser.add_argument(
        '--no-ai-validation',
        action='store_true',
        help='Disable OpenAI topology validation (use heuristics only)'
    )

    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress summary output'
    )

    args = parser.parse_args()

    # Validate input
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ Error: Input file not found: {args.input}")
        return 1

    # Auto-detect directory name if not provided
    directory_name = args.directory_name
    if not directory_name:
        directory_name = input_path.parent.name
        logger.info(f"Auto-detected directory name: {directory_name}")

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    elif args.output_dir:
        # Auto-create output structure: output_dir/source_folder/cleaned_filename.json
        source_folder = input_path.parent.name
        output_filename = f"{input_path.stem}_cleaned.json"
        output_path = Path(args.output_dir) / output_filename
        print(f"📁 Auto-output: {output_filename}")
    else:
        output_path = Path(DEFAULT_OUTPUT_PATH)

    print(f"📖 Loading book from: {args.input}")
    print(f"💾 Will save to: {output_path}")

    # Clean the book
    try:
        cleaned_book = clean_book_json(
            args.input,
            args.language,
            catalog_path=args.catalog_path,
            directory_name=directory_name,
            use_ai_validation=not args.no_ai_validation
        )
    except Exception as e:
        print(f"❌ Error cleaning book: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Save output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        output_path.write_text(
            json.dumps(cleaned_book, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"✓ Cleaned book saved to: {output_path}")
    except Exception as e:
        print(f"❌ Error saving output: {e}")
        return 1

    # Print summary
    if not args.quiet:
        print()
        print_summary(cleaned_book)

    # File size
    import os
    file_size = os.path.getsize(output_path)
    print(f"\n💾 File size: {file_size:,} bytes ({file_size/1024:.1f} KB)")

    return 0


if __name__ == "__main__":
    exit(main())
