#!/usr/bin/env python3
"""
TOC Alignment Fixer
Automatically applies fixes suggested by TOC alignment validator
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass

from utils.toc_alignment_validator import TOCAlignmentValidator, AlignmentResult, AlignmentIssue

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class FixResult:
    """Result of applying TOC alignment fixes"""
    success: bool
    fixes_applied: int = 0
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class TOCAlignmentFixer:
    """Fix TOC alignment issues automatically"""

    def __init__(self):
        """Initialize the fixer"""
        self.validator = TOCAlignmentValidator()
        logger.info("TOC Alignment Fixer initialized")

    def fix_from_validation_result(
        self,
        json_data: Dict[str, Any],
        validation_result: AlignmentResult
    ) -> FixResult:
        """
        Apply fixes from a validation result.

        Args:
            json_data: The book JSON data
            validation_result: Result from TOCAlignmentValidator

        Returns:
            FixResult with number of fixes applied
        """
        logger.info("Applying TOC alignment fixes...")

        # Filter for error-level issues with suggested fixes
        fixable_issues = [
            issue for issue in validation_result.issues
            if issue.severity == "error" and issue.suggested_fix
        ]

        if not fixable_issues:
            logger.info("No fixable issues found")
            return FixResult(success=True, fixes_applied=0)

        logger.info(f"Found {len(fixable_issues)} fixable issues")

        # Extract TOC entries
        try:
            toc_data = json_data['structure']['front_matter']['toc']
            if not toc_data or len(toc_data) == 0:
                return FixResult(success=False, errors=["No TOC found"])

            toc_entries = toc_data[0]['entries']
        except (KeyError, IndexError) as e:
            return FixResult(success=False, errors=[f"Invalid TOC structure: {e}"])

        # Apply each fix
        fixes_applied = 0
        errors = []

        for issue in fixable_issues:
            try:
                # Validate the index
                if issue.toc_index < 0 or issue.toc_index >= len(toc_entries):
                    errors.append(f"Invalid TOC index: {issue.toc_index}")
                    continue

                # Get the current entry
                current_entry = toc_entries[issue.toc_index]

                # Verify it matches what we expect to fix
                if current_entry.get('full_title') != issue.toc_entry:
                    logger.warning(
                        f"TOC entry at index {issue.toc_index} has changed. "
                        f"Expected '{issue.toc_entry}', found '{current_entry.get('full_title')}'. "
                        f"Skipping fix."
                    )
                    continue

                # Apply the fix
                old_title = current_entry['full_title']
                current_entry['full_title'] = issue.suggested_fix

                # Also update chapter_title if it exists and needs updating
                # Extract chapter title from the fix (everything after the chapter number)
                if '　' in issue.suggested_fix:
                    parts = issue.suggested_fix.split('　', 1)
                    if len(parts) > 1:
                        # Get everything after the chapter number
                        new_chapter_title = '　'.join(parts[1:])
                        current_entry['chapter_title'] = new_chapter_title

                logger.info(f"Fixed TOC entry {issue.toc_index}: '{old_title}' → '{issue.suggested_fix}'")
                fixes_applied += 1

            except Exception as e:
                error_msg = f"Error fixing TOC entry {issue.toc_index}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

        logger.info(f"Applied {fixes_applied} fixes")

        return FixResult(
            success=True,
            fixes_applied=fixes_applied,
            errors=errors if errors else []
        )

    def fix_file(self, file_path: str, output_path: str = None) -> FixResult:
        """
        Validate and fix a JSON file.

        Args:
            file_path: Path to the JSON file
            output_path: Optional output path (defaults to overwriting input)

        Returns:
            FixResult
        """
        file_path = Path(file_path)
        if not file_path.exists():
            return FixResult(success=False, errors=[f"File not found: {file_path}"])

        # Load the file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
        except Exception as e:
            return FixResult(success=False, errors=[f"Error loading file: {e}"])

        # Validate to get issues
        logger.info(f"Validating {file_path.name}...")
        validation_result = self.validator.validate(json_data)

        if validation_result.is_valid:
            logger.info("File is already valid, no fixes needed")
            return FixResult(success=True, fixes_applied=0)

        # Apply fixes
        fix_result = self.fix_from_validation_result(json_data, validation_result)

        if not fix_result.success:
            return fix_result

        # Save the fixed file
        output_path = Path(output_path) if output_path else file_path

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved fixed file to {output_path}")
        except Exception as e:
            return FixResult(
                success=False,
                fixes_applied=fix_result.fixes_applied,
                errors=[f"Error saving file: {e}"]
            )

        # Validate again to confirm
        logger.info("Re-validating fixed file...")
        final_validation = self.validator.validate(json_data)

        if final_validation.is_valid:
            logger.info("✓ File is now valid!")
        else:
            logger.warning(
                f"File still has {len(final_validation.issues)} issues after fixes. "
                f"Some issues may require manual intervention."
            )

        return fix_result


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Fix TOC alignment issues")
    parser.add_argument(
        "input_file",
        help="Path to cleaned JSON file"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output path (defaults to overwriting input)"
    )

    args = parser.parse_args()

    fixer = TOCAlignmentFixer()
    result = fixer.fix_file(args.input_file, args.output)

    if result.success:
        print(f"\n✓ Success! Applied {result.fixes_applied} fixes")
        if result.errors:
            print(f"\nWarnings:")
            for error in result.errors:
                print(f"  - {error}")
        return 0
    else:
        print(f"\n✗ Failed to fix file")
        for error in result.errors:
            print(f"  - {error}")
        return 1


if __name__ == "__main__":
    exit(main())
