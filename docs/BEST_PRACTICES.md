# Best Practices Guide

This document outlines organizational standards, coding conventions, and workflow practices for this project.

## Table of Contents

- [Project Organization](#project-organization)
- [Directory Structure](#directory-structure)
- [File Organization Rules](#file-organization-rules)
- [File Naming Conventions](#file-naming-conventions)
- [Git Workflow](#git-workflow)
- [Python Code Standards](#python-code-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation Standards](#documentation-standards)
- [Data Management](#data-management)
- [Security Practices](#security-practices)
- [Environment Configuration](#environment-configuration)

---

## Project Organization

### Core Principles

1. **Separation of Concerns**: Keep production code, test code, and generated data clearly separated
2. **Single Source of Truth**: Avoid duplicating functionality across files
3. **Progressive Enhancement**: Mark legacy code clearly, don't delete until replacement is proven
4. **Documentation Over Comments**: Prefer well-named functions and clear documentation over inline comments

### Module Structure

```
project_root/
├── processors/           # Core processing pipeline (production code)
├── utils/               # Helper functions and utilities
│   └── legacy_*/        # Archive old implementations with README
├── scripts/             # Executable scripts for batch operations
├── cli/                 # Command-line interfaces
├── tests/               # Unit and integration tests
├── docs/                # All documentation
├── translation_data/    # Data directory (symlink, not in git)
│   ├── cleaned/         # Production outputs
│   └── test/            # Test outputs
└── web_ui/             # Web interfaces
```

---

## Directory Structure

### Production vs Test Separation

**Production Outputs**: `translation_data/cleaned/`
- Fully validated, production-ready files
- Used by downstream systems
- Should pass all validation stages

**Test Outputs**: `translation_data/test/`
- Experimental runs and development testing
- Can contain incomplete or invalid data
- Organized by test name or iteration

### Legacy Code Management

When superseding code:
1. Create a `legacy_*/` subdirectory in the same parent directory
2. Move old implementations there
3. Add a `README.md` explaining:
   - Why code was moved
   - What replaced it
   - Migration guide for imports

**Example**: `utils/legacy_toc_validators/`

### Documentation Organization

```
docs/
├── BEST_PRACTICES.md        # This file
├── translation/             # Domain-specific docs
│   ├── TRANSLATION_FILES_INDEX.md
│   ├── TRANSLATION_PIPELINE_README.md
│   └── TRANSLATION_QUICK_START.md
└── WEB_UI_TRANSLATION_MANAGER.md
```

---

## File Organization Rules

### The Golden Rule

**Keep the root directory minimal**. Only these files belong at project root:
- `README.md` - Project overview
- `CLAUDE.md` - Instructions for Claude Code
- `SYMLINK_SETUP.md` - Setup instructions
- Configuration files (`.gitignore`, `pyproject.toml`, `package.json`, etc.)

Everything else belongs in organized subdirectories.

### Where Files Belong

#### Documentation Files (`.md`)

**ALL** markdown documentation → `docs/` directory with domain-specific subdirectories:

```
docs/
├── BEST_PRACTICES.md              # Coding standards (this file)
├── AI_ASSISTANT_GUIDE.md          # AI assistant management
├── POST_PROCESSING_GUIDE.md       # Post-processing workflows
├── WEB_UI_TRANSLATION_MANAGER.md  # Web UI documentation
│
├── translation/                   # Translation-specific
│   ├── GLOSSARY_INTEGRATION_GUIDE.md
│   ├── GLOSSARY_UPDATE_CHANGELOG.md
│   ├── TECHNIQUE_TRANSLATION_QUICK_REFERENCE.md
│   ├── WUXIA_TRANSLATION_EXAMPLES.md
│   └── PIPELINE_SUMMARY.md
│
├── formatting/                    # EPUB formatting
│   ├── EPUB_FORMATTING_STRATEGY.md
│   ├── FORMATTING_ANALYSIS_SUMMARY.md
│   └── FORMATTING_VISUAL_OVERVIEW.txt
│
├── scripts/                       # Script documentation
│   ├── CLEANUP_README.md
│   ├── VALIDATION_README.md
│   ├── WUXIA_CATALOG_README.md
│   └── SETUP_GUIDE.md
│
└── reports/                       # Analysis reports & bug reports
    ├── TOC_REGENERATION_BUG_FIX.md
    ├── glossary_integration_complete.md
    └── wuxia_deduplication_guide.md
```

**Rules**:
- NO `.md` files in root (except README, CLAUDE, SYMLINK_SETUP)
- NO `.md` files in `scripts/` (move to `docs/scripts/`)
- Group by domain: translation, formatting, scripts, reports
- Use descriptive names with domain prefixes

#### Data Files (`.csv`, `.json`, `.txt` reports)

**ALL** data files → `data/` directory:

```
data/
├── glossaries/                    # Glossary CSV files
│   ├── wuxia_translation_glossary.csv
│   ├── wuxia_translation_glossary_additions.csv
│   ├── wuxia_glossary_merged.csv
│   └── candidate_wuxia_terms.csv
│
└── analysis/                      # Generated analysis outputs
    ├── classification_data.json
    ├── deduplication_report.json
    ├── ai_classification_report.txt
    └── content_type_analysis_report.txt
```

**Rules**:
- NO CSV/JSON data files in root
- Separate source data (`glossaries/`) from generated reports (`analysis/`)
- Consider adding `data/` to `.gitignore` for large files

#### Scripts (`.py` executables)

**ONLY** executable Python scripts → `scripts/` directory:

```
scripts/
├── batch_process_books.py         # Production scripts
├── validate_toc_chapter_alignment.py
├── translate_work.py
├── ...                            # 19+ legitimate scripts
│
└── (NO .md files here!)           # Documentation → docs/scripts/
```

**Rules**:
- Scripts must be executable and have a clear purpose
- NO documentation files (`.md`) in `scripts/`
- NO ad-hoc test scripts in root (move to `scripts/` or delete)
- Test scripts like `test_*.py` should be gitignored

#### Log Files

**ALL** logs → `logs/` directory (gitignored), categorized by type:

```
logs/
├── batch/                         # Batch processing logs
│   ├── batch_report_20251110_154741.json
│   └── batch_report_20251110_200225.json
│
├── translation/                   # Translation logs
│   ├── checkpoints/
│   └── translation_progress.log
│
└── tests/                         # Test execution logs
    ├── translation_test.log
    └── translation_test_rerun.log
```

**Rules**:
- NO logs in root directory
- Categorize by log type (batch, translation, tests)
- Use timestamped names for batch reports
- Add log rotation/archival for large files

### Common Violations and Fixes

#### Violation: Documentation in Root

```
# BAD - Root directory cluttered
project_root/
├── README.md
├── CLAUDE.md
├── EPUB_FORMATTING_STRATEGY.md          ❌ Should be in docs/formatting/
├── GLOSSARY_INTEGRATION_GUIDE.md        ❌ Should be in docs/translation/
├── TOC_REGENERATION_BUG_FIX_REPORT.md   ❌ Should be in docs/reports/
└── wuxia_deduplication_guide.md         ❌ Should be in docs/reports/
```

```
# GOOD - Clean root, organized docs
project_root/
├── README.md
├── CLAUDE.md
└── docs/
    ├── formatting/
    │   └── EPUB_FORMATTING_STRATEGY.md  ✓
    ├── translation/
    │   └── GLOSSARY_INTEGRATION_GUIDE.md ✓
    └── reports/
        ├── TOC_REGENERATION_BUG_FIX.md   ✓
        └── wuxia_deduplication_guide.md  ✓
```

#### Violation: Scripts in Root

```
# BAD - Scripts scattered
project_root/
├── ai_content_classifier.py     ❌ Should be in scripts/
├── analyze_content_types.py     ❌ Should be in scripts/
├── test_translator_simple.py    ❌ Should be in scripts/ or deleted
└── scripts/
    └── batch_process_books.py
```

```
# GOOD - All scripts together
project_root/
└── scripts/
    ├── ai_content_classifier.py          ✓
    ├── analyze_content_types.py          ✓
    ├── batch_process_books.py            ✓
    └── (test_translator_simple.py)       ✓ Gitignored if needed
```

#### Violation: Data Files in Root

```
# BAD - Data files everywhere
project_root/
├── wuxia_translation_glossary.csv       ❌ Should be in data/glossaries/
├── classification_data.json             ❌ Should be in data/analysis/
├── deduplication_report.json            ❌ Should be in data/analysis/
└── candidate_wuxia_terms.csv            ❌ Should be in data/glossaries/
```

```
# GOOD - Data organized by type
project_root/
└── data/
    ├── glossaries/
    │   ├── wuxia_translation_glossary.csv    ✓
    │   └── candidate_wuxia_terms.csv         ✓
    └── analysis/
        ├── classification_data.json          ✓
        └── deduplication_report.json         ✓
```

#### Violation: Logs in Root

```
# BAD - Logs mixed with code
project_root/
├── batch_process_75_works.log           ❌ Should be in logs/batch/
├── translation_test.log                 ❌ Should be in logs/tests/
└── logs/
    └── translation/
```

```
# GOOD - Logs categorized
project_root/
└── logs/
    ├── batch/
    │   └── batch_process_75_works.log   ✓
    ├── translation/
    └── tests/
        └── translation_test.log         ✓
```

### Agent-Specific Guidelines

When working as a Claude Code agent, **always** follow these rules:

1. **Before creating any file**, determine its correct location based on type
2. **Before moving files**, check if directories need to be created first
3. **Never leave files in root** unless they are essential config files
4. **Update imports** when moving Python files
5. **Document moves** in commit messages

#### Quick Decision Tree

```
Creating a new file? Ask yourself:

Is it a README/CLAUDE/SYMLINK_SETUP.md?
  ├─ YES → Root directory
  └─ NO  → Continue...

Is it a .md documentation file?
  ├─ YES → docs/ (with domain subdirectory)
  └─ NO  → Continue...

Is it a .py script?
  ├─ YES → Is it a processor/util/cli module?
  │         ├─ YES → processors/ or utils/ or cli/
  │         └─ NO  → scripts/
  └─ NO  → Continue...

Is it a data file (.csv, .json report)?
  ├─ YES → data/glossaries/ or data/analysis/
  └─ NO  → Continue...

Is it a log file?
  ├─ YES → logs/batch/ or logs/translation/ or logs/tests/
  └─ NO  → Probably configuration → Root is OK
```

---

## File Naming Conventions

### Python Files

- **Modules**: `lowercase_with_underscores.py`
- **Classes**: `PascalCase` inside files
- **Scripts**: Executable scripts should be clear about their purpose
  - Good: `batch_translate_works.py`, `validate_toc_chapter_alignment.py`
  - Bad: `process.py`, `utils.py`

### Test Files

- **Unit tests**: `test_<module_name>.py` (gitignored in scripts/)
- **Integration tests**: Place in `tests/integration/` directory
- Test files in `scripts/` are development tests, should be gitignored

### Documentation Files

- **Uppercase for visibility**: `README.md`, `BEST_PRACTICES.md`
- **Domain prefix for context**: `TRANSLATION_PIPELINE_README.md`
- **Avoid generic names**: Don't use `doc.md` or `notes.md`

---

## Git Workflow

### Branch Strategy

- **main**: Stable, production-ready code
- **Feature branches**: Short-lived, named `feature/description`
- **Cleanup branches**: Use `cleanup-backup` for major refactors (provides rollback)

### Commit Messages

Follow Conventional Commits format:

```
<type>(<scope>): <subject>

<body>

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code restructuring without changing functionality
- `docs`: Documentation changes
- `test`: Test additions or modifications
- `chore`: Maintenance tasks

**Example**:
```
refactor(utils): Consolidate TOC validators

Moved legacy validators to utils/legacy_toc_validators/:
- toc_alignment_validator.py (basic, superseded)
- toc_alignment_fixer.py
- toc_auto_fix.py

toc_chapter_validator.py is now the canonical comprehensive validator.
Extracts actual headings from content_blocks and performs semantic validation.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
Co-Authored-By: Claude <noreply@anthropic.com>
```

### What NOT to Commit

Defined in `.gitignore`:
- Credentials (`env_creds.yml`, `.env`)
- Generated data (`translation_data/`, `output/`, `logs/`)
- Test scripts (`test_*.py`, `run_*.py` in scripts/)
- Build artifacts (`node_modules/`, `venv/`, `__pycache__/`)
- Database files (`*.db`, `*.sqlite`)
- Large CSV files (`works.csv`, `*_catalog.csv`)

---

## Python Code Standards

### Code Style

- **Formatter**: Use `black` for consistent formatting
- **Linter**: Use `flake8` for style checking
- **Type hints**: Use type annotations for function signatures

```python
from typing import Dict, List, Optional
from pathlib import Path

def process_file(
    input_path: Path,
    output_path: Path,
    config: Optional[Dict[str, any]] = None
) -> Dict[str, any]:
    """
    Process a single file with optional configuration.

    Args:
        input_path: Path to input file
        output_path: Path to output file
        config: Optional configuration dictionary

    Returns:
        Dictionary with processing results and statistics
    """
    pass
```

### Module Organization

Standard module structure:

```python
#!/usr/bin/env python3
"""
Module Title - Brief Description

Detailed explanation of what this module does.
Key classes and functions.
"""

import sys
from pathlib import Path
from typing import Dict, List

# Constants
DEFAULT_CONFIG = {...}

# Classes
class ProcessorName:
    """Docstring explaining the class"""
    pass

# Functions
def main():
    """CLI entry point"""
    pass

if __name__ == "__main__":
    sys.exit(main())
```

### Error Handling

- Use specific exceptions, not bare `except:`
- Log errors with context
- Provide actionable error messages

```python
try:
    result = process_file(path)
except FileNotFoundError:
    logger.error(f"Input file not found: {path}")
    sys.exit(1)
except ValidationError as e:
    logger.error(f"Validation failed for {path}: {e}")
    # Continue processing other files
```

### Package Installation

This project is a proper Python package. Install it in editable mode for development:

```bash
# Install package in editable mode
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"

# Install with environment config support
pip install -e ".[env]"

# Install everything
pip install -e ".[dev,env]"
```

After installation, all modules can be imported directly:

```python
from processors.json_cleaner import clean_book_json
from utils.environment_config import get_env_config
from processors.translation_config import TranslationConfig
```

**Important**: Never use `sys.path.insert()` to add the project root to the path. The package is properly installed and all imports should use absolute package paths.

### Imports

Order imports by:
1. Standard library
2. Third-party packages
3. Local modules

```python
import sys
import json
from pathlib import Path

from openai import OpenAI
import sqlite3

from processors.json_cleaner import clean_book_json
from utils.load_env_creds import get_openai_api_key
```

**Never** use relative imports or `sys.path` hacks:

```python
# BAD - Don't do this
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# GOOD - Use absolute imports
from processors.json_cleaner import clean_book_json
```

---

## Testing Guidelines

### Test Organization

```
tests/
├── unit/                    # Fast, isolated tests
│   ├── test_json_cleaner.py
│   └── test_validators.py
└── integration/             # Slower, end-to-end tests
    ├── test_pipeline.py
    └── test_batch_processing.py
```

### Test Naming

- Test files: `test_<module>.py`
- Test functions: `test_<functionality>_<scenario>`

```python
def test_clean_json_extracts_chapters():
    """Test that JSON cleaner correctly extracts chapter structure"""
    pass

def test_clean_json_handles_missing_toc():
    """Test that JSON cleaner gracefully handles missing TOC"""
    pass
```

### What to Test

- **Critical path**: Core processing functions
- **Edge cases**: Empty inputs, malformed data, missing fields
- **Error handling**: Invalid inputs, API failures
- **Regression prevention**: Fixed bugs should have tests

### What NOT to Test

- External APIs (mock them instead)
- Third-party library functionality
- Generated files (test the generation logic, not the output)

---

## Documentation Standards

### README Files

Every major directory should have a README explaining:
- Purpose of the directory
- Key files and their roles
- How to use/run the code
- Dependencies

### Docstrings

Use Google-style docstrings:

```python
def validate_toc_alignment(
    cleaned_json: Dict[str, any],
    use_ai: bool = True
) -> ValidationReport:
    """
    Validate TOC entries match actual chapter headings.

    Extracts actual headings from content_blocks and compares them
    to TOC entries. Uses OpenAI for semantic validation of ambiguous
    mismatches.

    Args:
        cleaned_json: Cleaned book JSON with structure and content_blocks
        use_ai: Whether to use OpenAI for semantic validation

    Returns:
        ValidationReport with issues, confidence score, and recommendations

    Raises:
        ValueError: If cleaned_json is missing required structure
        APIError: If OpenAI API call fails and use_ai is True

    Example:
        >>> validator = TOCChapterValidator(use_ai=True)
        >>> report = validator.validate(cleaned_json)
        >>> print(f"Valid: {report.is_valid}, Score: {report.confidence_score}%")
    """
    pass
```

### Inline Comments

Use comments sparingly:
- Explain **why**, not **what**
- Document non-obvious business logic
- Mark TODOs and FIXMEs with issues

```python
# Use special numeral handling for 廿(20), 卅(30), 卌(40)
# These are common in classical Chinese chapter numbering
if char == '廿':
    return 20
```

---

## Data Management

### Input Data

- **Location**: Symlinked to `translation_data/` (not in git)
- **Source**: `/Users/jacki/project_files/translation_project/wuxia_individual_files/`
- **Format**: Raw JSON files organized by work directory (`wuxia_NNNN/`)

### Output Data

**Production**: `translation_data/cleaned/COMPLETE_ALL_BOOKS/`
- Fully validated and ready for translation
- Should pass all 6 pipeline stages

**Test**: `translation_data/test/outputs/`
- Development and experimental outputs
- Can contain partial or invalid data

### Database Files

- **Location**: Not in git (too large, contains data)
- **Catalog**: `/Users/jacki/project_files/translation_project/wuxia_catalog.db`
- **Schema**: See `utils/catalog_metadata.py` for structure
- **Access**: Use provided helper classes, don't write raw SQL

```python
from utils.catalog_metadata import CatalogMetadataExtractor

extractor = CatalogMetadataExtractor('wuxia_catalog.db')
metadata = extractor.get_metadata_by_directory('wuxia_0117')
```

### Logs

- **Location**: `logs/` directory (gitignored)
- **Format**: JSON for structured data, text for human-readable
- **Rotation**: Keep recent logs, archive old ones
- **Size**: Large batch reports should be in logs/, not root

---

## Translation Data Management

### Output Organization

Translation outputs follow a predictable hierarchical structure for easy discovery:

```
translation_data/
├── outputs/              # Completed translations
│   ├── {work_number}/   # Work folder (e.g., D58/, I1046/)
│   │   ├── translated_{volume}.json        # Main translation output
│   │   ├── metadata_{volume}.json          # Job metadata
│   │   └── annotations_{volume}.json       # Cultural footnotes
│   └── index.json       # Catalog of all completed translations
├── checkpoints/         # Resume points for interrupted jobs
│   └── {work_number}/
│       └── {volume}/
│           └── checkpoint_{timestamp}.json
└── logs/                # Translation execution logs
    └── {work_number}/
        └── {volume}/
            └── translation_{timestamp}.log
```

### Predictable Path Formulas

**Translation Output**:
`translation_data/outputs/{work_number}/translated_{volume}.json`

Examples:
- D58, volume 001: `translation_data/outputs/D58/translated_001.json`
- I1046, no volume: `translation_data/outputs/I1046/translated.json`

**Checkpoint File**:
`translation_data/checkpoints/{work_number}/{volume}/checkpoint_{timestamp}.json`

**Log File**:
`translation_data/logs/{work_number}/{volume}/translation_{timestamp}.log`

### Index File Format

The `translation_data/outputs/index.json` file catalogs all completed translations:

```json
{
  "last_updated": "2025-01-14T10:30:00Z",
  "translations": [
    {
      "work_number": "D58",
      "volume": "001",
      "title_chinese": "書劍恩仇錄",
      "title_english": "The Book and the Sword",
      "author_chinese": "金庸",
      "author_english": "Jin Yong",
      "completed_at": "2025-01-14T09:15:00Z",
      "output_path": "translation_data/outputs/D58/translated_001.json",
      "total_chapters": 40,
      "total_blocks": 1250,
      "token_usage": 450000
    }
  ]
}
```

### UI Discovery Pattern

The web UI uses the index file to discover available translations:

1. Read `translation_data/outputs/index.json`
2. Display works with metadata (title, author, completion date)
3. Allow filtering by work_number, title, author
4. Link to translation output files

### Cleanup and Archival

**Checkpoints**: Keep for 30 days after completion, then archive or delete
**Logs**: Archive logs older than 90 days to `logs/archive/`
**Old Translations**: Keep previous versions when re-translating (add timestamp suffix)

```bash
# Example: Re-translation preserves old version
translation_data/outputs/D58/translated_001.json                    # New version
translation_data/outputs/D58/translated_001_20250114.json          # Archived old version
```

---

## Security Practices

### Credentials Management

**NEVER commit credentials to git**. Use:
- `.env` files (gitignored)
- `env_creds.yml` (gitignored)
- Environment variables

```python
# Good: Use helper function
from utils.load_env_creds import get_openai_api_key
api_key = get_openai_api_key()

# Bad: Hardcoded key
api_key = "sk-proj-abc123..."  # NEVER DO THIS
```

### API Keys

- Store in `env_creds.yml` or `.env`
- Load at runtime, never at import time
- Use environment variables in production
- Rotate keys regularly

### Database Security

- Use parameterized queries (prevents SQL injection)
- Don't log sensitive data
- Limit file permissions on database files

```python
# Good: Parameterized query
cursor.execute("SELECT * FROM works WHERE work_number = ?", (work_num,))

# Bad: String interpolation (SQL injection risk)
cursor.execute(f"SELECT * FROM works WHERE work_number = '{work_num}'")
```

---

## Validation Pipeline

### 6-Stage Processing

The batch processing pipeline follows these stages:

1. **Topology Analysis** - Structure analysis without modifications
2. **Sanity Check** - Metadata extraction and sequence validation
3. **JSON Cleaning** - Extract discrete blocks with IDs
4. **Chapter Alignment** - Fix EPUB metadata mismatches
5. **TOC Restructuring** - Convert TOC to structured format
6. **Comprehensive Validation** - Multiple validators in parallel

Each stage should:
- Log its actions
- Handle errors gracefully
- Provide detailed reports
- Not modify previous stage outputs

### Validator Selection

**Use `toc_chapter_validator.py` as the primary validator**:
- Most comprehensive (extracts actual headings)
- Semantic validation with OpenAI
- Detailed issue reporting

**Use `toc_body_count_validator.py` for quick checks**:
- Fast, deterministic
- No API calls
- Count-based validation

**Avoid legacy validators** in `utils/legacy_toc_validators/`:
- Kept for reference only
- Use modern replacements instead

---

## Web UI Development

### Single UI Pattern

- **Location**: `web_ui/translation_manager/`
- **Backend**: FastAPI with WebSocket support
- **Frontend**: React with Vite
- **No duplication**: Keep only one UI implementation

### UI Organization

```
web_ui/
└── translation_manager/
    ├── backend/
    │   ├── app.py          # FastAPI server
    │   └── requirements.txt
    ├── frontend/
    │   ├── src/
    │   └── package.json
    ├── logs/               # UI-specific logs
    ├── start.sh           # Start both servers
    └── stop.sh            # Stop both servers
```

### Development Workflow

```bash
# Start UI
cd web_ui/translation_manager
./start.sh

# Access at http://localhost:5174

# Stop UI
./stop.sh
```

---

## Common Pitfalls to Avoid

### 1. Test Script Proliferation

**Problem**: Creating many `test_*.py` files in scripts/

**Solution**:
- Use `tests/integration/` for integration tests
- Add `scripts/test_*.py` to .gitignore
- Delete obsolete test scripts regularly

### 2. Multiple Implementations of Same Functionality

**Problem**: Having 3+ validators/fixers doing similar things

**Solution**:
- Pick one canonical implementation
- Move others to `legacy_*/` with README
- Update documentation to point to canonical version

### 3. Root Directory Clutter

**Problem**: Logs, docs, and outputs accumulating at project root

**Solution**:
- Logs → `logs/`
- Docs → `docs/` and `docs/<domain>/`
- Outputs → `translation_data/cleaned/` or `translation_data/test/`

### 4. Hardcoded Paths

**Problem**: Paths like `/Users/jacki/...` in code

**Solution**:
- Use environment variables
- Accept paths as CLI arguments
- Provide sensible defaults in config

### 5. Mixing Production and Test Data

**Problem**: Test outputs mixed with production outputs

**Solution**:
- Clear separation: `translation_data/cleaned/` vs `translation_data/test/`
- Different naming conventions
- .gitignore both, but document structure

---

## Environment Configuration

### Overview

The project uses environment-based configuration to eliminate hardcoded paths and enable flexible deployment across different environments (development, production, CI/CD).

**Key Benefits**:
- No hardcoded absolute paths in code
- Easy configuration for different machines
- Consistent paths across all components
- Support for .env files and environment variables
- Graceful fallback to sensible defaults

### Quick Start

**1. Copy the template**:
```bash
cp .env.example .env
```

**2. Edit with your paths**:
```bash
# Edit .env with your local paths
nano .env  # or use your favorite editor
```

**3. Configure your environment**:
```bash
# Source data paths
WUXIA_SOURCE_DIR=/path/to/your/cleaned/source/files
WUXIA_CATALOG_PATH=/path/to/your/wuxia_catalog.db
WUXIA_GLOSSARY_DB_PATH=./wuxia_glossary.db

# Output paths (project-relative is recommended)
WUXIA_OUTPUT_DIR=./translation_data/outputs
WUXIA_LOG_DIR=./logs/translation

# API keys
OPENAI_API_KEY=your-openai-api-key-here
```

### Available Environment Variables

#### Source Data Paths

**WUXIA_SOURCE_DIR**
- Purpose: Directory containing cleaned JSON source files
- Default: `/Users/jacki/project_files/translation_project/cleaned/COMPLETE_ALL_BOOKS`
- Example: `/path/to/your/cleaned/source/files`
- Used by: Translation pipeline, batch processors

**WUXIA_CATALOG_PATH**
- Purpose: Path to wuxia catalog SQLite database
- Default: `/Users/jacki/project_files/translation_project/wuxia_catalog.db`
- Example: `/path/to/your/wuxia_catalog.db`
- Used by: Metadata extraction, catalog queries

**WUXIA_GLOSSARY_DB_PATH**
- Purpose: Path to wuxia glossary SQLite database
- Default: `./wuxia_glossary.db` (project root)
- Example: `./wuxia_glossary.db` or `/path/to/glossary.db`
- Used by: Translation glossary lookup, term matching

#### Output Paths

**WUXIA_OUTPUT_DIR**
- Purpose: Directory for translation outputs
- Default: `./translation_data/outputs` (project-relative)
- Example: `./translation_data/outputs`
- Used by: Translation output, file generation

**WUXIA_LOG_DIR**
- Purpose: Directory for translation logs
- Default: `./logs/translation` (project-relative)
- Example: `./logs/translation`
- Used by: Logging, checkpoint files

#### API Keys

**OPENAI_API_KEY**
- Purpose: OpenAI API key for translation services
- Required: Yes (for translation features)
- Example: `sk-proj-...`

**ANTHROPIC_API_KEY**
- Purpose: Anthropic API key (optional, for future features)
- Required: No
- Example: `sk-ant-...`

### How It Works

#### 1. Project Root Auto-Detection

The system automatically detects your project root by looking for:
- `.git` directory (most common)
- `pyproject.toml` file
- `processors/` and `utils/` directories

```python
from utils.environment_config import detect_project_root

project_root = detect_project_root()
# Returns: Path('/Users/jacki/PycharmProjects/agentic_test_project')
```

#### 2. Configuration Loading

Configuration is loaded in this order:
1. `.env` file (if python-dotenv installed and .env exists)
2. Environment variables (os.environ)
3. Hardcoded defaults (fallback)

```python
from utils.environment_config import get_env_config

config = get_env_config()
print(config.source_dir)      # Path from WUXIA_SOURCE_DIR or default
print(config.catalog_path)    # Path from WUXIA_CATALOG_PATH or default
```

#### 3. Singleton Pattern

For application-wide consistency, use the singleton pattern:

```python
from utils.environment_config import get_or_create_env_config

# Gets or creates the singleton instance
config = get_or_create_env_config()

# All subsequent calls return the same instance
config2 = get_or_create_env_config()
assert config is config2  # True
```

#### 4. Validation

Always validate configuration before starting operations:

```python
config = get_or_create_env_config()

errors = config.validate()
if errors:
    print("Configuration errors:")
    for error in errors:
        print(f"  - {error}")
    sys.exit(1)
```

### Using Environment Config in Your Code

#### TranslationConfig Integration

`TranslationConfig` automatically loads from environment:

```python
from processors.translation_config import TranslationConfig

# Paths loaded from environment automatically
config = TranslationConfig()

# Or override specific paths
config = TranslationConfig(
    source_dir=Path("/custom/source/path"),
    # other paths loaded from environment
)
```

#### Direct EnvironmentConfig Usage

For utilities that only need paths:

```python
from utils.environment_config import get_or_create_env_config

config = get_or_create_env_config()

# Validate paths exist
errors = config.validate()
if errors:
    logger.error(f"Configuration errors: {errors}")
    sys.exit(1)

# Create output directories
config.create_output_dirs()

# Use paths
with open(config.catalog_path) as f:
    data = f.read()
```

### Path Configuration Best Practices

#### 1. Use Project-Relative Paths for Outputs

**Good** (portable, works on any machine):
```bash
WUXIA_OUTPUT_DIR=./translation_data/outputs
WUXIA_LOG_DIR=./logs/translation
```

**Bad** (hardcoded, machine-specific):
```bash
WUXIA_OUTPUT_DIR=/Users/jacki/project_files/outputs
WUXIA_LOG_DIR=/Users/jacki/logs
```

#### 2. Use Absolute Paths for External Data

**Good** (explicit, clear):
```bash
WUXIA_SOURCE_DIR=/path/to/external/data/source
WUXIA_CATALOG_PATH=/path/to/external/data/wuxia_catalog.db
```

**Why**: External data locations vary by environment and shouldn't be inside the project.

#### 3. Use Forward Slashes Even on Windows

**Good** (cross-platform):
```bash
WUXIA_SOURCE_DIR=/c/Users/username/data/source
```

**Bad** (Windows-specific):
```bash
WUXIA_SOURCE_DIR=C:\Users\username\data\source
```

Python's `Path` handles forward slashes correctly on all platforms.

#### 4. Don't Commit .env Files

**Good**:
```bash
# .gitignore
.env
env_creds.yml
```

**Why**: .env files contain machine-specific paths and API keys. Use `.env.example` as template.

### Common Setup Scenarios

#### Scenario 1: Local Development

```bash
# .env
WUXIA_SOURCE_DIR=/Users/jacki/project_files/translation_project/cleaned/COMPLETE_ALL_BOOKS
WUXIA_CATALOG_PATH=/Users/jacki/project_files/translation_project/wuxia_catalog.db
WUXIA_GLOSSARY_DB_PATH=./wuxia_glossary.db
WUXIA_OUTPUT_DIR=./translation_data/outputs
WUXIA_LOG_DIR=./logs/translation
OPENAI_API_KEY=sk-proj-your-key-here
```

#### Scenario 2: CI/CD Pipeline

```bash
# Set as environment variables in CI system
export WUXIA_SOURCE_DIR=/ci/workspace/data/source
export WUXIA_CATALOG_PATH=/ci/workspace/data/catalog.db
export WUXIA_GLOSSARY_DB_PATH=/ci/workspace/data/glossary.db
export WUXIA_OUTPUT_DIR=/ci/workspace/outputs
export WUXIA_LOG_DIR=/ci/workspace/logs
export OPENAI_API_KEY=${CI_SECRET_OPENAI_KEY}
```

#### Scenario 3: Production Server

```bash
# /etc/environment or systemd service file
WUXIA_SOURCE_DIR=/var/lib/wuxia/source
WUXIA_CATALOG_PATH=/var/lib/wuxia/catalog.db
WUXIA_GLOSSARY_DB_PATH=/var/lib/wuxia/glossary.db
WUXIA_OUTPUT_DIR=/var/lib/wuxia/outputs
WUXIA_LOG_DIR=/var/log/wuxia/translation
OPENAI_API_KEY=sk-proj-production-key
```

### Migration Guide from Hardcoded Paths

#### Step 1: Identify Hardcoded Paths

Search for hardcoded paths:
```bash
grep -r "/Users/jacki/project_files" --include="*.py" .
```

#### Step 2: Create .env File

```bash
cp .env.example .env
# Edit .env with your actual paths
```

#### Step 3: Update Code to Use EnvironmentConfig

**Before** (hardcoded):
```python
catalog_path = "/Users/jacki/project_files/translation_project/wuxia_catalog.db"
```

**After** (environment-based):
```python
from utils.environment_config import get_or_create_env_config

config = get_or_create_env_config()
catalog_path = config.catalog_path
```

#### Step 4: Test Configuration

```bash
# Test environment config loading
python utils/environment_config.py

# Should output:
# ================================================================================
# Environment Configuration Test
# ================================================================================
#
# Project Root: /Users/jacki/PycharmProjects/agentic_test_project
# Source Paths:
#   Source Dir: /Users/jacki/project_files/translation_project/cleaned/COMPLETE_ALL_BOOKS
#   Catalog DB: /Users/jacki/project_files/translation_project/wuxia_catalog.db
#   Glossary DB: /Users/jacki/PycharmProjects/agentic_test_project/wuxia_glossary.db
# Output Paths:
#   Output Dir: /Users/jacki/PycharmProjects/agentic_test_project/translation_data/outputs
#   Log Dir: /Users/jacki/PycharmProjects/agentic_test_project/logs/translation
#
# Validation:
#   ✓ All required paths exist
#
# ✓ Configuration validated successfully
```

#### Step 5: Update Existing Scripts

**Before**:
```python
# scripts/translate_work.py
config = TranslationConfig(
    source_dir=Path("/Users/jacki/project_files/..."),
    catalog_path=Path("/Users/jacki/project_files/...")
)
```

**After**:
```python
# scripts/translate_work.py
# Paths loaded automatically from environment
config = TranslationConfig()

# Or override specific paths if needed
config = TranslationConfig(
    source_dir=args.source_dir  # from CLI args
)
```

### Troubleshooting

#### Issue: "Configuration errors: Catalog database not found"

**Solution**: Check that `WUXIA_CATALOG_PATH` points to an existing file:
```bash
echo $WUXIA_CATALOG_PATH
ls -la "$WUXIA_CATALOG_PATH"
```

#### Issue: "EnvironmentConfig not available, using hardcoded defaults"

**Solution**: This warning appears when `utils.environment_config` can't be imported. Check:
1. File exists: `ls utils/environment_config.py`
2. No syntax errors: `python -m py_compile utils/environment_config.py`
3. Imports work: `python -c "from utils.environment_config import get_env_config"`

#### Issue: ".env file not being loaded"

**Solution**:
1. Install python-dotenv: `pip install python-dotenv`
2. Verify .env location: Should be in project root
3. Check .env syntax: Use `KEY=value` format, no spaces around `=`

#### Issue: "Paths work on my machine but not CI"

**Solution**: Use environment variables in CI instead of .env:
```yaml
# .github/workflows/test.yml
env:
  WUXIA_SOURCE_DIR: /ci/workspace/data
  WUXIA_CATALOG_PATH: /ci/workspace/catalog.db
```

### Dependencies

**Required**: None (uses only Python stdlib)

**Optional**:
- `python-dotenv` - For .env file support (recommended)
  ```bash
  pip install python-dotenv
  ```
  Without it, system falls back to `os.environ` only.

### Files Reference

- **utils/environment_config.py** - Core configuration module
- **.env.example** - Template for local configuration
- **processors/translation_config.py** - Translation config with environment integration
- **docs/BEST_PRACTICES.md** - This file

---

## Maintenance Tasks

### Regular Cleanup (Monthly)

- [ ] Review and delete obsolete test scripts
- [ ] Archive old logs (keep last 30 days)
- [ ] Check for duplicate functionality
- [ ] Update documentation for new features

### Code Health Checks

```bash
# Format code
black processors/ utils/ scripts/ cli/

# Lint code
flake8 processors/ utils/ scripts/ cli/

# Type check
mypy processors/ utils/ scripts/ cli/

# Run tests
pytest tests/
```

### Dependency Updates (Quarterly)

```bash
# Check for outdated packages
pip list --outdated

# Update requirements
pip install --upgrade -r requirements.txt
pip freeze > requirements.txt
```

---

## Getting Help

### Resources

- **CLAUDE.md**: Instructions for Claude Code instances
- **README.md**: Project overview and setup
- **docs/translation/**: Domain-specific documentation
- **Agent files**: `.claude/agents/*.md` for specialized tasks

### When to Create New Documentation

Create new docs when:
- Introducing a new subsystem
- Complex workflow needs explanation
- Multiple people will use a feature
- Onboarding new contributors

Don't create docs for:
- Self-explanatory code
- One-off scripts
- Temporary workarounds

---

## Version History

- **2025-01-11**: Initial version after project cleanup
  - Codified organizational standards learned during refactoring
- **2025-01-14**: Added comprehensive File Organization Rules section
  - Added detailed file placement guidelines (docs/, data/, scripts/, logs/)
  - Added common violations and fixes with examples
  - Added agent-specific guidelines and decision tree
  - Purpose: Address root directory clutter and scattered files

---

*This document is living and should be updated as the project evolves.*
