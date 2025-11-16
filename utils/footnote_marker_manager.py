#!/usr/bin/env python3
"""
Footnote Marker Manager Utility

Manages footnote markers in content, ensuring they are contiguous, unique,
and properly synchronized with the footnotes array.

This utility can be called from other scripts that need to clean up footnote markers.
"""

import re
import logging
from typing import Dict, Any, List, Tuple, Set

logger = logging.getLogger(__name__)


def extract_markers_from_content(content: str) -> List[int]:
    """
    Extract all footnote markers from content in order of appearance.

    Args:
        content: Text content with footnote markers like [1], [2], etc.

    Returns:
        List of marker numbers in order of appearance (may contain duplicates)
    """
    if not content:
        return []

    markers = []
    for match in re.finditer(r'\[(\d+)\]', content):
        markers.append(int(match.group(1)))

    return markers


def remove_duplicate_markers(content: str) -> Tuple[str, int]:
    """
    Remove duplicate footnote marker references, keeping only first occurrence.

    Args:
        content: Text content with footnote markers

    Returns:
        Tuple of (cleaned_content, num_duplicates_removed)
    """
    if not content:
        return content, 0

    seen_markers: Set[int] = set()
    result = []
    duplicates_removed = 0
    i = 0

    while i < len(content):
        # Check for marker pattern
        match = re.match(r'\[(\d+)\]', content[i:])
        if match:
            marker_num = int(match.group(1))
            if marker_num not in seen_markers:
                # Keep this marker (first occurrence)
                seen_markers.add(marker_num)
                result.append(match.group(0))
            else:
                # Skip this marker (duplicate)
                duplicates_removed += 1

            i += len(match.group(0))
        else:
            result.append(content[i])
            i += 1

    return ''.join(result), duplicates_removed


def renumber_markers_sequentially(content: str, old_to_new: Dict[int, int]) -> str:
    """
    Renumber footnote markers based on a mapping dictionary.

    Uses placeholder technique to avoid conflicts during replacement.

    Args:
        content: Text content with footnote markers
        old_to_new: Mapping of old marker numbers to new marker numbers

    Returns:
        Content with renumbered markers
    """
    if not content or not old_to_new:
        return content

    # Replace markers from highest to lowest to avoid conflicts
    for old_key in sorted(old_to_new.keys(), reverse=True):
        new_key = old_to_new[old_key]
        if old_key != new_key:
            pattern = r'\[' + str(old_key) + r'\]'
            placeholder = f'<<FOOTNOTE_{new_key}_PLACEHOLDER>>'
            content = re.sub(pattern, placeholder, content)

    # Replace placeholders with final markers
    for old_key, new_key in old_to_new.items():
        placeholder = f'<<FOOTNOTE_{new_key}_PLACEHOLDER>>'
        content = content.replace(placeholder, f'[{new_key}]')

    return content


def synchronize_markers_with_footnotes(
    content: str,
    footnotes: List[Dict[str, Any]],
    remove_duplicates: bool = True,
    max_iterations: int = 10
) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
    """
    Synchronize footnote markers in content with footnotes array.

    This function iterates up to max_iterations times to ensure:
    1. Markers are contiguous (1, 2, 3...)
    2. No duplicate markers (each footnote referenced only once)
    3. Markers match footnote keys
    4. Orphaned footnotes (without markers) are removed

    Args:
        content: Text content with footnote markers
        footnotes: List of footnote dictionaries with 'key' field
        remove_duplicates: If True, remove duplicate marker references
        max_iterations: Maximum number of cleanup iterations (default: 10)

    Returns:
        Tuple of (cleaned_content, cleaned_footnotes, stats)
        where stats contains:
            - iterations: Number of iterations performed
            - duplicates_removed: Number of duplicate markers removed
            - orphans_removed: Number of orphaned footnotes removed
            - final_marker_count: Final number of unique markers
    """
    stats = {
        'iterations': 0,
        'duplicates_removed': 0,
        'orphans_removed': 0,
        'final_marker_count': 0
    }

    if not content or not footnotes:
        return content, footnotes, stats

    for iteration in range(max_iterations):
        stats['iterations'] = iteration + 1

        # Step 1: Remove duplicate markers if requested
        if remove_duplicates:
            content, dups = remove_duplicate_markers(content)
            stats['duplicates_removed'] += dups

        # Step 2: Extract markers from content
        content_markers = extract_markers_from_content(content)

        if not content_markers:
            # No markers in content - remove all footnotes
            stats['orphans_removed'] += len(footnotes)
            footnotes = []
            break

        # Step 3: Build mapping for sequential renumbering
        # Track which old marker numbers appear in content
        unique_markers = []
        for marker in content_markers:
            if marker not in unique_markers:
                unique_markers.append(marker)

        old_to_new = {}
        for new_idx, old_marker in enumerate(unique_markers, 1):
            old_to_new[old_marker] = new_idx

        # Step 4: Renumber markers in content
        if old_to_new:
            content = renumber_markers_sequentially(content, old_to_new)

        # Step 5: Update footnote keys and remove orphans
        updated_footnotes = []
        for footnote in footnotes:
            old_key = footnote.get('key')
            if old_key in old_to_new:
                footnote['key'] = old_to_new[old_key]
                updated_footnotes.append(footnote)
            else:
                # Orphaned footnote - not in content
                stats['orphans_removed'] += 1

        footnotes = updated_footnotes

        # Step 6: Verify synchronization
        final_markers = extract_markers_from_content(content)
        footnote_keys = [fn.get('key') for fn in footnotes]

        # Check if synchronized
        if (
            final_markers == list(range(1, len(final_markers) + 1))  # Contiguous
            and len(final_markers) == len(set(final_markers))  # No duplicates
            and sorted(set(final_markers)) == sorted(footnote_keys)  # Match keys
        ):
            # Success! Fully synchronized
            stats['final_marker_count'] = len(final_markers)
            logger.debug(
                f"Synchronized in {stats['iterations']} iteration(s): "
                f"{stats['final_marker_count']} markers, "
                f"{stats['duplicates_removed']} duplicates removed, "
                f"{stats['orphans_removed']} orphans removed"
            )
            break

    else:
        # Max iterations reached without full synchronization
        logger.warning(
            f"Reached max iterations ({max_iterations}) without full synchronization"
        )
        stats['final_marker_count'] = len(extract_markers_from_content(content))

    return content, footnotes, stats


def cleanup_block_footnotes(
    block: Dict[str, Any],
    remove_duplicates: bool = True,
    max_iterations: int = 10
) -> Dict[str, Any]:
    """
    Clean up footnote markers in a content block.

    Processes both 'translated_content' and 'original_content' fields if present.

    Args:
        block: Content block dictionary with 'footnotes', 'translated_content', etc.
        remove_duplicates: If True, remove duplicate marker references
        max_iterations: Maximum cleanup iterations

    Returns:
        Statistics dictionary with cleanup results
    """
    total_stats = {
        'iterations': 0,
        'duplicates_removed': 0,
        'orphans_removed': 0,
        'final_marker_count': 0,
        'fields_processed': []
    }

    footnotes = block.get('footnotes', [])

    if not footnotes:
        return total_stats

    # Process translated_content
    if 'translated_content' in block and block['translated_content']:
        content, footnotes, stats = synchronize_markers_with_footnotes(
            block['translated_content'],
            footnotes,
            remove_duplicates=remove_duplicates,
            max_iterations=max_iterations
        )
        block['translated_content'] = content
        block['footnotes'] = footnotes

        total_stats['iterations'] = max(total_stats['iterations'], stats['iterations'])
        total_stats['duplicates_removed'] += stats['duplicates_removed']
        total_stats['orphans_removed'] += stats['orphans_removed']
        total_stats['final_marker_count'] = stats['final_marker_count']
        total_stats['fields_processed'].append('translated_content')

    # Process original_content
    if 'original_content' in block and block['original_content']:
        # Note: footnotes already updated from translated_content processing
        footnote_keys = [fn.get('key') for fn in footnotes]

        # Just need to update markers to match
        if footnote_keys:
            old_to_new = {key: key for key in footnote_keys}  # No remapping needed
            content = block['original_content']

            # Remove duplicates if requested
            if remove_duplicates:
                content, _ = remove_duplicate_markers(content)

            # Ensure markers match footnote keys
            markers = extract_markers_from_content(content)
            if markers:
                # Build mapping for any misaligned markers
                old_to_new = {}
                for marker in set(markers):
                    if marker in footnote_keys:
                        old_to_new[marker] = marker

                if old_to_new:
                    content = renumber_markers_sequentially(content, old_to_new)

            block['original_content'] = content
            total_stats['fields_processed'].append('original_content')

    return total_stats


def cleanup_all_blocks(
    data: Dict[str, Any],
    remove_duplicates: bool = True,
    max_iterations: int = 10
) -> Dict[str, Any]:
    """
    Clean up footnote markers in all content blocks.

    Args:
        data: Parsed JSON data with chapters and content_blocks
        remove_duplicates: If True, remove duplicate marker references
        max_iterations: Maximum cleanup iterations per block

    Returns:
        Summary statistics for all blocks
    """
    summary = {
        'total_blocks': 0,
        'blocks_processed': 0,
        'total_iterations': 0,
        'total_duplicates_removed': 0,
        'total_orphans_removed': 0,
        'total_markers': 0
    }

    chapters = data.get('structure', {}).get('body', {}).get('chapters', [])

    for chapter in chapters:
        for block in chapter.get('content_blocks', []):
            summary['total_blocks'] += 1

            if 'footnotes' in block and block['footnotes']:
                stats = cleanup_block_footnotes(
                    block,
                    remove_duplicates=remove_duplicates,
                    max_iterations=max_iterations
                )

                summary['blocks_processed'] += 1
                summary['total_iterations'] += stats['iterations']
                summary['total_duplicates_removed'] += stats['duplicates_removed']
                summary['total_orphans_removed'] += stats['orphans_removed']
                summary['total_markers'] += stats['final_marker_count']

    logger.info(
        f"Cleaned {summary['blocks_processed']}/{summary['total_blocks']} blocks: "
        f"{summary['total_markers']} markers, "
        f"{summary['total_duplicates_removed']} duplicates removed, "
        f"{summary['total_orphans_removed']} orphans removed"
    )

    return summary


if __name__ == '__main__':
    # Test the utility
    import json
    import sys

    if len(sys.argv) < 2:
        print("Usage: python footnote_marker_manager.py <json_file>")
        sys.exit(1)

    input_file = sys.argv[1]

    logging.basicConfig(level=logging.INFO)

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    stats = cleanup_all_blocks(data, remove_duplicates=True, max_iterations=10)

    print("\n=== CLEANUP SUMMARY ===")
    print(f"Total blocks: {stats['total_blocks']}")
    print(f"Blocks processed: {stats['blocks_processed']}")
    print(f"Total iterations: {stats['total_iterations']}")
    print(f"Duplicates removed: {stats['total_duplicates_removed']}")
    print(f"Orphans removed: {stats['total_orphans_removed']}")
    print(f"Final marker count: {stats['total_markers']}")

    # Save updated file
    output_file = input_file.replace('.json', '_markers_cleaned.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\nSaved to: {output_file}")
