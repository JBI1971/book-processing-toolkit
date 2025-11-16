#!/usr/bin/env python3
"""
Component Interfaces for Book Processing Toolkit

Defines abstract base classes (interfaces) for core components to enable:
- Loose coupling between components
- Easy mocking for testing
- Swappable implementations (e.g., different translation services)
- Clear contracts for component behavior
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path


# =============================================================================
# TRANSLATION INTERFACES
# =============================================================================

@dataclass
class TranslationRequest:
    """Request for translating a single content block"""
    content_id: str
    source_text: str
    content_type: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


@dataclass
class TranslationResult:
    """Result of translating a single content block"""
    content_id: str
    source_text: str
    translated_text: str
    footnotes: List[Dict[str, Any]]
    content_type: str
    tokens_used: int
    success: bool
    error: Optional[str] = None


class TranslatorInterface(ABC):
    """
    Abstract interface for translation services.

    Implementations must provide:
    - Single block translation with annotations
    - Error handling and retry logic
    - Token tracking
    """

    @abstractmethod
    def translate_block(self, request: TranslationRequest) -> TranslationResult:
        """
        Translate a single content block with cultural annotations.

        Args:
            request: Translation request with source text and metadata

        Returns:
            TranslationResult with translated text, footnotes, and metrics
        """
        pass

    @abstractmethod
    def translate_blocks(self, requests: List[TranslationRequest]) -> List[TranslationResult]:
        """
        Translate multiple content blocks (potentially in parallel).

        Args:
            requests: List of translation requests

        Returns:
            List of translation results
        """
        pass


class BookTranslatorInterface(ABC):
    """
    Abstract interface for book-level translation orchestration.

    Implementations must provide:
    - Chapter-by-chapter processing
    - Progress tracking and checkpointing
    - Concurrent block processing
    - Comprehensive error handling
    """

    @abstractmethod
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
            Translation report dictionary with:
                - status: "success" | "partial" | "failed"
                - chapters_completed: int
                - total_chapters: int
                - tokens_used: int
                - errors: List[str]
                - warnings: List[str]
        """
        pass


# =============================================================================
# GLOSSARY INTERFACES
# =============================================================================

@dataclass
class GlossaryEntry:
    """Entry in a glossary database"""
    chinese: str
    pinyin: str
    translation_strategy: str
    recommended_form: str
    footnote_template: str
    category: str
    rationale: str
    deduplication_strategy: str
    expected_frequency: str
    source: str


class GlossaryInterface(ABC):
    """
    Abstract interface for glossary lookup services.

    Implementations must provide:
    - Term lookup by Chinese text
    - Multi-term matching in text
    - Footnote generation
    """

    @abstractmethod
    def lookup(self, chinese_term: str) -> Optional[GlossaryEntry]:
        """
        Look up a single term in the glossary.

        Args:
            chinese_term: Chinese text to look up

        Returns:
            GlossaryEntry if found, None otherwise
        """
        pass

    @abstractmethod
    def find_in_text(self, text: str) -> List[Tuple[str, GlossaryEntry]]:
        """
        Find all glossary terms in a text string.

        Args:
            text: Chinese text to search

        Returns:
            List of (matched_text, GlossaryEntry) tuples
        """
        pass

    @abstractmethod
    def generate_footnote(
        self,
        entry: GlossaryEntry,
        occurrence_num: int = 1,
        brief: bool = False
    ) -> str:
        """
        Generate footnote text for a glossary entry.

        Args:
            entry: Glossary entry
            occurrence_num: Which occurrence (1, 2, 3...)
            brief: Whether to use brief version

        Returns:
            Formatted footnote text
        """
        pass


# =============================================================================
# CATALOG INTERFACES
# =============================================================================

@dataclass
class WorkMetadata:
    """Metadata for a work from the catalog"""
    work_number: str
    title_chinese: str
    title_english: Optional[str]
    author_chinese: str
    author_english: Optional[str]
    volume: Optional[str]


class CatalogInterface(ABC):
    """
    Abstract interface for catalog metadata services.

    Implementations must provide:
    - Metadata lookup by work number
    - Metadata lookup by directory name
    - Work listing and querying
    """

    @abstractmethod
    def get_metadata_by_work_number(self, work_number: str) -> Optional[WorkMetadata]:
        """
        Get metadata for a work by its work number.

        Args:
            work_number: Work number (e.g., "D55")

        Returns:
            WorkMetadata if found, None otherwise
        """
        pass

    @abstractmethod
    def get_metadata_by_directory(self, directory_name: str) -> Optional[WorkMetadata]:
        """
        Get metadata for a work by its directory name.

        Args:
            directory_name: Directory name (e.g., "wuxia_0117")

        Returns:
            WorkMetadata if found, None otherwise
        """
        pass

    @abstractmethod
    def list_works(
        self,
        author: Optional[str] = None,
        multi_volume_only: bool = False
    ) -> List[WorkMetadata]:
        """
        List all works in the catalog with optional filters.

        Args:
            author: Filter by author (Chinese or English)
            multi_volume_only: Only return multi-volume works

        Returns:
            List of WorkMetadata
        """
        pass


# =============================================================================
# PROCESSOR INTERFACES
# =============================================================================

class ProcessorInterface(ABC):
    """
    Abstract interface for content processors.

    Generic interface for processors that transform book data.
    """

    @abstractmethod
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process book data and return transformed result.

        Args:
            data: Input book data (dictionary)

        Returns:
            Processed book data (dictionary)
        """
        pass

    @abstractmethod
    def process_file(self, input_path: Path, output_path: Path) -> Dict[str, Any]:
        """
        Process a book from file to file.

        Args:
            input_path: Input file path
            output_path: Output file path

        Returns:
            Processing report dictionary
        """
        pass


# =============================================================================
# VALIDATOR INTERFACES
# =============================================================================

@dataclass
class ValidationIssue:
    """Single validation issue"""
    severity: str  # "error" | "warning" | "info"
    issue_type: str
    message: str
    location: Optional[str] = None
    suggested_fix: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of validation check"""
    is_valid: bool
    issues: List[ValidationIssue]
    summary: str
    confidence_score: float


class ValidatorInterface(ABC):
    """
    Abstract interface for validators.

    Validators check data integrity and structure.
    """

    @abstractmethod
    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """
        Validate book data.

        Args:
            data: Book data to validate

        Returns:
            ValidationResult with issues and summary
        """
        pass

    @abstractmethod
    def validate_file(self, file_path: Path) -> ValidationResult:
        """
        Validate a book file.

        Args:
            file_path: Path to book file

        Returns:
            ValidationResult with issues and summary
        """
        pass
