#!/usr/bin/env python3
"""
Script to remove sys.path.insert() hacks from all Python files.

This is part of the Subsystem 2 refactoring to use proper package imports.
"""

import re
from pathlib import Path
from typing import List, Tuple

# Files that need updating
FILES_TO_UPDATE = [
    "cli/clean.py",
    "cli/structure.py",
    "cli/validate_structure.py",
    "processors/book_translator.py",
    "processors/translator.py",
    "processors/volume_manager.py",
    "processors/json_cleaner.py",
    "scripts/batch_translate_works.py",
    "scripts/batch_process_books.py",
    "scripts/add_english_translations.py",
    "scripts/verify_api_key.py",
    "scripts/list_works.py",
    "scripts/demo_glossary_matching.py",
    "scripts/translate_work.py",
    "scripts/find_consensus_translations.py",
    "scripts/translate_chapters_limit.py",
    "scripts/autonomous_test_and_fix.py",
    "scripts/demo_glossary_simple.py",
    "web_ui/backend/api/analysis.py",
    "web_ui/translation_manager/backend/app.py",
]


def remove_sys_path_hack(content: str) -> Tuple[str, bool]:
    """
    Remove sys.path.insert() statements and unused Path imports.

    Returns:
        Tuple of (updated_content, was_modified)
    """
    original = content

    # Pattern 1: Remove sys.path.insert line and comment
    content = re.sub(
        r'# Add parent directory to path.*?\n.*?sys\.path\.insert\(.*?\)\n',
        '',
        content,
        flags=re.DOTALL
    )

    # Pattern 2: Remove just sys.path.insert line without comment
    content = re.sub(
        r'sys\.path\.insert\(.*?\)\n',
        '',
        content
    )

    # If Path is no longer used after removing sys.path.insert, remove it from imports
    if 'from pathlib import Path' in content and 'Path(' not in content.replace('from pathlib import Path', ''):
        # Remove standalone "from pathlib import Path" line
        content = re.sub(r'from pathlib import Path\n', '', content)

        # Or remove Path from multi-imports
        content = re.sub(
            r'(from pathlib import .*?), Path([,\)])',
            r'\1\2',
            content
        )
        content = re.sub(
            r'(from pathlib import )Path, (.*)',
            r'\1\2',
            content
        )

    return content, content != original


def main():
    """Remove sys.path hacks from all files."""
    project_root = Path(__file__).parent.parent
    updated_files = []
    skipped_files = []

    for file_path in FILES_TO_UPDATE:
        full_path = project_root / file_path

        if not full_path.exists():
            print(f"⚠️  Skipped (not found): {file_path}")
            skipped_files.append(file_path)
            continue

        # Read file
        content = full_path.read_text()

        # Remove sys.path hack
        updated_content, was_modified = remove_sys_path_hack(content)

        if was_modified:
            # Write back
            full_path.write_text(updated_content)
            print(f"✅ Updated: {file_path}")
            updated_files.append(file_path)
        else:
            print(f"⏭️  No changes: {file_path}")

    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Updated: {len(updated_files)} files")
    print(f"  Skipped: {len(skipped_files)} files")
    print(f"  No changes: {len(FILES_TO_UPDATE) - len(updated_files) - len(skipped_files)} files")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
