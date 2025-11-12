# Best Practices Guide

This document outlines organizational standards, coding conventions, and workflow practices for this project.

## Table of Contents

- [Project Organization](#project-organization)
- [Directory Structure](#directory-structure)
- [File Naming Conventions](#file-naming-conventions)
- [Git Workflow](#git-workflow)
- [Python Code Standards](#python-code-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation Standards](#documentation-standards)
- [Data Management](#data-management)
- [Security Practices](#security-practices)

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
- **Purpose**: Codify organizational standards learned during refactoring

---

*This document is living and should be updated as the project evolves.*
