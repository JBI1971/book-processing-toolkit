#!/usr/bin/env python3
"""
Book Sanity Checker
Early validation after topology analysis to catch data quality issues
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, field

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.catalog_metadata import CatalogMetadataExtractor, WorkMetadata
from utils.chapter_sequence_validator import ChineseChapterSequenceValidator, SequenceIssue
from utils.volume_aware_validator import VolumeAwareValidator, VolumeValidationIssue

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class SanityCheckResult:
    """Result of sanity checking"""
    is_valid: bool
    has_errors: bool
    has_warnings: bool
    metadata: WorkMetadata = None
    sequence_issues: List[SequenceIssue] = field(default_factory=list)
    volume_issues: List[VolumeValidationIssue] = field(default_factory=list)
    data_issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    summary: str = ""
    volume_context: Dict = field(default_factory=dict)


class BookSanityChecker:
    """Perform early sanity checks on book data"""

    def __init__(self, catalog_path: str):
        """
        Initialize sanity checker.

        Args:
            catalog_path: Path to wuxia_catalog.db
        """
        self.catalog_path = catalog_path
        self.catalog_extractor = CatalogMetadataExtractor(catalog_path)
        self.sequence_validator = ChineseChapterSequenceValidator()
        self.volume_validator = VolumeAwareValidator(catalog_path)

    def check(
        self,
        json_file: Path,
        directory_name: str,
        strict_sequence: bool = False
    ) -> SanityCheckResult:
        """
        Perform sanity checks on book JSON.

        Args:
            json_file: Path to book JSON file
            directory_name: Directory name (e.g., 'wuxia_0008')
            strict_sequence: If True, sequence gaps are errors; if False, warnings

        Returns:
            SanityCheckResult
        """
        result = SanityCheckResult(is_valid=True, has_errors=False, has_warnings=False)

        try:
            # Load JSON
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Check 1: Metadata lookup
            logger.info(f"[1/3] Checking catalog metadata for {directory_name}...")
            # Use filename if available for more precise metadata (especially volume)
            filename = json_file.name
            result.metadata = self.catalog_extractor.get_metadata_by_filename(filename)
            # Fall back to directory-based lookup if filename lookup fails
            if not result.metadata:
                result.metadata = self.catalog_extractor.get_metadata_by_directory(directory_name)

            if not result.metadata:
                result.warnings.append(f"No catalog metadata found for {directory_name}")
                result.has_warnings = True
            else:
                logger.info(f"  ✓ Found: {result.metadata.title_chinese} by {result.metadata.author_chinese}")
                if result.metadata.volume:
                    logger.info(f"    Volume: {result.metadata.volume}")

            # Check 2: Basic structure
            logger.info(f"[2/3] Checking JSON structure...")
            if 'chapters' not in data:
                result.data_issues.append("Missing 'chapters' key")
                result.has_errors = True
                result.is_valid = False
                return result

            chapters = data['chapters']
            if not chapters or len(chapters) == 0:
                result.data_issues.append("Empty chapters array")
                result.has_errors = True
                result.is_valid = False
                return result

            logger.info(f"  ✓ Found {len(chapters)} chapters")

            # Check 3: Chapter sequence validation
            logger.info(f"[3/3] Validating chapter numbering sequence...")
            # Pass volume for continuation detection
            volume = result.metadata.volume if result.metadata else None
            is_valid, issues = self.sequence_validator.validate_sequence(
                chapters,
                strict=strict_sequence,
                volume=volume
            )

            result.sequence_issues = issues

            # Count errors and warnings
            error_count = sum(1 for issue in issues if issue.severity == "error")
            warning_count = sum(1 for issue in issues if issue.severity == "warning")

            if error_count > 0:
                result.has_errors = True
                result.is_valid = False
                logger.warning(f"  ✗ Found {error_count} sequence errors")
            elif warning_count > 0:
                result.has_warnings = True
                logger.warning(f"  ⚠  Found {warning_count} sequence warnings")
            else:
                logger.info(f"  ✓ Chapter sequence looks good")

            # Check 3b: Volume-aware validation (for multi-volume works)
            if result.metadata and result.metadata.work_number and result.metadata.volume:
                try:
                    logger.info(f"[3b] Volume-aware validation...")

                    # Get chapter range from sequence summary
                    summary = self.sequence_validator.get_chapter_sequence_summary(chapters)

                    if summary['numbered_chapters'] > 0:
                        vol_is_valid, vol_issues, vol_context = self.volume_validator.validate_with_context(
                            work_number=result.metadata.work_number,
                            volume=result.metadata.volume,
                            actual_chapter_start=summary['sequence_start'],
                            actual_chapter_end=summary['sequence_end'],
                            actual_chapter_count=summary['numbered_chapters']
                        )

                        result.volume_issues = vol_issues
                        result.volume_context = vol_context

                        if vol_context.get('is_multi_volume'):
                            logger.info(f"  ✓ Multi-volume work ({vol_context['total_volumes']} volumes)")
                            if vol_context.get('is_continuation'):
                                logger.info(f"  ℹ️  Continuation volume {vol_context['current_volume_number']}")

                        # Log volume issues
                        if vol_issues:
                            for issue in vol_issues:
                                icon = "ℹ"
                                logger.info(f"  {icon} [{issue.severity.upper()}] {issue.message}")
                except Exception as e:
                    logger.warning(f"  ⚠️  Volume-aware validation failed: {e}")

            # Get sequence summary (or reuse from above)
            if 'summary' not in locals():
                summary = self.sequence_validator.get_chapter_sequence_summary(chapters)

            # Build detailed report
            report_parts = []
            if result.metadata:
                report_parts.append(f"📚 {result.metadata.title_chinese} by {result.metadata.author_chinese}")
                if result.metadata.volume:
                    report_parts.append(f"   Volume: {result.metadata.volume}")

            if summary['numbered_chapters'] > 0:
                report_parts.append(f"📖 Chapters: {summary['total_chapters']} total, {summary['numbered_chapters']} numbered")
                report_parts.append(f"   Sequence: {summary['sequence_start']} → {summary['sequence_end']}")

                if summary['missing_count'] > 0:
                    report_parts.append(f"   ⚠️  Missing: {summary['missing_count']} chapters")

                if summary['has_duplicates']:
                    report_parts.append(f"   ✗ Has duplicate chapter numbers")

            result.summary = "\n".join(report_parts)

            # Log issues
            if issues:
                logger.info(f"\n📋 Sequence Issues:")
                for issue in issues:
                    icon = "✗" if issue.severity == "error" else "⚠" if issue.severity == "warning" else "ℹ"
                    logger.info(f"  {icon} [{issue.severity.upper()}] {issue.message}")

        except Exception as e:
            logger.error(f"Sanity check failed: {e}")
            result.data_issues.append(f"Exception during check: {str(e)}")
            result.has_errors = True
            result.is_valid = False

        return result

    def check_file(
        self,
        json_file: Path,
        directory_name: str,
        strict_sequence: bool = False
    ) -> SanityCheckResult:
        """
        Convenience method that just calls check().

        Args:
            json_file: Path to JSON file
            directory_name: Directory name
            strict_sequence: Strict sequence checking

        Returns:
            SanityCheckResult
        """
        return self.check(json_file, directory_name, strict_sequence)


def main():
    """CLI testing"""
    import sys

    if len(sys.argv) < 4:
        print("Usage: python sanity_checker.py <catalog_path> <json_file> <directory_name>")
        return 1

    catalog_path = sys.argv[1]
    json_file = Path(sys.argv[2])
    directory_name = sys.argv[3]

    print(f"\n{'='*80}")
    print(f"SANITY CHECK")
    print(f"{'='*80}\n")

    checker = BookSanityChecker(catalog_path)
    result = checker.check(json_file, directory_name, strict_sequence=False)

    print(f"\n{result.summary}")

    print(f"\n{'='*80}")
    if result.is_valid:
        print(f"✓ PASSED - No critical issues")
    else:
        print(f"✗ FAILED - {len(result.data_issues)} errors found")

    if result.has_warnings:
        print(f"⚠  {len(result.warnings + result.sequence_issues)} warnings")

    print(f"{'='*80}\n")

    return 0 if result.is_valid else 1


if __name__ == "__main__":
    exit(main())
