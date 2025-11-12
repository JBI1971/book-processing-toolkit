#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Base structure handler for book processing."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import re


@dataclass
class StructureDiscoveryResult:
    """Result of structure discovery pass."""

    # Extracted content blocks
    blocks: List[Dict[str, Any]] = field(default_factory=list)

    # TOC information
    toc_location: Optional[str] = None  # 'first_chapter', 'separate_section', etc.
    toc_entries: List[Dict[str, Any]] = field(default_factory=list)

    # Chapter boundaries
    chapter_boundaries: List[Dict[str, Any]] = field(default_factory=list)

    # Intro/front matter
    intro_blocks: List[Dict[str, Any]] = field(default_factory=list)

    # Metadata
    detected_format: str = "unknown"  # 'chapter', 'episode', 'volume', 'modern'
    total_chapters: int = 0
    has_toc: bool = False
    has_intro: bool = False

    # Quality indicators
    confidence: float = 0.0  # 0-1 confidence in structure detection
    issues: List[str] = field(default_factory=list)


class BaseStructureHandler(ABC):
    """Abstract base class for structure handlers."""

    def __init__(self):
        self.block_counter = 0

    @abstractmethod
    def can_handle(self, json_data: Dict[str, Any]) -> float:
        """
        Determine if this handler can process the given data.

        Returns:
            Confidence score 0-1 (1 = perfect match)
        """
        pass

    @abstractmethod
    def discover_structure(self, json_data: Dict[str, Any]) -> StructureDiscoveryResult:
        """
        First pass: Discover structure without modification.

        Extracts:
        - All content blocks
        - TOC location and entries
        - Chapter boundaries
        - Intro material
        """
        pass

    def extract_blocks_from_nodes(
        self,
        nodes: List[Any],
        start_id: int = 0,
        context: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Recursively extract content blocks from structured nodes.

        Args:
            nodes: List of node objects
            start_id: Starting block ID number
            context: Context string for debugging

        Returns:
            List of content blocks with IDs
        """
        blocks = []
        block_id = start_id

        for node in nodes:
            if isinstance(node, str):
                if node.strip():
                    blocks.append({
                        "id": f"block_{block_id:04d}",
                        "epub_id": f"text_{block_id}",
                        "type": "paragraph",
                        "content": node.strip(),
                        "metadata": {}
                    })
                    block_id += 1

            elif isinstance(node, dict):
                tag = node.get("tag", "").lower()
                content = node.get("content", "")

                # Heading elements
                if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                    text = self._extract_text_from_node(node)
                    if text.strip():
                        blocks.append({
                            "id": f"block_{block_id:04d}",
                            "epub_id": f"heading_{block_id}",
                            "type": "heading",
                            "content": text.strip(),
                            "metadata": {"level": int(tag[1])}
                        })
                        block_id += 1

                # Paragraph elements
                elif tag == "p":
                    text = self._extract_text_from_node(node)
                    if text.strip():
                        blocks.append({
                            "id": f"block_{block_id:04d}",
                            "epub_id": f"para_{block_id}",
                            "type": "paragraph",
                            "content": text.strip(),
                            "metadata": {}
                        })
                        block_id += 1

                # List elements
                elif tag in ("ul", "ol"):
                    if isinstance(content, list):
                        list_blocks = self.extract_blocks_from_nodes(
                            content,
                            block_id,
                            f"{context}/list"
                        )
                        blocks.extend(list_blocks)
                        block_id += len(list_blocks)

                # Container elements - recurse
                elif tag in ("div", "section", "article", "body", "li"):
                    if isinstance(content, list):
                        nested = self.extract_blocks_from_nodes(
                            content,
                            block_id,
                            f"{context}/{tag}"
                        )
                        blocks.extend(nested)
                        block_id += len(nested)
                    elif isinstance(content, str) and content.strip():
                        blocks.append({
                            "id": f"block_{block_id:04d}",
                            "epub_id": f"para_{block_id}",
                            "type": "paragraph",
                            "content": content.strip(),
                            "metadata": {}
                        })
                        block_id += 1

        self.block_counter = block_id
        return blocks

    def _extract_text_from_node(self, node: Any) -> str:
        """Extract all text from a node (including nested content)."""
        if isinstance(node, str):
            return node

        if isinstance(node, dict):
            content = node.get("content", "")
            if isinstance(content, str):
                return content
            elif isinstance(content, list):
                texts = []
                for item in content:
                    texts.append(self._extract_text_from_node(item))
                return " ".join(texts)

        return ""

    def parse_chinese_number(self, text: str) -> Optional[int]:
        """
        Parse Chinese numerals including special cases.

        Supports:
        - Basic: 一二三...十
        - Special: 廿 (20), 卅 (30), 卌 (40)
        - Large: 百 (100), 千 (1000)

        Examples:
        - 廿一 → 21
        - 卅五 → 35
        - 第三十二章 → 32
        """
        chinese_digits = {
            '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
            '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
            '十': 10, '廿': 20, '卅': 30, '卌': 40,
            '百': 100, '千': 1000
        }

        # Remove common prefixes/suffixes
        text = re.sub(r'^第', '', text)
        text = re.sub(r'[章回節集部卷]$', '', text)
        text = text.strip()

        # Try direct mapping for special numerals
        if text in chinese_digits:
            return chinese_digits[text]

        # Handle compound numbers like 廿一, 卅五
        if len(text) == 2 and text[0] in chinese_digits and text[1] in chinese_digits:
            first = chinese_digits[text[0]]
            second = chinese_digits[text[1]]
            if first >= 10:  # Special numeral (廿/卅/卌)
                return first + second

        # Handle complex patterns like 三十二
        result = 0
        temp = 0

        for char in text:
            if char not in chinese_digits:
                continue

            digit = chinese_digits[char]

            if digit >= 10:  # Multiplier (十/百/千)
                if temp == 0:
                    temp = 1
                temp *= digit
                result += temp
                temp = 0
            else:
                temp = digit

        result += temp

        return result if result > 0 else None

    def detect_toc_keywords(self, text: str) -> bool:
        """Check if text contains TOC keywords."""
        keywords = [
            "目錄", "目录", "contents",
            "table of contents", "toc"
        ]
        text_lower = text.lower()
        return any(kw in text_lower for kw in keywords)

    def detect_intro_keywords(self, text: str) -> bool:
        """Check if text contains intro/preface keywords."""
        keywords = [
            "序", "前言", "引言", "序章",
            "楔子", "自序", "序幕"
        ]
        return any(kw in text for kw in keywords)

    def detect_chapter_pattern(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Detect chapter patterns in text.

        Returns:
            Dict with 'number', 'title', 'format' if found
        """
        # Pattern: 第N章 or 第N回
        patterns = [
            r'^第([一二三四五六七八九十廿卅卌百千]+)章[\s　]*(.*)$',
            r'^第([一二三四五六七八九十廿卅卌百千]+)回[\s　]*(.*)$',
            r'^第(\d+)章[\s　]*(.*)$',
            r'^第(\d+)回[\s　]*(.*)$',
        ]

        for pattern in patterns:
            match = re.match(pattern, text.strip())
            if match:
                number_str = match.group(1)
                title = match.group(2).strip()

                # Parse number
                if number_str.isdigit():
                    number = int(number_str)
                else:
                    number = self.parse_chinese_number(number_str)

                if number is not None:
                    format_type = 'chapter' if '章' in pattern else 'episode'
                    return {
                        'number': number,
                        'title': title,
                        'format': format_type,
                        'full_text': text.strip()
                    }

        return None
