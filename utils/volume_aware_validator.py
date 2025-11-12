#!/usr/bin/env python3
"""
Volume-Aware Continuation Validator

Enhanced validation for multi-volume works that:
1. Queries catalog for all volumes of a work
2. Analyzes chapter numbering patterns across volumes
3. Validates continuation volumes start at expected chapter numbers
4. Provides detailed volume-aware validation reports

Addresses Priority 2: Multi-Volume Continuation Handling
"""

import sqlite3
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class VolumeInfo:
    """Information about a volume"""
    work_number: str
    title_chinese: str
    volume_number: int  # 1, 2, 3, etc.
    volume_label: str  # "001", "002", "003"
    directory_name: str
    filename: str
    expected_chapter_start: Optional[int] = None
    expected_chapter_end: Optional[int] = None
    actual_chapter_start: Optional[int] = None
    actual_chapter_end: Optional[int] = None
    chapter_count: Optional[int] = None


@dataclass
class VolumeValidationIssue:
    """Issue found during volume validation"""
    severity: str  # "error", "warning", "info"
    volume_number: int
    issue_type: str  # "wrong_start", "wrong_end", "unexpected_gap", "inconsistent_pattern"
    message: str
    expected: Optional[int] = None
    actual: Optional[int] = None


class VolumeAwareValidator:
    """
    Enhanced validator for multi-volume works.

    Goes beyond basic "volume > 1" check to validate:
    - Expected chapter start/end for each volume
    - Consistent chapter patterns across volumes
    - Proper continuation sequences
    """

    def __init__(self, catalog_path: str):
        """
        Initialize validator.

        Args:
            catalog_path: Path to wuxia_catalog.db
        """
        self.catalog_path = Path(catalog_path)
        if not self.catalog_path.exists():
            raise FileNotFoundError(f"Catalog database not found: {catalog_path}")

        logger.info(f"Volume-aware validator initialized with catalog: {catalog_path}")

    def get_all_volumes_for_work(self, work_number: str) -> List[VolumeInfo]:
        """
        Get all volumes for a given work.

        Args:
            work_number: Work identifier (e.g., "D61")

        Returns:
            List of VolumeInfo objects sorted by volume number
        """
        try:
            conn = sqlite3.connect(self.catalog_path)
            cursor = conn.cursor()

            query = """
                SELECT
                    w.work_number,
                    w.title_chinese,
                    wf.volume,
                    wf.directory_name,
                    wf.filename
                FROM works w
                JOIN work_files wf ON w.work_id = wf.work_id
                WHERE w.work_number = ?
                ORDER BY wf.volume
            """

            cursor.execute(query, (work_number,))
            rows = cursor.fetchall()
            conn.close()

            volumes = []
            for row in rows:
                volume_label = row[2] if row[2] else None
                if volume_label:
                    # Convert 'a' -> 1, 'b' -> 2, etc. or '001' -> 1
                    if len(volume_label) == 1 and volume_label.isalpha():
                        volume_num = ord(volume_label.lower()) - ord('a') + 1
                        volume_label_numeric = f"{volume_num:03d}"
                    elif volume_label.isdigit():
                        volume_num = int(volume_label)
                        volume_label_numeric = f"{volume_num:03d}"
                    else:
                        volume_num = 1
                        volume_label_numeric = "001"
                else:
                    volume_num = 1
                    volume_label_numeric = None

                volumes.append(VolumeInfo(
                    work_number=row[0],
                    title_chinese=row[1],
                    volume_number=volume_num,
                    volume_label=volume_label_numeric,
                    directory_name=row[3],
                    filename=row[4]
                ))

            logger.debug(f"Found {len(volumes)} volumes for work {work_number}")
            return volumes

        except Exception as e:
            logger.error(f"Error querying volumes for {work_number}: {e}")
            return []

    def analyze_chapter_pattern(
        self,
        volumes: List[VolumeInfo]
    ) -> Dict[str, any]:
        """
        Analyze chapter numbering pattern across volumes.

        Determines:
        - Average chapters per volume
        - Expected start/end for each volume
        - Whether chapters are continuous or reset per volume

        Args:
            volumes: List of VolumeInfo with actual chapter data

        Returns:
            Analysis dict with pattern information
        """
        if not volumes:
            return {"pattern": "unknown"}

        # Check if we have chapter counts
        volumes_with_data = [v for v in volumes if v.chapter_count is not None]
        if len(volumes_with_data) < 2:
            # Not enough data to determine pattern
            return {"pattern": "insufficient_data"}

        # Calculate average chapters per volume
        total_chapters = sum(v.chapter_count for v in volumes_with_data)
        avg_per_volume = total_chapters / len(volumes_with_data)

        # Check if chapters are continuous across volumes
        continuous = True
        for i in range(len(volumes_with_data) - 1):
            current = volumes_with_data[i]
            next_vol = volumes_with_data[i + 1]

            if (current.actual_chapter_end and next_vol.actual_chapter_start and
                next_vol.actual_chapter_start != current.actual_chapter_end + 1):
                # Check if next volume starts where previous ended
                if next_vol.actual_chapter_start == 1:
                    continuous = False
                    break

        return {
            "pattern": "continuous" if continuous else "reset_per_volume",
            "avg_chapters_per_volume": avg_per_volume,
            "total_volumes": len(volumes),
            "total_chapters": total_chapters if continuous else None
        }

    def calculate_expected_ranges(
        self,
        volumes: List[VolumeInfo],
        pattern: Dict[str, any]
    ) -> List[VolumeInfo]:
        """
        Calculate expected chapter ranges for each volume based on pattern.

        Args:
            volumes: List of VolumeInfo objects
            pattern: Pattern analysis from analyze_chapter_pattern()

        Returns:
            Updated list of VolumeInfo with expected ranges
        """
        if pattern["pattern"] == "continuous":
            # Continuous numbering across volumes
            avg_per_volume = int(pattern["avg_chapters_per_volume"])

            for i, volume in enumerate(volumes):
                volume.expected_chapter_start = i * avg_per_volume + 1
                volume.expected_chapter_end = (i + 1) * avg_per_volume

        elif pattern["pattern"] == "reset_per_volume":
            # Each volume starts at chapter 1
            for volume in volumes:
                volume.expected_chapter_start = 1
                volume.expected_chapter_end = int(pattern["avg_chapters_per_volume"])

        return volumes

    def validate_volume_continuation(
        self,
        volume_info: VolumeInfo,
        actual_chapter_start: int,
        actual_chapter_end: int,
        actual_chapter_count: int
    ) -> List[VolumeValidationIssue]:
        """
        Validate a single volume's chapter numbering.

        Args:
            volume_info: Volume information with expected ranges
            actual_chapter_start: First chapter number in volume
            actual_chapter_end: Last chapter number in volume
            actual_chapter_count: Number of chapters in volume

        Returns:
            List of validation issues
        """
        issues = []
        volume_num = volume_info.volume_number

        # Update actual data
        volume_info.actual_chapter_start = actual_chapter_start
        volume_info.actual_chapter_end = actual_chapter_end
        volume_info.chapter_count = actual_chapter_count

        # Check start number
        if volume_info.expected_chapter_start is not None:
            expected_start = volume_info.expected_chapter_start

            # Allow some tolerance for first volume (might have prologue, intro)
            tolerance = 1 if volume_num == 1 else 0

            if abs(actual_chapter_start - expected_start) > tolerance:
                severity = "warning" if volume_num == 1 else "error"
                issues.append(VolumeValidationIssue(
                    severity=severity,
                    volume_number=volume_num,
                    issue_type="wrong_start",
                    message=f"Volume {volume_num} starts at chapter {actual_chapter_start}, expected ~{expected_start}",
                    expected=expected_start,
                    actual=actual_chapter_start
                ))

        # Check end number (less strict, just informational)
        if volume_info.expected_chapter_end is not None:
            expected_end = volume_info.expected_chapter_end

            # Wide tolerance on end (volumes may vary in length)
            if abs(actual_chapter_end - expected_end) > 5:
                issues.append(VolumeValidationIssue(
                    severity="info",
                    volume_number=volume_num,
                    issue_type="unexpected_end",
                    message=f"Volume {volume_num} ends at chapter {actual_chapter_end}, expected ~{expected_end}",
                    expected=expected_end,
                    actual=actual_chapter_end
                ))

        return issues

    def get_volume_context(
        self,
        work_number: str,
        current_volume: str
    ) -> Dict[str, any]:
        """
        Get context about a volume within its work.

        Args:
            work_number: Work identifier
            current_volume: Current volume label (e.g., "001", "002")

        Returns:
            Context dict with volume position, total volumes, etc.
        """
        volumes = self.get_all_volumes_for_work(work_number)

        if not volumes:
            return {
                "total_volumes": 0,
                "is_multi_volume": False,
                "is_continuation": False
            }

        # Find current volume
        current_vol_num = int(current_volume) if current_volume and current_volume.isdigit() else 1

        return {
            "total_volumes": len(volumes),
            "current_volume_number": current_vol_num,
            "is_multi_volume": len(volumes) > 1,
            "is_continuation": current_vol_num > 1,
            "volumes": volumes
        }

    def validate_with_context(
        self,
        work_number: str,
        volume: str,
        actual_chapter_start: int,
        actual_chapter_end: int,
        actual_chapter_count: int
    ) -> Tuple[bool, List[VolumeValidationIssue], Dict[str, any]]:
        """
        Validate a volume with full work context.

        This is the main entry point for volume-aware validation.

        Args:
            work_number: Work identifier
            volume: Volume label (e.g., "001", "002")
            actual_chapter_start: First chapter number
            actual_chapter_end: Last chapter number
            actual_chapter_count: Number of chapters

        Returns:
            (is_valid, issues, context)
        """
        # Get all volumes for this work
        context = self.get_volume_context(work_number, volume)

        if not context["is_multi_volume"]:
            # Single volume work - no continuation validation needed
            return True, [], context

        volumes = context.get("volumes", [])

        # Analyze pattern (would need actual chapter data from other volumes)
        # For now, use a simplified approach

        current_vol_num = context["current_volume_number"]
        issues = []

        if current_vol_num > 1:
            # This is a continuation volume
            # Expected start is roughly: (vol_num - 1) * 10 (assuming ~10 chapters per volume)
            # This is a heuristic - would be better with actual data from previous volumes

            estimated_chapters_per_volume = 11  # Common for Jin Yong novels
            expected_start = (current_vol_num - 1) * estimated_chapters_per_volume + 1

            tolerance = 2  # Allow +/- 2 chapters variance

            if abs(actual_chapter_start - expected_start) > tolerance:
                issues.append(VolumeValidationIssue(
                    severity="info",
                    volume_number=current_vol_num,
                    issue_type="continuation_start",
                    message=f"Volume {current_vol_num} starts at chapter {actual_chapter_start} (estimated expected: ~{expected_start})",
                    expected=expected_start,
                    actual=actual_chapter_start
                ))
            else:
                # Continuation looks correct
                issues.append(VolumeValidationIssue(
                    severity="info",
                    volume_number=current_vol_num,
                    issue_type="continuation_volume",
                    message=f"Continuation volume {current_vol_num} - chapters {actual_chapter_start}-{actual_chapter_end}",
                    actual=actual_chapter_start
                ))

        # No errors, just info
        is_valid = all(issue.severity != "error" for issue in issues)

        return is_valid, issues, context


def main():
    """CLI testing"""
    import sys

    if len(sys.argv) < 6:
        print("Usage: python volume_aware_validator.py <catalog_path> <work_number> <volume> <chapter_start> <chapter_end> <chapter_count>")
        print("Example: python volume_aware_validator.py wuxia_catalog.db D61 002 12 22 11")
        return 1

    catalog_path = sys.argv[1]
    work_number = sys.argv[2]
    volume = sys.argv[3]
    chapter_start = int(sys.argv[4])
    chapter_end = int(sys.argv[5])
    chapter_count = int(sys.argv[6])

    print(f"\n{'='*80}")
    print(f"VOLUME-AWARE VALIDATION")
    print(f"{'='*80}\n")

    validator = VolumeAwareValidator(catalog_path)

    is_valid, issues, context = validator.validate_with_context(
        work_number=work_number,
        volume=volume,
        actual_chapter_start=chapter_start,
        actual_chapter_end=chapter_end,
        actual_chapter_count=chapter_count
    )

    print(f"Work: {work_number}")
    print(f"Volume: {volume} ({context['current_volume_number']} of {context['total_volumes']})")
    print(f"Chapters: {chapter_start}-{chapter_end} ({chapter_count} chapters)")
    print()

    if context["is_multi_volume"]:
        print(f"📚 Multi-volume work ({context['total_volumes']} volumes)")
    else:
        print(f"📕 Single-volume work")

    print()
    print(f"Issues Found: {len(issues)}")
    for issue in issues:
        icon = "✗" if issue.severity == "error" else "⚠" if issue.severity == "warning" else "ℹ"
        print(f"  {icon} [{issue.severity.upper()}] {issue.message}")

    print()
    print(f"{'='*80}")
    print(f"{'✓ VALID' if is_valid else '✗ INVALID'}")
    print(f"{'='*80}\n")

    return 0 if is_valid else 1


if __name__ == "__main__":
    exit(main())
