# Test Folder Cleanup Script Documentation

## Overview

`cleanup_test_folders.py` is a safety-focused script for cleaning up test output directories while ensuring source data is never deleted.

**Location:** `/Users/jacki/PycharmProjects/agentic_test_project/scripts/cleanup_test_folders.py`

## Purpose

Clean up test output folders and temporary files generated during testing, freeing disk space while maintaining multiple layers of protection against accidentally deleting source data.

## Safety Features

### 1. Protected Paths List
Hard-coded list of paths that must NEVER be deleted:
- `/Users/jacki/project_files/translation_project/wuxia_individual_files`
- Any subdirectories under protected paths

### 2. Keyword Protection
Paths containing these keywords are automatically blocked:
- `wuxia_individual_files`
- `source_files`
- `source_data`
- `original_data`
- `raw_data`

### 3. Source Indicator Detection
Paths ending with these patterns are blocked:
- `_individual_files`
- `_source`
- `_original`
- `_raw`

### 4. Multi-Level Safety Checks
1. Initial protected path verification
2. Per-file safety check before scanning
3. Final safety check before deletion
4. Explicit user confirmation required

### 5. Dry-Run Default
Script runs in safe preview mode by default unless `--confirm` is provided.

## Cleanup Targets

### Test Output Directories
- `/Users/jacki/project_files/translation_project/test_cleaned_json_v2/*`
  - Subdirectories (test runs)
  - Loose files (.json, .DS_Store)

### Log Directories
- `/Users/jacki/PycharmProjects/agentic_test_project/logs/*`
  - Batch reports (*.json)
  - Summary files (*.md)
  - Log subdirectories

### Temporary Test Files
Project root files matching patterns:
- `test_*.log`
- `test_*.json`
- `test_*_run.log`
- `test_*_fixed.log`
- `test_output.log`

## Usage

### Basic Commands

```bash
# Preview what would be deleted (SAFE - no actual deletion)
python scripts/cleanup_test_folders.py --dry-run

# Same as above (dry-run is default)
python scripts/cleanup_test_folders.py

# Actually delete files (requires confirmation)
python scripts/cleanup_test_folders.py --confirm

# Keep the latest 2 test runs and logs
python scripts/cleanup_test_folders.py --confirm --keep-latest 2

# Keep latest 5 test runs
python scripts/cleanup_test_folders.py --confirm --keep-latest 5
```

### Advanced Options

```bash
# Skip protected path verification (not recommended)
python scripts/cleanup_test_folders.py --skip-verification

# Get help
python scripts/cleanup_test_folders.py --help
```

## Output Examples

### Dry-Run Mode (Default)

```
================================================================================
TEST FOLDER CLEANUP SCRIPT
================================================================================

Started at: 2025-11-10 12:38:31

================================================================================
PROTECTED PATHS VERIFICATION
================================================================================

OK: /Users/jacki/project_files/translation_project/wuxia_individual_files
  Status: EXISTS, Size: 3.70 GB

Scanning test output directories...
  Found 7 test runs

Scanning log directories...
  Found 45 log files

================================================================================
CLEANUP PLAN
================================================================================

Test output directory: (7 items)
  /Users/jacki/project_files/translation_project/test_cleaned_json_v2/test_15_random
    Size: 39.95 MB
  ...

Total items: 66
Total space to be freed: 100.93 MB

================================================================================
CLEANUP EXECUTION
================================================================================

WARNING: DRY RUN MODE - No files will be deleted

[DRY RUN] Would delete: /path/to/test_folder
  Type: Test output directory, Size: 39.95 MB
  ...

Summary:
  Successfully deleted: 66
  Failed: 0
  Total space freed: 100.93 MB

To actually delete these files, run with --confirm flag:
  python scripts/cleanup_test_folders.py --confirm
```

### Confirmation Mode

When running with `--confirm`, you must type 'DELETE' to proceed:

```bash
$ python scripts/cleanup_test_folders.py --confirm

...

WARNING: YOU ARE ABOUT TO DELETE FILES!
WARNING: Total: 66 items, 100.93 MB

Type 'DELETE' to confirm deletion: DELETE

================================================================================
CLEANUP EXECUTION
================================================================================

Deleted directory: /path/to/test_folder
  Size freed: 39.95 MB
  ...

Summary:
  Successfully deleted: 66
  Failed: 0
  Total space freed: 100.93 MB

Cleanup completed successfully!
```

## Safety Testing

A companion test script verifies all safety checks work correctly:

```bash
# Run safety check tests
python scripts/test_cleanup_safety.py
```

Expected output:
```
Testing Cleanup Script Safety Checks

Running 10 safety check tests...

PASS | Exact match with protected source directory
PASS | Subdirectory of protected path
PASS | Contains protected keyword 'wuxia_individual_files'
...

Test Summary:
  Passed: 10/10
  Failed: 0/10

All safety checks passed!
```

## What Gets Deleted vs. Protected

### ✅ SAFE TO DELETE (Test Output)
- Test output directories in `test_cleaned_json_v2/`
- Log files in `logs/` directory
- Temporary test files (`test_*.log`, `test_*.json`)
- Validation reports
- Batch processing reports

### ❌ NEVER DELETED (Source Data)
- `/Users/jacki/project_files/translation_project/wuxia_individual_files/`
- Any subdirectory of protected paths
- Any path containing "wuxia_individual_files"
- Any path ending with "_individual_files"
- Production code files
- Configuration files

## Error Handling

### Protected Path Detected
If a protected path is encountered during scanning or deletion:

```
ERROR: PROTECTED (skipping): /path/containing/wuxia_individual_files
  Reason: Path contains protected keyword: 'wuxia_individual_files'
```

The script will skip this path and continue with other files.

### Safety Abort During Deletion
If a path passes initial checks but fails the final safety check:

```
SAFETY ABORT: /some/suspicious/path
  Reason: Path contains protected keyword: 'source_files'
```

The script increments the failed count and continues.

## Use Cases

### After Running Tests
```bash
# Clean up after testing, but keep the latest run for reference
python scripts/cleanup_test_folders.py --confirm --keep-latest 1
```

### Weekly Cleanup
```bash
# Remove all old test outputs (keeps nothing)
python scripts/cleanup_test_folders.py --confirm
```

### Before Major Testing
```bash
# Preview space that will be freed
python scripts/cleanup_test_folders.py --dry-run

# Clean everything if satisfied
python scripts/cleanup_test_folders.py --confirm
```

### Conservative Cleanup
```bash
# Keep the latest 5 test runs for comparison
python scripts/cleanup_test_folders.py --confirm --keep-latest 5
```

## Best Practices

1. **Always preview first:** Run with `--dry-run` (or no flags) to see what will be deleted
2. **Use --keep-latest for safety:** Keep at least 1-2 recent test runs
3. **Verify protected paths:** The script verifies protected paths exist at startup
4. **Check the summary:** Review the cleanup plan before confirming
5. **Read error messages:** If paths are blocked, there's a good reason

## Technical Details

### Directory Size Calculation
- Recursively walks directories to calculate total size
- Handles permission errors gracefully
- Formats output in human-readable units (B, KB, MB, GB)

### File Sorting for --keep-latest
- Sorts files/directories by modification time (oldest first)
- Keeps the N most recent items
- Applies separately to test runs and log files

### Color Coding
- 🔴 RED: Errors, dangerous operations
- 🟢 GREEN: Success, safe operations
- 🟡 YELLOW: Warnings, logs
- 🔵 BLUE: Information
- 🟣 MAGENTA: Directories
- 🔵 CYAN: Headers, files

## Troubleshooting

### "Nothing to clean up"
- All test directories are empty or already cleaned
- Check if paths in script match your actual directory structure

### Protected path doesn't exist
- Script continues anyway (just a warning)
- Verify path in PROTECTED_PATHS list is correct

### Permission denied errors
- Some files may be locked or require sudo
- Script logs these as failures but continues

### Want to clean different directories?
Edit these constants in the script:
- `TEST_OUTPUT_DIRS` - Test output locations
- `LOG_DIRS` - Log file locations
- `TEMP_FILE_PATTERNS` - Temporary file patterns

## Integration with Project

This script is part of the Book Processing Toolkit project and complements the testing workflow:

1. Run tests → Generate output in `test_cleaned_json_v2/` and `logs/`
2. Review results
3. Clean up → Use this script to free space
4. Repeat

## Security Notes

- Script does NOT require elevated permissions
- Only deletes files/directories in specified locations
- Multiple safety layers prevent accidental source data deletion
- Explicit confirmation required for deletion
- All actions are logged to stdout

## Version History

- **v1.0** (2025-11-10): Initial release with multi-layer safety checks

## Support

For issues or questions:
1. Review this documentation
2. Run the safety test: `python scripts/test_cleanup_safety.py`
3. Check the script source code for detailed comments
4. Test with `--dry-run` first

---

**Remember: When in doubt, use --dry-run first!**
