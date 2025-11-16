#!/usr/bin/env python3
"""
Translation Pipeline Configuration

Centralizes all configuration for translation and annotation workflows.
Supports rate limiting, retry logic, and output organization.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

# Import environment configuration
try:
    from utils.environment_config import get_or_create_env_config, EnvironmentConfig
    _ENV_CONFIG_AVAILABLE = True
except ImportError:
    _ENV_CONFIG_AVAILABLE = False
    EnvironmentConfig = None

# Import path management
try:
    from utils.path_manager import PathManager, PathConfig, create_path_manager_from_env
    _PATH_MANAGER_AVAILABLE = True
except ImportError:
    _PATH_MANAGER_AVAILABLE = False
    PathManager = None
    PathConfig = None

logger = logging.getLogger(__name__)


@dataclass
class TranslationConfig:
    """Configuration for translation pipeline"""

    # API Configuration
    model: str = "gpt-4.1-nano"
    temperature: float = 0.3
    max_retries: int = 3
    timeout: int = 120

    # Rate Limiting
    rate_limit_delay: float = 1.0  # Seconds between API calls
    batch_size: int = 10  # Blocks per batch
    max_concurrent_chapters: int = 3  # Parallel chapter processing

    # Input/Output (can be overridden, defaults loaded from environment)
    source_dir: Optional[Path] = None
    output_dir: Optional[Path] = None
    catalog_path: Optional[Path] = None
    log_dir: Optional[Path] = None

    # Processing Options
    dry_run: bool = False
    skip_completed: bool = True  # Resume from last completed
    save_checkpoints: bool = True  # Save progress after each chapter
    validate_output: bool = True  # Run validation after translation

    # Translation Features
    include_cultural_notes: bool = True
    include_pronunciation: bool = True
    preserve_original: bool = True  # Keep Chinese text alongside translation
    footnote_style: str = "inline"  # inline|endnote|chicago

    # Quality Control
    min_quality_score: int = 70  # Minimum validation score to accept
    retry_on_low_quality: bool = True

    # Logging
    verbose: bool = False
    save_token_usage: bool = True

    # Internal: PathManager instance (initialized in __post_init__)
    path_manager: Optional['PathManager'] = field(default=None, init=False, repr=False)

    def __post_init__(self):
        """
        Initialize paths from environment if not provided.

        Paths can be explicitly set, or will be loaded from EnvironmentConfig
        (which reads from .env or environment variables).
        """
        # Load environment config if paths not provided
        if _ENV_CONFIG_AVAILABLE and (
            self.source_dir is None or
            self.output_dir is None or
            self.catalog_path is None or
            self.log_dir is None
        ):
            env_config = get_or_create_env_config()

            # Use environment config for any unset paths
            if self.source_dir is None:
                self.source_dir = env_config.source_dir
            if self.output_dir is None:
                self.output_dir = env_config.output_dir
            if self.catalog_path is None:
                self.catalog_path = env_config.catalog_path
            if self.log_dir is None:
                self.log_dir = env_config.log_dir

            logger.debug("Loaded paths from environment configuration")
        else:
            # Fallback to hardcoded defaults if environment config not available
            if self.source_dir is None:
                self.source_dir = Path("/Users/jacki/project_files/translation_project/cleaned/COMPLETE_ALL_BOOKS")
            if self.output_dir is None:
                self.output_dir = Path("/Users/jacki/project_files/translation_project/translated_books")
            if self.catalog_path is None:
                self.catalog_path = Path("/Users/jacki/project_files/translation_project/wuxia_catalog.db")
            if self.log_dir is None:
                self.log_dir = Path("./logs/translation")

            if not _ENV_CONFIG_AVAILABLE:
                logger.warning("EnvironmentConfig not available, using hardcoded defaults")

        # Ensure paths are Path objects
        self.source_dir = Path(self.source_dir)
        self.output_dir = Path(self.output_dir)
        self.catalog_path = Path(self.catalog_path)
        self.log_dir = Path(self.log_dir)

        # Create output directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Initialize PathManager if available
        if _PATH_MANAGER_AVAILABLE:
            path_config = PathConfig(
                source_dir=self.source_dir,
                output_dir=self.output_dir,
                catalog_path=self.catalog_path,
                log_dir=self.log_dir
            )
            self.path_manager = PathManager(path_config)
            logger.debug("PathManager initialized")
        else:
            self.path_manager = None
            logger.debug("PathManager not available, using direct path methods")


@dataclass
class WorkProgress:
    """Track progress for a multi-volume work"""
    work_number: str
    title: str
    author: str
    total_volumes: int
    completed_volumes: List[str] = field(default_factory=list)
    failed_volumes: List[str] = field(default_factory=list)
    current_volume: Optional[str] = None

    @property
    def is_complete(self) -> bool:
        """Check if all volumes are completed"""
        return len(self.completed_volumes) == self.total_volumes

    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage"""
        if self.total_volumes == 0:
            return 0.0
        return (len(self.completed_volumes) / self.total_volumes) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "work_number": self.work_number,
            "title": self.title,
            "author": self.author,
            "total_volumes": self.total_volumes,
            "completed_volumes": self.completed_volumes,
            "failed_volumes": self.failed_volumes,
            "current_volume": self.current_volume,
            "is_complete": self.is_complete,
            "completion_percentage": self.completion_percentage
        }


@dataclass
class ChapterProgress:
    """Track progress for a single chapter"""
    chapter_id: str
    chapter_number: int
    title: str
    total_blocks: int
    completed_blocks: int = 0
    failed_blocks: List[str] = field(default_factory=list)
    token_usage: int = 0

    @property
    def is_complete(self) -> bool:
        return self.completed_blocks == self.total_blocks and len(self.failed_blocks) == 0

    @property
    def completion_percentage(self) -> float:
        if self.total_blocks == 0:
            return 0.0
        return (self.completed_blocks / self.total_blocks) * 100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chapter_id": self.chapter_id,
            "chapter_number": self.chapter_number,
            "title": self.title,
            "total_blocks": self.total_blocks,
            "completed_blocks": self.completed_blocks,
            "failed_blocks": self.failed_blocks,
            "token_usage": self.token_usage,
            "is_complete": self.is_complete,
            "completion_percentage": self.completion_percentage
        }


@dataclass
class TranslationReport:
    """Comprehensive report for translation job"""
    work_number: str
    work_title: str
    volumes_processed: int
    total_chapters: int
    total_blocks: int
    successful_blocks: int
    failed_blocks: int
    total_tokens: int
    start_time: str
    end_time: str
    duration_seconds: float
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.total_blocks == 0:
            return 0.0
        return (self.successful_blocks / self.total_blocks) * 100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "work_number": self.work_number,
            "work_title": self.work_title,
            "volumes_processed": self.volumes_processed,
            "total_chapters": self.total_chapters,
            "total_blocks": self.total_blocks,
            "successful_blocks": self.successful_blocks,
            "failed_blocks": self.failed_blocks,
            "success_rate": self.success_rate,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": self.total_tokens * 0.00015 / 1000,  # GPT-4o-mini pricing
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": self.duration_seconds,
            "duration_formatted": f"{self.duration_seconds / 60:.1f} minutes",
            "errors": self.errors,
            "warnings": self.warnings
        }


def get_output_path(
    config: TranslationConfig,
    work_number: str,
    volume: Optional[str] = None,
    filename: Optional[str] = None
) -> Path:
    """
    Generate standardized output path for translated files.

    Args:
        config: Translation configuration
        work_number: Work number (e.g., "D55")
        volume: Volume number (e.g., "001")
        filename: Optional custom filename

    Returns:
        Full output path

    Example:
        >>> get_output_path(config, "D55", "001", "射鵰英雄傳一_金庸.json")
        Path('/output/translated/D55/translated_D55_001_射鵰英雄傳一_金庸.json')
    """
    # Use PathManager if available
    if config.path_manager:
        return config.path_manager.get_output_path(work_number, volume, filename, create_dir=True)

    # Fallback to original implementation
    # Create work-specific directory
    work_dir = config.output_dir / work_number
    work_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename if not provided
    if filename is None:
        if volume:
            filename = f"translated_{work_number}_{volume}.json"
        else:
            filename = f"translated_{work_number}.json"
    elif not filename.startswith("translated_"):
        filename = f"translated_{filename}"

    return work_dir / filename


def get_checkpoint_path(
    config: TranslationConfig,
    work_number: str,
    volume: Optional[str] = None
) -> Path:
    """
    Get path for checkpoint file (resume progress).

    Args:
        config: Translation configuration
        work_number: Work number
        volume: Volume number

    Returns:
        Path to checkpoint file
    """
    # Use PathManager if available
    if config.path_manager:
        return config.path_manager.get_checkpoint_path(work_number, volume)

    # Fallback to original implementation
    checkpoint_dir = config.log_dir / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    if volume:
        return checkpoint_dir / f"{work_number}_{volume}_checkpoint.json"
    return checkpoint_dir / f"{work_number}_checkpoint.json"


def get_log_path(
    config: TranslationConfig,
    work_number: str,
    volume: Optional[str] = None,
    log_type: str = "translation"
) -> Path:
    """
    Get path for log file.

    Args:
        config: Translation configuration
        work_number: Work number
        volume: Volume number
        log_type: Type of log (translation, validation, error)

    Returns:
        Path to log file
    """
    # Use PathManager if available
    if config.path_manager:
        return config.path_manager.get_log_path(work_number, volume, log_type)

    # Fallback to original implementation
    if volume:
        return config.log_dir / f"{work_number}_{volume}_{log_type}.log"
    return config.log_dir / f"{work_number}_{log_type}.log"


def setup_logging(
    config: TranslationConfig,
    work_number: str,
    volume: Optional[str] = None
) -> logging.Logger:
    """
    Setup logging for translation job.

    Args:
        config: Translation configuration
        work_number: Work number
        volume: Volume number

    Returns:
        Configured logger
    """
    logger_name = f"translation.{work_number}"
    if volume:
        logger_name += f".{volume}"

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG if config.verbose else logging.INFO)

    # Remove existing handlers
    logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler
    log_path = get_log_path(config, work_number, volume)
    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    logger.info(f"Logging initialized for {work_number}" + (f" volume {volume}" if volume else ""))
    logger.info(f"Log file: {log_path}")

    return logger


if __name__ == "__main__":
    # Test configuration
    config = TranslationConfig()
    print("Translation Configuration:")
    print(f"  Model: {config.model}")
    print(f"  Source: {config.source_dir}")
    print(f"  Output: {config.output_dir}")
    print(f"  Catalog: {config.catalog_path}")

    # Test path generation
    output_path = get_output_path(config, "D55", "001", "射鵰英雄傳一_金庸.json")
    print(f"\nOutput path: {output_path}")

    checkpoint_path = get_checkpoint_path(config, "D55", "001")
    print(f"Checkpoint path: {checkpoint_path}")

    log_path = get_log_path(config, "D55", "001")
    print(f"Log path: {log_path}")
