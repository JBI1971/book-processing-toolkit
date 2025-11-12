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
from tqdm import tqdm

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

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
                translated_chapter, chapter_report = self._translate_chapter(chapter, book_logger)
                translated_chapters.append(translated_chapter)
                chapter_reports.append(chapter_report)

                total_blocks += chapter_report['total_blocks']
                successful_blocks += chapter_report['successful_blocks']

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

        return report.to_dict()

    def _translate_chapter(
        self,
        chapter: Dict[str, Any],
        logger: logging.Logger
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Translate a single chapter.

        Args:
            chapter: Chapter data with content_blocks
            logger: Logger instance

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

        logger.info(f"Translating {len(translatable_blocks)}/{len(content_blocks)} blocks")

        # Translate blocks
        translated_blocks = []
        block_id_to_translation = {}

        for block in tqdm(translatable_blocks, desc=f"  {chapter_title[:30]}", leave=False):
            block_id = block.get('id', f'block_{len(translated_blocks)}')

            try:
                # Prepare translation request
                request = TranslationRequest(
                    content_text_id=len(translated_blocks) + 1,
                    content_source_text=block['content']
                )

                # Translate
                response = self.translation_service.translate(request)

                # Track tokens (approximate)
                self.total_tokens += len(block['content']) + len(response.translated_annotated_content.annotated_content_text)
                progress.token_usage += len(block['content'])

                # Store translation
                block_id_to_translation[block_id] = response

                progress.completed_blocks += 1

                # Rate limiting
                time.sleep(self.config.rate_limit_delay)

            except Exception as e:
                logger.error(f"Failed to translate block {block_id}: {e}")
                progress.failed_blocks.append(block_id)
                self.warnings.append({
                    'chapter_id': chapter_id,
                    'block_id': block_id,
                    'error': str(e)
                })

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
        """Save checkpoint file"""
        checkpoint_path = get_checkpoint_path(self.config, work_number, volume)

        try:
            checkpoint_data = {
                'work_number': work_number,
                'volume': volume,
                'completed_chapters': completed_chapters,
                'timestamp': datetime.now().isoformat()
            }

            with open(checkpoint_path, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.warning(f"Could not save checkpoint: {e}")

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
