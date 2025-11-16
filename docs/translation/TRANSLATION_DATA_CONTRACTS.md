# Translation Data Contracts

**Version**: 1.0.0
**Last Updated**: 2025-01-15
**Purpose**: Detailed format specifications for data exchange in the translation pipeline

This document defines the exact data structures used at each stage of the translation pipeline. All services MUST adhere to these contracts.

---

## Table of Contents

1. [Input Format: Cleaned JSON](#input-format-cleaned-json)
2. [Translation Service Request/Response](#translation-service-requestresponse)
3. [Translated JSON Output](#translated-json-output)
4. [WIP Checkpoint Format](#wip-checkpoint-format)
5. [Job State Format](#job-state-format)
6. [Progress Event Format](#progress-event-format)
7. [QA Report Format](#qa-report-format)
8. [EPUB Builder Input (Future)](#epub-builder-input-future)

---

## Input Format: Cleaned JSON

**Source**: Output from Stage 6 (structure validation) of json-book-restructurer pipeline

**Schema Version**: 2.0.0

### Complete Structure

```json
{
  "meta": {
    "title": "羅剎夫人",
    "author": "朱貞木",
    "work_number": "I0929",
    "volume": {
      "volume_letter": null,
      "volume_number": 1,
      "total_volumes": 1,
      "title_suffix": null
    },
    "language": "zh-Hant",
    "schema_version": "2.0.0"
  },
  "structure": {
    "front_matter": {
      "intro": [
        {
          "id": "block_0000",
          "epub_id": "intro_0",
          "type": "paragraph",
          "content": "引言內容...",
          "metadata": {}
        }
      ],
      "toc": [
        {
          "full_title": "第二章　從天而降的救星",
          "chapter_title": "從天而降的救星",
          "chapter_number": 2,
          "chapter_id": "chapter_0001"
        }
      ]
    },
    "body": {
      "chapters": [
        {
          "id": "chapter_0001",
          "title": "從天而降的救星",
          "ordinal": 2,
          "content_blocks": [
            {
              "id": "block_0001",
              "epub_id": "heading_0",
              "type": "heading",
              "content": "第二章　從天而降的救星",
              "metadata": {"level": 2}
            },
            {
              "id": "block_0002",
              "epub_id": "para_1",
              "type": "paragraph",
              "content": "章節內容...",
              "metadata": {}
            }
          ]
        }
      ]
    },
    "back_matter": {
      "afterword": [],
      "appendix": []
    }
  },
  "validation": {
    "toc_mapping_complete": true,
    "intro_separated": true,
    "chapter_sequence_valid": true,
    "errors": []
  }
}
```

### Field Descriptions

**meta**:
- `title` (string): Chinese title from catalog database
- `author` (string): Chinese author from catalog database
- `work_number` (string): Unique work identifier (e.g., "I0929", "D63a")
- `volume` (object): Volume information for multi-volume works
  - `volume_letter` (string|null): Letter designation ('a', 'b', 'c') or null for single-volume
  - `volume_number` (integer): Canonical volume number (1, 2, 3...)
  - `total_volumes` (integer): Total volumes in this work
  - `title_suffix` (string|null): Optional volume title (e.g., "卷一")
- `language` (string): Source language code ("zh-Hant" for Traditional Chinese)
- `schema_version` (string): Data format version ("2.0.0")

**structure.front_matter.toc**:
- `full_title` (string): Complete TOC entry text
- `chapter_title` (string): Extracted chapter title
- `chapter_number` (integer): Chapter number
- `chapter_id` (string): Reference to chapter in body (e.g., "chapter_0001")

**structure.body.chapters**:
- `id` (string): Unique chapter identifier
- `title` (string): Chapter title
- `ordinal` (integer): Chapter number (may not start at 1)
- `content_blocks` (array): Ordered content blocks

**content_blocks**:
- `id` (string): Block identifier (e.g., "block_0001")
- `epub_id` (string): EPUB reference ID (e.g., "para_1")
- `type` (string): Semantic type (see [Content Block Types](#content-block-types))
- `content` (string): Actual text content
- `metadata` (object): Type-specific metadata (e.g., `{"level": 2}` for headings)

### Content Block Types

**12 Semantic Types** (from EPUB formatting pipeline):

1. **heading**: Chapter/section titles
2. **paragraph**: Standard narrative prose (alias: **narrative**)
3. **dialogue**: Character speech
4. **descriptive**: Scenery, visual descriptions
5. **action_sequence**: Fight scenes, martial arts
6. **internal_thought**: Character thoughts
7. **verse**: Classical Chinese poetry
8. **letter**: Correspondence, missives
9. **document**: Edicts, official documents
10. **inscription**: Tombstones, plaques
11. **transition**: Scene/time transitions
12. **author_note**: Author commentary

**Metadata Examples**:
- `heading`: `{"level": 1}` (h1) or `{"level": 2}` (h2)
- `verse`: `{"stanza": 1, "line": 3}`
- `dialogue`: `{"speaker": "character_name"}` (optional)

---

## Translation Service Request/Response

### Request Format

**Single Block Translation**:

```json
{
  "content_text_id": 13,
  "content_source_text": "且言紂王只因進香之後，看見女媧美貌...",
  "content_type": "narrative"
}
```

**Fields**:
- `content_text_id` (integer): Unique block identifier (for tracking)
- `content_source_text` (string): Chinese text to translate
- `content_type` (string, optional): Semantic type for type-aware translation

### Response Format

**Single Block Translation**:

```json
{
  "content_text_id": 13,
  "original_input": {
    "content_source_text": "且言紂王只因進香之後..."
  },
  "translated_annotated_content": {
    "annotated_content_text": "Now let us speak of King Zhou[1]. After his visit to offer incense[2] at the temple...",
    "content_footnotes": [
      {
        "footnote_key": 1,
        "footnote_details": {
          "footnote_ideogram": "紂王",
          "footnote_pinyin": "Zhòu Wáng",
          "footnote_explanation": "King Zhou, personal name Di Xin 帝辛 (r. c. 1075-1046 BCE)..."
        }
      },
      {
        "footnote_key": 2,
        "footnote_details": {
          "footnote_ideogram": "進香",
          "footnote_pinyin": "jìn xiāng",
          "footnote_explanation": "The ritual act of offering incense at a temple..."
        }
      }
    ],
    "content_type": "narrative"
  },
  "metadata": {
    "translation_attempts": 1,
    "editorial_issues": [],
    "status": "validated",
    "processing_time_seconds": 12.4
  }
}
```

**Fields**:
- `content_text_id`: Echoed from request
- `original_input`: Copy of request for reference
- `translated_annotated_content`: Translation result
  - `annotated_content_text`: English translation with footnote markers [1], [2], etc.
  - `content_footnotes`: Array of footnote objects
    - `footnote_key`: Sequential integer (1, 2, 3...)
    - `footnote_details`:
      - `footnote_ideogram`: Original Chinese characters
      - `footnote_pinyin`: Romanization WITH tone marks (required)
      - `footnote_explanation`: Full cultural/historical explanation
  - `content_type`: Semantic type (preserved or inferred)
- `metadata`: Processing information
  - `translation_attempts`: Number of revision cycles (1-2)
  - `editorial_issues`: Array of validation issues found
  - `status`: "validated" or "validated_with_issues"
  - `processing_time_seconds`: Duration

### Batch Request Format

```json
{
  "requests": [
    {
      "content_text_id": 1,
      "content_source_text": "...",
      "content_type": "narrative"
    },
    {
      "content_text_id": 2,
      "content_source_text": "...",
      "content_type": "dialogue"
    }
  ],
  "options": {
    "max_concurrent": 5,
    "preserve_order": true
  }
}
```

### Batch Response Format

```json
{
  "responses": [
    {
      "content_text_id": 1,
      "original_input": {...},
      "translated_annotated_content": {...},
      "metadata": {...}
    },
    {
      "content_text_id": 2,
      "original_input": {...},
      "translated_annotated_content": {...},
      "metadata": {...}
    }
  ],
  "batch_metadata": {
    "total_blocks": 2,
    "successful": 2,
    "failed": 0,
    "total_tokens": 2500,
    "total_time_seconds": 25.8
  }
}
```

---

## Translated JSON Output

**Schema Version**: 2.0.0 (extended with translation fields)

### Complete Structure

```json
{
  "meta": {
    "title": "The Lady Raksasi",
    "title_chinese": "羅剎夫人",
    "author": "Zhu Zhenmu",
    "author_chinese": "朱貞木",
    "work_number": "I0929",
    "volume": {
      "volume_letter": null,
      "volume_number": 1,
      "total_volumes": 1,
      "title_suffix": null
    },
    "language": "en",
    "source_language": "zh-Hant",
    "schema_version": "2.0.0"
  },
  "structure": {
    "front_matter": {
      "intro": [
        {
          "id": "block_0000",
          "epub_id": "intro_0",
          "type": "paragraph",
          "content": "Introduction content...",
          "source_content": "引言內容...",
          "metadata": {},
          "footnotes": []
        }
      ],
      "toc": [
        {
          "full_title": "Chapter Two: The Savior Descends from Heaven",
          "full_title_chinese": "第二章　從天而降的救星",
          "chapter_title": "The Savior Descends from Heaven",
          "chapter_title_chinese": "從天而降的救星",
          "chapter_number": 2,
          "chapter_id": "chapter_0001"
        }
      ]
    },
    "body": {
      "chapters": [
        {
          "id": "chapter_0001",
          "title": "The Savior Descends from Heaven",
          "title_chinese": "從天而降的救星",
          "ordinal": 2,
          "content_blocks": [
            {
              "id": "block_0001",
              "epub_id": "heading_0",
              "type": "heading",
              "content": "Chapter Two: The Savior Descends from Heaven",
              "source_content": "第二章　從天而降的救星",
              "metadata": {"level": 2},
              "footnotes": []
            },
            {
              "id": "block_0002",
              "epub_id": "para_1",
              "type": "paragraph",
              "content": "Chapter content with footnote[1]...",
              "source_content": "章節內容...",
              "metadata": {},
              "footnotes": [
                {
                  "footnote_key": 1,
                  "footnote_details": {
                    "footnote_ideogram": "漢字",
                    "footnote_pinyin": "hànzì",
                    "footnote_explanation": "Full explanation..."
                  }
                }
              ]
            }
          ]
        }
      ]
    },
    "back_matter": {
      "afterword": [],
      "appendix": []
    }
  },
  "translation_metadata": {
    "translation_service": "TranslationService v1.0",
    "translation_date": "2025-01-15T10:30:45Z",
    "translator_model": "gpt-5-nano",
    "total_blocks_translated": 150,
    "total_tokens_used": 12500,
    "total_api_calls": 30,
    "total_footnotes_generated": 250,
    "glossary_terms_applied": 45,
    "translation_stages": [
      {"stage": "metadata", "timestamp": "2025-01-15T10:00:00Z", "duration_s": 5.2},
      {"stage": "toc", "timestamp": "2025-01-15T10:00:05Z", "duration_s": 12.4},
      {"stage": "headings", "timestamp": "2025-01-15T10:00:18Z", "duration_s": 8.1},
      {"stage": "body", "timestamp": "2025-01-15T10:00:26Z", "duration_s": 245.8},
      {"stage": "special", "timestamp": "2025-01-15T10:04:32Z", "duration_s": 15.3}
    ],
    "wip_stages_saved": [
      "stage_7.1_metadata",
      "stage_7.2_toc",
      "stage_7.3_headings",
      "stage_7.4_body",
      "stage_7.5_special"
    ]
  },
  "footnotes_metadata": {
    "total_footnotes_before_cleanup": 250,
    "total_footnotes_after_cleanup": 180,
    "character_name_footnotes_removed": 70,
    "duplicate_footnotes_removed": 0,
    "cleanup_date": "2025-01-15T10:35:00Z"
  },
  "validation": {
    "translation_complete": true,
    "footnote_integrity_check": "passed",
    "pinyin_validation": "passed",
    "quality_score": 95,
    "qa_report_path": "./logs/I0929_qa_report.json",
    "validation_date": "2025-01-15T10:40:00Z"
  }
}
```

### New Fields in Translated JSON

**meta** (extended):
- `title`: English translation
- `title_chinese`: Original Chinese title (preserved)
- `author`: English translation
- `author_chinese`: Original Chinese author (preserved)
- `language`: "en" (target language)
- `source_language`: "zh-Hant" (source language)

**content_blocks** (extended):
- `content`: English translation
- `source_content`: Original Chinese text (preserved)
- `footnotes`: Array of footnotes for this block only

**toc** (extended):
- `full_title`: English translation
- `full_title_chinese`: Original Chinese (preserved)
- `chapter_title`: English translation
- `chapter_title_chinese`: Original Chinese (preserved)

**chapters** (extended):
- `title`: English translation
- `title_chinese`: Original Chinese (preserved)

---

## WIP Checkpoint Format

### Stage Data File

**Filename**: `{wip_dir}/stage_{N}_{stage_name}/{work_number}.json`

**Content**: Complete JSON structure at that stage (same as Translated JSON Output)

### Stage Metadata File

**Filename**: `{wip_dir}/stage_{N}_{stage_name}/stage_metadata.json`

```json
{
  "stage_num": 7.4,
  "stage_name": "body_translation",
  "job_id": "abc123-def456",
  "work_number": "I0929",
  "timestamp": "2025-01-15T10:30:45Z",
  "duration_seconds": 245.8,
  "status": "completed",
  "input_file": "/path/to/cleaned/I0929.json",
  "output_file": "/path/to/wip/stage_7.4_body/I0929.json",
  "processing_details": {
    "blocks_processed": 150,
    "blocks_with_footnotes": 120,
    "total_footnotes_generated": 200,
    "tokens_used": 10000,
    "api_calls": 25
  },
  "errors": [],
  "warnings": [
    {
      "type": "high_token_usage",
      "message": "Chapter 15 used 800 tokens (above 500 threshold)",
      "block_id": "block_0120",
      "severity": "info"
    }
  ],
  "previous_stage": "stage_7.3_headings",
  "next_stage": "stage_7.5_special"
}
```

### Stage Log File

**Filename**: `{log_dir}/{work_number}_stage_{N}_{stage_name}.json`

```json
{
  "job_id": "abc123-def456",
  "work_number": "I0929",
  "stage_num": 7.4,
  "stage_name": "body_translation",
  "started_at": "2025-01-15T10:00:00Z",
  "completed_at": "2025-01-15T10:04:05Z",
  "duration_seconds": 245.8,
  "status": "completed",
  "log_entries": [
    {
      "timestamp": "2025-01-15T10:00:00Z",
      "level": "INFO",
      "message": "Starting body translation",
      "details": {"total_blocks": 150}
    },
    {
      "timestamp": "2025-01-15T10:00:15Z",
      "level": "INFO",
      "message": "Translated block",
      "details": {"block_id": "block_0001", "tokens": 50}
    },
    {
      "timestamp": "2025-01-15T10:02:30Z",
      "level": "WARN",
      "message": "High token usage",
      "details": {"block_id": "block_0120", "tokens": 800}
    },
    {
      "timestamp": "2025-01-15T10:04:05Z",
      "level": "INFO",
      "message": "Completed body translation",
      "details": {"blocks_translated": 150, "total_tokens": 10000}
    }
  ],
  "summary": {
    "total_entries": 152,
    "info_count": 150,
    "warn_count": 2,
    "error_count": 0
  }
}
```

---

## Job State Format

### Job Database Schema (SQLite)

```sql
CREATE TABLE translation_jobs (
    job_id TEXT PRIMARY KEY,
    work_number TEXT NOT NULL,
    title TEXT,
    author TEXT,
    status TEXT NOT NULL,  -- pending, running, paused, completed, failed
    current_stage TEXT,    -- stage_7.1_metadata, stage_7.2_toc, etc.
    progress_percentage REAL,
    started_at TEXT,
    updated_at TEXT,
    completed_at TEXT,
    input_path TEXT NOT NULL,
    output_dir TEXT NOT NULL,
    wip_dir TEXT NOT NULL,
    log_path TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(work_number)  -- One job per work at a time
);

CREATE TABLE job_metrics (
    job_id TEXT PRIMARY KEY,
    total_blocks INTEGER,
    blocks_translated INTEGER,
    total_footnotes INTEGER,
    tokens_estimated INTEGER,
    tokens_used INTEGER,
    api_calls INTEGER,
    translation_duration_seconds REAL,
    FOREIGN KEY (job_id) REFERENCES translation_jobs(job_id)
);

CREATE TABLE job_stages (
    stage_id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    stage_num REAL NOT NULL,
    stage_name TEXT NOT NULL,
    status TEXT NOT NULL,  -- pending, running, completed, failed
    started_at TEXT,
    completed_at TEXT,
    duration_seconds REAL,
    output_path TEXT,
    FOREIGN KEY (job_id) REFERENCES translation_jobs(job_id)
);
```

### Job State JSON (API Format)

```json
{
  "job_id": "abc123-def456",
  "work_number": "I0929",
  "title": "The Lady Raksasi",
  "author": "Zhu Zhenmu",
  "status": "running",
  "current_stage": "stage_7.4_body",
  "progress_percentage": 67.5,
  "started_at": "2025-01-15T10:00:00Z",
  "updated_at": "2025-01-15T10:30:00Z",
  "completed_at": null,
  "input_path": "/path/to/cleaned/I0929.json",
  "output_dir": "/path/to/translated",
  "wip_dir": "/path/to/wip/abc123-def456",
  "log_path": "/path/to/logs/I0929_translation.log",
  "error_message": null,
  "stages": [
    {
      "stage_num": 7.1,
      "stage_name": "metadata",
      "status": "completed",
      "started_at": "2025-01-15T10:00:00Z",
      "completed_at": "2025-01-15T10:00:05Z",
      "duration_seconds": 5.2,
      "output_path": "/path/to/wip/stage_7.1_metadata/I0929.json"
    },
    {
      "stage_num": 7.2,
      "stage_name": "toc",
      "status": "completed",
      "started_at": "2025-01-15T10:00:05Z",
      "completed_at": "2025-01-15T10:00:18Z",
      "duration_seconds": 12.4,
      "output_path": "/path/to/wip/stage_7.2_toc/I0929.json"
    },
    {
      "stage_num": 7.3,
      "stage_name": "headings",
      "status": "completed",
      "started_at": "2025-01-15T10:00:18Z",
      "completed_at": "2025-01-15T10:00:26Z",
      "duration_seconds": 8.1,
      "output_path": "/path/to/wip/stage_7.3_headings/I0929.json"
    },
    {
      "stage_num": 7.4,
      "stage_name": "body",
      "status": "running",
      "started_at": "2025-01-15T10:00:26Z",
      "completed_at": null,
      "duration_seconds": null,
      "output_path": null
    },
    {
      "stage_num": 7.5,
      "stage_name": "special",
      "status": "pending",
      "started_at": null,
      "completed_at": null,
      "duration_seconds": null,
      "output_path": null
    }
  ],
  "metrics": {
    "total_blocks": 150,
    "blocks_translated": 100,
    "total_footnotes": 180,
    "tokens_estimated": 15000,
    "tokens_used": 10000,
    "api_calls": 25,
    "translation_duration_seconds": 245.8
  }
}
```

---

## Progress Event Format

### Event Types

1. **stage_started**: New stage beginning
2. **block_completed**: Single block finished
3. **stage_completed**: Entire stage finished
4. **error**: Error occurred
5. **warning**: Warning issued

### Event Structure

```json
{
  "event_id": "evt_789",
  "timestamp": "2025-01-15T10:30:45.123Z",
  "job_id": "abc123-def456",
  "work_number": "I0929",
  "event_type": "block_completed",
  "stage": "stage_7.4_body",
  "details": {
    "block_id": "block_0050",
    "block_type": "paragraph",
    "footnotes_generated": 3,
    "tokens_used": 120,
    "translation_attempts": 1,
    "editorial_issues": 0
  },
  "progress": {
    "blocks_completed": 50,
    "blocks_total": 150,
    "percentage": 33.3,
    "eta_seconds": 300
  },
  "metrics": {
    "tokens_used_cumulative": 5000,
    "api_calls_cumulative": 12
  }
}
```

### Progress Stream Format (WebSocket/SSE)

```json
{
  "type": "progress_update",
  "job_id": "abc123-def456",
  "timestamp": "2025-01-15T10:30:45Z",
  "data": {
    "current_stage": "stage_7.4_body",
    "progress_percentage": 33.3,
    "blocks_completed": 50,
    "blocks_total": 150,
    "eta_seconds": 300,
    "current_block_id": "block_0050",
    "recent_events": [
      {
        "timestamp": "2025-01-15T10:30:45Z",
        "event_type": "block_completed",
        "message": "Translated block_0050 (paragraph)"
      }
    ]
  }
}
```

---

## QA Report Format

```json
{
  "job_id": "abc123-def456",
  "work_number": "I0929",
  "qa_date": "2025-01-15T10:40:00Z",
  "overall_score": 95,
  "passed": true,
  "categories": {
    "translation_completeness": {
      "score": 100,
      "max_score": 30,
      "details": {
        "total_blocks": 150,
        "blocks_translated": 150,
        "missing_translations": 0
      }
    },
    "footnote_quality": {
      "score": 23,
      "max_score": 25,
      "issues": [
        {
          "type": "shallow_footnote",
          "severity": "minor",
          "block_id": "block_0050",
          "message": "Footnote for '紂王' lacks historical depth"
        }
      ]
    },
    "pinyin_accuracy": {
      "score": 20,
      "max_score": 20,
      "details": {
        "total_pinyin": 200,
        "missing_tone_marks": 0,
        "inconsistent_romanization": 0
      }
    },
    "format_correctness": {
      "score": 15,
      "max_score": 15,
      "details": {
        "json_valid": true,
        "schema_compliant": true,
        "character_encoding_ok": true
      }
    },
    "scholarly_depth": {
      "score": 7,
      "max_score": 10,
      "details": {
        "avg_footnote_length": 120,
        "citations_present": true,
        "cultural_context_depth": "adequate"
      }
    }
  },
  "issues": [
    {
      "category": "footnote_quality",
      "severity": "minor",
      "type": "shallow_footnote",
      "location": "block_0050",
      "description": "Footnote for '紂王' lacks historical depth",
      "suggestion": "Add dynasty dates, reign period, historical significance"
    }
  ],
  "recommendations": [
    "Consider enriching footnotes in blocks: block_0050, block_0075",
    "Overall quality is excellent - ready for EPUB generation"
  ],
  "metrics": {
    "total_blocks_checked": 150,
    "total_footnotes_checked": 180,
    "total_issues_found": 1,
    "critical_issues": 0,
    "minor_issues": 1
  }
}
```

---

## EPUB Builder Input (Future)

**Format**: Translated JSON (same as output format above)

**Required Fields for EPUB**:
- `meta`: All fields for EPUB metadata
- `structure.front_matter.toc`: For EPUB navigation document
- `structure.body.chapters`: For main content
- All footnotes embedded in content_blocks

**Additional Requirements**:
- Valid UTF-8 encoding
- Footnote markers [1], [2], [3] must be sequential per chapter
- EPUB IDs must be unique across entire book
- Content types used for CSS styling

**EPUB-Specific Metadata** (to be added):
```json
{
  "epub_metadata": {
    "cover_image_path": "./covers/I0929.jpg",
    "publisher": "Wuxia Translation Project",
    "publication_date": "2025-01-15",
    "isbn": null,
    "language": "en",
    "creator": "Zhu Zhenmu",
    "translator": "AI Translation Service v1.0",
    "rights": "Public Domain"
  }
}
```

---

## Version History

- **1.0.0** (2025-01-15): Initial specification
  - Complete data contracts for all pipeline stages
  - Translation service request/response formats
  - WIP checkpoint formats
  - Job state and progress event formats
  - QA report structure
  - EPUB builder input requirements

---

## Related Documentation

- [Translation Pipeline Specification](./TRANSLATION_PIPELINE_SPEC.md) - Architectural rules
- [Wuxia Glossary Integration Guide](./WUXIA_GLOSSARY_INTEGRATION_GUIDE.md) - Glossary usage
- [BEST_PRACTICES.md](../BEST_PRACTICES.md) - Coding standards
- [CLAUDE.md](../../CLAUDE.md) - Project technical guidance
