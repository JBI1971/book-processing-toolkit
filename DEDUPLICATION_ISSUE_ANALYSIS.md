# Footnote Deduplication Issue - Root Cause Analysis

**Date**: 2025-11-16
**Test**: Complete 7-stage pipeline on D1379
**Stage 6 Result**: **Removed 0 footnotes** (should have removed ~40-50)

---

## ✅ What's Working

1. **Pinyin with tone marks in English text**: ✓ FIXED
   - Example: "Yáng Lùchán[1]" (correct)
   - NOT: "Yang Luchan[1]" (old broken way)

2. **Stage 6 executes without crashing**: ✓ FIXED
   - Fixed `output_path` parameter issue
   - Fixed `CleanupResult` attribute names

3. **All 7 stages complete successfully**: ✓
   - Duration: 362 seconds (~6 minutes)
   - All WIP files created

---

## ❌ What's NOT Working

### Issue: AI Classification Failing

**Problem**: All 132 footnotes classified as "CULTURAL", **ZERO** identified as character names

**Evidence from logs**:
```
2025-11-16 02:21:27,243 - WARNING - Missing classification for footnote 1, defaulting to CULTURAL
2025-11-16 02:21:27,243 - WARNING - Missing classification for footnote 2, defaulting to CULTURAL
...
(repeated for ALL footnotes)

Result:
  Removed 0 redundant character footnotes
  Preserved 132 cultural/historical footnotes
```

**Actual Footnotes** (should be classified as CHARACTER NAMES):
```json
{
  "key": 1,
  "ideogram": "楊露蟬",
  "pinyin": "Yáng Lùchán",
  "explanation": "A legendary martial artist and teacher known for his skill in tàijíquán..."
}
```
**This is clearly a CHARACTER NAME, not a cultural term!**

---

## Root Cause

The `CharacterFootnoteCleanup` service uses OpenAI to classify footnotes into categories:
- FICTIONAL_CHARACTER
- HISTORICAL_FIGURE
- LEGENDARY_PERSONAGE
- CULTURAL

**What's happening**:
1. OpenAI API is called to classify footnotes in batches
2. API response is not being parsed correctly
3. All classifications default to "CULTURAL"
4. Since no character names are identified, nothing is removed

**Evidence**:
```
2025-11-16 02:24:20,304 - ERROR - Failed to parse OpenAI response: Expecting ',' delimiter: line 20 column 32581 (char 33306)
```

The AI response is malformed JSON and can't be parsed!

---

## Why Deduplication Didn't Happen

**Current behavior**:
```
Total footnotes: 132
Character names identified: 0  ❌ (should be ~80-90)
Cultural terms identified: 132
```

**Expected behavior**:
```
Total footnotes: 132
Character names identified: ~80-90
Cultural terms identified: ~40-50

Deduplication:
- Remove duplicate character name footnotes (keep first occurrence only)
- Preserve all cultural/historical footnotes
- Expected removal: ~40-50 footnotes
```

---

## Examples of What Should Be Deduplicated

### Example 1: Character Name Appears Multiple Times

**Block content**:
```
"Yáng Lùchán[1], also known as Lù Shàn[2]... Yáng Lùchán[1] was greatly ashamed..."
```

**Footnote 1** (楊露蟬):
```json
{
  "key": 1,
  "ideogram": "楊露蟬",
  "pinyin": "Yáng Lùchán",
  "explanation": "A legendary martial artist and teacher..."
}
```

**Problem**: This footnote should ONLY appear on the FIRST occurrence of "Yáng Lùchán" in the block. The second "[1]" marker should be removed.

**Current**: Both markers present (no deduplication)
**Expected**: Only first marker present

---

### Example 2: Character vs Cultural Term

**Character Name** (should be deduplicated):
```json
{
  "ideogram": "楊露蟬",
  "explanation": "A legendary martial artist and teacher..."
}
```
→ Classification: LEGENDARY_PERSONAGE or HISTORICAL_FIGURE
→ Action: Remove duplicates within same block

**Cultural Term** (should be preserved):
```json
{
  "ideogram": "太極拳",
  "explanation": "Taijíquán, also called Tai Chi Chuan, is a traditional Chinese internal martial art..."
}
```
→ Classification: CULTURAL
→ Action: Keep all occurrences

---

## Technical Details

### Location of Issue

**File**: `utils/cleanup_character_footnotes.py`

**Method**: `_classify_footnotes_batch()`

**Problem Areas**:
1. OpenAI prompt may not be clear enough about what constitutes a character name
2. Response parsing is failing (malformed JSON)
3. Fallback behavior (default to CULTURAL) means nothing gets deduplicated

---

## Suggested Fixes

### Option 1: Improve OpenAI Classification Prompt

**Current approach**: Send footnotes to OpenAI and ask it to classify

**Issue**: Prompt might not be specific enough, or model is returning malformed JSON

**Fix**:
- Make prompt more explicit about character name vs cultural term
- Add examples of each category
- Request structured JSON with strict schema
- Add validation to catch malformed responses

### Option 2: Use Heuristic Classification

**Instead of relying on AI**, use simple heuristics:

```python
def is_character_name(footnote):
    # Character names typically have:
    # - 2-4 character ideogram (楊露蟬, 陳清平)
    # - Explanation mentions "martial artist", "teacher", "master", "disciple"
    # - Short explanation (<100 chars)

    ideogram_len = len(footnote['ideogram'])
    explanation = footnote['explanation'].lower()

    # Heuristic rules
    is_person = any(word in explanation for word in [
        'martial artist', 'teacher', 'master', 'disciple',
        'student', 'warrior', 'fighter', 'practitioner'
    ])
    is_short_name = 2 <= ideogram_len <= 4
    is_brief_explanation = len(explanation) < 150

    return is_person and is_short_name and is_brief_explanation
```

**Advantages**:
- Fast (no API calls)
- Deterministic (same input always gives same output)
- No parsing errors

**Disadvantages**:
- Less accurate than AI (might misclassify edge cases)
- Requires manual tuning of heuristics

### Option 3: Hybrid Approach

1. Use heuristics first (fast, cheap)
2. If unsure, use AI to classify (slow, expensive)
3. Fall back to heuristic result if AI fails

---

## Immediate Next Steps

1. **Investigate why OpenAI response is malformed**
   - Check the classification prompt
   - Look at response structure
   - Add better error handling

2. **Add diagnostic logging**
   - Log the exact OpenAI request and response
   - Show which footnotes are being classified as what
   - Make it visible when default classification is used

3. **Consider heuristic approach**
   - Might be faster and more reliable
   - Could be a good fallback if AI fails

---

## Summary

| Component | Status | Details |
|-----------|--------|---------|
| Pinyin with tones | ✅ WORKING | "Yáng Lùchán" not "Yang Luchan" |
| Stage 6 execution | ✅ WORKING | No crashes, completes successfully |
| AI classification | ❌ BROKEN | All footnotes defaulting to CULTURAL |
| Deduplication | ❌ NOT HAPPENING | 0 footnotes removed (should be ~40-50) |

**Root Cause**: OpenAI API response parsing fails → all footnotes default to CULTURAL → no character names identified → no deduplication

**Impact**: Translated output has redundant character name footnotes, making reading experience cluttered

**Priority**: HIGH - This defeats the purpose of the cleanup stage
