#!/usr/bin/env python3
"""
Extract Missing Chapters - Defensive post-processing utility

Detects and extracts chapters that were missed during initial JSON cleaning.
This handles edge cases where chapter content is embedded in title pages or
other sections without explicit chapter headings.

Workflow:
1. Detect missing chapters by analyzing ordinal sequences
2. Search source JSON for the missing chapter content
3. Extract and insert the missing chapter into cleaned JSON

Use cases:
- Simplified chapter markers (一　標題) missed by cleaner
- Content embedded in title pages without clear separation
- Non-standard chapter formats

This is a defensive layer that runs after JSON cleaning and chapter alignment.
"""

import json
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class MissingChapterInfo:
    """Information about a missing chapter"""
    chapter_number: int
    expected_ordinal: int
    found_in_source: bool = False
    source_chapter_idx: Optional[int] = None
    extracted_title: Optional[str] = None
    extracted_blocks: Optional[List[Dict[str, Any]]] = None
    extraction_method: str = "unknown"  # "title_scan", "content_scan", "split_section"


class MissingChapterExtractor:
    """Extract chapters that were missed during initial cleaning"""

    # Chapter patterns (simplified and standard)
    CHAPTER_PATTERNS = [
        # Standard format
        r'第([一二三四五六七八九十廿卅卌百千]+)[回章][\s　]+(.{2,50})',
        # Simplified format (just numeral + title)
        r'^([一二三四五六七八九十廿卅卌百千]+)[\s　]+(.{2,50})',
    ]

    # Chinese numeral map
    CHINESE_NUMERALS = {
        '零': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
        '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
        '廿': 20, '卅': 30, '卌': 40, '百': 100, '千': 1000
    }

    def __init__(self):
        self.missing_chapters = []
        self.extracted_count = 0

    def parse_chinese_number(self, text: str) -> Optional[int]:
        """Parse Chinese numerals to integers"""
        if not text:
            return None

        # Handle special cases
        if '十' in text and len(text) == 1:
            return 10

        # Handle 廿/卅/卌 + single digit (e.g., 廿一 = 21)
        if text[0] in ['廿', '卅', '卌'] and len(text) == 2:
            base = self.CHINESE_NUMERALS[text[0]]
            if text[1] in self.CHINESE_NUMERALS:
                return base + self.CHINESE_NUMERALS[text[1]]

        # Handle 十N (e.g., 十一 = 11)
        if text.startswith('十') and len(text) == 2:
            if text[1] in self.CHINESE_NUMERALS:
                return 10 + self.CHINESE_NUMERALS[text[1]]

        # Handle N十 (e.g., 二十 = 20)
        if '十' in text and len(text) == 2:
            tens = self.CHINESE_NUMERALS.get(text[0], 0)
            return tens * 10

        # Handle N十M (e.g., 二十三 = 23)
        if '十' in text and len(text) == 3:
            tens = self.CHINESE_NUMERALS.get(text[0], 0)
            ones = self.CHINESE_NUMERALS.get(text[2], 0)
            return tens * 10 + ones

        # Single character
        return self.CHINESE_NUMERALS.get(text)

    def detect_missing_chapters(self, cleaned_data: Dict[str, Any]) -> List[int]:
        """
        Detect missing chapters by analyzing ordinal sequence.

        Returns:
            List of missing chapter numbers (e.g., [1] if book starts at chapter 2)
        """
        chapters = cleaned_data.get('structure', {}).get('body', {}).get('chapters', [])

        if not chapters:
            return []

        # Extract ordinals
        ordinals = []
        for ch in chapters:
            ordinal = ch.get('ordinal')
            if ordinal is not None:
                ordinals.append(ordinal)

        if not ordinals:
            return []

        ordinals.sort()
        min_ordinal = ordinals[0]
        max_ordinal = ordinals[-1]

        # Find gaps in sequence
        expected = set(range(min_ordinal, max_ordinal + 1))
        actual = set(ordinals)
        missing = sorted(expected - actual)

        # Also check if sequence starts above 1 (missing early chapters)
        if min_ordinal > 1:
            missing.extend(range(1, min_ordinal))
            missing = sorted(set(missing))

        logger.info(f"Ordinal sequence: {min_ordinal}-{max_ordinal}")
        logger.info(f"Missing ordinals: {missing if missing else 'None'}")

        return missing

    def search_source_for_chapter(
        self,
        source_data: Dict[str, Any],
        chapter_number: int
    ) -> Optional[MissingChapterInfo]:
        """
        Search source JSON for a specific chapter number.

        Strategies:
        1. Scan chapter titles for matching numbers
        2. Scan content within chapters for embedded headings
        3. Check front_matter sections for title pages with embedded content
        """
        info = MissingChapterInfo(
            chapter_number=chapter_number,
            expected_ordinal=chapter_number
        )

        # Strategy 1: Scan source chapter titles
        source_chapters = source_data.get('chapters', [])
        for idx, chapter in enumerate(source_chapters):
            title = chapter.get('title', '')

            # Check if title contains our chapter number
            for pattern in self.CHAPTER_PATTERNS:
                match = re.search(pattern, title, re.MULTILINE)
                if match:
                    num_str = match.group(1)
                    num = self.parse_chinese_number(num_str)

                    if num == chapter_number:
                        info.found_in_source = True
                        info.source_chapter_idx = idx
                        info.extracted_title = title
                        info.extraction_method = "title_scan"
                        logger.info(f"  Found ch {chapter_number} in source chapter {idx}: {title[:50]}")
                        return info

            # Strategy 2: Scan content for embedded headings
            content = chapter.get('content', [])
            if isinstance(content, list):
                embedded_result = self._scan_content_for_chapter(content, chapter_number)
                if embedded_result:
                    info.found_in_source = True
                    info.source_chapter_idx = idx
                    info.extracted_title = embedded_result['title']
                    info.extracted_blocks = embedded_result['blocks']
                    info.extraction_method = "content_scan"
                    logger.info(f"  Found ch {chapter_number} embedded in source chapter {idx}")
                    return info

        return info if info.found_in_source else None

    def _scan_content_for_chapter(
        self,
        content: List[Any],
        chapter_number: int
    ) -> Optional[Dict[str, Any]]:
        """
        Scan content nodes for embedded chapter heading.

        Returns:
            Dict with 'title' and 'blocks' if found, None otherwise
        """
        for node_idx, node in enumerate(content):
            if isinstance(node, dict):
                # Extract text from node
                node_content = node.get('content', '')
                if isinstance(node_content, str):
                    text = node_content
                else:
                    text = self._extract_text_from_node(node)

                # Check against patterns
                for pattern in self.CHAPTER_PATTERNS:
                    match = re.search(pattern, text, re.MULTILINE)
                    if match:
                        num_str = match.group(1)
                        num = self.parse_chinese_number(num_str)

                        if num == chapter_number:
                            # Found the chapter heading - extract from this point
                            title = match.group(0).strip()

                            # Extract remaining content as blocks
                            remaining_nodes = content[node_idx:]

                            return {
                                'title': title,
                                'blocks': remaining_nodes,
                                'start_idx': node_idx
                            }

        return None

    def _extract_text_from_node(self, node: Dict[str, Any]) -> str:
        """Extract all text from a structured node"""
        if isinstance(node, str):
            return node

        content = node.get('content', '')
        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            texts = []
            for item in content:
                if isinstance(item, str):
                    texts.append(item)
                elif isinstance(item, dict):
                    texts.append(self._extract_text_from_node(item))
            return ' '.join(texts)

        return ''

    def extract_and_insert_chapter(
        self,
        cleaned_data: Dict[str, Any],
        source_data: Dict[str, Any],
        chapter_info: MissingChapterInfo
    ) -> bool:
        """
        Extract missing chapter from source and insert into cleaned data.

        Returns:
            True if extraction and insertion successful, False otherwise
        """
        if not chapter_info.found_in_source:
            return False

        # Get source chapter content
        source_chapters = source_data.get('chapters', [])
        if chapter_info.source_chapter_idx >= len(source_chapters):
            return False

        source_chapter = source_chapters[chapter_info.source_chapter_idx]

        # Import block extraction function
        try:
            from processors.json_cleaner import extract_blocks_from_nodes
        except ImportError:
            # Try relative import from parent directory
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from processors.json_cleaner import extract_blocks_from_nodes

        # If extracted_blocks is set, use those (embedded chapter case)
        if chapter_info.extracted_blocks:
            content_blocks = extract_blocks_from_nodes(
                chapter_info.extracted_blocks,
                start_id=0,
                context=f"chapter_{chapter_info.chapter_number}"
            )

            new_chapter = {
                "id": f"chapter_{chapter_info.chapter_number:04d}",
                "title": chapter_info.extracted_title,
                "title_en": "",
                "ordinal": chapter_info.expected_ordinal,
                "content_blocks": content_blocks
            }

            logger.info(f"  Extracted {len(content_blocks)} blocks for chapter {chapter_info.chapter_number}")

        else:
            # Use entire source chapter content
            content = source_chapter.get('content', [])

            content_blocks = extract_blocks_from_nodes(
                content if isinstance(content, list) else [content],
                start_id=0,
                context=f"chapter_{chapter_info.chapter_number}"
            )

            new_chapter = {
                "id": f"chapter_{chapter_info.chapter_number:04d}",
                "title": chapter_info.extracted_title,
                "title_en": "",
                "ordinal": chapter_info.expected_ordinal,
                "content_blocks": content_blocks
            }

            logger.info(f"  Extracted {len(content_blocks)} blocks for chapter {chapter_info.chapter_number}")

        # Insert into cleaned data at correct position
        chapters = cleaned_data['structure']['body']['chapters']

        # Find insertion point (before first chapter with higher ordinal)
        insert_idx = 0
        for idx, ch in enumerate(chapters):
            if ch.get('ordinal', 999) > chapter_info.expected_ordinal:
                insert_idx = idx
                break
        else:
            insert_idx = len(chapters)

        chapters.insert(insert_idx, new_chapter)

        self.extracted_count += 1
        logger.info(f"✓ Inserted chapter {chapter_info.chapter_number} at position {insert_idx}")

        return True

    def process_file(
        self,
        cleaned_path: str,
        source_path: str,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a cleaned JSON file to extract missing chapters from source.

        Args:
            cleaned_path: Path to cleaned JSON file
            source_path: Path to original source JSON file
            output_path: Path to save updated file (defaults to cleaned_path)

        Returns:
            Updated cleaned data with missing chapters inserted
        """
        logger.info(f"Processing: {Path(cleaned_path).name}")

        # Load files
        with open(cleaned_path, 'r', encoding='utf-8') as f:
            cleaned_data = json.load(f)

        with open(source_path, 'r', encoding='utf-8') as f:
            source_data = json.load(f)

        # Detect missing chapters
        missing_numbers = self.detect_missing_chapters(cleaned_data)

        if not missing_numbers:
            logger.info("No missing chapters detected")
            return cleaned_data

        logger.info(f"Attempting to extract {len(missing_numbers)} missing chapters: {missing_numbers}")

        # Extract each missing chapter
        for chapter_num in missing_numbers:
            logger.info(f"\nSearching for chapter {chapter_num}...")

            chapter_info = self.search_source_for_chapter(source_data, chapter_num)

            if chapter_info and chapter_info.found_in_source:
                success = self.extract_and_insert_chapter(
                    cleaned_data,
                    source_data,
                    chapter_info
                )

                if success:
                    self.missing_chapters.append(chapter_info)
            else:
                logger.warning(f"  Could not find chapter {chapter_num} in source")

        # Save updated file
        if self.extracted_count > 0:
            output = output_path or cleaned_path

            with open(output, 'w', encoding='utf-8') as f:
                json.dump(cleaned_data, f, ensure_ascii=False, indent=2)

            logger.info(f"\n✓ Extracted and inserted {self.extracted_count} chapters")
            logger.info(f"✓ Updated file saved to: {output}")
        else:
            logger.info("\nNo chapters were extracted")

        return cleaned_data


def main():
    """CLI entry point"""
    if len(sys.argv) < 3:
        print("Usage: extract_missing_chapters.py <cleaned_json> <source_json> [output_json]")
        print("\nExtract chapters that were missed during initial JSON cleaning.")
        print("\nArguments:")
        print("  cleaned_json - Path to cleaned JSON file")
        print("  source_json  - Path to original source JSON file")
        print("  output_json  - Optional: Path to save updated file (defaults to cleaned_json)")
        sys.exit(1)

    cleaned_path = sys.argv[1]
    source_path = sys.argv[2]
    output_path = sys.argv[3] if len(sys.argv) > 3 else None

    extractor = MissingChapterExtractor()
    extractor.process_file(cleaned_path, source_path, output_path)


if __name__ == '__main__':
    main()
