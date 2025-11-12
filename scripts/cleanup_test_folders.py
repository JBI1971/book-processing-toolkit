#!/usr/bin/env python3
"""
Test Folder Cleanup Script

Purpose: Clean up test output folders while NEVER touching source data

CRITICAL SAFETY: This script has multiple layers of protection to ensure
the source data folder is NEVER deleted.

Usage:
    # Preview what would be deleted (safe, no actual deletion)
    python scripts/cleanup_test_folders.py --dry-run

    # Delete old test outputs (requires confirmation)
    python scripts/cleanup_test_folders.py --confirm

    # Keep last N test runs
    python scripts/cleanup_test_folders.py --confirm --keep-latest 2
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

# ANSI color codes for terminal output
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    RESET = '\033[0m'


# ============================================================================
# CRITICAL SAFETY CONFIGURATION
# ============================================================================

# PROTECTED PATHS: These paths must NEVER be deleted
PROTECTED_PATHS = [
    "/Users/jacki/project_files/translation_project/wuxia_individual_files",
    "/Users/jacki/project_files/translation_project/wuxia_individual_files/",
]

# Additional safety keywords - if a path contains any of these, ABORT
PROTECTED_KEYWORDS = [
    "wuxia_individual_files",
    "source_files",
    "source_data",
    "original_data",
    "raw_data",
]

# Source folder indicators - if path ends with these, likely a source folder
SOURCE_INDICATORS = [
    "_individual_files",
    "_source",
    "_original",
    "_raw",
]


# ============================================================================
# CLEANUP TARGETS
# ============================================================================

# Test output directories to clean
TEST_OUTPUT_DIRS = [
    "/Users/jacki/project_files/translation_project/test_cleaned_json_v2",
]

# Log directories to clean
LOG_DIRS = [
    "/Users/jacki/PycharmProjects/agentic_test_project/logs",
]

# Project root for temporary test files
PROJECT_ROOT = "/Users/jacki/PycharmProjects/agentic_test_project"

# Patterns for temporary test files in project root
TEMP_FILE_PATTERNS = [
    "test_*.log",
    "test_*.json",
    "test_*_run.log",
    "test_*_fixed.log",
    "test_output.log",
]


# ============================================================================
# SAFETY CHECK FUNCTIONS
# ============================================================================

def is_path_protected(path: Path) -> Tuple[bool, str]:
    """
    Check if a path is protected from deletion.

    Returns:
        (is_protected, reason) - Boolean and explanation string
    """
    path_str = str(path.resolve())

    # Check 1: Exact match with protected paths
    for protected in PROTECTED_PATHS:
        protected_path = Path(protected).resolve()
        if path.resolve() == protected_path:
            return True, f"Exact match with protected path: {protected}"
        # Check if path is under a protected directory
        try:
            path.resolve().relative_to(protected_path)
            return True, f"Path is under protected directory: {protected}"
        except ValueError:
            pass  # Not under this protected path

    # Check 2: Contains protected keywords
    for keyword in PROTECTED_KEYWORDS:
        if keyword in path_str:
            return True, f"Path contains protected keyword: '{keyword}'"

    # Check 3: Ends with source indicators
    for indicator in SOURCE_INDICATORS:
        if path_str.endswith(indicator) or path_str.endswith(indicator + "/"):
            return True, f"Path ends with source indicator: '{indicator}'"

    return False, ""


def get_directory_size(path: Path) -> int:
    """Calculate total size of directory in bytes."""
    if not path.exists():
        return 0

    if path.is_file():
        return path.stat().st_size

    total = 0
    try:
        for item in path.rglob('*'):
            if item.is_file():
                total += item.stat().st_size
    except PermissionError:
        pass
    return total


def format_size(bytes: int) -> str:
    """Format bytes as human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes < 1024.0:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.2f} PB"


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 80}{Colors.RESET}\n")


def print_warning(text: str):
    """Print a warning message."""
    print(f"{Colors.YELLOW}WARNING: {text}{Colors.RESET}")


def print_error(text: str):
    """Print an error message."""
    print(f"{Colors.RED}ERROR: {text}{Colors.RESET}")


def print_success(text: str):
    """Print a success message."""
    print(f"{Colors.GREEN}{text}{Colors.RESET}")


def print_info(text: str):
    """Print an info message."""
    print(f"{Colors.BLUE}{text}{Colors.RESET}")


# ============================================================================
# CLEANUP LOGIC
# ============================================================================

def find_cleanup_targets(keep_latest: int = 0) -> List[Tuple[Path, str, int]]:
    """
    Find all files and directories to clean up.

    Args:
        keep_latest: Number of latest test runs to keep

    Returns:
        List of (path, description, size_bytes) tuples
    """
    targets = []

    # 1. Test output directories
    print_info("Scanning test output directories...")
    for test_dir in TEST_OUTPUT_DIRS:
        test_path = Path(test_dir)
        if not test_path.exists():
            print(f"  Skipping non-existent: {test_dir}")
            continue

        # Find subdirectories (test runs)
        subdirs = [d for d in test_path.iterdir() if d.is_dir()]

        # Sort by modification time (oldest first)
        subdirs.sort(key=lambda p: p.stat().st_mtime)

        # Keep the latest N subdirectories
        if keep_latest > 0 and len(subdirs) > keep_latest:
            subdirs_to_clean = subdirs[:-keep_latest]
            print(f"  Found {len(subdirs)} test runs, keeping latest {keep_latest}")
        else:
            subdirs_to_clean = subdirs
            print(f"  Found {len(subdirs)} test runs")

        for subdir in subdirs_to_clean:
            # SAFETY CHECK
            is_protected, reason = is_path_protected(subdir)
            if is_protected:
                print_error(f"  PROTECTED (skipping): {subdir}")
                print_error(f"    Reason: {reason}")
                continue

            size = get_directory_size(subdir)
            targets.append((subdir, f"Test output directory", size))

        # Find loose files in test_cleaned_json_v2 root
        loose_files = [f for f in test_path.iterdir() if f.is_file()]
        for file in loose_files:
            size = file.stat().st_size
            targets.append((file, f"Test output file", size))

    # 2. Log directories
    print_info("\nScanning log directories...")
    for log_dir in LOG_DIRS:
        log_path = Path(log_dir)
        if not log_path.exists():
            print(f"  Skipping non-existent: {log_dir}")
            continue

        # Find log files
        log_files = list(log_path.glob("*.json")) + list(log_path.glob("*.log")) + list(log_path.glob("*.md"))

        # Sort by modification time (oldest first)
        log_files.sort(key=lambda p: p.stat().st_mtime)

        # Keep the latest N log files
        if keep_latest > 0 and len(log_files) > keep_latest:
            logs_to_clean = log_files[:-keep_latest]
            print(f"  Found {len(log_files)} log files, keeping latest {keep_latest}")
        else:
            logs_to_clean = log_files
            print(f"  Found {len(log_files)} log files")

        for log_file in logs_to_clean:
            size = log_file.stat().st_size
            targets.append((log_file, f"Log file", size))

        # Also check for log subdirectories
        log_subdirs = [d for d in log_path.iterdir() if d.is_dir()]
        for subdir in log_subdirs:
            size = get_directory_size(subdir)
            targets.append((subdir, f"Log subdirectory", size))

    # 3. Temporary test files in project root
    print_info("\nScanning project root for temporary test files...")
    project_path = Path(PROJECT_ROOT)
    for pattern in TEMP_FILE_PATTERNS:
        matching_files = list(project_path.glob(pattern))
        print(f"  Pattern '{pattern}': found {len(matching_files)} files")
        for file in matching_files:
            if file.is_file():
                size = file.stat().st_size
                targets.append((file, f"Temporary test file", size))

    return targets


def display_cleanup_plan(targets: List[Tuple[Path, str, int]]):
    """Display what will be cleaned up."""
    print_header("CLEANUP PLAN")

    if not targets:
        print_info("No files or directories to clean up.")
        return 0

    total_size = 0

    # Group by type
    by_type = {}
    for path, desc, size in targets:
        if desc not in by_type:
            by_type[desc] = []
        by_type[desc].append((path, size))
        total_size += size

    # Display by type
    for desc, items in by_type.items():
        print(f"{Colors.BOLD}{desc}:{Colors.RESET} ({len(items)} items)")
        for path, size in items:
            # Color code by type
            if "directory" in desc.lower():
                color = Colors.MAGENTA
            elif "log" in desc.lower():
                color = Colors.YELLOW
            else:
                color = Colors.CYAN

            print(f"  {color}{path}{Colors.RESET}")
            print(f"    Size: {format_size(size)}")
        print()

    print(f"{Colors.BOLD}Total items:{Colors.RESET} {len(targets)}")
    print(f"{Colors.BOLD}Total space to be freed:{Colors.RESET} {Colors.GREEN}{format_size(total_size)}{Colors.RESET}")

    return total_size


def perform_cleanup(targets: List[Tuple[Path, str, int]], dry_run: bool = True) -> int:
    """
    Perform the actual cleanup.

    Args:
        targets: List of (path, description, size) tuples
        dry_run: If True, only simulate deletion

    Returns:
        Number of items successfully deleted
    """
    if not targets:
        return 0

    print_header("CLEANUP EXECUTION")

    if dry_run:
        print_warning("DRY RUN MODE - No files will be deleted\n")

    deleted_count = 0
    failed_count = 0
    total_freed = 0

    for path, desc, size in targets:
        # Final safety check before deletion
        is_protected, reason = is_path_protected(path)
        if is_protected:
            print_error(f"SAFETY ABORT: {path}")
            print_error(f"  Reason: {reason}")
            failed_count += 1
            continue

        try:
            if dry_run:
                print(f"{Colors.CYAN}[DRY RUN]{Colors.RESET} Would delete: {path}")
                print(f"  Type: {desc}, Size: {format_size(size)}")
                deleted_count += 1
                total_freed += size
            else:
                if path.is_dir():
                    shutil.rmtree(path)
                    print_success(f"Deleted directory: {path}")
                else:
                    path.unlink()
                    print_success(f"Deleted file: {path}")
                print(f"  Size freed: {format_size(size)}")
                deleted_count += 1
                total_freed += size
        except Exception as e:
            print_error(f"Failed to delete {path}: {e}")
            failed_count += 1

    print()
    print(f"{Colors.BOLD}Summary:{Colors.RESET}")
    print(f"  Successfully deleted: {Colors.GREEN}{deleted_count}{Colors.RESET}")
    print(f"  Failed: {Colors.RED}{failed_count}{Colors.RESET}")
    print(f"  Total space freed: {Colors.GREEN}{format_size(total_freed)}{Colors.RESET}")

    return deleted_count


def verify_protected_paths():
    """Verify that protected paths exist and print their status."""
    print_header("PROTECTED PATHS VERIFICATION")

    all_exist = True
    for protected in PROTECTED_PATHS:
        path = Path(protected)
        if path.exists():
            size = get_directory_size(path)
            print_success(f"OK: {protected}")
            print(f"  Status: EXISTS, Size: {format_size(size)}")
        else:
            print_warning(f"Path does not exist: {protected}")
            all_exist = False

    return all_exist


# ============================================================================
# MAIN FUNCTION
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Clean up test output folders with multiple safety checks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview what would be deleted (safe)
  python scripts/cleanup_test_folders.py --dry-run

  # Delete old test outputs (requires confirmation)
  python scripts/cleanup_test_folders.py --confirm

  # Keep last 2 test runs
  python scripts/cleanup_test_folders.py --confirm --keep-latest 2

Safety Features:
  - Protected paths list (source data never deleted)
  - Keyword matching (blocks paths with "wuxia_individual_files")
  - Source indicator detection (blocks paths ending with "_individual_files")
  - Explicit confirmation required for deletion
  - Dry-run mode by default
  - Detailed logging of all actions
        """
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview what would be deleted without actually deleting (default mode)'
    )

    parser.add_argument(
        '--confirm',
        action='store_true',
        help='Actually perform deletion (requires explicit confirmation)'
    )

    parser.add_argument(
        '--keep-latest',
        type=int,
        default=0,
        metavar='N',
        help='Keep the N most recent test runs/logs (default: 0, clean all)'
    )

    parser.add_argument(
        '--skip-verification',
        action='store_true',
        help='Skip protected paths verification check'
    )

    args = parser.parse_args()

    # Print script header
    print_header("TEST FOLDER CLEANUP SCRIPT")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Verify protected paths exist
    if not args.skip_verification:
        if not verify_protected_paths():
            print_warning("\nSome protected paths do not exist. Continuing anyway...")

    # Find cleanup targets
    print()
    targets = find_cleanup_targets(keep_latest=args.keep_latest)

    # Display cleanup plan
    print()
    total_size = display_cleanup_plan(targets)

    if not targets:
        print_info("\nNothing to clean up. Exiting.")
        return 0

    # Determine mode
    if args.confirm and not args.dry_run:
        # Actual deletion mode - require explicit confirmation
        print()
        print_warning("YOU ARE ABOUT TO DELETE FILES!")
        print_warning(f"Total: {len(targets)} items, {format_size(total_size)}")
        print()
        response = input(f"{Colors.RED}Type 'DELETE' to confirm deletion: {Colors.RESET}")

        if response != 'DELETE':
            print_error("\nDeletion cancelled. Exiting.")
            return 1

        # Perform actual cleanup
        deleted = perform_cleanup(targets, dry_run=False)

        if deleted > 0:
            print()
            print_success("Cleanup completed successfully!")

        return 0
    else:
        # Dry run mode (default)
        print()
        if not args.dry_run and not args.confirm:
            print_info("No --confirm flag provided. Running in DRY RUN mode.")

        perform_cleanup(targets, dry_run=True)

        print()
        print_info("To actually delete these files, run with --confirm flag:")
        print_info("  python scripts/cleanup_test_folders.py --confirm")

        return 0


if __name__ == "__main__":
    sys.exit(main())
