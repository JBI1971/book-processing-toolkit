# Wuxia Glossary Integration Guide

## Overview

The wuxia glossary database (`wuxia_glossary.db`) has been successfully integrated into the translation pipeline. This ensures **consistent terminology, exact pinyin romanization, and standardized footnotes** across all translations.

## What Was Updated

### 1. Translation Service (`processors/translator.py`)

**Added Components:**
- Glossary initialization in `__init__()` with optional path parameter
- `_scan_glossary_terms()` - Scans source text for glossary matches
- `_build_glossary_context()` - Builds instructions for translator
- Enhanced `_translate_with_thread()` - Passes glossary context to OpenAI

**How It Works:**
```python
# When translating a content block:
1. Scan Chinese source text for glossary terms
2. Find up to 30 matching terms with positions
3. Build detailed glossary context with:
   - Exact recommended translation form
   - Exact pinyin (with tone marks)
   - Exact footnote template
   - Deduplication strategy
4. Pass context to translator with instructions to use EXACTLY these forms
```

**Key Features:**
- ✅ Automatic glossary term detection
- ✅ Exact form matching (no variations)
- ✅ Consistent pinyin for deduplication
- ✅ All occurrences footnoted (dedup happens later)
- ✅ Same JSON structure for glossary + custom footnotes

### 2. Book Translator (`processors/book_translator.py`)

**Integration:**
- Automatically inherits glossary from `TranslationService`
- No changes needed - glossary integration is transparent
- Works with existing checkpoint/resume functionality

### 3. Glossary Utility (`utils/wuxia_glossary.py`)

**Already Implemented:**
- `WuxiaGlossary` class for SQLite lookups
- `find_in_text()` - Pattern matching in Chinese text
- `GlossaryEntry` dataclass with all metadata
- Caching for performance
- Context manager support

## How to Use

### Basic Translation (Automatic Glossary)

```bash
# The glossary is loaded automatically from project root
python scripts/translate_work.py D58

# Or for single volume
python scripts/translate_work.py D58 --volume a
```

**Default behavior:**
- Glossary loaded from `wuxia_glossary.db` in project root
- If not found, proceeds without glossary (with warning)
- No configuration needed - just works

### Custom Glossary Path

```python
from processors.translator import TranslationService
from pathlib import Path

# Use custom glossary location
service = TranslationService(
    model='gpt-4.1-nano',
    glossary_path=Path('/custom/path/wuxia_glossary.db')
)
```

### Demonstration Scripts

**1. Simple Glossary Matching Demo**
```bash
python scripts/demo_glossary_simple.py
```

Shows:
- Glossary term detection in sample texts
- Exact forms and footnotes from database
- Translation integration example
- Statistics on matched terms

**2. Full Translation Test** (requires cleaned JSON)
```bash
python scripts/test_glossary_translation.py
```

Shows:
- Complete translation workflow
- Glossary integration in real translation
- Sample translated blocks with footnotes
- Performance metrics

## Glossary Integration Example

### Input Chinese Text:
```
他自幼修煉內功，日夜不輟，內力深厚無比。少林派的易筋經與武當派的純陽無極功，都是武林中的上乘內功心法。
```

### Detected Glossary Terms:
1. **內功** (*nèigōng*) - PINYIN_ONLY strategy
   - Position: 5
   - Form: `*nèigōng*`
   - Footnote: "Internal cultivation (內功 *nèigōng*): The practice of refining and circulating internal energy..."
   - Dedup: FIRST_OCCURRENCE_ONLY

2. **內力** (*nèilì*) - PINYIN_ONLY strategy
   - Position: 13
   - Form: `*nèilì*`
   - Footnote: "Internal force (內力 *nèilì*): The usable refined *qì* that powers strikes..."
   - Dedup: FIRST_OCCURRENCE_ONLY

3. **武林** (*wǔlín*) - PINYIN_ONLY strategy
   - Position: 40
   - Form: `*wǔlín*`
   - Footnote: "The martial community (武林 *wǔlín*): The institutional networks and formal hierarchies..."
   - Dedup: FIRST_OCCURRENCE_ONLY

4. **心法** (*xīnfǎ*) - PINYIN_ONLY strategy
   - Position: 48
   - Form: `*xīnfǎ*`
   - Footnote: "Mental doctrine (心法 *xīnfǎ*): The internal mental training formulas..."
   - Dedup: FIRST_OCCURRENCE_ONLY

### Glossary Context Sent to Translator:
```
**GLOSSARY TERMS FOUND IN THIS TEXT:**

The following wuxia/cultural terms appear in this passage. Use EXACTLY these forms and footnotes:

1. **內功** (內功)
   - Pinyin: nèigōng
   - Translation Strategy: PINYIN_ONLY
   - Recommended Form: *nèigōng*
   - Footnote Template: Internal cultivation (內功 *nèigōng*): The practice of refining...
   - Deduplication: FIRST_OCCURRENCE_ONLY

2. **內力** (內力)
   - Pinyin: nèilì
   - Translation Strategy: PINYIN_ONLY
   - Recommended Form: *nèilì*
   - Footnote Template: Internal force (內力 *nèilì*): The usable refined *qì*...
   - Deduplication: FIRST_OCCURRENCE_ONLY

[... more terms ...]

**INSTRUCTIONS:**
- Use the EXACT 'Recommended Form' when translating each term
- Use the EXACT 'Footnote Template' for footnotes
- Use the EXACT 'Pinyin' (with tone marks) for consistency
- Add footnotes for ALL occurrences (deduplication happens later)
- Ensure glossary footnotes and custom footnotes use the same JSON structure
```

### Expected Translation Output:
```json
{
  "content_text_id": 1,
  "translated_annotated_content": {
    "annotated_content_text": "From his youth he cultivated *nèigōng*[1], practicing day and night without rest, his *nèilì*[2] becoming incomparably deep. Both Shaolin's *Yi Jin Jing* and Wudang's Pure Yang Infinite Skill were supreme *nèigōng* *xīnfǎ*[3] of the *wǔlín*[4].",
    "content_footnotes": [
      {
        "footnote_key": 1,
        "footnote_details": {
          "footnote_ideogram": "內功",
          "footnote_pinyin": "nèigōng",
          "footnote_explanation": "Internal cultivation (內功 *nèigōng*): The practice of refining and circulating internal energy (*qì*) through meditation, breathing techniques, and meridian conditioning. Fundamental to Chinese martial arts."
        }
      },
      {
        "footnote_key": 2,
        "footnote_details": {
          "footnote_ideogram": "內力",
          "footnote_pinyin": "nèilì",
          "footnote_explanation": "Internal force (內力 *nèilì*): The usable refined *qì* that powers strikes, defenses, and supernatural feats. A martial artist's *nèilì* determines their combat effectiveness."
        }
      },
      {
        "footnote_key": 3,
        "footnote_details": {
          "footnote_ideogram": "心法",
          "footnote_pinyin": "xīnfǎ",
          "footnote_explanation": "Mental doctrine (心法 *xīnfǎ*): The internal mental training formulas that guide *qì* cultivation and meditation. The theoretical foundation underlying martial techniques."
        }
      },
      {
        "footnote_key": 4,
        "footnote_details": {
          "footnote_ideogram": "武林",
          "footnote_pinyin": "wǔlín",
          "footnote_explanation": "The martial community (武林 *wǔlín*): The institutional networks and formal hierarchies of martial society, more structured than *jiānghú*. Literally 'martial forest.'"
        }
      }
    ]
  }
}
```

## Benefits of Integration

### 1. Consistency Across Books
- ✅ Same term always translates the same way
- ✅ Same pinyin romanization (e.g., always "nèigōng", never "nei gong")
- ✅ Same footnote explanation for recurring concepts

### 2. Deduplication Support
- ✅ Exact pinyin enables later deduplication
- ✅ Deduplication strategy tracked per term
- ✅ First occurrence vs recurring brief vs every occurrence

### 3. Translation Quality
- ✅ Standardized wuxia terminology
- ✅ Comprehensive cultural explanations
- ✅ Appropriate translation strategy per term (pinyin/English/hybrid)

### 4. Efficiency
- ✅ Translator doesn't need to invent new footnotes
- ✅ Glossary handles 186 common terms automatically
- ✅ Reduces variation in AI responses

## Glossary Statistics

**Total Terms:** 186

**Categories:**
- technique_category: 30 terms (內功, 輕功, 劍法, etc.)
- concept: 25 terms (內力, 真氣, 經脈, etc.)
- world: 15 terms (江湖, 武林, etc.)
- organization: 12 terms (門派, 幫派, etc.)
- title: 35 terms (前輩, 師父, 大俠, etc.)
- relationship: 25 terms (兄, 妹, 師兄, etc.)
- general: 20 terms (武功, 武藝, etc.)
- doctrine: 8 terms (心法, 秘笈, etc.)
- technique: 16 terms (招式, 劍招, etc.)

**Frequency Distribution:**
- VERY_HIGH: 62 terms (內功, 內力, 江湖, 輕功, etc.)
- HIGH: 48 terms (武林, 心法, 劍法, etc.)
- MEDIUM: 42 terms (劍氣, 真氣, etc.)
- LOW: 34 terms (specific techniques, rare terms)

**Translation Strategies:**
- PINYIN_ONLY: 98 terms (內功 → *nèigōng*)
- ENGLISH_ONLY: 52 terms (武功 → martial arts)
- HYBRID: 36 terms (combining both)

## Architecture

```
Translation Request Flow:
┌─────────────────────────────────────────────────────────────┐
│ 1. BookTranslator receives content block                    │
│    - Chinese source text                                    │
│    - Block ID and metadata                                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. TranslationService.translate()                           │
│    - Calls _scan_glossary_terms(source_text)                │
│    - WuxiaGlossary.find_in_text() → List[GlossaryEntry]     │
│    - Up to 30 terms matched by position                     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Build Glossary Context                                   │
│    - _build_glossary_context(matches)                       │
│    - Format detailed instructions:                          │
│      * Exact recommended form                               │
│      * Exact pinyin with tone marks                         │
│      * Exact footnote template                              │
│      * Deduplication strategy                               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. OpenAI Translation                                       │
│    - _translate_with_thread(request, glossary_matches)      │
│    - System prompt + user message + glossary context        │
│    - Translator uses EXACT forms from glossary              │
│    - Returns JSON with translation + footnotes              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Validation                                               │
│    - _validate_with_thread(response)                        │
│    - Checks glossary adherence                              │
│    - Verifies pinyin consistency                            │
│    - Returns quality score and issues                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Output                                                   │
│    - TranslationResponse with:                              │
│      * Translated text with [n] markers                     │
│      * Footnotes (glossary + custom)                        │
│      * All using same JSON structure                        │
└─────────────────────────────────────────────────────────────┘
```

## Testing

### Quick Test: Glossary Matching Only
```bash
# Fast demonstration without actual translation
python scripts/demo_glossary_simple.py
```

Output shows:
- Sample wuxia texts
- Detected glossary terms with full metadata
- Translation integration example
- Statistics on matched terms

### Full Test: Complete Translation
```bash
# Requires cleaned JSON and API key
export OPENAI_API_KEY=your-key-here
python scripts/test_glossary_translation.py
```

Output shows:
- Complete book translation
- Glossary integration in real output
- Sample translated blocks
- Performance metrics

## Troubleshooting

### Glossary Not Loading
```
WARNING - Wuxia glossary not found at wuxia_glossary.db, proceeding without glossary
```

**Solution:**
- Ensure `wuxia_glossary.db` exists in project root
- Or specify custom path in config
- Database created by `scripts/deduplicate_wuxia_glossary.py`

### No Terms Matched
```
INFO - Found 0 glossary terms in source text
```

**Solution:**
- Check if text contains actual wuxia terms
- Glossary has 186 terms, may not cover all vocabulary
- Custom footnotes will still be created for non-glossary terms

### Inconsistent Pinyin
```
WARNING - Pinyin mismatch: expected "nèigōng" but got "nei gong"
```

**Solution:**
- This is caught by validation
- Translation will be retried with exact glossary pinyin
- Ensures deduplication works correctly

## Next Steps

### Deduplication Pipeline
After translation, a separate deduplication stage will:
1. Scan all translated blocks across entire book
2. Identify duplicate footnotes using exact pinyin matching
3. Keep only first occurrence (or apply other strategies)
4. Remove redundant footnotes from later occurrences

**Example:**
- Block 1: "內功" → Full footnote
- Block 5: "內功" → Brief reference or removed
- Block 10: "內功" → Brief reference or removed

### Glossary Expansion
To add more terms:
```bash
# Edit wuxia_translation_glossary.csv
# Add new rows with required fields
# Run deduplication script
python scripts/deduplicate_wuxia_glossary.py

# This regenerates wuxia_glossary.db
# No code changes needed - translation picks up new terms automatically
```

## Files Modified

1. **processors/translator.py**
   - Added glossary initialization
   - Added `_scan_glossary_terms()`
   - Added `_build_glossary_context()`
   - Enhanced `_translate_with_thread()` with glossary support

2. **scripts/demo_glossary_simple.py** (new)
   - Demonstrates glossary matching
   - Shows sample translations
   - Explains integration benefits

3. **scripts/test_glossary_translation.py** (new)
   - Full translation test
   - Real book processing
   - Sample output analysis

4. **WUXIA_GLOSSARY_INTEGRATION_GUIDE.md** (this file)
   - Complete integration documentation
   - Usage examples
   - Architecture diagrams

## Related Documentation

- **WUXIA_TRANSLATION_EXAMPLES.md** - Example translations with glossary terms
- **GLOSSARY_UPDATE_CHANGELOG.md** - Glossary update history
- **wuxia_deduplication_guide.md** - Deduplication strategy reference
- **utils/wuxia_glossary.py** - Glossary API documentation

## Summary

✅ **Glossary successfully integrated into translation pipeline**
✅ **Automatic term detection and matching**
✅ **Exact forms and footnotes from database**
✅ **Consistent pinyin for deduplication**
✅ **No configuration needed - just works**

The translation service now provides consistent, high-quality wuxia translations with standardized terminology and comprehensive cultural annotations.
