# Translation Pipeline Specification

**Version**: 1.0.0
**Last Updated**: 2025-01-15
**Purpose**: Master specification for the book translation pipeline architecture

This document defines the authoritative rules, policies, and architecture for the translation pipeline. All translation agents and services MUST adhere to these specifications.

---

## Table of Contents

1. [Pipeline Architecture](#pipeline-architecture)
2. [Translation Workflow Stages](#translation-workflow-stages)
3. [Translation Rules and Policies](#translation-rules-and-policies)
4. [Footnote Policy](#footnote-policy)
5. [Quality Standards](#quality-standards)
6. [WIP (Work-In-Progress) Management](#wip-management)
7. [Error Handling and Recovery](#error-handling-and-recovery)
8. [Integration Points](#integration-points)
9. [Performance Requirements](#performance-requirements)
10. [Validation Requirements](#validation-requirements)

---

## Pipeline Architecture

### Overall Flow

```
CLEANED JSON (from json-book-restructurer)
   ↓
[Stage 7] Translation Service
   → Translate metadata (NO footnotes)
   → Translate TOC (NO footnotes)
   → Translate chapter headings (use TOC, NO footnotes)
   → Translate body content (WITH cultural footnotes)
   → Translate special sections (WITH footnotes)
   → Save WIP after each substage
   ↓
[Stage 8] Footnote Cleanup
   → Remove redundant character name footnotes
   → Deduplicate footnotes by ideogram
   → Save cleaned output
   ↓
[Stage 9] Quality Validation
   → Verify translation completeness
   → Check footnote integrity
   → Validate pinyin tone marks
   → Generate QA report
   ↓
[Stage 10] EPUB Generation (future)
   → Convert to EPUB 3.0 format
   → Apply formatting rules
   → Embed footnotes
   ↓
FINAL OUTPUT (translated EPUB)
```

### Service Components

1. **TranslationService** (`processors/translator.py`)
   - Core translation engine
   - Integrates with wuxia glossary
   - Two-pass editorial validation
   - Type-aware translation (12 semantic content types)

2. **JobManager** (`utils/translation_job_manager.py`)
   - Job queue management
   - State persistence (SQLite)
   - Pause/resume capability
   - Recovery from failures

3. **ProgressTracker** (`utils/translation_progress_tracker.py`)
   - Real-time progress monitoring
   - Token usage tracking
   - ETA calculation
   - Detailed metrics reporting

4. **WIPManager** (`utils/wip_manager.py`)
   - Incremental saves at each stage
   - Rollback capability
   - Stage comparison tools
   - Resume from checkpoints

5. **FootnoteOptimizer** (`utils/cleanup_character_footnotes.py`)
   - Remove redundant character name explanations
   - Deduplicate by ideogram
   - Preserve unique cultural annotations

6. **QAValidator** (`utils/translation_qa.py`)
   - Automated quality checks
   - Completeness verification
   - Format validation
   - Quality scoring

---

## Translation Workflow Stages

### Stage 7: Translation Service

The translation stage processes content in this **specific order**:

#### 7.1 Metadata Translation (NO FOOTNOTES)

**Input**: `meta` section from cleaned JSON
**Process**:
- Translate `title` (Chinese → English)
- Translate `author` (Chinese → English)
- Preserve `work_number`, `language`, `schema_version`, `volume` unchanged
- **NO footnotes** - metadata must be clean for UI display and EPUB metadata

**Output**: Translated metadata in same structure

**Rationale**: Metadata appears in file browsers, EPUB readers, and UI listings. Footnote markers would break these contexts.

#### 7.2 TOC Translation (NO FOOTNOTES)

**Input**: `structure.front_matter.toc` entries
**Process**:
- Translate each TOC entry's `chapter_title` and `full_title`
- Preserve `chapter_number` and `chapter_id` unchanged
- **NO footnotes** - TOC is navigation, must remain clean
- Establish canonical chapter title translations for consistency

**Output**: Translated TOC entries

**Rationale**: TOC is navigation structure for EPUB. Footnote markers would clutter the table of contents and break hyperlinks.

**Consistency Requirement**: These translations become the **canonical chapter titles** used throughout the book.

#### 7.3 Chapter Heading Translation (NO FOOTNOTES)

**Input**: `structure.body.chapters[].title` fields
**Process**:
- Use TOC translations as canonical source
- Match chapter title to TOC entry by `chapter_number` or fuzzy matching
- Apply TOC translation to chapter heading
- **NO footnotes** - headings must match TOC exactly

**Output**: Translated chapter headings matching TOC

**Rationale**: Chapter headings must match TOC translations for consistency. Readers should see identical text in TOC and chapter headings. Footnote markers would break this consistency.

**Critical**: If chapter heading has extra decorative elements (e.g., "☆第一章☆"), preserve decorators but use TOC translation for chapter title portion.

#### 7.4 Body Content Translation (WITH CULTURAL FOOTNOTES)

**Input**: `structure.body.chapters[].content_blocks`
**Process**:
- Translate each content block based on semantic type
- Apply type-aware translation (narrative, dialogue, verse, etc.)
- **ADD cultural/historical footnotes** for significant terms
- Integrate wuxia glossary for martial arts terminology
- Use consistent pinyin with tone marks

**Output**: Translated content blocks with footnotes

**Footnote Criteria** (see [Footnote Policy](#footnote-policy)):
- ✅ Proper names (people, places, titles)
- ✅ Cultural concepts and practices
- ✅ Historical references
- ✅ Literary allusions
- ✅ Martial arts techniques (NOT in glossary)
- ❌ Common words (walking, looking, etc.)
- ❌ Character psychology
- ❌ Plot interpretation

#### 7.5 Special Sections Translation (WITH FOOTNOTES)

**Input**: `structure.front_matter` (intro, preface) and `structure.back_matter` (afterword, appendix)
**Process**:
- Translate prefaces, introductions, author notes
- Translate afterwords, appendices
- **ADD appropriate footnotes** for cultural/historical context
- Less dense footnoting than body content (use judgment)

**Output**: Translated special sections with selective footnotes

**Rationale**: Special sections often contain cultural commentary that benefits from annotation, but typically need fewer footnotes than narrative body content.

---

## Translation Rules and Policies

### Consistency Requirements

1. **Chapter Title Consistency**
   - TOC translations are **canonical**
   - Chapter headings in body MUST match TOC exactly
   - Any decorative elements (☆, 　, etc.) should be preserved but not translated

2. **Pinyin Consistency**
   - All pinyin MUST have tone marks (ā á ǎ à ē é ě è ī í ǐ ì ō ó ǒ ò ū ú ǔ ù ǖ ǘ ǚ ǜ)
   - Use IDENTICAL pinyin for recurring concepts (enables deduplication)
   - Example: "紂王" → ALWAYS "Zhòu Wáng" (not "Zhou Wang" or "Zhouwang")

3. **Wuxia Glossary Integration**
   - Use glossary translations for standardized martial arts terminology
   - Apply glossary's `translation_strategy` (PINYIN_ONLY, ENGLISH_ONLY, HYBRID)
   - Use glossary's `recommended_form` and `footnote_template` verbatim
   - Exception: Individual technique names (translate to English, not in glossary)

4. **Tense Usage**
   - **Narrative prose**: Use simple PAST tense ("He walked", NOT "He walks")
   - **Dialogue**: Use tenses appropriate to speech act (present, past, future)
   - **Descriptive passages**: Match narrative tense
   - This is critical for Classical Chinese which doesn't mark tense

### Translation Quality Standards

**Target Audience**: PhD-level reader interested in historical/cultural context

**Quality Bar**:
- Scholarly and sophisticated (think David Hawkes, Arthur Waley)
- Precise and exact (no approximations, no vagueness)
- Literarily accomplished (quality writing)
- NOT dumbed down (assume intelligence and cultural curiosity)
- NO sloppiness (user values precision and careful writing)

**Type-Aware Translation**: Adapt tone and register based on semantic content type:
- **dialogue**: Natural quotation marks (""), conversational tone
- **verse**: Poetic language, preserve rhythm where possible
- **action_sequence**: Dynamic verbs, kinetic flow
- **narrative**: Flowing literary prose
- **descriptive**: Rich sensory language
- **internal_thought**: Introspective voice
- **letter/document**: Formal register
- **inscription**: Terse, monumental

### Two-Pass Editorial Validation

**Pass 1**: Translation → Editor Review
- Translator generates translation with footnotes
- Editor validates for accuracy, fluency, footnote quality, pinyin consistency
- If issues found: generate revision feedback

**Pass 2**: Revision → Editor Review
- Translator revises based on feedback
- Editor validates revision
- If still issues: log as "validated_with_issues" and proceed

**Thread Isolation**: Each pass uses NEW OpenAI threads to prevent cross-contamination

---

## Footnote Policy

### What Gets Footnoted

**✅ DO footnote**:
1. **Proper names**
   - People: Historical figures, characters (with context)
   - Places: Cities, landmarks, regions (with historical background)
   - Titles: Official positions, ranks (with dynasty context)
   - Must include pinyin with tone marks in footnote

2. **Cultural concepts**
   - Ritual practices (jìn xiāng 進香, ancestral worship)
   - Social structures (kinship terms, hierarchies)
   - Philosophical concepts (dào 道, dé 德, qì 氣)
   - Traditional customs (festivals, ceremonies)

3. **Historical references**
   - Dynasties, emperors, events (with dates)
   - Classical texts (*Shiji* 史記, *Lunyu* 論語)
   - Historical sources and citations

4. **Literary allusions**
   - Classical poetry references
   - Genre conventions
   - Narrative tropes with cultural significance

5. **Martial arts terminology** (from wuxia glossary)
   - General concepts: nèigōng 內功, nèilì 內力
   - Weapons: jiàn 劍, dāo 刀
   - Social roles: xiákè 俠客, shīfu 師父
   - Medical terms: dāntián 丹田, jīngmài 經脈
   - BUT: Individual technique names → translate to English

6. **Measurements and time systems**
   - Traditional measurements (lǐ 里, chǐ 尺)
   - Calendrical systems
   - Time periods (gēng 更, shíchén 時辰)

**❌ DO NOT footnote**:
1. **Obvious translations**
   - Common words (walking, looking, peeking)
   - Simple verbs of motion, observation
   - Everyday concepts any reader would understand

2. **Narrative/plot elements**
   - Character psychology ("this shows X's motivation")
   - Plot interpretation ("the reader should understand...")
   - Story developments explained in text itself

3. **Trivial concepts**
   - Simple actions (sitting, standing, eating)
   - Basic emotions (happy, sad, angry)
   - Self-explanatory terms

### Footnote Quality Standards

**Depth**: Full, thorough explanations (not brief glosses)
- Bad: "紂王 - Last Shang Dynasty ruler"
- Good: "紂王 (Zhòu Wáng) - King Zhou, personal name Di Xin 帝辛 (r. c. 1075-1046 BCE), last ruler of the Shang Dynasty. Traditional historiography, particularly Sima Qian's *Shiji* 史記, depicts him as a paradigmatic tyrant..."

**Structure**:
1. Ideogram
2. Pinyin with tone marks (REQUIRED)
3. Brief identification
4. Historical/cultural context
5. Literary significance (if relevant)
6. Classical sources (if applicable)

**Factual Focus**:
- ✅ Historical facts, dates, cultural practices
- ✅ Literary tradition and genre context
- ❌ Character analysis or psychological interpretation
- ❌ Reader guidance or plot explanation

### Footnote Deduplication

**After Translation**:
- Deduplicate footnotes by `footnote_ideogram`
- Keep first occurrence with full explanation
- Later occurrences: brief reference or omit entirely
- Consistent pinyin enables accurate matching

---

## Quality Standards

### Translation Completeness

**Required**:
- All Chinese text translated (metadata, TOC, headings, body, special sections)
- No missing chapters or content blocks
- All semantic types preserved (narrative, dialogue, verse, etc.)
- Block IDs and structure maintained

### Footnote Integrity

**Required**:
- Footnote markers [1], [2], [3] sequential and consistent
- Every marker in text has corresponding footnote
- No duplicate or missing footnote numbers
- All pinyin has tone marks (ā á ǎ à...)

### Format Validation

**Required**:
- Valid JSON structure
- Schema compliance (translated JSON schema)
- Proper character escaping
- UTF-8 encoding

### Quality Metrics

**Scoring** (0-100):
- Translation completeness: 30 points
- Footnote quality: 25 points
- Pinyin accuracy: 20 points
- Format correctness: 15 points
- Scholarly depth: 10 points

**Passing Score**: ≥ 90

---

## WIP Management

### Incremental Saves

**Save WIP after EVERY stage**:
- Stage 7.1: Metadata translated
- Stage 7.2: TOC translated
- Stage 7.3: Chapter headings translated
- Stage 7.4: Body content translated
- Stage 7.5: Special sections translated
- Stage 8: Footnotes cleaned
- Stage 9: Quality validated

### WIP Directory Structure

```
{wip_dir}/{job_id}/
├── stage_7.1_metadata/
│   ├── {work_number}.json
│   └── stage_metadata.json
├── stage_7.2_toc/
│   ├── {work_number}.json
│   └── stage_metadata.json
├── stage_7.3_headings/
│   ├── {work_number}.json
│   └── stage_metadata.json
├── stage_7.4_body/
│   ├── {work_number}.json
│   └── stage_metadata.json
├── stage_7.5_special/
│   ├── {work_number}.json
│   └── stage_metadata.json
├── stage_8_cleanup/
│   ├── {work_number}.json
│   └── stage_metadata.json
└── stage_9_validation/
    ├── {work_number}.json
    ├── qa_report.json
    └── stage_metadata.json
```

### Stage Metadata Format

```json
{
  "stage_num": 7.4,
  "stage_name": "body_translation",
  "timestamp": "2025-01-15T10:30:45Z",
  "duration_seconds": 245.8,
  "blocks_processed": 150,
  "tokens_used": 12500,
  "api_calls": 30,
  "status": "completed",
  "errors": [],
  "warnings": ["High token usage on chapter 15"]
}
```

### Rollback Capability

**Enable rollback to any stage**:
- Load WIP from target stage
- Reset job status to that stage
- Resume processing from there
- Useful for testing, debugging, parameter tuning

---

## Error Handling and Recovery

### Error Categories

1. **TRANSIENT**: Network blip → Retry immediately
2. **RATE_LIMIT**: API quota exceeded → Exponential backoff, retry
3. **VALIDATION**: Output validation failed → Log, skip, or manual review
4. **PERSISTENT**: Repeated failures → Circuit breaker, alert admin
5. **FATAL**: Unrecoverable → Fail job, detailed error report

### Retry Strategy

**Configuration**:
- Max retries: 3
- Initial delay: 2 seconds
- Exponential backoff: 2× per attempt
- Max delay: 60 seconds
- Timeout: 300 seconds per API call

**Circuit Breaker**:
- After 5 consecutive failures: open circuit
- Pause all API calls for 5 minutes
- Resume with reduced concurrency (50%)
- Gradually restore full concurrency if successful

### Recovery from Crashes

**Job State Persistence**:
- Save job state after each stage
- Store in SQLite database
- Include: job_id, work_number, current_stage, progress_percentage, WIP paths

**Resume Process**:
1. Load job state from database
2. Identify last completed stage
3. Load WIP from that stage
4. Resume processing from next stage

---

## Integration Points

### Input: Cleaned JSON

**Source**: Stage 6 output from json-book-restructurer pipeline

**Required Fields**:
- `meta`: work_number, title, author, volume, language, schema_version
- `structure.front_matter.toc`: Array of TOC entries with chapter_id mappings
- `structure.body.chapters`: Array of chapters with content_blocks
- `structure.back_matter`: Optional special sections

**Validation**: Run schema validation before translation

### Output: Translated JSON

**Format**: Same structure as input, with translations

**New Fields**:
- `translation_metadata`: Translation service info, token usage, timestamps
- `footnotes_metadata`: Deduplication stats, cleanup actions

**File Naming**: `{work_number}_translated.json`

### Integration with EPUB Builder (Future)

**Output**: Translated JSON ready for EPUB conversion

**Requirements**:
- Footnotes embedded with proper markers
- Semantic types preserved for formatting
- Chapter IDs maintained for hyperlinks
- Metadata complete for EPUB metadata section

---

## Performance Requirements

### Throughput Targets

- **Single block**: 10-15 seconds (including two-pass validation)
- **Average chapter**: 3-5 minutes (20-30 blocks)
- **Typical book**: 2-4 hours (30-50 chapters, 500-1000 blocks)

### Concurrency Limits

- **Blocks per book**: 5 concurrent (to avoid rate limits)
- **Books in batch**: 3 concurrent (resource management)
- **API calls**: Rate limiting at 0.5s intervals

### Resource Management

- **Token budget**: Track per book, alert at 80% of quota
- **API quota**: Monitor rate limits, auto-throttle if approaching
- **Memory usage**: Process large books in chunks, not all in memory
- **Disk space**: Monitor WIP directory size, clean up old jobs

---

## Validation Requirements

### Pre-Translation Validation

**Check before starting**:
- Input JSON schema valid
- All required fields present
- No malformed content blocks
- Catalog metadata accessible
- API keys configured and valid

### Post-Translation Validation

**Check after completion**:
- All source blocks have translations
- Footnote markers match footnote list
- Pinyin has tone marks
- Chapter headings match TOC
- No untranslated Chinese text (except ideograms in footnotes)
- JSON structure valid
- Quality score ≥ 90

### Continuous Validation

**During processing**:
- Monitor API response validity
- Check for JSON parse errors
- Validate footnote structure
- Verify pinyin formatting
- Track token usage vs. estimates

---

## Version History

- **1.0.0** (2025-01-15): Initial specification
  - Complete pipeline architecture
  - Translation rules and policies
  - Footnote policy and quality standards
  - WIP management specification
  - Error handling and recovery patterns
  - Integration points defined
  - Performance and validation requirements

---

## Related Documentation

- [Translation Data Contracts](./TRANSLATION_DATA_CONTRACTS.md) - Detailed format specifications
- [Wuxia Glossary Integration Guide](./WUXIA_GLOSSARY_INTEGRATION_GUIDE.md) - Glossary usage
- [BEST_PRACTICES.md](../BEST_PRACTICES.md) - Coding standards
- [CLAUDE.md](../../CLAUDE.md) - Project technical guidance