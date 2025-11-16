#!/usr/bin/env python3
"""
Volume Manager for Multi-Volume Works

Handles discovery, ordering, and coordination of multi-volume translations.
Integrates with catalog database to identify all volumes for a work.
"""

import sys
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
import json


from utils.catalog_metadata import CatalogMetadataExtractor, WorkMetadata

logger = logging.getLogger(__name__)


@dataclass
class VolumeInfo:
    """Information about a single volume"""
    work_number: str
    volume: str  # e.g., "001", "002"
    title: str
    author: str
    directory_name: str
    cleaned_json_path: Optional[Path] = None
    translated_json_path: Optional[Path] = None
    is_processed: bool = False
    chapter_count: Optional[int] = None
    error: Optional[str] = None


class VolumeManager:
    """
    Manages multi-volume work discovery and processing order.

    Responsibilities:
    - Query catalog database for all volumes of a work
    - Locate cleaned JSON files for each volume
    - Track processing status
    - Maintain processing order
    """

    def __init__(
        self,
        catalog_path: Path,
        source_dir: Path,
        output_dir: Path
    ):
        """
        Initialize volume manager.

        Args:
            catalog_path: Path to wuxia_catalog.db
            source_dir: Directory containing cleaned JSON files (organized by directory)
            output_dir: Directory for translated output
        """
        self.catalog_path = Path(catalog_path)
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir)

        # Initialize catalog extractor
        self.catalog = CatalogMetadataExtractor(str(catalog_path))

        logger.info(f"VolumeManager initialized")
        logger.info(f"  Catalog: {catalog_path}")
        logger.info(f"  Source: {source_dir}")
        logger.info(f"  Output: {output_dir}")

    def get_volumes_for_work(self, work_number: str) -> List[VolumeInfo]:
        """
        Get all volumes for a work number.

        Args:
            work_number: Work number like "D55"

        Returns:
            List of VolumeInfo objects, sorted by volume number

        Example:
            >>> manager.get_volumes_for_work("D55")
            [VolumeInfo(work_number="D55", volume="001", ...),
             VolumeInfo(work_number="D55", volume="002", ...)]
        """
        import sqlite3

        try:
            conn = sqlite3.connect(self.catalog_path)
            cursor = conn.cursor()

            # Query for all volumes of this work
            query = """
                SELECT
                    w.work_number,
                    w.title_chinese,
                    w.author_chinese,
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

            if not rows:
                logger.warning(f"No volumes found for work_number: {work_number}")
                return []

            # Build VolumeInfo objects
            volumes = []
            for row in rows:
                work_num, title, author, volume, directory_name, filename = row

                # Convert volume letter to numeric (a -> 001, b -> 002)
                from utils.catalog_metadata import convert_volume_to_numeric
                volume_numeric = convert_volume_to_numeric(volume) if volume else "001"

                # Locate cleaned JSON file
                cleaned_path = self._find_cleaned_json(directory_name, work_num, volume)

                # Generate output path
                output_path = None
                if cleaned_path:
                    output_filename = cleaned_path.name.replace("cleaned_", "translated_")
                    output_path = self.output_dir / work_num / output_filename

                # Check if already processed
                is_processed = output_path.exists() if output_path else False

                # Get chapter count if file exists
                chapter_count = None
                if cleaned_path and cleaned_path.exists():
                    try:
                        chapter_count = self._count_chapters(cleaned_path)
                    except Exception as e:
                        logger.warning(f"Could not count chapters in {cleaned_path}: {e}")

                volume_info = VolumeInfo(
                    work_number=work_num,
                    volume=volume_numeric,
                    title=title,
                    author=author,
                    directory_name=directory_name,
                    cleaned_json_path=cleaned_path,
                    translated_json_path=output_path,
                    is_processed=is_processed,
                    chapter_count=chapter_count
                )

                volumes.append(volume_info)

            logger.info(f"Found {len(volumes)} volumes for {work_number}")
            return volumes

        except Exception as e:
            logger.error(f"Error querying volumes for {work_number}: {e}")
            return []

    def _find_cleaned_json(
        self,
        directory_name: str,
        work_number: str,
        volume: Optional[str]
    ) -> Optional[Path]:
        """
        Find cleaned JSON file for a volume.

        Args:
            directory_name: Directory like "wuxia_0001"
            work_number: Work number like "D55"
            volume: Volume letter like "a", "b", "c"

        Returns:
            Path to cleaned JSON file or None
        """
        # Check if directory exists
        dir_path = self.source_dir / directory_name
        if not dir_path.exists():
            logger.warning(f"Directory not found: {dir_path}")
            return None

        # Find JSON files matching pattern
        pattern = f"cleaned_{work_number}"
        if volume:
            pattern += volume  # e.g., cleaned_D55a_*.json

        json_files = list(dir_path.glob(f"{pattern}*.json"))

        if not json_files:
            logger.warning(f"No cleaned JSON files found matching: {pattern}*.json in {dir_path}")
            return None

        if len(json_files) > 1:
            logger.warning(f"Multiple JSON files found for {pattern}, using first: {json_files[0]}")

        return json_files[0]

    def _count_chapters(self, json_path: Path) -> int:
        """
        Count chapters in cleaned JSON file.

        Args:
            json_path: Path to cleaned JSON

        Returns:
            Number of chapters
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            chapters = data.get('structure', {}).get('body', {}).get('chapters', [])
            return len(chapters)

        except Exception as e:
            logger.error(f"Error counting chapters in {json_path}: {e}")
            return 0

    def get_work_summary(self, work_number: str) -> Dict[str, Any]:
        """
        Get summary information for a work.

        Args:
            work_number: Work number

        Returns:
            Dictionary with work summary
        """
        volumes = self.get_volumes_for_work(work_number)

        if not volumes:
            return {
                "work_number": work_number,
                "found": False,
                "error": "No volumes found"
            }

        total_chapters = sum(v.chapter_count or 0 for v in volumes)
        completed_volumes = [v for v in volumes if v.is_processed]
        pending_volumes = [v for v in volumes if not v.is_processed]

        return {
            "work_number": work_number,
            "title": volumes[0].title,
            "author": volumes[0].author,
            "found": True,
            "total_volumes": len(volumes),
            "completed_volumes": len(completed_volumes),
            "pending_volumes": len(pending_volumes),
            "total_chapters": total_chapters,
            "volumes": [
                {
                    "volume": v.volume,
                    "title": v.title,
                    "directory": v.directory_name,
                    "chapters": v.chapter_count,
                    "is_processed": v.is_processed,
                    "cleaned_path": str(v.cleaned_json_path) if v.cleaned_json_path else None,
                    "translated_path": str(v.translated_json_path) if v.translated_json_path else None
                }
                for v in volumes
            ]
        }

    def get_all_multi_volume_works(self) -> List[Tuple[str, int]]:
        """
        Get all works that have multiple volumes.

        Returns:
            List of tuples: (work_number, volume_count)
            Sorted by volume count descending
        """
        import sqlite3

        try:
            conn = sqlite3.connect(self.catalog_path)
            cursor = conn.cursor()

            query = """
                SELECT w.work_number, COUNT(DISTINCT wf.volume) as volume_count
                FROM works w
                JOIN work_files wf ON w.work_id = wf.work_id
                GROUP BY w.work_number
                HAVING volume_count > 1
                ORDER BY volume_count DESC
            """

            cursor.execute(query)
            results = cursor.fetchall()
            conn.close()

            logger.info(f"Found {len(results)} multi-volume works")
            return results

        except Exception as e:
            logger.error(f"Error querying multi-volume works: {e}")
            return []

    def verify_volume_integrity(self, work_number: str) -> Dict[str, Any]:
        """
        Verify all volumes for a work are present and accessible.

        Args:
            work_number: Work number

        Returns:
            Dictionary with verification results
        """
        volumes = self.get_volumes_for_work(work_number)

        missing_files = []
        accessible_volumes = []
        total_chapters = 0

        for vol in volumes:
            if not vol.cleaned_json_path or not vol.cleaned_json_path.exists():
                missing_files.append({
                    "volume": vol.volume,
                    "directory": vol.directory_name,
                    "expected_path": str(vol.cleaned_json_path) if vol.cleaned_json_path else "unknown"
                })
            else:
                accessible_volumes.append(vol.volume)
                total_chapters += vol.chapter_count or 0

        return {
            "work_number": work_number,
            "total_volumes": len(volumes),
            "accessible_volumes": len(accessible_volumes),
            "missing_volumes": len(missing_files),
            "is_complete": len(missing_files) == 0,
            "total_chapters": total_chapters,
            "missing_files": missing_files
        }


def main():
    """CLI testing"""
    import sys
    from processors.translation_config import TranslationConfig

    if len(sys.argv) < 2:
        print("Usage: python volume_manager.py <work_number>")
        print("Example: python volume_manager.py D55")
        return 1

    work_number = sys.argv[1]

    # Initialize with default config
    config = TranslationConfig()
    manager = VolumeManager(
        catalog_path=config.catalog_path,
        source_dir=config.source_dir,
        output_dir=config.output_dir
    )

    # Get work summary
    print(f"\n{'='*60}")
    print(f"WORK SUMMARY: {work_number}")
    print(f"{'='*60}\n")

    summary = manager.get_work_summary(work_number)

    if not summary['found']:
        print(f"✗ {summary['error']}")
        return 1

    print(f"Title: {summary['title']}")
    print(f"Author: {summary['author']}")
    print(f"Total Volumes: {summary['total_volumes']}")
    print(f"Total Chapters: {summary['total_chapters']}")
    print(f"Completed: {summary['completed_volumes']}/{summary['total_volumes']}")
    print()

    # Volume details
    print(f"{'='*60}")
    print("VOLUMES")
    print(f"{'='*60}\n")

    for vol in summary['volumes']:
        status = "✓ Translated" if vol['is_processed'] else "○ Pending"
        print(f"{status} Volume {vol['volume']}: {vol['chapters']} chapters")
        print(f"    Directory: {vol['directory']}")
        print(f"    Source: {vol['cleaned_path']}")
        if vol['is_processed']:
            print(f"    Output: {vol['translated_path']}")
        print()

    # Verify integrity
    print(f"{'='*60}")
    print("INTEGRITY CHECK")
    print(f"{'='*60}\n")

    integrity = manager.verify_volume_integrity(work_number)

    if integrity['is_complete']:
        print(f"✓ All {integrity['total_volumes']} volumes are accessible")
        print(f"✓ Ready for translation ({integrity['total_chapters']} chapters total)")
    else:
        print(f"✗ Missing {integrity['missing_volumes']} volumes:")
        for missing in integrity['missing_files']:
            print(f"    - Volume {missing['volume']} in {missing['directory']}")
            print(f"      Expected: {missing['expected_path']}")

    return 0


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    exit(main())
