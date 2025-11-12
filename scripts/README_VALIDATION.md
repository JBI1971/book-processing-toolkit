# TOC/Chapter Validation Script

## Overview

Comprehensive validation script that extracts actual chapter headings from `content_blocks` to detect structural mismatches between TOC and body chapters.

## Usage

### Basic Validation

```bash
python scripts/validate_toc_chapter_alignment.py /path/to/cleaned_book.json
```

**Output**:
- Prints detailed report to console
- Saves JSON report to `cleaned_book_validation_report.json`
- Exit code: 0 if valid, 1 if errors found

### Options

```bash
# Disable AI semantic validation (faster, less accurate)
python scripts/validate_toc_chapter_alignment.py --no-ai cleaned_book.json

# Don't save report file
python scripts/validate_toc_chapter_alignment.py --no-report cleaned_book.json

# Both options
python scripts/validate_toc_chapter_alignment.py --no-ai --no-report cleaned_book.json
```

## What It Checks

### 1. TOC Coverage
- Ensures TOC exists in `structure.front_matter.toc`
- Verifies TOC has entries

### 2. Chapter Extraction
- Finds actual chapter headings in `content_blocks`
- Parses chapter numbers from headings (第N章/回)
- Supports Chinese numerals: 一二三...十廿卅卌...百千

### 3. Alignment Checks
- **Missing chapters**: TOC references chapter that doesn't exist
- **Count mismatch**: TOC entry count ≠ body chapter count
- **Title mismatch**: TOC title doesn't match actual heading
- **Sequence gaps**: Missing chapter numbers (e.g., ch 1, 2, 4 - missing 3)
- **Duplicates**: Same chapter number appears multiple times

### 4. AI Semantic Validation (Optional)
- Only for ambiguous title mismatches
- Batch processing (10 pairs per call)
- Model: gpt-4o-mini, temperature: 0.1
- Classifies: `real_mismatch`, `minor_difference`, `transcription_error`

## Example Output

### Console Report

```
================================================================================
TOC/CHAPTER ALIGNMENT VALIDATION REPORT
================================================================================

Summary: TOC Entries: 20 | Body Chapters: 19 | Matched: 19 | Confidence: 95.0% | Errors: 1
Valid: ✗ No

TOC ENTRIES (20):
   1. 第一章　神秘的年輕人
   2. 第二章　從天而降的救星
   3. 第三章　大變忽然來
   4. 第四章　計曝內奸
   5. 第五章　方豪的身分
  ... and 15 more

BODY CHAPTERS (19):
   2. 第二章　從天而降的救星 [body_chapter]
   3. 第三章　大變忽然來 [body_chapter]
   4. 第四章　計曝內奸 [body_chapter]
   5. 第五章　方豪的身分 [body_chapter]
   6. 第六章　翠雲班的解散 [body_chapter]
  ... and 14 more

ISSUES FOUND (2):
================================================================================

⚠ [WARNING] count_mismatch
   TOC has 20 entries but body has 19 chapters
   - toc_count: 20
   - chapter_count: 19
   - difference: 1

✗ [ERROR] missing_chapter
   TOC references chapter 1 '神秘的年輕人' but it's not in body
   - toc_entry: 第一章　神秘的年輕人
   - chapter_number: 1
   - toc_index: 0
   💡 Suggested fix: Check if chapter is missing from source EPUB or was incorrectly filtered

================================================================================
```

### JSON Report Structure

```json
{
  "is_valid": false,
  "summary": "TOC Entries: 20 | Body Chapters: 19 | Matched: 19 | Confidence: 95.0% | Errors: 1",
  "confidence_score": 95.0,
  "counts": {
    "toc_entries": 20,
    "body_chapters": 19,
    "matched": 19
  },
  "issues": [
    {
      "severity": "error",
      "type": "missing_chapter",
      "message": "TOC references chapter 1 '神秘的年輕人' but it's not in body",
      "details": {
        "toc_entry": "第一章　神秘的年輕人",
        "chapter_number": 1,
        "toc_index": 0
      },
      "suggested_fix": "Check if chapter is missing from source EPUB or was incorrectly filtered",
      "confidence": 0.0
    }
  ],
  "toc_entries": [
    {
      "index": 0,
      "full_title": "第一章　神秘的年輕人",
      "chapter_title": "神秘的年輕人",
      "chapter_number": 1,
      "chapter_id": "chapter_0001"
    }
  ],
  "chapter_headings": [
    {
      "index": 0,
      "chapter_id": "chapter_0002",
      "chapter_title": "第二章　從天而降的救星",
      "actual_heading": "第二章　從天而降的救星",
      "chapter_number": 2,
      "classification": "body_chapter",
      "confidence": 0.9
    }
  ]
}
```

## Issue Types

| Severity | Type | Description |
|----------|------|-------------|
| error | `missing_toc` | No TOC found in front_matter |
| error | `missing_chapters` | No chapters found in body |
| error | `missing_chapter` | TOC references chapter that doesn't exist |
| error | `duplicate_chapter_number` | Same chapter number appears multiple times |
| warning | `count_mismatch` | TOC count ≠ chapter count |
| warning | `title_mismatch` | TOC title doesn't match actual heading |
| warning | `chapter_not_in_toc` | Chapter exists but not in TOC |
| info | `sequence_gap` | Missing chapter numbers (may be intentional) |

## Integration with Pipeline

This validator is automatically run as part of Stage 6 in `batch_process_books.py`:

```python
# Stage 6: Comprehensive validation
from utils.toc_chapter_validator import TOCChapterValidator

validator = TOCChapterValidator(use_ai=True)
report = validator.validate(cleaned_json)
```

## Performance

- **Fast**: Heuristic validation completes in <1 second
- **AI calls**: Only for ambiguous mismatches (optional)
- **Batch processing**: 10 pairs per API call
- **Caching**: OpenAI responses for repeated patterns

## Environment Requirements

```bash
# Required for AI validation
export OPENAI_API_KEY=your-key-here

# Or use .env file
echo "OPENAI_API_KEY=your-key-here" > .env
```

## Troubleshooting

### OpenAI API Key Not Found
```
OPENAI_API_KEY not found in environment
```
**Solution**: Set environment variable or use `--no-ai` flag

### No Issues Found
```
✓ No issues found!
```
**Meaning**: TOC and chapters align perfectly (rare!)

### Missing Chapter Errors
```
✗ [ERROR] missing_chapter
TOC references chapter 1 but it's not in body
```
**Causes**:
1. Source EPUB is missing the chapter
2. Chapter was incorrectly filtered during cleaning
3. Book metadata was skipped by AI classifier

**Diagnosis**:
1. Check source JSON for chapter presence
2. Review AI classification confidence
3. Verify TOC is correct (may be outdated)

## Exit Codes

- `0`: Validation passed (no errors)
- `1`: Validation failed (errors found)

Use in CI/CD pipelines:
```bash
python scripts/validate_toc_chapter_alignment.py book.json || echo "Validation failed!"
```

## Related Tools

- **`utils/toc_alignment_validator.py`** - Legacy basic validator (deprecated)
- **`utils/fix_chapter_alignment.py`** - Fix EPUB metadata mismatches
- **`utils/restructure_toc.py`** - Convert TOC from blob to structured array
- **`processors/structure_validator.py`** - AI chapter classification

## See Also

- **Implementation Details**: `/TOC_VALIDATION_IMPLEMENTATION.md`
- **Documentation**: `/CLAUDE.md` (search for "Comprehensive TOC/Chapter Validator")
- **Batch Processing**: `/scripts/batch_process_books.py`
