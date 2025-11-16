#!/usr/bin/env python3
"""
Work Discovery and Listing Utility

Helps discover and select works for translation. Provides filtering,
sorting, and detailed information about available works.

Usage:
    # List all multi-volume works
    python scripts/list_works.py --multi-volume

    # List works by specific author
    python scripts/list_works.py --author 金庸

    # List works with volume counts
    python scripts/list_works.py --min-volumes 4 --max-volumes 8

    # Show detailed info for specific work
    python scripts/list_works.py D55 --details

    # Export work list to file
    python scripts/list_works.py --multi-volume --export works_to_translate.txt
"""

import sys
import argparse
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import defaultdict


from processors.translation_config import TranslationConfig
from processors.volume_manager import VolumeManager


class WorkDiscovery:
    """Discover and list available works for translation"""

    def __init__(self, catalog_path: Path, source_dir: Path, output_dir: Path):
        self.catalog_path = catalog_path
        self.volume_manager = VolumeManager(catalog_path, source_dir, output_dir)

    def get_all_works(self) -> List[Dict[str, Any]]:
        """Get all works from catalog"""
        conn = sqlite3.connect(self.catalog_path)
        cursor = conn.cursor()

        query = """
            SELECT
                w.work_number,
                w.title_chinese,
                w.title_english,
                w.author_chinese,
                w.author_english,
                w.category_english,
                COUNT(DISTINCT wf.volume) as volume_count
            FROM works w
            LEFT JOIN work_files wf ON w.work_id = wf.work_id
            GROUP BY w.work_number
            ORDER BY w.work_number
        """

        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()

        works = []
        for row in rows:
            works.append({
                'work_number': row[0],
                'title_chinese': row[1],
                'title_english': row[2],
                'author_chinese': row[3],
                'author_english': row[4],
                'category': row[5],
                'volume_count': row[6]
            })

        return works

    def filter_works(
        self,
        works: List[Dict[str, Any]],
        author: Optional[str] = None,
        category: Optional[str] = None,
        min_volumes: Optional[int] = None,
        max_volumes: Optional[int] = None,
        multi_volume_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Filter works by criteria"""
        filtered = works

        if author:
            author_lower = author.lower()
            filtered = [
                w for w in filtered
                if (w['author_chinese'] and author_lower in w['author_chinese'].lower()) or
                   (w['author_english'] and author_lower in w['author_english'].lower())
            ]

        if category:
            category_lower = category.lower()
            filtered = [
                w for w in filtered
                if w['category'] and category_lower in w['category'].lower()
            ]

        if multi_volume_only:
            filtered = [w for w in filtered if w['volume_count'] > 1]

        if min_volumes:
            filtered = [w for w in filtered if w['volume_count'] >= min_volumes]

        if max_volumes:
            filtered = [w for w in filtered if w['volume_count'] <= max_volumes]

        return filtered

    def get_works_by_author(self) -> Dict[str, List[Dict[str, Any]]]:
        """Group works by author"""
        works = self.get_all_works()
        by_author = defaultdict(list)

        for work in works:
            author = work['author_chinese'] or work['author_english'] or 'Unknown'
            by_author[author].append(work)

        return dict(by_author)

    def get_translation_status(self, work_number: str) -> Dict[str, Any]:
        """Get translation status for a work"""
        summary = self.volume_manager.get_work_summary(work_number)
        return {
            'found': summary['found'],
            'total_volumes': summary.get('total_volumes', 0),
            'completed_volumes': summary.get('completed_volumes', 0),
            'pending_volumes': summary.get('pending_volumes', 0),
            'is_complete': summary.get('completed_volumes', 0) == summary.get('total_volumes', 0)
        }


def print_work_list(works: List[Dict[str, Any]], show_details: bool = False):
    """Print formatted work list"""
    if not works:
        print("No works found matching criteria")
        return

    print(f"\n{'='*80}")
    print(f"WORKS ({len(works)})")
    print(f"{'='*80}\n")

    # Group by volume count for better organization
    single_volume = [w for w in works if w['volume_count'] == 1]
    multi_volume = [w for w in works if w['volume_count'] > 1]

    if multi_volume:
        print(f"MULTI-VOLUME WORKS ({len(multi_volume)}):")
        print(f"{'-'*80}\n")

        for work in sorted(multi_volume, key=lambda x: x['volume_count'], reverse=True):
            print(f"{work['work_number']:8s} [{work['volume_count']} vols] {work['title_chinese']}")
            if work['author_chinese']:
                print(f"         by {work['author_chinese']}")
            if show_details:
                if work['title_english']:
                    print(f"         EN: {work['title_english']}")
                if work['category']:
                    print(f"         Category: {work['category']}")
            print()

    if single_volume and show_details:
        print(f"\nSINGLE-VOLUME WORKS ({len(single_volume)}):")
        print(f"{'-'*80}\n")

        for work in single_volume[:20]:  # Limit display
            print(f"{work['work_number']:8s} {work['title_chinese']}")
            if work['author_chinese']:
                print(f"         by {work['author_chinese']}")
            print()

        if len(single_volume) > 20:
            print(f"... and {len(single_volume) - 20} more single-volume works")


def print_work_details(work_number: str, discovery: WorkDiscovery):
    """Print detailed information for a specific work"""
    summary = discovery.volume_manager.get_work_summary(work_number)

    if not summary['found']:
        print(f"\n✗ Work {work_number} not found")
        return

    print(f"\n{'='*80}")
    print(f"WORK DETAILS: {work_number}")
    print(f"{'='*80}\n")

    print(f"Title: {summary['title']}")
    print(f"Author: {summary['author']}")
    print(f"Volumes: {summary['total_volumes']}")
    print(f"Total Chapters: {summary['total_chapters']}")
    print(f"Translation Status: {summary['completed_volumes']}/{summary['total_volumes']} volumes completed")
    print()

    print(f"{'='*80}")
    print("VOLUMES")
    print(f"{'='*80}\n")

    for vol in summary['volumes']:
        status = "✓" if vol['is_processed'] else "○"
        print(f"{status} Volume {vol['volume']}: {vol['chapters']} chapters")
        print(f"    Directory: {vol['directory']}")
        print(f"    Source: {vol['cleaned_path']}")
        if vol['is_processed']:
            print(f"    Translated: {vol['translated_path']}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description='Discover and list works for translation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all multi-volume works
  python scripts/list_works.py --multi-volume

  # List works by Jin Yong (金庸)
  python scripts/list_works.py --author 金庸

  # List works with 4-8 volumes
  python scripts/list_works.py --min-volumes 4 --max-volumes 8

  # Show detailed info for specific work
  python scripts/list_works.py D55 --details

  # Export work numbers to file
  python scripts/list_works.py --multi-volume --export works.txt

  # List by author with details
  python scripts/list_works.py --author 金庸 --show-details
        """
    )

    parser.add_argument(
        'work_numbers',
        nargs='*',
        help='Specific work numbers to show details for'
    )

    parser.add_argument(
        '--multi-volume',
        action='store_true',
        help='List only multi-volume works'
    )

    parser.add_argument(
        '--author',
        help='Filter by author (Chinese or English name)'
    )

    parser.add_argument(
        '--category',
        help='Filter by category'
    )

    parser.add_argument(
        '--min-volumes',
        type=int,
        help='Minimum number of volumes'
    )

    parser.add_argument(
        '--max-volumes',
        type=int,
        help='Maximum number of volumes'
    )

    parser.add_argument(
        '--details',
        action='store_true',
        help='Show detailed information'
    )

    parser.add_argument(
        '--show-details',
        action='store_true',
        help='Show more details in list view'
    )

    parser.add_argument(
        '--export',
        type=Path,
        help='Export work numbers to file'
    )

    parser.add_argument(
        '--by-author',
        action='store_true',
        help='Group by author'
    )

    args = parser.parse_args()

    # Initialize
    config = TranslationConfig()
    discovery = WorkDiscovery(
        catalog_path=config.catalog_path,
        source_dir=config.source_dir,
        output_dir=config.output_dir
    )

    # Show details for specific works
    if args.work_numbers:
        for work_number in args.work_numbers:
            print_work_details(work_number, discovery)
        return 0

    # Get and filter works
    works = discovery.get_all_works()
    works = discovery.filter_works(
        works,
        author=args.author,
        category=args.category,
        min_volumes=args.min_volumes,
        max_volumes=args.max_volumes,
        multi_volume_only=args.multi_volume
    )

    # Group by author view
    if args.by_author:
        by_author = defaultdict(list)
        for work in works:
            author = work['author_chinese'] or work['author_english'] or 'Unknown'
            by_author[author].append(work)

        print(f"\n{'='*80}")
        print(f"WORKS BY AUTHOR ({len(by_author)} authors, {len(works)} works)")
        print(f"{'='*80}\n")

        for author, author_works in sorted(by_author.items()):
            print(f"{author} ({len(author_works)} works):")
            for work in sorted(author_works, key=lambda x: x['volume_count'], reverse=True):
                vols = f"[{work['volume_count']} vols]" if work['volume_count'] > 1 else ""
                print(f"  {work['work_number']:8s} {vols:10s} {work['title_chinese']}")
            print()
        return 0

    # Regular list view
    print_work_list(works, args.show_details or args.details)

    # Export if requested
    if args.export:
        work_numbers = [w['work_number'] for w in works]
        with open(args.export, 'w') as f:
            for work_num in work_numbers:
                f.write(f"{work_num}\n")
        print(f"\n✓ Exported {len(work_numbers)} work numbers to {args.export}")

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}\n")
    print(f"Total works: {len(works)}")
    print(f"Multi-volume: {len([w for w in works if w['volume_count'] > 1])}")
    print(f"Single-volume: {len([w for w in works if w['volume_count'] == 1])}")
    total_volumes = sum(w['volume_count'] for w in works)
    print(f"Total volumes: {total_volumes}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
