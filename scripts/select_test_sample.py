#!/usr/bin/env python3
"""
Sample Selection Script for JSON Book Restructurer Testing

Selects a random sample of books for testing:
- 3 works with 2+ volumes (process first 2 volumes of each)
- 7 single-volume works

Output: JSON file with selected works and their file paths
"""

import json
import random
from pathlib import Path
from typing import List, Dict, Tuple
import argparse


def analyze_source_directory(source_dir: Path) -> Tuple[List[Dict], List[Dict]]:
    """
    Analyze source directory to identify single-volume and multi-volume works.

    Returns:
        Tuple of (single_volume_works, multi_volume_works)
        Each work is a dict with: {directory, files, volume_count}
    """
    single_volume = []
    multi_volume = []

    # Iterate through all subdirectories
    for subdir in sorted(source_dir.iterdir()):
        if not subdir.is_dir() or subdir.name.startswith('.'):
            continue

        # Find book JSON files (I*.json or D*.json)
        book_files = []
        for pattern in ['I*.json', 'D*.json']:
            book_files.extend(list(subdir.glob(pattern)))

        if not book_files:
            continue

        # Extract volume information from filenames
        volumes = []
        for book_file in book_files:
            # Extract volume letter from filename (e.g., D55a, D55b)
            # Volume letter is the last character before underscore in work ID
            parts = book_file.stem.split('_')
            if parts:
                work_id = parts[0]
                # Check if last char is a letter (volume indicator)
                if work_id and work_id[-1].isalpha() and work_id[-1].lower() not in ['d', 'i']:
                    volume = work_id[-1]
                else:
                    volume = None
                volumes.append({
                    'file': book_file,
                    'volume': volume,
                    'work_id': work_id
                })

        work_info = {
            'directory': subdir.name,
            'path': str(subdir),
            'files': volumes,
            'volume_count': len(volumes)
        }

        if len(volumes) > 1:
            multi_volume.append(work_info)
        else:
            single_volume.append(work_info)

    return single_volume, multi_volume


def select_sample(single_volume: List[Dict], multi_volume: List[Dict],
                  num_multi: int = 3, num_single: int = 7,
                  seed: int = None) -> Dict:
    """
    Select random sample of works for testing.

    Args:
        single_volume: List of single-volume works
        multi_volume: List of multi-volume works
        num_multi: Number of multi-volume works to select (default: 3)
        num_single: Number of single-volume works to select (default: 7)
        seed: Random seed for reproducibility

    Returns:
        Dict with selected works and metadata
    """
    if seed is not None:
        random.seed(seed)

    # Ensure we have enough works
    if len(multi_volume) < num_multi:
        print(f"Warning: Only {len(multi_volume)} multi-volume works available, "
              f"requested {num_multi}")
        num_multi = len(multi_volume)

    if len(single_volume) < num_single:
        print(f"Warning: Only {len(single_volume)} single-volume works available, "
              f"requested {num_single}")
        num_single = len(single_volume)

    # Random selection
    selected_multi = random.sample(multi_volume, num_multi)
    selected_single = random.sample(single_volume, num_single)

    # For multi-volume works, select only first 2 volumes
    for work in selected_multi:
        if work['volume_count'] > 2:
            # Sort volumes alphabetically and take first 2
            # Handle None volumes by treating them as empty string
            work['files'] = sorted(work['files'],
                                  key=lambda x: x.get('volume') or '')[:2]
            work['selected_volumes'] = 2
        else:
            work['selected_volumes'] = work['volume_count']

    return {
        'metadata': {
            'total_single_available': len(single_volume),
            'total_multi_available': len(multi_volume),
            'selected_single': num_single,
            'selected_multi': num_multi,
            'seed': seed
        },
        'multi_volume_works': selected_multi,
        'single_volume_works': selected_single,
        'total_files_to_process': sum(w['selected_volumes'] for w in selected_multi) + num_single
    }


def main():
    parser = argparse.ArgumentParser(
        description='Select random sample of books for restructurer testing'
    )
    parser.add_argument(
        '--source-dir',
        type=Path,
        default=Path('/Users/jacki/project_files/translation_project/wuxia_individual_files'),
        help='Source directory containing book subdirectories'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('./test_sample_selection.json'),
        help='Output JSON file with selected sample'
    )
    parser.add_argument(
        '--num-multi',
        type=int,
        default=3,
        help='Number of multi-volume works to select (default: 3)'
    )
    parser.add_argument(
        '--num-single',
        type=int,
        default=7,
        help='Number of single-volume works to select (default: 7)'
    )
    parser.add_argument(
        '--seed',
        type=int,
        help='Random seed for reproducibility'
    )

    args = parser.parse_args()

    print(f"Analyzing source directory: {args.source_dir}")
    single_volume, multi_volume = analyze_source_directory(args.source_dir)

    print(f"\nFound:")
    print(f"  - {len(single_volume)} single-volume works")
    print(f"  - {len(multi_volume)} multi-volume works")

    print(f"\nSelecting sample:")
    print(f"  - {args.num_multi} multi-volume works (first 2 volumes each)")
    print(f"  - {args.num_single} single-volume works")
    if args.seed:
        print(f"  - Using random seed: {args.seed}")

    sample = select_sample(single_volume, multi_volume,
                          args.num_multi, args.num_single, args.seed)

    # Save to file
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(sample, f, ensure_ascii=False, indent=2, default=str)

    print(f"\nSample selection saved to: {args.output}")
    print(f"Total files to process: {sample['total_files_to_process']}")

    # Print summary
    print("\n=== MULTI-VOLUME WORKS ===")
    for work in sample['multi_volume_works']:
        print(f"\n{work['directory']}:")
        for file_info in work['files']:
            print(f"  - {Path(file_info['file']).name}")

    print("\n=== SINGLE-VOLUME WORKS ===")
    for work in sample['single_volume_works']:
        print(f"\n{work['directory']}:")
        for file_info in work['files']:
            print(f"  - {Path(file_info['file']).name}")

    return 0


if __name__ == "__main__":
    exit(main())
