#!/usr/bin/env python3
"""
Fix Chapter Alignment - Post-processing script

Fixes misalignment between chapter titles and actual chapter headings
found in the content. Common issue with EPUB conversions where:
- EPUB metadata says chapter title is "《Book Title》Author"
- But actual chapter heading "第一回 ..." appears inside content

This script:
1. Scans content blocks for chapter heading patterns (第N回)
2. When found, uses that as the real chapter title
3. Optionally splits combined chapters into separate entries
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Import enhanced chapter parser for accurate ordinal extraction
try:
    from utils.enhanced_chapter_parser import EnhancedChapterParser
except ImportError:
    from enhanced_chapter_parser import EnhancedChapterParser


class ChapterAlignmentFixer:
    """Fix chapter title/content alignment issues"""

    # Pattern for Chinese chapter headings
    # Ordered by specificity (most specific first)
    CHAPTER_PATTERNS = [
        # Chinese traditional formats (回 = hui/episode)
        r'第[一二三四五六七八九十百千\d]+回[　\s]+(.+)',      # 第N回 Title (with title)
        r'第[一二三四五六七八九十百千\d]+回[　\s]*$',        # 第N回 (no title)

        # Chinese modern formats (章 = zhang/chapter)
        r'第[一二三四五六七八九十百千\d]+章[　\s]+(.+)',      # 第N章 Title (with title)
        r'第[一二三四五六七八九十百千\d]+章[　\s]*$',        # 第N章 (no title)

        # Without 第 prefix
        r'([一二三四五六七八九十百千]+)　(.+)',              # N　Title (traditional)
        r'(\d+)　(.+)',                                      # 1　Title (numeric)

        # English formats
        r'Chapter\s+(\d+)[:\s]*(.+)',                        # Chapter N: Title
        r'CHAPTER\s+(\d+)[:\s]*(.+)',                        # CHAPTER N: Title
    ]

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.fixes = []
        self.chapter_parser = EnhancedChapterParser()

    def fix_file(self, input_path: str, output_path: str = None) -> Dict[str, Any]:
        """Fix chapter alignment in a cleaned JSON file"""

        # Load the file
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Fix chapters
        original_count = len(data['structure']['body']['chapters'])
        data['structure']['body']['chapters'] = self._fix_chapters(
            data['structure']['body']['chapters']
        )
        fixed_count = len(data['structure']['body']['chapters'])

        # Extract actual chapter numbers from titles (preserves multi-volume numbering)
        # For continuation volumes, this keeps chapter 31, 32, 33... instead of resetting to 1, 2, 3...
        total_chapters = len(data['structure']['body']['chapters'])
        for i, chapter in enumerate(data['structure']['body']['chapters']):
            title = chapter.get('title', '')

            # Extract chapter number from title using enhanced parser
            result = self.chapter_parser.extract_with_fallback(title, i, total_chapters)

            if result.number is not None:
                chapter['ordinal'] = result.number
            else:
                # Fallback: use position (1-based)
                chapter['ordinal'] = i + 1

        # Report
        print(f"\n📊 ALIGNMENT FIX SUMMARY")
        print(f"  Original chapters: {original_count}")
        print(f"  Fixed chapters: {fixed_count}")
        print(f"  Changes made: {len(self.fixes)}")

        if self.fixes:
            print(f"\n🔧 FIXES APPLIED:")
            for fix in self.fixes[:10]:  # Show first 10
                print(f"  • {fix}")
            if len(self.fixes) > 10:
                print(f"  ... and {len(self.fixes) - 10} more")

        # Save if not dry run
        if not self.dry_run:
            if output_path is None:
                output_path = input_path

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"\n✓ Fixed file saved to: {output_path}")
        else:
            print(f"\n⚠️  DRY RUN - No files modified")

        return data

    def _fix_chapters(self, chapters: List[Dict]) -> List[Dict]:
        """Fix chapter titles and split combined chapters"""
        fixed_chapters = []

        for i, chapter in enumerate(chapters):
            # Check if this is a metadata heading (typically first chapter)
            if self._is_metadata_chapter(chapter):
                self.fixes.append(
                    f"Removed metadata chapter: '{chapter['title'][:60]}...'"
                )
                continue  # Skip this chapter entirely

            # Check if this chapter contains a real chapter heading
            heading_found = self._find_chapter_heading(chapter)

            if heading_found:
                block_idx, new_title = heading_found
                old_title = chapter['title']

                # Case 1: Title doesn't match heading pattern, but content does
                if not self._matches_chapter_pattern(old_title):
                    self.fixes.append(
                        f"Chapter {i+1}: '{old_title[:40]}...' → '{new_title[:40]}...'"
                    )
                    chapter['title'] = new_title
                    chapter['title_en'] = ""

                # Case 2: Check if multiple chapter headings exist in content
                # (indicates combined chapters that should be split)
                all_headings = self._find_all_chapter_headings(chapter)
                if len(all_headings) > 1:
                    # Split into multiple chapters
                    split_chapters = self._split_chapter(chapter, all_headings)
                    fixed_chapters.extend(split_chapters)
                    self.fixes.append(
                        f"Split chapter {i+1} into {len(split_chapters)} chapters"
                    )
                    continue

            # No splitting needed, add as-is
            fixed_chapters.append(chapter)

        return fixed_chapters

    def _is_metadata_chapter(self, chapter: Dict) -> bool:
        """Check if an entire chapter is just metadata (title page, etc.)"""
        title = chapter.get('title', '').strip()

        # Check title itself
        if self._is_metadata_heading(title):
            return True

        # Check first few content blocks
        content_blocks = chapter.get('content_blocks', [])
        if not content_blocks:
            return False

        # If first 3 blocks are all metadata/decorators, it's likely a metadata chapter
        metadata_count = 0
        for block in content_blocks[:3]:
            content = block.get('content', '').strip()
            if self._is_metadata_heading(content) or self._is_decorator(content):
                metadata_count += 1

        # If majority (2/3) of first blocks are metadata, skip this chapter
        return metadata_count >= 2

    def _matches_chapter_pattern(self, title: str) -> bool:
        """Check if title matches a chapter heading pattern"""
        for pattern in self.CHAPTER_PATTERNS:
            if re.search(pattern, title):
                return True
        return False

    def _is_metadata_heading(self, content: str) -> bool:
        """
        Check if content is a metadata heading (book title, author info, etc.)

        These are typically found at the start of books and should not be
        treated as chapter 1.

        Patterns:
        - Contains book title markers: 《》
        - Contains author delimiters: ／ (slash), 、(comma)
        - Contains publication date patterns
        - Matches typical metadata formats
        """
        content = content.strip()

        # Check for book title markers
        if '《' in content or '》' in content:
            return True

        # Check for author delimiter patterns (e.g., "Title／Author", "Title、Author")
        if '／' in content or ('、' in content and len(content) < 50):
            return True

        # Check for publication date patterns
        date_patterns = [
            r'[一二三四五六七八九十○〇]+年[一二三四五六七八九十○〇]+月',  # Chinese date
            r'\d{4}年\d{1,2}月',  # Numeric date
            r'(民國|西元)\d+年',  # ROC/Western year
        ]
        for pattern in date_patterns:
            if re.search(pattern, content):
                return True

        # Check for common metadata keywords
        metadata_keywords = [
            '出版', '版權', '著作權', 'ISBN', '印刷', '發行',
            'Publisher', 'Copyright', 'All Rights Reserved',
            '好讀出版', '遠流出版', '聯經出版'
        ]
        if any(kw in content for kw in metadata_keywords):
            return True

        return False

    def _is_decorator(self, content: str) -> bool:
        """
        Check if content is just a decorator (visual separator).

        Decorators are repetitive characters used for visual separation,
        not actual chapter headings.

        Examples: ☆☆☆☆☆☆, ＊＊＊＊＊＊, ━━━━━━, ─────, ＝＝＝＝＝＝
        """
        content = content.strip()

        # Empty or very short strings
        if len(content) < 3:
            return False

        # Check if content is mostly repetitive decorator characters
        decorator_chars = {'☆', '＊', '※', '◆', '●', '○', '◎', '★',
                          '━', '─', '＝', '═', '▬', '－', '＿',
                          '~', '～', '·', '•', '▪', '▫'}

        # Count decorator characters
        decorator_count = sum(1 for c in content if c in decorator_chars)

        # If more than 60% of content is decorator characters, it's a decorator
        if len(content) > 0 and decorator_count / len(content) > 0.6:
            return True

        # Check for repetitive patterns (same char repeated 4+ times)
        if len(set(content)) <= 2 and len(content) >= 4:
            return True

        return False

    def _find_chapter_heading(self, chapter: Dict) -> Tuple[int, str] | None:
        """Find first chapter heading in content blocks"""
        for i, block in enumerate(chapter.get('content_blocks', [])):
            content = block.get('content', '')

            # Skip decorators
            if self._is_decorator(content):
                continue

            # Check all patterns
            for pattern in self.CHAPTER_PATTERNS:
                match = re.search(pattern, content)
                if match:
                    # Return block index and the full heading
                    return (i, content.strip())

        return None

    def _find_all_chapter_headings(self, chapter: Dict) -> List[Tuple[int, str]]:
        """Find all chapter headings in content blocks"""
        headings = []
        last_heading = None

        for i, block in enumerate(chapter.get('content_blocks', [])):
            content = block.get('content', '').strip()

            # Skip decorators
            if self._is_decorator(content):
                continue

            # Check all patterns
            for pattern in self.CHAPTER_PATTERNS:
                match = re.search(pattern, content)
                if match:
                    # Skip if this is the same as the last heading (consecutive duplicates)
                    if content != last_heading:
                        # Also skip if very close (within 3 blocks) and same text
                        if not headings or i - headings[-1][0] > 3 or content != headings[-1][1]:
                            headings.append((i, content))
                            last_heading = content
                    break  # Only count each block once

        return headings

    def _split_chapter(self, chapter: Dict, headings: List[Tuple[int, str]]) -> List[Dict]:
        """Split a chapter with multiple headings into separate chapters"""
        split_chapters = []
        content_blocks = chapter.get('content_blocks', [])
        original_ordinal = chapter.get('ordinal', 0)

        # Split part identifiers: a, b, c, d, ...
        split_parts = 'abcdefghijklmnopqrstuvwxyz'

        for i, (block_idx, heading) in enumerate(headings):
            # Determine slice range
            start_idx = block_idx
            end_idx = headings[i+1][0] if i+1 < len(headings) else len(content_blocks)

            # Create new chapter with split tracking
            new_chapter = {
                'id': f"{chapter['id']}_split_{i+1}",
                'title': heading,
                'title_en': "",
                'ordinal': original_ordinal,  # Keep original chapter number
                'split_part': split_parts[i] if i < len(split_parts) else str(i),  # a, b, c, ...
                'content_blocks': content_blocks[start_idx:end_idx]
            }
            split_chapters.append(new_chapter)

        return split_chapters


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Fix chapter title/content alignment in cleaned JSON files'
    )
    parser.add_argument(
        '--input', '-i',
        required=True,
        help='Input cleaned JSON file'
    )
    parser.add_argument(
        '--output', '-o',
        default=None,
        help='Output file (default: overwrite input)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be fixed without modifying files'
    )

    args = parser.parse_args()

    # Validate input
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ Error: File not found: {input_path}")
        return 1

    print(f"🔧 Fixing chapter alignment in: {input_path}")
    if args.dry_run:
        print(f"   (DRY RUN - no changes will be saved)")
    print()

    # Fix alignment
    try:
        fixer = ChapterAlignmentFixer(dry_run=args.dry_run)
        fixer.fix_file(str(input_path), args.output)
        return 0

    except Exception as e:
        print(f"❌ Error fixing alignment: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
