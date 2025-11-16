#!/usr/bin/env python3
"""
Path Management Utilities

Centralized path generation and file discovery for the translation pipeline.
Provides a single source of truth for all path conventions and directory structures.
"""

from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class PathConfig:
    """
    Configuration for all paths in the translation pipeline.

    This replaces scattered path logic throughout the codebase with
    a centralized configuration that can be easily validated and tested.
    """
    source_dir: Path
    output_dir: Path
    catalog_path: Path
    log_dir: Path
    glossary_db_path: Optional[Path] = None

    def __post_init__(self):
        """Ensure all paths are Path objects"""
        self.source_dir = Path(self.source_dir)
        self.output_dir = Path(self.output_dir)
        self.catalog_path = Path(self.catalog_path)
        self.log_dir = Path(self.log_dir)
        if self.glossary_db_path:
            self.glossary_db_path = Path(self.glossary_db_path)

    def validate(self) -> bool:
        """
        Validate that required paths exist.

        Returns:
            True if all required paths exist

        Raises:
            FileNotFoundError: If required paths don't exist
        """
        errors = []

        if not self.source_dir.exists():
            errors.append(f"Source directory not found: {self.source_dir}")

        if not self.catalog_path.exists():
            errors.append(f"Catalog database not found: {self.catalog_path}")

        if self.glossary_db_path and not self.glossary_db_path.exists():
            errors.append(f"Glossary database not found: {self.glossary_db_path}")

        if errors:
            raise FileNotFoundError("\n".join(errors))

        return True

    def create_output_dirs(self):
        """Create output and log directories if they don't exist"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created output directories: {self.output_dir}, {self.log_dir}")


class PathManager:
    """
    Centralized path management for translation pipeline.

    Provides methods for:
    - Generating standardized file paths
    - Discovering source files
    - Creating work-specific directories
    - Managing checkpoints and logs

    Example:
        >>> config = PathConfig(
        ...     source_dir=Path("/data/cleaned"),
        ...     output_dir=Path("/data/translated"),
        ...     catalog_path=Path("/data/catalog.db"),
        ...     log_dir=Path("/logs")
        ... )
        >>> manager = PathManager(config)
        >>> output_path = manager.get_output_path("D55", "001")
        >>> print(output_path)
        /data/translated/D55/translated_D55_001.json
    """

    def __init__(self, config: PathConfig):
        """
        Initialize path manager.

        Args:
            config: PathConfig with all required paths
        """
        self.config = config
        logger.debug(f"PathManager initialized with source={config.source_dir}, output={config.output_dir}")

    # ==================== Output Paths ====================

    def get_output_path(
        self,
        work_number: str,
        volume: Optional[str] = None,
        filename: Optional[str] = None,
        create_dir: bool = True
    ) -> Path:
        """
        Generate standardized output path for translated files.

        Args:
            work_number: Work number (e.g., "D55")
            volume: Volume number (e.g., "001")
            filename: Optional custom filename
            create_dir: Whether to create work directory

        Returns:
            Full output path

        Example:
            >>> manager.get_output_path("D55", "001", "射鵰英雄傳一_金庸.json")
            Path('/output/translated/D55/translated_D55_001_射鵰英雄傳一_金庸.json')
        """
        # Create work-specific directory
        work_dir = self.config.output_dir / work_number
        if create_dir:
            work_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename if not provided
        if filename is None:
            if volume:
                filename = f"translated_{work_number}_{volume}.json"
            else:
                filename = f"translated_{work_number}.json"
        elif not filename.startswith("translated_"):
            # Add prefix if not present
            filename = f"translated_{filename}"

        return work_dir / filename

    def get_work_dir(self, work_number: str, create: bool = True) -> Path:
        """
        Get work-specific output directory.

        Args:
            work_number: Work number
            create: Whether to create directory if it doesn't exist

        Returns:
            Path to work directory
        """
        work_dir = self.config.output_dir / work_number
        if create:
            work_dir.mkdir(parents=True, exist_ok=True)
        return work_dir

    # ==================== Checkpoint Paths ====================

    def get_checkpoint_path(
        self,
        work_number: str,
        volume: Optional[str] = None
    ) -> Path:
        """
        Get path for checkpoint file (resume progress).

        Args:
            work_number: Work number
            volume: Volume number

        Returns:
            Path to checkpoint file
        """
        checkpoint_dir = self.config.log_dir / "checkpoints"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        if volume:
            return checkpoint_dir / f"{work_number}_{volume}_checkpoint.json"
        return checkpoint_dir / f"{work_number}_checkpoint.json"

    # ==================== Log Paths ====================

    def get_log_path(
        self,
        work_number: str,
        volume: Optional[str] = None,
        log_type: str = "translation"
    ) -> Path:
        """
        Get path for log file.

        Args:
            work_number: Work number
            volume: Volume number
            log_type: Type of log (translation, validation, error)

        Returns:
            Path to log file
        """
        self.config.log_dir.mkdir(parents=True, exist_ok=True)

        if volume:
            return self.config.log_dir / f"{work_number}_{volume}_{log_type}.log"
        return self.config.log_dir / f"{work_number}_{log_type}.log"

    # ==================== Source File Discovery ====================

    def find_cleaned_json(
        self,
        directory_name: str,
        work_number: str,
        volume: Optional[str] = None
    ) -> Optional[Path]:
        """
        Find cleaned JSON file for a volume.

        Args:
            directory_name: Directory like "wuxia_0001"
            work_number: Work number like "D55"
            volume: Volume letter like "a", "b", "c" (optional)

        Returns:
            Path to cleaned JSON file or None

        Example:
            >>> manager.find_cleaned_json("wuxia_0001", "D55", "a")
            Path('/data/cleaned/wuxia_0001/cleaned_D55a_射鵰英雄傳一_金庸.json')
        """
        # Check if directory exists
        dir_path = self.config.source_dir / directory_name
        if not dir_path.exists():
            logger.warning(f"Directory not found: {dir_path}")
            return None

        # Build search pattern
        pattern = f"cleaned_{work_number}"
        if volume:
            pattern += volume  # e.g., cleaned_D55a_*.json

        # Find matching files
        json_files = list(dir_path.glob(f"{pattern}*.json"))

        if not json_files:
            logger.warning(f"No cleaned JSON files found matching: {pattern}*.json in {dir_path}")
            return None

        if len(json_files) > 1:
            logger.warning(f"Multiple JSON files found for {pattern}, using first: {json_files[0]}")

        return json_files[0]

    def find_work_files(
        self,
        work_number: str,
        directory_pattern: Optional[str] = None
    ) -> List[Path]:
        """
        Find all cleaned JSON files for a work across directories.

        Args:
            work_number: Work number
            directory_pattern: Optional directory pattern (e.g., "wuxia_*")

        Returns:
            List of paths to cleaned JSON files
        """
        if directory_pattern is None:
            directory_pattern = "*"

        pattern = f"cleaned_{work_number}*.json"
        found_files = []

        # Search in matching directories
        for dir_path in self.config.source_dir.glob(directory_pattern):
            if dir_path.is_dir():
                found_files.extend(dir_path.glob(pattern))

        logger.debug(f"Found {len(found_files)} files for {work_number}")
        return sorted(found_files)

    # ==================== Path Validation ====================

    def validate_source_file(self, file_path: Path) -> bool:
        """
        Validate that source file exists and is readable.

        Args:
            file_path: Path to source file

        Returns:
            True if file is valid

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is not a JSON file
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Source file not found: {file_path}")

        if file_path.suffix != '.json':
            raise ValueError(f"File is not a JSON file: {file_path}")

        return True

    # ==================== Utility Methods ====================

    @staticmethod
    def convert_volume_letter_to_numeric(volume: str) -> str:
        """
        Convert volume letter to numeric format.

        Args:
            volume: Volume letter (a, b, c, ...)

        Returns:
            Numeric volume (001, 002, 003, ...)

        Example:
            >>> PathManager.convert_volume_letter_to_numeric("a")
            "001"
            >>> PathManager.convert_volume_letter_to_numeric("b")
            "002"
        """
        if not volume:
            return "001"

        if volume.isdigit():
            # Already numeric
            return volume.zfill(3)

        # Convert letter to number (a=1, b=2, ...)
        if len(volume) == 1 and volume.isalpha():
            num = ord(volume.lower()) - ord('a') + 1
            return str(num).zfill(3)

        # Unknown format, return as-is
        return volume

    @staticmethod
    def extract_work_info_from_filename(filename: str) -> dict:
        """
        Extract work number and volume from filename.

        Args:
            filename: Filename like "cleaned_D55a_射鵰英雄傳一_金庸.json"

        Returns:
            Dict with work_number, volume, and full_title

        Example:
            >>> PathManager.extract_work_info_from_filename("cleaned_D55a_射鵰英雄傳一_金庸.json")
            {'work_number': 'D55', 'volume': 'a', 'full_title': '射鵰英雄傳一_金庸'}
        """
        import re

        # Pattern: cleaned_{work_number}{optional_volume}_{title}.json
        # Examples: cleaned_D55a_title.json, cleaned_I0929_title.json
        pattern = r'cleaned_([A-Z]\d+)([a-z])?_(.+)\.json'
        match = re.match(pattern, filename)

        if match:
            work_number = match.group(1)
            volume = match.group(2) or None
            title = match.group(3)

            return {
                'work_number': work_number,
                'volume': volume,
                'full_title': title
            }

        return {}


def create_path_manager_from_env() -> PathManager:
    """
    Create PathManager from environment configuration.

    This is a convenience function that loads paths from EnvironmentConfig
    and creates a PathManager instance.

    Returns:
        Configured PathManager instance

    Example:
        >>> manager = create_path_manager_from_env()
        >>> output_path = manager.get_output_path("D55", "001")
    """
    try:
        from utils.environment_config import get_or_create_env_config
        env_config = get_or_create_env_config()

        path_config = PathConfig(
            source_dir=env_config.source_dir,
            output_dir=env_config.output_dir,
            catalog_path=env_config.catalog_path,
            log_dir=env_config.log_dir,
            glossary_db_path=env_config.glossary_db_path
        )

        # Create output directories
        path_config.create_output_dirs()

        return PathManager(path_config)

    except ImportError:
        logger.warning("EnvironmentConfig not available, cannot create PathManager from environment")
        raise


if __name__ == "__main__":
    # Test path manager
    import sys

    print("PathManager Test Suite")
    print("=" * 60)

    # Test 1: Create from hardcoded config
    print("\n1. Creating PathConfig with test paths...")
    config = PathConfig(
        source_dir=Path("/tmp/test_source"),
        output_dir=Path("/tmp/test_output"),
        catalog_path=Path("/tmp/test_catalog.db"),
        log_dir=Path("/tmp/test_logs")
    )
    print(f"   ✓ Source: {config.source_dir}")
    print(f"   ✓ Output: {config.output_dir}")
    print(f"   ✓ Catalog: {config.catalog_path}")
    print(f"   ✓ Logs: {config.log_dir}")

    # Test 2: Create PathManager
    print("\n2. Creating PathManager...")
    manager = PathManager(config)
    print("   ✓ PathManager initialized")

    # Test 3: Path generation
    print("\n3. Testing path generation...")
    output_path = manager.get_output_path("D55", "001", create_dir=False)
    print(f"   Output path: {output_path}")

    checkpoint_path = manager.get_checkpoint_path("D55", "001")
    print(f"   Checkpoint: {checkpoint_path}")

    log_path = manager.get_log_path("D55", "001", "translation")
    print(f"   Log path: {log_path}")

    # Test 4: Volume conversion
    print("\n4. Testing volume letter to numeric conversion...")
    for letter in ['a', 'b', 'c', 'z']:
        numeric = PathManager.convert_volume_letter_to_numeric(letter)
        print(f"   {letter} → {numeric}")

    # Test 5: Filename parsing
    print("\n5. Testing filename parsing...")
    test_files = [
        "cleaned_D55a_射鵰英雄傳一_金庸.json",
        "cleaned_I0929_羅剎夫人_朱貞木.json",
        "cleaned_D27b_天龍八部二_金庸.json"
    ]

    for filename in test_files:
        info = PathManager.extract_work_info_from_filename(filename)
        print(f"   {filename}")
        print(f"     → Work: {info.get('work_number')}, Volume: {info.get('volume')}")

    # Test 6: Try loading from environment (if available)
    print("\n6. Testing environment-based creation...")
    try:
        env_manager = create_path_manager_from_env()
        print("   ✓ Created PathManager from environment config")
        print(f"     Source: {env_manager.config.source_dir}")
        print(f"     Output: {env_manager.config.output_dir}")
    except (ImportError, FileNotFoundError) as e:
        print(f"   ✗ Could not create from environment: {e}")

    print("\n" + "=" * 60)
    print("PathManager test complete!")
