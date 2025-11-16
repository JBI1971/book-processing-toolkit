"""
HTTP Utilities

HTTP client with retry logic and HTML parsing.
"""

from .http import get_text
from .parse import extract_title

__all__ = ['get_text', 'extract_title']
