#!/usr/bin/env python3
"""
TOC Auto-Fix Utility

Automatically fixes TOC/body count mismatches by:
1. Detecting missing chapters from TOC
2. Generating proper TOC entries for those chapters
3. Inserting them in correct order
4. Optionally removing extra TOC entries

Addresses Priority 3: TOC/Body Count Validation Enhancement
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class TOCFix:
    """Represents a fix applied to TOC"""
    fix_type: str  # "add_entry", "remove_entry", "reorder"
    chapter_number: int
    chapter_title: str
    chapter_id: str
    position: int  # Where in TOC this was added/removed


class TOCAutoFixer:
    """
    Automatically fixes TOC/body mismatches.

    Generates missing TOC entries and inserts them in correct order.
    """

    def generate_toc_entry(
        self,
        chapter: Dict[str, Any],
        ordinal: int
    ) -> Dict[str, Any]:
        """
        Generate a proper TOC entry for a chapter.

        Args:
            chapter: Chapter dict with id, title, ordinal
            ordinal: Chapter number (ordinal)

        Returns:
            TOC entry dict
        """
        # Get chapter title
        title = chapter.get('title', '')

        # Generate full_title (with chapter number)
        # Try to preserve original format if it exists
        if '回' in title and '第' in title:
            # Already has "第N回" format
            full_title = title
        elif '章' in title and '第' in title:
            # Already has "第N章" format
            full_title = title
        else:
            # Add chapter number
            full_title = f"第{self._number_to_chinese(ordinal)}章　{title}"

        # Extract chapter title (without number)
        chapter_title = title
        if '　' in title:
            parts = title.split('　', 1)
            if len(parts) > 1:
                chapter_title = parts[1]

        return {
            "full_title": full_title,
            "chapter_title": chapter_title,
            "chapter_number": ordinal,
            "chapter_id": chapter.get('id', f"chapter_{ordinal:04d}")
        }

    def _number_to_chinese(self, num: int) -> str:
        """
        Convert number to Chinese numerals.

        Args:
            num: Integer 1-999

        Returns:
            Chinese numeral string
        """
        if num == 0:
            return "零"

        # Map for basic digits
        digits = ['', '一', '二', '三', '四', '五', '六', '七', '八', '九']
        units = ['', '十', '百', '千']

        if num < 10:
            return digits[num]
        elif num == 10:
            return '十'
        elif num < 20:
            # 11-19: 十一, 十二, etc.
            return f"十{digits[num - 10]}"
        elif num < 100:
            # 20-99
            tens = num // 10
            ones = num % 10
            result = digits[tens] + '十'
            if ones > 0:
                result += digits[ones]
            return result
        elif num < 1000:
            # 100-999
            hundreds = num // 100
            remainder = num % 100
            result = digits[hundreds] + '百'

            if remainder == 0:
                return result
            elif remainder < 10:
                result += '零' + digits[remainder]
            else:
                tens = remainder // 10
                ones = remainder % 10
                if tens > 0:
                    result += digits[tens] + '十'
                if ones > 0:
                    result += digits[ones]

            return result
        else:
            # For very large numbers, just use the number
            return str(num)

    def fix_toc_mismatches(
        self,
        cleaned_json: Dict[str, Any],
        dry_run: bool = False
    ) -> Tuple[Dict[str, Any], List[TOCFix]]:
        """
        Fix TOC/body mismatches by adding missing entries.

        Args:
            cleaned_json: Cleaned book JSON
            dry_run: If True, don't modify JSON, just return what would be done

        Returns:
            (modified_json, list of fixes applied)
        """
        fixes = []

        try:
            # Get TOC and chapters
            structure = cleaned_json.get('structure', {})
            front_matter = structure.get('front_matter', {})
            toc_data = front_matter.get('toc', [])

            if not toc_data or len(toc_data) == 0:
                logger.warning("No TOC found - cannot fix")
                return cleaned_json, fixes

            toc = toc_data[0]
            toc_entries = toc.get('entries', [])

            body = structure.get('body', {})
            chapters = body.get('chapters', [])

            if not chapters:
                logger.warning("No chapters found - cannot fix")
                return cleaned_json, fixes

            # Build lookup of existing TOC entries
            existing_toc_nums = {entry.get('chapter_number', 0) for entry in toc_entries}

            # Find missing chapters
            missing_chapters = []
            for chapter in chapters:
                ordinal = chapter.get('ordinal', 0)
                if ordinal not in existing_toc_nums:
                    missing_chapters.append(chapter)
                    logger.info(f"Found missing chapter from TOC: Ch {ordinal} - {chapter.get('title', 'Untitled')}")

            if not missing_chapters:
                logger.info("✓ No missing chapters - TOC is complete")
                return cleaned_json, fixes

            # Generate TOC entries for missing chapters
            new_entries = []
            for chapter in missing_chapters:
                ordinal = chapter.get('ordinal', 0)
                new_entry = self.generate_toc_entry(chapter, ordinal)
                new_entries.append(new_entry)

                fixes.append(TOCFix(
                    fix_type="add_entry",
                    chapter_number=ordinal,
                    chapter_title=chapter.get('title', ''),
                    chapter_id=chapter.get('id', ''),
                    position=-1  # Will be determined after sorting
                ))

            # Merge new entries with existing entries
            all_entries = toc_entries + new_entries

            # Sort by chapter number
            all_entries.sort(key=lambda e: e.get('chapter_number', 0))

            # Update position in fixes
            for fix in fixes:
                for i, entry in enumerate(all_entries):
                    if entry.get('chapter_number') == fix.chapter_number:
                        fix.position = i
                        break

            if not dry_run:
                # Update TOC in cleaned_json
                toc['entries'] = all_entries
                logger.info(f"✓ Added {len(new_entries)} missing TOC entries")
            else:
                logger.info(f"[DRY RUN] Would add {len(new_entries)} missing TOC entries")

            return cleaned_json, fixes

        except Exception as e:
            logger.error(f"Error fixing TOC mismatches: {e}")
            return cleaned_json, fixes

    def remove_extra_toc_entries(
        self,
        cleaned_json: Dict[str, Any],
        dry_run: bool = False
    ) -> Tuple[Dict[str, Any], List[TOCFix]]:
        """
        Remove TOC entries that reference non-existent chapters.

        Args:
            cleaned_json: Cleaned book JSON
            dry_run: If True, don't modify JSON, just return what would be done

        Returns:
            (modified_json, list of fixes applied)
        """
        fixes = []

        try:
            # Get TOC and chapters
            structure = cleaned_json.get('structure', {})
            front_matter = structure.get('front_matter', {})
            toc_data = front_matter.get('toc', [])

            if not toc_data or len(toc_data) == 0:
                return cleaned_json, fixes

            toc = toc_data[0]
            toc_entries = toc.get('entries', [])

            body = structure.get('body', {})
            chapters = body.get('chapters', [])

            if not chapters:
                return cleaned_json, fixes

            # Build lookup of chapter numbers
            valid_chapter_nums = {ch.get('ordinal', 0) for ch in chapters}

            # Find extra TOC entries
            valid_entries = []
            for i, entry in enumerate(toc_entries):
                chapter_num = entry.get('chapter_number', 0)

                if chapter_num in valid_chapter_nums:
                    valid_entries.append(entry)
                else:
                    logger.warning(f"Found extra TOC entry: Ch {chapter_num} - {entry.get('full_title', 'Unknown')}")
                    fixes.append(TOCFix(
                        fix_type="remove_entry",
                        chapter_number=chapter_num,
                        chapter_title=entry.get('full_title', ''),
                        chapter_id=entry.get('chapter_id', ''),
                        position=i
                    ))

            if not dry_run and fixes:
                # Update TOC with only valid entries
                toc['entries'] = valid_entries
                logger.info(f"✓ Removed {len(fixes)} extra TOC entries")
            elif dry_run and fixes:
                logger.info(f"[DRY RUN] Would remove {len(fixes)} extra TOC entries")

            return cleaned_json, fixes

        except Exception as e:
            logger.error(f"Error removing extra TOC entries: {e}")
            return cleaned_json, fixes

    def fix_file(
        self,
        input_path: Path,
        output_path: Optional[Path] = None,
        dry_run: bool = False,
        remove_extra: bool = False
    ) -> List[TOCFix]:
        """
        Fix TOC mismatches in a file.

        Args:
            input_path: Path to input JSON
            output_path: Path to output JSON (defaults to input_path)
            dry_run: If True, don't modify files
            remove_extra: If True, also remove extra TOC entries

        Returns:
            List of fixes applied
        """
        if output_path is None:
            output_path = input_path

        logger.info(f"{'[DRY RUN] ' if dry_run else ''}Fixing TOC in {input_path}")

        try:
            # Load JSON
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Apply fixes
            all_fixes = []

            # Add missing entries
            data, add_fixes = self.fix_toc_mismatches(data, dry_run=dry_run)
            all_fixes.extend(add_fixes)

            # Optionally remove extra entries
            if remove_extra:
                data, remove_fixes = self.remove_extra_toc_entries(data, dry_run=dry_run)
                all_fixes.extend(remove_fixes)

            # Save if not dry run
            if not dry_run and all_fixes:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                logger.info(f"✓ Saved fixed JSON to {output_path}")

            # Print summary
            add_count = sum(1 for f in all_fixes if f.fix_type == "add_entry")
            remove_count = sum(1 for f in all_fixes if f.fix_type == "remove_entry")

            logger.info(f"\nSummary: {add_count} added, {remove_count} removed")

            return all_fixes

        except Exception as e:
            logger.error(f"Error fixing file: {e}")
            return []


def main():
    """CLI testing"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python toc_auto_fix.py <input_json> [--dry-run] [--remove-extra] [--output output.json]")
        print("\nOptions:")
        print("  --dry-run        Don't modify files, just show what would be done")
        print("  --remove-extra   Also remove extra TOC entries (not in body)")
        print("  --output PATH    Output path (defaults to input path)")
        return 1

    input_path = Path(sys.argv[1])
    dry_run = '--dry-run' in sys.argv
    remove_extra = '--remove-extra' in sys.argv

    output_path = None
    if '--output' in sys.argv:
        output_idx = sys.argv.index('--output')
        if output_idx + 1 < len(sys.argv):
            output_path = Path(sys.argv[output_idx + 1])

    print(f"\n{'='*80}")
    print(f"TOC AUTO-FIX UTILITY")
    print(f"{'='*80}\n")

    fixer = TOCAutoFixer()
    fixes = fixer.fix_file(input_path, output_path, dry_run=dry_run, remove_extra=remove_extra)

    print(f"\n{'='*80}")
    print(f"✓ COMPLETE - {len(fixes)} fixes {'would be' if dry_run else 'were'} applied")
    print(f"{'='*80}\n")

    return 0


if __name__ == "__main__":
    exit(main())
