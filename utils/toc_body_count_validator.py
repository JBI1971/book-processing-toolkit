#!/usr/bin/env python3
"""
TOC/Body Count Validator
Validates that TOC entries count matches body chapters count and identifies missing chapters

Usage:
    # Direct import for programmatic use
    from utils.toc_body_count_validator import validate_toc_body_alignment

    result = validate_toc_body_alignment(cleaned_json)
    if not result['valid']:
        print(f"Missing from TOC: {result['missing_chapters']}")

    # CLI usage
    python utils/toc_body_count_validator.py input.json --use-alignment

This validator detects cases where:
- TOC has fewer entries than body chapters (missing chapters)
- TOC has more entries than body chapters (extra/invalid references)
- Specific chapter numbers are missing from TOC
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class CountMismatchIssue:
    """Represents a chapter missing from or extra in TOC"""
    issue_type: str  # "missing_from_toc" or "extra_in_toc"
    chapter_id: str
    chapter_number: int
    chapter_title: str
    severity: str = "error"  # "error" or "warning"


@dataclass
class CountValidationResult:
    """Result of TOC/body count validation"""
    is_valid: bool
    toc_count: int
    body_count: int
    issues: List[CountMismatchIssue] = field(default_factory=list)
    summary: str = ""

    @property
    def missing_from_toc_count(self) -> int:
        """Count of chapters in body but not in TOC"""
        return sum(1 for i in self.issues if i.issue_type == "missing_from_toc")

    @property
    def extra_in_toc_count(self) -> int:
        """Count of TOC entries not in body"""
        return sum(1 for i in self.issues if i.issue_type == "extra_in_toc")


class TOCBodyCountValidator:
    """
    Validates that TOC entries count matches body chapters count.
    Identifies which specific chapters are missing from or extra in TOC.
    """

    def validate_toc_body_alignment(self, cleaned_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate that TOC entries match body chapters.

        This method provides a simplified interface that returns a dict with:
        - valid: bool
        - toc_count: int
        - body_count: int
        - missing_from_toc: set of chapter numbers in body but not TOC
        - extra_in_toc: set of chapter numbers in TOC but not body
        - missing_chapters: list of dicts with {chapter_num, title, id} for chapters in body missing from TOC

        Args:
            cleaned_json: Cleaned book JSON

        Returns:
            Dict with validation results
        """
        try:
            # Extract TOC entries
            toc_data = cleaned_json.get('structure', {}).get('front_matter', {}).get('toc', [])
            if not toc_data or len(toc_data) == 0:
                return {
                    "valid": False,
                    "toc_count": 0,
                    "body_count": 0,
                    "missing_from_toc": [],
                    "extra_in_toc": [],
                    "missing_chapters": [],
                    "error": "No TOC found in structure"
                }

            toc_entries = toc_data[0].get('entries', [])
            toc_count = len(toc_entries)

            # Extract body chapters
            chapters = cleaned_json.get('structure', {}).get('body', {}).get('chapters', [])
            body_count = len(chapters)

            if body_count == 0:
                return {
                    "valid": False,
                    "toc_count": toc_count,
                    "body_count": 0,
                    "missing_from_toc": [],
                    "extra_in_toc": [],
                    "missing_chapters": [],
                    "error": "No chapters found in body"
                }

            # Get chapter numbers from both
            toc_chapter_nums = self._extract_toc_chapter_numbers(toc_entries)
            body_chapter_info = self._extract_body_chapter_info(chapters)
            body_chapter_nums = {info['ordinal'] for info in body_chapter_info}

            # Find mismatches
            missing_from_toc = body_chapter_nums - toc_chapter_nums
            extra_in_toc = toc_chapter_nums - body_chapter_nums

            # Get details of missing chapters
            missing_chapters = []
            if missing_from_toc:
                for ch in body_chapter_info:
                    if ch['ordinal'] in missing_from_toc:
                        missing_chapters.append({
                            "chapter_num": ch['ordinal'],
                            "title": ch['title'],
                            "id": ch['id']
                        })

            # Determine validity
            is_valid = (toc_count == body_count and not missing_from_toc and not extra_in_toc)

            return {
                "valid": is_valid,
                "toc_count": toc_count,
                "body_count": body_count,
                "missing_from_toc": sorted(list(missing_from_toc)),
                "extra_in_toc": sorted(list(extra_in_toc)),
                "missing_chapters": missing_chapters
            }

        except Exception as e:
            logger.error(f"TOC/body alignment validation failed: {e}")
            return {
                "valid": False,
                "toc_count": 0,
                "body_count": 0,
                "missing_from_toc": [],
                "extra_in_toc": [],
                "missing_chapters": [],
                "error": str(e)
            }

    def validate(self, cleaned_json: Dict[str, Any]) -> CountValidationResult:
        """
        Validate TOC/body chapter count alignment.

        Args:
            cleaned_json: Cleaned book JSON with TOC and chapters

        Returns:
            CountValidationResult with issues found
        """
        logger.info("Starting TOC/body count validation...")

        try:
            # Extract TOC entries
            toc_data = cleaned_json.get('structure', {}).get('front_matter', {}).get('toc', [])
            if not toc_data or len(toc_data) == 0:
                return CountValidationResult(
                    is_valid=False,
                    toc_count=0,
                    body_count=0,
                    summary="❌ No TOC found in structure"
                )

            toc_entries = toc_data[0].get('entries', [])
            toc_count = len(toc_entries)

            # Extract body chapters
            chapters = cleaned_json.get('structure', {}).get('body', {}).get('chapters', [])
            body_count = len(chapters)

            if body_count == 0:
                return CountValidationResult(
                    is_valid=False,
                    toc_count=toc_count,
                    body_count=0,
                    summary="❌ No chapters found in body"
                )

            # Build lookup sets
            toc_chapter_numbers = self._extract_toc_chapter_numbers(toc_entries)
            body_chapter_info = self._extract_body_chapter_info(chapters)
            body_chapter_numbers = {info['ordinal'] for info in body_chapter_info}

            # Find mismatches
            missing_from_toc = body_chapter_numbers - toc_chapter_numbers
            extra_in_toc = toc_chapter_numbers - body_chapter_numbers

            # Create result
            result = CountValidationResult(
                is_valid=(toc_count == body_count and not missing_from_toc and not extra_in_toc),
                toc_count=toc_count,
                body_count=body_count
            )

            # Build issues list with full chapter details
            for chapter_info in body_chapter_info:
                if chapter_info['ordinal'] in missing_from_toc:
                    result.issues.append(CountMismatchIssue(
                        issue_type="missing_from_toc",
                        chapter_id=chapter_info['id'],
                        chapter_number=chapter_info['ordinal'],
                        chapter_title=chapter_info['title'],
                        severity="error"
                    ))

            # For extra TOC entries, we need to find them
            for toc_entry in toc_entries:
                toc_num = toc_entry.get('chapter_number', 0)
                if toc_num in extra_in_toc:
                    result.issues.append(CountMismatchIssue(
                        issue_type="extra_in_toc",
                        chapter_id=toc_entry.get('chapter_ref', 'unknown'),
                        chapter_number=toc_num,
                        chapter_title=toc_entry.get('full_title', 'Unknown'),
                        severity="error"
                    ))

            # Build summary
            result.summary = self._build_summary(result)

            if result.is_valid:
                logger.info(f"✓ TOC/body count validation PASSED: {toc_count} entries match {body_count} chapters")
            else:
                logger.warning(f"✗ TOC/body count validation FAILED: {toc_count} TOC entries vs {body_count} body chapters")

            return result

        except Exception as e:
            logger.error(f"Count validation failed: {e}")
            return CountValidationResult(
                is_valid=False,
                toc_count=0,
                body_count=0,
                summary=f"❌ Validation error: {str(e)}"
            )

    def _extract_toc_chapter_numbers(self, toc_entries: List[Dict]) -> Set[int]:
        """Extract chapter numbers from TOC entries"""
        numbers = set()
        for entry in toc_entries:
            chapter_num = entry.get('chapter_number', 0)
            # Handle both int and string types
            try:
                chapter_num = int(chapter_num) if chapter_num else 0
            except (ValueError, TypeError):
                logger.warning(f"Invalid chapter_number: {chapter_num}")
                continue
            if chapter_num > 0:
                numbers.add(chapter_num)
        return numbers

    def _extract_body_chapter_info(self, chapters: List[Dict]) -> List[Dict]:
        """Extract chapter info from body chapters"""
        info_list = []
        for chapter in chapters:
            ordinal = chapter.get('ordinal', 0)
            # Handle both int and string types
            try:
                ordinal = int(ordinal) if ordinal else 0
            except (ValueError, TypeError):
                logger.warning(f"Invalid ordinal: {ordinal} for chapter {chapter.get('id', 'unknown')}")
                ordinal = 0
            info_list.append({
                'id': chapter.get('id', 'unknown'),
                'ordinal': ordinal,
                'title': chapter.get('title', 'Unknown')
            })
        return info_list

    def _build_summary(self, result: CountValidationResult) -> str:
        """Build human-readable summary"""
        if result.is_valid:
            return f"✓ TOC/Body counts match: {result.toc_count} entries"

        summary_parts = [f"❌ TOC/Body Mismatch"]
        summary_parts.append(f"TOC entries: {result.toc_count}")
        summary_parts.append(f"Body chapters: {result.body_count}")

        if result.missing_from_toc_count > 0:
            missing_chapters = [i.chapter_title for i in result.issues if i.issue_type == "missing_from_toc"]
            summary_parts.append(f"Missing from TOC: {result.missing_from_toc_count} chapter(s)")
            for chapter_title in missing_chapters[:3]:  # Show first 3
                summary_parts.append(f"  - {chapter_title}")
            if len(missing_chapters) > 3:
                summary_parts.append(f"  ... and {len(missing_chapters) - 3} more")

        if result.extra_in_toc_count > 0:
            extra_chapters = [i.chapter_title for i in result.issues if i.issue_type == "extra_in_toc"]
            summary_parts.append(f"Extra in TOC (not in body): {result.extra_in_toc_count} entry/entries")
            for chapter_title in extra_chapters[:3]:
                summary_parts.append(f"  - {chapter_title}")
            if len(extra_chapters) > 3:
                summary_parts.append(f"  ... and {len(extra_chapters) - 3} more")

        return "\n".join(summary_parts)

    def validate_file(self, json_file: str) -> CountValidationResult:
        """
        Validate TOC/body count from a file.

        Args:
            json_file: Path to cleaned JSON file

        Returns:
            CountValidationResult
        """
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return self.validate(data)

    def save_report(self, result: CountValidationResult, output_path: str):
        """
        Save validation report to JSON.

        Args:
            result: CountValidationResult to save
            output_path: Path to save report
        """
        report = {
            "is_valid": result.is_valid,
            "toc_count": result.toc_count,
            "body_count": result.body_count,
            "missing_from_toc_count": result.missing_from_toc_count,
            "extra_in_toc_count": result.extra_in_toc_count,
            "summary": result.summary,
            "issues": [
                {
                    "issue_type": issue.issue_type,
                    "chapter_id": issue.chapter_id,
                    "chapter_number": issue.chapter_number,
                    "chapter_title": issue.chapter_title,
                    "severity": issue.severity
                }
                for issue in result.issues
            ]
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"Count validation report saved to: {output_path}")


def validate_toc_body_alignment(cleaned_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Standalone function to validate TOC/body alignment.

    Convenience function that returns a simplified dict format.
    Use this for quick validation checks.

    Args:
        cleaned_json: Cleaned book JSON

    Returns:
        Dict with validation results
    """
    validator = TOCBodyCountValidator()
    return validator.validate_toc_body_alignment(cleaned_json)


def print_alignment_result(result: Dict[str, Any], file_name: str = ""):
    """
    Print formatted alignment validation result.

    Args:
        result: Result dict from validate_toc_body_alignment()
        file_name: Optional file name to display
    """
    print(f"\n{'='*80}")
    if file_name:
        print(f"TOC/BODY ALIGNMENT: {file_name}")
    else:
        print(f"TOC/BODY ALIGNMENT VALIDATION")
    print(f"{'='*80}\n")

    if result.get('error'):
        print(f"❌ Error: {result['error']}")
        return

    print(f"TOC Entries: {result['toc_count']}")
    print(f"Body Chapters: {result['body_count']}")

    if result['valid']:
        print(f"✓ Validation: PASSED\n")
    else:
        print(f"✗ Validation: FAILED\n")

        # Show missing chapters
        if result.get('missing_from_toc'):
            print(f"❌ TOC/Body Mismatch")
            print(f"- TOC entries: {result['toc_count']}")
            print(f"- Body chapters: {result['body_count']}")
            print(f"- Missing from TOC:")

            for ch in result.get('missing_chapters', []):
                print(f"  * Chapter {ch['chapter_num']}: {ch['title']} ({ch['id']})")

        # Show extra TOC entries
        if result.get('extra_in_toc'):
            print(f"\n⚠️  Extra TOC entries (not in body):")
            print(f"- Chapters: {result['extra_in_toc']}")

    print(f"\n{'='*80}\n")


def main():
    """CLI testing"""
    import sys
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate TOC/body chapter count alignment"
    )
    parser.add_argument('input', help='Path to cleaned JSON file')
    parser.add_argument('--save-report', action='store_true',
                        help='Save validation report to JSON')
    parser.add_argument('--use-alignment', action='store_true',
                        help='Use simplified alignment validation')

    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"Error: File not found: {args.input}")
        return 1

    # Load data
    with open(args.input, 'r', encoding='utf-8') as f:
        data = json.load(f)

    validator = TOCBodyCountValidator()

    if args.use_alignment:
        # Use simplified alignment validation
        result_dict = validator.validate_toc_body_alignment(data)
        print_alignment_result(result_dict, Path(args.input).name)

        if args.save_report:
            output_path = Path(args.input).parent / f"{Path(args.input).stem}_alignment.json"
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result_dict, f, ensure_ascii=False, indent=2)
            print(f"Report saved to: {output_path}\n")

        return 0 if result_dict['valid'] else 1

    else:
        # Use full validation (original behavior)
        result = validator.validate_file(args.input)

        # Print summary
        print(f"\n{'='*80}")
        print(f"TOC/BODY COUNT VALIDATION")
        print(f"{'='*80}\n")
        print(result.summary)
        print()

        # Print detailed issues
        if result.issues:
            print(f"{'='*80}")
            print(f"DETAILED ISSUES ({len(result.issues)})")
            print(f"{'='*80}\n")

            for issue in result.issues:
                icon = "❌" if issue.severity == "error" else "⚠️"
                print(f"{icon} {issue.issue_type.replace('_', ' ').title()}")
                print(f"   Chapter ID: {issue.chapter_id}")
                print(f"   Chapter Number: {issue.chapter_number}")
                print(f"   Title: {issue.chapter_title}")
                print()

        # Save report if requested
        if args.save_report:
            input_path = Path(args.input)
            output_path = input_path.parent / f"{input_path.stem}_count_validation.json"
            validator.save_report(result, str(output_path))
            print(f"\n{'='*80}")
            print(f"Report saved to: {output_path}")
            print(f"{'='*80}\n")

        print(f"{'='*80}\n")

        return 0 if result.is_valid else 1


if __name__ == "__main__":
    exit(main())
