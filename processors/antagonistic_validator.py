#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Antagonistic Validator - Actively hunts for structural issues.

This validator implements 5 challenges that seek to find problems:
1. Inverted Structure (40 points) - Intro masquerading as Chapter 1
2. TOC Mappings (25 points) - Every TOC entry maps to real chapter
3. Chapter Boundaries (15 points) - No combined chapters
4. Intro Separation (10 points) - Intro properly extracted
5. Chapter Sequence (10 points) - No gaps or duplicates
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import re


@dataclass
class ValidationChallenge:
    """Result of a single validation challenge."""

    name: str
    max_points: int
    points_earned: int
    passed: bool
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class AntagonisticValidationResult:
    """Complete antagonistic validation result."""

    passed: bool
    score: int  # 0-100
    total_points: int = 100
    challenges: Dict[str, ValidationChallenge] = field(default_factory=dict)
    critical_issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    summary: str = ""


class AntagonisticValidator:
    """
    Validator that actively seeks structural problems.

    Unlike traditional validators that check for correctness,
    this validator challenges the structure with specific scenarios
    that commonly cause issues.
    """

    def __init__(self):
        self.challenges = {
            'inverted_structure': 40,
            'toc_mappings': 25,
            'chapter_boundaries': 15,
            'intro_separation': 10,
            'chapter_sequence': 10,
        }

    def validate(self, processed_data: Dict[str, Any]) -> AntagonisticValidationResult:
        """
        Run all validation challenges.

        Args:
            processed_data: Processed book structure

        Returns:
            AntagonisticValidationResult with detailed scores
        """
        result = AntagonisticValidationResult(
            passed=False,
            score=0,
            total_points=100
        )

        # Challenge 1: Inverted Structure (40 points)
        inverted = self._challenge_inverted_structure(processed_data)
        result.challenges['inverted_structure'] = inverted
        result.score += inverted.points_earned

        # Challenge 2: TOC Mappings (25 points)
        toc_mappings = self._challenge_toc_mappings(processed_data)
        result.challenges['toc_mappings'] = toc_mappings
        result.score += toc_mappings.points_earned

        # Challenge 3: Chapter Boundaries (15 points)
        boundaries = self._challenge_chapter_boundaries(processed_data)
        result.challenges['chapter_boundaries'] = boundaries
        result.score += boundaries.points_earned

        # Challenge 4: Intro Separation (10 points)
        intro = self._challenge_intro_separation(processed_data)
        result.challenges['intro_separation'] = intro
        result.score += intro.points_earned

        # Challenge 5: Chapter Sequence (10 points)
        sequence = self._challenge_chapter_sequence(processed_data)
        result.challenges['chapter_sequence'] = sequence
        result.score += sequence.points_earned

        # Collect critical issues and warnings
        for challenge in result.challenges.values():
            if not challenge.passed and challenge.max_points >= 20:
                result.critical_issues.extend(challenge.issues)
            elif not challenge.passed:
                result.warnings.extend(challenge.issues)

        # Determine pass/fail (score >= 90)
        result.passed = result.score >= 90

        # Generate summary
        result.summary = self._generate_summary(result)

        return result

    def _challenge_inverted_structure(
        self,
        data: Dict[str, Any]
    ) -> ValidationChallenge:
        """
        Challenge 1: Inverted Structure (40 points)

        Check if intro material is mistakenly classified as Chapter 1.

        Tests:
        - Is "intro" too long (>2000 chars)?
        - Does "intro" title have 序章/楔子 (prologue CHAPTER)?
        - Does TOC reference the "intro"?
        - Would AI classify it as chapter content?
        """
        challenge = ValidationChallenge(
            name="Inverted Structure",
            max_points=40,
            points_earned=0,
            passed=False
        )

        intro_blocks = data.get('structure', {}).get('front_matter', {}).get('intro', [])
        chapters = data.get('structure', {}).get('body', {}).get('chapters', [])
        toc = data.get('structure', {}).get('front_matter', {}).get('toc', [])

        # Test 1: Intro too long? (>2000 chars suggests chapter content)
        if intro_blocks:
            total_chars = sum(len(block.get('content', '')) for block in intro_blocks)
            if total_chars > 2000:
                challenge.issues.append(
                    f"Intro is suspiciously long ({total_chars} chars). "
                    "Likely a full chapter."
                )
                challenge.suggestions.append(
                    "Consider reclassifying intro as Chapter 1"
                )
                return challenge  # Critical failure

        # Test 2: Check first chapter for intro keywords in title
        if chapters:
            first_chapter = chapters[0]
            title = first_chapter.get('title', '')
            # Keywords that indicate prologue CHAPTER, not intro
            chapter_prologue_keywords = ['序章', '楔子', '序幕']
            if any(kw in title for kw in chapter_prologue_keywords):
                challenge.issues.append(
                    f"Chapter 1 title '{title}' contains prologue chapter marker. "
                    "This should be a numbered chapter, not front matter."
                )
                challenge.suggestions.append(
                    "Keep as Chapter 1, do not extract to intro"
                )
                # This is OK - prologue chapter should be Chapter 1

        # Test 3: TOC references intro?
        if toc and intro_blocks:
            # Check if any TOC entry points to intro
            for entry in toc:
                chapter_id = entry.get('chapter_id', '')
                if 'intro' in chapter_id or chapter_id == 'chapter_0000':
                    challenge.issues.append(
                        f"TOC entry references intro: {entry.get('full_title')}"
                    )
                    challenge.suggestions.append(
                        "Intro should not be in TOC - reclassify as Chapter 1"
                    )
                    return challenge  # Critical failure

        # Test 4: Intro exists but is actually empty/minimal
        if intro_blocks:
            total_chars = sum(len(block.get('content', '')) for block in intro_blocks)
            if total_chars < 50:
                challenge.issues.append(
                    f"Intro exists but is tiny ({total_chars} chars). "
                    "Likely misclassified."
                )

        # Test 5: Check for inverted case - Chapter 1 is too short
        if chapters and not intro_blocks:
            first_chapter = chapters[0]
            first_blocks = first_chapter.get('content_blocks', [])
            total_chars = sum(len(block.get('content', '')) for block in first_blocks)

            # If Chapter 1 is very short and has intro keywords, suspicious
            title = first_chapter.get('title', '')
            simple_intro_keywords = ['序', '前言', '引言', '自序']
            if total_chars < 500 and any(kw in title for kw in simple_intro_keywords):
                challenge.issues.append(
                    f"Chapter 1 is short ({total_chars} chars) with intro title '{title}'. "
                    "Might need extraction to front_matter."
                )
                challenge.suggestions.append(
                    "Consider extracting to front_matter.intro"
                )

        # Pass if no issues found
        if not challenge.issues:
            challenge.passed = True
            challenge.points_earned = challenge.max_points

        return challenge

    def _challenge_toc_mappings(
        self,
        data: Dict[str, Any]
    ) -> ValidationChallenge:
        """
        Challenge 2: TOC Mappings (25 points)

        Verify every TOC entry maps to a real chapter.

        Tests:
        - Every TOC entry has chapter_id?
        - Every chapter_id exists in body.chapters?
        - No orphaned entries?
        """
        challenge = ValidationChallenge(
            name="TOC Mappings",
            max_points=25,
            points_earned=0,
            passed=False
        )

        toc = data.get('structure', {}).get('front_matter', {}).get('toc', [])
        chapters = data.get('structure', {}).get('body', {}).get('chapters', [])

        if not toc:
            # No TOC is acceptable (will be generated)
            challenge.passed = True
            challenge.points_earned = challenge.max_points
            return challenge

        # Build chapter_id set
        chapter_ids = {ch.get('id') for ch in chapters}

        missing_chapter_id = []
        invalid_chapter_id = []

        for entry in toc:
            chapter_id = entry.get('chapter_id')

            # Test 1: Has chapter_id?
            if not chapter_id:
                missing_chapter_id.append(entry.get('full_title', 'Unknown'))
                continue

            # Test 2: chapter_id exists?
            if chapter_id not in chapter_ids:
                invalid_chapter_id.append(
                    f"{entry.get('full_title')} -> {chapter_id}"
                )

        if missing_chapter_id:
            challenge.issues.append(
                f"{len(missing_chapter_id)} TOC entries missing chapter_id"
            )
            challenge.suggestions.append(
                "Run TOC mapper to assign chapter_ids"
            )

        if invalid_chapter_id:
            challenge.issues.append(
                f"{len(invalid_chapter_id)} TOC entries point to non-existent chapters"
            )
            challenge.suggestions.append(
                "Verify chapter alignment and re-run TOC mapper"
            )

        # Calculate partial credit
        total_entries = len(toc)
        valid_entries = total_entries - len(missing_chapter_id) - len(invalid_chapter_id)

        if total_entries > 0:
            success_rate = valid_entries / total_entries
            challenge.points_earned = int(challenge.max_points * success_rate)
            challenge.passed = success_rate >= 0.95  # 95% threshold
        else:
            challenge.passed = True
            challenge.points_earned = challenge.max_points

        return challenge

    def _challenge_chapter_boundaries(
        self,
        data: Dict[str, Any]
    ) -> ValidationChallenge:
        """
        Challenge 3: Chapter Boundaries (15 points)

        Check for combined chapters (multiple headings in one chapter).

        Tests:
        - Each chapter has exactly one heading?
        - No multiple chapter markers in content?
        """
        challenge = ValidationChallenge(
            name="Chapter Boundaries",
            max_points=15,
            points_earned=0,
            passed=False
        )

        chapters = data.get('structure', {}).get('body', {}).get('chapters', [])

        combined_chapters = []

        for chapter in chapters:
            content_blocks = chapter.get('content_blocks', [])

            # Count headings
            headings = [b for b in content_blocks if b.get('type') == 'heading']

            if len(headings) > 1:
                # Multiple headings - likely combined chapter
                titles = [h.get('content') for h in headings]
                combined_chapters.append({
                    'chapter_id': chapter.get('id'),
                    'headings': titles
                })

        if combined_chapters:
            challenge.issues.append(
                f"{len(combined_chapters)} chapters have multiple headings"
            )
            challenge.suggestions.append(
                "Split combined chapters into separate chapters"
            )

            # Partial credit
            total_chapters = len(chapters)
            clean_chapters = total_chapters - len(combined_chapters)
            success_rate = clean_chapters / total_chapters if total_chapters > 0 else 0
            challenge.points_earned = int(challenge.max_points * success_rate)
            challenge.passed = success_rate >= 0.95
        else:
            challenge.passed = True
            challenge.points_earned = challenge.max_points

        return challenge

    def _challenge_intro_separation(
        self,
        data: Dict[str, Any]
    ) -> ValidationChallenge:
        """
        Challenge 4: Intro Separation (10 points)

        Check if intro keywords still present in Chapter 1.

        Tests:
        - Chapter 1 title has intro keywords?
        - Should be extracted to front_matter?
        """
        challenge = ValidationChallenge(
            name="Intro Separation",
            max_points=10,
            points_earned=0,
            passed=False
        )

        chapters = data.get('structure', {}).get('body', {}).get('chapters', [])

        if not chapters:
            challenge.passed = True
            challenge.points_earned = challenge.max_points
            return challenge

        first_chapter = chapters[0]
        title = first_chapter.get('title', '')

        # Simple intro keywords (not chapter prologue keywords)
        simple_intro_keywords = ['序', '前言', '引言', '自序']

        # Check if title is ONLY intro keyword (e.g., just "序")
        if title.strip() in simple_intro_keywords:
            challenge.issues.append(
                f"Chapter 1 title is '{title}' - should be in front_matter"
            )
            challenge.suggestions.append(
                "Extract Chapter 1 to front_matter.intro"
            )
        else:
            challenge.passed = True
            challenge.points_earned = challenge.max_points

        return challenge

    def _challenge_chapter_sequence(
        self,
        data: Dict[str, Any]
    ) -> ValidationChallenge:
        """
        Challenge 5: Chapter Sequence (10 points)

        Check for gaps, duplicates, or out-of-order chapters.

        Tests:
        - Sequential numbering?
        - No gaps?
        - No duplicates?
        """
        challenge = ValidationChallenge(
            name="Chapter Sequence",
            max_points=10,
            points_earned=0,
            passed=False
        )

        chapters = data.get('structure', {}).get('body', {}).get('chapters', [])

        if not chapters:
            challenge.passed = True
            challenge.points_earned = challenge.max_points
            return challenge

        # Extract ordinals
        ordinals = [ch.get('ordinal') for ch in chapters if ch.get('ordinal')]

        if not ordinals:
            # No ordinals - can't validate
            challenge.passed = True
            challenge.points_earned = challenge.max_points
            return challenge

        # Check for duplicates
        if len(ordinals) != len(set(ordinals)):
            duplicates = [x for x in ordinals if ordinals.count(x) > 1]
            challenge.issues.append(
                f"Duplicate chapter numbers: {set(duplicates)}"
            )

        # Check for gaps
        ordinals_sorted = sorted(ordinals)
        start = ordinals_sorted[0]
        expected = list(range(start, start + len(ordinals)))

        if ordinals_sorted != expected:
            missing = set(expected) - set(ordinals_sorted)
            if missing:
                challenge.issues.append(
                    f"Missing chapter numbers: {sorted(missing)}"
                )

        # Check for out-of-order
        if ordinals != ordinals_sorted:
            challenge.issues.append(
                "Chapters are out of order"
            )

        if not challenge.issues:
            challenge.passed = True
            challenge.points_earned = challenge.max_points

        return challenge

    def _generate_summary(self, result: AntagonisticValidationResult) -> str:
        """Generate human-readable summary."""
        lines = [
            f"Antagonistic Validation: {'PASSED' if result.passed else 'FAILED'}",
            f"Score: {result.score}/{result.total_points}",
            "",
            "Challenge Results:"
        ]

        for name, challenge in result.challenges.items():
            status = "PASS" if challenge.passed else "FAIL"
            lines.append(
                f"  {challenge.name}: {status} "
                f"({challenge.points_earned}/{challenge.max_points} points)"
            )

        if result.critical_issues:
            lines.append("")
            lines.append("Critical Issues:")
            for issue in result.critical_issues:
                lines.append(f"  - {issue}")

        if result.warnings:
            lines.append("")
            lines.append("Warnings:")
            for warning in result.warnings:
                lines.append(f"  - {warning}")

        return "\n".join(lines)
