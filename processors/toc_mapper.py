#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TOC Mapper - Maps TOC entries to chapter IDs."""

from typing import Any, Dict, List, Optional
import re
from difflib import SequenceMatcher


class TOCMapper:
    """
    Map TOC entries to actual chapter IDs.

    Handles:
    - Exact matches
    - Fuzzy matches (character variants)
    - Number-based matching
    - AI-assisted matching (when AIStructureValidator provided)
    """

    def __init__(self, ai_validator: Optional[Any] = None):
        """
        Initialize TOC mapper.

        Args:
            ai_validator: Optional AIStructureValidator for semantic matching
        """
        self.ai_validator = ai_validator

    def map_toc_to_chapters(
        self,
        toc_entries: List[Dict[str, Any]],
        chapters: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Map TOC entries to chapter IDs.

        Args:
            toc_entries: TOC entries with 'full_title', 'chapter_number'
            chapters: Chapters with 'id', 'title', 'ordinal'

        Returns:
            Updated TOC entries with 'chapter_id' field
        """
        # Try AI matching first if available
        if self.ai_validator:
            return self._ai_assisted_mapping(toc_entries, chapters)

        # Fallback to heuristic matching
        return self._heuristic_mapping(toc_entries, chapters)

    def _ai_assisted_mapping(
        self,
        toc_entries: List[Dict[str, Any]],
        chapters: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Use AI for semantic matching."""
        # Prepare chapter data
        chapter_data = [
            {'id': ch.get('id'), 'title': ch.get('title')}
            for ch in chapters
        ]

        # Get AI matches
        matches = self.ai_validator.match_toc_to_chapter(
            toc_entries,
            chapter_data
        )

        # Apply matches
        for match in matches:
            toc_entry = match['toc_entry']
            toc_entry['chapter_id'] = match['chapter_id']
            toc_entry['match_confidence'] = match['confidence']
            toc_entry['match_notes'] = match['notes']

        return toc_entries

    def _heuristic_mapping(
        self,
        toc_entries: List[Dict[str, Any]],
        chapters: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Heuristic-based mapping (no AI)."""
        # Build lookup maps
        ordinal_to_id = {
            ch.get('ordinal'): ch.get('id')
            for ch in chapters
            if ch.get('ordinal') is not None
        }

        title_to_id = {
            ch.get('title'): ch.get('id')
            for ch in chapters
        }

        for entry in toc_entries:
            chapter_id = None
            confidence = 0.0

            # Strategy 1: Match by chapter number
            chapter_number = entry.get('chapter_number')
            if chapter_number and chapter_number in ordinal_to_id:
                chapter_id = ordinal_to_id[chapter_number]
                confidence = 0.95

            # Strategy 2: Exact title match
            if not chapter_id:
                full_title = entry.get('full_title', '')
                if full_title in title_to_id:
                    chapter_id = title_to_id[full_title]
                    confidence = 1.0

            # Strategy 3: Fuzzy title match
            if not chapter_id:
                chapter_title = entry.get('chapter_title', '')
                best_match = self._fuzzy_match_title(
                    chapter_title,
                    [ch.get('title', '') for ch in chapters]
                )
                if best_match:
                    match_title, match_score = best_match
                    if match_score > 0.8:
                        chapter_id = title_to_id.get(match_title)
                        confidence = match_score

            # Apply mapping
            if chapter_id:
                entry['chapter_id'] = chapter_id
                entry['match_confidence'] = confidence

        return toc_entries

    def _fuzzy_match_title(
        self,
        target: str,
        candidates: List[str]
    ) -> Optional[tuple]:
        """
        Find best fuzzy match for title.

        Returns:
            (matched_title, score) or None
        """
        best_match = None
        best_score = 0.0

        for candidate in candidates:
            score = SequenceMatcher(None, target, candidate).ratio()
            if score > best_score:
                best_score = score
                best_match = candidate

        if best_match and best_score > 0.8:
            return (best_match, best_score)

        return None

    def generate_toc_from_chapters(
        self,
        chapters: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate TOC entries from chapter list.

        Args:
            chapters: Chapters with 'id', 'title', 'ordinal'

        Returns:
            TOC entries
        """
        toc_entries = []

        for chapter in chapters:
            title = chapter.get('title', '')
            ordinal = chapter.get('ordinal')
            chapter_id = chapter.get('id')

            # Parse chapter number from title if ordinal missing
            if ordinal is None:
                ordinal = self._extract_chapter_number(title)

            # Create TOC entry
            entry = {
                'full_title': title,
                'chapter_title': self._extract_chapter_title(title),
                'chapter_number': ordinal,
                'chapter_id': chapter_id,
                'match_confidence': 1.0,
                'match_notes': 'Generated from chapters'
            }
            toc_entries.append(entry)

        return toc_entries

    def _extract_chapter_number(self, title: str) -> Optional[int]:
        """Extract chapter number from title."""
        # Pattern: 第N章 or 第N回
        patterns = [
            r'^第([一二三四五六七八九十廿卅卌百千]+)[章回]',
            r'^第(\d+)[章回]',
        ]

        for pattern in patterns:
            match = re.match(pattern, title)
            if match:
                number_str = match.group(1)
                if number_str.isdigit():
                    return int(number_str)
                else:
                    return self._parse_chinese_number(number_str)

        return None

    def _parse_chinese_number(self, text: str) -> Optional[int]:
        """Parse Chinese numeral."""
        chinese_digits = {
            '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
            '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
            '十': 10, '廿': 20, '卅': 30, '卌': 40,
            '百': 100, '千': 1000
        }

        if text in chinese_digits:
            return chinese_digits[text]

        # Handle compound numbers
        if len(text) == 2 and text[0] in chinese_digits and text[1] in chinese_digits:
            first = chinese_digits[text[0]]
            second = chinese_digits[text[1]]
            if first >= 10:
                return first + second

        result = 0
        temp = 0

        for char in text:
            if char not in chinese_digits:
                continue

            digit = chinese_digits[char]

            if digit >= 10:
                if temp == 0:
                    temp = 1
                temp *= digit
                result += temp
                temp = 0
            else:
                temp = digit

        result += temp
        return result if result > 0 else None

    def _extract_chapter_title(self, full_title: str) -> str:
        """Extract chapter title (remove chapter number prefix)."""
        # Remove 第N章/回 prefix
        patterns = [
            r'^第[一二三四五六七八九十廿卅卌百千\d]+[章回][\s　]*',
        ]

        for pattern in patterns:
            full_title = re.sub(pattern, '', full_title)

        return full_title.strip()
