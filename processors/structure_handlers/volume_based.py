#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Volume-based structure handler for multi-volume books."""

from typing import Any, Dict, List
import re
from .base import BaseStructureHandler, StructureDiscoveryResult


class VolumeBasedHandler(BaseStructureHandler):
    """Handler for multi-volume book structures."""

    def can_handle(self, json_data: Dict[str, Any]) -> float:
        """
        Check if data uses volume-based structure.

        Returns:
            Confidence score 0-1
        """
        # Check for volume indicators in metadata
        meta = json_data.get('meta', {})
        if meta.get('volume'):
            return 0.9

        # Check for volume markers in chapters
        chapters = json_data.get('chapters', [])
        if not chapters:
            return 0.0

        volume_count = 0
        total_count = min(5, len(chapters))

        for chapter in chapters[:total_count]:
            title = chapter.get('title', '')
            if re.search(r'[第卷].*[卷集部]', title):
                volume_count += 1

        confidence = volume_count / total_count if total_count > 0 else 0.0
        return confidence * 0.7  # Lower confidence as this is less common

    def discover_structure(self, json_data: Dict[str, Any]) -> StructureDiscoveryResult:
        """
        Discover volume-based structure.

        Pass 1: Extract all content, identify volumes, TOC, chapters.
        """
        result = StructureDiscoveryResult()
        result.detected_format = "volume"

        chapters = json_data.get('chapters', [])
        if not chapters:
            result.issues.append("No chapters found in JSON")
            return result

        result.total_chapters = len(chapters)

        # Process each chapter
        for idx, chapter in enumerate(chapters):
            title = chapter.get('title', '').strip()
            content = chapter.get('content', '')

            # Check if this is TOC
            if idx == 0 and self._is_toc_chapter(title, content):
                result.has_toc = True
                result.toc_location = 'first_chapter'
                result.toc_entries = self._parse_toc_content(content)
                continue

            # Check if this is intro
            if idx == 0 and self.detect_intro_keywords(title):
                result.has_intro = True
                intro_blocks = self._extract_chapter_blocks(chapter, idx)
                result.intro_blocks.extend(intro_blocks)
                continue

            # Regular chapter - extract blocks
            chapter_blocks = self._extract_chapter_blocks(chapter, idx)

            # Detect chapter boundaries
            chapter_info = self.detect_chapter_pattern(title)
            if chapter_info:
                result.chapter_boundaries.append({
                    'chapter_index': idx,
                    'chapter_number': chapter_info['number'],
                    'title': chapter_info['title'],
                    'full_title': chapter_info['full_text'],
                    'block_start': len(result.blocks),
                    'block_count': len(chapter_blocks)
                })

            result.blocks.extend(chapter_blocks)

        # Calculate confidence
        result.confidence = self._calculate_confidence(result)

        return result

    def _is_toc_chapter(self, title: str, content: Any) -> bool:
        """Check if this chapter is a TOC."""
        if self.detect_toc_keywords(title):
            return True

        if isinstance(content, str):
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            if len(lines) >= 5:
                short_lines = sum(1 for line in lines if len(line) <= 15)
                if short_lines / len(lines) >= 0.7:
                    return True

        return False

    def _parse_toc_content(self, content: Any) -> List[Dict[str, Any]]:
        """Parse TOC entries from content."""
        entries = []

        if isinstance(content, str):
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            for line in lines:
                chapter_info = self.detect_chapter_pattern(line)
                if chapter_info:
                    entries.append({
                        'full_title': chapter_info['full_text'],
                        'chapter_title': chapter_info['title'],
                        'chapter_number': chapter_info['number']
                    })

        return entries

    def _extract_chapter_blocks(
        self,
        chapter: Dict[str, Any],
        chapter_idx: int
    ) -> List[Dict[str, Any]]:
        """Extract blocks from a single chapter."""
        blocks = []
        title = chapter.get('title', '').strip()
        content = chapter.get('content', '')

        # Add title as heading block
        if title:
            blocks.append({
                "id": f"block_{self.block_counter:04d}",
                "epub_id": f"heading_{self.block_counter}",
                "type": "heading",
                "content": title,
                "metadata": {"level": 2}
            })
            self.block_counter += 1

        # Extract content blocks
        if isinstance(content, str):
            paragraphs = [p.strip() for p in content.split('\n') if p.strip()]
            for para in paragraphs:
                blocks.append({
                    "id": f"block_{self.block_counter:04d}",
                    "epub_id": f"para_{self.block_counter}",
                    "type": "paragraph",
                    "content": para,
                    "metadata": {}
                })
                self.block_counter += 1

        elif isinstance(content, list):
            content_blocks = self.extract_blocks_from_nodes(
                content,
                self.block_counter
            )
            blocks.extend(content_blocks)
            self.block_counter += len(content_blocks)

        return blocks

    def _calculate_confidence(self, result: StructureDiscoveryResult) -> float:
        """Calculate confidence score."""
        score = 0.0

        if result.total_chapters > 0:
            score += 0.3

        if len(result.chapter_boundaries) > 0:
            boundary_ratio = len(result.chapter_boundaries) / result.total_chapters
            score += 0.4 * boundary_ratio

        if result.has_toc:
            score += 0.15

        if len(result.blocks) > 0:
            score += 0.15

        return min(score, 1.0)
