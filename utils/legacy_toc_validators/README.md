# Legacy TOC Validators

This directory contains older TOC validation and fixing scripts that have been superseded by newer implementations.

## Current Production Scripts (in utils/)

Use these for all TOC validation and fixing tasks:

1. **`toc_chapter_validator.py`** - **CORE VALIDATOR** (Most comprehensive)
   - Extracts actual chapter headings from content_blocks
   - Semantic validation using OpenAI
   - Detects missing chapters, title mismatches, sequence gaps
   - Generates detailed validation reports
   - **Use this as your primary validator**

2. **`toc_body_count_validator.py`** - Fast count-based validation
   - Validates TOC entry count matches body chapter count
   - Identifies specific missing/extra chapters
   - Fast, deterministic (no API calls)
   - **Use for quick count checks**

3. **`auto_fix_toc_alignment.py`** - Production auto-fixer
   - Applies fixes based on toc_chapter_validator results
   - Most recent auto-fix implementation
   - **Use this for automated fixes**

## Legacy Scripts (in this directory)

These are kept for reference but should not be used in production:

1. **`toc_alignment_validator.py`** - Basic OpenAI validation (legacy)
   - Simpler validation approach
   - Superseded by toc_chapter_validator.py
   - Described as "basic, legacy" in CLAUDE.md

2. **`toc_alignment_fixer.py`** - Fixer for legacy validator
   - Works with toc_alignment_validator.py
   - Superseded by auto_fix_toc_alignment.py

3. **`toc_auto_fix.py`** - Earlier auto-fix attempt
   - Older implementation
   - Superseded by auto_fix_toc_alignment.py

## Migration Guide

If you have scripts importing from these legacy validators:

```python
# OLD (legacy)
from utils.toc_alignment_validator import TOCAlignmentValidator

# NEW (current)
from utils.toc_chapter_validator import TOCChapterValidator
```

## Why Keep These?

These scripts are archived rather than deleted because:
- They may contain useful logic for reference
- Some older test scripts might still reference them
- Documentation purposes for understanding the evolution of the validation approach

If you need to use these legacy validators, you can import them with:

```python
from utils.legacy_toc_validators.toc_alignment_validator import TOCAlignmentValidator
```

However, we strongly recommend using the current production scripts instead.
