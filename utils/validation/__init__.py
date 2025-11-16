"""
Validation utilities for book processing pipeline.

Provides quality gates and data integrity checks.
"""

from .footnote_integrity_validator import (
    FootnoteIntegrityValidator,
    FootnoteValidationResult,
    FootnoteIssue,
)

__all__ = [
    'FootnoteIntegrityValidator',
    'FootnoteValidationResult',
    'FootnoteIssue',
]
