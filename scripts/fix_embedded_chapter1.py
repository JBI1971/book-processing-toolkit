#!/usr/bin/env python3
"""
Fix embedded first chapter in cleaned book JSON files.

This script handles the common pattern where the FIRST CHAPTER OF A VOLUME
is embedded in the title page/introduction section.

IMPORTANT: This applies to ANY volume, not just Volume 1:
- Volume 1: First chapter (e.g., "一、...") may be embedded
- Volume 2: First chapter (e.g., "一、..." if reset, or "廿一、..." if continuing)
- Volume 3: First chapter (e.g., "卅一、...", "卌一、...", or "一、..." if reset)

Chapter numbering varies:
- Some works reset to Chapter 1 per volume
- Some works continue numbering across volumes (Vol 1: 1-20, Vol 2: 21-40, etc.)
- Some works have irregular numbering (Vol 3 might start at 31, not 41)

The script detects ANY Chinese chapter marker (一、二、三... 廿、卅、卌...)
and extracts the first one found, regardless of the specific number.

For multi-volume works, run this script on EACH volume file separately.
"""

import json
import sys
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple


def parse_chinese_number(text: str) -> Optional[int]:
    """Parse Chinese numerals including special cases."""
    chinese_nums = {
        '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
        '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
        '廿': 20, '卅': 30, '卌': 40, '百': 100, '千': 1000
    }

    # Handle special patterns
    if '廿' in text:
        base = 20
        remainder_match = re.search(r'廿([一二三四五六七八九])', text)
        if remainder_match:
            return base + chinese_nums.get(remainder_match.group(1), 0)
        return base

    if '卅' in text:
        base = 30
        remainder_match = re.search(r'卅([一二三四五六七八九])', text)
        if remainder_match:
            return base + chinese_nums.get(remainder_match.group(1), 0)
        return base

    if '卌' in text:
        base = 40
        remainder_match = re.search(r'卌([一二三四五六七八九])', text)
        if remainder_match:
            return base + chinese_nums.get(remainder_match.group(1), 0)
        return base

    # Handle 十X pattern (10+)
    ten_match = re.search(r'十([一二三四五六七八九])', text)
    if ten_match:
        return 10 + chinese_nums.get(ten_match.group(1), 0)

    # Simple lookup
    for char in text:
        if char in chinese_nums:
            return chinese_nums[char]

    return None


def extract_chapter_title_and_number(content: str) -> Tuple[Optional[int], Optional[str]]:
    """
    Extract chapter number and title from content.

    Returns:
        (chapter_number, full_title) or (None, None)
    """
    # Pattern: 一、弱齡習武，志訪絕學
    pattern = r'^([一二三四五六七八九十廿卅卌百千]+)、(.+)$'
    match = re.match(pattern, content.strip())

    if match:
        chinese_num = match.group(1)
        title_part = match.group(2)
        chapter_num = parse_chinese_number(chinese_num)
        full_title = content.strip()

        return (chapter_num, full_title)

    return (None, None)


def find_embedded_chapter1(intro_section: Dict[str, Any]) -> Optional[int]:
    """
    Find the block index where Chapter 1 starts in the introduction section.

    Returns:
        Block index where Chapter 1 title is found, or None
    """
    if not intro_section or 'content_blocks' not in intro_section:
        return None

    content_blocks = intro_section['content_blocks']

    for i, block in enumerate(content_blocks):
        content = block.get('content', '').strip()
        chapter_num, _ = extract_chapter_title_and_number(content)

        if chapter_num == 1:
            return i

    return None


def extract_chapter1_from_intro(data: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    """
    Extract Chapter 1 from introduction section if found.

    Returns:
        (modified_data, was_modified)
    """
    # Check if we have an introduction section
    # It might be in front_matter.introduction OR front_matter.sections OR front_matter.toc array
    intro_sections = data.get('structure', {}).get('front_matter', {}).get('introduction', [])
    intro_location = 'introduction'

    # If not found, check in sections array for type="introduction"
    if not intro_sections:
        sections_array = data.get('structure', {}).get('front_matter', {}).get('sections', [])
        if isinstance(sections_array, list):
            intro_sections = [item for item in sections_array if item.get('type') == 'introduction']
            if intro_sections:
                intro_location = 'sections'

    # If still not found, check in toc array for type="introduction"
    if not intro_sections:
        toc_array = data.get('structure', {}).get('front_matter', {}).get('toc', [])
        if isinstance(toc_array, list):
            intro_sections = [item for item in toc_array if item.get('type') == 'introduction']
            if intro_sections:
                intro_location = 'toc'

    if not intro_sections:
        print("No introduction section found.")
        return (data, False)

    # Find the intro section
    intro = intro_sections[0] if isinstance(intro_sections, list) else intro_sections

    # Find where Chapter 1 starts
    ch1_start_idx = find_embedded_chapter1(intro)

    if ch1_start_idx is None:
        print("No embedded Chapter 1 found in introduction.")
        return (data, False)

    print(f"Found Chapter 1 at block index {ch1_start_idx} in introduction section")

    # Extract Chapter 1 content blocks
    content_blocks = intro['content_blocks']
    ch1_blocks = content_blocks[ch1_start_idx:]
    intro_blocks = content_blocks[:ch1_start_idx]

    # Get Chapter 1 title
    ch1_title_block = ch1_blocks[0]
    ch1_title = ch1_title_block.get('content', '').strip()
    _, ch1_full_title = extract_chapter_title_and_number(ch1_title)

    print(f"Chapter 1 title: {ch1_full_title}")
    print(f"Extracted {len(ch1_blocks)} blocks for Chapter 1")
    print(f"Remaining {len(intro_blocks)} blocks in introduction")

    # Renumber Chapter 1 blocks
    renumbered_ch1_blocks = []
    for i, block in enumerate(ch1_blocks):
        new_block = block.copy()
        new_block['id'] = f"block_{i:04d}"
        renumbered_ch1_blocks.append(new_block)

    # Create Chapter 1
    chapter1 = {
        "id": "chapter_0001",
        "title": ch1_full_title,
        "ordinal": 1,
        "content_blocks": renumbered_ch1_blocks
    }

    # Update introduction section (keep only metadata blocks)
    if intro_blocks:
        intro['content_blocks'] = intro_blocks
    else:
        # Remove introduction section if empty
        if intro_location == 'introduction':
            data['structure']['front_matter']['introduction'] = []
        elif intro_location == 'sections':
            # Remove from sections array
            sections_array = data.get('structure', {}).get('front_matter', {}).get('sections', [])
            if isinstance(sections_array, list):
                data['structure']['front_matter']['sections'] = [
                    item for item in sections_array if item.get('id') != intro.get('id')
                ]
        elif intro_location == 'toc':
            # Remove from toc array
            toc_array = data.get('structure', {}).get('front_matter', {}).get('toc', [])
            if isinstance(toc_array, list):
                data['structure']['front_matter']['toc'] = [
                    item for item in toc_array if item.get('id') != intro.get('id')
                ]

    # Get existing chapters and renumber them
    existing_chapters = data.get('structure', {}).get('body', {}).get('chapters', [])

    # Renumber existing chapters (they become 2, 3, 4, ...)
    renumbered_chapters = []
    for i, chapter in enumerate(existing_chapters, start=2):
        new_chapter = chapter.copy()
        new_chapter['id'] = f"chapter_{i:04d}"
        new_chapter['ordinal'] = i

        # Update title if it has incorrect chapter number
        old_title = chapter.get('title', '')
        old_num, title_part = extract_chapter_title_and_number(old_title)
        if old_num and title_part:
            # Keep original title format, just verify numbering
            new_chapter['title'] = old_title

        renumbered_chapters.append(new_chapter)

    # Insert Chapter 1 at the beginning
    all_chapters = [chapter1] + renumbered_chapters

    # Update body
    data['structure']['body']['chapters'] = all_chapters

    print(f"Created {len(all_chapters)} chapters (1 extracted + {len(renumbered_chapters)} existing)")

    # Update TOC
    toc_section = data.get('structure', {}).get('front_matter', {}).get('toc', [])

    if toc_section:
        toc = toc_section[0] if isinstance(toc_section, list) else toc_section

        # Create Chapter 1 TOC entry
        ch1_toc_entry = {
            "full_title": ch1_full_title,
            "chapter_title": ch1_full_title,
            "chapter_number": 1,
            "chapter_id": "chapter_0001"
        }

        # Update existing TOC entries
        existing_entries = toc.get('entries', [])
        updated_entries = []

        # Renumber TOC entries to match new chapter numbering
        for i, entry in enumerate(existing_entries, start=2):
            new_entry = entry.copy()
            new_entry['chapter_number'] = i
            new_entry['chapter_id'] = f"chapter_{i:04d}"
            updated_entries.append(new_entry)

        # Insert Chapter 1 at the beginning
        all_entries = [ch1_toc_entry] + updated_entries
        toc['entries'] = all_entries

        print(f"Updated TOC with {len(all_entries)} entries (1 new + {len(updated_entries)} existing)")

    return (data, True)


def main():
    if len(sys.argv) < 2:
        print("Usage: python fix_embedded_chapter1.py <input_file> [output_file]")
        print("\nIf output_file is not specified, will overwrite input_file.")
        return 1

    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2]) if len(sys.argv) > 2 else input_file

    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
        return 1

    print(f"Processing: {input_file}")

    # Load JSON
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Extract Chapter 1
    modified_data, was_modified = extract_chapter1_from_intro(data)

    if not was_modified:
        print("No changes needed.")
        return 0

    # Save result
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(modified_data, f, ensure_ascii=False, indent=2)

    print(f"\nSaved to: {output_file}")

    # Show summary
    chapters = modified_data.get('structure', {}).get('body', {}).get('chapters', [])
    print(f"\nFinal structure:")
    print(f"  Total chapters: {len(chapters)}")
    for ch in chapters[:5]:  # Show first 5
        print(f"    - Chapter {ch['ordinal']}: {ch['title']}")
    if len(chapters) > 5:
        print(f"    ... and {len(chapters) - 5} more")

    return 0


if __name__ == "__main__":
    sys.exit(main())
