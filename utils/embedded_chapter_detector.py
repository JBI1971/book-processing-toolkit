#!/usr/bin/env python3
"""
Embedded Chapter Detector - Detects and extracts chapters embedded in introduction sections.

This module handles the common pattern where the FIRST CHAPTER OF A VOLUME
is embedded in the title page/introduction section.

IMPORTANT: This applies to ANY volume, not just Volume 1:
- Volume 1: First chapter (e.g., "一、...") may be embedded
- Volume 2: First chapter (e.g., "一、..." if reset, or "廿一、..." if continuing)
- Volume 3: First chapter (e.g., "卅一、...", "卌一、...", or "一、..." if reset)

Chapter numbering varies:
- Some works reset to Chapter 1 per volume
- Some works continue numbering across volumes (Vol 1: 1-20, Vol 2: 21-40, etc.)
- Some works have irregular numbering (Vol 3 might start at 31, not 41)

The detector finds ANY Chinese chapter marker (一、二、三... 廿、卅、卌...)
and extracts the first one found, regardless of the specific number.

For multi-volume works, process EACH volume file separately.
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)


def parse_chinese_number(text: str) -> Optional[int]:
    """Parse Chinese numerals including special cases."""
    chinese_nums = {
        '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
        '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
        '廿': 20, '卅': 30, '卌': 40, '百': 100, '千': 1000
    }

    # Handle special patterns
    if '廿' in text:
        base = 20
        remainder_match = re.search(r'廿([一二三四五六七八九])', text)
        if remainder_match:
            return base + chinese_nums.get(remainder_match.group(1), 0)
        return base

    if '卅' in text:
        base = 30
        remainder_match = re.search(r'卅([一二三四五六七八九])', text)
        if remainder_match:
            return base + chinese_nums.get(remainder_match.group(1), 0)
        return base

    if '卌' in text:
        base = 40
        remainder_match = re.search(r'卌([一二三四五六七八九])', text)
        if remainder_match:
            return base + chinese_nums.get(remainder_match.group(1), 0)
        return base

    # Handle 十X pattern (10+)
    ten_match = re.search(r'十([一二三四五六七八九])', text)
    if ten_match:
        return 10 + chinese_nums.get(ten_match.group(1), 0)

    # Handle two-digit format (e.g., 二一 = 21)
    if len(text) >= 2:
        first_char = text[0]
        second_char = text[1]
        if (first_char in chinese_nums and second_char in chinese_nums and
            chinese_nums[first_char] <= 9 and chinese_nums[second_char] <= 9):
            return chinese_nums[first_char] * 10 + chinese_nums[second_char]

    # Simple lookup
    for char in text:
        if char in chinese_nums:
            return chinese_nums[char]

    return None


def extract_chapter_title_and_number(content: str) -> Tuple[Optional[int], Optional[str]]:
    """
    Extract chapter number and title from content.

    Supports multiple patterns:
    - 一、弱齡習武，志訪絕學 (simplified format)
    - 第一章　標題 (standard format)
    - 第廿一回　標題 (hui format with special numerals)

    Returns:
        (chapter_number, full_title) or (None, None)
    """
    # Pattern 1: Simplified format (一、標題)
    pattern_simple = r'^([一二三四五六七八九十廿卅卌百千]+)、(.+)$'
    match = re.match(pattern_simple, content.strip())

    if match:
        chinese_num = match.group(1)
        title_part = match.group(2)
        chapter_num = parse_chinese_number(chinese_num)
        full_title = content.strip()
        return (chapter_num, full_title)

    # Pattern 2: Standard format (第N章/回　標題)
    pattern_standard = r'^第([一二三四五六七八九十廿卅卌百千]+)[章回][\s　]+(.+)$'
    match = re.match(pattern_standard, content.strip())

    if match:
        chinese_num = match.group(1)
        title_part = match.group(2)
        chapter_num = parse_chinese_number(chinese_num)
        full_title = content.strip()
        return (chapter_num, full_title)

    return (None, None)


class EmbeddedChapterDetector:
    """Detects and extracts chapters embedded in introduction sections."""

    def __init__(self):
        # Patterns for intro section locations
        self.intro_locations = [
            ('front_matter', 'introduction'),
            ('front_matter', 'sections'),
            ('front_matter', 'toc')
        ]

    def find_embedded_chapter(self, intro_section: Dict[str, Any]) -> Optional[int]:
        """
        Find the block index where a chapter starts in the introduction section.

        This detects ANY chapter marker (一、二、三... 廿、卅、卌... etc.)
        not just Chapter 1, making it work for any volume.

        Returns:
            Block index where chapter title is found, or None
        """
        if not intro_section or 'content_blocks' not in intro_section:
            return None

        content_blocks = intro_section['content_blocks']

        for i, block in enumerate(content_blocks):
            content = block.get('content', '').strip()
            chapter_num, _ = extract_chapter_title_and_number(content)

            # Return on FIRST chapter marker found (any number)
            if chapter_num is not None:
                logger.info(f"Found embedded chapter {chapter_num} at block index {i}")
                return i

        return None

    def detect_and_extract(self, data: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
        """
        Detect and extract embedded chapter from introduction section.

        This is the main entry point for the detector.

        Args:
            data: Cleaned book JSON structure

        Returns:
            (modified_data, was_modified) tuple
        """
        # Find introduction section
        intro_section, intro_location = self._find_intro_section(data)

        if not intro_section:
            logger.debug("No introduction section found")
            return (data, False)

        # Find where chapter starts
        chapter_start_idx = self.find_embedded_chapter(intro_section)

        if chapter_start_idx is None:
            logger.debug("No embedded chapter found in introduction")
            return (data, False)

        logger.info(f"Found embedded chapter at block index {chapter_start_idx}")

        # Extract and reorganize
        modified_data = self._extract_chapter_from_intro(
            data, intro_section, intro_location, chapter_start_idx
        )

        return (modified_data, True)

    def _find_intro_section(self, data: Dict[str, Any]) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Find introduction section in data structure.

        Checks multiple possible locations:
        - structure.front_matter.introduction
        - structure.front_matter.sections (type='introduction')
        - structure.front_matter.toc (type='introduction')

        Returns:
            (intro_section, location_key) or (None, None)
        """
        # Try front_matter.introduction
        intro_sections = data.get('structure', {}).get('front_matter', {}).get('introduction', [])
        if intro_sections:
            intro = intro_sections[0] if isinstance(intro_sections, list) else intro_sections
            return (intro, 'introduction')

        # Try front_matter.sections array
        sections_array = data.get('structure', {}).get('front_matter', {}).get('sections', [])
        if isinstance(sections_array, list):
            for section in sections_array:
                if section.get('type') == 'introduction':
                    return (section, 'sections')

        # Try front_matter.toc array
        toc_array = data.get('structure', {}).get('front_matter', {}).get('toc', [])
        if isinstance(toc_array, list):
            for item in toc_array:
                if item.get('type') == 'introduction':
                    return (item, 'toc')

        return (None, None)

    def _extract_chapter_from_intro(
        self,
        data: Dict[str, Any],
        intro_section: Dict[str, Any],
        intro_location: str,
        chapter_start_idx: int
    ) -> Dict[str, Any]:
        """
        Extract chapter blocks from intro and reorganize structure.

        Steps:
        1. Split intro content_blocks at chapter_start_idx
        2. Create new chapter from extracted blocks
        3. Update intro section (remove chapter blocks)
        4. Insert new chapter at beginning of body.chapters
        5. Renumber all subsequent chapters
        6. Update TOC entries

        Args:
            data: Book structure
            intro_section: Introduction section containing embedded chapter
            intro_location: Where intro was found ('introduction', 'sections', 'toc')
            chapter_start_idx: Block index where chapter starts

        Returns:
            Modified book structure
        """
        content_blocks = intro_section['content_blocks']
        chapter_blocks = content_blocks[chapter_start_idx:]
        intro_blocks = content_blocks[:chapter_start_idx]

        # Get chapter title and number
        chapter_title_block = chapter_blocks[0]
        chapter_title = chapter_title_block.get('content', '').strip()
        chapter_num, chapter_full_title = extract_chapter_title_and_number(chapter_title)

        if chapter_num is None:
            logger.warning(f"Could not parse chapter number from: {chapter_title}")
            chapter_num = 1
            chapter_full_title = chapter_title

        logger.info(f"Extracting chapter {chapter_num}: {chapter_full_title}")
        logger.info(f"  - Chapter blocks: {len(chapter_blocks)}")
        logger.info(f"  - Remaining intro blocks: {len(intro_blocks)}")

        # Renumber chapter blocks
        renumbered_chapter_blocks = []
        for i, block in enumerate(chapter_blocks):
            new_block = block.copy()
            new_block['id'] = f"block_{i:04d}"
            renumbered_chapter_blocks.append(new_block)

        # Create new chapter
        new_chapter = {
            "id": f"chapter_{chapter_num:04d}",
            "title": chapter_full_title,
            "ordinal": chapter_num,
            "content_blocks": renumbered_chapter_blocks,
            "metadata": {
                "source": "extracted_from_intro",
                "extraction_info": f"Extracted from {intro_location} at block {chapter_start_idx}"
            }
        }

        # Update introduction section
        if intro_blocks:
            intro_section['content_blocks'] = intro_blocks
        else:
            # Remove empty introduction
            self._remove_intro_section(data, intro_location, intro_section)

        # Get existing chapters
        existing_chapters = data.get('structure', {}).get('body', {}).get('chapters', [])

        # Determine if we need to renumber existing chapters
        # If the extracted chapter number is LESS than the first existing chapter,
        # we insert it at the beginning and renumber
        # Otherwise, we insert it in the correct position
        if existing_chapters and chapter_num < existing_chapters[0].get('ordinal', 999):
            # Insert at beginning and renumber all
            logger.info(f"Inserting chapter {chapter_num} at beginning, renumbering existing chapters")
            renumbered_chapters = []
            for i, chapter in enumerate(existing_chapters, start=chapter_num + 1):
                new_ch = chapter.copy()
                new_ch['id'] = f"chapter_{i:04d}"
                new_ch['ordinal'] = i
                renumbered_chapters.append(new_ch)

            all_chapters = [new_chapter] + renumbered_chapters
        else:
            # Just insert in correct position without renumbering
            logger.info(f"Inserting chapter {chapter_num} in correct position")
            all_chapters = [new_chapter] + existing_chapters

        # Update body
        data['structure']['body']['chapters'] = all_chapters

        # Update TOC
        self._update_toc(data, new_chapter, existing_chapters)

        logger.info(f"Created {len(all_chapters)} chapters total")

        return data

    def _remove_intro_section(self, data: Dict[str, Any], location: str, intro_section: Dict):
        """Remove empty introduction section from data."""
        if location == 'introduction':
            data['structure']['front_matter']['introduction'] = []
        elif location == 'sections':
            sections = data.get('structure', {}).get('front_matter', {}).get('sections', [])
            data['structure']['front_matter']['sections'] = [
                s for s in sections if s.get('id') != intro_section.get('id')
            ]
        elif location == 'toc':
            toc = data.get('structure', {}).get('front_matter', {}).get('toc', [])
            data['structure']['front_matter']['toc'] = [
                t for t in toc if t.get('id') != intro_section.get('id')
            ]

    def _update_toc(
        self,
        data: Dict[str, Any],
        new_chapter: Dict[str, Any],
        existing_chapters: List[Dict[str, Any]]
    ):
        """Update TOC to include extracted chapter."""
        toc_section = data.get('structure', {}).get('front_matter', {}).get('toc', [])

        if not toc_section:
            logger.debug("No TOC to update")
            return

        # Handle nested TOC structure
        toc = toc_section[0] if isinstance(toc_section, list) else toc_section

        if 'entries' not in toc:
            logger.debug("TOC has no entries array")
            return

        # Create new TOC entry for extracted chapter
        new_toc_entry = {
            "full_title": new_chapter['title'],
            "chapter_title": new_chapter['title'],
            "chapter_number": new_chapter['ordinal'],
            "chapter_id": new_chapter['id']
        }

        # Get existing entries
        existing_entries = toc.get('entries', [])

        # Determine insertion logic
        chapter_num = new_chapter['ordinal']
        if existing_entries and chapter_num < existing_entries[0].get('chapter_number', 999):
            # Renumber existing entries
            logger.info("Renumbering TOC entries")
            updated_entries = []
            for i, entry in enumerate(existing_entries, start=chapter_num + 1):
                new_entry = entry.copy()
                new_entry['chapter_number'] = i
                new_entry['chapter_id'] = f"chapter_{i:04d}"
                updated_entries.append(new_entry)

            all_entries = [new_toc_entry] + updated_entries
        else:
            # Just prepend
            all_entries = [new_toc_entry] + existing_entries

        toc['entries'] = all_entries
        logger.info(f"Updated TOC with {len(all_entries)} entries")


def detect_embedded_chapters(data: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    """
    Convenience function to detect and extract embedded chapters.

    This is the main entry point for external callers.

    Args:
        data: Cleaned book JSON structure

    Returns:
        (modified_data, was_modified) tuple
    """
    detector = EmbeddedChapterDetector()
    return detector.detect_and_extract(data)
