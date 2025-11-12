#!/usr/bin/env python3
"""
Auto-Fix TOC Alignment - Apply AI validation suggestions automatically

This script reads validation reports from toc_chapter_validator and applies
automatic fixes for common issues:

1. Systematic offset (e.g., all chapters off by 1)
2. Missing chapters (remove from TOC or flag for review)
3. Character variants (apply fuzzy matching)
4. Number mismatches with clear patterns

Generates before/after reports to validate fixes.
"""

import json
import logging
import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class FixResult:
    """Result of applying a fix"""
    success: bool
    fix_type: str
    description: str
    before: Any
    after: Any


class TOCAlignmentAutoFixer:
    """Automatically fix common TOC alignment issues"""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.fixes_applied = []

    def fix_file(self, input_path: str, output_path: str = None) -> Dict[str, Any]:
        """
        Apply automatic fixes to a cleaned JSON file.

        Args:
            input_path: Path to cleaned JSON file
            output_path: Path to save fixed file (default: overwrite input)

        Returns:
            Dict with fix results
        """
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        original_data = json.dumps(data)

        # Apply fixes in order
        self._detect_and_fix_metadata_chapters(data)
        self._detect_and_fix_systematic_offset(data)
        self._fix_missing_toc_entries(data)

        # Save if not dry run and changes were made
        if not self.dry_run and json.dumps(data) != original_data:
            if output_path is None:
                output_path = input_path

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info(f"Fixed file saved to: {output_path}")

        return {
            'success': True,
            'fixes_applied': len(self.fixes_applied),
            'fixes': self.fixes_applied,
            'dry_run': self.dry_run
        }

    def _detect_and_fix_metadata_chapters(self, data: Dict) -> bool:
        """
        Detect and remove metadata chapters (already done by ChapterAlignmentFixer).
        This is a sanity check in case it was missed.
        """
        chapters = data.get('structure', {}).get('body', {}).get('chapters', [])
        if not chapters:
            return False

        # Check first chapter
        first_chapter = chapters[0]
        title = first_chapter.get('title', '')

        # Metadata patterns
        if '《' in title or '》' in title or '／' in title:
            logger.info(f"Found metadata chapter: {title[:60]}")
            chapters.pop(0)

            # Renumber remaining chapters
            for i, ch in enumerate(chapters, 1):
                ch['ordinal'] = i

            self.fixes_applied.append(FixResult(
                success=True,
                fix_type="remove_metadata_chapter",
                description=f"Removed metadata chapter: {title[:60]}",
                before=title,
                after=None
            ))
            return True

        return False

    def _detect_and_fix_systematic_offset(self, data: Dict) -> bool:
        """
        Detect systematic offset in TOC/chapter numbering.

        If all TOC entries are consistently off by N (e.g., TOC says ch1 but
        actual content is ch2), renumber TOC entries.
        """
        toc_entries = self._get_toc_entries(data)
        chapters = data.get('structure', {}).get('body', {}).get('chapters', [])

        if not toc_entries or not chapters:
            return False

        # Extract chapter numbers from actual headings
        actual_numbers = self._extract_chapter_numbers_from_content(chapters)

        if len(actual_numbers) < 3:  # Need at least 3 to detect pattern
            return False

        # Check if there's a consistent offset
        offset = None
        offset_count = 0

        # Extract TOC numbers first to avoid variable scoping issue
        toc_numbers = [e.get('chapter_number', idx+1) for idx, e in enumerate(toc_entries)]

        for i, (toc_num, actual_num) in enumerate(zip(toc_numbers, actual_numbers)):
            current_offset = actual_num - toc_num
            if offset is None:
                offset = current_offset
                offset_count = 1
            elif current_offset == offset:
                offset_count += 1

        # If 80%+ have same offset, apply fix
        if offset and offset_count / len(actual_numbers) >= 0.8:
            logger.info(f"Detected systematic offset: {offset}")

            # Apply offset to TOC
            for entry in toc_entries:
                old_num = entry.get('chapter_number', 0)
                entry['chapter_number'] = old_num + offset

            self.fixes_applied.append(FixResult(
                success=True,
                fix_type="systematic_offset",
                description=f"Applied offset of {offset} to all TOC entries",
                before=f"offset: 0",
                after=f"offset: {offset}"
            ))
            return True

        return False

    def _fix_missing_toc_entries(self, data: Dict) -> bool:
        """
        Generate missing TOC entries from chapter headings.
        """
        toc_entries = self._get_toc_entries(data)
        chapters = data.get('structure', {}).get('body', {}).get('chapters', [])

        if not chapters:
            return False

        # If TOC is empty or much shorter than chapters, regenerate
        if len(toc_entries) < len(chapters) * 0.5:
            logger.info(f"Regenerating TOC (had {len(toc_entries)}, need {len(chapters)})")

            new_toc = []
            for i, chapter in enumerate(chapters, 1):
                title = chapter.get('title', f'Chapter {i}')
                chapter_num = self._parse_chapter_number_from_title(title) or i

                new_toc.append({
                    'full_title': title,
                    'chapter_title': self._extract_chapter_title(title),
                    'chapter_number': chapter_num,
                    'chapter_id': chapter.get('id', f'chapter_{i:04d}')
                })

            # Update TOC
            toc_structure = data.get('structure', {}).get('front_matter', {})
            if isinstance(toc_structure.get('toc'), list) and len(toc_structure['toc']) > 0:
                if 'entries' in toc_structure['toc'][0]:
                    toc_structure['toc'][0]['entries'] = new_toc
                else:
                    toc_structure['toc'] = new_toc
            else:
                toc_structure['toc'] = new_toc

            self.fixes_applied.append(FixResult(
                success=True,
                fix_type="regenerate_toc",
                description=f"Regenerated TOC with {len(new_toc)} entries",
                before=f"{len(toc_entries)} entries",
                after=f"{len(new_toc)} entries"
            ))
            return True

        return False

    def _get_toc_entries(self, data: Dict) -> List[Dict]:
        """Extract TOC entries from data structure"""
        toc = data.get('structure', {}).get('front_matter', {}).get('toc', [])

        if not toc:
            return []

        # Handle both old and new TOC formats
        if isinstance(toc, list) and len(toc) > 0:
            if 'entries' in toc[0]:
                return toc[0]['entries']
            elif isinstance(toc[0], dict) and 'chapter_number' in toc[0]:
                return toc

        return []

    def _extract_chapter_numbers_from_content(self, chapters: List[Dict]) -> List[int]:
        """Extract actual chapter numbers from chapter content"""
        numbers = []

        for chapter in chapters:
            # Try to find chapter number in content blocks
            content_blocks = chapter.get('content_blocks', [])
            for block in content_blocks[:3]:  # Check first few blocks
                content = block.get('content', '')
                num = self._parse_chapter_number_from_title(content)
                if num:
                    numbers.append(num)
                    break

        return numbers

    def _parse_chapter_number_from_title(self, title: str) -> Optional[int]:
        """Parse chapter number from title string"""
        # Pattern: 第N回 or 第N章
        patterns = [
            r'第([一二三四五六七八九十百千廿卅卌\d]+)[回章]',
            r'Chapter\s+(\d+)',
            r'CHAPTER\s+(\d+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, title)
            if match:
                num_str = match.group(1)
                # Convert Chinese numeral if needed
                if num_str.isdigit():
                    return int(num_str)
                else:
                    return self._chinese_to_int(num_str)

        return None

    def _chinese_to_int(self, chinese: str) -> Optional[int]:
        """Convert Chinese numerals to integer"""
        chinese_nums = {
            '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
            '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
            '廿': 20, '卅': 30, '卌': 40,
            '百': 100, '千': 1000
        }

        result = 0
        temp = 0
        last_multiplier = 1

        for char in chinese:
            if char in chinese_nums:
                value = chinese_nums[char]
                if value >= 10:
                    if temp == 0:
                        temp = 1
                    result += temp * value
                    temp = 0
                    last_multiplier = value
                else:
                    temp = value
            else:
                logger.warning(f"Unknown Chinese numeral character: {char}")
                return None

        result += temp
        return result if result > 0 else None

    def _extract_chapter_title(self, full_title: str) -> str:
        """Extract chapter title without number prefix"""
        # Remove 第N回/章 prefix
        match = re.match(r'第[一二三四五六七八九十百千廿卅卌\d]+[回章][　\s]*(.+)', full_title)
        if match:
            return match.group(1)

        # Remove Chapter N prefix
        match = re.match(r'(?:Chapter|CHAPTER)\s+\d+[:\s]*(.+)', full_title)
        if match:
            return match.group(1)

        return full_title


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Automatically fix common TOC alignment issues'
    )
    parser.add_argument(
        '--input', '-i',
        required=True,
        help='Input cleaned JSON file'
    )
    parser.add_argument(
        '--output', '-o',
        help='Output file (default: overwrite input)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be fixed without modifying files'
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        return 1

    print(f"Auto-fixing TOC alignment in: {input_path}")
    if args.dry_run:
        print("  (DRY RUN - no changes will be saved)")
    print()

    try:
        fixer = TOCAlignmentAutoFixer(dry_run=args.dry_run)
        result = fixer.fix_file(str(input_path), args.output)

        print(f"\nFixes Applied: {result['fixes_applied']}")
        for fix in result['fixes']:
            print(f"  - {fix.fix_type}: {fix.description}")

        return 0

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
