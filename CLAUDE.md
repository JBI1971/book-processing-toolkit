# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**📖 For organizational standards and coding conventions, see [docs/BEST_PRACTICES.md](docs/BEST_PRACTICES.md)**

## Project Overview

**Book Processing Toolkit** - Complete pipeline for processing books from raw JSON through cleaning, AI structuring, translation, footnotes, to final EPUB generation.

**Vision**: `Raw JSON → Clean → Structure → Translate → Footnotes → EPUB`

**Current Status**:
- ✅ JSON Cleaner (implemented)
- ✅ Post-Processing Tools (chapter alignment, TOC restructuring, embedded chapter detection)
- ✅ Validation Tools (sanity checker, sequence validator, TOC alignment validator)
- ✅ Content Structurer (implemented)
- ✅ Batch Pipeline (8-stage processing with metadata enrichment)
- ✅ Translation Orchestration (7-stage pipeline with AI footnotes + cleanup)
- ✅ Footnote Cleanup (AI-powered character name removal + deduplication)
- 🚧 EPUB Builder (placeholder)

## Development Commands

### Environment Setup
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development
```

### Running Processors

```bash
# JSON cleaning (no API needed)
python cli/clean.py --input book.json --output cleaned.json --language zh-Hant

# AI-powered structuring (requires OPENAI_API_KEY)
python cli/structure.py --input cleaned.json --output structured.json --max-workers 3

# Structure validation (requires OPENAI_API_KEY for AI classification)
python cli/validate_structure.py --input cleaned.json --output validation_report.json

# Translation orchestration (7-stage pipeline with footnote cleanup)
python scripts/orchestrate_translation_pipeline.py D1379  # Translate work D1379
python scripts/orchestrate_translation_pipeline.py D1379 --volume a  # Specific volume
python scripts/orchestrate_translation_pipeline.py D1379 --resume  # Resume from checkpoint

# Standalone footnote cleanup (if needed separately)
python cli/cleanup_character_footnotes.py --input translated.json --output-dir ./cleaned

# Future processors (placeholders)
python cli/build_epub.py --input translated.json --output book.epub
```

### Testing
```bash
pytest                          # Run all tests
pytest tests/test_specific.py   # Run specific test
pytest -v                       # Verbose output
pytest --cov                    # Coverage report
```

### Code Quality
```bash
black processors ai utils cli   # Format code
flake8 processors ai utils cli  # Lint code
mypy processors ai utils cli    # Type checking
```

### Package Scripts (npm)
```bash
npm run clean      # Run JSON cleaner
npm run structure  # Run content structurer
npm run test       # Run pytest
npm run lint       # Run flake8
npm run format     # Run black
```

## Architecture

### Pipeline Structure

```
processors/
├── json_cleaner.py          [IMPLEMENTED] Raw JSON → Discrete blocks
├── content_structurer.py    [IMPLEMENTED] Blocks → Semantic types
├── structure_validator.py   [IMPLEMENTED] AI-powered TOC/structure validation
├── translator.py            [PLACEHOLDER] Translate content
├── footnote_generator.py    [PLACEHOLDER] Add scholarly notes
└── epub_builder.py          [PLACEHOLDER] Generate EPUB file

utils/
├── topology_analyzer.py         [IMPLEMENTED] Structure analysis without modification
├── sanity_checker.py            [IMPLEMENTED] Early validation with metadata enrichment
├── catalog_metadata.py          [IMPLEMENTED] Extract metadata from SQLite catalog
├── chapter_sequence_validator.py [IMPLEMENTED] Chinese chapter numbering validation
├── toc_alignment_validator.py   [IMPLEMENTED] OpenAI-powered TOC validation
├── fix_chapter_alignment.py     [IMPLEMENTED] Fix EPUB metadata mismatches
├── restructure_toc.py           [IMPLEMENTED] Convert TOC to structured navigation
├── embedded_chapter_detector.py [IMPLEMENTED] Detect/extract chapters from intro sections
├── clients/                     [IMPLEMENTED] API wrappers (OpenAI, Anthropic)
└── http/                        [IMPLEMENTED] HTTP with retry logic

scripts/
├── batch_process_books.py   [IMPLEMENTED] 8-stage pipeline with metadata enrichment
└── fix_embedded_chapter1.py [IMPLEMENTED] Standalone embedded chapter extractor

ai/
└── assistant_manager.py     [IMPLEMENTED] Manage OpenAI assistants

cli/
├── clean.py                 [IMPLEMENTED] CLI for json_cleaner
├── structure.py             [IMPLEMENTED] CLI for content_structurer
├── validate_structure.py    [IMPLEMENTED] CLI for structure_validator
├── translate.py             [PLACEHOLDER] CLI for translator
├── footnotes.py             [PLACEHOLDER] CLI for footnote_generator
└── build_epub.py            [PLACEHOLDER] CLI for epub_builder
```

### Data Flow

**Standard Batch Pipeline (8 Stages)**:
```
RAW INPUT (source JSON in individual directories)
   ↓
[Stage 1] utils/topology_analyzer.py
   → Analyze JSON structure without modifications
   → Estimate tokens for AI processing
   → Identify content locations and nesting depth
   → Deterministic, no API calls
   ↓
[Stage 2] utils/sanity_checker.py
   → Extract metadata from catalog SQLite database
     (work_number, title, author, volume)
   → Validate Chinese chapter numbering sequences
   → Detect missing, duplicate, or out-of-order chapters
   → Parse Chinese numerals: 一二三...十廿卅卌...百千
   → Non-fatal validation (continues on errors)
   ↓
[Stage 3] processors/json_cleaner.py
   → Recursive extraction from nested structures
   → TOC auto-detection
   → Block ID generation (block_0000, block_0001...)
   → EPUB ID generation (heading_0, para_1...)
   → Enrich with catalog metadata (work_number, title, author, volume)
   ↓
CLEANED JSON (discrete blocks + metadata)
   ↓
[Stage 4] utils/embedded_chapter_detector.py
   → Detect chapters embedded in introduction/title pages
   → Extract ANY chapter marker (一、二、三... 廿、卅、卌... 第N章/回)
   → Works for any starting chapter number (not limited to Chapter 1)
   → Handles multi-volume works with different numbering schemes
   → Creates new chapter, renumbers existing, updates TOC
   → Removes chapter content from introduction section
   → Non-fatal (continues on errors)
   ↓
[Stage 5] utils/fix_chapter_alignment.py
   → Fix EPUB metadata mismatches
   → Match chapter titles to actual content headings
   → Support 第N回 (hui) and 第N章 (zhang) formats
   → Support special numerals: 廿 (20), 卅 (30), 卌 (40)
   → Split combined chapters
   → Deterministic, pattern-based
   ↓
[Stage 6] utils/restructure_toc.py
   → Convert TOC from text blob to structured list
   → Create chapter references for EPUB navigation
   → Handle blob format (space-separated entries)
   → Generate TOC from chapters when missing
   → Support Chinese numerals including 廿/卅/卌
   → Fuzzy matching for variants
   ↓
[Stage 7] Comprehensive Validation (3 validators)
   → batch_process_books.py orchestrates multiple validators:

   A. processors/structure_validator.py
      - AI-powered chapter classification (front_matter, body, back_matter)
      - Detects special sections (preface, afterword, appendix)
      - Quality scoring

   B. utils/toc_chapter_validator.py
      - Extracts actual headings from content_blocks
      - OpenAI-powered semantic TOC/chapter title matching
      - Detects missing chapters, title mismatches
      - Handles Chinese numeral variations (廿/卅/卌)

   C. utils/toc_body_count_validator.py [NEW]
      - Validates TOC entry count matches body chapter count
      - Identifies specific chapters missing from TOC
      - Detects extra TOC entries not in body
      - Fast, deterministic (no API calls)

   → All validators run in parallel
   → Results merged with error/warning categorization
   → Requires OPENAI_API_KEY for validators A & B
   ↓
VALIDATED JSON (ready for translation)
```

**Translation Orchestration Pipeline (7 Stages)**:
```
CLEANED & VALIDATED JSON
   ↓
scripts/orchestrate_translation_pipeline.py
   ↓
[Stage 1] METADATA Translation
   → Translate title, author, publisher
   → NO footnotes (clean metadata only)
   → Output: Translated meta block
   ↓
[Stage 2] TOC Translation
   → Translate table of contents entries
   → NO footnotes (clean navigation)
   → Preserve chapter references
   ↓
[Stage 3] HEADINGS Translation
   → Translate chapter titles/headings
   → NO footnotes (clean headings)
   → Sequential processing
   ↓
[Stage 4] BODY Translation
   → Translate main content blocks
   → WITH cultural/historical footnotes
   → AI-powered footnote generation:
     • Character names with pinyin (Yáng Lùchán[1])
     • Cultural concepts (氣[2] - vital energy)
     • Historical references
     • Martial arts terminology
   → Parallel processing (configurable workers)
   → Checkpoint/resume support
   ↓
[Stage 5] SPECIAL SECTIONS Translation
   → Translate front_matter/back_matter
   → WITH footnotes for cultural content
   → Prefaces, afterwords, appendices
   ↓
[Stage 6] FOOTNOTE PROCESSING ✨
   → Multiple cleanup stages process footnotes sequentially
   → ALL stages require work-level processing (entire work at once)
   → Footnote renumbering after each stage maintains consistency

   [6a] CHARACTER FOOTNOTE CLEANUP [INTEGRATED - AUTOMATIC]
   → AI classification (OpenAI GPT-4.1-nano)
   → Remove fictional character footnotes
     Examples removed: 魯世雄 (404×), 完顏長之 (160×)
   → Preserve historical figures (康熙帝, 孔子, 李白)
   → Preserve legendary personages (關羽, 觀音)
   → Preserve cultural notes (氣, 內功, 金國)
   → Work-wide deduplication (keep only first occurrence)
   → Typical reduction: 50-60% of footnotes
   → Configuration: --skip-character-footnote-cleanup

   [6b] DUPLICATE TERM CLEANUP [SCRIPT GENERATOR - MANUAL]
   → Use footnote-deduplicator agent to generate scripts
   → Removes duplicate cultural term explanations
   → Agent generates (does NOT execute):
     • exact_match_deletion.py
     • candidate_analysis.py
     • ai_assisted_deletion.py
     • validation_suite.py
   → You review and run scripts manually
   → Additional ~10-20% reduction

   [6c-6z] FUTURE FOOTNOTE STAGES [RESERVED]
   → Cross-reference consolidation
   → Redundant pinyin cleanup
   → Footnote length optimization
   → Custom cleanup rules
   → Each stage maintains work-level processing
   ↓
[Stage 7] VALIDATION
   → Verify translation completeness
   → Check footnote marker integrity
   → Quality scoring
   → Generate final report
   ↓
TRANSLATED JSON (ready for EPUB)
   → English translation with optimized footnotes
   → WIP files saved for each stage
   → Detailed logs and progress reports
   ↓
processors/epub_builder.py [TODO]
   → EPUB 3.0 generation
   → Internal linking via block IDs
   ↓
FINAL EPUB FILE
```

### Translation Orchestration Commands

**Basic Usage**:
```bash
# Translate single work
python scripts/orchestrate_translation_pipeline.py D1379

# Translate specific volume
python scripts/orchestrate_translation_pipeline.py I1046 --volume a

# Resume from checkpoint (if interrupted)
python scripts/orchestrate_translation_pipeline.py D1379 --resume

# Process specific stages only
python scripts/orchestrate_translation_pipeline.py D1379 --start-stage 4 --end-stage 6

# Dry run (no file writes)
python scripts/orchestrate_translation_pipeline.py D1379 --dry-run
```

**Output Structure**:
```
/Users/jacki/project_files/translation_project/
├── wip/                                    # Work-in-progress files
│   ├── stage_1_metadata/
│   ├── stage_2_toc/
│   ├── stage_3_headings/
│   ├── stage_4_body/
│   ├── stage_5_special/
│   ├── stage_6_cleanup/                   # After footnote cleanup
│   └── stage_7_validation/
├── translation_data/
│   ├── translated_D1379_偷拳_白羽.json   # Final output
│   └── logs/
│       ├── D1379_translation.log          # Main translation log
│       ├── D1379_stage_1_metadata.json    # Stage-specific logs
│       ├── D1379_stage_2_toc.json
│       ├── D1379_stage_3_headings.json
│       ├── D1379_stage_4_body.json
│       ├── D1379_stage_5_special.json
│       ├── D1379_stage_6_cleanup.json     # Footnote cleanup details
│       ├── D1379_stage_7_validation.json
│       └── checkpoints/
│           └── D1379_checkpoint.json      # Resume checkpoint
```

**Footnote Cleanup Results** (Stage 6):
- Classification log includes removed vs preserved breakdown
- Example metrics:
  - Total footnotes: 3,876
  - Fictional characters removed: 2,054 (53%)
  - Cultural/historical preserved: 1,822
  - Work-wide duplicates removed: ~1,063
  - Final unique footnotes: ~800

## Key Implementation Details

### JSON Cleaner (processors/json_cleaner.py)

**Input Formats Supported**:
- `{chapters: [{title, content}]}` - Standard format
- `{sections: [{title, content}]}` - Alternative field names
- Content as string, HTML-like objects, or nested structures

**Block Extraction**:
- Recursive `extract_blocks_from_nodes()` handles arbitrary nesting
- Recognizes tags: h1-h6, p, div, section, article, body, ul, ol, li
- Generates sequential IDs: `block_0000`, `block_0001`...
- Creates EPUB IDs: `heading_0`, `para_1`, `text_2`, `list_3`

**TOC Detection**:
- Title keywords: "目錄", "目录", "contents", "table of contents", "toc"
- Structure heuristic (first chapter only): ≥5 lines with 70%+ having ≤15 chars

**Output Structure**:
```json
{
  "meta": {
    "title": "Book Title",
    "author": "Author Name",
    "work_number": "I0929",
    "volume": "a",
    "language": "zh-Hant",
    "schema_version": "2.0.0"
  },
  "structure": {
    "front_matter": {"toc": [...]},
    "body": {"chapters": [{"id", "title", "ordinal", "content_blocks": [...]}]},
    "back_matter": {}
  }
}
```

### Catalog Metadata Extractor (utils/catalog_metadata.py)

**Purpose**: Extract metadata from SQLite catalog database for enrichment

**Database Schema**:
- `works` table: work_id, work_number, title_chinese, title_english, author_chinese, author_english
- `work_files` table: work_id, directory_name, volume

**Classes**:
- `WorkMetadata` - Dataclass holding extracted metadata
- `CatalogMetadataExtractor` - Main extractor with query methods

**Key Methods**:
```python
def get_metadata_by_directory(self, directory_name: str) -> Optional[WorkMetadata]:
    """
    Extract metadata by directory name (e.g., 'wuxia_0117').
    Returns WorkMetadata with work_number, title, author, volume.
    """
```

**Usage**:
```python
extractor = CatalogMetadataExtractor('wuxia_catalog.db')
metadata = extractor.get_metadata_by_directory('wuxia_0117')
# Returns: WorkMetadata(work_number='I0929', title_chinese='羅剎夫人',
#                       author_chinese='朱貞木', volume=None)
```

### Chinese Chapter Sequence Validator (utils/chapter_sequence_validator.py)

**Purpose**: Validate Chinese chapter numbering sequences and detect gaps/duplicates

**Chinese Numeral Support**:
- Basic: 一二三四五六七八九十
- Special: 廿 (20), 卅 (30), 卌 (40)
- Large: 百 (100), 千 (1000)

**Parsing Logic**:
```python
def parse_chinese_number(self, text: str) -> Optional[int]:
    """
    Parse Chinese numerals including special cases:
    - 廿一 → 21 (20 + 1)
    - 卅五 → 35 (30 + 5)
    - 第三十二章 → 32
    """
```

**Classes**:
- `SequenceIssue` - Dataclass for validation issues (gap, duplicate, out_of_order)
- `ChineseChapterSequenceValidator` - Main validator

**Common Issue Types**:
- `gap` - Missing chapter numbers (e.g., ch 1, 2, 4 missing 3)
- `duplicate` - Same chapter number appears twice
- `out_of_order` - Chapters not in ascending order
- `nonstandard_start` - Book starts at ch 2+ instead of ch 1

### Sanity Checker (utils/sanity_checker.py)

**Purpose**: Combined early validation with metadata enrichment (Stage 2)

**Integration**:
- Combines `CatalogMetadataExtractor` + `ChineseChapterSequenceValidator`
- Runs after topology analysis, before cleaning
- Non-fatal: continues processing even on errors

**Classes**:
- `SanityCheckResult` - Dataclass with metadata, issues, summary
- `BookSanityChecker` - Main checker

**Workflow**:
```python
checker = BookSanityChecker(catalog_path='wuxia_catalog.db')
result = checker.check(
    json_file=Path('book.json'),
    directory_name='wuxia_0117',
    strict_sequence=False  # Don't fail on sequence issues
)
# Returns: SanityCheckResult with metadata + sequence_issues
```

**Output**:
- `metadata`: WorkMetadata from catalog
- `sequence_issues`: List of SequenceIssue objects
- `has_errors`: Boolean indicating critical issues
- `summary`: Human-readable summary string

### Chapter Alignment Fixer (utils/fix_chapter_alignment.py)

**Purpose**: Fix EPUB metadata mismatches (Stage 4)

**What It Fixes**:
- Matches chapter titles to actual content headings
- Splits combined chapters (multiple headings in one chapter)
- Handles duplicate headings with ordinals

**Supported Formats**:
- 第N回 - Traditional episode format (hui)
- 第N章 - Modern chapter format (zhang)
- Special numerals: 廿 (20), 卅 (30), 卌 (40)

**Known Issue**:
⚠️ Assumes books start at Chapter 1. Some books (e.g., volume 3 of series) start at Chapter 2+, which causes incorrect chapter_number fields in TOC.

**Usage**:
```python
fixer = ChapterAlignmentFixer()
result = fixer.fix_chapter_alignment_in_file('cleaned_book.json')
# Modifies file in-place, returns fix count
```

### Embedded Chapter Detector (utils/embedded_chapter_detector.py)

**Purpose**: Detect and extract chapters embedded in introduction/title pages (Stage 4)

**Problem Addressed**: In Chinese novels, the first chapter of EACH volume is often embedded within the title page or introduction section, not properly separated into the body chapters.

**What It Detects**:
- ANY Chinese chapter marker (一、二、三... 廿、卅、卌... 第N章/回)
- Works for any starting chapter number (not limited to Chapter 1)
- Handles multi-volume works with different numbering schemes:
  - Reset per volume (Vol 1: 1-20, Vol 2: 1-20)
  - Continuous across volumes (Vol 1: 1-20, Vol 2: 21-40)
  - Irregular numbering (Vol 3 starts at 31 instead of 41)

**What It Does**:
1. Scans introduction sections for chapter markers
2. Extracts chapter content blocks from introduction
3. Creates new chapter with proper ID and ordinal
4. Renumbers existing chapters if necessary
5. Updates TOC to include extracted chapter
6. Removes chapter content from introduction section

**Classes**:
- `EmbeddedChapterDetector` - Main detector with extraction logic
- Convenience function: `detect_embedded_chapters(data)` for external callers

**Key Methods**:
```python
def find_embedded_chapter(intro_section) -> Optional[int]:
    """Find block index where chapter starts (any chapter number)"""

def detect_and_extract(data) -> Tuple[Dict, bool]:
    """Main entry point - returns (modified_data, was_modified)"""
```

**Usage**:
```python
from utils.embedded_chapter_detector import detect_embedded_chapters

modified_data, was_modified = detect_embedded_chapters(cleaned_json)
if was_modified:
    print(f"Extracted chapter from introduction")
```

**Integration**: Automatically runs as Stage 4 in batch processing pipeline.

**Standalone Script**: `scripts/fix_embedded_chapter1.py` available for manual fixes outside pipeline.

### TOC Restructurer (utils/restructure_toc.py)

**Purpose**: Convert TOC from text blob to structured navigation (Stage 6)

**What It Does**:
- Parses space-separated TOC entries from blob format
- Creates chapter references (chapter_id, chapter_number)
- Generates TOC from chapters when missing
- Fuzzy matching for minor character variants (薄/泊, 到/至)

**Structured TOC Format**:
```json
{
  "toc": [
    {
      "full_title": "第一章　標題",
      "chapter_title": "標題",
      "chapter_number": 1,
      "chapter_id": "chapter_0001"
    }
  ]
}
```

**Chinese Numeral Support**:
- Full character set including 廿/卅/卌
- Regex patterns updated in 2 locations (lines ~175 and ~362)

### TOC/Body Count Validator (utils/toc_body_count_validator.py)

**Purpose**: Validate that TOC entries match body chapters by count and chapter numbers

**What It Detects**:
- Missing chapters from TOC (chapters in body but not in TOC)
- Extra TOC entries (TOC references non-existent chapters)
- Count mismatches between TOC and body

**Classes**:
- `CountMismatchIssue` - Represents a chapter missing from or extra in TOC
- `CountValidationResult` - Complete validation result with issues
- `TOCBodyCountValidator` - Main validator

**Key Methods**:
```python
def validate_toc_body_alignment(self, cleaned_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simplified validation that returns:
    - valid: bool
    - toc_count: int
    - body_count: int
    - missing_from_toc: list of chapter numbers in body but not TOC
    - extra_in_toc: list of chapter numbers in TOC but not body
    - missing_chapters: list of dicts with {chapter_num, title, id}
    """
```

**Usage**:
```python
from utils.toc_body_count_validator import validate_toc_body_alignment

result = validate_toc_body_alignment(cleaned_json)
if not result['valid']:
    for ch in result['missing_chapters']:
        print(f"Missing: Ch {ch['chapter_num']} - {ch['title']}")
```

**CLI Usage**:
```bash
# Full validation with detailed report
python utils/toc_body_count_validator.py input.json

# Simplified alignment check
python utils/toc_body_count_validator.py input.json --use-alignment

# Save report
python utils/toc_body_count_validator.py input.json --save-report
```

**Integration**: Automatically runs as part of Stage 7 validation in batch processing pipeline.

### TOC Alignment Validator (utils/toc_alignment_validator.py)

**Purpose**: OpenAI-powered semantic TOC/chapter title validation (basic, legacy)

**Validation Method**:
- Batch processing (20 TOC/chapter pairs per API call)
- GPT-4o-mini with low temperature (0.1) for consistency
- JSON response format for structured results

**Classes**:
- `AlignmentIssue` - Dataclass for mismatch issues
- `AlignmentResult` - Complete validation result
- `TOCAlignmentValidator` - Main validator

**Issue Types**:
- `mismatch` - TOC doesn't match chapter title
- `number_mismatch` - Chapter numbers don't align
- `missing_chapter` - TOC references non-existent chapter
- `typo` - Minor transcription error

**API Call Pattern**:
```python
validator = TOCAlignmentValidator(model='gpt-4.1-nano', temperature=0.1)
result = validator.validate(cleaned_json)
# Returns: AlignmentResult with issues, confidence_score, summary
```

**Output Metrics**:
- `is_valid` - Boolean (True if no errors)
- `total_pairs` - Number of TOC/chapter pairs checked
- `matched_pairs` - Number of successful matches
- `confidence_score` - Percentage (0-100%)
- `issues` - List of AlignmentIssue objects with severity

### Comprehensive TOC/Chapter Validator (utils/toc_chapter_validator.py)

**Purpose**: Advanced validation that extracts actual chapter headings from content_blocks (Stage 7 - enhanced)

**Key Innovation**: Unlike the basic validator above, this validator extracts the **actual heading from content_blocks** to detect when:
- Book metadata is incorrectly treated as a chapter
- First chapter heading is buried in content
- TOC lists chapters that don't exist in the body
- Chapter topology doesn't match TOC structure

**Validation Workflow**:
1. Extract TOC entries from `front_matter.toc`
2. Extract **actual chapter headings** from each chapter's `content_blocks` (first heading-type block)
3. Parse chapter numbers from actual headings (第N章/回)
4. Compare TOC entries to actual chapter headings
5. Detect missing chapters, sequence gaps, duplicates
6. Use OpenAI for semantic validation of ambiguous mismatches

**Classes**:
- `TOCChapterValidator` - Main validator with heading extraction
- `ChapterHeading` - Extracted heading data (chapter_index, actual_heading, chapter_number)
- `TOCEntry` - TOC entry data
- `AlignmentIssue` - Issue found during validation
- `ValidationReport` - Complete report with detailed metrics

**Issue Types**:
- `missing_toc` - No TOC found in front_matter
- `missing_chapters` - No chapters found in body
- `count_mismatch` - TOC count ≠ chapter count
- `missing_chapter` - TOC references chapter that doesn't exist (e.g., 第一章 in TOC but body starts at 第二章)
- `duplicate_chapter_number` - Same chapter number appears multiple times
- `title_mismatch` - TOC title doesn't match actual heading
- `chapter_not_in_toc` - Chapter exists but not in TOC
- `sequence_gap` - Missing chapter numbers in sequence

**Usage**:
```python
from utils.toc_chapter_validator import TOCChapterValidator

validator = TOCChapterValidator(use_ai=True)
report = validator.validate(cleaned_json)

# Report includes:
# - toc_entries: List of TOC entries
# - chapter_headings: List of extracted headings with actual chapter numbers
# - issues: Detailed list of problems
# - confidence_score: Match percentage
# - is_valid: True if no errors

# Save detailed report
report = validator.validate_file('cleaned_book.json', save_report=True)
# Generates: cleaned_book_validation_report.json
```

**Report Metrics**:
- `toc_count` - Number of TOC entries
- `chapter_count` - Number of body chapters
- `matched_count` - Successfully matched pairs
- `confidence_score` - Match percentage (0-100%)
- `is_valid` - True if no errors
- `summary` - Human-readable summary
- `issues` - List with severity, type, message, details, suggested_fix

**AI Validation**:
- Only used for ambiguous title mismatches
- Batch processing (10 pairs per call)
- Model: gpt-4.1-nano, temperature: 0.1
- Classifies mismatches as: real_mismatch, minor_difference, transcription_error
- Provides suggested fixes for typos

**Example Output**:
```
TOC/CHAPTER ALIGNMENT VALIDATION REPORT
Summary: TOC Entries: 20 | Body Chapters: 19 | Matched: 19 | Confidence: 95.0% | Errors: 1
Valid: ✗ No

TOC ENTRIES (20):
   1. 第一章　神秘的年輕人
   2. 第二章　從天而降的救星
   ...

BODY CHAPTERS (19):
   2. 第二章　從天而降的救星 [body_chapter]
   3. 第三章　大變忽然來 [body_chapter]
   ...

ISSUES FOUND (2):
✗ [ERROR] missing_chapter
   TOC references chapter 1 '神秘的年輕人' but it's not in body
   💡 Suggested fix: Check if chapter is missing from source EPUB or was incorrectly filtered
```

**Integration**:
- Used in `batch_process_books.py` as part of Stage 7 validation
- CLI available: `scripts/validate_toc_chapter_alignment.py`
- Generates detailed JSON reports for debugging

### Content Structurer (processors/content_structurer.py)

**Classes**:
- `ProcessingConfig` - Configuration dataclass (max_retries, timeout, mode)
- `SchemaValidator` - Validates against JSON schema
- `TextChunker` - Splits large texts (max 4000 chars, 200 overlap)
- `ContentStructuringProcessor` - Main processor with retry/batch support

**Processing Modes**:
- STRICT - Fail on first error
- FLEXIBLE (default) - Retry most errors
- BEST_EFFORT - Continue despite errors

**Semantic Block Types**:
- `narrative`, `dialogue`, `verse`, `document`, `thought`, `descriptive`, `chapter_title`

**OpenAI Assistant Pattern**:
```python
thread = client.beta.threads.create()
client.beta.threads.messages.create(thread_id, role="user", content=text)
run = client.beta.threads.runs.create(thread_id, assistant_id)
# Poll until completed (max 300s)
messages = client.beta.threads.messages.list(thread_id)
# Parse JSON response
```

**Batch Processing**:
- ThreadPoolExecutor with configurable workers (default: 3)
- Rate limiting: 0.5s delay between requests
- Progress tracking with tqdm (optional)

### Structure Validator (processors/structure_validator.py)

**Purpose**: AI-powered validation of TOC/chapter alignment and structural classification

**Validation Checks**:
1. **TOC Coverage** - Ensures all chapters are represented in TOC
2. **TOC/Chapter Alignment** - Verifies TOC entries match actual chapter titles
3. **Chapter Numbering** - Checks for gaps and duplicates in ordinals
4. **Section Classification** - AI classifies chapters as front_matter, body, or back_matter
5. **Special Section Detection** - Identifies prefaces, afterwords, appendices, etc.

**Classes**:
- `StructureValidator` - Main validation engine
- `ValidationIssue` - Represents a single validation issue (error/warning/info)
- `ChapterClassification` - AI classification result for a chapter
- `ValidationResult` - Complete validation report with scores

**Section Types**:
- `FRONT_MATTER` - Preface, introduction, author notes
- `BODY` - Main story chapters
- `BACK_MATTER` - Afterword, appendix, notes

**Special Section Types** (Chinese novel structure):
- `preface` - 自序, 前言, 序
- `introduction` - 引言, 序章
- `prologue` - 序幕, 楔子
- `afterword` - 後記, 跋
- `appendix` - 附錄
- `author_note` - 作者註, 說明
- `epilogue` - 尾聲
- `main_chapter` - Regular story chapter

**AI Classification Pattern**:
```python
# Uses OpenAI to semantically analyze chapter titles
validator = StructureValidator(model="gpt-4.1-nano", temperature=0.3)
result = validator.validate(cleaned_json_data)

# Graceful degradation: Falls back to basic validation if AI fails
# (API key issues, rate limits, etc.)
```

**Output Metrics**:
- `toc_coverage` - Percentage of chapters in TOC (0-100%)
- `structure_quality` - Overall quality score (0-100)
- `is_valid` - Boolean indicating no critical errors
- `issues` - List of errors/warnings with suggestions

**Integration with Batch Pipeline**:
- Automatically runs as Stage 5 in `batch_process_books.py`
- Falls back to basic validation if OpenAI API unavailable
- Generates detailed validation reports (JSON)

**Usage Example**:
```python
from processors.structure_validator import StructureValidator

validator = StructureValidator()
result = validator.process_file(
    input_path="cleaned_book.json",
    save_report=True  # Saves to {input}_validation.json
)

print(f"Valid: {result.is_valid}")
print(f"TOC Coverage: {result.toc_coverage}%")
print(f"Quality Score: {result.structure_quality}/100")

for issue in result.issues:
    print(f"[{issue.severity}] {issue.message}")
```

**Common Issues Detected**:
- Partial title mismatches (e.g., TOC has decorators like "☆☆☆" not in chapter)
- Missing chapters from TOC
- Invalid TOC references (pointing to non-existent chapters)
- Out-of-order sections (e.g., afterword before main chapters)
- Duplicate or missing chapter ordinals

### Assistant Manager (ai/assistant_manager.py)

**Purpose**: Centralized OpenAI assistant lifecycle management with versioning

**Storage**: `.assistants/` directory (JSON files)

**Key Methods**:
- `create_assistant(name, instructions, schema, model, temperature)`
- `get_assistant(name, version)` - version can be "v1", "v2", "latest"
- `list_assistants()` - All stored configs
- `update_assistant(name, updates)` - Modify existing
- `delete_assistant(name, version, remote=False)` - Remove with optional API deletion
- `export_assistant(name, version)` - Export config
- `import_assistant(file_path)` - Import config
- `compare_versions(name, v1, v2)` - Show differences

**Versioning**: Supports semantic versions, tracks changes, "latest" keyword

## Configuration & Environment

### Required Environment Variables
```bash
export OPENAI_API_KEY=your-key-here        # For AI features
export ANTHROPIC_API_KEY=your-key-here     # Optional alternative
```

### Default Paths
- Input: `./input/book.json`
- Output: `./output/cleaned_book.json`
- Assistants: `.assistants/` (AI configs)
- Schemas: `schemas/` (JSON schemas)

### Processing Defaults

**json_cleaner.py**:
- DEFAULT_INPUT_PATH: `./input/book.json`
- DEFAULT_OUTPUT_PATH: `./output/cleaned_book.json`
- DEFAULT_LANGUAGE: `zh-Hant`

**content_structurer.py**:
- max_retries: 3
- retry_delay: 2.0s
- rate_limit_delay: 0.5s
- timeout: 300s (5 min)
- max_workers: 3
- max_chunk_size: 4000 chars
- chunk_overlap: 200 chars

**structure_validator.py**:
- model: "gpt-4.1-nano"
- temperature: 0.3 (low for consistent validation)
- timeout: 60s (1 min)
- save_report: True (generates validation JSON)

**toc_alignment_validator.py**:
- model: "gpt-4.1-nano"
- temperature: 0.1 (very low for consistency)
- batch_size: 20 (TOC/chapter pairs per API call)

**batch_process_books.py**:
- catalog_path: Required (path to SQLite catalog database)
- dry_run: False (set True to skip file writes)
- limit: None (process all files, or set number for testing)
- 6-stage pipeline: topology → sanity_check → cleaning → alignment → toc → validation

## Dependencies

From `requirements.txt`:
- `openai>=1.0.0` - OpenAI API client
- `anthropic>=0.18.0` - Anthropic API client
- `httpx>=0.24.0` - Async HTTP
- `beautifulsoup4>=4.12.0` + `lxml>=4.9.0` - HTML parsing
- `tenacity>=8.2.0` - Retry logic
- `tqdm>=4.65.0` - Progress bars
- `pytest>=7.4.0` - Testing

## Common Workflows

### Add New Block Type

1. Update `SchemaValidator.validate()` in content_structurer.py:
   ```python
   valid_types = [..., "new_type"]
   ```
2. Update assistant instructions to recognize new type
3. Update schema file if using validation

### Process Large Book

```bash
# Automatic chunking for >4000 chars
python cli/structure.py --input large_novel.txt --output result.json

# Disable chunking (may hit token limits)
python cli/structure.py --input novel.txt --no-chunking
```

### Debug AI Assistant

```bash
# List all assistants
python ai/assistant_manager.py list

# View specific config
python ai/assistant_manager.py export --name structuring --version latest

# Compare versions
python ai/assistant_manager.py compare --name structuring --version1 v1 --version2 v2
```

### Batch Processing (6-Stage Pipeline)

**Complete Pipeline** (recommended):
```bash
# Process all files with full pipeline
python scripts/batch_process_books.py \
  --source-dir /path/to/source_files \
  --output-dir /path/to/output \
  --catalog-path /path/to/wuxia_catalog.db \
  --log-dir ./logs

# Test on subset
python scripts/batch_process_books.py \
  --source-dir /path/to/source_files \
  --output-dir /path/to/output \
  --catalog-path /path/to/wuxia_catalog.db \
  --limit 10  # Process first 10 files only
```

**Individual Stage Processing**:
```bash
# Run specific post-processing stages
python utils/fix_chapter_alignment.py --input cleaned_book.json
python utils/restructure_toc.py --input cleaned_book.json
python -m utils.toc_alignment_validator cleaned_book.json

# Content structuring (separate from 6-stage pipeline)
python cli/structure.py --input ./books/ --output ./results/ --max-workers 5
```

**Pipeline Output**:
- Detailed JSON report in logs directory
- Stage-by-stage success rates
- File-level results with warnings and errors
- Performance metrics (time per file, tokens estimated)
- Issue categorization (topology errors, TOC mismatches, etc.)

### Implement New Processor

1. Create file in `processors/` (e.g., `translator.py`)
2. Implement processor class with `process()` method
3. Update `processors/__init__.py` to export it
4. Create CLI in `cli/` (e.g., `translate.py`)
5. Add entry point in `pyproject.toml` [project.scripts]
6. Add npm script in `package.json`
7. Update README.md roadmap

## File Organization

### Processors Module Structure
Each processor should follow this pattern:
```python
class ProcessorName:
    def __init__(self, **config):
        """Initialize with configuration"""

    def process(self, data: Dict) -> Dict:
        """Main processing method"""

    def process_file(self, input_path: str, output_path: str):
        """File-based processing"""

def main():
    """CLI entry point with argparse"""

if __name__ == "__main__":
    exit(main())
```

### CLI Module Structure
Each CLI should wrap a processor:
```python
#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from processors.module_name import main

if __name__ == "__main__":
    sys.exit(main())
```

## Testing Notes

Current test coverage is minimal (`tests/test_sanity.py` only).

When adding tests:
- Test each processor independently
- Mock AI API calls (don't hit real APIs in tests)
- Test edge cases: empty input, malformed JSON, large files
- Test chunking boundary conditions
- Test batch processing concurrency
- Validate output schema compliance

## Error Handling Patterns

### Retry Strategy (content_structurer.py)
- 3 attempts with 2s delay
- 300s timeout per request
- Mode-dependent: FLEXIBLE retries, STRICT fails fast
- Handles: JSON parse errors, validation failures, API failures

### Schema Validation
Checks:
- `content_blocks` array exists and non-empty
- Each block has: `id`, `type`, `content`, `metadata`
- Valid block types from predefined list
- IDs start with `block_`
- Non-empty content

### Batch Processing
- ThreadPoolExecutor catches individual failures
- Continues processing remaining files (unless STRICT mode)
- Returns: `{file: {status: "success|failed", result|error}}`

## Migration Notes

### v0.1.0 → v0.2.0 (Current Refactoring)

**File Moves**:
- `clean_input_json.py` → `processors/json_cleaner.py`
- `content_structuring_processor.py` → `processors/content_structurer.py`
- `translation_assistant_manager.py` → `ai/assistant_manager.py`
- `src/template_pkg/clients/*` → `utils/clients/`
- `src/template_pkg/scraping/*` → `utils/http/`
- `TRANSLATION_ASSISTANT_MANAGER_GUIDE.md` → `docs/AI_ASSISTANT_GUIDE.md`

**CLI Changes**:
- Old: `python clean_input_json.py --input book.json`
- New: `python cli/clean.py --input book.json`

**Import Changes**:
- Old: `from clean_input_json import clean_book_json`
- New: `from processors.json_cleaner import clean_book_json`

## Known Issues and Limitations

### Embedded First Chapter Pattern (Per Volume)

**Status**: ✅ **RESOLVED** - Now handled automatically by Stage 4 of batch processing pipeline

**Pattern**: First chapter of a volume embedded in title/introduction page

**Common in Chinese novels**: The first chapter of EACH volume is often embedded within what appears to be a title page or introduction section.

**Examples**:
- Volume 1: First chapter (typically "一、...") embedded in title page
- Volume 2: First chapter (could be "一、..." if reset, or "廿一、..." if continuing)
- Volume 3: First chapter (could be "三十一、...", "卅一、...", "一、..." depending on numbering scheme)

**Note**: Chapter numbering varies by work:
- Some reset to Chapter 1 per volume
- Some continue across volumes (Vol 1: 1-20, Vol 2: 21-40)
- Some have irregular numbering (Vol 3 might start at 31, not 41)

**Automatic Solution**: As of integration update, this is now handled automatically by:
- **Stage 4**: `utils/embedded_chapter_detector.py` in batch processing pipeline
- Runs automatically after JSON cleaning, before chapter alignment
- No manual intervention required

**Manual Solution** (if needed outside pipeline):
Use `scripts/fix_embedded_chapter1.py` standalone script to:
1. Extract first chapter from introduction/title page (regardless of chapter number)
2. Create proper chapter in body.chapters
3. Update TOC to include the extracted chapter
4. Clean introduction section (remove story content)

**Detection Capabilities**:
- ANY Chinese chapter markers (一、二、三... 廿、卅、卌... 第N章/回)
- Multiple possible intro locations (front_matter.introduction, front_matter.sections, etc.)
- Content boundaries between intro metadata and story content
- Works for any starting chapter number (not limited to Chapter 1)

**Multi-Volume Works**: Each volume file is processed separately, with automatic detection for each

### Chapter Alignment Fixer

**Issue**: Assumes books start at Chapter 1

**Problem**:
- The fixer in `utils/fix_chapter_alignment.py` assumes all books start at Chapter 1
- Some books (e.g., volume 3 of a series) start at Chapter 2 or higher
- This causes incorrect `chapter_number` fields in TOC entries

**Example**:
- Book: 羅剎夫人 (I0929) - Actually starts at 第二章 (Chapter 2)
- After processing: TOC shows 第一章 pointing to title page instead of first actual chapter
- Result: TOC chapter_number fields don't match actual chapter headings

**Workaround**:
- Sanity checker detects this as `nonstandard_start` issue (info severity)
- Validation stage may flag TOC/chapter mismatches
- Consider fixing the alignment fixer to detect and respect actual starting chapter

### Chinese Numeral Parsing

**Fixed**: Special numerals 廿 (20), 卅 (30), 卌 (40) now fully supported

**Historical Issue**:
- Before fix: 第廿一章 was parsed as 1 instead of 21
- Caused false duplicate chapter errors
- Fixed in `chapter_sequence_validator.py` with special case handling

### TOC Blob Parsing

**Edge Case**: Space-separated entries on single line

**Handling**:
- `restructure_toc.py` uses careful pattern matching
- Avoids over-splitting on internal spaces in chapter titles
- Supports both blob format and structured format

## Git Workflow

**IMPORTANT**: Git commits should ONLY be created when explicitly requested by the user.

- Do NOT create commits automatically after completing tasks
- Do NOT commit changes unless the user specifically asks you to
- Always ask the user if they want changes committed to git
- Wait for explicit confirmation before running git commands

When the user does request a commit, follow the standard git commit protocol as documented in the project guidelines.

## Roadmap Awareness

When implementing features, reference the roadmap in README.md:

- **v0.3.0**: Translator processor (language detection, glossaries)
- **v0.4.0**: Footnote generator (citation styles, cultural notes)
- **v0.5.0**: EPUB builder (EPUB 3.0, CSS themes, cover images)

Placeholders exist for all future processors with TODO comments indicating planned features.
- the source json files are individual diretoriestries  in a directory  /Users/jacki/project_files/translation_project/wuxia_individual_files