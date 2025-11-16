# Output File Locations - Strategy and Configuration

**Date**: 2025-11-16
**Status**: Implemented

---

## Strategy: Option 1 - Symlink for Logs (RECOMMENDED)

We use a hybrid approach where:
- **Logs** are stored in `translation_data/logs` (accessible from both projects via symlink)
- **WIP files** stay in translation_project (local, not shared)
- **Final outputs** stay in translation_project (local, not shared)

---

## Directory Structure

### agentic_test_project/ (Development Project)
```
/Users/jacki/PycharmProjects/agentic_test_project/
├── translation_data → /Users/jacki/project_files/translation_project/translation_data
│   └── logs/                          # SYMLINK - points to translation_project
│       ├── checkpoints/               # Translation checkpoints
│       │   └── D1379_checkpoint.json
│       ├── D1379_translation.log      # Translation logs
│       └── *_character_cleanup_log.json  # Cleanup logs
├── processors/                        # Core translation logic
├── utils/                             # Utility functions
├── scripts/                           # Orchestration scripts
└── tests/                             # Test scripts and outputs
```

### translation_project/ (Data Project)
```
/Users/jacki/project_files/translation_project/
├── wuxia_individual_files/            # SOURCE: Raw JSON files
├── wuxia_catalog.db                   # SOURCE: Catalog database
├── works.csv                          # SOURCE: Catalog CSV
├── cleaned/                           # PROCESSED: Cleaned JSON files
│   └── COMPLETE_ALL_BOOKS/
├── translation_data/                  # LOGS ONLY (symlinked)
│   └── logs/                          # Shared logs (accessible from both projects)
│       ├── checkpoints/               # Translation checkpoints
│       └── *.log, *.json              # Log files
├── wip/                               # TEMPORARY: Work-in-progress outputs
│   ├── stage_1_metadata/              # After metadata translation
│   ├── stage_2_toc/                   # After TOC translation
│   ├── stage_3_headings/              # After heading translation
│   ├── stage_4_body/                  # After body translation
│   ├── stage_5_special/               # After special sections
│   ├── stage_6_cleanup/               # After footnote cleanup
│   └── stage_7_validation/            # After validation
├── translated_files/                  # FINAL: Completed translations
│   └── D55/                           # Organized by work number
│       ├── translated_D55_001.json
│       └── translated_D55_002.json
├── tests/                             # Test scripts and outputs
│   ├── scripts/
│   └── outputs/
└── .gitignore                         # Excludes WIP, test outputs, Mac files
```

---

## Why This Approach?

### 1. Logs Accessible from Both Projects
- Development team (agentic_test_project) can monitor logs
- Data team (translation_project) has local access to logs
- Symlink makes it seamless

### 2. WIP Files Stay Local
- WIP files are temporary staging for each pipeline stage
- No need to share across projects
- Can be cleaned up after final output generated
- Organized by stage for debugging

### 3. Final Outputs Stay Local
- Completed translations stay in translation_project
- Organized by work number for easy navigation
- Ready for EPUB generation or distribution

### 4. Clean Separation of Concerns
- Source data in translation_project
- Processing logic in agentic_test_project
- Shared logs via symlink
- No confusion about where files belong

---

## Configuration Updates

### 1. Orchestration Script
**File**: `scripts/orchestrate_translation_pipeline.py`

```python
@dataclass
class OrchestrationConfig:
    """Orchestration configuration"""
    # Paths
    source_dir: Path = Path("/Users/jacki/project_files/translation_project/wuxia_individual_files")
    output_dir: Path = Path("/Users/jacki/project_files/translation_project/translated_files")
    wip_dir: Path = Path("/Users/jacki/project_files/translation_project/wip")
    log_dir: Path = Path("/Users/jacki/project_files/translation_project/translation_data/logs")  # ← Fixed!
    catalog_path: Path = Path("/Users/jacki/project_files/translation_project/wuxia_catalog.db")
```

**Change**: `log_dir` now points to `translation_data/logs` instead of `logs`

### 2. Environment Configuration
**File**: `utils/environment_config.py`

```python
def get_env_config(...) -> EnvironmentConfig:
    config = EnvironmentConfig(
        # Output paths - default to project-relative
        output_dir=Path(os.getenv(
            'WUXIA_OUTPUT_DIR',
            str(project_root / 'translation_data' / 'outputs')
        )),
        log_dir=Path(os.getenv(
            'WUXIA_LOG_DIR',
            str(project_root / 'translation_data' / 'logs')  # ← Fixed!
        )),
        ...
    )
```

**Change**: Default `log_dir` now uses `translation_data/logs` instead of `logs/translation`

### 3. Translation Config
**File**: `processors/translation_config.py`

No changes needed! It loads from `EnvironmentConfig` automatically, so fixing `environment_config.py` fixes this too.

---

## Symlink Verification

### Check Symlink
```bash
# View symlink
ls -la /Users/jacki/PycharmProjects/agentic_test_project/ | grep translation_data

# Should show:
# lrwxr-xr-x  ... translation_data -> /Users/jacki/project_files/translation_project/translation_data
```

### Verify Contents Match
```bash
# Via symlink
ls -R /Users/jacki/PycharmProjects/agentic_test_project/translation_data

# Direct access
ls -R /Users/jacki/project_files/translation_project/translation_data

# Both should show identical contents (only logs/ directory)
```

### Test Write Access
```bash
# Write via symlink
echo "test" > /Users/jacki/PycharmProjects/agentic_test_project/translation_data/logs/test.txt

# Check direct access
cat /Users/jacki/project_files/translation_project/translation_data/logs/test.txt

# Should display: test

# Cleanup
rm /Users/jacki/project_files/translation_project/translation_data/logs/test.txt
```

---

## File Flow Through Pipeline

### Stage-by-Stage File Movement

```
INPUT (Source)
↓
/translation_project/wuxia_individual_files/wuxia_0116/D1379_偷拳_白羽.json

STAGE 1: Metadata Translation
↓
/translation_project/wip/stage_1_metadata/D1379_偷拳_白羽.json
Log: /translation_project/translation_data/logs/D1379_偷拳_白羽_stage_1_metadata.json

STAGE 2: TOC Translation
↓
/translation_project/wip/stage_2_toc/D1379_偷拳_白羽.json
Log: /translation_project/translation_data/logs/D1379_偷拳_白羽_stage_2_toc.json

STAGE 3: Headings Translation
↓
/translation_project/wip/stage_3_headings/D1379_偷拳_白羽.json
Log: /translation_project/translation_data/logs/D1379_偷拳_白羽_stage_3_headings.json

STAGE 4: Body Translation
↓
/translation_project/wip/stage_4_body/D1379_偷拳_白羽.json
Log: /translation_project/translation_data/logs/D1379_偷拳_白羽_stage_4_body.json
Checkpoint: /translation_project/translation_data/logs/checkpoints/D1379_checkpoint.json

STAGE 5: Special Sections
↓
/translation_project/wip/stage_5_special/D1379_偷拳_白羽.json
Log: /translation_project/translation_data/logs/D1379_偷拳_白羽_stage_5_special.json

STAGE 6: Footnote Cleanup
↓
/translation_project/wip/stage_6_cleanup/D1379_偷拳_白羽.json
Log: /translation_project/translation_data/logs/D1379_偷拳_白羽_stage_6_cleanup.json
Cleanup Log: /translation_project/translation_data/logs/translated_D1379_偷拳_白羽_character_cleanup_log.json

STAGE 7: Validation
↓
/translation_project/wip/stage_7_validation/D1379_偷拳_白羽.json
Log: /translation_project/translation_data/logs/D1379_偷拳_白羽_stage_7_validation.json

FINAL OUTPUT
↓
/translation_project/translated_files/translated_D1379_偷拳_白羽.json
```

---

## Cleanup Strategy

### What to Clean Regularly
```bash
# Remove WIP files after successful completion
rm -rf /translation_project/wip/stage_*

# Old test outputs
rm -rf /translation_project/tests/outputs/*

# Keep .gitkeep files
```

### What to Keep
```bash
# NEVER delete:
- translation_data/logs/checkpoints/  # Resume functionality depends on this
- translation_data/logs/*.log         # Important for debugging
- translated_files/                   # Final outputs
- wuxia_individual_files/             # Source data
- wuxia_catalog.db                    # Catalog database
```

---

## .gitignore Configuration

**File**: `/translation_project/.gitignore`

```gitignore
# Mac system files
.DS_Store

# Test outputs (regenerable)
tests/outputs/*
!tests/outputs/.gitkeep

# WIP files (temporary staging)
wip/*
!wip/.gitkeep

# Logs (too large, personal debugging)
translation_data/logs/*.log
translation_data/logs/checkpoints/*.json

# Translation data temporary files
translation_data/*
!translation_data/logs/
```

**Rationale**:
- Test outputs: Can be regenerated by running tests
- WIP files: Temporary, can be regenerated by re-running pipeline
- Logs: Too large for git, contain personal debugging info
- Preserve directory structure with `.gitkeep` files

---

## Environment Variables (Optional)

You can override paths via environment variables or `.env` file:

```bash
# .env file (optional)
WUXIA_SOURCE_DIR=/custom/path/to/source
WUXIA_OUTPUT_DIR=/custom/path/to/output
WUXIA_LOG_DIR=/custom/path/to/logs
WUXIA_CATALOG_PATH=/custom/path/to/wuxia_catalog.db
```

**When to use**:
- Testing with different datasets
- Running on different machines
- CI/CD pipelines

**Default behavior**:
- If not set, uses sensible defaults from `environment_config.py`
- Logs default to `translation_data/logs` (symlinked)
- Outputs default to `translation_data/outputs`

---

## Troubleshooting

### Issue: Logs not appearing in symlinked folder
```bash
# Check symlink is valid
ls -la translation_data

# Recreate symlink if broken
rm translation_data
ln -s /Users/jacki/project_files/translation_project/translation_data translation_data
```

### Issue: Permission errors writing to logs
```bash
# Check directory permissions
ls -la /Users/jacki/project_files/translation_project/translation_data/logs

# Fix permissions if needed
chmod 755 /Users/jacki/project_files/translation_project/translation_data/logs
```

### Issue: WIP files not being created
```bash
# Check WIP directory exists
ls -la /Users/jacki/project_files/translation_project/wip

# Create if missing
mkdir -p /Users/jacki/project_files/translation_project/wip
```

---

## Summary

✅ **Logs**: Shared via symlink in `translation_data/logs`
✅ **WIP**: Local to translation_project in `wip/`
✅ **Outputs**: Local to translation_project in `translated_files/`
✅ **Configurations**: Updated to use correct paths
✅ **Clean structure**: No duplicate directories
✅ **Git-friendly**: Proper `.gitignore` excludes temporary files

This approach gives us:
- **Flexibility**: Easy to monitor from both projects
- **Organization**: Clear separation of temporary vs final files
- **Maintainability**: Logs accessible for debugging
- **Scalability**: Easy to add new stages or outputs
