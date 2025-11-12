#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Book Structure Analyzer - Main orchestrator for JSON cleaning pipeline.

Implements two-pass processing with iteration support:
- Pass 1: Structure Discovery
- Pass 2: Alignment & Mapping
- Antagonistic Validation
- Iteration until validation passes or max iterations reached
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from .structure_handlers import (
    ChapterBasedHandler,
    EpisodeBasedHandler,
    VolumeBasedHandler,
    ModernNovelHandler
)
from .antagonistic_validator import AntagonisticValidator
from .ai_structure_validator import AIStructureValidator
from .toc_mapper import TOCMapper
from .intro_separator import IntroSeparator


@dataclass
class ProcessingResult:
    """Result of processing pipeline."""

    success: bool
    iterations: int
    final_score: int
    data: Optional[Dict[str, Any]] = None
    validation_result: Optional[Any] = None
    issues: List[str] = field(default_factory=list)
    processing_log: List[str] = field(default_factory=list)


class BookStructureAnalyzer:
    """
    Main orchestrator for book structure analysis.

    Pipeline:
    1. Select appropriate structure handler
    2. Pass 1: Structure Discovery
    3. Pass 2: Alignment & Mapping
    4. Antagonistic Validation
    5. Iterate if validation fails (max 3 iterations)
    """

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        max_iterations: int = 3,
        passing_score: int = 90
    ):
        """
        Initialize analyzer.

        Args:
            openai_api_key: Optional OpenAI API key for AI validation
            max_iterations: Max iterations to try (default: 3)
            passing_score: Minimum score to pass (default: 90)
        """
        self.max_iterations = max_iterations
        self.passing_score = passing_score

        # Initialize handlers
        self.handlers = [
            ChapterBasedHandler(),
            EpisodeBasedHandler(),
            VolumeBasedHandler(),
            ModernNovelHandler()  # Fallback
        ]

        # Initialize validators
        self.antagonistic_validator = AntagonisticValidator()

        # Initialize AI components (optional)
        self.ai_validator = None
        if openai_api_key:
            self.ai_validator = AIStructureValidator(openai_api_key)

        # Initialize processors
        self.toc_mapper = TOCMapper(ai_validator=self.ai_validator)
        self.intro_separator = IntroSeparator(ai_validator=self.ai_validator)

        # Logging
        self.logger = logging.getLogger(__name__)

    def process(self, json_data: Dict[str, Any]) -> ProcessingResult:
        """
        Process book JSON through complete pipeline.

        Args:
            json_data: Raw book JSON

        Returns:
            ProcessingResult with final data and validation
        """
        result = ProcessingResult(
            success=False,
            iterations=0,
            final_score=0
        )

        best_score = 0
        best_data = None
        best_validation = None

        # Select handler
        handler = self._select_handler(json_data)
        result.processing_log.append(
            f"Selected handler: {handler.__class__.__name__}"
        )

        # Iteration loop
        for iteration in range(1, self.max_iterations + 1):
            result.iterations = iteration
            result.processing_log.append(f"\n=== Iteration {iteration} ===")

            # Pass 1: Structure Discovery
            self.logger.info(f"Iteration {iteration}: Pass 1 - Structure Discovery")
            discovery = handler.discover_structure(json_data)
            result.processing_log.append(
                f"Discovery: format={discovery.detected_format}, "
                f"chapters={discovery.total_chapters}, "
                f"confidence={discovery.confidence:.2f}"
            )

            # Pass 2: Alignment & Mapping
            self.logger.info(f"Iteration {iteration}: Pass 2 - Alignment & Mapping")
            aligned_data = self._align_and_map(discovery, json_data)
            result.processing_log.append(
                f"Alignment: {len(aligned_data.get('structure', {}).get('body', {}).get('chapters', []))} chapters"
            )

            # Antagonistic Validation
            self.logger.info(f"Iteration {iteration}: Antagonistic Validation")
            validation = self.antagonistic_validator.validate(aligned_data)
            result.processing_log.append(
                f"Validation: score={validation.score}/100, passed={validation.passed}"
            )

            # Track best result
            if validation.score > best_score:
                best_score = validation.score
                best_data = aligned_data
                best_validation = validation
                result.processing_log.append(f"New best score: {best_score}")

            # Check if passed
            if validation.passed and validation.score >= self.passing_score:
                result.processing_log.append(f"PASSED on iteration {iteration}")
                break

            # Log issues for next iteration
            if validation.critical_issues:
                result.processing_log.append("Critical issues:")
                for issue in validation.critical_issues:
                    result.processing_log.append(f"  - {issue}")

            # Apply fixes for next iteration
            if iteration < self.max_iterations:
                json_data = self._apply_fixes(aligned_data, validation)

        # Set final result
        result.success = best_validation.passed if best_validation else False
        result.final_score = best_score
        result.data = best_data
        result.validation_result = best_validation

        if best_validation:
            for issue in best_validation.critical_issues:
                result.issues.append(issue)
            for warning in best_validation.warnings:
                result.issues.append(warning)

        return result

    def _select_handler(self, json_data: Dict[str, Any]):
        """Select best handler for data."""
        best_handler = None
        best_confidence = 0.0

        for handler in self.handlers:
            confidence = handler.can_handle(json_data)
            if confidence > best_confidence:
                best_confidence = confidence
                best_handler = handler

        return best_handler or self.handlers[-1]  # Fallback to modern

    def _align_and_map(
        self,
        discovery: Any,
        original_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Pass 2: Align and map structure.

        - Map TOC entries to chapter IDs
        - Separate intro from Chapter 1
        - Build final structure
        """
        # Build base structure
        meta = original_data.get('meta', {})
        if not meta:
            # Extract from discovery
            meta = {
                'title': original_data.get('title', 'Unknown'),
                'author': original_data.get('author', 'Unknown'),
                'language': 'zh-Hant',
                'schema_version': '2.0.0'
            }

        # Build chapters from boundaries
        chapters = self._build_chapters_from_boundaries(
            discovery.chapter_boundaries,
            discovery.blocks
        )

        # Separate intro
        front_matter = {'toc': discovery.toc_entries, 'intro': discovery.intro_blocks}
        front_matter, chapters = self.intro_separator.separate_intro(
            front_matter,
            chapters
        )

        # Map TOC to chapters
        if front_matter['toc']:
            front_matter['toc'] = self.toc_mapper.map_toc_to_chapters(
                front_matter['toc'],
                chapters
            )
        else:
            # Generate TOC from chapters
            front_matter['toc'] = self.toc_mapper.generate_toc_from_chapters(chapters)

        # Build final structure
        return {
            'meta': meta,
            'structure': {
                'front_matter': front_matter,
                'body': {'chapters': chapters},
                'back_matter': {}
            }
        }

    def _build_chapters_from_boundaries(
        self,
        boundaries: List[Dict[str, Any]],
        blocks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Build chapter objects from boundaries and blocks."""
        chapters = []

        for boundary in boundaries:
            chapter_idx = boundary['chapter_index']
            block_start = boundary['block_start']
            block_count = boundary['block_count']

            # Extract blocks for this chapter
            chapter_blocks = blocks[block_start:block_start + block_count]

            chapter = {
                'id': f"chapter_{boundary['chapter_number']:04d}",
                'title': boundary['title'],
                'ordinal': boundary['chapter_number'],
                'content_blocks': chapter_blocks
            }
            chapters.append(chapter)

        return chapters

    def _apply_fixes(
        self,
        data: Dict[str, Any],
        validation: Any
    ) -> Dict[str, Any]:
        """Apply fixes based on validation issues."""
        # For now, return data unchanged
        # In future iterations, could implement automatic fixes
        return data

    def process_file(
        self,
        input_path: str,
        directory_name: Optional[str] = None,
        output_path: Optional[str] = None
    ) -> ProcessingResult:
        """
        Process a JSON file.

        Args:
            input_path: Input JSON file path
            directory_name: Directory name for metadata extraction
            output_path: Optional output path

        Returns:
            ProcessingResult
        """
        # Load input
        input_path = Path(input_path)
        with open(input_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)

        # Process
        result = self.process(json_data)

        # Save output
        if output_path and result.data:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result.data, f, ensure_ascii=False, indent=2)

        return result
