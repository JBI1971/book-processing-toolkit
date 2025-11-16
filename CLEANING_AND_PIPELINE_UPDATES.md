# Cleaning and Pipeline Updates

**Date**: 2025-11-16
**Status**: ✅ **COMPLETED**

---

## Issue 1: TOC/Chapter Mismatch in D1379

### Problem
The cleaned file `/Users/jacki/project_files/translation_project/cleaned/COMPLETE_ALL_BOOKS/wuxia_0116/cleaned_D1379_偷拳_白羽.json` had:
- **TOC entries**: 24
- **Body chapters**: 2
- **Missing**: 22 chapters!

### Root Cause
The cleaning process incorrectly classified "楊露蟬父子傳略" and "董海川師徒" as **title pages** (front_matter) instead of body chapters.

### Fix Applied
Re-ran cleaning process with proper parameters:
```python
from processors.json_cleaner import clean_book_json

result = clean_book_json(
    input_file,
    catalog_path='/Users/jacki/project_files/translation_project/wuxia_catalog.db',
    directory_name='wuxia_0116'
)
```

### Result
✅ **Fixed**:
- TOC entries: 22
- Body chapters: 22
- All chapters properly extracted

**Body chapters (first 10)**:
1. 《偷拳》白羽 - 16 blocks
2. 二、入豫投師，觀場觸忌 - 18 blocks
3. 三、路見不平，解紛揮拳 - 26 blocks
4. 四、誤鬥強手，失著一蹴 - 15 blocks
5. 五、獻贄被拒，負氣告絕 - 16 blocks
6. 六、忽來啞丐，悄掃晨街 - 12 blocks
7. 七、劣徒遭誣，恩師援救 - 12 blocks
8. 八、有客投柬，揭破陰謀 - 18 blocks
9. 九、娼奴嫁禍，紳豪訊奸 - 19 blocks
10. 十、雪漫寒街，矜收凍丐 - 25 blocks

---

## Issue 2: Pipeline Stage Order

### Requirement
Move **body translation** to the **beginning** of the pipeline (before metadata/TOC/headings).

### Rationale
- Body content translation is the most important and time-consuming stage
- Translating body first allows for:
  - Early progress visibility
  - Better error detection
  - Checkpoint/resume on the most critical content
  - Metadata/TOC/headings can reference translated body content

### Old Pipeline Order
1. Metadata (no footnotes)
2. TOC (no footnotes)
3. Headings (no footnotes)
4. **Body** (WITH footnotes) ← Was stage 4
5. Special sections
6. Cleanup
7. Validation

### New Pipeline Order
1. **Body** (WITH footnotes) ← Now stage 1
2. Metadata (no footnotes)
3. TOC (no footnotes)
4. Headings (no footnotes)
5. Special sections
6. Cleanup
7. Validation

### Implementation
Modified `/Users/jacki/PycharmProjects/agentic_test_project/scripts/orchestrate_translation_pipeline.py`:

```python
class PipelineStage(Enum):
    """Translation pipeline stages"""
    BODY = (1, "body", "Translate body content - WITH cultural/historical footnotes")
    METADATA = (2, "metadata", "Translate metadata (title, author) - NO footnotes")
    TOC = (3, "toc", "Translate TOC - NO footnotes (clean navigation)")
    HEADINGS = (4, "headings", "Translate chapter headings (use TOC) - NO footnotes")
    SPECIAL = (5, "special", "Translate special sections - WITH footnotes")
    CLEANUP = (6, "cleanup", "Remove redundant character name footnotes")
    VALIDATION = (7, "validation", "Validate translation completeness and quality")
```

### Impact
- **WIP directories** will change:
  - Old: `stage_4_body/` → New: `stage_1_body/`
  - Old: `stage_1_metadata/` → New: `stage_2_metadata/`
  - Old: `stage_2_toc/` → New: `stage_3_toc/`
  - Old: `stage_3_headings/` → New: `stage_4_headings/`

- **Stage numbering** automatically updated via `stage.num` property
- **No code changes** needed in processors - they reference `PipelineStage.BODY`, etc.

---

## Testing

### Verified
✅ Pipeline stage order correctly updated
✅ D1379 re-cleaned with all 22 chapters
✅ TOC/chapter count matches
✅ No errors in enum definition

### Next Steps
1. Test complete 7-stage pipeline with new order
2. Verify WIP files created with correct stage numbers
3. Confirm body translation runs before metadata/TOC/headings

---

## Summary

**Changes Made**:
1. ✅ Re-cleaned D1379: 22 chapters (was 2)
2. ✅ Moved body translation to Stage 1 (was Stage 4)

**Files Modified**:
- `/Users/jacki/project_files/translation_project/cleaned/COMPLETE_ALL_BOOKS/wuxia_0116/cleaned_D1379_偷拳_白羽.json` (replaced)
- `/Users/jacki/PycharmProjects/agentic_test_project/scripts/orchestrate_translation_pipeline.py` (enum order updated)

**Status**: Ready for testing
