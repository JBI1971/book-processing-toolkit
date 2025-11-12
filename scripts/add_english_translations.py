#!/usr/bin/env python3
"""
Add English translations to existing cleaned JSON files from catalog database
"""
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.catalog_metadata import CatalogMetadataExtractor

def add_translations_to_file(json_file: Path, catalog_path: str) -> bool:
    """
    Add English translations to a single JSON file.

    Args:
        json_file: Path to cleaned JSON file
        catalog_path: Path to catalog database

    Returns:
        True if updated, False if skipped
    """
    # Get directory name (e.g., wuxia_0001)
    directory_name = json_file.parent.name

    # Load JSON
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"  ✗ Error loading {json_file.name}: {e}")
        return False

    # Check if already has English translations
    meta = data.get('meta', {})
    if meta.get('title_english') and meta.get('author_english'):
        return False  # Skip, already has translations

    # Get metadata from catalog
    extractor = CatalogMetadataExtractor(catalog_path)
    metadata = extractor.get_metadata_by_directory(directory_name)

    if not metadata:
        print(f"  ⚠ No catalog metadata for {directory_name}")
        return False

    # Add English translations if available
    updated = False
    if metadata.title_english and not meta.get('title_english'):
        data['meta']['title_english'] = metadata.title_english
        updated = True

    if metadata.author_english and not meta.get('author_english'):
        data['meta']['author_english'] = metadata.author_english
        updated = True

    if not updated:
        return False

    # Write back to file
    try:
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  ✓ Updated {json_file.name}")
        print(f"    - Title: {metadata.title_english}")
        print(f"    - Author: {metadata.author_english}")
        return True
    except Exception as e:
        print(f"  ✗ Error writing {json_file.name}: {e}")
        return False


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Add English translations to cleaned JSON files from catalog"
    )
    parser.add_argument(
        '--input-dir',
        required=True,
        help='Directory containing cleaned JSON files (e.g., 01_clean_json)'
    )
    parser.add_argument(
        '--catalog-path',
        required=True,
        help='Path to catalog database (wuxia_catalog.db)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Print what would be done without making changes'
    )

    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        print(f"Error: Input directory not found: {input_dir}")
        return 1

    catalog_path = Path(args.catalog_path)
    if not catalog_path.exists():
        print(f"Error: Catalog database not found: {catalog_path}")
        return 1

    print(f"Scanning {input_dir} for cleaned JSON files...")
    print(f"Using catalog: {catalog_path}")
    print()

    # Find all cleaned_*.json files
    json_files = list(input_dir.glob("*/cleaned_*.json"))
    print(f"Found {len(json_files)} JSON files")
    print()

    if args.dry_run:
        print("DRY RUN - No changes will be made")
        print()

    updated_count = 0
    skipped_count = 0

    for json_file in sorted(json_files):
        if args.dry_run:
            print(f"Would process: {json_file.parent.name}/{json_file.name}")
            skipped_count += 1
        else:
            if add_translations_to_file(json_file, str(catalog_path)):
                updated_count += 1
            else:
                skipped_count += 1

    print()
    print("=" * 60)
    print(f"Updated: {updated_count} files")
    print(f"Skipped: {skipped_count} files")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
