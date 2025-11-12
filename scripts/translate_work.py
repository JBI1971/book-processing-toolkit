#!/usr/bin/env python3
"""
Translation Orchestrator for Multi-Volume Works

Coordinates translation of all volumes for a given work number.
Handles volume ordering, progress tracking, and comprehensive reporting.

Usage:
    python scripts/translate_work.py D55
    python scripts/translate_work.py D55 --resume
    python scripts/translate_work.py D55 --volume 001
"""

import sys
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from processors.translation_config import TranslationConfig, WorkProgress, setup_logging
from processors.volume_manager import VolumeManager
from processors.book_translator import BookTranslator
from utils.load_env_creds import load_env_credentials

logger = logging.getLogger(__name__)


class WorkTranslationOrchestrator:
    """
    Orchestrates translation of all volumes for a work.

    Features:
    - Discovers all volumes via catalog database
    - Processes volumes in order
    - Tracks progress across volumes
    - Generates comprehensive reports
    - Supports resume functionality
    """

    def __init__(self, config: TranslationConfig):
        """
        Initialize orchestrator.

        Args:
            config: Translation configuration
        """
        self.config = config
        self.volume_manager = VolumeManager(
            catalog_path=config.catalog_path,
            source_dir=config.source_dir,
            output_dir=config.output_dir
        )

        self.work_progress: Optional[WorkProgress] = None
        self.volume_reports: List[Dict[str, Any]] = []

    def translate_work(
        self,
        work_number: str,
        specific_volume: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Translate all volumes of a work (or specific volume).

        Args:
            work_number: Work number (e.g., "D55")
            specific_volume: Optional specific volume to translate (e.g., "001")

        Returns:
            Comprehensive work report
        """
        start_time = datetime.now()

        # Setup logging
        work_logger = setup_logging(self.config, work_number)
        work_logger.info(f"{'='*60}")
        work_logger.info(f"TRANSLATION ORCHESTRATOR: {work_number}")
        work_logger.info(f"{'='*60}")

        # Get volumes
        volumes = self.volume_manager.get_volumes_for_work(work_number)

        if not volumes:
            error_msg = f"No volumes found for work {work_number}"
            work_logger.error(error_msg)
            return self._create_error_report(work_number, error_msg, start_time)

        # Filter to specific volume if requested
        if specific_volume:
            volumes = [v for v in volumes if v.volume == specific_volume]
            if not volumes:
                error_msg = f"Volume {specific_volume} not found for work {work_number}"
                work_logger.error(error_msg)
                return self._create_error_report(work_number, error_msg, start_time)

        # Initialize progress tracking
        self.work_progress = WorkProgress(
            work_number=work_number,
            title=volumes[0].title,
            author=volumes[0].author,
            total_volumes=len(volumes)
        )

        work_logger.info(f"Work: {self.work_progress.title} by {self.work_progress.author}")
        work_logger.info(f"Volumes to process: {len(volumes)}")

        # Verify integrity
        integrity = self.volume_manager.verify_volume_integrity(work_number)
        if not integrity['is_complete']:
            work_logger.warning(f"⚠ Incomplete volume set: {integrity['missing_volumes']} volumes missing")
            for missing in integrity['missing_files']:
                work_logger.warning(f"  - Volume {missing['volume']}: {missing['expected_path']}")

        # Process volumes
        for i, volume_info in enumerate(volumes, 1):
            work_logger.info(f"\n{'='*60}")
            work_logger.info(f"VOLUME {i}/{len(volumes)}: {volume_info.volume}")
            work_logger.info(f"{'='*60}\n")

            # Skip if already processed
            if self.config.skip_completed and volume_info.is_processed:
                work_logger.info(f"✓ Volume {volume_info.volume} already translated, skipping")
                self.work_progress.completed_volumes.append(volume_info.volume)
                continue

            # Check if source file exists
            if not volume_info.cleaned_json_path or not volume_info.cleaned_json_path.exists():
                error_msg = f"Source file not found: {volume_info.cleaned_json_path}"
                work_logger.error(error_msg)
                self.work_progress.failed_volumes.append(volume_info.volume)
                self.volume_reports.append({
                    'volume': volume_info.volume,
                    'success': False,
                    'error': error_msg
                })
                continue

            # Translate volume
            self.work_progress.current_volume = volume_info.volume

            try:
                work_logger.info(f"Translating: {volume_info.cleaned_json_path.name}")
                work_logger.info(f"Output: {volume_info.translated_json_path}")

                # Initialize translator
                translator = BookTranslator(self.config)

                # Translate
                volume_report = translator.translate_book(
                    input_path=volume_info.cleaned_json_path,
                    output_path=volume_info.translated_json_path,
                    work_number=work_number,
                    volume=volume_info.volume
                )

                # Track success
                if volume_report.get('success', True):
                    self.work_progress.completed_volumes.append(volume_info.volume)
                    work_logger.info(f"✓ Volume {volume_info.volume} translated successfully")
                else:
                    self.work_progress.failed_volumes.append(volume_info.volume)
                    work_logger.error(f"✗ Volume {volume_info.volume} translation failed")

                self.volume_reports.append(volume_report)

            except Exception as e:
                error_msg = f"Translation failed for volume {volume_info.volume}: {e}"
                work_logger.error(error_msg)
                self.work_progress.failed_volumes.append(volume_info.volume)
                self.volume_reports.append({
                    'volume': volume_info.volume,
                    'success': False,
                    'error': str(e)
                })

        # Generate final report
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        final_report = self._generate_final_report(work_number, start_time, end_time, duration)

        # Save report
        report_path = self.config.log_dir / f"{work_number}_translation_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(final_report, f, ensure_ascii=False, indent=2)

        work_logger.info(f"\n{'='*60}")
        work_logger.info("TRANSLATION COMPLETE")
        work_logger.info(f"{'='*60}\n")
        work_logger.info(f"Report saved: {report_path}")

        return final_report

    def _generate_final_report(
        self,
        work_number: str,
        start_time: datetime,
        end_time: datetime,
        duration: float
    ) -> Dict[str, Any]:
        """Generate comprehensive final report"""

        # Aggregate statistics
        total_chapters = sum(r.get('total_chapters', 0) for r in self.volume_reports)
        total_blocks = sum(r.get('total_blocks', 0) for r in self.volume_reports)
        successful_blocks = sum(r.get('successful_blocks', 0) for r in self.volume_reports)
        total_tokens = sum(r.get('total_tokens', 0) for r in self.volume_reports)

        # Collect all errors
        all_errors = []
        for report in self.volume_reports:
            if 'errors' in report:
                all_errors.extend(report['errors'])

        return {
            'work_number': work_number,
            'work_title': self.work_progress.title if self.work_progress else 'Unknown',
            'author': self.work_progress.author if self.work_progress else 'Unknown',
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration_seconds': duration,
            'duration_formatted': f"{duration / 60:.1f} minutes",
            'volumes': {
                'total': self.work_progress.total_volumes if self.work_progress else 0,
                'completed': len(self.work_progress.completed_volumes) if self.work_progress else 0,
                'failed': len(self.work_progress.failed_volumes) if self.work_progress else 0,
                'completion_percentage': self.work_progress.completion_percentage if self.work_progress else 0
            },
            'statistics': {
                'total_chapters': total_chapters,
                'total_blocks': total_blocks,
                'successful_blocks': successful_blocks,
                'failed_blocks': total_blocks - successful_blocks,
                'success_rate': (successful_blocks / total_blocks * 100) if total_blocks > 0 else 0,
                'total_tokens': total_tokens,
                'estimated_cost_usd': total_tokens * 0.00015 / 1000  # GPT-4o-mini pricing
            },
            'errors': all_errors,
            'volume_reports': self.volume_reports,
            'config': {
                'model': self.config.model,
                'temperature': self.config.temperature,
                'max_retries': self.config.max_retries,
                'rate_limit_delay': self.config.rate_limit_delay
            }
        }

    def _create_error_report(
        self,
        work_number: str,
        error: str,
        start_time: datetime
    ) -> Dict[str, Any]:
        """Create error report"""
        end_time = datetime.now()
        return {
            'work_number': work_number,
            'success': False,
            'error': error,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration_seconds': (end_time - start_time).total_seconds()
        }


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description='Translate all volumes of a wuxia work',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Translate all volumes of a work
  python scripts/translate_work.py D55

  # Translate specific volume
  python scripts/translate_work.py D55 --volume 001

  # Resume from checkpoint
  python scripts/translate_work.py D55 --resume

  # Dry run (don't save files)
  python scripts/translate_work.py D55 --dry-run

  # Custom output directory
  python scripts/translate_work.py D55 --output-dir /path/to/output
        """
    )

    parser.add_argument(
        'work_number',
        help='Work number to translate (e.g., D55, D70, J090908)'
    )

    parser.add_argument(
        '--volume',
        help='Translate specific volume only (e.g., 001, 002)'
    )

    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume from checkpoint (skip completed volumes)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run mode (no file writes)'
    )

    parser.add_argument(
        '--output-dir',
        type=Path,
        help='Custom output directory (default: from config)'
    )

    parser.add_argument(
        '--model',
        default='gpt-4o-mini',
        help='OpenAI model to use (default: gpt-4o-mini)'
    )

    parser.add_argument(
        '--max-workers',
        type=int,
        default=3,
        help='Max concurrent chapter processing (default: 3)'
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

    # Load API credentials
    try:
        load_env_credentials(required_keys=['OPENAI_API_KEY'])
    except Exception as e:
        logger.error(f"Failed to load API credentials: {e}")
        return 1

    # Initialize configuration
    config = TranslationConfig(
        model=args.model,
        dry_run=args.dry_run,
        skip_completed=args.resume,
        max_concurrent_chapters=args.max_workers,
        verbose=args.verbose
    )

    if args.output_dir:
        config.output_dir = args.output_dir

    # Initialize orchestrator
    orchestrator = WorkTranslationOrchestrator(config)

    # Translate work
    print(f"\n{'='*60}")
    print(f"TRANSLATION ORCHESTRATOR")
    print(f"{'='*60}\n")
    print(f"Work Number: {args.work_number}")
    if args.volume:
        print(f"Volume: {args.volume}")
    print(f"Model: {config.model}")
    print(f"Output: {config.output_dir}")
    if args.dry_run:
        print("⚠ DRY RUN MODE (no files will be written)")
    print()

    report = orchestrator.translate_work(
        work_number=args.work_number,
        specific_volume=args.volume
    )

    # Print summary
    print(f"\n{'='*60}")
    print("TRANSLATION SUMMARY")
    print(f"{'='*60}\n")

    if report.get('success', True):
        stats = report.get('statistics', {})
        volumes = report.get('volumes', {})

        print(f"✓ Work: {report.get('work_title')} by {report.get('author')}")
        print(f"✓ Volumes: {volumes.get('completed')}/{volumes.get('total')} completed")
        print(f"✓ Chapters: {stats.get('total_chapters')}")
        print(f"✓ Blocks: {stats.get('successful_blocks')}/{stats.get('total_blocks')}")
        print(f"✓ Success Rate: {stats.get('success_rate', 0):.1f}%")
        print(f"✓ Tokens: {stats.get('total_tokens', 0):,}")
        print(f"✓ Estimated Cost: ${stats.get('estimated_cost_usd', 0):.2f}")
        print(f"✓ Duration: {report.get('duration_formatted')}")

        if report.get('errors'):
            print(f"\n⚠ Errors: {len(report['errors'])}")

        report_path = config.log_dir / f"{args.work_number}_translation_report.json"
        print(f"\n📄 Full report: {report_path}")

        return 0
    else:
        print(f"✗ Translation failed: {report.get('error')}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
