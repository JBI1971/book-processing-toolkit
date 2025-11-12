#!/usr/bin/env python3
"""
Structure Validator Processor
AI-powered validation of TOC/chapter alignment and structural classification
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file (override existing)
load_dotenv(override=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TEMPERATURE = 0.3
DEFAULT_TIMEOUT = 60


# =============================================================================
# ENUMS AND DATA CLASSES
# =============================================================================

class SectionType(Enum):
    """Section classification types"""
    FRONT_MATTER = "front_matter"  # Preface, introduction, author notes
    BODY = "body"  # Main story chapters
    BACK_MATTER = "back_matter"  # Afterword, appendix, notes


class SpecialSectionType(Enum):
    """Special section types within Chinese novels"""
    PREFACE = "preface"  # 自序, 前言
    INTRODUCTION = "introduction"  # 引言, 序章
    PROLOGUE = "prologue"  # 序幕, 楔子
    AFTERWORD = "afterword"  # 後記, 跋
    APPENDIX = "appendix"  # 附錄
    AUTHOR_NOTE = "author_note"  # 作者註, 說明
    EPILOGUE = "epilogue"  # 尾聲
    MAIN_CHAPTER = "main_chapter"  # Regular story chapter


@dataclass
class ValidationIssue:
    """Represents a validation issue found"""
    severity: str  # "error", "warning", "info"
    category: str  # "toc_mismatch", "structure", "numbering", etc.
    message: str
    chapter_id: Optional[str] = None
    toc_entry: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class ChapterClassification:
    """Classification result for a chapter"""
    chapter_id: str
    chapter_title: str
    section_type: SectionType
    special_type: SpecialSectionType
    confidence: float  # 0.0-1.0
    reasoning: str


@dataclass
class ValidationResult:
    """Complete validation result"""
    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    classifications: List[ChapterClassification] = field(default_factory=list)
    toc_coverage: float = 0.0  # % of chapters in TOC
    structure_quality: float = 0.0  # Overall structure quality score
    summary: str = ""


# =============================================================================
# STRUCTURE VALIDATOR
# =============================================================================

class StructureValidator:
    """
    AI-powered validator for book structure, TOC alignment, and classification
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
        timeout: int = DEFAULT_TIMEOUT,
        api_key: Optional[str] = None
    ):
        """
        Initialize the validator.

        Args:
            model: OpenAI model to use
            temperature: Model temperature (lower = more consistent)
            timeout: Timeout in seconds
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
        """
        self.model = model
        self.temperature = temperature
        self.timeout = timeout
        self.client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))
        logger.info(f"StructureValidator initialized with model: {model}")

    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """
        Validate book structure and TOC alignment.

        Args:
            data: Cleaned book JSON

        Returns:
            ValidationResult with issues and classifications
        """
        logger.info("Starting structure validation...")
        result = ValidationResult(is_valid=True)

        try:
            # Extract structure components
            structure = data.get("structure", {})
            toc_data = structure.get("front_matter", {}).get("toc", [])
            chapters = structure.get("body", {}).get("chapters", [])

            # Run validation checks
            self._validate_toc_coverage(toc_data, chapters, result)
            self._validate_toc_chapter_alignment(toc_data, chapters, result)
            self._validate_chapter_numbering(chapters, result)

            # AI-powered classification
            self._classify_chapters(chapters, result)

            # Calculate overall scores
            self._calculate_scores(result, len(chapters))

            # Generate summary
            result.summary = self._generate_summary(result)

            # Determine if valid (no errors)
            result.is_valid = not any(i.severity == "error" for i in result.issues)

            logger.info(f"Validation complete: {len(result.issues)} issues found")

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            result.is_valid = False
            result.issues.append(ValidationIssue(
                severity="error",
                category="validation_error",
                message=f"Validation process failed: {str(e)}"
            ))

        return result

    def _validate_toc_coverage(
        self,
        toc_data: List[Dict],
        chapters: List[Dict],
        result: ValidationResult
    ):
        """Check what % of chapters are in TOC"""
        if not chapters:
            return

        toc_entries = []
        for toc in toc_data:
            toc_entries.extend(toc.get("entries", []))

        # First check: TOC count vs body count
        toc_count = len(toc_entries)
        body_count = len(chapters)

        if toc_count != body_count:
            # Get chapter numbers to identify specific mismatches
            toc_chapter_numbers = {entry.get("chapter_number", 0) for entry in toc_entries}
            body_chapter_ordinals = {ch.get("ordinal", 0) for ch in chapters}

            missing_from_toc = body_chapter_ordinals - toc_chapter_numbers
            extra_in_toc = toc_chapter_numbers - body_chapter_ordinals

            if missing_from_toc:
                # Find the actual chapters missing
                missing_chapters = [ch for ch in chapters if ch.get("ordinal", 0) in missing_from_toc]
                missing_titles = [ch.get("title", "Unknown") for ch in missing_chapters[:3]]
                message = f"TOC count ({toc_count}) != Body count ({body_count}). Missing from TOC: {len(missing_from_toc)} chapters"
                if missing_titles:
                    message += f" - {', '.join(missing_titles)}"
                    if len(missing_chapters) > 3:
                        message += f" and {len(missing_chapters) - 3} more"

                result.issues.append(ValidationIssue(
                    severity="error",
                    category="toc_count_mismatch",
                    message=message,
                    suggestion="Add missing chapters to TOC"
                ))

            if extra_in_toc:
                result.issues.append(ValidationIssue(
                    severity="error",
                    category="toc_count_mismatch",
                    message=f"TOC has {len(extra_in_toc)} entries not found in body chapters",
                    suggestion="Remove invalid TOC entries or add missing body chapters"
                ))

        # Get chapter refs from TOC
        toc_refs = {entry.get("chapter_ref") for entry in toc_entries}
        chapter_ids = {ch.get("id") for ch in chapters}

        # Find missing chapters
        missing = chapter_ids - toc_refs
        coverage = (len(toc_refs & chapter_ids) / len(chapter_ids)) * 100

        result.toc_coverage = coverage

        if missing and toc_count == body_count:
            # Only report this if counts match but refs don't
            result.issues.append(ValidationIssue(
                severity="warning",
                category="toc_coverage",
                message=f"{len(missing)} chapters missing from TOC ({coverage:.1f}% coverage)",
                suggestion="Add missing chapters to TOC"
            ))

    def _validate_toc_chapter_alignment(
        self,
        toc_data: List[Dict],
        chapters: List[Dict],
        result: ValidationResult
    ):
        """Check if TOC entries accurately match chapter titles"""
        # Build chapter lookup
        chapter_lookup = {ch.get("id"): ch for ch in chapters}

        # Check each TOC entry
        for toc in toc_data:
            for entry in toc.get("entries", []):
                chapter_ref = entry.get("chapter_ref")
                toc_title = entry.get("full_title", "")

                if chapter_ref in chapter_lookup:
                    chapter = chapter_lookup[chapter_ref]
                    chapter_title = chapter.get("title", "")

                    # Check for exact match
                    if toc_title != chapter_title:
                        # Check if it's a partial match
                        if toc_title in chapter_title or chapter_title in toc_title:
                            result.issues.append(ValidationIssue(
                                severity="warning",
                                category="toc_mismatch",
                                message=f"Partial title mismatch",
                                chapter_id=chapter_ref,
                                toc_entry=f"TOC: '{toc_title}' vs Chapter: '{chapter_title}'",
                                suggestion="Verify if TOC entry should match chapter title exactly"
                            ))
                        else:
                            result.issues.append(ValidationIssue(
                                severity="error",
                                category="toc_mismatch",
                                message=f"Title mismatch",
                                chapter_id=chapter_ref,
                                toc_entry=f"TOC: '{toc_title}' vs Chapter: '{chapter_title}'",
                                suggestion="Update TOC or chapter title to match"
                            ))

    def _validate_chapter_numbering(
        self,
        chapters: List[Dict],
        result: ValidationResult
    ):
        """Validate chapter numbering sequences"""
        ordinals = [ch.get("ordinal", 0) for ch in chapters]

        # Check for duplicates
        seen = set()
        duplicates = set()
        for ordinal in ordinals:
            if ordinal in seen:
                duplicates.add(ordinal)
            seen.add(ordinal)

        if duplicates:
            result.issues.append(ValidationIssue(
                severity="error",
                category="numbering",
                message=f"Duplicate ordinals found: {sorted(duplicates)}",
                suggestion="Ensure each chapter has unique ordinal number"
            ))

        # Check for gaps (allowing for TOC at position 1)
        sorted_ordinals = sorted([o for o in ordinals if o > 0])
        if sorted_ordinals:
            expected_range = range(sorted_ordinals[0], sorted_ordinals[-1] + 1)
            missing = set(expected_range) - set(sorted_ordinals)
            if missing:
                result.issues.append(ValidationIssue(
                    severity="warning",
                    category="numbering",
                    message=f"Gaps in ordinal sequence: {sorted(missing)}",
                    suggestion="Verify if missing ordinals are intentional"
                ))

    def _classify_chapters(
        self,
        chapters: List[Dict],
        result: ValidationResult
    ):
        """Use AI to classify chapters as front_matter, body, or back_matter"""
        if not chapters:
            return

        # Prepare chapter titles for classification
        chapter_data = [
            {
                "id": ch.get("id"),
                "title": ch.get("title", ""),
                "ordinal": ch.get("ordinal", 0)
            }
            for ch in chapters[:50]  # Limit to first 50 for performance
        ]

        try:
            # Use OpenAI to classify chapters
            prompt = self._build_classification_prompt(chapter_data)

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert in Chinese novel structure and classification.
Your task is to classify chapters as front matter (prefaces, introductions),
body (main story), or back matter (afterwords, appendices).

Identify special sections:
- 自序, 前言, 序 = preface
- 引言, 序章 = introduction
- 序幕, 楔子 = prologue
- 後記, 跋 = afterword
- 附錄 = appendix
- 作者註, 說明 = author_note
- 尾聲 = epilogue

Return JSON array with: {id, section_type, special_type, confidence, reasoning}"""
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                timeout=self.timeout,
                response_format={"type": "json_object"}
            )

            # Parse response
            response_data = json.loads(response.choices[0].message.content)
            classifications = response_data.get("classifications", [])

            for classification in classifications:
                result.classifications.append(ChapterClassification(
                    chapter_id=classification["id"],
                    chapter_title=classification.get("title", ""),
                    section_type=SectionType(classification["section_type"]),
                    special_type=SpecialSectionType(classification["special_type"]),
                    confidence=classification.get("confidence", 0.0),
                    reasoning=classification.get("reasoning", "")
                ))

            # Check for misplaced sections
            self._validate_section_placement(result)

        except Exception as e:
            logger.error(f"Chapter classification failed: {e}")
            result.issues.append(ValidationIssue(
                severity="warning",
                category="classification",
                message=f"AI classification failed: {str(e)}",
                suggestion="Manual review recommended"
            ))

    def _build_classification_prompt(self, chapter_data: List[Dict]) -> str:
        """Build prompt for chapter classification"""
        chapters_text = "\n".join([
            f"{i+1}. [{ch['id']}] Ordinal: {ch['ordinal']} - Title: {ch['title']}"
            for i, ch in enumerate(chapter_data)
        ])

        return f"""Classify these Chinese novel chapters:

{chapters_text}

Return JSON:
{{
  "classifications": [
    {{
      "id": "chapter_0001",
      "title": "...",
      "section_type": "front_matter|body|back_matter",
      "special_type": "preface|introduction|prologue|afterword|appendix|author_note|epilogue|main_chapter",
      "confidence": 0.95,
      "reasoning": "Contains '後記' indicating afterword"
    }}
  ]
}}"""

    def _validate_section_placement(self, result: ValidationResult):
        """Check if sections are in correct order (front→body→back)"""
        # Group by section type
        section_order = []
        for classification in result.classifications:
            section_order.append(classification.section_type)

        # Check order is maintained
        prev_section = None
        for i, section in enumerate(section_order):
            if prev_section:
                # Check if we're going backwards
                type_order = [SectionType.FRONT_MATTER, SectionType.BODY, SectionType.BACK_MATTER]
                prev_idx = type_order.index(prev_section)
                curr_idx = type_order.index(section)

                if curr_idx < prev_idx:
                    result.issues.append(ValidationIssue(
                        severity="warning",
                        category="structure",
                        message=f"Section order issue: {section.value} after {prev_section.value}",
                        chapter_id=result.classifications[i].chapter_id,
                        suggestion="Consider reordering sections: front_matter → body → back_matter"
                    ))

            prev_section = section

    def _calculate_scores(self, result: ValidationResult, total_chapters: int):
        """Calculate overall quality scores"""
        # Structure quality based on issues
        error_count = sum(1 for i in result.issues if i.severity == "error")
        warning_count = sum(1 for i in result.issues if i.severity == "warning")

        # Deduct points for issues
        quality = 100.0
        quality -= error_count * 20  # Errors are serious
        quality -= warning_count * 5  # Warnings are less serious

        result.structure_quality = max(0.0, quality)

    def _generate_summary(self, result: ValidationResult) -> str:
        """Generate human-readable summary"""
        error_count = sum(1 for i in result.issues if i.severity == "error")
        warning_count = sum(1 for i in result.issues if i.severity == "warning")
        info_count = sum(1 for i in result.issues if i.severity == "info")

        summary_parts = []

        if result.is_valid:
            summary_parts.append("✓ Structure validation PASSED")
        else:
            summary_parts.append("✗ Structure validation FAILED")

        summary_parts.append(f"TOC Coverage: {result.toc_coverage:.1f}%")
        summary_parts.append(f"Quality Score: {result.structure_quality:.1f}/100")

        if error_count:
            summary_parts.append(f"Errors: {error_count}")
        if warning_count:
            summary_parts.append(f"Warnings: {warning_count}")
        if info_count:
            summary_parts.append(f"Info: {info_count}")

        # Classification summary
        if result.classifications:
            front_count = sum(1 for c in result.classifications if c.section_type == SectionType.FRONT_MATTER)
            body_count = sum(1 for c in result.classifications if c.section_type == SectionType.BODY)
            back_count = sum(1 for c in result.classifications if c.section_type == SectionType.BACK_MATTER)

            summary_parts.append(f"Sections: {front_count} front + {body_count} body + {back_count} back")

        return " | ".join(summary_parts)

    def process_file(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        save_report: bool = True
    ) -> ValidationResult:
        """
        Validate a book file.

        Args:
            input_path: Path to cleaned JSON file
            output_path: Optional path to save validation report
            save_report: Whether to save detailed report

        Returns:
            ValidationResult
        """
        logger.info(f"Processing file: {input_path}")

        # Load file
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Validate
        result = self.validate(data)

        # Save report if requested
        if save_report:
            if not output_path:
                input_file = Path(input_path)
                output_path = input_file.parent / f"{input_file.stem}_validation.json"

            self._save_report(result, output_path)
            logger.info(f"Validation report saved to: {output_path}")

        return result

    def _save_report(self, result: ValidationResult, output_path: str):
        """Save validation report to JSON"""
        report = {
            "is_valid": result.is_valid,
            "summary": result.summary,
            "scores": {
                "toc_coverage": result.toc_coverage,
                "structure_quality": result.structure_quality
            },
            "issues": [
                {
                    "severity": issue.severity,
                    "category": issue.category,
                    "message": issue.message,
                    "chapter_id": issue.chapter_id,
                    "toc_entry": issue.toc_entry,
                    "suggestion": issue.suggestion
                }
                for issue in result.issues
            ],
            "classifications": [
                {
                    "chapter_id": c.chapter_id,
                    "chapter_title": c.chapter_title,
                    "section_type": c.section_type.value,
                    "special_type": c.special_type.value,
                    "confidence": c.confidence,
                    "reasoning": c.reasoning
                }
                for c in result.classifications
            ]
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)


# =============================================================================
# CLI
# =============================================================================

def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate book structure and TOC alignment"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Input cleaned JSON file"
    )
    parser.add_argument(
        "--output",
        help="Output validation report path (default: input_validation.json)"
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"OpenAI model (default: {DEFAULT_MODEL})"
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Don't save validation report"
    )

    args = parser.parse_args()

    # Validate
    validator = StructureValidator(model=args.model)
    result = validator.process_file(
        args.input,
        args.output,
        save_report=not args.no_report
    )

    # Print summary
    print("\n" + "="*80)
    print(result.summary)
    print("="*80)

    # Print issues
    if result.issues:
        print("\nISSUES FOUND:")
        for issue in result.issues:
            icon = "✗" if issue.severity == "error" else "⚠" if issue.severity == "warning" else "ℹ"
            print(f"\n{icon} [{issue.severity.upper()}] {issue.category}")
            print(f"  {issue.message}")
            if issue.chapter_id:
                print(f"  Chapter: {issue.chapter_id}")
            if issue.toc_entry:
                print(f"  Details: {issue.toc_entry}")
            if issue.suggestion:
                print(f"  💡 {issue.suggestion}")

    # Print classifications
    if result.classifications:
        print("\n\nCHAPTER CLASSIFICATIONS:")
        for c in result.classifications[:10]:  # Show first 10
            print(f"  {c.chapter_id}: {c.special_type.value} ({c.section_type.value}) - {c.confidence:.0%}")

    return 0 if result.is_valid else 1


if __name__ == "__main__":
    exit(main())
