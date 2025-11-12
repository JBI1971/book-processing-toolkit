#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Intro Separator - Extract intro material from Chapter 1."""

from typing import Any, Dict, List, Optional


class IntroSeparator:
    """
    Separate intro/preface material from Chapter 1.

    Handles:
    - Embedded intros (intro blocks in Chapter 1)
    - Inverted cases (Chapter 1 is actually intro)
    - Prologue chapters (序章/楔子 that should stay as Chapter 1)
    """

    def __init__(self, ai_validator: Optional[Any] = None):
        """
        Initialize intro separator.

        Args:
            ai_validator: Optional AIStructureValidator for classification
        """
        self.ai_validator = ai_validator

    def separate_intro(
        self,
        front_matter: Dict[str, Any],
        chapters: List[Dict[str, Any]]
    ) -> tuple:
        """
        Separate intro material from chapters.

        Args:
            front_matter: Front matter with 'intro' list
            chapters: List of chapters

        Returns:
            (updated_front_matter, updated_chapters)
        """
        if not chapters:
            return front_matter, chapters

        first_chapter = chapters[0]
        title = first_chapter.get('title', '')
        content_blocks = first_chapter.get('content_blocks', [])

        # Check if Chapter 1 should be extracted to intro
        should_extract = self._should_extract_as_intro(title, content_blocks)

        if should_extract:
            # Move Chapter 1 to intro
            front_matter['intro'] = content_blocks
            # Remove first chapter
            chapters = chapters[1:]
            # Renumber remaining chapters
            chapters = self._renumber_chapters(chapters)

        return front_matter, chapters

    def _should_extract_as_intro(
        self,
        title: str,
        content_blocks: List[Dict[str, Any]]
    ) -> bool:
        """Determine if Chapter 1 should be extracted to intro."""
        # Simple intro keywords (not prologue chapters)
        simple_intro_keywords = ['序', '前言', '引言', '自序']

        # Prologue chapter keywords (should stay as Chapter 1)
        chapter_prologue_keywords = ['序章', '楔子', '序幕']

        # If title contains prologue chapter keyword, keep as Chapter 1
        if any(kw in title for kw in chapter_prologue_keywords):
            return False

        # If title is ONLY simple intro keyword, extract
        if title.strip() in simple_intro_keywords:
            return True

        # Use AI if available
        if self.ai_validator:
            content_sample = self._get_content_sample(content_blocks)
            result = self.ai_validator.classify_intro_vs_chapter(
                title,
                content_sample
            )

            if result.get('classification') == 'intro' and result.get('confidence', 0) > 0.7:
                return True

        return False

    def _get_content_sample(self, content_blocks: List[Dict[str, Any]]) -> str:
        """Get first 500 chars of content."""
        text = ""
        for block in content_blocks:
            if block.get('type') == 'paragraph':
                text += block.get('content', '') + " "
                if len(text) >= 500:
                    break
        return text[:500]

    def _renumber_chapters(self, chapters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Renumber chapters after extraction."""
        for idx, chapter in enumerate(chapters):
            # Update ordinal to start from 1
            if chapter.get('ordinal'):
                chapter['ordinal'] = idx + 1

            # Update chapter ID
            chapter['id'] = f"chapter_{idx + 1:04d}"

        return chapters

    def detect_embedded_intro(
        self,
        content_blocks: List[Dict[str, Any]]
    ) -> tuple:
        """
        Detect and extract embedded intro from content blocks.

        Returns:
            (intro_blocks, remaining_blocks)
        """
        intro_blocks = []
        remaining_blocks = []

        # Look for intro keywords in first few blocks
        intro_keywords = ['序', '前言', '引言', '自序', '作者序']

        found_intro_end = False

        for idx, block in enumerate(content_blocks):
            if found_intro_end:
                remaining_blocks.append(block)
                continue

            content = block.get('content', '')

            # Check if this block starts main content
            if idx > 0 and self._is_chapter_start(content):
                found_intro_end = True
                remaining_blocks.append(block)
                continue

            # Check if intro keyword
            has_intro_keyword = any(kw in content for kw in intro_keywords)

            if has_intro_keyword or idx == 0:
                intro_blocks.append(block)
            else:
                # No intro keyword and not first block - main content
                found_intro_end = True
                remaining_blocks.append(block)

        # If we didn't find any separation, return all as remaining
        if not intro_blocks:
            return [], content_blocks

        return intro_blocks, remaining_blocks

    def _is_chapter_start(self, text: str) -> bool:
        """Check if text looks like chapter start."""
        # Pattern: 第N章 or 第N回
        import re
        patterns = [
            r'^第[一二三四五六七八九十廿卅卌百千\d]+[章回]',
        ]

        for pattern in patterns:
            if re.match(pattern, text.strip()):
                return True

        return False
