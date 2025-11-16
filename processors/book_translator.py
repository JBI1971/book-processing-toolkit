#!/usr/bin/env python3
"""
Book Translator - Processes Complete Books (Single Volumes)

Translates cleaned JSON files chapter-by-chapter with:
- Cultural and historical annotations
- Progress tracking and checkpointing
- Error recovery and retry logic
- Token usage tracking
"""

import sys
import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from tqdm import tqdm


from processors.translator import TranslationService, TranslationRequest
from processors.translation_config import (
    TranslationConfig,
    ChapterProgress,
    TranslationReport,
    get_checkpoint_path,
    setup_logging
)

logger = logging.getLogger(__name__)


class BookTranslator:
    """
    Translates a complete book (cleaned JSON) with cultural annotations.

    Features:
    - Chapter-by-chapter processing with progress tracking
    - Checkpoint/resume functionality
    - Concurrent block processing within chapters
    - Comprehensive error handling and reporting
    """

    def __init__(self, config: TranslationConfig):
        """
        Initialize book translator.

        Args:
            config: Translation configuration
        """
        self.config = config
        self.translation_service = TranslationService(
            model=config.model,
            temperature=config.temperature,
            max_retries=config.max_retries,
            timeout=config.timeout
        )

        self.total_tokens = 0
        self.errors = []
        self.warnings = []

        # Thread-safe locks
        self._state_lock = Lock()  # For shared state updates
        self._file_lock = Lock()  # For file I/O

    def translate_book(
        self,
        input_path: Path,
        output_path: Path,
        work_number: str,
        volume: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Translate a complete book from cleaned JSON.

        Args:
            input_path: Path to cleaned JSON file
            output_path: Path for translated output
            work_number: Work number (e.g., "D55")
            volume: Volume number (e.g., "001")

        Returns:
            Translation report dictionary
        """
        start_time = datetime.now()

        # Setup logging
        book_logger = setup_logging(self.config, work_number, volume)
        book_logger.info(f"Starting translation: {input_path}")
        book_logger.info(f"Output: {output_path}")

        # Load cleaned JSON
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                book_data = json.load(f)
        except Exception as e:
            error_msg = f"Failed to load input file: {e}"
            book_logger.error(error_msg)
            return self._create_error_report(work_number, error_msg, start_time)

        # Extract metadata
        meta = book_data.get('meta', {})
        title = meta.get('title', 'Unknown')
        author = meta.get('author', 'Unknown')

        book_logger.info(f"Book: {title} by {author}")

        # Get chapters
        chapters = book_data.get('structure', {}).get('body', {}).get('chapters', [])
        if not chapters:
            error_msg = "No chapters found in book"
            book_logger.error(error_msg)
            return self._create_error_report(work_number, error_msg, start_time)

        book_logger.info(f"Found {len(chapters)} chapters to translate")

        # Initialize progress tracking
        self._total_chapters = len(chapters)
        self._chapter_progress_list = []
        self._current_chapter_progress = None

        # Load checkpoint if resuming
        checkpoint = self._load_checkpoint(work_number, volume)
        completed_chapter_ids = set(checkpoint.get('completed_chapters', []))

        if completed_chapter_ids:
            book_logger.info(f"Resuming from checkpoint: {len(completed_chapter_ids)} chapters already completed")

        # Translate chapters
        translated_chapters = []
        chapter_reports = []
        total_blocks = 0
        successful_blocks = 0

        for i, chapter in enumerate(tqdm(chapters, desc="Translating chapters")):
            chapter_id = chapter.get('id', f'chapter_{i}')

            # Skip if already completed
            if self.config.skip_completed and chapter_id in completed_chapter_ids:
                book_logger.info(f"Skipping chapter {chapter_id}: already completed")
                translated_chapters.append(chapter)  # Keep existing translation
                continue

            # Translate chapter
            book_logger.info(f"Translating chapter {i+1}/{len(chapters)}: {chapter.get('title', 'Untitled')}")

            try:
                # Update current chapter progress
                self._current_chapter_progress = {
                    'chapter_id': chapter_id,
                    'chapter_number': i + 1,
                    'title': chapter.get('title', 'Untitled'),
                    'total_blocks': len(chapter.get('content_blocks', [])),
                    'completed_blocks': 0
                }

                translated_chapter, chapter_report = self._translate_chapter(
                    chapter,
                    book_logger,
                    output_path=output_path,
                    book_data=book_data
                )
                translated_chapters.append(translated_chapter)
                chapter_reports.append(chapter_report)

                total_blocks += chapter_report['total_blocks']
                successful_blocks += chapter_report['successful_blocks']

                # Update current chapter progress to completed
                self._current_chapter_progress['completed_blocks'] = chapter_report['successful_blocks']
                self._chapter_progress_list.append(self._current_chapter_progress.copy())

                # Save checkpoint
                if self.config.save_checkpoints:
                    completed_chapter_ids.add(chapter_id)
                    self._save_checkpoint(work_number, volume, list(completed_chapter_ids))

                # Rate limiting
                time.sleep(self.config.rate_limit_delay)

            except Exception as e:
                error_msg = f"Failed to translate chapter {chapter_id}: {e}"
                book_logger.error(error_msg)
                self.errors.append({
                    'chapter_id': chapter_id,
                    'chapter_title': chapter.get('title', 'Unknown'),
                    'error': str(e)
                })

                # Keep original chapter if translation fails
                translated_chapters.append(chapter)

        # Update book data with translations
        book_data['structure']['body']['chapters'] = translated_chapters

        # Add translation metadata
        if 'translation' not in book_data['meta']:
            book_data['meta']['translation'] = {}

        book_data['meta']['translation'].update({
            'target_language': 'en',
            'source_language': meta.get('language', 'zh-Hant'),
            'translator': 'AI (OpenAI GPT-4o-mini)',
            'translation_date': datetime.now().isoformat(),
            'model': self.config.model,
            'total_tokens': self.total_tokens,
            'chapters_translated': len(translated_chapters),
            'blocks_translated': successful_blocks
        })

        # Save output
        if not self.config.dry_run:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(book_data, f, ensure_ascii=False, indent=2)
            book_logger.info(f"Saved translated book to {output_path}")

        # Generate report
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        report = TranslationReport(
            work_number=work_number,
            work_title=title,
            volumes_processed=1,
            total_chapters=len(chapters),
            total_blocks=total_blocks,
            successful_blocks=successful_blocks,
            failed_blocks=total_blocks - successful_blocks,
            total_tokens=self.total_tokens,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            duration_seconds=duration,
            errors=self.errors,
            warnings=self.warnings
        )

        book_logger.info(f"Translation complete: {successful_blocks}/{total_blocks} blocks successful")
        book_logger.info(f"Duration: {duration/60:.1f} minutes")
        book_logger.info(f"Tokens used: {self.total_tokens:,}")

        # Save report to file
        report_dict = report.to_dict()
        if not self.config.dry_run:
            report_filename = f"translation_report_{work_number}"
            if volume:
                report_filename += f"_{volume}"
            report_filename += ".json"

            report_path = self.config.output_dir / report_filename
            report_path.parent.mkdir(parents=True, exist_ok=True)

            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report_dict, f, ensure_ascii=False, indent=2)

            book_logger.info(f"Saved translation report to {report_path}")

        return report_dict

    def _translate_block(
        self,
        block: Dict[str, Any],
        block_index: int,
        chapter_id: str
    ) -> tuple[str, Any, Optional[Exception]]:
        """
        Translate a single block (thread-safe helper).

        Args:
            block: Content block to translate
            block_index: Index of block for tracking
            chapter_id: Parent chapter ID for error reporting

        Returns:
            Tuple of (block_id, translation_response, error)
        """
        block_id = block.get('id', f'block_{block_index}')

        try:
            # Prepare translation request
            request = TranslationRequest(
                content_text_id=block_index + 1,
                content_source_text=block['content']
            )

            # Translate
            response = self.translation_service.translate(request)

            # Rate limiting (per block)
            time.sleep(self.config.rate_limit_delay)

            return (block_id, response, None)

        except Exception as e:
            logger.error(f"Failed to translate block {block_id}: {e}")
            return (block_id, None, e)

    def _translate_chapter(
        self,
        chapter: Dict[str, Any],
        logger: logging.Logger,
        output_path: Optional[Path] = None,
        book_data: Optional[Dict[str, Any]] = None
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Translate a single chapter with parallel block processing.

        Args:
            chapter: Chapter data with content_blocks
            logger: Logger instance
            output_path: Output file path for incremental saves
            book_data: Complete book data for incremental saves

        Returns:
            Tuple of (translated_chapter, chapter_report)
        """
        chapter_id = chapter.get('id', 'unknown')
        chapter_title = chapter.get('title', 'Untitled')
        content_blocks = chapter.get('content_blocks', [])

        logger.info(f"Chapter {chapter_id}: {chapter_title} ({len(content_blocks)} blocks)")

        # Track progress
        progress = ChapterProgress(
            chapter_id=chapter_id,
            chapter_number=chapter.get('chapter_number', 0),
            title=chapter_title,
            total_blocks=len(content_blocks),
            completed_blocks=0,
            token_usage=0
        )

        # Filter blocks that need translation (skip headings, etc.)
        translatable_blocks = [
            block for block in content_blocks
            if block.get('type') in ['text', 'paragraph', 'narrative', 'dialogue', 'verse', 'document', 'thought', 'descriptive']
            and block.get('content', '').strip()
        ]

        logger.info(f"Translating {len(translatable_blocks)}/{len(content_blocks)} blocks in parallel")

        # Translate blocks in parallel using ThreadPoolExecutor
        block_id_to_translation = {}

        # Create index mapping for blocks
        block_to_index = {
            block.get('id', f'block_{i}'): i
            for i, block in enumerate(translatable_blocks)
        }

        with ThreadPoolExecutor(max_workers=self.config.max_concurrent_chapters) as executor:
            # Submit all translation tasks
            future_to_block = {
                executor.submit(
                    self._translate_block,
                    block,
                    block_to_index[block.get('id', f'block_{i}')],
                    chapter_id
                ): block
                for i, block in enumerate(translatable_blocks)
            }

            # Process completed translations with progress bar
            for future in tqdm(
                as_completed(future_to_block),
                total=len(future_to_block),
                desc=f"  {chapter_title[:30]}",
                leave=False
            ):
                block = future_to_block[future]
                block_id, translation_response, error = future.result()

                if error:
                    # Translation failed
                    with self._state_lock:
                        progress.failed_blocks.append(block_id)
                        self.warnings.append({
                            'chapter_id': chapter_id,
                            'block_id': block_id,
                            'error': str(error)
                        })
                else:
                    # Translation successful
                    with self._state_lock:
                        # Track tokens (approximate)
                        token_count = len(block['content']) + len(
                            translation_response.translated_annotated_content.annotated_content_text
                        )
                        self.total_tokens += token_count
                        progress.token_usage += len(block['content'])

                        # Store translation
                        block_id_to_translation[block_id] = translation_response
                        progress.completed_blocks += 1

                    # Incremental save after each block completes
                    if output_path and book_data:
                        # Update the book_data with current translations
                        self._update_chapter_in_book_data(
                            book_data,
                            chapter_id,
                            content_blocks,
                            block_id_to_translation
                        )
                        self._save_incremental_progress(output_path, book_data)

        # Update chapter with translations
        translated_chapter = chapter.copy()
        translated_content_blocks = []

        for block in content_blocks:
            block_id = block.get('id')
            translation = block_id_to_translation.get(block_id)

            if translation:
                # Create translated block
                translated_block = {
                    'id': block_id,
                    'type': block.get('type'),
                    'original_content': block['content'],
                    'translated_content': translation.translated_annotated_content.annotated_content_text,
                    'footnotes': [
                        {
                            'key': fn.footnote_key,
                            'ideogram': fn.footnote_details.footnote_ideogram,
                            'pinyin': fn.footnote_details.footnote_pinyin,
                            'explanation': fn.footnote_details.footnote_explanation
                        }
                        for fn in translation.translated_annotated_content.content_footnotes
                    ],
                    'content_type': translation.translated_annotated_content.content_type,
                    'epub_id': block.get('epub_id'),
                    'metadata': block.get('metadata', {})
                }
            else:
                # Keep original block if not translated
                translated_block = block

            translated_content_blocks.append(translated_block)

        translated_chapter['content_blocks'] = translated_content_blocks

        # Add chapter-level translation metadata
        translated_chapter['translation_info'] = {
            'translated': True,
            'blocks_translated': progress.completed_blocks,
            'blocks_failed': len(progress.failed_blocks),
            'tokens_used': progress.token_usage
        }

        # Chapter report
        chapter_report = {
            'chapter_id': chapter_id,
            'chapter_title': chapter_title,
            'total_blocks': len(content_blocks),
            'translatable_blocks': len(translatable_blocks),
            'successful_blocks': progress.completed_blocks,
            'failed_blocks': len(progress.failed_blocks),
            'token_usage': progress.token_usage
        }

        return translated_chapter, chapter_report

    def _load_checkpoint(self, work_number: str, volume: Optional[str]) -> Dict[str, Any]:
        """Load checkpoint file if it exists"""
        checkpoint_path = get_checkpoint_path(self.config, work_number, volume)

        if checkpoint_path.exists():
            try:
                with open(checkpoint_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load checkpoint: {e}")

        return {}

    def _save_checkpoint(self, work_number: str, volume: Optional[str], completed_chapters: List[str]):
        """Save checkpoint file with enhanced progress tracking"""
        checkpoint_path = get_checkpoint_path(self.config, work_number, volume)

        try:
            # Build enhanced checkpoint with chapter progress details
            checkpoint_data = {
                'work_number': work_number,
                'volume': volume,
                'total_chapters': self._total_chapters if hasattr(self, '_total_chapters') else len(completed_chapters),
                'completed_chapters': completed_chapters,
                'timestamp': datetime.now().isoformat()
            }

            # Add current chapter details if available
            if hasattr(self, '_current_chapter_progress') and self._current_chapter_progress:
                checkpoint_data['current_chapter'] = self._current_chapter_progress

            # Add chapter progress list if available
            if hasattr(self, '_chapter_progress_list') and self._chapter_progress_list:
                checkpoint_data['chapter_progress'] = [
                    prog.to_dict() if hasattr(prog, 'to_dict') else prog
                    for prog in self._chapter_progress_list
                ]

            with open(checkpoint_path, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.warning(f"Could not save checkpoint: {e}")

    def _update_chapter_in_book_data(
        self,
        book_data: Dict[str, Any],
        chapter_id: str,
        content_blocks: List[Dict[str, Any]],
        block_id_to_translation: Dict[str, Any]
    ):
        """
        Update a chapter's content blocks in the book data with current translations.

        Args:
            book_data: Complete book data structure
            chapter_id: ID of chapter to update
            content_blocks: Original content blocks
            block_id_to_translation: Mapping of block IDs to translation responses
        """
        # Find the chapter in the book data
        chapters = book_data.get('structure', {}).get('body', {}).get('chapters', [])

        for chapter in chapters:
            if chapter.get('id') == chapter_id:
                # Build translated content blocks
                translated_content_blocks = []

                for block in content_blocks:
                    block_id = block.get('id')
                    translation = block_id_to_translation.get(block_id)

                    if translation:
                        # Create translated block
                        translated_block = {
                            'id': block_id,
                            'type': block.get('type'),
                            'original_content': block['content'],
                            'translated_content': translation.translated_annotated_content.annotated_content_text,
                            'footnotes': [
                                {
                                    'key': fn.footnote_key,
                                    'ideogram': fn.footnote_details.footnote_ideogram,
                                    'pinyin': fn.footnote_details.footnote_pinyin,
                                    'explanation': fn.footnote_details.footnote_explanation
                                }
                                for fn in translation.translated_annotated_content.content_footnotes
                            ],
                            'content_type': translation.translated_annotated_content.content_type,
                            'epub_id': block.get('epub_id'),
                            'metadata': block.get('metadata', {})
                        }
                    else:
                        # Keep original block if not yet translated
                        translated_block = block

                    translated_content_blocks.append(translated_block)

                # Update chapter's content blocks
                chapter['content_blocks'] = translated_content_blocks
                break

    def _save_incremental_progress(
        self,
        output_path: Path,
        book_data: Dict[str, Any]
    ):
        """
        Save current translation progress to file (thread-safe).

        Args:
            output_path: Output file path
            book_data: Current book data with partial translations
        """
        if self.config.dry_run:
            return

        with self._file_lock:
            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(book_data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.warning(f"Failed to save incremental progress: {e}")

    def _create_error_report(self, work_number: str, error: str, start_time: datetime) -> Dict[str, Any]:
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
    """CLI testing"""
    import sys
    from utils.load_env_creds import load_env_credentials

    if len(sys.argv) < 3:
        print("Usage: python book_translator.py <input_json> <output_json>")
        print("Example: python book_translator.py cleaned_D55a.json translated_D55a.json")
        return 1

    # Load API credentials
    load_env_credentials(required_keys=['OPENAI_API_KEY'])

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    # Extract work_number from filename
    import re
    match = re.search(r'([A-Z]\d+[a-z]?)', input_path.name)
    work_number = match.group(1) if match else "UNKNOWN"

    # Initialize config and translator
    config = TranslationConfig()
    translator = BookTranslator(config)

    # Translate
    print(f"\nTranslating: {input_path}")
    print(f"Output: {output_path}\n")

    report = translator.translate_book(
        input_path=input_path,
        output_path=output_path,
        work_number=work_number
    )

    # Print report
    print(f"\n{'='*60}")
    print("TRANSLATION REPORT")
    print(f"{'='*60}\n")

    if report.get('success', True):
        print(f"✓ Translation completed successfully")
        print(f"  Chapters: {report['total_chapters']}")
        print(f"  Blocks: {report['successful_blocks']}/{report['total_blocks']}")
        print(f"  Success Rate: {report.get('success_rate', 0):.1f}%")
        print(f"  Tokens: {report['total_tokens']:,}")
        print(f"  Duration: {report['duration_seconds']/60:.1f} minutes")

        if report['errors']:
            print(f"\n⚠ Errors: {len(report['errors'])}")
    else:
        print(f"✗ Translation failed: {report.get('error')}")

    return 0


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    exit(main())
