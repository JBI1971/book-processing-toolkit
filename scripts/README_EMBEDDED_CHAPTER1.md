# Fix Embedded Chapter 1 Script

## Overview

This script fixes a common issue in Chinese book JSON files where Chapter 1 is embedded inside the title page or introduction section instead of being in the body chapters.

## Problem Pattern

Many Chinese wuxia novels have this structure:

```
front_matter:
  sections:
    - introduction: "《Book Title》Author"
        blocks:
          - "《Book Title》Author"
          - "Version info"
          - "一、Chapter 1 Title"  ← This should be in body!
          - [Chapter 1 content...]
body:
  chapters:
    - Chapter 2
    - Chapter 3
    - ...
```

**Result**: Missing Chapter 1 in body, TOC starts at Chapter 2

## Solution

The script automatically:
1. Finds introduction sections (in multiple possible locations)
2. Detects Chinese chapter markers (一、二、三...)
3. Extracts Chapter 1 from introduction
4. Creates proper chapter structure
5. Updates TOC with Chapter 1 entry
6. Cleans introduction (removes story content)

## Usage

### Basic Usage (Overwrites Original)

```bash
python scripts/fix_embedded_chapter1.py <input_file>
```

### With Separate Output

```bash
python scripts/fix_embedded_chapter1.py <input_file> <output_file>
```

### Example

```bash
# Fix in place
python scripts/fix_embedded_chapter1.py \
  /path/to/cleaned_D1379_偷拳_白羽.json

# Save to new file
python scripts/fix_embedded_chapter1.py \
  /path/to/cleaned_D1379_偷拳_白羽.json \
  /path/to/fixed_D1379_偷拳_白羽.json
```

## What Gets Fixed

### Before

```json
{
  "structure": {
    "front_matter": {
      "toc": {
        "entries": [
          {"chapter_number": 2, "title": "二、..."},
          {"chapter_number": 3, "title": "三、..."}
        ]
      },
      "sections": [
        {
          "type": "introduction",
          "content_blocks": [
            {"content": "Book Title"},
            {"content": "一、Chapter 1 Title"},
            {"content": "Chapter 1 story content..."}
          ]
        }
      ]
    },
    "body": {
      "chapters": [
        {"ordinal": 2, "title": "二、..."},
        {"ordinal": 3, "title": "三、..."}
      ]
    }
  }
}
```

### After

```json
{
  "structure": {
    "front_matter": {
      "toc": {
        "entries": [
          {"chapter_number": 1, "chapter_id": "chapter_0001", "title": "一、..."},
          {"chapter_number": 2, "chapter_id": "chapter_0002", "title": "二、..."},
          {"chapter_number": 3, "chapter_id": "chapter_0003", "title": "三、..."}
        ]
      },
      "sections": [
        {
          "type": "introduction",
          "content_blocks": [
            {"content": "Book Title"}
          ]
        }
      ]
    },
    "body": {
      "chapters": [
        {"ordinal": 1, "id": "chapter_0001", "title": "一、...", "content_blocks": [...]},
        {"ordinal": 2, "id": "chapter_0002", "title": "二、..."},
        {"ordinal": 3, "id": "chapter_0003", "title": "三、..."}
      ]
    }
  }
}
```

## Features

### Chinese Numeral Support

Handles all Chinese numerals including special cases:

- Basic: 一 (1), 二 (2), 三 (3), 四 (4), 五 (5), 六 (6), 七 (7), 八 (8), 九 (9), 十 (10)
- Special: 廿 (20), 卅 (30), 卌 (40)
- Compounds: 廿一 (21), 卅五 (35), 卌八 (48)
- Large: 百 (100), 千 (1000)

### Flexible Location Detection

Searches for introduction in:
1. `front_matter.introduction`
2. `front_matter.sections` (where type="introduction")
3. `front_matter.toc` (where type="introduction")

### Automatic TOC Update

- Inserts Chapter 1 entry at beginning
- Updates all chapter_id references
- Renumbers chapter_number fields
- Maintains TOC/body alignment

### Block ID Renumbering

- Chapter 1 blocks: block_0000, block_0001, ...
- Existing chapters keep their block numbering
- Sequential and consistent

## Output

### Console Output

```
Processing: /path/to/file.json
Found Chapter 1 at block index 3 in introduction section
Chapter 1 title: 一、弱齡習武，志訪絕學
Extracted 13 blocks for Chapter 1
Remaining 3 blocks in introduction
Created 22 chapters (1 extracted + 21 existing)
Updated TOC with 22 entries (1 new + 21 existing)

Saved to: /path/to/file.json

Final structure:
  Total chapters: 22
    - Chapter 1: 一、弱齡習武，志訪絕學
    - Chapter 2: 二、入豫投師，觀場觸忌
    - Chapter 3: 三、路見不平，解紛揮拳
    - Chapter 4: 四、誤鬥強手，失著一蹴
    - Chapter 5: 五、獻贄被拒，負氣告絕
    ... and 17 more
```

### No Changes Needed

```
Processing: /path/to/file.json
No introduction section found.
No changes needed.
```

Or:

```
Processing: /path/to/file.json
No embedded Chapter 1 found in introduction.
No changes needed.
```

## Verification

After running, the script ensures:

✓ Chapter 1 exists in body.chapters
✓ Chapter 1 in TOC with correct chapter_id
✓ TOC count == body chapter count
✓ Introduction cleaned (no story content)
✓ All chapter ordinals sequential (1, 2, 3, ...)
✓ All chapter IDs sequential (chapter_0001, chapter_0002, ...)

## Integration

This script can be:

1. **Run manually** on individual files
2. **Integrated into batch pipeline** as Stage 3.5
3. **Added to json_cleaner.py** as automatic detection

### Suggested Pipeline Integration

```
Stage 3: JSON Cleaning
  ↓
Stage 3.5: Extract Embedded Chapter 1 (NEW)
  ↓
Stage 4: Chapter Alignment
  ↓
Stage 5: TOC Restructuring
```

## Related Files

- **Script**: `/Users/jacki/PycharmProjects/agentic_test_project/scripts/fix_embedded_chapter1.py`
- **Summary**: `/Users/jacki/PycharmProjects/agentic_test_project/CHAPTER1_EXTRACTION_SUMMARY.md`
- **Test Case**: D1379 《偷拳》白羽

## Dependencies

- Python 3.6+
- Standard library only (json, re, pathlib, typing)

No external dependencies required.

## Error Handling

The script is safe to run multiple times on the same file:
- If Chapter 1 already extracted: "No embedded Chapter 1 found"
- If no introduction section: "No introduction section found"
- If file doesn't exist: Error message with file path

## Future Enhancements

Potential improvements:
- Detect Chapter 0 (序章/楔子 = prologue)
- Handle multiple embedded chapters
- Support alternative chapter markers (第N回, 第N節)
- Auto-detect and fix all books in a directory
