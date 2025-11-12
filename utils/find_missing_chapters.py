#!/usr/bin/env python3
"""
Find Missing Chapters - Search for chapters listed in TOC but missing from body

This utility performs comprehensive searches for missing chapters by:
1. Comparing TOC entries to body.chapters
2. Searching all sections (front_matter, body, back_matter) for missing chapter titles
3. Using fuzzy matching to detect slight title variations
4. Reporting whether missing chapters exist elsewhere or are truly missing from source

Example:
    TOC lists: 第一回、第二回、第三回
    Body has: 第二回、第三回

    Missing: 第一回
    Search result: Not found in any section → Actually missing from source EPUB
"""

import json
import re
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from difflib import SequenceMatcher

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class MissingChapter:
    """Information about a missing chapter"""
    chapter_number: int
    toc_title: str
    full_toc_entry: str
    toc_index: int
    found_in: Optional[str] = None  # Section where found (front_matter, back_matter, etc.)
    found_title: Optional[str] = None  # Actual title found
    found_id: Optional[str] = None  # ID of found content
    similarity_score: float = 0.0
    status: str = "missing"  # "missing", "found", "misclassified", "embedded"
    embedded_content_start: Optional[int] = None  # Index where chapter content starts in embedded case
    embedded_content_blocks: Optional[List[Dict[str, Any]]] = None  # Extracted content blocks


@dataclass
class SearchResult:
    """Results of missing chapter search"""
    total_toc_entries: int
    total_body_chapters: int
    missing_count: int
    found_elsewhere_count: int
    truly_missing_count: int
    missing_chapters: List[MissingChapter] = field(default_factory=list)
    summary: str = ""


class MissingChapterFinder:
    """Search for chapters listed in TOC but missing from body"""

    def __init__(self, similarity_threshold: float = 0.6):
        """
        Initialize finder.

        Args:
            similarity_threshold: Minimum similarity score for fuzzy matching (0.0-1.0)
        """
        self.similarity_threshold = similarity_threshold

    def find_missing(self, cleaned_json: Dict[str, Any]) -> SearchResult:
        """
        Find missing chapters in a cleaned JSON structure.

        Args:
            cleaned_json: Cleaned book JSON

        Returns:
            SearchResult with findings
        """
        logger.info("Starting missing chapter search...")

        result = SearchResult(
            total_toc_entries=0,
            total_body_chapters=0,
            missing_count=0,
            found_elsewhere_count=0,
            truly_missing_count=0
        )

        # Extract TOC entries
        toc_data = cleaned_json.get('structure', {}).get('front_matter', {}).get('toc', [])
        toc_entries = self._extract_toc_entries(toc_data)
        result.total_toc_entries = len(toc_entries)

        # Extract body chapters
        body_chapters = cleaned_json.get('structure', {}).get('body', {}).get('chapters', [])
        result.total_body_chapters = len(body_chapters)

        # Build chapter number map from body
        body_chapter_numbers = set()
        for chapter in body_chapters:
            # First try using the ordinal field (most reliable)
            chapter_num = chapter.get('ordinal')
            if not chapter_num:
                # Fall back to extracting from title
                chapter_num = self._extract_chapter_number(chapter.get('title', ''))
            if chapter_num:
                body_chapter_numbers.add(chapter_num)

        # Find missing chapters
        for toc_entry in toc_entries:
            chapter_num = toc_entry.get('chapter_number')
            if chapter_num and chapter_num not in body_chapter_numbers:
                # This chapter is missing from body
                missing = MissingChapter(
                    chapter_number=chapter_num,
                    toc_title=toc_entry.get('chapter_title', ''),
                    full_toc_entry=toc_entry.get('full_title', ''),
                    toc_index=toc_entry.get('toc_index', 0)
                )

                # Search for it elsewhere
                self._search_for_chapter(missing, cleaned_json)

                result.missing_chapters.append(missing)
                result.missing_count += 1

                if missing.status in ["found", "embedded"]:
                    result.found_elsewhere_count += 1
                elif missing.status == "missing":
                    result.truly_missing_count += 1

        # Build summary
        result.summary = self._build_summary(result)

        logger.info(f"Search complete: {result.summary}")

        return result

    def _extract_toc_entries(self, toc_data: Any) -> List[Dict[str, Any]]:
        """Extract TOC entries from front_matter.toc"""
        entries = []

        if not toc_data:
            return entries

        if isinstance(toc_data, list):
            for toc_section in toc_data:
                # Handle nested structure: [{"entries": [...]}]
                if isinstance(toc_section, dict) and 'entries' in toc_section:
                    nested_entries = toc_section.get('entries', [])
                    for idx, entry in enumerate(nested_entries):
                        if isinstance(entry, dict):
                            # Parse chapter number from chapter_number field (Chinese numeral)
                            chapter_num_str = entry.get('chapter_number', '')
                            chapter_num = self._parse_chinese_number(chapter_num_str) if chapter_num_str else None

                            if chapter_num:
                                entries.append({
                                    'toc_index': idx,
                                    'full_title': entry.get('full_title', ''),
                                    'chapter_title': entry.get('chapter_title', ''),
                                    'chapter_number': chapter_num,
                                    'chapter_id': entry.get('chapter_ref', '')
                                })

                # Handle flat structure
                elif isinstance(toc_section, dict) and 'chapter_number' in toc_section:
                    chapter_num = self._extract_chapter_number(toc_section.get('full_title', ''))
                    if chapter_num:
                        entries.append({
                            'toc_index': len(entries),
                            'full_title': toc_section.get('full_title', ''),
                            'chapter_title': toc_section.get('chapter_title', ''),
                            'chapter_number': chapter_num,
                            'chapter_id': toc_section.get('chapter_id', '')
                        })

        return entries

    def _extract_chapter_number(self, text: str) -> Optional[int]:
        """Extract chapter number from text using Chinese numerals"""
        if not text:
            return None

        # Match 第N章/回 pattern
        match = re.search(r'第([一二三四五六七八九十廿卅卌百千]+)[章回]', text)
        if not match:
            return None

        return self._parse_chinese_number(match.group(1))

    def _parse_chinese_number(self, numeral_text: str) -> Optional[int]:
        """Parse Chinese numerals to integers"""
        numerals = {
            '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
            '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
            '廿': 20, '卅': 30, '卌': 40, '百': 100, '千': 1000
        }

        # Handle special cases
        for special, base in [('廿', 20), ('卅', 30), ('卌', 40)]:
            if special in numeral_text:
                remainder = numeral_text.replace(special, '')
                if remainder:
                    for char in remainder:
                        if char in numerals:
                            base += numerals[char]
                return base

        # Standard parsing
        result = 0
        temp = 0

        for char in numeral_text:
            if char not in numerals:
                continue

            val = numerals[char]

            if val >= 10:
                if temp == 0:
                    temp = 1
                result += temp * val
                temp = 0
            else:
                temp = val

        result += temp
        return result if result > 0 else None

    def _extract_embedded_chapter(
        self,
        section: Dict[str, Any],
        missing: MissingChapter
    ) -> bool:
        """
        Detect and extract chapter content embedded in title pages.

        Returns True if embedded content found and extracted.
        """
        content_blocks = section.get('content_blocks', [])
        if not content_blocks:
            return False

        # Indicators of title page: short blocks, metadata, poems
        title_indicators = ['版', '金庸', '《', '》', '趙客縵胡纓', '俠客行']

        # Find where story content likely begins
        story_start_idx = None
        accumulated_text_length = 0

        for idx, block in enumerate(content_blocks):
            block_type = block.get('type', '')
            content = block.get('content', '')

            # Ensure content is a string
            if not isinstance(content, str):
                content = str(content) if content is not None else ''

            # Skip metadata/title blocks
            if any(indicator in content for indicator in title_indicators):
                if len(content) < 100:  # Short metadata blocks
                    continue

            # Look for substantial prose content (>50 chars)
            if block_type in ['text', 'para'] and len(content) > 50:
                accumulated_text_length += len(content)

                # If we've accumulated >200 chars of prose, this is likely story content
                if accumulated_text_length > 200 and story_start_idx is None:
                    story_start_idx = idx

            # Confirm by finding more prose blocks after start
            if story_start_idx is not None and idx > story_start_idx:
                if block_type in ['text', 'para'] and len(content) > 30:
                    # Found embedded chapter content
                    missing.found_in = 'front_matter (embedded)'
                    missing.found_title = section.get('title', '')
                    missing.found_id = section.get('id', '')
                    missing.status = "embedded"
                    missing.embedded_content_start = story_start_idx
                    missing.embedded_content_blocks = content_blocks[story_start_idx:]
                    missing.similarity_score = 1.0  # High confidence

                    logger.info(f"  ✓ Found embedded chapter {missing.chapter_number} in title page")
                    logger.info(f"    Story content starts at block {story_start_idx}")
                    logger.info(f"    Extracted {len(missing.embedded_content_blocks)} content blocks")

                    return True

        return False

    def _search_for_chapter(self, missing: MissingChapter, cleaned_json: Dict[str, Any]):
        """
        Search for missing chapter in all sections.

        Checks:
        1. front_matter sections (title pages, etc.) - including embedded content
        2. body chapters (in case of numbering mismatch)
        3. back_matter sections
        4. Unclassified content
        """
        structure = cleaned_json.get('structure', {})

        # Search patterns
        chapter_pattern = f"第{self._int_to_chinese(missing.chapter_number)}[章回]"
        title_pattern = missing.toc_title

        # Special case: Check for Chapter 1 embedded in title pages
        if missing.chapter_number == 1:
            front_matter = structure.get('front_matter', {})
            sections = front_matter.get('sections', [])

            for section in sections:
                # Look for title page sections (contain book title, metadata)
                section_title = section.get('title', '')
                if any(keyword in section_title for keyword in ['《', '金庸', '上', '下']):
                    if self._extract_embedded_chapter(section, missing):
                        return  # Found and extracted

        # Search front_matter sections (regular search)
        front_matter = structure.get('front_matter', {})
        found = self._search_in_sections(
            front_matter.get('sections', []),
            chapter_pattern,
            title_pattern,
            'front_matter'
        )
        if found:
            missing.found_in, missing.found_title, missing.found_id, missing.similarity_score = found
            missing.status = "found"
            return

        # Search body chapters (in case title doesn't match but content does)
        body_chapters = structure.get('body', {}).get('chapters', [])
        found = self._search_in_chapters(
            body_chapters,
            chapter_pattern,
            title_pattern,
            'body'
        )
        if found:
            missing.found_in, missing.found_title, missing.found_id, missing.similarity_score = found
            missing.status = "misclassified"
            return

        # Search back_matter
        back_matter = structure.get('back_matter', {})
        found = self._search_in_sections(
            back_matter.get('sections', []) if isinstance(back_matter, dict) else [],
            chapter_pattern,
            title_pattern,
            'back_matter'
        )
        if found:
            missing.found_in, missing.found_title, missing.found_id, missing.similarity_score = found
            missing.status = "found"
            return

        # Not found anywhere
        missing.status = "missing"

    def _search_in_sections(
        self,
        sections: List[Dict[str, Any]],
        chapter_pattern: str,
        title_pattern: str,
        section_name: str
    ) -> Optional[Tuple[str, str, str, float]]:
        """Search for chapter in a list of sections"""
        for section in sections:
            section_title = section.get('title', '')
            section_id = section.get('id', '')

            # Check if section title contains chapter number
            if re.search(chapter_pattern, section_title):
                similarity = self._calculate_similarity(title_pattern, section_title)
                return (section_name, section_title, section_id, similarity)

            # Fuzzy match on title
            if title_pattern:
                similarity = self._calculate_similarity(title_pattern, section_title)
                if similarity >= self.similarity_threshold:
                    return (section_name, section_title, section_id, similarity)

            # Search in content_blocks
            content_blocks = section.get('content_blocks', [])
            for block in content_blocks:
                if block.get('type') == 'heading':
                    block_content = block.get('content', '')
                    if re.search(chapter_pattern, block_content):
                        similarity = self._calculate_similarity(title_pattern, block_content)
                        return (section_name, block_content, section_id, similarity)

        return None

    def _search_in_chapters(
        self,
        chapters: List[Dict[str, Any]],
        chapter_pattern: str,
        title_pattern: str,
        section_name: str
    ) -> Optional[Tuple[str, str, str, float]]:
        """Search for chapter in body chapters"""
        for chapter in chapters:
            chapter_title = chapter.get('title', '')
            chapter_id = chapter.get('id', '')

            # Check title
            if re.search(chapter_pattern, chapter_title):
                similarity = self._calculate_similarity(title_pattern, chapter_title)
                return (section_name, chapter_title, chapter_id, similarity)

            # Search in content_blocks
            content_blocks = chapter.get('content_blocks', [])
            for block in content_blocks:
                if block.get('type') == 'heading':
                    block_content = block.get('content', '')
                    if re.search(chapter_pattern, block_content):
                        similarity = self._calculate_similarity(title_pattern, block_content)
                        return (section_name, block_content, chapter_id, similarity)

        return None

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts using SequenceMatcher"""
        if not text1 or not text2:
            return 0.0

        # Normalize
        t1 = re.sub(r'\s+', '', text1.lower())
        t2 = re.sub(r'\s+', '', text2.lower())

        return SequenceMatcher(None, t1, t2).ratio()

    def _int_to_chinese(self, num: int) -> str:
        """Convert integer to Chinese numerals (basic support)"""
        numerals = {
            1: '一', 2: '二', 3: '三', 4: '四', 5: '五',
            6: '六', 7: '七', 8: '八', 9: '九', 10: '十',
            20: '廿', 30: '卅', 40: '卌', 100: '百', 1000: '千'
        }

        if num in numerals:
            return numerals[num]

        # Handle numbers 11-19
        if 11 <= num <= 19:
            return f"十{numerals[num - 10]}"

        # Handle numbers 21-29, 31-39, 41-49
        if 21 <= num <= 29:
            return f"廿{numerals[num - 20]}"
        if 31 <= num <= 39:
            return f"卅{numerals[num - 30]}"
        if 41 <= num <= 49:
            return f"卌{numerals[num - 40]}"

        # Fallback: just use the number
        return str(num)

    def _build_summary(self, result: SearchResult) -> str:
        """Build human-readable summary"""
        lines = []

        lines.append(f"TOC: {result.total_toc_entries} entries")
        lines.append(f"Body: {result.total_body_chapters} chapters")
        lines.append(f"Missing: {result.missing_count}")
        lines.append(f"Found elsewhere: {result.found_elsewhere_count}")
        lines.append(f"Truly missing: {result.truly_missing_count}")

        return " | ".join(lines)

    def find_missing_file(self, json_file: str, save_report: bool = True) -> SearchResult:
        """
        Find missing chapters in a JSON file.

        Args:
            json_file: Path to cleaned JSON file
            save_report: Save detailed report to file

        Returns:
            SearchResult
        """
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        result = self.find_missing(data)

        if save_report:
            report_file = Path(json_file).parent / f"{Path(json_file).stem}_missing_chapters.json"
            self._save_report(result, report_file)
            logger.info(f"Report saved to: {report_file}")

        return result

    def _save_report(self, result: SearchResult, output_path: Path):
        """Save search report to JSON"""
        report_data = {
            "summary": result.summary,
            "counts": {
                "toc_entries": result.total_toc_entries,
                "body_chapters": result.total_body_chapters,
                "missing": result.missing_count,
                "found_elsewhere": result.found_elsewhere_count,
                "truly_missing": result.truly_missing_count
            },
            "missing_chapters": [
                {
                    "chapter_number": mc.chapter_number,
                    "toc_title": mc.toc_title,
                    "full_toc_entry": mc.full_toc_entry,
                    "status": mc.status,
                    "found_in": mc.found_in,
                    "found_title": mc.found_title,
                    "found_id": mc.found_id,
                    "similarity_score": mc.similarity_score
                }
                for mc in result.missing_chapters
            ]
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)


def print_report(result: SearchResult):
    """Print formatted search report"""
    print(f"\n{'='*80}")
    print(f"MISSING CHAPTER SEARCH REPORT")
    print(f"{'='*80}\n")

    print(f"Summary: {result.summary}\n")

    if not result.missing_chapters:
        print("✓ All TOC chapters found in body!\n")
        return

    print(f"MISSING CHAPTERS ({result.missing_count}):")
    print(f"{'='*80}\n")

    for mc in result.missing_chapters:
        status_icon = "✓" if mc.status == "found" else "📦" if mc.status == "embedded" else "⚠" if mc.status == "misclassified" else "✗"

        print(f"{status_icon} Chapter {mc.chapter_number}: {mc.full_toc_entry}")
        print(f"   TOC Title: {mc.toc_title}")
        print(f"   Status: {mc.status.upper()}")

        if mc.status == "embedded":
            print(f"   Found in: {mc.found_in}")
            print(f"   Title page: {mc.found_title}")
            print(f"   Content blocks: {len(mc.embedded_content_blocks) if mc.embedded_content_blocks else 0}")
            print(f"   Start index: {mc.embedded_content_start}")
            print(f"   💡 Action Required: Extract embedded content from title page")
            print(f"   💡 Split section '{mc.found_id}' at block {mc.embedded_content_start}")
            print(f"   💡 Create new chapter with title '{mc.full_toc_entry}'")
        elif mc.status == "found":
            print(f"   Found in: {mc.found_in}")
            print(f"   Found title: {mc.found_title}")
            print(f"   Similarity: {mc.similarity_score:.2%}")
            print(f"   💡 Suggestion: Reclassify '{mc.found_id}' from {mc.found_in} to body.chapters")
        elif mc.status == "misclassified":
            print(f"   Found in: {mc.found_in} (but with different title)")
            print(f"   Found title: {mc.found_title}")
            print(f"   Similarity: {mc.similarity_score:.2%}")
            print(f"   💡 Suggestion: Check chapter numbering or title mismatch")
        else:
            print(f"   ✗ NOT FOUND in any section")
            print(f"   💡 Conclusion: Chapter {mc.chapter_number} is missing from source EPUB")

        print()

    print(f"{'='*80}\n")


def main():
    """CLI entry point"""
    import sys
    import argparse

    parser = argparse.ArgumentParser(
        description='Find missing chapters by searching all sections'
    )
    parser.add_argument('input', help='Path to cleaned JSON file')
    parser.add_argument('--threshold', type=float, default=0.6,
                       help='Similarity threshold for fuzzy matching (default: 0.6)')
    parser.add_argument('--no-report', action='store_true',
                       help='Do not save report file')

    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"Error: File not found: {args.input}")
        return 1

    finder = MissingChapterFinder(similarity_threshold=args.threshold)
    result = finder.find_missing_file(args.input, save_report=not args.no_report)

    print_report(result)

    return 0 if result.truly_missing_count == 0 else 1


if __name__ == "__main__":
    exit(main())
