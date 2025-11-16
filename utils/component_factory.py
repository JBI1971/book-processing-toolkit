#!/usr/bin/env python3
"""
Component Factory for Dependency Injection

Provides centralized creation and configuration of system components.
Enables:
- Loose coupling through interface-based design
- Easy swapping of implementations
- Simplified testing with mock objects
- Centralized configuration
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from processors.interfaces import (
    TranslatorInterface,
    BookTranslatorInterface,
    GlossaryInterface,
    CatalogInterface
)

logger = logging.getLogger(__name__)


# =============================================================================
# FACTORY CLASS
# =============================================================================

class ComponentFactory:
    """
    Factory for creating system components with dependency injection.

    Usage:
        factory = ComponentFactory()
        translator = factory.create_translator(model="gpt-4o-mini")
        glossary = factory.create_glossary(db_path="./wuxia_glossary.db")
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize component factory.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self._instances = {}  # Singleton cache

    # =========================================================================
    # TRANSLATOR COMPONENTS
    # =========================================================================

    def create_translator(
        self,
        model: str = "gpt-4o-mini",
        temperature: float = 0.3,
        max_retries: int = 3,
        timeout: float = 120.0,
        implementation: str = "openai"
    ) -> TranslatorInterface:
        """
        Create a translator service instance.

        Args:
            model: Model name (e.g., "gpt-4o-mini")
            temperature: Model temperature (0.0-1.0)
            max_retries: Maximum retry attempts
            timeout: Request timeout in seconds
            implementation: Implementation to use ("openai", "anthropic", etc.)

        Returns:
            TranslatorInterface implementation
        """
        if implementation == "openai":
            from processors.translator import TranslationService
            return TranslationService(
                model=model,
                temperature=temperature,
                max_retries=max_retries,
                timeout=timeout
            )
        elif implementation == "mock":
            return MockTranslator()
        else:
            raise ValueError(f"Unknown translator implementation: {implementation}")

    def create_book_translator(
        self,
        config: Optional[Any] = None,
        translator: Optional[TranslatorInterface] = None
    ) -> BookTranslatorInterface:
        """
        Create a book translator instance.

        Args:
            config: Translation configuration object
            translator: Optional translator service (will create default if None)

        Returns:
            BookTranslatorInterface implementation
        """
        from processors.book_translator import BookTranslator
        from processors.translation_config import TranslationConfig

        if config is None:
            config = TranslationConfig()

        return BookTranslator(config=config)

    # =========================================================================
    # GLOSSARY COMPONENTS
    # =========================================================================

    def create_glossary(
        self,
        db_path: Optional[str] = None,
        implementation: str = "sqlite"
    ) -> GlossaryInterface:
        """
        Create a glossary service instance.

        Args:
            db_path: Path to glossary database (or None for default)
            implementation: Implementation to use ("sqlite", "mock", etc.)

        Returns:
            GlossaryInterface implementation
        """
        if implementation == "sqlite":
            from utils.wuxia_glossary import WuxiaGlossary

            if db_path is None:
                # Try to load from environment or use default
                try:
                    from utils.environment_config import get_or_create_env_config
                    env_config = get_or_create_env_config()
                    db_path = str(env_config.glossary_db_path)
                except Exception as e:
                    logger.warning(f"Could not load env config: {e}, using default")
                    db_path = "./wuxia_glossary.db"

            return WuxiaGlossary(db_path)
        elif implementation == "mock":
            return MockGlossary()
        else:
            raise ValueError(f"Unknown glossary implementation: {implementation}")

    def get_or_create_glossary(
        self,
        db_path: Optional[str] = None
    ) -> GlossaryInterface:
        """
        Get or create singleton glossary instance.

        Args:
            db_path: Path to glossary database

        Returns:
            Cached GlossaryInterface instance
        """
        cache_key = f"glossary:{db_path}"
        if cache_key not in self._instances:
            self._instances[cache_key] = self.create_glossary(db_path=db_path)
        return self._instances[cache_key]

    # =========================================================================
    # CATALOG COMPONENTS
    # =========================================================================

    def create_catalog(
        self,
        catalog_path: Optional[str] = None,
        implementation: str = "sqlite"
    ) -> CatalogInterface:
        """
        Create a catalog service instance.

        Args:
            catalog_path: Path to catalog database (or None for default)
            implementation: Implementation to use ("sqlite", "mock", etc.)

        Returns:
            CatalogInterface implementation
        """
        if implementation == "sqlite":
            from utils.catalog_metadata import CatalogMetadataExtractor

            if catalog_path is None:
                # Try to load from environment or use default
                try:
                    from utils.environment_config import get_or_create_env_config
                    env_config = get_or_create_env_config()
                    catalog_path = str(env_config.catalog_path)
                except Exception as e:
                    logger.warning(f"Could not load env config: {e}, using default")
                    catalog_path = "/Users/jacki/project_files/translation_project/wuxia_catalog.db"

            return CatalogAdapter(catalog_path)
        elif implementation == "mock":
            return MockCatalog()
        else:
            raise ValueError(f"Unknown catalog implementation: {implementation}")

    def get_or_create_catalog(
        self,
        catalog_path: Optional[str] = None
    ) -> CatalogInterface:
        """
        Get or create singleton catalog instance.

        Args:
            catalog_path: Path to catalog database

        Returns:
            Cached CatalogInterface instance
        """
        cache_key = f"catalog:{catalog_path}"
        if cache_key not in self._instances:
            self._instances[cache_key] = self.create_catalog(catalog_path=catalog_path)
        return self._instances[cache_key]

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def clear_cache(self):
        """Clear all singleton instances"""
        self._instances.clear()


# =============================================================================
# ADAPTER CLASSES
# =============================================================================

class CatalogAdapter(CatalogInterface):
    """
    Adapter to make CatalogMetadataExtractor conform to CatalogInterface.

    This allows existing code to work with the new interface system.
    """

    def __init__(self, catalog_path: str):
        from utils.catalog_metadata import CatalogMetadataExtractor
        self._extractor = CatalogMetadataExtractor(catalog_path)

    def get_metadata_by_work_number(self, work_number: str):
        # CatalogMetadataExtractor doesn't have this method yet
        # Would need to add it to the original class
        raise NotImplementedError("get_metadata_by_work_number not yet implemented")

    def get_metadata_by_directory(self, directory_name: str):
        return self._extractor.get_metadata_by_directory(directory_name)

    def list_works(self, author=None, multi_volume_only=False):
        # CatalogMetadataExtractor doesn't have this method yet
        # Would need to add it to the original class
        raise NotImplementedError("list_works not yet implemented")


# =============================================================================
# MOCK IMPLEMENTATIONS (FOR TESTING)
# =============================================================================

class MockTranslator(TranslatorInterface):
    """Mock translator for testing"""

    def translate_block(self, request):
        from processors.interfaces import TranslationResult
        return TranslationResult(
            content_id=request.content_id,
            source_text=request.source_text,
            translated_text=f"[MOCK TRANSLATION] {request.source_text}",
            footnotes=[],
            content_type=request.content_type or "narrative",
            tokens_used=10,
            success=True
        )

    def translate_blocks(self, requests):
        return [self.translate_block(req) for req in requests]


class MockGlossary(GlossaryInterface):
    """Mock glossary for testing"""

    def lookup(self, chinese_term: str):
        return None  # No entries in mock

    def find_in_text(self, text: str):
        return []  # No matches in mock

    def generate_footnote(self, entry, occurrence_num=1, brief=False):
        return f"[MOCK FOOTNOTE {occurrence_num}]"


class MockCatalog(CatalogInterface):
    """Mock catalog for testing"""

    def get_metadata_by_work_number(self, work_number: str):
        from processors.interfaces import WorkMetadata
        return WorkMetadata(
            work_number=work_number,
            title_chinese="测试作品",
            title_english="Test Work",
            author_chinese="测试作者",
            author_english="Test Author",
            volume=None
        )

    def get_metadata_by_directory(self, directory_name: str):
        return self.get_metadata_by_work_number("D999")

    def list_works(self, author=None, multi_volume_only=False):
        return [self.get_metadata_by_work_number("D999")]


# =============================================================================
# GLOBAL FACTORY INSTANCE
# =============================================================================

# Singleton factory instance for application-wide use
_default_factory = None


def get_factory() -> ComponentFactory:
    """
    Get the global component factory instance.

    Returns:
        Singleton ComponentFactory
    """
    global _default_factory
    if _default_factory is None:
        _default_factory = ComponentFactory()
    return _default_factory
