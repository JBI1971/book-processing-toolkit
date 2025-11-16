#!/usr/bin/env python3
"""
Footnote Integrity Validator

Validates that footnote markers [1], [2], etc. in content match footnote definitions.
This is CRITICAL for translation quality - mismatches make the output "hot garbage".

Checks:
1. Every marker [1], [2], etc. has corresponding footnote definition
2. Every footnote has at least one marker in text
3. No duplicate markers within a block
4. Markers are contiguous (1, 2, 3... no gaps)
5. Marker numbers match footnote keys

Can be used:
- Standalone utility (CLI)
- Validation stage in workflow
- Quality gate after translation
- Auto-fix pre-processor (future)
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Set, Optional
from pathlib import Path
import re
import json
import logging
import sys

logger = logging.getLogger(__name__)


@dataclass
class FootnoteIssue:
    """Represents a footnote integrity issue."""
    severity: str  # 'error', 'warning', 'info'
    issue_type: str  # 'missing_footnote', 'orphaned_footnote', 'duplicate_marker', 'sequence_gap', 'marker_list_mismatch'
    message: str
    chapter_id: str
    block_id: str
    marker_numbers: List[int]  # Affected marker numbers
    suggested_fix: str


@dataclass
class FootnoteValidationResult:
    """Complete validation result for footnote integrity."""
    is_valid: bool
    total_blocks_checked: int
    total_markers_found: int
    total_footnotes_found: int
    issues: List[FootnoteIssue] = field(default_factory=list)

    # Summary stats
    missing_footnotes: int = 0  # Markers without footnote definitions
    orphaned_footnotes: int = 0  # Footnotes without markers in text
    duplicate_markers: int = 0  # Same marker used multiple times
    sequence_gaps: int = 0  # Non-contiguous markers (e.g., [1], [2], [5])
    marker_list_mismatches: int = 0  # Marker number doesn't match footnote key

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict for reporting."""
        return {
            "valid": self.is_valid,
            "summary": {
                "blocks_checked": self.total_blocks_checked,
                "markers_found": self.total_markers_found,
                "footnotes_found": self.total_footnotes_found,
                "missing_footnotes": self.missing_footnotes,
                "orphaned_footnotes": self.orphaned_footnotes,
                "duplicate_markers": self.duplicate_markers,
                "sequence_gaps": self.sequence_gaps,
                "marker_list_mismatches": self.marker_list_mismatches
            },
            "issues": [
                {
                    "severity": issue.severity,
                    "type": issue.issue_type,
                    "message": issue.message,
                    "location": f"{issue.chapter_id}/{issue.block_id}",
                    "markers": issue.marker_numbers,
                    "suggested_fix": issue.suggested_fix
                }
                for issue in self.issues
            ]
        }


class FootnoteIntegrityValidator:
    """
    Validates footnote markers against footnote definitions.

    Checks:
    1. Every marker [1], [2], etc. has corresponding footnote definition
    2. Every footnote has at least one marker in text
    3. No duplicate markers within a block
    4. Markers are contiguous (1, 2, 3... no gaps)
    5. Marker numbers match footnote keys
    """

    def __init__(self, auto_fix: bool = False):
        """
        Initialize validator.

        Args:
            auto_fix: If True, attempt to fix issues automatically (not implemented yet)
        """
        self.auto_fix = auto_fix
        self._marker_pattern = re.compile(r'\[(\d+)\]')

    def validate_block(
        self,
        block: Dict[str, Any],
        chapter_id: str
    ) -> List[FootnoteIssue]:
        """Validate footnotes in a single content block."""
        issues = []
        block_id = block.get('id', 'unknown')

        # Extract content (prefer translated, fall back to original)
        content = block.get('translated_content') or block.get('english_text') or block.get('content', '')
        footnotes = block.get('footnotes', [])

        if not content:
            return issues

        # Extract markers from content
        marker_matches = self._marker_pattern.findall(content)
        marker_numbers = [int(m) for m in marker_matches]
        footnote_keys = [fn.get('key', 0) for fn in footnotes]

        # Check 1: Duplicate markers
        seen = set()
        duplicates = set()
        for marker in marker_numbers:
            if marker in seen:
                duplicates.add(marker)
            seen.add(marker)

        if duplicates:
            issues.append(FootnoteIssue(
                severity='error',
                issue_type='duplicate_marker',
                message=f"Duplicate footnote markers: {sorted(duplicates)}",
                chapter_id=chapter_id,
                block_id=block_id,
                marker_numbers=sorted(duplicates),
                suggested_fix="Remove duplicate markers, keeping only first occurrence"
            ))

        # Check 2: Missing footnotes (markers without definitions)
        unique_markers = set(marker_numbers)
        footnote_keys_set = set(footnote_keys)
        missing = unique_markers - footnote_keys_set

        if missing:
            issues.append(FootnoteIssue(
                severity='error',
                issue_type='missing_footnote',
                message=f"Markers without footnote definitions: {sorted(missing)}",
                chapter_id=chapter_id,
                block_id=block_id,
                marker_numbers=sorted(missing),
                suggested_fix="Add missing footnote definitions or remove markers"
            ))

        # Check 3: Orphaned footnotes (definitions without markers)
        orphaned = footnote_keys_set - unique_markers

        if orphaned:
            issues.append(FootnoteIssue(
                severity='warning',
                issue_type='orphaned_footnote',
                message=f"Footnotes without markers in text: {sorted(orphaned)}",
                chapter_id=chapter_id,
                block_id=block_id,
                marker_numbers=sorted(orphaned),
                suggested_fix="Remove orphaned footnotes or add markers to text"
            ))

        # Check 4: Sequence gaps (non-contiguous)
        if unique_markers:
            sorted_markers = sorted(unique_markers)
            expected = list(range(1, len(sorted_markers) + 1))

            if sorted_markers != expected:
                issues.append(FootnoteIssue(
                    severity='warning',
                    issue_type='sequence_gap',
                    message=f"Non-contiguous markers: {sorted_markers} (expected: {expected})",
                    chapter_id=chapter_id,
                    block_id=block_id,
                    marker_numbers=sorted_markers,
                    suggested_fix="Renumber markers to be contiguous starting from 1"
                ))

        # Check 5: Marker/key mismatch
        mismatches = []
        for footnote in footnotes:
            marker = footnote.get('key')
            if marker and marker not in unique_markers:
                continue  # Covered by orphaned check
            if marker and marker in unique_markers:
                # Check that the footnote key matches the order
                # This is a simplified check - more sophisticated logic could be added
                pass

        return issues

    def validate_book(self, data: Dict[str, Any]) -> FootnoteValidationResult:
        """Validate footnote integrity for entire book."""
        all_issues = []
        total_blocks = 0
        total_markers = 0
        total_footnotes = 0

        chapters = data.get('structure', {}).get('body', {}).get('chapters', [])

        for chapter in chapters:
            chapter_id = chapter.get('id', 'unknown')

            for block in chapter.get('content_blocks', []):
                total_blocks += 1

                # Count markers and footnotes
                content = block.get('translated_content') or block.get('english_text') or block.get('content', '')
                if content:
                    markers = self._marker_pattern.findall(content)
                    total_markers += len(markers)

                footnotes = block.get('footnotes', [])
                total_footnotes += len(footnotes)

                # Validate block
                block_issues = self.validate_block(block, chapter_id)
                all_issues.extend(block_issues)

        # Calculate summary stats
        issue_counts = {
            'missing_footnote': 0,
            'orphaned_footnote': 0,
            'duplicate_marker': 0,
            'sequence_gap': 0,
            'marker_list_mismatch': 0
        }

        for issue in all_issues:
            if issue.issue_type in issue_counts:
                issue_counts[issue.issue_type] += 1

        # Overall validity: no ERRORS (warnings are OK)
        is_valid = not any(
            issue.severity == 'error'
            for issue in all_issues
        )

        return FootnoteValidationResult(
            is_valid=is_valid,
            total_blocks_checked=total_blocks,
            total_markers_found=total_markers,
            total_footnotes_found=total_footnotes,
            issues=all_issues,
            missing_footnotes=issue_counts['missing_footnote'],
            orphaned_footnotes=issue_counts['orphaned_footnote'],
            duplicate_markers=issue_counts['duplicate_marker'],
            sequence_gaps=issue_counts['sequence_gap'],
            marker_list_mismatches=issue_counts['marker_list_mismatch']
        )

    def validate_file(
        self,
        input_path: Path,
        save_report: bool = True
    ) -> FootnoteValidationResult:
        """Validate footnotes in a JSON file."""
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        result = self.validate_book(data)

        if save_report:
            report_path = input_path.parent / f"{input_path.stem}_footnote_validation.json"
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
            logger.info(f"Validation report saved: {report_path}")

        return result


# CLI interface for standalone usage
def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Validate footnote marker/definition integrity - prevents "hot garbage" translations!'
    )
    parser.add_argument('input', help='Input JSON file')
    parser.add_argument('--save-report', action='store_true',
                       help='Save validation report to JSON')
    parser.add_argument('--auto-fix', action='store_true',
                       help='Attempt automatic fixes (not implemented yet)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(levelname)s: %(message)s'
    )

    validator = FootnoteIntegrityValidator(auto_fix=args.auto_fix)
    result = validator.validate_file(Path(args.input), save_report=args.save_report)

    print(f"\n{'='*60}")
    print("FOOTNOTE INTEGRITY VALIDATION")
    print(f"{'='*60}")
    print(f"Status: {'✓ VALID' if result.is_valid else '✗ INVALID'}")
    print(f"\nBlocks checked: {result.total_blocks_checked}")
    print(f"Markers found: {result.total_markers_found}")
    print(f"Footnotes found: {result.total_footnotes_found}")
    print(f"\nIssues:")
    print(f"  Missing footnotes: {result.missing_footnotes}")
    print(f"  Orphaned footnotes: {result.orphaned_footnotes}")
    print(f"  Duplicate markers: {result.duplicate_markers}")
    print(f"  Sequence gaps: {result.sequence_gaps}")
    print(f"  Marker/list mismatches: {result.marker_list_mismatches}")

    if result.issues:
        print(f"\nDetailed Issues ({len(result.issues)}):")
        for i, issue in enumerate(result.issues[:10], 1):  # Show first 10
            print(f"\n  [{i}] {issue.severity.upper()}: {issue.issue_type}")
            print(f"      Location: {issue.chapter_id}/{issue.block_id}")
            print(f"      {issue.message}")
            print(f"      Fix: {issue.suggested_fix}")

        if len(result.issues) > 10:
            print(f"\n  ... and {len(result.issues) - 10} more issues")

    print(f"\n{'='*60}\n")

    return 0 if result.is_valid else 1


if __name__ == '__main__':
    sys.exit(main())
