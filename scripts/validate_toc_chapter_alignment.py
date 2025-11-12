#!/usr/bin/env python3
"""
TOC/Chapter Alignment Validator

Comprehensive validation that:
1. Extracts actual chapter headings from content_blocks
2. Compares with TOC entries
3. Uses OpenAI for semantic validation of mismatches
4. Generates detailed report of gaps/errors

This addresses cases where:
- Book metadata is treated as a chapter
- Actual chapter headings are buried in content
- TOC entries don't map to actual chapters
- Chapters are missing from source data
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class ChapterHeading:
    """Extracted chapter heading information"""
    chapter_index: int
    chapter_id: str
    chapter_title: str  # From metadata
    actual_heading: Optional[str] = None  # Extracted from content_blocks
    heading_block_id: Optional[str] = None
    chapter_number: Optional[int] = None  # Parsed from heading
    classification: str = "unknown"
    confidence: float = 0.0


@dataclass
class TOCEntry:
    """TOC entry information"""
    toc_index: int
    full_title: str
    chapter_title: str
    chapter_number: int
    chapter_id: str


@dataclass
class AlignmentIssue:
    """An issue found in TOC/chapter alignment"""
    severity: str  # "error", "warning", "info"
    issue_type: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    suggested_fix: Optional[str] = None
    confidence: float = 0.0


@dataclass
class ValidationReport:
    """Complete validation report"""
    is_valid: bool
    toc_count: int
    chapter_count: int
    matched_count: int
    issues: List[AlignmentIssue] = field(default_factory=list)
    toc_entries: List[TOCEntry] = field(default_factory=list)
    chapter_headings: List[ChapterHeading] = field(default_factory=list)
    summary: str = ""
    confidence_score: float = 0.0


class TOCChapterValidator:
    """Comprehensive TOC/Chapter alignment validator"""

    def __init__(self, use_ai: bool = True, model: str = "gpt-4o-mini", temperature: float = 0.1):
        """
        Initialize validator.

        Args:
            use_ai: Use OpenAI for semantic validation
            model: OpenAI model to use
            temperature: Temperature for generation (low for consistency)
        """
        self.use_ai = use_ai
        self.model = model
        self.temperature = temperature
        self.client = None

        if use_ai:
            api_key = os.environ.get("OPENAI_API_KEY")
            if api_key:
                self.client = OpenAI(api_key=api_key)
                logger.info(f"OpenAI client initialized with model: {model}")
            else:
                logger.warning("OPENAI_API_KEY not found, AI validation disabled")
                self.use_ai = False

    def extract_chapter_headings(self, chapters: List[Dict[str, Any]]) -> List[ChapterHeading]:
        """
        Extract actual chapter headings from content_blocks.

        This looks for the first heading-type block in each chapter
        to determine what the chapter is actually about.
        """
        headings = []

        for idx, chapter in enumerate(chapters):
            chapter_id = chapter.get('id', f'chapter_{idx:04d}')
            chapter_title = chapter.get('title', '')
            content_blocks = chapter.get('content_blocks', [])
            classification = chapter.get('metadata', {}).get('classification', 'unknown')
            confidence = chapter.get('metadata', {}).get('confidence', 0.0)

            # Find first heading block
            actual_heading = None
            heading_block_id = None

            for block in content_blocks:
                if block.get('type') == 'heading':
                    actual_heading = block.get('content', '').strip()
                    heading_block_id = block.get('id')
                    break

            # If no heading found, check if title itself looks like a chapter heading
            if not actual_heading:
                # Use chapter title as heading if it matches chapter pattern
                if re.search(r'第[一二三四五六七八九十廿卅卌百千]+[章回]', chapter_title):
                    actual_heading = chapter_title

            # Parse chapter number from heading
            chapter_num = self._parse_chinese_number(actual_heading or chapter_title)

            headings.append(ChapterHeading(
                chapter_index=idx,
                chapter_id=chapter_id,
                chapter_title=chapter_title,
                actual_heading=actual_heading,
                heading_block_id=heading_block_id,
                chapter_number=chapter_num,
                classification=classification,
                confidence=confidence
            ))

        return headings

    def extract_toc_entries(self, toc_data: Any) -> List[TOCEntry]:
        """Extract TOC entries from front_matter.toc"""
        entries = []

        if not toc_data:
            return entries

        # Handle different TOC formats
        if isinstance(toc_data, list):
            for idx, entry in enumerate(toc_data):
                if isinstance(entry, dict):
                    # Structured TOC entry
                    if 'chapter_number' in entry:
                        entries.append(TOCEntry(
                            toc_index=idx,
                            full_title=entry.get('full_title', ''),
                            chapter_title=entry.get('chapter_title', ''),
                            chapter_number=entry.get('chapter_number', idx + 1),
                            chapter_id=entry.get('chapter_id', f'chapter_{idx+1:04d}')
                        ))

        return entries

    def validate(self, cleaned_json: Dict[str, Any]) -> ValidationReport:
        """
        Perform comprehensive validation.

        Args:
            cleaned_json: Cleaned book JSON

        Returns:
            ValidationReport with detailed issues
        """
        logger.info("Starting comprehensive TOC/Chapter validation...")

        report = ValidationReport(is_valid=True, toc_count=0, chapter_count=0, matched_count=0)

        # Extract TOC entries
        toc_data = cleaned_json.get('structure', {}).get('front_matter', {}).get('toc', [])
        report.toc_entries = self.extract_toc_entries(toc_data)
        report.toc_count = len(report.toc_entries)

        # Extract chapter headings
        chapters = cleaned_json.get('structure', {}).get('body', {}).get('chapters', [])
        report.chapter_headings = self.extract_chapter_headings(chapters)
        report.chapter_count = len(report.chapter_headings)

        # Check basic counts
        if report.toc_count == 0:
            report.issues.append(AlignmentIssue(
                severity="error",
                issue_type="missing_toc",
                message="No TOC found in front_matter"
            ))
            report.is_valid = False

        if report.chapter_count == 0:
            report.issues.append(AlignmentIssue(
                severity="error",
                issue_type="missing_chapters",
                message="No chapters found in body"
            ))
            report.is_valid = False

        # Compare counts
        if report.toc_count != report.chapter_count:
            report.issues.append(AlignmentIssue(
                severity="warning",
                issue_type="count_mismatch",
                message=f"TOC has {report.toc_count} entries but body has {report.chapter_count} chapters",
                details={
                    "toc_count": report.toc_count,
                    "chapter_count": report.chapter_count,
                    "difference": abs(report.toc_count - report.chapter_count)
                }
            ))

        # Detailed alignment checking
        self._check_alignment(report)

        # AI semantic validation if enabled
        if self.use_ai and self.client:
            self._ai_validate_mismatches(report)

        # Calculate confidence score
        if report.toc_count > 0:
            report.confidence_score = (report.matched_count / report.toc_count) * 100
        else:
            report.confidence_score = 0.0

        # Determine validity
        error_count = sum(1 for issue in report.issues if issue.severity == 'error')
        report.is_valid = error_count == 0

        # Build summary
        report.summary = self._build_summary(report)

        logger.info(f"Validation complete: {report.summary}")

        return report

    def _check_alignment(self, report: ValidationReport):
        """Check detailed alignment between TOC and chapters"""

        # Build chapter number map
        chapter_by_number = {}
        for heading in report.chapter_headings:
            if heading.chapter_number:
                if heading.chapter_number in chapter_by_number:
                    # Duplicate chapter number
                    report.issues.append(AlignmentIssue(
                        severity="error",
                        issue_type="duplicate_chapter_number",
                        message=f"Chapter number {heading.chapter_number} appears multiple times",
                        details={
                            "chapter_number": heading.chapter_number,
                            "chapters": [heading.chapter_id, chapter_by_number[heading.chapter_number].chapter_id]
                        }
                    ))
                else:
                    chapter_by_number[heading.chapter_number] = heading

        # Check each TOC entry
        for toc_entry in report.toc_entries:
            expected_num = toc_entry.chapter_number

            if expected_num not in chapter_by_number:
                # Missing chapter
                report.issues.append(AlignmentIssue(
                    severity="error",
                    issue_type="missing_chapter",
                    message=f"TOC references chapter {expected_num} '{toc_entry.chapter_title}' but it's not in body",
                    details={
                        "toc_entry": toc_entry.full_title,
                        "chapter_number": expected_num,
                        "toc_index": toc_entry.toc_index
                    },
                    suggested_fix="Check if chapter is missing from source EPUB or was incorrectly filtered"
                ))
            else:
                # Chapter exists, check title match
                chapter = chapter_by_number[expected_num]
                toc_title = toc_entry.chapter_title
                actual_heading = chapter.actual_heading or chapter.chapter_title

                # Simple heuristic: check if titles are similar
                if not self._titles_match(toc_title, actual_heading):
                    report.issues.append(AlignmentIssue(
                        severity="warning",
                        issue_type="title_mismatch",
                        message=f"TOC and chapter titles don't match for chapter {expected_num}",
                        details={
                            "chapter_number": expected_num,
                            "toc_title": toc_title,
                            "actual_title": actual_heading,
                            "toc_full": toc_entry.full_title
                        }
                    ))
                else:
                    report.matched_count += 1

        # Check for chapters not in TOC
        toc_numbers = {entry.chapter_number for entry in report.toc_entries}
        for heading in report.chapter_headings:
            if heading.chapter_number and heading.chapter_number not in toc_numbers:
                report.issues.append(AlignmentIssue(
                    severity="warning",
                    issue_type="chapter_not_in_toc",
                    message=f"Chapter {heading.chapter_number} exists in body but not in TOC",
                    details={
                        "chapter_number": heading.chapter_number,
                        "chapter_title": heading.chapter_title,
                        "chapter_id": heading.chapter_id
                    }
                ))

        # Check for sequence gaps
        if chapter_by_number:
            numbers = sorted(chapter_by_number.keys())
            for i in range(len(numbers) - 1):
                if numbers[i+1] - numbers[i] > 1:
                    missing = list(range(numbers[i] + 1, numbers[i+1]))
                    report.issues.append(AlignmentIssue(
                        severity="info",
                        issue_type="sequence_gap",
                        message=f"Chapter sequence gap: missing chapters {missing}",
                        details={
                            "missing_numbers": missing,
                            "before": numbers[i],
                            "after": numbers[i+1]
                        },
                        suggested_fix="This may be intentional (missing from source) or a data issue"
                    ))

    def _ai_validate_mismatches(self, report: ValidationReport):
        """Use AI to validate mismatches semantically"""
        if not self.client:
            return

        # Find title mismatches to validate
        mismatches = [
            issue for issue in report.issues
            if issue.issue_type == "title_mismatch"
        ]

        if not mismatches:
            return

        logger.info(f"AI validating {len(mismatches)} title mismatches...")

        # Process in batches
        batch_size = 10
        for i in range(0, len(mismatches), batch_size):
            batch = mismatches[i:i+batch_size]
            self._ai_validate_batch(batch)

    def _ai_validate_batch(self, mismatches: List[AlignmentIssue]):
        """Validate a batch of mismatches with AI"""
        if not self.client:
            return

        # Build prompt
        pairs_text = []
        for idx, issue in enumerate(mismatches):
            details = issue.details
            pairs_text.append(
                f"{idx+1}. TOC: '{details.get('toc_title')}' | "
                f"Chapter: '{details.get('actual_title')}' "
                f"(Ch {details.get('chapter_number')})"
            )

        prompt = f"""You are validating Table of Contents (TOC) entries against actual chapter titles in a Chinese wuxia novel.

For each pair, determine if the mismatch is:
1. "real_mismatch" - Genuinely different chapters/content
2. "minor_difference" - Same chapter, just formatting/spacing differences
3. "transcription_error" - Likely a typo or character variant

Consider:
- Chinese numeral variations (第一章, 第廿一章)
- Spacing and punctuation differences
- Character variants (繁/簡, 異體字)
- Context clues in titles

Pairs to validate:
{chr(10).join(pairs_text)}

Respond with JSON:
{{
  "validations": [
    {{
      "pair_number": <1-{len(mismatches)}>,
      "verdict": "real_mismatch" | "minor_difference" | "transcription_error",
      "confidence": <0.0-1.0>,
      "reasoning": "brief explanation",
      "suggested_fix": "what the correct title should be (if applicable)"
    }}
  ]
}}
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a precise book structure validator. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content
            data = json.loads(content)

            # Update issues with AI results
            for validation in data.get('validations', []):
                pair_num = validation.get('pair_number', 1) - 1
                if 0 <= pair_num < len(mismatches):
                    issue = mismatches[pair_num]
                    verdict = validation.get('verdict', 'unknown')

                    # Downgrade severity if minor difference
                    if verdict == "minor_difference":
                        issue.severity = "info"
                        issue.message += " [AI: Minor formatting difference]"
                    elif verdict == "transcription_error":
                        issue.severity = "warning"
                        issue.message += " [AI: Likely transcription error]"
                        if validation.get('suggested_fix'):
                            issue.suggested_fix = validation['suggested_fix']

                    issue.confidence = validation.get('confidence', 0.0)
                    issue.details['ai_reasoning'] = validation.get('reasoning', '')

        except Exception as e:
            logger.error(f"AI validation failed: {e}")

    def _titles_match(self, title1: str, title2: str) -> bool:
        """Check if two titles match (fuzzy)"""
        if not title1 or not title2:
            return False

        # Normalize
        t1 = re.sub(r'\s+', '', title1.lower())
        t2 = re.sub(r'\s+', '', title2.lower())

        # Exact match
        if t1 == t2:
            return True

        # Contains match (one is substring of other)
        if t1 in t2 or t2 in t1:
            return True

        return False

    def _parse_chinese_number(self, text: str) -> Optional[int]:
        """Parse Chinese chapter number from text"""
        if not text:
            return None

        # Match 第N章/回 pattern
        match = re.search(r'第([一二三四五六七八九十廿卅卌百千]+)[章回]', text)
        if not match:
            return None

        numeral_text = match.group(1)

        # Chinese numeral mapping
        numerals = {
            '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
            '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
            '廿': 20, '卅': 30, '卌': 40, '百': 100, '千': 1000
        }

        # Handle special cases
        if '廿' in numeral_text:
            base = 20
            remainder = numeral_text.replace('廿', '')
            if remainder:
                for char in remainder:
                    if char in numerals:
                        base += numerals[char]
            return base

        if '卅' in numeral_text:
            base = 30
            remainder = numeral_text.replace('卅', '')
            if remainder:
                for char in remainder:
                    if char in numerals:
                        base += numerals[char]
            return base

        if '卌' in numeral_text:
            base = 40
            remainder = numeral_text.replace('卌', '')
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

    def _build_summary(self, report: ValidationReport) -> str:
        """Build human-readable summary"""
        lines = []

        lines.append(f"TOC Entries: {report.toc_count}")
        lines.append(f"Body Chapters: {report.chapter_count}")
        lines.append(f"Matched: {report.matched_count}")
        lines.append(f"Confidence: {report.confidence_score:.1f}%")

        error_count = sum(1 for i in report.issues if i.severity == 'error')
        warning_count = sum(1 for i in report.issues if i.severity == 'warning')
        info_count = sum(1 for i in report.issues if i.severity == 'info')

        if error_count:
            lines.append(f"Errors: {error_count}")
        if warning_count:
            lines.append(f"Warnings: {warning_count}")
        if info_count:
            lines.append(f"Info: {info_count}")

        return " | ".join(lines)

    def validate_file(self, json_file: str, save_report: bool = True) -> ValidationReport:
        """
        Validate TOC alignment from a file.

        Args:
            json_file: Path to cleaned JSON file
            save_report: Save detailed report to file

        Returns:
            ValidationReport
        """
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        report = self.validate(data)

        if save_report:
            report_file = Path(json_file).parent / f"{Path(json_file).stem}_validation_report.json"
            self._save_report(report, report_file)
            logger.info(f"Report saved to: {report_file}")

        return report

    def _save_report(self, report: ValidationReport, output_path: Path):
        """Save validation report to JSON"""
        report_data = {
            "is_valid": report.is_valid,
            "summary": report.summary,
            "confidence_score": report.confidence_score,
            "counts": {
                "toc_entries": report.toc_count,
                "body_chapters": report.chapter_count,
                "matched": report.matched_count
            },
            "issues": [
                {
                    "severity": issue.severity,
                    "type": issue.issue_type,
                    "message": issue.message,
                    "details": issue.details,
                    "suggested_fix": issue.suggested_fix,
                    "confidence": issue.confidence
                }
                for issue in report.issues
            ],
            "toc_entries": [
                {
                    "index": entry.toc_index,
                    "full_title": entry.full_title,
                    "chapter_title": entry.chapter_title,
                    "chapter_number": entry.chapter_number,
                    "chapter_id": entry.chapter_id
                }
                for entry in report.toc_entries
            ],
            "chapter_headings": [
                {
                    "index": heading.chapter_index,
                    "chapter_id": heading.chapter_id,
                    "chapter_title": heading.chapter_title,
                    "actual_heading": heading.actual_heading,
                    "chapter_number": heading.chapter_number,
                    "classification": heading.classification,
                    "confidence": heading.confidence
                }
                for heading in report.chapter_headings
            ]
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)


def print_report(report: ValidationReport):
    """Print formatted validation report"""
    print(f"\n{'='*80}")
    print(f"TOC/CHAPTER ALIGNMENT VALIDATION REPORT")
    print(f"{'='*80}\n")

    print(f"Summary: {report.summary}")
    print(f"Valid: {'✓ Yes' if report.is_valid else '✗ No'}")
    print(f"\n")

    # TOC Overview
    print(f"TOC ENTRIES ({report.toc_count}):")
    for entry in report.toc_entries[:5]:
        print(f"  {entry.chapter_number:2d}. {entry.full_title}")
    if report.toc_count > 5:
        print(f"  ... and {report.toc_count - 5} more")

    print(f"\n")

    # Chapter Overview
    print(f"BODY CHAPTERS ({report.chapter_count}):")
    for heading in report.chapter_headings[:5]:
        num = heading.chapter_number or '?'
        title = heading.actual_heading or heading.chapter_title
        print(f"  {num:>2}. {title} [{heading.classification}]")
    if report.chapter_count > 5:
        print(f"  ... and {report.chapter_count - 5} more")

    print(f"\n")

    # Issues
    if report.issues:
        print(f"ISSUES FOUND ({len(report.issues)}):")
        print(f"{'='*80}\n")

        for issue in report.issues:
            icon = "✗" if issue.severity == "error" else "⚠" if issue.severity == "warning" else "ℹ"
            print(f"{icon} [{issue.severity.upper()}] {issue.issue_type}")
            print(f"   {issue.message}")

            if issue.details:
                for key, value in issue.details.items():
                    if key != 'ai_reasoning':
                        print(f"   - {key}: {value}")

            if issue.suggested_fix:
                print(f"   💡 Suggested fix: {issue.suggested_fix}")

            if 'ai_reasoning' in issue.details:
                print(f"   🤖 AI: {issue.details['ai_reasoning']}")

            print()
    else:
        print("✓ No issues found!\n")

    print(f"{'='*80}\n")


def main():
    """CLI entry point"""
    import sys
    import argparse

    parser = argparse.ArgumentParser(
        description='Validate TOC/Chapter alignment in cleaned JSON'
    )
    parser.add_argument('input', help='Path to cleaned JSON file')
    parser.add_argument('--no-ai', action='store_true', help='Disable AI validation')
    parser.add_argument('--no-report', action='store_true', help='Do not save report file')

    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"Error: File not found: {args.input}")
        return 1

    validator = TOCChapterValidator(use_ai=not args.no_ai)
    report = validator.validate_file(args.input, save_report=not args.no_report)

    print_report(report)

    return 0 if report.is_valid else 1


if __name__ == "__main__":
    exit(main())
