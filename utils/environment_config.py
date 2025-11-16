#!/usr/bin/env python3
"""
Environment Configuration Management

Centralizes all environment-specific paths and settings.
Loads from environment variables with sensible defaults.

Usage:
    from utils.environment_config import get_env_config

    config = get_env_config()
    print(config.source_dir)
    print(config.catalog_path)
"""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class EnvironmentConfig:
    """
    Centralized environment configuration.

    All paths default to sensible values but can be overridden via environment variables.
    """
    # Source data paths
    source_dir: Path
    catalog_path: Path
    glossary_db_path: Path

    # Output paths
    output_dir: Path
    log_dir: Path

    # Project root (auto-detected)
    project_root: Path

    def __post_init__(self):
        """Ensure all paths are Path objects"""
        self.source_dir = Path(self.source_dir)
        self.catalog_path = Path(self.catalog_path)
        self.glossary_db_path = Path(self.glossary_db_path)
        self.output_dir = Path(self.output_dir)
        self.log_dir = Path(self.log_dir)
        self.project_root = Path(self.project_root)

    def validate(self) -> list[str]:
        """
        Validate that required paths exist.

        Returns:
            List of validation errors (empty if all valid)
        """
        errors = []

        # Check required source files/dirs
        if not self.catalog_path.exists():
            errors.append(f"Catalog database not found: {self.catalog_path}")

        if not self.glossary_db_path.exists():
            errors.append(f"Glossary database not found: {self.glossary_db_path}")

        if not self.source_dir.exists():
            errors.append(f"Source directory not found: {self.source_dir}")

        return errors

    def create_output_dirs(self):
        """Create output directories if they don't exist"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Output directories created: {self.output_dir}, {self.log_dir}")


def detect_project_root() -> Path:
    """
    Detect project root directory.

    Looks for markers like .git, pyproject.toml, or specific directories.
    Falls back to current working directory.
    """
    current = Path.cwd()

    # Search upwards for project root markers
    for parent in [current] + list(current.parents):
        if (parent / '.git').exists() or (parent / 'pyproject.toml').exists():
            return parent
        if (parent / 'processors').exists() and (parent / 'utils').exists():
            return parent

    # Fallback to current directory
    return current


def get_env_config(
    project_root: Optional[Path] = None,
    load_dotenv: bool = True
) -> EnvironmentConfig:
    """
    Load environment configuration.

    Attempts to load from .env file if python-dotenv is available,
    then falls back to environment variables, then to defaults.

    Args:
        project_root: Optional project root override
        load_dotenv: Whether to attempt loading .env file

    Returns:
        Configured EnvironmentConfig instance
    """
    if project_root is None:
        project_root = detect_project_root()

    # Attempt to load .env file
    if load_dotenv:
        try:
            from dotenv import load_dotenv as load_env_file
            env_path = project_root / '.env'
            if env_path.exists():
                load_env_file(env_path)
                logger.info(f"Loaded environment from {env_path}")
        except ImportError:
            logger.debug("python-dotenv not installed, skipping .env file loading")

    # Load configuration from environment variables with defaults
    config = EnvironmentConfig(
        # Source data paths - default to external project directory
        source_dir=Path(os.getenv(
            'WUXIA_SOURCE_DIR',
            '/Users/jacki/project_files/translation_project/cleaned/COMPLETE_ALL_BOOKS'
        )),
        catalog_path=Path(os.getenv(
            'WUXIA_CATALOG_PATH',
            '/Users/jacki/project_files/translation_project/wuxia_catalog.db'
        )),
        glossary_db_path=Path(os.getenv(
            'WUXIA_GLOSSARY_DB_PATH',
            str(project_root / 'wuxia_glossary.db')
        )),

        # Output paths - default to project-relative
        output_dir=Path(os.getenv(
            'WUXIA_OUTPUT_DIR',
            str(project_root / 'translation_data' / 'outputs')
        )),
        log_dir=Path(os.getenv(
            'WUXIA_LOG_DIR',
            str(project_root / 'translation_data' / 'logs')
        )),

        # Project root
        project_root=project_root
    )

    logger.debug(f"Environment configuration loaded:")
    logger.debug(f"  Project root: {config.project_root}")
    logger.debug(f"  Source dir: {config.source_dir}")
    logger.debug(f"  Output dir: {config.output_dir}")
    logger.debug(f"  Catalog: {config.catalog_path}")
    logger.debug(f"  Glossary DB: {config.glossary_db_path}")

    return config


# Module-level singleton for convenience
_ENV_CONFIG: Optional[EnvironmentConfig] = None


def get_or_create_env_config() -> EnvironmentConfig:
    """
    Get or create singleton environment configuration.

    Use this for consistent configuration across the application.
    """
    global _ENV_CONFIG
    if _ENV_CONFIG is None:
        _ENV_CONFIG = get_env_config()
    return _ENV_CONFIG


def reset_env_config():
    """Reset singleton (useful for testing)"""
    global _ENV_CONFIG
    _ENV_CONFIG = None


if __name__ == "__main__":
    # Test configuration loading
    import sys

    print("=" * 80)
    print("Environment Configuration Test")
    print("=" * 80)

    config = get_env_config()

    print(f"\nProject Root: {config.project_root}")
    print(f"\nSource Paths:")
    print(f"  Source Dir: {config.source_dir}")
    print(f"  Catalog DB: {config.catalog_path}")
    print(f"  Glossary DB: {config.glossary_db_path}")
    print(f"\nOutput Paths:")
    print(f"  Output Dir: {config.output_dir}")
    print(f"  Log Dir: {config.log_dir}")

    # Validate
    print(f"\nValidation:")
    errors = config.validate()
    if errors:
        print("  Errors found:")
        for error in errors:
            print(f"    - {error}")
        sys.exit(1)
    else:
        print("  ✓ All required paths exist")

    # Create output dirs
    config.create_output_dirs()
    print(f"\n✓ Configuration validated successfully")
