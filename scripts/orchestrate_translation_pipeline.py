#!/usr/bin/env python3
"""
Translation Pipeline Orchestrator

Coordinates multiple specialized agents into a cohesive, extensible translation pipeline:
1. wuxia-translator-annotator - Performs 5-stage translation with cultural footnotes
2. progress-manager - Tracks processing status and generates progress reports
3. translation-ui-manager - Displays results and enables user review
4. footnote-cleanup-optimizer - Removes redundant character name footnotes

Features:
- 5-stage translation pipeline with WIP tracking after each stage
- Incremental saves prevent data loss
- Stage-specific logging for debugging
- Resumable processing (skip completed stages)
- Comprehensive error handling and reporting
- Extensible architecture for adding new agents

Usage:
    # Translate single work
    python scripts/orchestrate_translation_pipeline.py D55

    # Translate specific volume
    python scripts/orchestrate_translation_pipeline.py D55 --volume 001

    # Resume from checkpoint
    python scripts/orchestrate_translation_pipeline.py D55 --resume

    # Skip to specific stage
    python scripts/orchestrate_translation_pipeline.py D55 --start-stage 3

    # Batch translation
    python scripts/orchestrate_translation_pipeline.py --batch --limit 10
"""

import sys
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import translation services
from processors.translator import TranslationService
from processors.book_translator import BookTranslator
from processors.volume_manager import VolumeManager
from utils.cleanup_character_footnotes import CharacterFootnoteCleanup
from processors.structure_validator import StructureValidator


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# PIPELINE STAGES
# =============================================================================

class PipelineStage(Enum):
    """Translation pipeline stages"""
    BODY = (1, "body", "Translate body content - WITH cultural/historical footnotes")
    METADATA = (2, "metadata", "Translate metadata (title, author) - NO footnotes")
    TOC = (3, "toc", "Translate TOC - NO footnotes (clean navigation)")
    HEADINGS = (4, "headings", "Translate chapter headings (use TOC) - NO footnotes")
    SPECIAL = (5, "special", "Translate special sections - WITH footnotes")
    CLEANUP = (6, "cleanup", "Remove redundant character name footnotes")
    VALIDATION = (7, "validation", "Validate translation completeness and quality")

    def __init__(self, num: int, name: str, description: str):
        self.num = num
        self.stage_name = name
        self.description = description

    @property
    def wip_dir_name(self) -> str:
        """WIP directory name for this stage"""
        return f"stage_{self.num}_{self.stage_name}"

    @property
    def log_suffix(self) -> str:
        """Log file suffix for this stage"""
        return f"stage_{self.num}_{self.stage_name}"


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class OrchestrationConfig:
    """Orchestration configuration"""
    # Paths
    source_dir: Path = Path("/Users/jacki/project_files/translation_project/cleaned/COMPLETE_ALL_BOOKS")
    output_dir: Path = Path("/Users/jacki/project_files/translation_project/translated_files")
    wip_dir: Path = Path("/Users/jacki/project_files/translation_project/wip")
    log_dir: Path = Path("/Users/jacki/project_files/translation_project/translation_data/logs")
    catalog_path: Path = Path("/Users/jacki/project_files/translation_project/wuxia_catalog.db")

    # Translation settings
    model: str = "gpt-4.1-nano"
    temperature: float = 0.3
    max_retries: int = 2
    timeout: int = 120

    # Processing settings
    max_concurrent_chapters: int = 3
    rate_limit_delay: float = 0.5
    skip_completed: bool = False
    dry_run: bool = False

    # Pipeline settings
    start_stage: int = 1  # Start from this stage (1-7)
    end_stage: int = 7    # End at this stage (1-7)
    enable_ui_preview: bool = True
    enable_progress_tracking: bool = True

    # Footnote cleanup settings (Stage 6)
    enable_footnote_cleanup: bool = True
    footnote_batch_size: int = 25
    preserve_historical: bool = True
    preserve_legendary: bool = True
    preserve_cultural: bool = True

    # Verbose logging
    verbose: bool = False

    def __post_init__(self):
        """Ensure directories exist"""
        for directory in [self.output_dir, self.wip_dir, self.log_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    def get_stage_wip_dir(self, stage: PipelineStage) -> Path:
        """Get WIP directory for a specific stage"""
        stage_dir = self.wip_dir / stage.wip_dir_name
        stage_dir.mkdir(parents=True, exist_ok=True)
        return stage_dir

    def get_stage_log_path(self, filename: str, stage: PipelineStage) -> Path:
        """Get log path for a specific stage"""
        return self.log_dir / f"{filename}_{stage.log_suffix}.json"


# =============================================================================
# WIP MANAGER
# =============================================================================

class WIPManager:
    """
    Manages Work-In-Progress files across pipeline stages.

    Features:
    - Save WIP after each stage completion
    - Load WIP from any previous stage
    - Track stage completion status
    - Enable rollback to previous stages
    """

    def __init__(self, config: OrchestrationConfig):
        """
        Initialize WIP manager.

        Args:
            config: Orchestration configuration
        """
        self.config = config

    def save_wip(
        self,
        data: Dict[str, Any],
        filename: str,
        stage: PipelineStage,
        stage_log: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        Save WIP file after stage completion.

        Args:
            data: JSON data to save
            filename: Base filename (without extension)
            stage: Pipeline stage
            stage_log: Optional stage processing log

        Returns:
            Path to saved WIP file
        """
        # Save WIP data
        wip_dir = self.config.get_stage_wip_dir(stage)
        wip_path = wip_dir / f"{filename}.json"

        if not self.config.dry_run:
            with open(wip_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"✓ Saved WIP: {wip_path}")
        else:
            logger.info(f"[DRY RUN] Would save WIP: {wip_path}")

        # Save stage log if provided
        if stage_log:
            log_path = self.config.get_stage_log_path(filename, stage)
            if not self.config.dry_run:
                with open(log_path, 'w', encoding='utf-8') as f:
                    json.dump(stage_log, f, ensure_ascii=False, indent=2)
                logger.debug(f"  Saved stage log: {log_path}")

        return wip_path

    def load_wip(self, filename: str, stage: PipelineStage) -> Optional[Dict[str, Any]]:
        """
        Load WIP file from a specific stage.

        Args:
            filename: Base filename (without extension)
            stage: Pipeline stage

        Returns:
            JSON data if WIP exists, None otherwise
        """
        wip_dir = self.config.get_stage_wip_dir(stage)
        wip_path = wip_dir / f"{filename}.json"

        if wip_path.exists():
            with open(wip_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def get_completed_stages(self, filename: str) -> List[PipelineStage]:
        """
        Get list of completed stages for a file.

        Args:
            filename: Base filename (without extension)

        Returns:
            List of completed stages
        """
        completed = []
        for stage in PipelineStage:
            if self.load_wip(filename, stage) is not None:
                completed.append(stage)
        return completed

    def rollback_to_stage(self, filename: str, target_stage: PipelineStage) -> Optional[Dict[str, Any]]:
        """
        Rollback to a previous stage.

        Args:
            filename: Base filename (without extension)
            target_stage: Stage to roll back to

        Returns:
            JSON data from target stage, or None if not found
        """
        logger.info(f"Rolling back to {target_stage.stage_name} (stage {target_stage.num})")
        return self.load_wip(filename, target_stage)


# =============================================================================
# STAGE PROCESSORS
# =============================================================================

class StageProcessor:
    """Base class for stage processors"""

    def __init__(self, config: OrchestrationConfig, wip_manager: WIPManager):
        self.config = config
        self.wip_manager = wip_manager

    def process(self, data: Dict[str, Any], filename: str) -> Dict[str, Any]:
        """
        Process a single stage.

        Args:
            data: Input JSON data
            filename: Base filename

        Returns:
            Processed JSON data
        """
        raise NotImplementedError("Subclasses must implement process()")

    def create_stage_log(
        self,
        stage: PipelineStage,
        start_time: datetime,
        end_time: datetime,
        items_processed: int,
        success: bool,
        errors: List[str] = None
    ) -> Dict[str, Any]:
        """Create stage processing log"""
        duration = (end_time - start_time).total_seconds()

        return {
            "stage_number": stage.num,
            "stage_name": stage.stage_name,
            "description": stage.description,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "items_processed": items_processed,
            "success": success,
            "errors": errors or []
        }


class MetadataTranslationProcessor(StageProcessor):
    """Stage 1: Translate metadata (NO footnotes)"""

    def process(self, data: Dict[str, Any], filename: str) -> Dict[str, Any]:
        """Translate metadata fields"""
        start_time = datetime.now()
        logger.info(f"Stage 1: Translating metadata for {filename}...")

        # Use TranslationService for lightweight translation (NO footnotes)
        translator = TranslationService(
            model=self.config.model,
            temperature=self.config.temperature
        )

        meta = data.get('meta', {})
        items_processed = 0
        errors = []

        # Translate title (if not already translated)
        if 'title_chinese' in meta and not meta.get('title_english'):
            try:
                title_response = translator.translate_from_dict({
                    "content_text_id": 0,
                    "content_source_text": meta['title_chinese']
                })
                # Extract translation without footnotes
                translated_content = title_response.get('translated_annotated_content', {})
                meta['title_english'] = translated_content.get('annotated_content_text', '')
                items_processed += 1
                logger.info(f"  ✓ Title: {meta['title_chinese']} → {meta['title_english']}")
            except Exception as e:
                error_msg = f"Failed to translate title: {e}"
                logger.warning(f"  ✗ {error_msg}")
                errors.append(error_msg)

        # Translate author (if not already translated)
        if 'author_chinese' in meta and not meta.get('author_english'):
            try:
                author_response = translator.translate_from_dict({
                    "content_text_id": 1,
                    "content_source_text": meta['author_chinese']
                })
                translated_content = author_response.get('translated_annotated_content', {})
                meta['author_english'] = translated_content.get('annotated_content_text', '')
                items_processed += 1
                logger.info(f"  ✓ Author: {meta['author_chinese']} → {meta['author_english']}")
            except Exception as e:
                error_msg = f"Failed to translate author: {e}"
                logger.warning(f"  ✗ {error_msg}")
                errors.append(error_msg)

        # Update meta in data
        data['meta'] = meta

        end_time = datetime.now()
        stage_log = self.create_stage_log(
            PipelineStage.METADATA,
            start_time,
            end_time,
            items_processed,
            success=len(errors) == 0,
            errors=errors
        )

        # Save WIP
        self.wip_manager.save_wip(data, filename, PipelineStage.METADATA, stage_log)

        return data


class TOCTranslationProcessor(StageProcessor):
    """Stage 2: Translate TOC (NO footnotes)"""

    def process(self, data: Dict[str, Any], filename: str) -> Dict[str, Any]:
        """Translate TOC entries"""
        start_time = datetime.now()
        logger.info(f"Stage 2: Translating TOC for {filename}...")

        # Use TranslationService for clean navigation (NO footnotes)
        translator = TranslationService(
            model=self.config.model,
            temperature=self.config.temperature
        )

        structure = data.get('structure', {})
        front_matter = structure.get('front_matter', {})
        toc = front_matter.get('toc', [])

        items_processed = 0
        errors = []

        # Translate each TOC entry
        for i, entry in enumerate(toc):
            if isinstance(entry, dict):
                full_title = entry.get('full_title', '')
                chapter_title = entry.get('chapter_title', '')

                # Skip if already translated
                if entry.get('full_title_english'):
                    items_processed += 1
                    continue

                # Translate full title
                if full_title:
                    try:
                        response = translator.translate_from_dict({
                            "content_text_id": i,
                            "content_source_text": full_title
                        })
                        translated_content = response.get('translated_annotated_content', {})
                        entry['full_title_english'] = translated_content.get('annotated_content_text', '')
                        items_processed += 1
                        logger.debug(f"  ✓ TOC[{i}]: {full_title} → {entry['full_title_english']}")
                    except Exception as e:
                        error_msg = f"Failed to translate TOC entry {i}: {e}"
                        logger.warning(f"  ✗ {error_msg}")
                        errors.append(error_msg)

        # Update structure
        if toc:
            front_matter['toc'] = toc
            structure['front_matter'] = front_matter
            data['structure'] = structure

        logger.info(f"  Translated {items_processed}/{len(toc)} TOC entries")

        end_time = datetime.now()
        stage_log = self.create_stage_log(
            PipelineStage.TOC,
            start_time,
            end_time,
            items_processed,
            success=len(errors) == 0,
            errors=errors
        )

        self.wip_manager.save_wip(data, filename, PipelineStage.TOC, stage_log)
        return data


class HeadingTranslationProcessor(StageProcessor):
    """Stage 3: Translate chapter headings (use TOC, NO footnotes)"""

    def process(self, data: Dict[str, Any], filename: str) -> Dict[str, Any]:
        """Translate chapter headings using TOC translations"""
        start_time = datetime.now()
        logger.info(f"Stage 3: Translating chapter headings for {filename}...")

        # Get TOC translations to use for headings (ensure consistency)
        toc = data.get('structure', {}).get('front_matter', {}).get('toc', [])
        toc_map = {}
        for entry in toc:
            if isinstance(entry, dict):
                chapter_num = entry.get('chapter_number')
                full_title_en = entry.get('full_title_english', '')
                if chapter_num and full_title_en:
                    toc_map[chapter_num] = full_title_en

        chapters = data.get('structure', {}).get('body', {}).get('chapters', [])
        items_processed = 0
        errors = []

        # Translate chapter headings (match TOC if possible)
        for chapter in chapters:
            chapter_num = chapter.get('chapter_number')
            title_chinese = chapter.get('title', '')

            # Skip if already translated
            if chapter.get('title_english'):
                items_processed += 1
                continue

            # Try to use TOC translation first
            if chapter_num in toc_map:
                chapter['title_english'] = toc_map[chapter_num]
                items_processed += 1
                logger.debug(f"  ✓ Chapter {chapter_num}: Used TOC translation")
            elif title_chinese:
                # Fall back to translating directly
                try:
                    translator = TranslationService(
                        model=self.config.model,
                        temperature=self.config.temperature
                    )
                    response = translator.translate_from_dict({
                        "content_text_id": chapter_num or 0,
                        "content_source_text": title_chinese
                    })
                    translated_content = response.get('translated_annotated_content', {})
                    chapter['title_english'] = translated_content.get('annotated_content_text', '')
                    items_processed += 1
                    logger.debug(f"  ✓ Chapter {chapter_num}: {title_chinese} → {chapter['title_english']}")
                except Exception as e:
                    error_msg = f"Failed to translate chapter {chapter_num} heading: {e}"
                    logger.warning(f"  ✗ {error_msg}")
                    errors.append(error_msg)

        logger.info(f"  Translated {items_processed}/{len(chapters)} chapter headings")

        end_time = datetime.now()
        stage_log = self.create_stage_log(
            PipelineStage.HEADINGS,
            start_time,
            end_time,
            items_processed,
            success=len(errors) == 0,
            errors=errors
        )

        self.wip_manager.save_wip(data, filename, PipelineStage.HEADINGS, stage_log)
        return data


class BodyTranslationProcessor(StageProcessor):
    """Stage 4: Translate body content (WITH cultural/historical footnotes)"""

    def process(self, data: Dict[str, Any], filename: str) -> Dict[str, Any]:
        """Translate body content with footnotes"""
        start_time = datetime.now()
        logger.info(f"Stage 4: Translating body content for {filename}...")

        # Use BookTranslator for comprehensive translation WITH footnotes
        from processors.translation_config import TranslationConfig

        # Create config for book translator
        trans_config = TranslationConfig(
            model=self.config.model,
            temperature=self.config.temperature,
            max_retries=self.config.max_retries,
            timeout=self.config.timeout,
            max_concurrent_chapters=self.config.max_concurrent_chapters,
            rate_limit_delay=self.config.rate_limit_delay,
            skip_completed=self.config.skip_completed,
            dry_run=self.config.dry_run
        )

        # Initialize book translator
        book_translator = BookTranslator(trans_config)

        # Extract work metadata
        meta = data.get('meta', {})
        work_number = meta.get('work_number', 'UNKNOWN')
        volume = meta.get('volume')

        # Process book through BookTranslator
        # Note: This will translate all content_blocks with cultural/historical footnotes
        try:
            # Save current data to temp file for BookTranslator
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as tmp_input:
                json.dump(data, tmp_input, ensure_ascii=False, indent=2)
                tmp_input_path = Path(tmp_input.name)

            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as tmp_output:
                tmp_output_path = Path(tmp_output.name)

            # Translate book
            report = book_translator.translate_book(
                input_path=tmp_input_path,
                output_path=tmp_output_path,
                work_number=work_number,
                volume=volume
            )

            # Load translated data
            if tmp_output_path.exists():
                with open(tmp_output_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

            # Clean up temp files
            tmp_input_path.unlink(missing_ok=True)
            tmp_output_path.unlink(missing_ok=True)

            chapters = data.get('structure', {}).get('body', {}).get('chapters', [])
            total_blocks = sum(len(ch.get('content_blocks', [])) for ch in chapters)
            items_processed = report.get('total_blocks_translated', total_blocks)
            errors = report.get('errors', [])

            logger.info(f"  Translated {items_processed}/{total_blocks} content blocks")
            logger.info(f"  Total tokens used: {report.get('total_tokens_used', 0)}")

        except Exception as e:
            error_msg = f"Body translation failed: {e}"
            logger.error(f"  ✗ {error_msg}")
            errors = [error_msg]
            items_processed = 0

        end_time = datetime.now()
        stage_log = self.create_stage_log(
            PipelineStage.BODY,
            start_time,
            end_time,
            items_processed,
            success=len(errors) == 0 if 'errors' in locals() else False,
            errors=errors if 'errors' in locals() else []
        )

        self.wip_manager.save_wip(data, filename, PipelineStage.BODY, stage_log)
        return data


class SpecialSectionsProcessor(StageProcessor):
    """Stage 5: Translate special sections (WITH footnotes)"""

    def process(self, data: Dict[str, Any], filename: str) -> Dict[str, Any]:
        """Translate special sections (preface, afterword, etc.)"""
        start_time = datetime.now()
        logger.info(f"Stage 5: Translating special sections for {filename}...")

        # Use TranslationService for special sections WITH footnotes
        translator = TranslationService(
            model=self.config.model,
            temperature=self.config.temperature
        )

        front_matter = data.get('structure', {}).get('front_matter', {})
        back_matter = data.get('structure', {}).get('back_matter', {})
        items_processed = 0
        errors = []

        # Translate front matter sections (excluding TOC which is already done)
        for key, value in front_matter.items():
            if key == 'toc':  # Skip TOC (already translated)
                continue

            if isinstance(value, str) and value and not value.startswith('translated:'):
                try:
                    response = translator.translate_from_dict({
                        "content_text_id": f"front_{key}",
                        "content_source_text": value
                    })
                    translated_content = response.get('translated_annotated_content', {})
                    front_matter[key] = f"translated:{translated_content.get('annotated_content_text', '')}"
                    items_processed += 1
                    logger.debug(f"  ✓ Front matter: {key}")
                except Exception as e:
                    error_msg = f"Failed to translate front matter {key}: {e}"
                    logger.warning(f"  ✗ {error_msg}")
                    errors.append(error_msg)

        # Translate back matter sections
        for key, value in back_matter.items():
            if isinstance(value, str) and value and not value.startswith('translated:'):
                try:
                    response = translator.translate_from_dict({
                        "content_text_id": f"back_{key}",
                        "content_source_text": value
                    })
                    translated_content = response.get('translated_annotated_content', {})
                    back_matter[key] = f"translated:{translated_content.get('annotated_content_text', '')}"
                    items_processed += 1
                    logger.debug(f"  ✓ Back matter: {key}")
                except Exception as e:
                    error_msg = f"Failed to translate back matter {key}: {e}"
                    logger.warning(f"  ✗ {error_msg}")
                    errors.append(error_msg)

        logger.info(f"  Translated {items_processed} special sections")

        end_time = datetime.now()
        stage_log = self.create_stage_log(
            PipelineStage.SPECIAL,
            start_time,
            end_time,
            items_processed,
            success=len(errors) == 0,
            errors=errors
        )

        self.wip_manager.save_wip(data, filename, PipelineStage.SPECIAL, stage_log)
        return data


class CharacterFootnoteCleanupProcessor(StageProcessor):
    """Stage 6: Remove redundant character name footnotes

    NOTE: This processes the ENTIRE WORK to ensure:
    1. Consistent footnote numbering across all chapters
    2. Work-wide deduplication (first occurrence only)

    Future cleanup stages (6b, 6c, etc.) may be added for other footnote types.
    """

    def process(self, data: Dict[str, Any], filename: str) -> Dict[str, Any]:
        """Clean up redundant character footnotes (work-level processing)"""
        start_time = datetime.now()

        # Check if character footnote cleanup is disabled
        if not self.config.enable_footnote_cleanup:
            logger.info(f"Stage 6: Character footnote cleanup SKIPPED (disabled by user)")
            end_time = datetime.now()
            stage_log = self.create_stage_log(
                PipelineStage.CLEANUP,
                start_time,
                end_time,
                0,
                success=True,
                errors=[],
                metadata={"skipped": True, "reason": "Disabled by --skip-character-footnote-cleanup flag"}
            )
            self.wip_manager.save_wip(data, filename, PipelineStage.CLEANUP, stage_log)
            return data

        logger.info(f"Stage 6: Cleaning up character footnotes for {filename} (work-level processing)...")

        # Use CharacterFootnoteCleanup to remove redundant character footnotes
        # Preserves cultural/historical footnotes
        from utils.cleanup_character_footnotes import CleanupConfig

        cleanup_config = CleanupConfig(
            model=self.config.model,
            temperature=0.1,  # Low temperature for consistent classification
            batch_size=self.config.footnote_batch_size,
            preserve_historical=self.config.preserve_historical,
            preserve_legendary=self.config.preserve_legendary,
            preserve_cultural=self.config.preserve_cultural,
            dry_run=self.config.dry_run
        )

        footnote_processor = CharacterFootnoteCleanup(cleanup_config)

        errors = []
        items_processed = 0

        try:
            # Save current data to temp file for cleanup processor
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as tmp_file:
                json.dump(data, tmp_file, ensure_ascii=False, indent=2)
                tmp_path = Path(tmp_file.name)

            # Process footnote cleanup (in-place: input and output are same file)
            cleanup_result = footnote_processor.process_file(
                input_path=tmp_path,
                output_path=tmp_path,
                dry_run=False
            )

            # Load cleaned data
            with open(tmp_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Clean up temp file
            tmp_path.unlink(missing_ok=True)

            items_processed = cleanup_result.removed_count
            logger.info(f"  Removed {cleanup_result.removed_count} redundant character footnotes")
            logger.info(f"  Preserved {cleanup_result.preserved_count} cultural/historical footnotes")

        except Exception as e:
            error_msg = f"Footnote cleanup failed: {e}"
            logger.error(f"  ✗ {error_msg}")
            errors.append(error_msg)

        end_time = datetime.now()
        stage_log = self.create_stage_log(
            PipelineStage.CLEANUP,
            start_time,
            end_time,
            items_processed,
            success=len(errors) == 0,
            errors=errors
        )

        self.wip_manager.save_wip(data, filename, PipelineStage.CLEANUP, stage_log)
        return data


class ValidationProcessor(StageProcessor):
    """Stage 7: Validate translation completeness"""

    def process(self, data: Dict[str, Any], filename: str) -> Dict[str, Any]:
        """Validate translation quality and completeness"""
        start_time = datetime.now()
        logger.info(f"Stage 7: Validating translation for {filename}...")

        # Use StructureValidator for comprehensive validation
        validator = StructureValidator(
            model=self.config.model,
            temperature=0.3
        )

        errors = []
        warnings = []
        validation_checks = 0

        try:
            # Run structure validation
            validation_result = validator.validate(data)

            validation_checks += 1

            # Check validation results
            for issue in validation_result.issues:
                if issue.severity == "error":
                    errors.append(issue.message)
                elif issue.severity == "warning":
                    warnings.append(issue.message)

            # Additional custom validation checks
            # 1. Check metadata translation
            meta = data.get('meta', {})
            if not meta.get('title_english'):
                warnings.append("Title not translated")
            if not meta.get('author_english'):
                warnings.append("Author not translated")
            validation_checks += 1

            # 2. Check TOC translation
            toc = data.get('structure', {}).get('front_matter', {}).get('toc', [])
            untranslated_toc = sum(1 for entry in toc if isinstance(entry, dict) and not entry.get('full_title_english'))
            if untranslated_toc > 0:
                warnings.append(f"{untranslated_toc} TOC entries not translated")
            validation_checks += 1

            # 3. Check chapter translation
            chapters = data.get('structure', {}).get('body', {}).get('chapters', [])
            for i, chapter in enumerate(chapters):
                if not chapter.get('title_english'):
                    warnings.append(f"Chapter {i+1} title not translated")

                # Check content blocks
                content_blocks = chapter.get('content_blocks', [])
                for j, block in enumerate(content_blocks):
                    if 'translated_content' not in block and 'english_text' not in block:
                        errors.append(f"Chapter {i+1}, Block {j+1} not translated")
            validation_checks += 1

            # Log validation summary
            logger.info(f"  Validation checks: {validation_checks}")
            logger.info(f"  Structure quality: {validation_result.structure_quality:.1f}/100")
            logger.info(f"  TOC coverage: {validation_result.toc_coverage:.1f}%")
            if warnings:
                logger.info(f"  Warnings: {len(warnings)}")
                for warning in warnings[:5]:  # Show first 5
                    logger.info(f"    - {warning}")
            if errors:
                logger.error(f"  Errors: {len(errors)}")
                for error in errors[:5]:  # Show first 5
                    logger.error(f"    - {error}")

        except Exception as e:
            error_msg = f"Validation failed: {e}"
            logger.error(f"  ✗ {error_msg}")
            errors.append(error_msg)

        end_time = datetime.now()
        stage_log = self.create_stage_log(
            PipelineStage.VALIDATION,
            start_time,
            end_time,
            validation_checks,
            success=len(errors) == 0,
            errors=errors
        )

        # Add warnings to stage log
        stage_log['warnings'] = warnings

        self.wip_manager.save_wip(data, filename, PipelineStage.VALIDATION, stage_log)
        return data


# =============================================================================
# ORCHESTRATOR
# =============================================================================

class TranslationPipelineOrchestrator:
    """
    Orchestrates the complete translation pipeline.

    Coordinates:
    1. wuxia-translator-annotator (5 translation stages)
    2. footnote-cleanup-optimizer (redundant footnote removal)
    3. progress-manager (status tracking)
    4. translation-ui-manager (preview and review)
    """

    def __init__(self, config: OrchestrationConfig):
        """
        Initialize orchestrator.

        Args:
            config: Orchestration configuration
        """
        self.config = config
        self.wip_manager = WIPManager(config)

        # Initialize stage processors
        self.processors = {
            PipelineStage.METADATA: MetadataTranslationProcessor(config, self.wip_manager),
            PipelineStage.TOC: TOCTranslationProcessor(config, self.wip_manager),
            PipelineStage.HEADINGS: HeadingTranslationProcessor(config, self.wip_manager),
            PipelineStage.BODY: BodyTranslationProcessor(config, self.wip_manager),
            PipelineStage.SPECIAL: SpecialSectionsProcessor(config, self.wip_manager),
            PipelineStage.CLEANUP: CharacterFootnoteCleanupProcessor(config, self.wip_manager),
            PipelineStage.VALIDATION: ValidationProcessor(config, self.wip_manager),
        }

    def process_file(
        self,
        input_path: Path,
        filename: str,
        resume: bool = False
    ) -> Dict[str, Any]:
        """
        Process a single file through the pipeline.

        Args:
            input_path: Path to input JSON file
            filename: Base filename (without extension)
            resume: Whether to resume from last completed stage

        Returns:
            Processing report
        """
        start_time = datetime.now()
        logger.info(f"\n{'='*60}")
        logger.info(f"PROCESSING: {filename}")
        logger.info(f"{'='*60}\n")

        # Load input
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Determine starting stage
        if resume:
            completed = self.wip_manager.get_completed_stages(filename)
            if completed:
                last_completed = max(completed, key=lambda s: s.num)
                start_stage_num = min(last_completed.num + 1, 7)
                logger.info(f"Resuming from stage {start_stage_num} (last completed: {last_completed.stage_name})")
            else:
                start_stage_num = self.config.start_stage
        else:
            start_stage_num = self.config.start_stage

        # Process each stage
        errors = []
        for stage in PipelineStage:
            if stage.num < start_stage_num or stage.num > self.config.end_stage:
                continue

            try:
                logger.info(f"\n--- Stage {stage.num}: {stage.stage_name.upper()} ---")
                logger.info(f"Description: {stage.description}\n")

                processor = self.processors[stage]
                data = processor.process(data, filename)

            except Exception as e:
                error_msg = f"Stage {stage.num} ({stage.stage_name}) failed: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

                if not self.config.dry_run:
                    # Save error log
                    error_log = {
                        "stage_number": stage.num,
                        "stage_name": stage.stage_name,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    }
                    error_path = self.config.log_dir / f"{filename}_stage_{stage.num}_error.json"
                    with open(error_path, 'w', encoding='utf-8') as f:
                        json.dump(error_log, f, ensure_ascii=False, indent=2)

                # Continue to next stage or stop based on severity
                # For now, we stop on any error
                break

        # Save final output
        if not errors and not self.config.dry_run:
            output_path = self.config.output_dir / f"{filename}.json"
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"\n✓ Final output saved: {output_path}")

        # Generate report
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        report = {
            "filename": filename,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "success": len(errors) == 0,
            "stages_completed": start_stage_num,
            "errors": errors
        }

        return report

    def process_work(
        self,
        work_number: str,
        specific_volume: Optional[str] = None,
        resume: bool = False
    ) -> Dict[str, Any]:
        """
        Process all volumes of a work.

        Args:
            work_number: Work number (e.g., "D55")
            specific_volume: Optional specific volume
            resume: Whether to resume from checkpoints

        Returns:
            Work processing report
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"ORCHESTRATOR: {work_number}")
        logger.info(f"{'='*60}\n")

        # Use VolumeManager to discover volumes
        volume_manager = VolumeManager(
            catalog_path=self.config.catalog_path,
            source_dir=self.config.source_dir,
            output_dir=self.config.output_dir
        )

        # Get all volumes for the work
        all_volumes = volume_manager.get_volumes_for_work(work_number)

        if not all_volumes:
            error_msg = f"No volumes found for work {work_number}"
            logger.error(error_msg)
            return {
                "work_number": work_number,
                "success": False,
                "message": error_msg,
                "volumes_processed": 0,
                "errors": [error_msg]
            }

        # Filter to specific volume if requested
        if specific_volume:
            all_volumes = [v for v in all_volumes if v.volume == specific_volume]
            if not all_volumes:
                error_msg = f"Volume {specific_volume} not found for work {work_number}"
                logger.error(error_msg)
                return {
                    "work_number": work_number,
                    "success": False,
                    "message": error_msg,
                    "volumes_processed": 0,
                    "errors": [error_msg]
                }

        logger.info(f"Found {len(all_volumes)} volume(s) for {work_number}")
        for vol in all_volumes:
            logger.info(f"  - Volume {vol.volume}: {vol.title}")

        # Process each volume
        volume_reports = []
        total_errors = []

        for vol_info in all_volumes:
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing Volume {vol_info.volume}: {vol_info.title}")
            logger.info(f"{'='*60}\n")

            # Check if cleaned JSON exists
            if not vol_info.cleaned_json_path or not vol_info.cleaned_json_path.exists():
                error_msg = f"Cleaned JSON not found for volume {vol_info.volume}"
                logger.error(error_msg)
                total_errors.append(error_msg)
                volume_reports.append({
                    "volume": vol_info.volume,
                    "success": False,
                    "message": error_msg
                })
                continue

            # Generate filename for WIP tracking
            filename = vol_info.cleaned_json_path.stem  # e.g., "cleaned_D55_001"

            # Process file through pipeline
            try:
                report = self.process_file(
                    input_path=vol_info.cleaned_json_path,
                    filename=filename,
                    resume=resume
                )
                volume_reports.append(report)

                if not report.get('success'):
                    total_errors.extend(report.get('errors', []))

            except Exception as e:
                error_msg = f"Failed to process volume {vol_info.volume}: {e}"
                logger.error(error_msg)
                total_errors.append(error_msg)
                volume_reports.append({
                    "volume": vol_info.volume,
                    "success": False,
                    "message": error_msg
                })

        # Generate work summary
        successful_volumes = sum(1 for r in volume_reports if r.get('success'))
        all_successful = successful_volumes == len(all_volumes)

        summary_report = {
            "work_number": work_number,
            "success": all_successful,
            "volumes_processed": len(all_volumes),
            "volumes_successful": successful_volumes,
            "volumes_failed": len(all_volumes) - successful_volumes,
            "volume_reports": volume_reports,
            "errors": total_errors
        }

        # Log summary
        logger.info(f"\n{'='*60}")
        logger.info(f"WORK SUMMARY: {work_number}")
        logger.info(f"{'='*60}")
        logger.info(f"Volumes processed: {len(all_volumes)}")
        logger.info(f"Successful: {successful_volumes}")
        logger.info(f"Failed: {len(all_volumes) - successful_volumes}")
        if total_errors:
            logger.error(f"Errors: {len(total_errors)}")

        return summary_report


# =============================================================================
# CLI
# =============================================================================

def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description='Orchestrate translation pipeline with multiple specialized agents',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Translate single work
  python scripts/orchestrate_translation_pipeline.py D55

  # Translate specific volume
  python scripts/orchestrate_translation_pipeline.py D55 --volume 001

  # Resume from checkpoint
  python scripts/orchestrate_translation_pipeline.py D55 --resume

  # Process specific stages only
  python scripts/orchestrate_translation_pipeline.py D55 --start-stage 3 --end-stage 5

  # Batch translation
  python scripts/orchestrate_translation_pipeline.py --batch --limit 10

  # Dry run (no file writes)
  python scripts/orchestrate_translation_pipeline.py D55 --dry-run
        """
    )

    parser.add_argument(
        'work_number',
        nargs='?',
        help='Work number to translate (e.g., D55, J090908)'
    )

    parser.add_argument(
        '--volume',
        help='Translate specific volume only (e.g., 001, 002)'
    )

    parser.add_argument(
        '--batch',
        action='store_true',
        help='Batch mode (process multiple works)'
    )

    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of works to process (batch mode only)'
    )

    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume from last completed stage'
    )

    parser.add_argument(
        '--start-stage',
        type=int,
        default=1,
        choices=range(1, 8),
        help='Start from this stage (1-7, default: 1)'
    )

    parser.add_argument(
        '--end-stage',
        type=int,
        default=7,
        choices=range(1, 8),
        help='End at this stage (1-7, default: 7)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run mode (no file writes)'
    )

    # Character footnote cleanup options (Stage 6)
    parser.add_argument(
        '--skip-character-footnote-cleanup',
        dest='skip_footnote_cleanup',
        action='store_true',
        help='Skip character footnote cleanup stage (Stage 6)'
    )

    parser.add_argument(
        '--character-footnote-batch-size',
        dest='footnote_batch_size',
        type=int,
        default=25,
        help='Character footnotes per API call for cleanup (default: 25)'
    )

    parser.add_argument(
        '--no-preserve-historical',
        dest='preserve_historical',
        action='store_false',
        default=True,
        help='Remove historical figure footnotes (default: preserve)'
    )

    parser.add_argument(
        '--no-preserve-legendary',
        dest='preserve_legendary',
        action='store_false',
        default=True,
        help='Remove legendary personage footnotes (default: preserve)'
    )

    parser.add_argument(
        '--no-preserve-cultural',
        dest='preserve_cultural',
        action='store_false',
        default=True,
        help='Remove cultural footnotes (default: preserve)'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.batch and not args.work_number:
        parser.error("work_number required unless --batch is specified")

    # Setup logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Initialize configuration
    config = OrchestrationConfig(
        start_stage=args.start_stage,
        end_stage=args.end_stage,
        skip_completed=args.resume,
        dry_run=args.dry_run,
        verbose=args.verbose,
        # Footnote cleanup configuration
        enable_footnote_cleanup=not args.skip_footnote_cleanup,
        footnote_batch_size=args.footnote_batch_size,
        preserve_historical=args.preserve_historical,
        preserve_legendary=args.preserve_legendary,
        preserve_cultural=args.preserve_cultural
    )

    # Initialize orchestrator
    orchestrator = TranslationPipelineOrchestrator(config)

    # Execute
    print(f"\n{'='*60}")
    print("TRANSLATION PIPELINE ORCHESTRATOR")
    print(f"{'='*60}\n")
    print(f"Stages: {args.start_stage} → {args.end_stage}")
    print(f"Model: {config.model}")
    print(f"Output: {config.output_dir}")
    if args.dry_run:
        print("⚠ DRY RUN MODE (no files will be written)")
    print()

    if args.batch:
        print("Batch mode not yet implemented")
        return 1
    else:
        report = orchestrator.process_work(
            work_number=args.work_number,
            specific_volume=args.volume,
            resume=args.resume
        )

        print(f"\n{'='*60}")
        print("ORCHESTRATION SUMMARY")
        print(f"{'='*60}\n")

        if report.get('success'):
            print(f"✓ {report.get('message', 'Processing complete')}")
            return 0
        else:
            print(f"✗ {report.get('message', 'Processing failed')}")
            return 1


if __name__ == "__main__":
    sys.exit(main())
