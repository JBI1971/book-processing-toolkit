#!/usr/bin/env python3
"""
Wuxia Glossary Lookup Utility

Provides fast lookup and matching for wuxia terminology in translations.
Uses SQLite database created by deduplicate_wuxia_glossary.py.

Usage:
    from utils.wuxia_glossary import WuxiaGlossary

    glossary = WuxiaGlossary('wuxia_glossary.db')
    entry = glossary.lookup('內功')
    matches = glossary.find_in_text('他修煉內功多年')
"""

import sqlite3
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class GlossaryEntry:
    """Wuxia glossary term"""
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

    def should_footnote_first_occurrence(self) -> bool:
        """Check if this term should be footnoted on first occurrence"""
        return self.deduplication_strategy == "FIRST_OCCURRENCE_ONLY"

    def should_footnote_recurring(self) -> bool:
        """Check if this term should have brief recurring footnotes"""
        return self.deduplication_strategy == "RECURRING_BRIEF"

    def should_footnote_every_occurrence(self) -> bool:
        """Check if this term should be footnoted every time"""
        return self.deduplication_strategy == "EVERY_OCCURRENCE"

    def is_high_frequency(self) -> bool:
        """Check if this is a high frequency term"""
        return self.expected_frequency in ['VERY_HIGH', 'HIGH']

    def format_inline(self) -> str:
        """
        Format term for inline use in translation.

        Returns pinyin with italics or English based on strategy.
        """
        if self.translation_strategy == "PINYIN_ONLY":
            # Already has asterisks from recommended_form
            return self.recommended_form
        elif self.translation_strategy == "HYBRID":
            return self.recommended_form
        else:
            # ENGLISH_ONLY
            return self.recommended_form

    def generate_footnote(self, occurrence_num: int = 1, brief: bool = False) -> str:
        """
        Generate footnote text based on occurrence and strategy.

        Args:
            occurrence_num: Which occurrence this is (1, 2, 3...)
            brief: Whether to use brief version for recurring

        Returns:
            Formatted footnote text
        """
        if occurrence_num == 1 or not brief:
            # Full footnote
            return self.footnote_template
        else:
            # Brief recurring footnote
            return f"{self.chinese} *{self.pinyin}*"


class WuxiaGlossary:
    """
    Fast lookup and matching for wuxia terminology.

    Thread-safe implementation that loads all data into memory on initialization,
    avoiding SQLite thread-safety issues in parallel translation.

    Provides methods for:
    - Direct term lookup
    - Finding all matches in text
    - Intelligent footnoting based on deduplication strategy
    """

    def __init__(self, db_path: Path = Path('wuxia_glossary.db')):
        """
        Initialize glossary by loading all data from SQLite into memory.

        This ensures thread-safety for parallel translation by avoiding
        SQLite connection sharing across threads.

        Args:
            db_path: Path to wuxia_glossary.db
        """
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Glossary database not found: {db_path}")

        # Load all data into memory from SQLite (thread-safe)
        self._load_all_data_into_memory()

        # No persistent connection needed - all data is in memory
        logger.info(f"Loaded wuxia glossary with {len(self._all_terms)} terms into memory (thread-safe)")

    def _load_all_data_into_memory(self):
        """
        Load all glossary data from SQLite into memory.

        Creates in-memory dictionaries for fast lookup without SQLite connection.
        This ensures thread-safety for parallel translation.
        """
        # Create temporary connection just for loading data
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Load all entries into memory
        cursor.execute("SELECT * FROM wuxia_glossary")
        rows = cursor.fetchall()

        # Build in-memory cache (chinese -> GlossaryEntry)
        self._cache: Dict[str, GlossaryEntry] = {}
        for row in rows:
            entry = GlossaryEntry(
                chinese=row['chinese'],
                pinyin=row['pinyin'],
                translation_strategy=row['translation_strategy'],
                recommended_form=row['recommended_form'],
                footnote_template=row['footnote_template'],
                category=row['category'],
                rationale=row['rationale'],
                deduplication_strategy=row['deduplication_strategy'],
                expected_frequency=row['expected_frequency'],
                source=row['source']
            )
            self._cache[row['chinese']] = entry

        # Build list of all terms sorted by length (longest first)
        # This ensures we match longer terms before shorter substrings
        self._all_terms: List[str] = sorted(
            self._cache.keys(),
            key=len,
            reverse=True
        )

        # Close the temporary connection - we don't need it anymore
        conn.close()

        logger.info(f"Loaded {len(self._cache)} glossary entries into memory")

    def lookup(self, chinese: str) -> Optional[GlossaryEntry]:
        """
        Look up a term by Chinese characters (thread-safe, uses in-memory cache).

        Args:
            chinese: Chinese term to look up

        Returns:
            GlossaryEntry if found, None otherwise
        """
        # All data is already in memory - just return from cache
        return self._cache.get(chinese)

    def find_in_text(self, text: str, max_matches: int = 20) -> List[Tuple[str, GlossaryEntry, int]]:
        """
        Find all glossary terms in Chinese text.

        Args:
            text: Chinese text to search
            max_matches: Maximum number of matches to return

        Returns:
            List of (term, entry, position) tuples sorted by position
        """
        matches = []

        # Track positions to avoid overlapping matches
        matched_positions: Set[int] = set()

        # Search for each term (longest first to avoid partial matches)
        for term in self._all_terms:
            for match in re.finditer(re.escape(term), text):
                start = match.start()
                end = match.end()

                # Check if this position overlaps with existing match
                if any(start <= pos < end for pos in matched_positions):
                    continue

                # Get entry
                entry = self.lookup(term)
                if entry:
                    matches.append((term, entry, start))

                    # Mark positions as matched
                    for pos in range(start, end):
                        matched_positions.add(pos)

                if len(matches) >= max_matches:
                    break

            if len(matches) >= max_matches:
                break

        # Sort by position
        matches.sort(key=lambda x: x[2])
        return matches

    def get_by_category(self, category: str) -> List[GlossaryEntry]:
        """
        Get all terms in a specific category (thread-safe, uses in-memory cache).

        Args:
            category: Category to filter by

        Returns:
            List of GlossaryEntry objects sorted by Chinese
        """
        # Filter in-memory cache by category
        entries = [
            entry for entry in self._cache.values()
            if entry.category == category
        ]

        # Sort by Chinese characters
        entries.sort(key=lambda e: e.chinese)

        return entries

    def get_high_frequency_terms(self) -> List[GlossaryEntry]:
        """
        Get all high-frequency terms (VERY_HIGH or HIGH) (thread-safe, uses in-memory cache).

        Returns:
            List of GlossaryEntry objects sorted by frequency then Chinese
        """
        # Filter in-memory cache by frequency
        entries = [
            entry for entry in self._cache.values()
            if entry.expected_frequency in ('VERY_HIGH', 'HIGH')
        ]

        # Sort by frequency (VERY_HIGH first), then by Chinese
        frequency_order = {'VERY_HIGH': 0, 'HIGH': 1}
        entries.sort(key=lambda e: (frequency_order.get(e.expected_frequency, 2), e.chinese))

        return entries

    def search(self, query: str, limit: int = 10) -> List[GlossaryEntry]:
        """
        Search glossary by Chinese, pinyin, or English (thread-safe, uses in-memory cache).

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of matching GlossaryEntry objects sorted by relevance
        """
        query_lower = query.lower()
        results = []

        # Search in-memory cache
        for entry in self._cache.values():
            # Check if query matches any field (case-insensitive for non-Chinese)
            if (query in entry.chinese or
                query_lower in entry.pinyin.lower() or
                query_lower in entry.recommended_form.lower() or
                query_lower in entry.footnote_template.lower()):

                # Assign priority for sorting
                if entry.chinese == query:
                    priority = 1
                elif entry.pinyin.lower() == query_lower:
                    priority = 2
                elif entry.chinese.startswith(query):
                    priority = 3
                else:
                    priority = 4

                results.append((priority, entry))

        # Sort by priority, then by Chinese
        results.sort(key=lambda x: (x[0], x[1].chinese))

        # Return entries only (without priority), limited
        return [entry for _, entry in results[:limit]]

    def close(self):
        """
        Close database connection (no-op since all data is in memory).

        Kept for backward compatibility with context manager usage.
        """
        # No persistent connection to close - all data is in memory
        pass

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def format_pinyin_italic(pinyin: str) -> str:
    """
    Format pinyin with italic markers for EPUB.

    Args:
        pinyin: Raw pinyin text

    Returns:
        Pinyin wrapped in italic markers (*pinyin*)
    """
    # Check if already has markers
    if pinyin.startswith('*') and pinyin.endswith('*'):
        return pinyin
    return f"*{pinyin}*"


def extract_pinyin_from_recommended_form(recommended_form: str) -> Optional[str]:
    """
    Extract pinyin from recommended form (handles various formats).

    Examples:
        "*nèigōng*" → "nèigōng"
        "yin energy (*yīnqì*)" → "yīnqì"
        "meridians (*jīngmài*)" → "jīngmài"

    Args:
        recommended_form: The recommended_form field from glossary

    Returns:
        Extracted pinyin without markers, or None if not found
    """
    # Pattern 1: *pinyin*
    match = re.search(r'\*([^*]+)\*', recommended_form)
    if match:
        return match.group(1)

    # Pattern 2: Plain text (fallback)
    return None


# =============================================================================
# MAIN / TEST
# =============================================================================

def main():
    """Test the glossary lookup"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python utils/wuxia_glossary.py <chinese_term_or_text>")
        print("\nExample:")
        print("  python utils/wuxia_glossary.py 內功")
        print("  python utils/wuxia_glossary.py '他修煉內功多年，內力深厚'")
        return 1

    query = sys.argv[1]

    try:
        with WuxiaGlossary() as glossary:
            print(f"\n=== WUXIA GLOSSARY LOOKUP ===\n")

            # Try direct lookup first
            entry = glossary.lookup(query)
            if entry:
                print(f"Direct Match: {entry.chinese}")
                print(f"  Pinyin: {entry.pinyin}")
                print(f"  Strategy: {entry.translation_strategy}")
                print(f"  Form: {entry.recommended_form}")
                print(f"  Category: {entry.category}")
                print(f"  Frequency: {entry.expected_frequency}")
                print(f"  Dedup: {entry.deduplication_strategy}")
                print(f"\nFootnote:")
                print(f"  {entry.footnote_template}")
            else:
                # Try finding in text
                print(f"Searching for terms in: '{query}'\n")
                matches = glossary.find_in_text(query)

                if matches:
                    print(f"Found {len(matches)} term(s):\n")
                    for i, (term, entry, pos) in enumerate(matches, 1):
                        print(f"{i}. {term} @ position {pos}")
                        print(f"   {entry.pinyin} ({entry.translation_strategy})")
                        print(f"   Inline: {entry.format_inline()}")
                        print(f"   Footnote: {entry.generate_footnote()[:100]}...")
                        print()
                else:
                    print("No matches found.")
                    print("\nTrying search...")
                    results = glossary.search(query)
                    if results:
                        print(f"\nSearch results for '{query}':")
                        for entry in results:
                            print(f"  - {entry.chinese} ({entry.pinyin}): {entry.recommended_form}")
                    else:
                        print("No results found.")

        return 0

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
