# Footnote Deduplication Fixes - Complete Summary

**Date**: 2025-11-16
**Status**: ✅ **ALL FIXES IMPLEMENTED AND TESTED**

---

## Issues Fixed

### 1. ✅ Pinyin with Tone Marks in English Text

**Issue**: English translations showed "Yang Luchan[1]" instead of "Yáng Lùchán[1]"

**Fix**: Updated translation prompt in `processors/translator.py` (lines 66-72)

**Result**: English text now correctly uses pinyin with diacritical marks (ā, á, ǎ, à)

**Example**:
- ❌ Before: "Yang Luchan[1] traveled to Henan..."
- ✅ After: "Yáng Lùchán[1] traveled to Hénán..."

---

### 2. ✅ Work-wide Deduplication by Ideogram

**Issue**: Footnotes were only deduplicated within individual blocks, allowing duplicates across the entire work

**Requirement**: Deduplication should work **across the entire work** by ideogram, keeping only the first occurrence

**Fix**: Modified `utils/cleanup_character_footnotes.py` (lines 436-465)

**Changes**:
```python
# Before: Per-block deduplication
seen_ideograms = set()  # Reset for each block

# After: Work-wide deduplication
seen_ideograms_global = set()  # Track across ALL chapters
```

**Result**:
- Removed **22-35 duplicate footnotes** across entire work (was 0 before)
- Only **first occurrence** of each ideogram is kept
- Subsequent occurrences of same ideogram have NO footnote

**Example**:
- Chapter 1, Block 1: "Yáng Lùchán[1]" → footnote defined
- Chapter 1, Block 5: "Yáng Lùchán" → NO footnote marker (duplicate removed)

---

### 3. ✅ Footnote Marker Renumbering

**Issue**: Footnote markers needed to be renumbered sequentially within each block after deduplication

**Fix**: Existing logic already handled this (lines 497-499)

**Result**: Each block's footnotes are numbered [1], [2], [3]... regardless of global deduplication

**Example**:
```json
Block A: [1] ideogram1, [2] ideogram2, [3] ideogram3
Block B: [1] ideogram4, [2] ideogram5  // Renumbered from 1
```

---

### 4. ✅ Duplicate Marker Removal from Translated Text

**Issue**: When a character name appeared multiple times in the same block, the translator created:
- ✅ Only **one** footnote entry (correct)
- ❌ Multiple `[1]` markers in the text (incorrect - creates orphaned markers)

**Example Problem**:
```
Text: "Yáng Lùchán[1] fought... Later Yáng Lùchán[1] won..."
Footnotes: [1] 杨露蟾
```
→ Second `[1]` marker has no corresponding footnote!

**Fix**: Added duplicate marker removal logic (lines 501-520)

**Logic**:
1. After renumbering footnotes, scan `translated_content`
2. Track which markers have been seen
3. Keep only **first occurrence** of each marker `[N]`
4. Remove subsequent occurrences of same marker

**Result**: Each marker `[N]` appears exactly once in the text, matching the footnote count

**Verification**:
- ✅ All 16 blocks checked
- ✅ 0 blocks with duplicate markers
- ✅ Marker count matches footnote count in every block

---

## Technical Implementation

### File Modified: `utils/cleanup_character_footnotes.py`

**Line 437**: Changed from `seen_ideograms = set()` (per-block) to `seen_ideograms_global = set()` (work-wide)

**Lines 450-465**: Work-wide deduplication check
```python
# Check if this ideogram has appeared anywhere in the work before
if ideogram in seen_ideograms_global:
    # This is a duplicate across the entire work - remove it
    self.result.removed_footnotes.append({
        'ideogram': ideogram,
        'type': 'DUPLICATE',
        'reasoning': f"Duplicate occurrence of '{ideogram}' (already appeared earlier in work)"
    })
    self.result.removed_count += 1
    continue  # Skip this duplicate footnote

# Mark this ideogram as seen globally
seen_ideograms_global.add(ideogram)
```

**Lines 501-520**: Duplicate marker removal
```python
# Remove duplicate markers from translated_content
translated_content = block.get('translated_content', '')
if translated_content:
    seen_markers = set()

    def replace_marker(match):
        marker = match.group(1)
        if marker in seen_markers:
            return ''  # Remove duplicate
        else:
            seen_markers.add(marker)
            return match.group(0)  # Keep first occurrence

    block['translated_content'] = re.sub(r'\[(\d+)\]', replace_marker, translated_content)
```

---

## Test Results

### Test Book: D1379 (偷拳 by 白羽)

**Before Fixes**:
- Total footnotes: 167
- Duplicates removed: 0
- Duplicate markers: Multiple blocks with duplicate `[1]`, `[2]`, `[3]` markers
- Pinyin: "Yang Luchan" (no tone marks)

**After Fixes**:
- Total footnotes: 132 (unique)
- Duplicates removed: 35
- Duplicate markers: 0 blocks with duplicates
- Pinyin: "Yáng Lùchán" (with tone marks)

### Detailed Verification

**Block_0004 Example** (had duplicate `[1]` marker):

Before cleanup:
```
Text: "Yáng Lùchán[1] perfected... whenever Yáng Lùchán[1] threw..."
Footnotes: 8
Markers in text: 9 (including duplicate [1])
```

After cleanup:
```
Text: "Yáng Lùchán[1] perfected... whenever Yáng Lùchán threw..."
Footnotes: 8
Markers in text: 8 (duplicate [1] removed)
```

---

## Integration Test Results

**Complete 7-Stage Pipeline Test**:
- Duration: 159 seconds
- ✅ All stages completed successfully
- ✅ Stage 6 cleanup: Removed 35 duplicates, preserved 132 unique
- ✅ No orphaned markers
- ✅ Pinyin with tone marks working
- ✅ Final output validated

---

## Summary

All requested fixes have been successfully implemented:

1. ✅ **Pinyin with tone marks** in English text
2. ✅ **Work-wide deduplication** by ideogram (not per-block)
3. ✅ **Footnote marker renumbering** within each block
4. ✅ **Duplicate marker removal** from translated content

The footnote cleanup system now:
- Removes **ALL duplicate footnotes** across the entire work
- Keeps only the **first occurrence** of each ideogram
- Renumbers footnote markers sequentially within each block
- Removes orphaned markers from translated text
- Uses pinyin with proper diacritical marks

**Status**: Ready for production use.
