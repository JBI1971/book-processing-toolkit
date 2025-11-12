#!/usr/bin/env python3
"""
Calculate character counts, word counts, and token estimates for cleaned JSON files
and store them in the SQLite database.

This script:
1. Scans all cleaned JSON files in the specified directory
2. Extracts all content from content_blocks
3. Counts Chinese characters, words, and estimates tokens
4. Updates the work_files table in the catalog database
"""

import json
import sqlite3
import re
from pathlib import Path
from typing import Dict, Tuple
import sys

# Configuration
CLEANED_JSON_DIR = Path("/Users/jacki/project_files/translation_project/test_cleaned_json_v2/test_10_works")
CATALOG_DB_PATH = Path("/Users/jacki/project_files/translation_project/wuxia_catalog.db")

# Chinese character Unicode ranges
CHINESE_CHAR_PATTERN = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf\U00020000-\U0002a6df\U0002a700-\U0002b73f\U0002b740-\U0002b81f\U0002b820-\U0002ceaf]')

def count_chinese_characters(text: str) -> int:
    """Count Chinese characters in text"""
    return len(CHINESE_CHAR_PATTERN.findall(text))


def estimate_word_count(text: str, char_count: int) -> int:
    """
    Estimate word count for Chinese text

    Chinese doesn't use spaces, so we estimate based on:
    - Punctuation marks as word boundaries
    - Average of 2-3 characters per word
    """
    # Count punctuation marks (word boundaries)
    punctuation_pattern = re.compile(r'[。！？；，、：]')
    punctuation_count = len(punctuation_pattern.findall(text))

    # Estimate: punctuation count + char_count / 2.5 (average chars per word)
    if punctuation_count > 0:
        return punctuation_count + int(char_count / 2.5)
    else:
        # Fallback: assume average of 2.5 characters per word
        return int(char_count / 2.5)


def estimate_tokens(char_count: int) -> int:
    """
    Estimate token count for Chinese text

    Chinese text typically uses 1.5-2 characters per token.
    We use 1.7 as a middle ground.
    """
    return int(char_count / 1.7)


def extract_content_from_json(file_path: Path) -> Tuple[int, int, int]:
    """
    Extract all content from a cleaned JSON file and calculate statistics

    Returns:
        (character_count, word_count, estimated_tokens)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Collect all content from the JSON
        all_content = []

        # Function to recursively extract content from any structure
        def extract_content(obj):
            if isinstance(obj, dict):
                # Check for content_blocks
                if 'content_blocks' in obj:
                    for block in obj['content_blocks']:
                        if isinstance(block, dict) and 'content' in block:
                            all_content.append(block['content'])

                # Check for chapters
                if 'chapters' in obj:
                    for chapter in obj['chapters']:
                        extract_content(chapter)

                # Recursively check other dict values
                for value in obj.values():
                    if isinstance(value, (dict, list)):
                        extract_content(value)

            elif isinstance(obj, list):
                for item in obj:
                    extract_content(item)

        # Extract from structure
        if 'structure' in data:
            extract_content(data['structure'])

        # Combine all content
        full_text = '\n'.join(all_content)

        # Calculate statistics
        char_count = count_chinese_characters(full_text)
        word_count = estimate_word_count(full_text, char_count)
        token_count = estimate_tokens(char_count)

        return char_count, word_count, token_count

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return 0, 0, 0


def update_database(conn: sqlite3.Connection, file_path: str, char_count: int, word_count: int, token_count: int):
    """Update work_files table with calculated statistics"""
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE work_files
        SET character_count = ?, word_count = ?, estimated_tokens = ?
        WHERE full_path = ?
    """, (char_count, word_count, token_count, file_path))

    return cursor.rowcount > 0


def main():
    """Main function to process all files and update database"""

    if not CLEANED_JSON_DIR.exists():
        print(f"Error: Cleaned JSON directory not found: {CLEANED_JSON_DIR}")
        return 1

    if not CATALOG_DB_PATH.exists():
        print(f"Error: Catalog database not found: {CATALOG_DB_PATH}")
        return 1

    # Connect to database
    conn = sqlite3.connect(CATALOG_DB_PATH)

    # Get all file paths from database
    cursor = conn.cursor()
    cursor.execute("SELECT file_id, full_path, directory_name, filename FROM work_files")
    db_files = cursor.fetchall()

    print(f"Found {len(db_files)} cleaned files in database")
    print(f"Scanning directory: {CLEANED_JSON_DIR}")
    print()

    processed = 0
    updated = 0
    errors = 0

    for file_id, file_path, directory, filename in db_files:
        # Look for cleaned version of this file
        cleaned_filename = f"cleaned_{filename}" if not filename.startswith("cleaned_") else filename
        test_path = CLEANED_JSON_DIR / directory / cleaned_filename

        if not test_path.exists():
            # Try original path
            path_obj = Path(file_path)
            if not path_obj.exists():
                errors += 1
                continue
        else:
            path_obj = test_path

        # Extract statistics
        char_count, word_count, token_count = extract_content_from_json(path_obj)

        if char_count > 0:
            # Update database
            if update_database(conn, file_path, char_count, word_count, token_count):
                updated += 1
                print(f"✓ {directory}/{filename:50} - {char_count:>8,} chars, {word_count:>8,} words, ~{token_count:>8,} tokens")
            else:
                print(f"⚠️  Failed to update: {file_path}")
                errors += 1
        else:
            print(f"⚠️  No content found: {path_obj.name}")
            errors += 1

        processed += 1

        # Commit every 10 files
        if processed % 10 == 0:
            conn.commit()

    # Final commit
    conn.commit()
    conn.close()

    print()
    print("=" * 80)
    print(f"Processing complete!")
    print(f"  Total files processed: {processed}")
    print(f"  Successfully updated: {updated}")
    print(f"  Errors: {errors}")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
