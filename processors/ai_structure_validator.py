#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI-powered structure validation using OpenAI."""

from typing import Any, Dict, List, Optional
import json
from openai import OpenAI


class AIStructureValidator:
    """
    Use OpenAI to validate structural classifications.

    Provides semantic validation for:
    - Intro vs Chapter 1 classification
    - TOC entry matching to chapter titles
    - Section type classification
    """

    def __init__(self, api_key: str, model: str = "gpt-4o-mini", temperature: float = 0.1):
        """
        Initialize AI validator.

        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-4o-mini for cost efficiency)
            temperature: Low temperature for consistency (default: 0.1)
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature

    def classify_intro_vs_chapter(
        self,
        title: str,
        content_sample: str
    ) -> Dict[str, Any]:
        """
        Classify if content should be intro or Chapter 1.

        Args:
            title: Chapter title
            content_sample: First 500 chars of content

        Returns:
            Dict with 'classification', 'confidence', 'reasoning'
        """
        prompt = f"""Analyze this Chinese novel section and determine if it should be classified as front matter (intro/preface) or Chapter 1.

Title: {title}
Content Sample: {content_sample[:500]}

Respond with JSON:
{{
  "classification": "intro" or "chapter",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation"
}}

Guidelines:
- 序章, 楔子, 序幕 = prologue CHAPTER (classify as "chapter")
- 序, 前言, 引言, 自序 alone = intro (classify as "intro")
- If content tells a story, it's likely a chapter
- If content is author's note/introduction, it's intro
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            return result

        except Exception as e:
            # Fallback on error
            return {
                "classification": "unknown",
                "confidence": 0.0,
                "reasoning": f"AI validation failed: {str(e)}"
            }

    def match_toc_to_chapter(
        self,
        toc_entries: List[Dict[str, Any]],
        chapter_titles: List[Dict[str, Any]],
        batch_size: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Match TOC entries to chapter titles using semantic matching.

        Args:
            toc_entries: List of TOC entries with 'full_title'
            chapter_titles: List of chapters with 'title' and 'id'
            batch_size: Entries per API call

        Returns:
            List of matches with 'toc_entry', 'chapter_id', 'confidence'
        """
        matches = []

        # Process in batches
        for i in range(0, len(toc_entries), batch_size):
            batch = toc_entries[i:i + batch_size]
            batch_matches = self._match_batch(batch, chapter_titles)
            matches.extend(batch_matches)

        return matches

    def _match_batch(
        self,
        toc_batch: List[Dict[str, Any]],
        chapter_titles: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Match a batch of TOC entries to chapters."""
        prompt = f"""Match these TOC entries to chapter titles. Handle character variants and typos.

TOC Entries:
{json.dumps([e.get('full_title') for e in toc_batch], ensure_ascii=False, indent=2)}

Chapter Titles (with IDs):
{json.dumps([{'id': c.get('id'), 'title': c.get('title')} for c in chapter_titles], ensure_ascii=False, indent=2)}

Respond with JSON array of matches:
[
  {{
    "toc_index": 0,
    "chapter_id": "chapter_0001",
    "confidence": 0.95,
    "notes": "exact match" or "fuzzy match: 薄->泊"
  }}
]

Consider:
- Character variants (薄/泊, 到/至)
- Extra decorators in TOC (☆☆☆)
- Partial matches
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            matches_data = result.get('matches', [])

            # Convert to full match objects
            matches = []
            for match in matches_data:
                toc_index = match.get('toc_index')
                if toc_index is not None and toc_index < len(toc_batch):
                    matches.append({
                        'toc_entry': toc_batch[toc_index],
                        'chapter_id': match.get('chapter_id'),
                        'confidence': match.get('confidence', 0.0),
                        'notes': match.get('notes', '')
                    })

            return matches

        except Exception as e:
            # Fallback: simple matching by index
            matches = []
            for idx, toc_entry in enumerate(toc_batch):
                if idx < len(chapter_titles):
                    matches.append({
                        'toc_entry': toc_entry,
                        'chapter_id': chapter_titles[idx].get('id'),
                        'confidence': 0.5,
                        'notes': f'Fallback match (AI failed): {str(e)}'
                    })
            return matches

    def classify_section_type(
        self,
        title: str,
        position: str  # 'first', 'middle', 'last'
    ) -> str:
        """
        Classify section type (front_matter, body, back_matter).

        Args:
            title: Section title
            position: Position in book

        Returns:
            'front_matter', 'body', or 'back_matter'
        """
        prompt = f"""Classify this Chinese novel section.

Title: {title}
Position: {position} of book

Respond with JSON:
{{
  "section_type": "front_matter" or "body" or "back_matter",
  "special_type": "preface", "prologue", "afterword", "appendix", "main_chapter", etc.
}}

Guidelines:
- 序, 前言, 引言, 自序 = front_matter (preface)
- 序章, 楔子, 序幕 = body (prologue chapter)
- 後記, 跋 = back_matter (afterword)
- 附錄 = back_matter (appendix)
- 第N章/回 = body (main_chapter)
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            return result.get('section_type', 'body')

        except Exception as e:
            # Fallback to heuristic
            if position == 'first':
                return 'front_matter'
            elif position == 'last':
                return 'back_matter'
            else:
                return 'body'
