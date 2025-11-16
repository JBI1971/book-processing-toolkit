#!/usr/bin/env python3
"""
Batch Translation for Multiple Multi-Volume Works

Processes multiple complete works (all volumes) from a list or file.
Supports prioritization, filtering, and comprehensive progress tracking.

Usage:
    # Translate specific works
    python scripts/batch_translate_works.py D55 D70 D81

    # Translate from file
    python scripts/batch_translate_works.py --file works_to_translate.txt

    # Translate all multi-volume works
    python scripts/batch_translate_works.py --all-multi-volume

    # Translate works with specific volume counts
    python scripts/batch_translate_works.py --min-volumes 4 --max-volumes 8
"""

import sys
import json
import argparse
import logging
from datetime import datetime
from typing import List, Dict, Any
from tqdm import tqdm


from processors.translation_config import TranslationConfig
from processors.volume_manager import VolumeManager
from scripts.translate_work import WorkTranslationOrchestrator
from utils.load_env_creds import load_env_credentials

logger = logging.getLogger(__name__)


class BatchTranslationManager:
    """
    Manages batch translation of multiple works.

    Features:
    - Queue management with prioritization
    - Progress tracking across works
    - Comprehensive reporting
    - Error recovery
    """

    def __init__(self, config: TranslationConfig):
        """
        Initialize batch manager.

        Args:
            config: Translation configuration
        """
        self.config = config
        self.volume_manager = VolumeManager(
            catalog_path=config.catalog_path,
            source_dir=config.source_dir,
            output_dir=config.output_dir
        )

        self.work_reports: List[Dict[str, Any]] = []
        self.failed_works: List[str] = []
        self.completed_works: List[str] = []

    def translate_batch(
        self,
        work_numbers: List[str],
        min_volumes: Optional[int] = None,
        max_volumes: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Translate multiple works in batch.

        Args:
            work_numbers: List of work numbers to translate
            min_volumes: Optional minimum volume count filter
            max_volumes: Optional maximum volume count filter

        Returns:
            Batch translation report
        """
        start_time = datetime.now()

        logger.info(f"{'='*60}")
        logger.info(f"BATCH TRANSLATION MANAGER")
        logger.info(f"{'='*60}")
        logger.info(f"Works to process: {len(work_numbers)}")

        # Filter by volume count if requested
        if min_volumes or max_volumes:
            work_numbers = self._filter_by_volume_count(work_numbers, min_volumes, max_volumes)
            logger.info(f"After filtering: {len(work_numbers)} works")

        # Process works
        for i, work_number in enumerate(tqdm(work_numbers, desc="Processing works"), 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"WORK {i}/{len(work_numbers)}: {work_number}")
            logger.info(f"{'='*60}\n")

            try:
                # Get work summary
                summary = self.volume_manager.get_work_summary(work_number)

                if not summary['found']:
                    logger.error(f"Work {work_number} not found, skipping")
                    self.failed_works.append(work_number)
                    continue

                logger.info(f"Title: {summary['title']}")
                logger.info(f"Author: {summary['author']}")
                logger.info(f"Volumes: {summary['total_volumes']}")

                # Create orchestrator for this work
                orchestrator = WorkTranslationOrchestrator(self.config)

                # Translate work
                work_report = orchestrator.translate_work(work_number)

                # Track result
                if work_report.get('success', True):
                    self.completed_works.append(work_number)
                    logger.info(f"✓ Work {work_number} completed successfully")
                else:
                    self.failed_works.append(work_number)
                    logger.error(f"✗ Work {work_number} failed")

                self.work_reports.append(work_report)

            except Exception as e:
                error_msg = f"Failed to process work {work_number}: {e}"
                logger.error(error_msg)
                self.failed_works.append(work_number)
                self.work_reports.append({
                    'work_number': work_number,
                    'success': False,
                    'error': str(e)
                })

        # Generate batch report
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        batch_report = self._generate_batch_report(start_time, end_time, duration)

        # Save report
        report_path = self.config.log_dir / f"batch_translation_{start_time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(batch_report, f, ensure_ascii=False, indent=2)

        logger.info(f"\n{'='*60}")
        logger.info("BATCH TRANSLATION COMPLETE")
        logger.info(f"{'='*60}\n")
        logger.info(f"Report saved: {report_path}")

        return batch_report

    def _filter_by_volume_count(
        self,
        work_numbers: List[str],
        min_volumes: Optional[int],
        max_volumes: Optional[int]
    ) -> List[str]:
        """Filter works by volume count"""
        filtered = []

        for work_number in work_numbers:
            volumes = self.volume_manager.get_volumes_for_work(work_number)
            volume_count = len(volumes)

            if min_volumes and volume_count < min_volumes:
                continue
            if max_volumes and volume_count > max_volumes:
                continue

            filtered.append(work_number)

        return filtered

    def _generate_batch_report(
        self,
        start_time: datetime,
        end_time: datetime,
        duration: float
    ) -> Dict[str, Any]:
        """Generate comprehensive batch report"""

        # Aggregate statistics
        total_volumes = sum(r.get('volumes', {}).get('total', 0) for r in self.work_reports)
        completed_volumes = sum(r.get('volumes', {}).get('completed', 0) for r in self.work_reports)
        total_chapters = sum(r.get('statistics', {}).get('total_chapters', 0) for r in self.work_reports)
        total_blocks = sum(r.get('statistics', {}).get('total_blocks', 0) for r in self.work_reports)
        successful_blocks = sum(r.get('statistics', {}).get('successful_blocks', 0) for r in self.work_reports)
        total_tokens = sum(r.get('statistics', {}).get('total_tokens', 0) for r in self.work_reports)

        return {
            'batch_summary': {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration_seconds': duration,
                'duration_formatted': f"{duration / 3600:.1f} hours"
            },
            'works': {
                'total': len(self.work_reports),
                'completed': len(self.completed_works),
                'failed': len(self.failed_works),
                'completion_rate': (len(self.completed_works) / len(self.work_reports) * 100) if self.work_reports else 0
            },
            'volumes': {
                'total': total_volumes,
                'completed': completed_volumes,
                'completion_rate': (completed_volumes / total_volumes * 100) if total_volumes > 0 else 0
            },
            'statistics': {
                'total_chapters': total_chapters,
                'total_blocks': total_blocks,
                'successful_blocks': successful_blocks,
                'failed_blocks': total_blocks - successful_blocks,
                'success_rate': (successful_blocks / total_blocks * 100) if total_blocks > 0 else 0,
                'total_tokens': total_tokens,
                'estimated_cost_usd': total_tokens * 0.00015 / 1000
            },
            'completed_works': self.completed_works,
            'failed_works': self.failed_works,
            'work_reports': self.work_reports,
            'config': {
                'model': self.config.model,
                'temperature': self.config.temperature,
                'max_retries': self.config.max_retries,
                'rate_limit_delay': self.config.rate_limit_delay
            }
        }


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description='Batch translate multiple wuxia works',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Translate specific works
  python scripts/batch_translate_works.py D55 D70 D81

  # Translate from file (one work_number per line)
  python scripts/batch_translate_works.py --file works.txt

  # Translate all multi-volume works
  python scripts/batch_translate_works.py --all-multi-volume

  # Translate works with 4-8 volumes
  python scripts/batch_translate_works.py --all-multi-volume --min-volumes 4 --max-volumes 8

  # Preview without translating
  python scripts/batch_translate_works.py --all-multi-volume --list-only
        """
    )

    parser.add_argument(
        'work_numbers',
        nargs='*',
        help='Work numbers to translate (e.g., D55 D70 D81)'
    )

    parser.add_argument(
        '--file',
        type=Path,
        help='File containing work numbers (one per line)'
    )

    parser.add_argument(
        '--all-multi-volume',
        action='store_true',
        help='Translate all multi-volume works'
    )

    parser.add_argument(
        '--min-volumes',
        type=int,
        help='Minimum number of volumes (filter)'
    )

    parser.add_argument(
        '--max-volumes',
        type=int,
        help='Maximum number of volumes (filter)'
    )

    parser.add_argument(
        '--list-only',
        action='store_true',
        help='List works without translating'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run mode (no file writes)'
    )

    parser.add_argument(
        '--output-dir',
        type=Path,
        help='Custom output directory'
    )

    parser.add_argument(
        '--model',
        default='gpt-4.1-nano',
        help='OpenAI model to use (default: gpt-4.1-nano)'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Initialize configuration
    config = TranslationConfig(
        model=args.model,
        dry_run=args.dry_run,
        verbose=args.verbose
    )

    if args.output_dir:
        config.output_dir = args.output_dir

    # Determine work numbers to process
    work_numbers = []

    if args.work_numbers:
        work_numbers = args.work_numbers
    elif args.file:
        if not args.file.exists():
            logger.error(f"File not found: {args.file}")
            return 1
        with open(args.file, 'r') as f:
            work_numbers = [line.strip() for line in f if line.strip()]
    elif args.all_multi_volume:
        volume_manager = VolumeManager(
            catalog_path=config.catalog_path,
            source_dir=config.source_dir,
            output_dir=config.output_dir
        )
        multi_volume_works = volume_manager.get_all_multi_volume_works()
        work_numbers = [work_num for work_num, _ in multi_volume_works]
    else:
        parser.print_help()
        return 1

    if not work_numbers:
        logger.error("No work numbers to process")
        return 1

    # List mode
    if args.list_only:
        volume_manager = VolumeManager(
            catalog_path=config.catalog_path,
            source_dir=config.source_dir,
            output_dir=config.output_dir
        )

        print(f"\n{'='*60}")
        print(f"WORKS TO TRANSLATE ({len(work_numbers)})")
        print(f"{'='*60}\n")

        for work_number in work_numbers:
            summary = volume_manager.get_work_summary(work_number)
            if summary['found']:
                print(f"{work_number}: {summary['title']} by {summary['author']}")
                print(f"    Volumes: {summary['total_volumes']}, Chapters: {summary['total_chapters']}")
            else:
                print(f"{work_number}: NOT FOUND")

        return 0

    # Load API credentials
    try:
        load_env_credentials(required_keys=['OPENAI_API_KEY'])
    except Exception as e:
        logger.error(f"Failed to load API credentials: {e}")
        return 1

    # Initialize batch manager
    manager = BatchTranslationManager(config)

    # Print configuration
    print(f"\n{'='*60}")
    print(f"BATCH TRANSLATION CONFIGURATION")
    print(f"{'='*60}\n")
    print(f"Works: {len(work_numbers)}")
    print(f"Model: {config.model}")
    print(f"Output: {config.output_dir}")
    if args.min_volumes:
        print(f"Min Volumes: {args.min_volumes}")
    if args.max_volumes:
        print(f"Max Volumes: {args.max_volumes}")
    if args.dry_run:
        print("⚠ DRY RUN MODE")
    print()

    # Execute batch translation
    report = manager.translate_batch(
        work_numbers=work_numbers,
        min_volumes=args.min_volumes,
        max_volumes=args.max_volumes
    )

    # Print summary
    print(f"\n{'='*60}")
    print("BATCH TRANSLATION SUMMARY")
    print(f"{'='*60}\n")

    works = report.get('works', {})
    volumes = report.get('volumes', {})
    stats = report.get('statistics', {})
    batch = report.get('batch_summary', {})

    print(f"✓ Works: {works.get('completed')}/{works.get('total')} completed ({works.get('completion_rate', 0):.1f}%)")
    print(f"✓ Volumes: {volumes.get('completed')}/{volumes.get('total')} completed ({volumes.get('completion_rate', 0):.1f}%)")
    print(f"✓ Chapters: {stats.get('total_chapters', 0):,}")
    print(f"✓ Blocks: {stats.get('successful_blocks', 0):,}/{stats.get('total_blocks', 0):,} ({stats.get('success_rate', 0):.1f}%)")
    print(f"✓ Tokens: {stats.get('total_tokens', 0):,}")
    print(f"✓ Estimated Cost: ${stats.get('estimated_cost_usd', 0):.2f}")
    print(f"✓ Duration: {batch.get('duration_formatted')}")

    if report.get('failed_works'):
        print(f"\n⚠ Failed works ({len(report['failed_works'])}):")
        for work_num in report['failed_works']:
            print(f"    - {work_num}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
